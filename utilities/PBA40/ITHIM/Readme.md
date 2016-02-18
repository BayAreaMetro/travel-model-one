
# ITHIM Inputs

This directory contains scripts to create inputs for ITHIM (Integrated Transport and Health Impacts
Model) for California.

From **Table 1** – Key Parameters and Their Definition, Units, Strata and Data Sources
of the *User’s Guide for Metropolitan Transportation Commission and Bay Area Departments of Public Health*, Version: *DRAFT 5/27/2014*

No. |  Item Definition                                    | Units           | Strata                        | Source
----|-----------------------------------------------------|-----------------|-------------------------------|-----------------------------------------------
1   | Per capita mean daily travel distance               | Miles/person/d  | Age and sex<sup>#</sup> by mode<sup>&#8224;</sup> | NHTS20099 (walk, bike) or Travel Demand model
2   | Per capita mean daily travel time                   | Min/person/d    | Travel mode                   | NHTS2009 or Travel Demand model
10  | Personal travel distance by facility type           | mi/d            | Travel mode and facility type | Travel Model
11  | Vehicle distance traveled (VMT) by facility type    | mi/d            | Travel mode and facility      | Travel Model
14  | Emissions of primary and secondary sources of PM2.5 | tons/d          | PM<sub>2.5</sub>, tire wear, brake wear, NO<sub>x</sub>, SO<sub>2</sub>, ROG | EMFAC2011


<sup>#</sup> 8 age groups (0-4, 5-14, 15-29, 30-44, 45-59, 60-69, 70-79, 80+) by 2 gender (M,F) = 16 strata

<sup>&#8224;</sup> Mode: car-driver, car-passenger, motorcycle, truck, bus, rail, walk, bicycle

[RunITHIMMetrics.bat](RunITHIMMetrics.bat) will produce these items as follows, rolling them up into *metrics\ITHIM\results.csv*

No(s).| Item Definition  | Output File | Notes | Scripts
------|------------------|-------------|-------|---------
1 & 2 | Per capita mean daily travel distance & time | *metrics\ITHIM\ percapita_daily_ dist_time.csv* | Includes **car_driver, car_passenger, bus, rail, walk and bike modes**. <br>Walk and bike modes are also broken by age group and gender. <br>Since these numbers come from simulated persons and households, non-resident trips such as internal/external trips and airport trips aren't included. Walk mode includes walk segments from walk-to-transit, and car-driver includes drive segments from drive-to-transit.  Bus mode includes bus segments from all transit trips regardless of the primary mode and ditto for rail mode.  The denominators (population) are counts of all popsyn persons in the age_group/gender category (if there is one), regardless of whether they travel or by what mode. The denominators are also included in the output as population forecasts. | Created by [PerCapita DailyTravelDistance Time.R](PerCapitaDailyTravelDistanceTime.R); this script uses the updated_output of [CoreSummaries.R](../../../model-files/scripts/core_summaries/CoreSummaries.R) along with ITHIM skims from [SkimsDatabaseITHIM.job](SkimsDatabaseITHIM.job).
10 & 11 | Personal & Vehicle travel distance by facility type | *metrics\ITHIM\ Distance TraveledBy FacilityType_ auto+truck.csv* | Includes **auto and trucks**. <br>Personal categories are car_driver, car_passenger, truck_driver.  Vehicle categories are car and truck by ITHIM facility type (arterial, freeway and local). <br>Since these numbers come from the network, non-resident trips such as internal/external trips and airport trips are included.| Producted by [net2csv_ avgload5period.job](../metrics/net2csv_avgload5period.job) to convert the network to CSV, and [Distance TraveledBy FacilityType_ auto.py](DistanceTraveledByFacilityType_auto.py).
10 & 11 | Personal & Vehicle travel distance by facility type | *metrics\ITHIM\ Distance TraveledBy FacilityType_ transit.csv* | Includes daily **transit** vehicle miles traveled on bus and rail vehicles (where ferries are considered rail). Bus links are joined with roadways to further allocate them to facility types.  For vehicle travel distances and miles, transit is assumed to run throughout the time period (which may be over-counting for EV). | Computed using [DistanceTraveledBy FacilityType_ transit.py](DistanceTraveledByFacilityType_transit.py), which reads transit assignment output line files along with the roadway network for facility type information.

