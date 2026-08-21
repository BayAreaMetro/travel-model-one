# projects

One directory per **project** — a pipeline and the cases that run through it.

```
projects/<project>/
  config.yaml     the full model: every step, in fixed order, with its default values
  cases.yaml      the cases to run, each a set of overrides into config.yaml
  hooks.py        project-local pipeline steps, wired in from config.yaml
  variants/       version-controlled alternate params/ and jobs/ a case can point at
```

A **project** is one pipeline shape. A **case** varies values inside it — inputs,
parameters, which scripts a step runs — but can never add, remove, or reorder steps.
A different pipeline shape is a different project.

`config.yaml` runs as written; it is not a template with blanks to fill. Cases perturb
it. Shared model configuration lives in [`../default-configs/`](../default-configs/).

| Project | Engine | Notes |
|---|---|---|
| `ctramp_2023` | Java CT-RAMP | 2023 base year; RunModel.bat parity |

Run every case in a project, or one by name:

```
tm1 run ctramp_2023
tm1 status ctramp_2023
```
