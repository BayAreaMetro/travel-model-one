"""Dataclasses and YAML loader for the truck trip distribution model configuration.

``TripDistributionConfig.from_yaml`` is the single entry point for configuration.
If it returns without raising, the rest of the pipeline can trust that:
  - All required YAML fields are present and correctly typed.
  - Run ``name`` and ``short_name`` values are unique.
  - All declared file paths exist on disk.
  - Every ``productions_column``, ``attractions_column``, and ``geo_agg_cols``
    value is a column in the PA parquet (checked via schema peek, no data load).
  - Every ``skim_column`` is a matrix key in the OMX file (checked via a
    lightweight file open, no array load).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
import pyarrow.parquet as pq
import openmatrix as omx



@dataclass
class ModelSettings:
    """Algorithm tuning parameters and output location.

    Parameters
    ----------
    gravity_max_iters : int
        Maximum IPF iterations per gravity run.
    gravity_max_rmse : float
        Convergence threshold — RMSE of column sums vs target attractions
        (vehicle trips).
    optimizer_method : str
        ``scipy.optimize.minimize`` method name.
    optimizer_max_iters : int
        Maximum optimizer function evaluations.
    atl_penalty_weight : float
        Weight of the average-trip-length penalty term in the calibration
        loss. Set to 0.0 to optimize on TLFD shape only.
    verbosity : str
        Logging level: ``"DEBUG"``, ``"INFO"``, or ``"WARNING"``.
    output_dir : Path
        Root directory for all outputs (Excel, plots, matrices, log).
    gamma_b_bounds : tuple[float, float]
        Search bounds ``(lo, hi)`` for the gamma ``b`` parameter. Both
        values must be negative.
    gamma_c_bounds : tuple[float, float]
        Search bounds ``(lo, hi)`` for the gamma ``c`` parameter. Both
        values must be negative.
    """

    gravity_max_iters: int = 99
    gravity_max_rmse: float = 10.0
    optimizer_method: str = "Nelder-Mead"
    optimizer_max_iters: int = 500
    atl_penalty_weight: float = 0.1
    verbosity: str = "INFO"
    output_dir: Path = field(default_factory=lambda: Path("outputs/trip_distribution"))
    gamma_b_bounds: tuple[float, float] = (-3.0, -0.01)
    gamma_c_bounds: tuple[float, float] = (-0.5, -0.001)


@dataclass
class Inputs:
    """Shared file paths and zone attribute columns used by all runs.

    Parameters
    ----------
    pa_path : Path
        Parquet file with productions, attractions, and zone attributes.
        Index must be 1-based integer zone IDs.
    skim_path : Path
        OMX file containing pre-processed travel time matrices (one per
        truck type). Arrays are 0-based; zone ID ``z`` = row/col ``z-1``.
    geo_agg_cols : list[str]
        Zone attribute columns in the PA parquet used for geographic
        aggregation in outputs. Omit entirely (empty list) to skip all
        geo-aggregated tabs and plots.
    """

    pa_path: Path
    skim_path: Path
    geo_agg_cols: list[str] = field(default_factory=list)


@dataclass
class RunConfig:
    """Per-run data decisions: which columns, which skim, which files.

    Parameters
    ----------
    name : str
        Full run name used in output filenames and parquet columns. Must
        be unique across all runs.
    short_name : str
        Short label used as Excel tab prefix (keep ≤ 4 characters). Must
        be unique across all runs.
    productions_column : str
        Column in the PA parquet containing trip productions for this
        truck type (daily vehicle trips).
    attractions_column : str
        Column in the PA parquet containing trip attractions for this
        truck type (daily vehicle trips).
    skim_column : str
        Matrix name in the OMX file containing the travel time matrix
        (minutes) for this truck type.
    gamma_b0 : float
        Initial value for the gamma ``b`` parameter passed to the
        optimizer. Should be negative.
    gamma_c0 : float
        Initial value for the gamma ``c`` parameter passed to the
        optimizer. Should be negative.
    tlfd_path : Path
        CSV with the observed TLFD. Required columns: ``bin_start``,
        ``bin_end``, ``share``.
    target_od_path : Path or None
        Optional parquet with observed OD trips for validation. Required
        columns: ``origin``, ``destination``, ``trips`` (1-based zone IDs).
        If ``None``, all OD comparison outputs are skipped for this run.
    """

    name: str
    short_name: str
    productions_column: str
    attractions_column: str
    skim_column: str
    gamma_b0: float
    gamma_c0: float
    tlfd_path: Path
    target_od_path: Path | None = None


@dataclass
class TripDistributionConfig:
    """Top-level configuration object. Constructed only via ``from_yaml``.

    Parameters
    ----------
    model_settings : ModelSettings
        Algorithm tuning and output location.
    inputs : Inputs
        Shared input file paths and zone attribute columns.
    runs : list[RunConfig]
        One entry per truck type to calibrate and apply.
    """

    model_settings: ModelSettings
    inputs: Inputs
    runs: list[RunConfig]

    @classmethod
    def from_yaml(cls, path: Path) -> TripDistributionConfig:
        """Load and validate config from a YAML file.

        Performs all validation before returning — if this method succeeds,
        the pipeline can proceed without further config checks:

        1. YAML is parsed and all required fields are present.
        2. ``name`` and ``short_name`` are unique across runs.
        3. All declared file paths exist on disk.
        4. All ``productions_column``, ``attractions_column``, and
           ``geo_agg_cols`` values are columns in the PA parquet (schema
           peek only — no data is loaded).
        5. All ``skim_column`` values are matrix keys in the OMX file
           (lightweight open — no arrays are loaded into memory).

        Parameters
        ----------
        path : Path
            Path to the YAML configuration file.

        Returns
        -------
        TripDistributionConfig
            Fully validated configuration object.

        Raises
        ------
        FileNotFoundError
            If the config file, PA parquet, OMX skim, TLFD CSV, or any
            declared ``target_od_path`` does not exist.
        ValueError
            If any required YAML field is missing, ``name`` or
            ``short_name`` values are duplicated, any ``geo_agg_cols``
            column is absent from the PA parquet, any
            ``productions_column`` or ``attractions_column`` is absent,
            or any ``skim_column`` is not a key in the OMX file.
        """

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as fh:
            raw = yaml.safe_load(fh)

        # ----------------------------------------------------------------
        # model_settings  (all fields are optional — use dataclass defaults)
        # ----------------------------------------------------------------
        ms_raw = raw.get("model_settings") or {}
        b_bounds_raw = ms_raw.get("gamma_b_bounds", [-3.0, -0.01])
        c_bounds_raw = ms_raw.get("gamma_c_bounds", [-0.5, -0.001])

        model_settings = ModelSettings(
            gravity_max_iters=int(ms_raw.get("gravity_max_iters", 99)),
            gravity_max_rmse=float(ms_raw.get("gravity_max_rmse", 10.0)),
            optimizer_method=str(ms_raw.get("optimizer_method", "Nelder-Mead")),
            optimizer_max_iters=int(ms_raw.get("optimizer_max_iters", 500)),
            atl_penalty_weight=float(ms_raw.get("atl_penalty_weight", 0.1)),
            verbosity=str(ms_raw.get("verbosity", "INFO")),
            output_dir=Path(ms_raw.get("output_dir", "outputs/trip_distribution")),
            gamma_b_bounds=(float(b_bounds_raw[0]), float(b_bounds_raw[1])),
            gamma_c_bounds=(float(c_bounds_raw[0]), float(c_bounds_raw[1])),
        )

        # ----------------------------------------------------------------
        # inputs  (pa_path and skim_path are required)
        # ----------------------------------------------------------------
        inp_raw = raw.get("inputs") or {}
        _require_key(inp_raw, "pa_path", section="inputs")
        _require_key(inp_raw, "skim_path", section="inputs")

        geo_agg_cols_raw = inp_raw.get("geo_agg_cols") or []

        inputs = Inputs(
            pa_path=Path(inp_raw["pa_path"]),
            skim_path=Path(inp_raw["skim_path"]),
            geo_agg_cols=list(geo_agg_cols_raw),
        )

        # ----------------------------------------------------------------
        # runs  (at least one required; all fields except target_od_path
        #        are required per run)
        # ----------------------------------------------------------------
        runs_raw = raw.get("runs") or []
        if not runs_raw:
            raise ValueError("Config must contain at least one entry under 'runs'.")

        _RUN_REQUIRED = [
            "name", "short_name",
            "productions_column", "attractions_column",
            "skim_column",
            "gamma_b0", "gamma_c0",
            "tlfd_path",
        ]
        runs: list[RunConfig] = []
        for i, r in enumerate(runs_raw):
            # TODO: Evaluate if _require_key can be used here. Looks duplicated.
            for key in _RUN_REQUIRED:
                if key not in r:
                    raise ValueError(
                        f"runs[{i}] (name={r.get('name', '?')!r}) "
                        f"is missing required field '{key}'."
                    )
            runs.append(
                RunConfig(
                    name=str(r["name"]),
                    short_name=str(r["short_name"]),
                    productions_column=str(r["productions_column"]),
                    attractions_column=str(r["attractions_column"]),
                    skim_column=str(r["skim_column"]),
                    gamma_b0=float(r["gamma_b0"]),
                    gamma_c0=float(r["gamma_c0"]),
                    tlfd_path=Path(r["tlfd_path"]),
                    target_od_path=(
                        Path(r["target_od_path"]) if r.get("target_od_path") else None
                    ),
                )
            )

        # ----------------------------------------------------------------
        # Uniqueness: name and short_name
        # ----------------------------------------------------------------
        _check_unique([r.name for r in runs], field="name")
        _check_unique([r.short_name for r in runs], field="short_name")

        # ----------------------------------------------------------------
        # File existence: pa_path, skim_path, tlfd_paths, target_od_paths
        # ----------------------------------------------------------------
        if not inputs.pa_path.exists():
            raise FileNotFoundError(f"PA parquet not found: {inputs.pa_path}")
        if not inputs.skim_path.exists():
            raise FileNotFoundError(f"OMX skim file not found: {inputs.skim_path}")
        for run in runs:
            if not run.tlfd_path.exists():
                raise FileNotFoundError(
                    f"Run '{run.name}': TLFD file not found: {run.tlfd_path}"
                )
            if run.target_od_path is not None and not run.target_od_path.exists():
                raise FileNotFoundError(
                    f"Run '{run.name}': target_od_path not found: {run.target_od_path}"
                )

        # ----------------------------------------------------------------
        # PA column validation (schema peek — no data loaded)
        # pyarrow.parquet.read_schema reads only file metadata, not row data
        # ----------------------------------------------------------------
        pa_schema = pq.read_schema(inputs.pa_path).names

        missing_geo = [c for c in inputs.geo_agg_cols if c not in pa_schema]
        if missing_geo:
            raise ValueError(
                f"geo_agg_cols not found in PA parquet: {missing_geo}\n"
                f"Available columns: {sorted(pa_schema)}"
            )

        for run in runs:
            missing_pa = [
                col
                for col in (run.productions_column, run.attractions_column)
                if col not in pa_schema
            ]
            if missing_pa:
                raise ValueError(
                    f"Run '{run.name}': column(s) not found in PA parquet: {missing_pa}\n"
                    f"Available columns: {sorted(pa_schema)}"
                )

        # ----------------------------------------------------------------
        # OMX skim key validation (lightweight open — no arrays loaded)
        # ----------------------------------------------------------------
        with omx.open_file(str(inputs.skim_path), "r") as f:
            available_skims = list(f.list_matrices())

        for run in runs:
            if run.skim_column not in available_skims:
                raise ValueError(
                    f"Run '{run.name}': skim_column '{run.skim_column}' "
                    f"not found in OMX file.\n"
                    f"Available matrices: {available_skims}"
                )

        return cls(model_settings=model_settings, inputs=inputs, runs=runs)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _require_key(d: dict, key: str, section: str) -> None:
    """Raise ValueError if ``key`` is absent from ``d``."""
    if key not in d:
        raise ValueError(f"Config section '{section}' is missing required field '{key}'.")


def _check_unique(values: list[str], field: str) -> None:
    """Raise ValueError if any value appears more than once."""
    seen: set[str] = set()
    dupes: list[str] = []
    for v in values:
        if v in seen:
            dupes.append(v)
        seen.add(v)
    if dupes:
        raise ValueError(
            f"Run '{field}' values must be unique across all runs. "
            f"Duplicates found: {sorted(set(dupes))}"
        )
