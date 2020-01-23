
## workbook_templates

Contains sumodel calibration workbook templates.  These include calibration targets and observed data for 2015.


The `copy_output.bat` does the following:

* exports skims to csvs
* copies model core outputs from `%MODEL_DIR%` into `%TARGET_DIR%`
* runs the sumodel R scripts which summarize those outputs into csvs and pastes those into the calibration workbook templates, creating an iteration of the calibration workbook

The modeler then:
* inspects the calibration workbook and makes changes to dampening factors, etc.
* breaks the links to other workbooks and saves as a calibration workbook iteration
* run `updateUEC.R` to update actual UEC
* on model machine, run `calibrateModel.bat`