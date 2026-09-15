"""All file I/O for the truck trip distribution model.

Responsibilities
----------------
- Load and validate the PA parquet, OMX skims, TLFD CSVs, and target OD parquets.
- Reconcile 1-based zone IDs (parquet) with 0-based array indexing (OMX).
- Write modeled trip matrices as long-format parquet and wide-format OMX.

Zone convention
---------------
PA parquet  → 1-based integer index (zones 1…N). Canonical zone list.
OMX arrays  → 0-based (row/col k = zone ID k+1 when no explicit mapping exists).
Target OD   → 1-based ``origin``/``destination`` columns.

All internal numpy arrays throughout the pipeline are 0-indexed. Zone ID ``z``
in the parquet corresponds to array index ``z-1`` in every OMX-derived matrix.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import openmatrix as omx
import pandas as pd


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_pa(path: Path) -> pd.DataFrame:
    """Load the productions/attractions parquet file.

    The index is expected to be 1-based integer zone IDs. No renaming or
    reindexing is applied — the caller receives the file as-is and
    references columns by the names declared in each ``RunConfig``.

    Parameters
    ----------
    path : Path
        Path to the PA parquet file.

    Returns
    -------
    pd.DataFrame
        DataFrame with 1-based integer zone IDs as the index and
        arbitrary production, attraction, and zone attribute columns.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the index is not integer dtype or contains duplicate zone IDs.
    """
    path = Path(path)

    pa = pd.read_parquet(path)
    idx = pa.index

    if not pd.api.types.is_integer_dtype(idx.dtype):
        raise ValueError(
            f"PA parquet index must contain integer zone IDs. "
            f"Got dtype: {idx.dtype}. File: {path}"
        )
    if not idx.is_unique:
        dupes = idx[idx.duplicated()].tolist()
        raise ValueError(
            f"PA parquet index contains duplicate zone IDs: {dupes}. "
            f"File: {path}"
        )

    return pa


def load_skims(
    path: Path,
    pa_zone_ids: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Load all matrices from an OMX skim file.

    Each matrix is returned as a float64 numpy array with 0-based
    indexing aligned to the PA zone list. Zone ID ``z`` corresponds
    to row/column ``z-1``.

    If ``pa_zone_ids`` is provided the function:

    1. Reads the zone mapping from the OMX file (falls back to sequential
       1-based IDs when no explicit mapping is stored).
    2. Verifies that every PA zone ID exists in the OMX mapping —
       raises if not.
    3. Filters each matrix to exactly the rows/columns matching the PA
       zones, in PA order. OMX files with more zones than the PA (e.g.
       statewide models with gateway zones) are silently trimmed.

    Parameters
    ----------
    path : Path
        Path to the OMX file.
    pa_zone_ids : np.ndarray or None, optional
        1-D array of 1-based integer zone IDs from the PA table, used
        to align and optionally filter the OMX arrays. When ``None``
        the matrices are returned at their native OMX size without any
        filtering or alignment validation.

    Returns
    -------
    dict[str, np.ndarray]
        Mapping of matrix name → (n_zones, n_zones) float64 array,
        where ``n_zones = len(pa_zone_ids)`` when filtering is applied.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the OMX file contains no matrices, or if any PA zone ID is
        absent from the OMX zone mapping.
    """
    path = Path(path)
    result: dict[str, np.ndarray] = {}

    with omx.open_file(str(path), "r") as f:
        matrix_names = list(f.list_matrices())
        if not matrix_names:
            raise ValueError(f"OMX file contains no matrices: {path}")

        # ── Read zone mapping from OMX ──────────────────────────────────
        # OMX files may store an explicit zone-ID mapping. If none is
        # present we assume sequential 1-based IDs (index 0 = zone 1).
        skim_zone_ids: np.ndarray
        try:
            available_mappings = f.list_mappings()
            if available_mappings:
                skim_zone_ids = np.array(
                    f.mapping(available_mappings[0]), dtype=np.int64
                )
            else:
                n = np.array(f[matrix_names[0]]).shape[0]
                skim_zone_ids = np.arange(1, n + 1, dtype=np.int64)
        except Exception:
            n = np.array(f[matrix_names[0]]).shape[0]
            skim_zone_ids = np.arange(1, n + 1, dtype=np.int64)

        # ── Build positional index for filtering ────────────────────────
        if pa_zone_ids is not None:
            pa_ids = np.asarray(pa_zone_ids, dtype=np.int64)
            skim_id_to_idx: dict[int, int] = {
                int(z): i for i, z in enumerate(skim_zone_ids)
            }
            missing = [int(z) for z in pa_ids if int(z) not in skim_id_to_idx]
            if missing:
                raise ValueError(
                    f"PA zone IDs not found in OMX skim: {missing}\n"
                    f"OMX has {len(skim_zone_ids)} zones "
                    f"(range {int(skim_zone_ids.min())}–{int(skim_zone_ids.max())})."
                )
            row_col_idx = np.array(
                [skim_id_to_idx[int(z)] for z in pa_ids], dtype=np.intp
            )
        else:
            row_col_idx = None

        # ── Load and optionally filter each matrix ──────────────────────
        for name in matrix_names:
            mat = np.array(f[name], dtype=np.float64)
            if row_col_idx is not None:
                mat = mat[np.ix_(row_col_idx, row_col_idx)]
            result[name] = mat

    # ── Post-load dimension validation ───────────────────────────────────
    if pa_zone_ids is not None:
        n_expected = len(pa_zone_ids)
        for name, mat in result.items():
            if mat.shape != (n_expected, n_expected):
                raise ValueError(
                    f"Skim '{name}' has shape {mat.shape} after filtering; "
                    f"expected ({n_expected}, {n_expected})."
                )

    return result


def load_tlfd(path: Path) -> pd.DataFrame:
    """Load and validate an observed trip length frequency distribution CSV.

    Required columns: ``bin_start``, ``bin_end``, ``share``.
    Additional columns are allowed and silently ignored.

    Validation (raises on failure):

    - Shares sum to approximately 1.0 (tolerance ±0.01).
    - Bins are non-overlapping (when sorted by ``bin_start``).
    - Bins are contiguous — no gaps between consecutive bin edges.

    After validation the shares are re-normalised to sum exactly to 1.0.

    Parameters
    ----------
    path : Path
        Path to the TLFD CSV file.

    Returns
    -------
    pd.DataFrame
        Validated and normalised DataFrame with columns
        ``bin_start`` (float), ``bin_end`` (float), ``share`` (float).
        Sorted by ``bin_start``, index reset to 0…N-1.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If required columns are missing, shares do not sum to ~1.0,
        or bins are non-contiguous or overlapping.
    """
    path = Path(path)

    df = pd.read_csv(path)

    # Required columns
    required = {"bin_start", "bin_end", "share"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"TLFD CSV missing required columns: {sorted(missing_cols)}. "
            f"Found: {sorted(df.columns.tolist())}. File: {path}"
        )

    df = df[["bin_start", "bin_end", "share"]].copy()
    df = df.sort_values("bin_start").reset_index(drop=True)

    # Shares must sum to ~1.0
    total = float(df["share"].sum())
    if abs(total - 1.0) > 0.01:
        raise ValueError(
            f"TLFD shares sum to {total:.6f}; expected 1.0 (tolerance ±0.01). "
            f"File: {path}"
        )

    # Bins must be non-overlapping and contiguous
    for i in range(len(df) - 1):
        end_i = float(df.loc[i, "bin_end"])
        start_next = float(df.loc[i + 1, "bin_start"])

        if end_i > start_next + 1e-9:
            raise ValueError(
                f"TLFD bins overlap: bin {i} [{df.loc[i, 'bin_start']}, {end_i}) "
                f"overlaps bin {i+1} [{start_next}, {df.loc[i+1, 'bin_end']}). "
                f"File: {path}"
            )
        if not np.isclose(end_i, start_next, atol=1e-9):
            raise ValueError(
                f"TLFD bins are not contiguous: bin {i} ends at {end_i} "
                f"but bin {i+1} starts at {start_next} "
                f"(gap = {start_next - end_i:.6f}). File: {path}"
            )

    # Normalise to sum exactly to 1.0
    df["share"] = df["share"] / df["share"].sum()

    return df


def load_od(
    path: Path,
    pa_zone_ids: np.ndarray | None = None,
) -> pd.DataFrame:
    """Load a target OD trip table from a long-format parquet file.

    Required columns: ``origin``, ``destination``, ``trips``.
    Zone IDs are 1-based integers matching the PA parquet index.

    Parameters
    ----------
    path : Path
        Path to the OD parquet file.
    pa_zone_ids : np.ndarray or None, optional
        1-D array of valid 1-based zone IDs from the PA table. When
        provided, every ``origin`` and ``destination`` value in the OD
        is validated against this set — raises if any unknown IDs are
        found.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ``origin`` (int), ``destination`` (int),
        ``trips`` (float). Zone IDs are 1-based.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If required columns are missing or any zone ID in the OD is not
        present in ``pa_zone_ids``.
    """
    path = Path(path)

    df = pd.read_parquet(path)

    required = {"origin", "destination", "trips"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Target OD parquet missing required columns: {sorted(missing_cols)}. "
            f"Found: {sorted(df.columns.tolist())}. File: {path}"
        )

    df = df[["origin", "destination", "trips"]].copy()

    # Validate zone IDs against the PA index when provided
    if pa_zone_ids is not None:
        valid_ids: set[int] = set(int(z) for z in pa_zone_ids)
        od_ids = set(int(z) for z in df["origin"].unique()) | set(
            int(z) for z in df["destination"].unique()
        )
        unknown = sorted(od_ids - valid_ids)
        if unknown:
            raise ValueError(
                f"Target OD contains zone IDs not present in PA index: {unknown}. "
                f"File: {path}"
            )

    return df


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_trips_parquet(
    trips: dict[str, np.ndarray],
    zone_ids: np.ndarray,
    output_dir: Path,
) -> None:
    """Write modeled trip matrices as a single long-format parquet file.

    Output file: ``output_dir/modeled_trips.parquet``.

    Columns: ``origin``, ``destination`` (1-based zone IDs), then one
    column per run name containing the modeled trip count (float64).
    All origin–destination pairs are included (including intrazonal).

    Parameters
    ----------
    trips : dict[str, np.ndarray]
        Mapping of run name → (n_zones, n_zones) float64 trip matrix.
        Arrays use 0-based indexing; zone ID ``z`` = row/col ``z-1``.
    zone_ids : np.ndarray
        1-D array of 1-based integer zone IDs, shape (n_zones,).
        Defines the mapping from array index to zone ID.
    output_dir : Path
        Directory to write the output file into (must already exist).

    Raises
    ------
    ValueError
        If any trip matrix shape does not match ``(len(zone_ids), len(zone_ids))``.
    """
    output_dir = Path(output_dir)
    n = len(zone_ids)

    # Build origin/destination ID grid (1-based)
    orig_ids, dest_ids = np.meshgrid(zone_ids, zone_ids, indexing="ij")

    df = pd.DataFrame(
        {
            "origin": orig_ids.ravel().astype(np.int64),
            "destination": dest_ids.ravel().astype(np.int64),
        }
    )

    for run_name, matrix in trips.items():
        if matrix.shape != (n, n):
            raise ValueError(
                f"Trip matrix for '{run_name}' has shape {matrix.shape}; "
                f"expected ({n}, {n})."
            )
        df[run_name] = matrix.ravel()

    df.to_parquet(output_dir / "modeled_trips.parquet", index=False)


def write_trips_omx(
    trips: dict[str, np.ndarray],
    output_dir: Path,
) -> None:
    """Write modeled trip matrices as a wide-format OMX file.

    Output file: ``output_dir/modeled_trips.omx``.
    One matrix per run name. For Cube/TP+ compatibility.
    Arrays are 0-based (row/col k = zone ID k+1).

    Parameters
    ----------
    trips : dict[str, np.ndarray]
        Mapping of run name → (n_zones, n_zones) float64 trip matrix.
    output_dir : Path
        Directory to write the output file into (must already exist).
    """
    output_dir = Path(output_dir)
    out_path = output_dir / "modeled_trips.omx"

    with omx.open_file(str(out_path), "w") as f:
        for run_name, matrix in trips.items():
            f[run_name] = matrix.astype(np.float64)
