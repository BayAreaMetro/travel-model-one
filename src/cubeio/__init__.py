"""Generic Cube Voyager I/O.

Public API:

- :func:`read_tpp`  — TPP matrix file  -> numpy  (:mod:`cubeio.tpp_read`)
- :func:`write_tpp` — numpy            -> TPP    (:mod:`cubeio.tpp_write`)
- :func:`tpp_to_omx` — TPP files       -> one OMX (:mod:`cubeio.omx`)
- :func:`omx_to_tpp` — OMX matrices    -> TPP files (:mod:`cubeio.omx`)
- :func:`find_latest_iter` — resolve ``{stem}.avg.iter{N}.tpp`` skim files

Internal modules import each other by submodule (e.g. ``cubeio.tpp_read``);
external callers should use this package-level API.
"""

import re
from pathlib import Path

from cubeio.omx import omx_to_tpp, tpp_to_omx
from cubeio.tpp_read import read_tpp
from cubeio.tpp_write import write_tpp

__all__ = [
    "find_latest_iter",
    "omx_to_tpp",
    "read_tpp",
    "tpp_to_omx",
    "write_tpp",
]


def find_latest_iter(
    directory: str | Path, stem: str, suffix: str = ".tpp"
) -> Path | None:
    """Find the highest-numbered ``{stem}.avg.iter{N}{suffix}`` file.

    Falls back to ``{stem}{suffix}`` if no iteration files exist.
    Returns *None* if neither pattern matches.
    """
    iters = sorted(
        Path(directory).glob(f"{stem}.avg.iter*{suffix}"),
        key=lambda p: int(re.search(r"iter(\d+)", p.name).group(1)),
    )
    if iters:
        return iters[-1]
    plain = Path(directory) / f"{stem}{suffix}"
    return plain if plain.exists() else None
