# default-configs/assignment

Assignment policy constants — vehicle occupancy factors, ride-hail shares and deadhead
factors, volume-delay function parameters, transit path-building limits.

Policy constants live here, never hard-coded in `src/`, so a value can be traced to a
documented source and changed without touching code.

Empty until **phase 5** (assignment backend). Assignment currently runs from the legacy Cube
`.job` scripts, which carry their own parameters.

See [`../../MIGRATION_NOTES.md`](../../MIGRATION_NOTES.md).
