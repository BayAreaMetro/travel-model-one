# default-configs

Shared model configuration: specs, coefficient tables, lookup tables and default assets that
every project inherits from. Projects in [`../projects/`](../projects/) hold only their
*deltas* against what lives here.

**No data files.** Inputs (networks, land use, populations, skims) are fetched or referenced
from outside the repo. The only acceptable data here is small (<1 MB), slow-changing, and
free of personally identifiable information.

| Directory | Holds | Arrives in |
|---|---|---|
| `activity/` | ActivitySim configs — specs, coefficients, YAML settings | phase 4 |
| `population/` | PopulationSim configs — controls, crosswalks, seed encoding | phase 4 |
| `assignment/` | Assignment policy constants (occupancy, ride-hail shares, VDF params) | phase 5 |

These directories are scaffolded and intentionally empty — the structure is settled now so
that later phases drop files into agreed locations rather than proposing a layout and a
100-file diff at the same time. See [`../MIGRATION_NOTES.md`](../MIGRATION_NOTES.md).
