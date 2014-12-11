# Metrics

Also known as COBRA metrics, this directoy consists of a set of scripts to calculate intermediate results
for cost/benefit ratio analysis.

Most of the files are run at the end of a model run via [RunMetrics.bat](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/RunMetrics.bat)

## Inputs & Configuration

In addition to reading model output (of course), metrics require a few additional inputs
in `INPUT\metrics`:

  * `BC_config.csv` has scenario specifics (Project ID, Project Name, County, Project Type,
    Project Mode, Costs, Life of Project, and optional baseline directory for comparison)
  * `collisionLookup.csv` maps roadways (indexed by area type, facility type and number of
    lanes) to different rates of fatality, injury or property damage
  * `emissionsLookup.csv` maps VMT (by period, vehicle class and speed) to emissions rates
  * `nodes.xls` is a node lookup for quickboards, mapping node numbers to human-readable names
  * `nonRecurringDelayLookup.csv` maps V/C ratios to delay depending on the number of lanes
  * `Transit Operator LSR VMT Estimates.xlsx` maps transit operator codes to estimates of
    the share of their VMT on local streets & roads (vs highways), as well as
    how that local VMT is distributed by county

## Output

Intermediate COBRA metrics output can be found in the subdir `metrics` for the model run.
Detailed metrics for the scenario will be summarized in `metrics\BC_[project_id].xlsx`.
This will include metrics for this run and optionally compare those metrics to a base in
order to compute costs and benefits.

Additionally, a (slightly user-unfriendly) text version of these outputs will be written to
`..\all_project_metrics\[project_id].csv`.  The idea here is that a number of scenarios can
be summarized into this directory, and then all of those results can get rolled up into a
single set of files, `..\all_project_metrics\AllProjects_[Data,Desc].csv` by
[rollupAllProjects.py](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/rollupAllProjects.py)

This can be viewed in Tableau using [Cobra Tableau.twb](https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/metrics/Cobra%20Tableau.twb)

