
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

[RunITHIMMetrics.bat](RunITHIMMetrics.bat) will produce these items as follows.

No(s).| Item Definition  | Output File | Notes | Scripts
------|------------------|-------------|-------|---------
1 & 2 | Per capita mean daily travel distance & time | metrics\ ITHIM\ percapita_ daily_ dist_ time.csv | Includes car-driver, car-passenger, bus, rail, walk and bicycle modes only. <br>Since these numbers come from simulated persons and households, non-resident trips such as internal/external trips and airport trips aren't included.| Created by [PerCapita DailyTravel Distance Time.Rmd](PerCapitaDailyTravelDistanceTime); this script uses the updated_output of [CoreSummaries.Rmd](../../../model-files/scripts/core_summaries/CoreSummaries.Rmd).
1 & 2 | Per capita mean daily travel distance & time | metrics\ auto_times.csv | Use this (the last line) for trucks. <br>This is not segmented by age and sex, nor does it really know if multiple truck trips are driven by a single driver, so we can only infer **mean truck trip travel distance** and **mean truck trip travel time**. | Produced by [sumAutoTimes.job](../metrics/sumAutoTimes.job)
10 & 11 |Personal & Vehicle travel distance by facility type | metrics\ ITHIM\ Distance TraveledBy FacilityType_ auto+truck.csv | Includes auto and trucks only. <br>Personal categories are car_driver, car_passenger, truck_driver.  Vehicle categories are auto, sm_med_truck, heavy_truck. <br>Since these numbers come from the network, non-resident trips such as internal/external trips and airport trips are included.| Producted by [net2csv_ avgload5 period.job](../metrics/net2csv_avgload5period.job) to convert the network to CSV, and [Distance TraveledBy FacilityType.py](DistanceTraveledByFacilityType.py).
10 |Personal travel distance by facility type | metrics\ nonmot_times.csv | This doesn't actually have facility type, just total distance.  The TM1 network doesn't have enough detail to give meaningful walk and bike distances by facility types, nor does it have walk and bike route choice models. | Produced using [sum Nonmot Times.job](../metrics/sumNonmotTimes.job), which multiplies skims by trip tables.
10 |Personal travel distance by facility type | metrics\ ITHIM\ Distance TraveledBy FacilityType_ transit.csv | Includes person miles traveled on different facilities (local bus, light rail or ferry, express bus, heavy rail, commuter rail, drive, walk) by access, transit and egress modes. From transit skims x trip tables. | Computed using [sumTransit Distance.job](sumTransitDistance.job).
11 | Vehicle travel distance by facility type | metrics\ ITHIM\ Distance TraveledBy FacilityType_ transitveh.csv | Includes daily transit vehicle miles traveled for local bus, light rail or ferry, express bus, heavy rail, and commuter rail vehicles. | Computed using [Distance TraveledBy FacilityType_ transitveh.py](DistanceTraveledByFacilityType_transitveh.py), which reads transit assignment output line files.

