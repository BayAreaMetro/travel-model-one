
# Validation

This directory contains scripts an utilities for validation TM1.  There are a few types of validation:

## Roadway Validation - PeMS

PeMS data is collected/processed via scripts in https://github.com/BayAreaMetro/pems-typical-weekday, and resulting PeMS data is saved to https://mtcdrive.box.com/v/pems-typical-weekday. 


1. [crosswalk_pems_to_TM.R](crosswalk_pems_to_TM.R) - this script creates a crosswalk between PeMS locations and the model network links. 2015 and 2023 are both supported and passed as arguments to the script.

2. [RoadwayValidation.py](RoadwayValidation.py) - this script combines model data with PeMS data via the crosswalk, and creates a long-form and wide-form of the merged data for Tableau.

By convention, for base years, model validation is done in `[M_drive_model_dir]\OUTPUT\validations\pems`, so that is where [RoadwayValidation.py](RoadwayValidation.py) should be run.

3. [Roadways_PeMS_2015.twb](Roadways_PeMS_2015.twb) - this Tableau visualizes the results from the previous steps.  It also consumes [pems_screenline_stations.csv](pems_screenline_stations.csv) to create visualize a Screenline dashboard.
   1. Copy this tableau into `[M_drive_model_dir]\OUTPUT\validations\pems`.
   2. Rename the tableau to include the model directory since it's important to know which model run to which this tableau refers; e.g. `Roadways_PeMS_[model_dir].twb`
   3. Open the tableau file in a text editor and replace the existing model directory embedded in the file with the model directory in question.
   4. To use for 2023, additionally search/replace the following:
      * 2014 -> 2022
      * 2015 -> 2023
      * 2016 -> 2024
