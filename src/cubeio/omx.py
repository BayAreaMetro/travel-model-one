"""Generic Cube TPP <-> OMX matrix converters.

Bidirectional bridge between Cube TPP files and a single OMX file, renaming
tables according to a caller-supplied mapping.  Knows nothing about TM1 naming
conventions — the mapping is purely data-driven.
"""

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio.tpp_read import read_tpp
from cubeio.tpp_write import write_tpp

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

log = logging.getLogger(__name__)


def tpp_to_omx(
    file_map: dict[Path, dict[str, str]],
    output: Path,
    *,
    dtype: np.dtype = np.float32,
) -> int:
    """Convert one or more Cube TPP files to a single OMX file.

    Parameters
    ----------
    file_map
        ``{tpp_path: {cube_table_name: omx_key}}``.
        Each TPP is read once; only tables listed in the inner dict are written.
        Missing TPP files or missing tables within a TPP are silently skipped.
    output
        Path for the output OMX file (overwritten if it exists).
    dtype
        NumPy dtype for the output matrices (default float32).

    Returns:
    -------
    int
        Number of matrices written.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    zones: int | None = None
    count = 0
    seen: set[str] = set()

    with omx.open_file(str(output), "w") as f:
        items = file_map.items()
        if tqdm is not None:
            items = tqdm(list(items), desc="TPP → OMX", unit="file")

        for tpp_path_str, table_map in items:
            tpp_path = Path(tpp_path_str)
            if not tpp_path.exists():
                log.warning("%s not found, skipping", tpp_path)
                continue

            if tqdm is not None and hasattr(items, "set_postfix_str"):
                items.set_postfix_str(tpp_path.name)

            result = read_tpp(tpp_path)

            if zones is None:
                zones = result["zones"]
                f.create_mapping("zone", np.arange(1, zones + 1))

            for cube_name, omx_key in table_map.items():
                if cube_name not in result["data"]:
                    continue
                if omx_key in seen:
                    log.warning("duplicate key %s, skipping", omx_key)
                    continue
                seen.add(omx_key)
                f[omx_key] = result["data"][cube_name].astype(dtype)
                count += 1
                log.debug("  %s/%s -> %s", tpp_path.name, cube_name, omx_key)

    log.info("Wrote %d matrices (%s zones) to %s", count, zones, output)
    return count


def omx_to_tpp(
    omx_path: Path,
    file_map: dict[Path, dict[str, str]],
    *,
    zones: int | None = None,
) -> int:
    """Convert OMX matrices to one or more Cube TPP files (inverse of ``tpp_to_omx``).

    Parameters
    ----------
    omx_path
        Source OMX file.
    file_map
        ``{tpp_path: {omx_key: cube_table_name}}``.  One entry per output TPP;
        each inner dict maps OMX matrix keys to the Cube table names to write
        into that file.  Missing OMX keys are skipped with a warning.
    zones
        Zone count; inferred from the first matrix's shape if omitted.

    Returns:
    -------
    int
        Number of TPP files written.
    """
    written = 0

    with omx.open_file(str(omx_path), "r") as f:
        available = set(f.list_matrices())
        items = file_map.items()
        if tqdm is not None:
            items = tqdm(list(items), desc="OMX → TPP", unit="file")

        for tpp_path, table_map in items:
            if tqdm is not None and hasattr(items, "set_postfix_str"):
                items.set_postfix_str(Path(tpp_path).name)

            data: dict[str, np.ndarray] = {}
            for omx_key, cube_name in table_map.items():
                if omx_key not in available:
                    log.warning("OMX key %s not found, skipping", omx_key)
                    continue
                data[cube_name] = np.asarray(f[omx_key])

            if not data:
                log.warning("No matrices found for %s, skipping", tpp_path)
                continue

            write_tpp(Path(tpp_path), data, zones=zones)
            written += 1
            log.debug("Wrote %s (%d tables)", tpp_path, len(data))

    log.info("Wrote %d TPP file(s) from %s", written, omx_path)
    return written
