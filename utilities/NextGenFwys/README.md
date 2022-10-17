This folder hosts scripts and data for the Next Generation Freeways Study project in addition to an standard TM1.5 application.

## Metrics
Calculates and visualizes metrics to analyze and evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
* TBD

## ModelRuns tracking
Tracks model runs with run set, run category, input data version, etc. Also used to create cross-run comparison visualizations in Tableau.
* [ModelRuns.xlsx](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/ModelRuns.xlsx): color-coded to show different sets of runs. When a run is done that needs to be added to cross-run comparison Tableau, add it to this file.
* [ModelRuns.csv](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/ModelRuns.csv): used by [`summarizeAcrossScenariosUnion.bat`](X:\travel-model-one-master\utilities\CoreSummaries\summarizeAcrossScenariosUnion.bat). When `ModelRuns.xlsx` is updated, do the following:
    * "save as .csv" to update this file
    * open in a text editor, and replace `"""` with `"` to reverse the reformating of quotation marks by .xlsx
    * copy it into `L:\Application\Model_One\NextGenFwys\across_runs_union` to update the older version
    



