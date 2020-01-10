
## workbook_templates

Contains sumodel calibration workbook templates.  These include calibration targets and observed data for 2015.


The `copy_output.bat` does the following:

* exports skims to csvs
* copies model core outputs from `%MODEL_DIR%` into `%TARGET_DIR%`
* runs the sumodel R scripts which summarize those outputs into csvs and pastes those into the calibration workbook templates, creating an iteration of the calibration workbook