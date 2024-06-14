This folder hosts scripts for Round 2 of the Next Generation Freeways Study project.

# Round 2 Metrics

Also known as NGFS (Next Generation Freeways Study) metrics, this directoy consists of a set of scripts to calculate various [metrics](#metrics) for a set of model runs (pathways/scenarios).


Most of the files are run at the end of a model run via [run_NGF_Tableau_scripts.bat](../run_NGF_Tableau_scripts.bat)

Most of this is written to check the existence of files and run things only if things
don't exist, so to force everything to run, clear out the relevant folder (L:\Application\Model_One\NextGenFwys_Round2\Metrics).

## Table of Contents
  * [Metrics](#metrics)
  * [New ModelRuns Sets](#new-modelruns-sets)
  * [run_NGF_Tableau_scripts.bat](#run_ngf_tableau_scriptsbat)
  * [Metrics Scripts](#metrics-scripts)
    * [post_run_model_steps.py](#post_run_model_stepspy)
    * [copyFilesAcrossScenarios.py](#copyfilesacrossscenariospy)


## Metrics
calculates metrics to evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
* Metrics are:
    1) Affordable 1: Transportation costs as a share of household income
    2) Affordable 2: Ratio of value of auto travel time savings to incremental toll costs
    3) Efficient 1: Ratio of travel time by transit vs. auto between  representative origin-destination pairs
    4) Efficient 2: Transit, walk and bike mode share of commute trips during peak hours
    5) Reliable 1: Change in peak hour travel time on key freeway corridors and parallel arterials
    6) Reliable 2: Ratio of travel time during peak hours vs. non-peak hours between representative origin-destination pairs 
    7) Reparative 1: Absolute dollar amount of new revenues generated that is reinvested in freeway adjacent communities
    8) Reparative 2: Ratio of new revenues paid for by low-income populations to revenues reinvested toward low-income populations
    9) Safe 1: Annual number of estimated fatalities on freeways and non-freeway facilities
    10) Safe 2: Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

## New ModelRuns Sets
* When [ModelRuns_Round2.xlsx](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/ModelRuns_Round2.xlsx) is updated, do the following:
    * Using a modeling machine with run [run_NGF_Tableau_scripts.bat](../run_NGF_Tableau_scripts.bat) from L:\Application\Model_One\NextGenFwys_Round2\Metrics

### run_NGF_Tableau_scripts.bat

This batch script runs the metric scripts needed to update the metrics tableau for the NextGenFwys study.
This file takes an optional environment variable SKIP, meant to check the existence of files and run things only if things don't exist. 
By default SKIP is set to True. 

It then goes through each scenario and calls all the [Metrics Scripts](#metrics-scripts)

## Metrics Scripts
the following scripts calculate the various [Metrics](#metrics) used to evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
* Metrics Scripts are:
    * [post_run_model_steps.py](#post_run_model_stepspy): before running the scripts below, this script is run to generate necessary inputs such as network_links.DBF and network_links_TAZ.csv for all "current" model runs 
    1) Affordable1_transportation_costs.py: calculates Affordable 1
    2) Affordable2_ratio_time_cost.py: calculates Affordable 2
    3) Efficient1_ratio_travel_time.py: calculates Efficient 1
    4) Efficient2_commute_tours_mode_share.py: calculates Efficient 2
    5) Efficient2b_non_commute_trips_mode_share.py: calculates Efficient 2b
    6) Reliable1_change_travel_time.py: calculates Reliable 1
    7) Reliable2_ratio_peak_nonpeak.py: calculates Reliable 2
    8) Safe1_run_fatalities_Rscript.py: calculates Safe 1
    9) Safe2_vmt_from_auto_times.py: calculates Safe 2
    10) Safe2_vmt_from_loaded_network.py: calculates Safe 2
    11) Top_level_metrics_toll_revenues.py: calculates the toll revenue
    * [copyFilesAcrossScenarios.py](#copyfilesacrossscenariospy): run at the end to update the Round 2 across_runs_union folder

### post_run_model_steps.py

### copyFilesAcrossScenarios.py

This copies required files from the variously specified input directories to a single place.