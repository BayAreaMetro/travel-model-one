
# ITHIM Inputs

This directory contains scripts to create inputs for ITHIM (Integrated Transport and Health Impacts
Model) for California.  They work as follows:

* [RunITHIMMetrics.bat](RunITHIMMetrics.bat)
  * *What:* Batch process that runs all the scripts described below.  Doesn't rerun a script if the output already exists.
  * See this file for input and output files, which are described in comments.
* [SkimsDatabaseITHIM.job](SkimsDatabaseITHIM.job)
  * *What:* Reads model transit skim files and outputs the distances and time components for each origin/destination/mode that
    are walk, drive, bus or rail.
* [PerCapitaDailyTravelDistanceTime.py](PerCapitaDailyTravelDistanceTime.py)
  * *What:* Reads resident trips and summarizes their *Per Capita Mean Daily Travel Time* (item 1),
    *Per Capita Mean Daily Travel Distance* (item 3) and *Population Forecasts (ABM)* (item 18).
    The per capita mean dailyt travel times and distances are split by mode (walk, bike, rail, bus,
    auto driver and auto passenger) and the total population is used as the denominator.
  * *Notes:* This script uses the updated_output of [CoreSummaries.R](../../../model-files/scripts/core_summaries/CoreSummaries.R) and the
    output of [SkimsDatabaseITHIM.job](SkimsDatabaseITHIM.job).  Walk and drive times include walk segments that are a part of transit trips.
* [DistanceTraveledByFacilityType_auto.py](DistanceTraveledByFacilityType_auto.py)
  * *What:* Summarizes the loaded network by facility type categories, for autos and trucks.  Splits auto person miles to drivers and passengers.
  * *Notes:* Since these numbers come from the network, non-resident trips such as internal/external trips and airport trips are included.  Network
    output is produced by [net2csv_ avgload5period.job](../metrics/net2csv_avgload5period.job)
* [DistanceTraveledByFacilityType_transit.py](DistanceTraveledByFacilityType_transit.py)
  * *What:* Summarizes the transit assignment output by joining to the network and summarizing bus miles by facility type.
  * *Notes:* For vehicle travel distances and miles, transit is assumed to run throughout the time period (which may be over-counting for EV).
* [rollupITHIM.py](rollupITHIM.py)
  * *What:* This rolls together the outputs from the other scripts into a single file, and adds columns so that the resulting output is the
    expected format.


* [reformatEmissions.py](reformatEmissions.py)
  * *What:* This was to the emissions output for ITHIM, but it's not currently being used.
