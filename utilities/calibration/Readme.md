
## Contents

* `workbook_templates`: Contains sumodel calibration workbook templates.  These include calibration targets and observed data for 2015.
* `00_submodel.R`: summarizes model core output (plus some inputs) to create model summaries and pastes those into calibration workbooks
* `updateUEC.R`: used to copy new constants from calibration workbooks into model UECs

### Process

Periodically run full model run to get skims, etc.  For these, `CALIB_ITER=0`.
Note that subsequent calibration iterations are just the model core; increment `CALIB_ITER` for these.

Then use `copy_output.bat` to do the following:

* exports skims to csvs (if `CALIB_ITER=0`)
* copies model core outputs from `%MODEL_DIR%` into `%TARGET_DIR%`
* runs the sumodel R scripts which summarize those outputs into csvs and pastes those into the calibration workbook templates, creating an iteration of the calibration workbook

The modeler then:

* inspects the calibration workbook and makes changes to dampening factors, etc.
* breaks the links to other workbooks and saves as a calibration workbook iteration
* runs `updateUEC.R` to update actual UEC with new constants (if changes are desired)
* on model machine, run `calibrateModel.bat` to run just model core
* go back to `copy_output.bat` with incremented `CALIB_ITER`