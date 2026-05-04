
## Contents

### Framework

* [calibration_framework.py](calibration_framework.py): Base class (`CalibrationBase`) and shared utilities for all Python calibration scripts. Handles configuration loading, logging, Excel workbook setup, and DataFrame writing.
* [calibration_data_models.py](calibration_data_models.py): Pydantic data models and labeled enums (counties, person types, activity patterns, etc.) shared across calibration scripts.
* [calibration_config.yaml](calibration_config.yaml): Configuration for model-run calibration. Specifies paths to model outputs, calibration iteration, workbook templates, and submodel-specific settings. Environment variables `TARGET_DIR`, `CODE_DIR`, `CALIB_ITER`, `ITER`, `MODEL_DIR`, and `WORKBOOK_BASE_PATH` override the corresponding `general` settings in this file.
* [calibration_config_BATS.yaml](calibration_config_BATS.yaml): Alternate configuration for comparing model outputs against BATS survey data. Points submodels at BATS pipeline outputs instead of model run outputs.
* [environment.yml](environment.yml): Conda environment definition (`tm1.7_calibration`). Install with `conda env create -f environment.yml`.

### Submodel Scripts (Python)

Submodels 01, 02, and 04 have been rewritten in Python and use the shared framework above. Each script reads its configuration from `calibration_config.yaml` (or a config file specified via command line), writes CSVs to `OUTPUT_{CALIB_ITER}/calibration/`, and populates the corresponding Excel workbook template.

* [01_usual_work_school_location_TM.py](01_usual_work_school_location_TM.py): Usual work and school location. Supports a `bats_data` mode that reads from BATS pipeline outputs (`MandatoryLocationData.csv`, `PersonData.csv`) instead of model outputs.
* [02_auto_ownership_TM.py](02_auto_ownership_TM.py): Automobile ownership.
* [04_daily_activity_pattern_TM.py](04_daily_activity_pattern_TM.py): Coordinated daily activity pattern. Supports a `bats_data` mode that reads from BATS `PersonData.csv` and uses person weights.

The following submodel scripts are still in R and are not yet active in [copy_output.bat](copy_output.bat):

* [09_nonwork_destination_choice_TM.R](09_nonwork_destination_choice_TM.R)
* [11_tour_mode_choice_TM.R](11_tour_mode_choice_TM.R)
* [15_trip_mode_choice_TM.R](15_trip_mode_choice_TM.R)

### Other Scripts

* [updateUEC.py](updateUEC.py): Copies new constants from calibration workbooks into model UEC (Utility Expression Calculator) files. Run with `python updateUEC.py <submodel> <version>`.
* [calibrateModel.bat](calibrateModel.bat): Runs just the model core (CTRAMP) on the model machine for a calibration iteration.
* [copy_output.bat](copy_output.bat): Copies model core outputs and runs the active Python submodel scripts (see Process below).
* [caltrain_skim_summary.R](caltrain_skim_summary.R), [skim_district_summary.R](skim_district_summary.R): Skim diagnostic summaries (R).
* [Car ownership - AVs vs HVs summary.r](Car%20ownership%20-%20AVs%20vs%20HVs%20summary.r): AV vs. HV auto ownership comparison (R).
* [caltrain_tazs.csv](caltrain_tazs.csv): TAZ list for Caltrain stations.
* `extract_*.job`: Cube scripts to export skims to CSV.
* [TransitSkimVisualizer.twb](TransitSkimVisualizer.twb): Tableau workbook for visualizing transit skims.

### Subdirectories

* [workbook_templates/](workbook_templates/): Blank Excel calibration workbook templates. Includes `_2023` variants for submodels 01 and 02 with 2023 calibration targets.
* [targets/](targets/): R scripts for creating calibration targets from OBS and CHTS observed data.

---

### Process

#### Environment Setup

Create the conda environment (first time only):

```
conda env create -f environment.yml -p E:\conda\envs\tm1.7_calibration
```

Activate the conda environment before running Python scripts:

```
conda activate tm1.7_calibration
```

#### Calibration Iterations

Periodically run a full model run to refresh skims and inputs. Set `CALIB_ITER=00` in `copy_output.bat` for these. Subsequent iterations run only the model core; increment `CALIB_ITER` for each.

Edit the top of [copy_output.bat](copy_output.bat) to set:

* `MODEL_DIR`: model run directory on the model machine
* `TARGET_DIR`: local directory where outputs are collected
* `CODE_DIR`: path to this calibration utilities directory
* `CALIB_ITER`: current calibration iteration number

Then run [copy_output.bat](copy_output.bat), which:

* exports skims to CSVs (if `CALIB_ITER=00`)
* copies model core outputs from `%MODEL_DIR%` into `%TARGET_DIR%`
* runs the active Python submodel scripts, which summarize outputs into CSVs and populate calibration workbook templates

The modeler then:

* inspects the calibration workbook and makes changes to constants/dampening factors
* runs `python updateUEC.py <submodel> <version>` to push new constants into the model UEC files
* on the model machine, runs [calibrateModel.bat](calibrateModel.bat) to run just the model core
* increments `CALIB_ITER` and reruns [copy_output.bat](copy_output.bat)

#### BATS Survey Comparison

To compare model outputs against BATS survey data, use [calibration_config_BATS.yaml](calibration_config_BATS.yaml) instead of the default config. This is configured per-submodel via the `bats_data: true` flag, which redirects input paths to BATS pipeline output files. Scripts supporting BATS mode: [01_usual_work_school_location_TM.py](01_usual_work_school_location_TM.py), [04_daily_activity_pattern_TM.py](04_daily_activity_pattern_TM.py).
