"""Add CT-RAMP walk-to-transit subzone shares to existing ActivitySim land_use files.

One-off patcher for scenario data dirs created before the setup step gained the
``walk_access_buffers`` entry (see scenario_config.yaml).  New setups merge the
shares automatically; this script back-fills already-built ``data/land_use.csv``
files without re-running setup.

Usage:
    python scripts/add_walk_access_shares.py <walkAccessBuffers.float.csv> <land_use.csv> [...]
"""

import sys
from pathlib import Path

from tm1.steps.walk_access_buffers import merge_walk_access_shares

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    buffers = Path(sys.argv[1])
    for target in sys.argv[2:]:
        merge_walk_access_shares(buffers, Path(target))
