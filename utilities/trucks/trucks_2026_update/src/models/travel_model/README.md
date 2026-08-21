# Travel Model Runner (Truck Validation Harness)

This module is a validation tool for the TM-1.x commercial vehicle models. It runs **one iteration** of the demand → assignment loop (not the usual three-iteration feedback), and only the **commercial vehicle (truck) models** plus the highway assignment. Everything else in the travel model is left untouched.

It works by starting from the outputs of a **completed full model run**: because skims and the CT-RAMP core (auto/person demand) already exist in that run, this tool can restart the model at any point in the truck pipeline, swap in experimental script/data files, re-run just the truck demand and the highway assignment, and compare the loaded network against observed counts. This makes it fast to iterate on a single change (a new trip-generation spec, distance-based friction factors, special generators, …) without re-running the entire model.

Each scenario's assignment results are written to a **separate iteration folder** (`hwy/iter<ITER>`, where `ITER` defaults to `TEST`) so they never overwrite the base run's `iter1` / `iter2` / `iter3` outputs.

> **Note:** Running this tool requires **Windows + Cube/Voyager**.

## How It Works

For each scenario in the config, [`pipeline.py`](pipeline.py) runs:

1. **Extract** the base zip into `output_root/<scenario name>/` (a wrapper folder, if any, is stripped).
2. **Apply replacements** — copy each configured source file over its destination in the extracted run (see [Experiments](#experiments)). Sources may be local paths or GitHub URLs (fetched at run time).
3. **Run `CTRAMP/RunIteration.bat`** with `ITER=TEST`. The batch file's `goto` at the top jumps past skims and CT-RAMP core straight into the truck models, so only the commercial-vehicle sequence and the highway assignment execute. Assigned networks are moved to `hwy/iterTEST`.
4. **Convert** the assignment outputs: `.tpp` matrices → `.omx` and loaded `.net` networks → shapefiles (both via `runtpp`), so the evaluation code can read them.

After all scenarios are attempted, [`run_scenarios.py`](run_scenarios.py) calls [`run_evaluation`](../../evaluation/run_evaluation.py) on the ones that completed, producing the observed-vs-predicted comparison (scatter plots, VMT, Excel workbook, shapefile).

### Restart points

The model can be restarted at different points depending on which `RunIteration*.bat` a scenario swaps in. The `.bat` differs only in where its top-of-file `goto` lands:

| `.bat` variant | Restarts at | Use when the experiment changes… |
|----------------|-------------|----------------------------------|
| `RunIteration.bat` | `:trucks` (truck generation) | only the truck generation/distribution/TOD/toll steps |
| `RunIteration_from_nonres_ixforecast.bat` | `:nonres` (IX forecasts) | the internal/external (IX/XI/XX) demand as well |
| `RunIteration_from_truck_toll_choice.bat` | `:trucks` | truck inputs fed in just before toll choice |
| `RunIteration_special_generators.bat` | `:nonres` + special-generator jobs | special-generator truck demand |

## How to Run

Run as a module from the project root (`utilities/trucks/trucks_2026_update`):

```bash
python -m src.models.travel_model.run_scenarios --config configs/travel_model_scenarios.yaml
```

`--config` defaults to `configs/travel_model_scenarios.yaml`. On start, the runner stamps a timestamped experiment directory (`<out_folder>/<timestamp>_<experiment_name>/`) and writes a `configurations_used.yaml` copy of the resolved config there for reproducibility, then runs every scenario and the evaluation.

## Configuration

The config is one YAML file, validated by the Pydantic models in [`config.py`](config.py) before anything runs (a typo fails immediately). See [`configs/travel_model_scenarios.yaml`](../../../configs/travel_model_scenarios.yaml).

### Top-level keys

| Key | Required | Used by | Description |
|-----|----------|---------|-------------|
| `base_zip` | Yes | runner | Path to the completed full-run zip shared by all scenarios. |
| `output_root` | Yes | runner | Parent folder where each scenario's run folder is created (e.g. `C:/temp/mtc_cube_runs`). |
| `iteration` | Yes | runner | `ITER` value for the run — names the assignment output folder `hwy/iter<ITER>`. Set to `TEST` to keep results separate from the base run's `iter1/2/3`. |
| `scenarios` | Yes | runner | List of scenarios to run, in order (see below). |
| `observed_data` | — | evaluation | Path to the merged observed counts CSV (from `src.data.observed`), used for obs-vs-predicted comparison. |
| `network_crs` | — | evaluation | Projected CRS of the network (e.g. `EPSG:26910`). |
| `evaluation_output` / `out_folder` | — | evaluation | Base folder for evaluation outputs. |
| `experiment_name` | — | runner | Label folded into the timestamped experiment directory name (default `test`). |

### Scenario schema

Each entry in `scenarios`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Scenario name; also the folder created under `output_root`. |
| `replacements` | list | `[]` | Files to swap into the extracted run (see below). Empty = untouched base run. |
| `skip_if_exists` | bool | `false` | If `true` and the scenario folder already exists, skip the extract + `.bat` (the conversions still run). Lets you re-evaluate an existing run without rebuilding it. |
| `base_zip` | str \| null | `null` | Per-scenario override of the shared `base_zip`. |

Each **replacement** is a `{source, destination}` pair:

| Field | Description |
|-------|-------------|
| `source` | Local file path **or** a GitHub URL (auto-detected and downloaded at run time — paste a permalink with a commit hash to pin it). |
| `destination` | Path **relative to the scenario root**. |

## Experiments

The experiments run during the TM-1.7 truck update are captured as scenarios in the config.


| Experiment | Trip Generation | Trip Distribution | Time of Day | IX/XI/XX Demand | Special Generators |
|------------|-----------------|-------------------|-------------|-----------------|--------------------|
| **TM-1.6** |  |  |  |  |  |
| **TM-1.6_FIX_ROUNDING_ISSUE** |  |  |  |  |  |
| **TM-1.6_FIXES** |  |  |  |  |  |
| **TM-1.6_TRK_SW** |  |  |  |  |  |
| **TM-1.7_GEN_REEST** |  |  |  |  |  |
| **TM-1.7_GEN_NEWSPEC** |  |  |  |  |  |
| **TM-1.7_GEN_IX** |  |  |  |  |  |
| **TM-1.7_GEN_IX_NVF** |  |  |  |  |  |
| **TM-1.7_Updates** |  |  |  |  |  |

The CUBE scripts an experiment swaps in (`.bat` restart variants, `.job` model steps, and the friction-factor `.dat`) live in [`TruckTripGeneration_scripts/`](TruckTripGeneration_scripts/). The CUBE→Python output-conversion scripts used in step 4 — `.tpp`→`.omx` and `.net`→shapefile — live in [`cube_scripts/`](cube_scripts/).

## Outputs

#TODO: Reference BOX Link to this outputs 
Per scenario, under `output_root/<name>/`:

- `hwy/iter<ITER>/` — assigned networks for this run (`ITER=TEST` by default), kept separate from the base run's iterations.
- Converted `.omx` matrices and `.shp` networks the evaluation reads.

Per run, under the timestamped experiment directory:

- `configurations_used.yaml` — the exact resolved config, for reproducibility.
- Evaluation outputs (scatter plots, VMT comparison, Excel workbook, validation shapefile).