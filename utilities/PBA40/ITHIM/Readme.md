
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

RunITHIMMetrics.bat will produce these items as follows:

* **1 - Per capita mean daily travel distance** and **2 - Per capita mean daily travel time** is produced by
  PerCapitaDailyTravelDistanceTime.Rmd for car-driver, car-passenger, bus, rail, walk and bicycle modes.  This script
  uses the updated_output of CoreSummaries.Rmd.
* **1 - Per capita mean daily travel distance** and **2 - Per capita mean daily travel time** for trucks
  is produced by sumAutoTimes.job.  This is not segmented by age and sex, nor does it really know
  if multiple truck trips are driven by a single driver, so these numbers are really 
  **mean truck trip travel distance** and **mean truck trip travel time**.