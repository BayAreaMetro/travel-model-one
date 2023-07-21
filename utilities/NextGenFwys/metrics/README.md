[NGF_Metrics_Union.twb](https://github.com/BayAreaMetro/travel-model-one/blob/5f9f298ff0a50d826167cd5ee0b8abcd928cf7f3/utilities/NextGenFwys/metrics/NGF_Metrics_Union.twb) visualizes data for the Next Generation Freeways Study project.

## Metrics
visualizes metrics to evaluate a variety of pathways/scenarios for Next Generation Freeways policies.
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
* When [ModelRuns.xlsx](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/ModelRuns.xlsx) is updated, do the following:
    * run ngfs_metrics.py from local cloned github repository or from L: drive
        * if running the python script from L:\Application\Model_One\NextGenFwys\metrics
            * may need to run [commute_tours_by_inc_tp.r](https://github.com/BayAreaMetro/travel-model-one/commit/4d324a60200558cbf460369aff5e1840a57fbc04) for runs in new set to create the missing input files for the script (this step will soon be automated)
            * run the python script and pass the github repository directory as an argument
            * open NGF_Metrics_Union.twb and refresh data source
        * if running the python script from local cloned github repository
            * may need to run [commute_tours_by_inc_tp.r](https://github.com/BayAreaMetro/travel-model-one/commit/4d324a60200558cbf460369aff5e1840a57fbc04) for runs in new set to create the missing input files for the script (this step will soon be automated)
            * run the python script
            * copy and paste the new metrics files along with the log file into L:\Application\Model_One\NextGenFwys\metrics
            * open NGF_Metrics_Union.twb and refresh data source

    



