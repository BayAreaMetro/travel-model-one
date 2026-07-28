# scenarios

One directory per model run. Each holds a `scenario_config.yaml` declaring the pipeline steps
and the machine-specific paths for that run.

A scenario is a **delta**, not a copy of the model: shared configuration lives in
[`../default-configs/`](../default-configs/) and is inherited. Keep scenario directories to
what genuinely differs — networks, land use, population, and the parameters being varied.

| Scenario | Engine | Notes |
|---|---|---|
| `base_2023_ctramp` | Java CT-RAMP | 2023 base year; demand model only, against pre-built skims |

To add one, copy an existing `scenario_config.yaml`, repoint `reference_run` and `proj_dir`,
and run `tm1 run --scenario <name>`.
