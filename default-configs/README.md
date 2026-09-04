# default-configs

Shared model configuration: pipeline shape, specs, coefficient tables, lookup tables and
default assets that every project inherits from. Projects in [`../projects/`](../projects/)
hold only their *deltas* against what lives here.

**No data files.** Inputs (networks, land use, populations, skims) are fetched or referenced
from outside the repo. The only acceptable data here is small (<1 MB), slow-changing, and
free of personally identifiable information.

| File / directory | Holds | Arrives in |
|---|---|---|
| `ctramp-cube-model.yaml` | The CT-RAMP+Cube pipeline every project shares -- steps, job paths, the whole `warmstart:`/`iterate:` shape. Each scenario in a project's `scenarios.yaml` overrides the handful of addresses that make it a project (data sources, forecast year) directly, through the same address grammar. See [`../docs/running-a-model.md`](../docs/running-a-model.md). | phase 1 |
| `activity/` | ActivitySim configs — specs, coefficients, YAML settings | phase 4 |
| `population/` | PopulationSim configs — controls, crosswalks, seed encoding | phase 4 |
| `assignment/` | Assignment policy constants (occupancy, ride-hail shares, VDF params) | phase 5 |

`activity/`, `population/` and `assignment/` are scaffolded and intentionally empty — the
structure is settled now so that later phases drop files into agreed locations rather than
proposing a layout and a 100-file diff at the same time. See
[`../MIGRATION_NOTES.md`](../MIGRATION_NOTES.md).

