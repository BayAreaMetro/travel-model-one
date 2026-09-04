# projects

One directory per **project** — a set of data sources and scenarios run through the shared
CT-RAMP+Cube pipeline in [`../default-configs/ctramp-cube-model.yaml`](../default-configs/ctramp-cube-model.yaml).

```
projects/<project>/
  scenarios.yaml  every scenario, self-contained (required) + steps: additions
  hooks.py        project-local pipeline steps, appended via top-level steps:
  variants/       version-controlled alternate params/ and jobs/ a scenario can point at
```

Every project runs the same pipeline shape -- the shared model in
[`../default-configs/ctramp-cube-model.yaml`](../default-configs/ctramp-cube-model.yaml).
A **scenario** varies values inside it — inputs, parameters, which scripts a step runs
— but can never add, remove, or reorder steps. A project's own `steps:` (in
`scenarios.yaml`) is the one way to extend the shared pipeline, and it applies to every
scenario alike.

There is no project-level defaults layer: each scenario in `scenarios.yaml` states its
own full set of overrides through the same address grammar, so it is a *diff* against
the shared pipeline that is readable on its own, without also reading a separate block
to know what it runs. Shared model configuration lives in
[`../default-configs/`](../default-configs/).

| Project | Engine | Notes |
|---|---|---|
| `PBA50+_FBP` | Java CT-RAMP | Plan Bay Area 2050+ Final Blueprint |

Run every scenario in a project, or one by name:

```
tm1 run PBA50+_FBP
tm1 status PBA50+_FBP
```

