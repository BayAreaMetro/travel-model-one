# Base 2023 Scenario

Calibration scenario for TM1.7 ActivitySim against the 2023 BATS survey and
the legacy CTRAMP v1.61 reference run.

## Folder Structure

```
base_2023/
├── scenario_config.yaml   # Main scenario definition (steps, paths, datasets)
├── bats_config.yaml       # Survey cleaning/formatting pipeline config
├── configs/               # (optional) ActivitySim config overrides for this scenario
│   └── settings.yaml      # e.g. sample size, shadow pricing, num_processes
└── README.md              # This file
```

## How Config Resolution Works

ActivitySim uses a **config directory chain** — files in earlier directories
override files in later directories (first wins, whole-file replacement):

```
configs chain (highest priority first):
  1. projects/activitysim_2023_frozen_popsim/activitysim/   ← scenario-specific overrides
  2. default-configs/activity/configs_mp/   ← multiprocessing defaults
  3. default-configs/activity/configs/      ← full model specification
```

To override a setting, copy the relevant file from `default-configs/` into
this scenario's `activitysim/` directory and edit it there.

### Example: run a small sample for testing

Create `activitysim/settings.yaml` with only the settings you want to change:

```yaml
inherit_settings: True
households_sample_size: 1000
num_processes: 4
chunk_training_mode: disabled
```

## Quick Start

### Prerequisites

- Python environment with `tm1` package installed (`pip install -e .` from repo root)
- Access to the reference run network share (for input data and skims)
- A local project directory for outputs (set via `run_dir` in scenario_config.yaml)

### Running

```bash
# Full pipeline
tm1 run activitysim_2023_frozen_popsim

# Single step
tm1 run activitysim_2023_frozen_popsim --steps simulate_activitysim

# Or via the convenience script
python scripts/run_model.py
```

### Machine-Specific Configuration

Edit the top of `scenario_config.yaml` to set paths for your machine:

```yaml
ctramp_run: "//MODEL3-C/Model3C-Share/Projects/2023_TM161_IPA_35_testrun"
run_dir: "E:/Tests/base_2023_frozen_popsim"
```

Everything else derives from these two variables.

## Steps

| Step | Description |
|------|-------------|
| `setup.copy_inputs` | Copy input files (land use, households, persons) from reference run |
| `setup.convert_skims` | Convert CUBE .tpp skims to OMX format |
| `prepare_survey` | Clean and format BATS 2023 survey to CTRAMP structure |
| `simulate_activitysim` | Run ActivitySim (iterates with highway assignment when iterations > 0) |
| `summaries` | Generate calibration report comparing survey, ActivitySim, and CTRAMP |
