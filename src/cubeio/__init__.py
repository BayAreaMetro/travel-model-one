"""Generic Cube I/O utilities — TPP reader, OMX converter."""

import re
from pathlib import Path


def find_latest_iter(directory, stem, suffix=".tpp"):
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
