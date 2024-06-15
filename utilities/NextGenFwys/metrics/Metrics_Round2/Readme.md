This folder hosts scripts for Round 2 of the Next Generation Freeways Study project.

# Round 2 Metrics

Also known as NGFS (Next Generation Freeways Study) metrics, this directoy consists of a set of scripts to calculate various [metrics](#metrics) for a set of model runs (pathways/scenarios).


Most of the files are run at the end of a model run via [run_NGF_Tableau_scripts.bat](../Metrics_Round2/run_NGF_Tableau_scripts.bat)

Most of this is written to check the existence of files and run things only if things
don't exist, so to force everything to run, clear out the relevant folder (L:\Application\Model_One\NextGenFwys_Round2\Metrics).

## Table of Contents
  * [Metrics](#metrics)
  * [New ModelRuns Sets](#new-modelruns-sets)
  * [run_NGF_Tableau_scripts.bat](#run_ngf_tableau_scriptsbat)
  * [Metrics Scripts](#metrics-scripts)
    * [post_run_model_steps.py](#post_run_model_stepspy)
    * [copyFilesAcrossScenarios.py](#copyfilesacrossscenariospy)
    * [post_run_model_steps.py](#post_run_model_stepspy)
    * [Affordable1_transportation_costs.py](#affordable1_transportation_costspy)
    * [Affordable2_ratio_time_cost.py](#affordable2_ratio_time_costpy)
    * [Efficient1_ratio_travel_time.py](#efficient1_ratio_travel_timepy)
    * [Efficient2_commute_tours_mode_share.py](#efficient2_commute_tours_mode_sharepy)
    * [Efficient2b_non_commute_trips_mode_share.py](#efficient2b_non_commute_trips_mode_sharepy)
    * [Reliable1_change_travel_time.py](#reliable1_change_travel_timepy)
    * [Reliable2_ratio_peak_nonpeak.py](#reliable2_ratio_peak_nonpeakpy)
    * [Safe1_run_fatalities_Rscript.py](#safe1_run_fatalities_rscriptpy)
    * [Safe2_vmt_from_auto_times.py](#safe2_vmt_from_auto_timespy)
    * [Safe2_vmt_from_loaded_network.py](#safe2_vmt_from_loaded_networkpy)
    * [Top_level_metrics_toll_revenues.py](#top_level_metrics_toll_revenuespy)
    * [copyFilesAcrossScenarios.py](#copyfilesacrossscenariospy)


## Metrics
Calculates metrics to evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
Metrics are:
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
When [ModelRuns_Round2.xlsx](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/ModelRuns_Round2.xlsx) is updated, do the following:
  * Using a machine with ArcGIS Pro, NetworkWrangler and geopandas installed, run [run_NGF_Tableau_scripts.bat](../Metrics_Round2/run_NGF_Tableau_scripts.bat) from L:\Application\Model_One\NextGenFwys_Round2\Metrics

### [run_NGF_Tableau_scripts.bat](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/run_NGF_Tableau_scripts.bat)

This batch script runs the metric scripts needed to update the metrics tableau for the NextGenFwys study.
This file takes an optional environment variable SKIP, meant to check the existence of files and run things only if things don't exist. 
By default SKIP is set to True. 
set SKIP=n to recalculate all metrics

It then goes through each scenario and calls all the [Metrics Scripts](#metrics-scripts)

## Metrics Scripts
The following scripts calculate the various [Metrics](#metrics) used to evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
Metrics Scripts are:
  * [post_run_model_steps.py](#post_run_model_stepspy): before running the scripts below, this script is run to generate necessary inputs such as network_links.DBF and network_links_TAZ.csv for all "current" model runs 
  1) [Affordable1_transportation_costs.py](#affordable1_transportation_costspy): calculates Affordable 1
  2) [Affordable2_ratio_time_cost.py](#affordable2_ratio_time_costpy): calculates Affordable 2
  3) [Efficient1_ratio_travel_time.py](#efficient1_ratio_travel_timepy): calculates Efficient 1
  4) [Efficient2_commute_tours_mode_share.py](#efficient2_commute_tours_mode_sharepy): calculates Efficient 2
  5) [Efficient2b_non_commute_trips_mode_share.py](#efficient2b_non_commute_trips_mode_sharepy): calculates Efficient 2b
  6) [Reliable1_change_travel_time.py](#reliable1_change_travel_timepy): calculates Reliable 1
  7) [Reliable2_ratio_peak_nonpeak.py](#reliable2_ratio_peak_nonpeakpy): calculates Reliable 2
  8) [Safe1_run_fatalities_Rscript.py](#safe1_run_fatalities_rscriptpy): calculates Safe 1
  9) [Safe2_vmt_from_auto_times.py](#safe2_vmt_from_auto_timespy): calculates Safe 2
  10) [Safe2_vmt_from_loaded_network.py](#safe2_vmt_from_loaded_networkpy): calculates Safe 2
  11) [Top_level_metrics_toll_revenues.py](#top_level_metrics_toll_revenuespy): calculates the toll revenue
  * [copyFilesAcrossScenarios.py](#copyfilesacrossscenariospy): run at the end to update the Round 2 across_runs_union folder

### [post_run_model_steps.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/post_run_model_steps.py)
accomplishes the following tasks:
* Shapefiles output
    * Runs the run_CubeToShapefile.bat batch file to generate the shapefiles outputs from each completed model run directory's OUTPUT\\shapefile directory. 
    * The batch file needs to be run from a machine with ArcGIS Pro, NetworkWrangler and geopandas installed. satmodel is recommended
* metrics\\vmt_vht_metrics_by_taz.csv
    * Steps:
        * Shapefiles output from above are required
        * Correspond links to taz by running (in the shapefile directory):  python X:\\travel-model-one-master\\utilities\\cube-to-shapefile\\correspond_link_to_TAZ.py network_links.shp network_links_TAZ.csv
        * Rerun hwynet.py in the model run directory on the modeling machine: python X:\\travel-model-one-master\\utilities\\RTP\\metrics\\hwynet.py --filter PBA50 --year 2035 --link_mapping L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\[Scenario]\\OUTPUT\\shapefile\\network_links_TAZ.csv TAZ1454 linktaz_share _by_taz .\\hwy\\iter3\\avgload5period_vehclasses.csv
        * Copy resulting vmt_vht_metrics_by_taz.csv to L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\[Scenario]\OUTPUT\metrics
        * run copyFilesAcrossScenarios.py again to copy the files to the across_runs_union directory (see detailed steps under Step 1 of "across_NGFS_runs_union tableau")        

### [Affordable1_transportation_costs.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Affordable1_transportation_costs.py)
Input Files:
  * travel-cost-hhldtraveltype.csv: transportation costs summarized by income, home_taz, hhld_travel type
  
This file has the following columns:
  * 'metric_desc',
  * 'value',
  * 'income levels',
  * 'modes',
  * 'intermediate/final',
  * 'modelrun_id',
  * 'year',
  * 'metric_id',
  * 'value type',
  * 'Households, Income, Autos, Trips, Costs'

### [Affordable2_ratio_time_cost.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Affordable2_ratio_time_cost.py)
Input Files:
  * taz_with_cities.csv: Lookup table linking Traffic Analysis Zones (TAZ) to groups of named cities for geographic analysis.
  * taz_with_origins.csv: Lookup table that contain TAZs for trips originating within and outside of the cordons and headed to the cordons, for geographic analysis.
  * taz_with_cordons.csv: Lookup table indicating cordon designations for Traffic Analysis Zones (TAZ), for geographic analysis.
  * ODTravelTime_byModeTimeperiodIncome.csv: OD travel time summarized by mode, time period and income group
  * network_links.DBF: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * avgload5period.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.

This file will have the following columns:
  * 'Corridor',
  * 'Value Type',
  * 'Income Group/Occupation',
  * 'modelrun_id',
  * 'metric_id',
  * 'intermediate/final',
  * 'Household/Commercial',
  * 'metric_desc',
  * 'year',
  * 'value'

### [Efficient1_ratio_travel_time.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Efficient1_ratio_travel_time.py)
Input Files:
  * taz_with_cities.csv: Lookup table linking Traffic Analysis Zones (TAZ) to groups of named cities for geographic analysis.
  * ODTravelTime_byModeTimeperiodIncome.csv: OD travel time summarized by mode, time period and income group
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.
  * taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.

This file will have the following columns:
  * 'metric_desc',
  * 'value',
  * 'intermediate/final',
  * 'Origin and Destination',
  * 'modelrun_id',
  * 'year',
  * 'metric_id'

### [Efficient2_commute_tours_mode_share.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Efficient2_commute_tours_mode_share.py)
Input Files:
  * JourneyToWork_modes.csv: JourneyToWork summary with SD, subzone, and commute mode

This file will have the following columns:
  * 'commute mode',
  * 'value',
  * 'metric_desc'
  * 'shares',
  * 'commute_non',
  * 'Aggregate Tour Mode',
  * 'Model Run ID',
  * 'Metric ID',
  * 'Year'

### [Efficient2b_non_commute_trips_mode_share.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Efficient2b_non_commute_trips_mode_share.py)
Inputs:
  * TripDistance.csv: Trip Distance Summary

This file will have the following columns:
  * 'commute mode',
  * 'commute_non',
  * 'peak_non',
  * 'trip_mode',
  * 'timeCode',
  * 'value',
  * 'intermediate/final',
  * 'metric_desc',
  * 'shares',
  * 'Model Run ID',
  * 'Metric IC',
  * 'Year'
  
### [Reliable1_change_travel_time.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Reliable1_change_travel_time.py)
Inputs:
  * taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * ParallelArterialLinks.csv: Lookup file indicating parallel arterial designation for Roadway network, used for classification.
  * network_links_TAZ.csv: Lookup table linking network links to Traffic Analysis Zones (TAZ) for geographic analysis.
  * goods_routes_a_b.csv: Lookup file indicating goods routes designation for Roadway network, used for classification.

This file will have the following columns:
  * 'grouping',
  * 'congested/other',
  * 'Metric Description',
  * 'value',
  * 'Road Type',
  * 'Model Run ID',
  * 'Metric ID',
  * 'Intermediate/Final',
  * 'Year',
  * 'taz_epc'
  
### [Reliable2_ratio_peak_nonpeak.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Reliable2_ratio_peak_nonpeak.py)
Inputs:
  * taz_with_cities.csv: Lookup table linking Traffic Analysis Zones (TAZ) to groups of named cities for geographic analysis.
  * taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
  * TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.
  * ODTravelTime_byModeTimeperiodIncome.csv: OD travel time summarized by mode, time period and income group
  * goods_routes_a_b.csv: Lookup file indicating goods routes designation for Roadway network, used for classification.
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.

This file will have the following columns:
  * 'metric_desc',
  * 'value',
  * 'intermediate/final',
  * 'Origin and Destination',
  * 'modelrun_id',
  * 'year',
  * 'metric_id',
  * 'Goods Routes Y/N',
  * 'Peak/Non',
  * 'N/A',
  * 'Route'
  
### [Safe1_run_fatalities_Rscript.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Safe1_run_fatalities_Rscript.py)
runs [VZ_safety_calc_correction_v2.R](https://github.com/BayAreaMetro/travel-model-one/blob/5ceeb9d638680b93432177793cd0ec25d6cef93c/utilities/RTP/metrics/VZ_safety_calc_correction_v2.R) and copies output to L:\\Application\\Model_One\\NextGenFwys_Round2\\Metrics     

### [Safe2_vmt_from_auto_times.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Safe2_vmt_from_auto_times.py)
Inputs:
  * auto_times.csv: Daily Person Trips, Daily Vehicle Trips, PersonTime, VehicleTime, PersonMiles, VehicleMiles, TotalCost, Bridge Tolls, Value Tolls

This file will have the following columns:
  * 'Household/Non-Household',
  * 'Income Level/Travel Mode',
  * 'Metric Description',
  * 'value',
  * 'Model Run ID',
  * 'Metric ID',
  * 'Intermediate/Final', 
  * 'Year'
  
### [Safe2_vmt_from_loaded_network.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Safe2_vmt_from_loaded_network.py)
Inputs:
  * taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
  * avgload5period.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * network_links_TAZ.csv: Lookup table linking network links to Traffic Analysis Zones (TAZ) for geographic analysis.
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.

This file will have the following columns:
  * 'Freeway/Non-Freeway',
  * 'Facility Type Definition',
  * 'EPC/Non-EPC',
  * 'Tolled/Non-tolled Facilities',
  * 'County',
  * 'Revenue Facilities',
  * 'grouping',
  * 'grouping_dir',
  * 'tollclass',
  * 'Metric Description',
  * 'value',
  * 'Model Run ID',
  * 'Metric ID',
  * 'Intermediate/Final', 
  * 'Year' 
  
### [Top_level_metrics_toll_revenues.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/metrics/Metrics_Round2/Top_level_metrics_toll_revenues.py)
Input Files:
  * network_links.DBF: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.
  * network_links_TAZ.csv: Lookup table linking network links to Traffic Analysis Zones (TAZ) for geographic analysis.
  * TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.
  * taz_epc_crosswalk.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.

The generated CSV will contain the following columns:
  * 'Freeway/Non-Freeway',
  * 'EPC/Non-EPC',
  * 'Tolled/Non-tolled Facilities',
  * 'Model Run ID',
  * 'Metric ID',
  * 'Intermediate/Final', 
  * 'Facility Type Definition',
  * 'Metric Description',
  * 'County',
  * 'Revenue Facilities',
  * 'Grouping',
  * 'value',
  * 'TOLLCLASS'

### [copyFilesAcrossScenarios.py](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/CoreSummaries/copyFilesAcrossScenarios.py)

This copies required files from the variously specified input directories to a single place.