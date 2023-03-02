## CoreSummaries.R

This R script reads Trips, Tours, Persons and Households, joining them together and joining them with skims in order to create summaries of interest.

**A note on costs**: The costs databases used by CoreSummaries do not [split auto costs by bridge tolls, value tolls, and distance-based auto operating costs](../database/SkimsDatabase.JOB). Therefore, the means based discounts for auto modes below are being applied incorrectly because only the value-toll based factor is implemented and it is being applied to the entire cost rather than the express lane tolls.  The means-based discounts for cordon tolls are not implemented here.

It outputs numerious summaries both as `.csv` files and as `.rdata` files.  The
Tableau data extracts are converted from the `.rdata` files because the binary format
is more compressed and also contains information about data types.  The index columns are those
before the `freq` column.  These outputs include:

* [ActiveTransport](#activetransport)
* [ActivityPattern](#activitypattern)
* [AutomobileOwnership](#automobileownership)
* [AutoTripsVMT_perOrigDestHomeWork](#autotripsvmt_perorigdesthomework)
* [AutoTripsVMT_personsHomeWork](#autotripsvmt_personshomework)
* [CommuteByEmploymentLocation](#commutebyemploymentlocation)
* [CommuteByIncomeHousehold](#commutebyincomehousehold)
* [CommuteByIncomeJob](#commutebyincomejob)
* [JourneyToWork](#journeytowork)
* [PerTripTravelTime](#pertriptraveltime)
* [TimeOfDay](#timeofday)
* [TimeOfDay_personsTouring](#timeofday_personstouring)
* [TravelCost](#travelcost)
* [TripDistance](#tripdistance)
* [VehicleMilesTraveled](#vehiclemilestraveled)
* [VehicleMilesTraveled_households](#vehiclemilestraveled_households)
* [Additional Output Tables](#additional-output-tables)
  * [tours.rdata](#toursrdata)
  * [trips.rdata](#tripsrdata)
* [TelecommuteEligibleBySD](#telecommuteeligiblebysd)

### ActiveTransport

Active transportation summary of persons.  Sum(freq) = population

| Column Name | Description |
|-------------|-------------|
| taz | TAZ of residence |
| county_name | County of residence |
| ptype | Person type. (1:"Full-time worker"; 2:"Part-time worker"; 3:"University student"; 4:"Nonworker"; 5:"Retired"; 6:"Student of non-driving age"; 7:"Student of driving age"; 8:"Child too young for school" |
| zeroAuto | boolean, True if zero autos in the household |
| freq | Frequency of persons |
| active | Average minutes of active travel per person per weekday |
| more15 | Share of population that engages in at least 15 minutes of active travel per typical weekday |
| more30 | Share of population that engages in at least 30 minutes of active travel per typical weekday |
| wlk_trip | Share of population that makes walk trips (excluding walking as part of transit travel) |
| bik_trip | Share of population that makes bicycle trips |
| wtr_trip | Share of population that makes walk-to-transit trips |
| dtr_trip | Share of population that makes drive-to-transit trips (note these have a walk component) |
| atHomeA | Share of population that does not leave home on a typical weekday |
   
### ActivityPattern
Activity pattern summary of persons.  Sum(freq) = population

| Column Name | Description |
|-------------|-------------|
| type | Person type string.  One of ("Full-time worker"; "Part-time worker"; "University student"; "Nonworker"; "Retired"; "Student of non-driving age"; "Student of driving age"; "Child too young for school") |
| activity_pattern | Daily activity pattern category.  One of 'H' for home, 'M' for mandatory, or 'N' for non-mandatory. |
| imf_choice | Individual mandatory tour frequency .  See https://github.com/BayAreaMetro/modeling-website/wiki/Person |
| inmf_choice | Individual non-mandatory tour frequency. See https://github.com/BayAreaMetro/modeling-website/wiki/Person |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| freq | Frequency of persons |

### AutomobileOwnership
Automobile Ownership summary of households.  Sum(freq) = households

| Column Name | Description |
|-------------|-------------|
| SD | Superdistrict geographical designation of residence. See https://github.com/BayAreaMetro/modeling-website/wiki/TazData |
| COUNTY | County code of residence.  See https://github.com/BayAreaMetro/modeling-website/wiki/TazData |
| county_name   | County name of residence. |
| autos | Number of autos in the household, from 0 to 4 |
| incQ  | Income quartile, from 1 to 4 |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| walk_subzone | Walk to transit sub-zone.  One of 0,1, or 2.  See https://github.com/BayAreaMetro/modeling-website/wiki/Household |
| walk_subzone_label | String version of `walk_subzone` |
| workers | Number of workers in the household |
| kidsNoDr| Boolean; True iff the household has children in the househole that don't drive
 (either pre-school age or school age) |
| freq | Frequency of households |

### AutoTripsVMT_perOrigDestHomeWork
Automobile trips for VMT summing.  Sum(trips) = total auto trips for an average weekday.

| Column Name | Description |
|-------------|-------------|
| orig_taz | Origin TAZ for the trip |
| dest_taz | Destination TAZ for the trip |
| taz | TAZ of residence for the tripmaker |
| WorkLocation | TAZ of work location for the tripmaker, or 0 if none |
| vmt | VMT for the trips, a sum of `vmt_indiv` and `vmt_joint` |
| vmt_indiv | VMT from individual trips |
| vmt_joint | VMT from joint trips |
| trips | Number of (person) trips |
| vehicle_trips | Number of vehicle trips |

### AutoTripsVMT_personsHomeWork
Automobile trips by person.  Sum(freq) = population

| Column Name | Description |
|-------------|-------------|
| COUNTY | County code of residence |
| county_name   | County name of residence |
| taz   | TAZ of residence |
| WorkLocation  | TAZ of Work location or 0 if none |
| freq | Number of persons with this home/work combination |

### CommuteByEmploymentLocation
Commute characteristics by employment location.  Sum(freq) = commute tours

| Column Name | Description |
|-------------|-------------|
| dest_COUNTY | County code of work commute destination |
| dest_county_name | County name of work commute destination |
| dest_SD   | Superdistrict of work commute destination |
| tour_mode | Work tour mode.  See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour |
| freq | Number of commute tours |
| totCost   | Total round-trip out of pocket costs in cents in 2000$.  Sum of `cost` and `parking_cost`. |
| cost | See https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims#cost-skims for what's included |
| parking_cost | Parking costs (in cents in 2000$)|
| distance | Distance of commute (in miles)|
| cost_fail | Commute tours for which the cost lookup failed |

### CommuteByIncomeHousehold
Commute characteristics by household location. Sum(freq) = commute tours

| Column Name | Description |
|-------------|-------------|
| res_COUNTY | County code of residence |
| res_county_name | County name of residence |
| res_SD | Superdistrict of residence |
| orig_taz | Origin TAZ |
| tour_mode | Work tour mode.  See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour |
| incQ  | Income quartile |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| freq | Number of commute tours.
| totCost  | Total round-trip out of pocket costs in cents in 2000$.  Sum of `cost` and `parking_cost`. |
| cost | See https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims#cost-skims for what's included |
| parking_cost | Parking costs (in cents in 2000$)|
| distance | Distance of commute (in miles)|
| duration  | Duration of commute (in minutes) |
| cost_fail | Commute tours for which the cost lookup failed |
| time_fail | Commute tours for which the time lookup failed |

### CommuteByIncomeJob
Commute characteristics by job location.  Sum(freq) = commute tours

Columns are the same as CommuteByIncomeHousehold, except they are summed 
to job/destination geographies instead of to residential geographies.

### JourneyToWork
Workplace location summaries (including when tours are not made)  Sum(freq) = persons with work locations

| Column Name | Description |
|-------------|-------------|
| homeCOUNTY | County code of residence |
| home_county_name  | County name of residence |
| HomeTAZ | TAZ of residence |
| WorkLocation | TAZ of work location |
| workCOUNTY | County code of work location |
| work_county_name | County name of work location |
| freq | Number of persons with home/work locations as described |
| Income | Average income |

### JourneyToWork_modes
Workplace location summaries (including when tours are not made) with commute mode. Sum(freq) = persons with work locations

| Column Name | Description |
|-------------|-------------|
| incQ | Income Quartile |
| incQ_label | Income Quartile label |
| homeSD | Home superdistrict |
| HomeSubZone | Walk to transit subzone of home |
| workSD | Work superdistrict |
| WorkSubZone | Walk to transit zubzone of work |
| tour_mode | Tour mode of commute trip |
| freq | Number of persons |
| distance | Total distance for the commute tour of this category |


### PerTripTravelTime
Sum(freq) = trips

| Column Name | Description |
|-------------|-------------|
| incQ | Income quartile |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| trip_mode | Trip mode. See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip |
| tour_purpose | Tour purpose for the trip.  See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour |
| freq | Number of trips |
| num_participants | Number of participants for these trips |
| trvlTime | Average travel time (in minutes)|
| time_fail | Commute tours for which the time lookup failed |

### TimeOfDay
Sum(freq) = tours

| Column Name | Description |
|-------------|-------------|
| SD | Superdistrict of residence |
| COUNTY | County of residence |
| county_name | County name of residence |
| simple_purpose | Simple tour purpose, one of ('work', 'school', 'non-work', 'at-work', 'college') |
| tour_mode | Tour mode.  See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour |
| start_hour | Start hour for the tour, in [5,23] |
| end_hour | End  hour for the tour, in [5,23] |
| freq | Number of tours |
| num_participants | Number of person participants |

### TimeOfDay_personsTouring
Summary of how many persons are touring at a given hour.

| Column Name | Description |
|-------------|-------------|
| simple_purpose | Simple tour purpose, one of ('work', 'school', 'non-work', 'at-work', 'college') |
| persons_touring | Number of persons touring |
| hour | The hour of their tour, in [5,23] |

### TravelCost
Travel costs by household.  Sum(freq) = households

| Column Name | Description |
|-------------|-------------|
| SD | Superdistrict of residence |
| COUNTY | County code of residence |
| county_name | County name of residence |
| people | Persons per household, capped at 6 |
| incQ | Income Quartile |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| autos | Number of autos in the household, from 0 to 4 |
| freq | Number of households |
| total_cost | Total travel costs (in cents in 2000$) |
| trip_cost_indiv | Total travel costs from individual trips (in cents in 2000$)|
| trip_cost_joint   | Total travel costs from joint trips (in cents in 2000$) |
| cost_fail | Trips for which the cost lookup failed |
| pcost_indiv | Parking cost from individual trips (in cents in 2000$) |
| pcost_joint | Parking cost from joint trips (in cents in 2000$)|


### TripDistance
Distance summaries for trips.  Sum(freq) = trips

| Column Name | Description |
|-------------|-------------|
| autoSuff | Auto sufficiency code, one of [0,1,2] |
| autoSuff_label | Auto sufficiency label, one of ('Zero automobiles','Automobiles < workers','Automobiles >= workers') |
| incQ | Income Quartile |
| incQ_label | Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k') |
| timeCode | Time period of trip, one of ('AM','MD','PM','EV','EA') |
| timeperiod_label | Time period label, one of ('AM Peak', 'Midday', 'PM Peak', 'Evening', 'Early AM') |
| trip_mode | Trip mode. See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip |
| tour_purpose | Tour purpose for the trip.  See https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour |
| freq | Number of trips |
| distance | Average trip distance (in miles) |

### VehicleMilesTraveled
Auto vehicle miles traveled summed to persons. Sum(freq) = population

| Column Name | Description |
|-------------|-------------|
| COUNTY | County code of residence |
| county_name | County name of residence |
| SD | Superdistrict of residence |
| taz | TAZ of residence |
| walk_subzone | Walk to transit sub-zone.  One of 0,1, or 2.  See https://github.com/BayAreaMetro/modeling-website/wiki/Household |
| walk_subzone_label | String version of `walk_subzone` |
| ptype | Person type. (1:"Full-time worker"; 2:"Part-time worker"; 3:"University student"; 4:"Nonworker"; 5:"Retired"; 6:"Student of non-driving age"; 7:"Student of driving age"; 8:"Child too young for school" |
| ptype_label   | Person type label from 'ptype' |
| autoSuff | Auto sufficiency code, one of [0,1,2] |
| autoSuff_label | Auto sufficiency label, one of ('Zero automobiles','Automobiles < workers','Automobiles >= workers') |
| freq | Number of persons |
| vmt_indiv | Mean VMT from individual trips |
| vmt_joint | Mean VMT from joint trips |
| vmt | Mean VMT (i.e. VMT per person) So, to get total VMT, it would be vmt * freq |
| person_trips | Total person Trips |
| vehicle_trips | Total vehicle Trips |

### VehicleMilesTraveled_households

Auto vehicle miles traveled summed to households.
Same columns as VehicleMilesTraveled but Sum(freq) = households and no ptype columns.

### Additional Output Tables
It also outputs updated `.rdata` versions of the Trip, Tours, Persons and Households table, 
with the extra data fields added in `updated_output`

### tours.rdata

Each row corresponds to an individual tour or joint tour.  Note that each joint tour is represented *once*, with *num_participants* > 1.

| Column Name | Description | Data Type |
|-------------|-------------|-----------|
| hh_id | Unique household ID number corresponding to the HHID in [PopSynHousehold](https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold) | Long integer |
| tour_id | Updated string ID (differs from version in tour outputfiles).  Concatenation of `i` or `j` for individual or joint, first four characters of *tour_purpose*, and *tour_id* from [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) | String |
| tour_category | Type of tour | String, "MANDATORY"; "INDIVIDUAL_NON_MANDATORY"; "AT_WORK"; "JOINT_NON_MANDATORY" |
| tour_purpose | Tour purpose | String, "work_low"; "work_med"; "work_high"; "work_very high"; "university"; "school_high"; "school_grade"; "atwork_business"; "atwork_eat"; "atwork_maint"; "eatout"; "escort_kids"; "escort_no kids"; "othdiscr", "othmaint"; "shopping"; "social" |
| orig_taz | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| orig_walk_segment | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| dest_taz | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| dest_walk_segment | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| start_hour | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| end_hour | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| tour_mode | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| num_ob_stops | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| num_ib_stops | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
| avAvailable | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | dcLogsum | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | sampleRate | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | origTaxiWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | destTaxiWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | origSingleTNCWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | destSingleTNCWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | origSharedTNCWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | destSharedTNCWait | Same as [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) ||
 | income | Annual household income ($2000) from [PopSynHousehold](https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold) | Integer |
 | incQ | Income Quartile | Integer, 1: less than 30k (in $2000); 2: 30-60k (not including 60k); 3: 60-100k (not including 100k); 4: 100k and above |
 | incQ_label | Income Quartile label | String, "Less than $30k","$30k to $60k","$60k to $100k","More than $100k" |
 | num_participants | Number of household participants in the tour; 1 if individual, more if joint | Integer, 1 to 10 |
 | dest_COUNTY | County of dest_taz | Integer, 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7=Napa; 8=Sonoma; 9=Marin |
 | dest_county_name | County of dest_taz | String, "San Francisco"; "San Mateo"; "Santa Clara"; "Alameda"; "Contra Costa"; "Solano"; "Napa"; "Sonoma"; "Marin" |
 | dest_SD | Superdistrict of dest_taz | Integer |
 | PRKCST | Hourly parking rate paid by long-term (8-hours) parkers (year 200 cents), from dest_taz and [TazData](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) | Float |
 | OPRKCST | Hourly parking rate paid by short-term parkers (year 2000 cents), from dest_taz and [TazData](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) | Float |
 | fp_choice | Free parking eligibility choice from [Person](https://github.com/BayAreaMetro/modeling-website/wiki/Person) | Integer, 1 - person will park for free; 2 - person will pay to park; 0 - joint tour, so not applicable. Note fp_choice applies to work tours only |
 | parking_rate | Hourly parking rate for this tour (year 2000 cents).  One of PRKCST or OPRKCST, depending on tour_category.  If work tour and person has free parking, then this is zero | Float |
 | taz | Household residence TAZ | Integer |
 | SD | Household residence Superdistrict | Integer |
 | COUNTY | Household residence county | Integer, 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7=Napa; 8=Sonoma; 9=Marin |
 | county_name | Household residence county | String, "San Francisco"; "San Mateo"; "Santa Clara"; "Alameda"; "Contra Costa"; "Solano"; "Napa"; "Sonoma"; "Marin" |
 | simple_purpose | Simplified purpose, from tour_purpose | String, "non-work"; "work"; "school"; "college"; "at work" |
 | duration | Tour duration, end_hour-start_hour+0.5 | Float |
 | parking_cost | Total parking cost, based on tour duration and parking_rate.  Split if tour_mode is SR2/SR3. Zero for non-private-auto modes. | Float |
 | pcost_indiv | Parking cost for individual tours | Float |
 | pcost_joint | Parking cost for joint tours | Float |


### trips.rdata

| Column Name | Description | Data Type |
|-------------|-------------|-----------|
| hh_id             | Unique household ID number corresponding to the HHID in [PopSynHousehold](https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold) | Long integer |
| person_id         | Unique person ID number corresponding to the PERID in [PopSynPerson](https://github.com/BayAreaMetro/modeling-website/wiki/PopSynPerson) | Long integer |
| person_num        | Person number unique to the household, starting at 1 (see [Person](https://github.com/BayAreaMetro/modeling-website/wiki/Person)) | Integer |
| tour_id           | Updated string ID (differs from version in tour outputfiles).  Concatenation of `i` or `j` for individual or joint, first four characters of *tour_purpose*, and *tour_id* from [IndividualTour](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour) or [JointTour](https://github.com/BayAreaMetro/modeling-website/wiki/JointTour) | String |
| orig_taz          | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| orig_walk_segment | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| dest_taz          | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| dest_walk_segment | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| trip_mode         | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| tour_purpose      | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| orig_purpose      | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| dest_purpose      | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| depart_hour       | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| stop_id           | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| tour_category     | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| avAvailable       | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| sampleRate        | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| inbound           | Same as [IndividualTrip](https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip) or [JointTrip](https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip) ||
| num_participants  | Number of participants on the tour; 1 if individual, 2 and up if joint | Integer |
| tour_participants | Household members participating in the tour | String of Integers, with spaces between, of the person_num |
| timeCodeNum       | Time period of travel, based on depart_hour | Integer, 1=EA; 2=AM; 3=MD; 4=PM; 5=EV |
| timeperiod_label  | Time period of travel, based on timeCodeNum | String, one of "Early AM","AM Peak","Midday","PM Peak","Evening" |
| timeCode          | Time period of travel, based on timeCodeNum | String, one of "EA","AM","MD","PM","EV" |
| incQ              | Income Quartile | Integer, 1: less than 30k (in $2000); 2: 30-60k (not including 60k); 3: 60-100k (not including 100k); 4: 100k and above |
| incQ_label        | Income Quartile label | String, "Less than $30k","$30k to $60k","$60k to $100k","More than $100k" |
| autoSuff          | Auto sufficiency code, one of [0,1,2] | Integer |
| autoSuff_label    | Auto sufficiency label | String, "Zero automobiles",'Automobiles < workers","Automobiles >= workers" |
| home_taz          | TAZ of home location | Integer |
| walk_subzone      | Walk to transit sub-zone of home from [Household](https://github.com/BayAreaMetro/modeling-website/wiki/Household) | Integer, 0=cannot walk to transit; 1=short walk to transit; 2=long walk to transit |
| walk_subzone_label| Label for walk_subzone | String |
| ptype             | Person type | Integer, 1=Full-time worker; 2=Part-time worker; 3=College student; 4=Non-working adult; 5=Retired; 6=Driving-age student; 7-Non-driving-age student; 8=Child too young for school |
| ptype_label       | Label for person type | String |
| fp_choice | Free parking eligibility choice from [Person](https://github.com/BayAreaMetro/modeling-website/wiki/Person) | Integer, 1 - person will park for free; 2 - person will pay to park; 0 - joint tour, so not applicable. Note fp_choice applies to work tours only |
| distance          | Distance of trip, in miles.  Note that these are based on [SimpleSkims](https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims) so the transit distances are from da/datoll | Float |
| tour_duration     | Duration of tour, in hours | Float |
| amode             | Active trip mode mode| Integer, 0=no walk, 1=walk, 2=bike, 3=walk to and from transit, 4=walk to transit, 5=walk from transit |
| wlk_trip          | Walk trip mode | Integer, 1=walk, 0 otherwise | Integer |
| bik_trip          | Walk trip mode | Integer, 1=bike, 0 otherwise | Integer |
| wtr_trip          | Walk to transit trip mode | Integer, 1=walk to and from transit, 0 otherwise |
| dtr_trip          | Drive to transit trip mode | Integer, 1=drive from transit, 6=drive to transit, 0 otherwise |
| active            | Active transportation time for the trip, in minutes | Float
| costMode          | (doc to be added) | |
| cost              | (doc to be added) | |
| cost_fail         | (doc to be added) | |
| time              | (doc to be added) | |
| time_fail         | (doc to be added) | |
| trip_cost_indiv   | (doc to be added) | |
| trip_cost_joint   | (doc to be added) | |


## TelecommuteEligibleBySD

This output is generated by [TelcommuteByIncome.py](TelecommuteByIncome.py).

The script TelecommuteByIncome.py generates a second output, telecommuteEligibleBySDByinc.csv. The columns in this second output file is very similar to those in TelecommuteEligibleBySD.csv, except that:
- It includes an additional column "incQ" indicating the income quartile of the full-time worker (where 1='Less than $30k', 2='$30k-$60k', 3='$60k-$100k', and 4='More than $100k'). 
- It excludes the six columns, (RETEMPN,FPSEMPN,HEREMPN,OTHEMPN,AGREMPN,MWTEMPN)_TazData

Additionally, TelecommuteByIncome.py also outputs a file num_ftworkers_with_telecommutable_jobs.csv, which generates the same data as telecommuteEligibleBySDByinc.csv and telecommuteEligibleBySDByinc.csv.except that it keeps both WorkLocation and HomeTAZ in the index. This output file has not been used for analysis and it will likely be dropped from the next version of the script.

| Column Name | Description |
|-------------|-------------|
| SD | Superdistrict of usual work location |
| SD_NUM_NAME | Superdistrict number and name |
| COUNTY_NUM_NAME | County number and name |
| ftworkers_ (RETEMPN, FPSEMPN, HEREMPN, OTHEMPN, AGREMPN, MWTEMPN) | Number of full-time workers in the given industry (see [TazData.csv](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) for industry categories) who have their usual work locations at this Superdistrict, approximated based on the relationship between income and industry specified in the [destination choice size coefficients](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/DestinationChoiceSizeCoefficients.csv) |
| ftworkers_eligible_ (RETEMPN, FPSEMPN, HEREMPN, OTHEMPN, AGREMPN, MWTEMPN) | Number of full-time workers with jobs that are telecommute eligible in the given industry category, based on the input file [wfh_by_industry.csv](https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/wfh_by_industry.csv) which specifies the percentage of jobs that can be performed at home by industry |
| (RETEMPN, FPSEMPN, HEREMPN, OTHEMPN, AGREMPN, MWTEMPN) _TazData | Employment in the given industry, from the input file [TazData.csv](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) |
| num_NoWorkTours | Number of full-time workers who have their usual work locations at this Superdistrict but make no work tour |
| num_ftworkers_wWrkLoc | Number of full-time workers who their have usual work locations at this Superdistrict. Note that the values in this column may not be exactly the same as the sum of ftworkers_RETEMPN, ftworkers_FPSEMPN, ftworkers_HEREMPN, ftworkers_OTHEMPN, ftworkers_AGREMPN and ftworkers_MWTEMPN, because the destination choice size coefficients do not always add up to exactly 1. |
| P_telecommute | Percentage of full-time workers who have their have usual work locations at this Superdistrict and telecommute |
| num_telecommuters | Number of telecommuters who have this Superdistrict as their usual work location |
| numEligible_numTele_diff | Number of full-time workers with telecommute eligible jobs minus number of full-time workers who telecommute |
| run_directory | Name of the model run |


