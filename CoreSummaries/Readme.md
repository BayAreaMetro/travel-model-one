
# Core Summaries

This directory consists of a set of files to compile summaries across a set of model runs.

Most of this is written to check the existence of files and run things only if things
don't exist, so to force everything to run, clear out the scenario and across-scenario dirs.

The files contained are as follows (from the top down):

### summarizeAcrossScenarios.bat

This file sets up some environment variables such as what scenarios we will summarize,
where this code is setup, and where the combined (across scenarios) data files should reside.

It then goes through each scenario and calls [summarizeScenario.bat](summarizeScenario.bat)

After those summaries are complete, it creates a Tableau Data Extract for each summary type,
which combines the data across scenarios.  The Tableau workbook then loads data across all the
scenarios, with worksheets showing across-scenario summaries (non-white tabs) or
per-scenario summaries (with white tabs).

### summarizeScenario.bat

This script summarizes a single scenario.

(It starts with a mapping from scenario name (e.g. 2010_04_ZZZ) to some directory locations,
but this mapping will likely be elsewhere or removed.)

It works by
 * copying the files required via [copyCoreSummariesInputs.bat](copyCoreSummariesInputs.bat)
 * running the R script, [CoreSummaries.Rmd](CoreSummaries.Rmd), if needed (if any of the summary outputs don't exist)
 * converting the resulting `.rdata` files to Tableau Data Extracts via [RdataToTableauExtract.py](RdataToTableauExtract.py)
 * converting a couple of other csv files to Tablea Data Extracts via [csvToTableauExtract.py](csvToTableauExtract.py)

### copyCoreSummariesInputs.bat

This copies required files from the variously specified input directories to a single place.

If Core Summaries scripts happen as part of a model run, this will likely be unnecessary and
the summary scripts can just refer to the inputs in their original locations.

### CoreSummaries.Rmd

This R script is the bulk of the process.  It reads Trips, Tours, Persons and Households,
joining them together and joining them with skims in order to create summaries of interest.

It outputs numerious summaries both as `.csv` files and as `.rdata` files.  The
Tableau data extracts are converted from the `.rdata` files because the binary format
is more compressed and also contains information about data types.  The index columns are those
before the `freq` column.  These outputs include:

 * *ActiveTransport* - Active transportation summary of persons.  Sum(freq) = Population
   * taz - TAZ of residence
   * county_name - County of residence
   * ptype - Person type. (1:"Full-time worker"; 2:"Part-time worker"; 3:"University student"; 4:"Nonworker"; 5:"Retired"; 6:"Student of non-driving age"; 7:"Student of driving age"; 8:"Child too young for school")
   * zeroAuto - boolean, True if zero autos in the household
   * freq - Frequency of persons
   * active - Average minutes of active travel per person per weekday
   * more15 - Share of population that engages in at least 15 minutes of active travel per typical weekday.
   * more30 - Share of population that engages in at least 30 minutes of active travel per typical weekday.
   * wlk_trip - Share of population that makes walk trips (excluding walking as part of transit travel)
   * bik_trip - Share of population that makes bicycle trips
   * wtr_trip - Share of population that makes walk-to-transit trips
   * dtr_trip - Share of population that makes drive-to-transit trips (note these have a walk component)
   * atHomeA - Share of population that does not leave home on a typical weekday
   
 * *ActivityPattern* - Activity pattern summary of persons.  Sum(freq) = Population
   * *type* - Person type string.  One of ("Full-time worker"; "Part-time worker"; "University student"; "Nonworker"; "Retired"; "Student of non-driving age"; "Student of driving age"; "Child too young for school")
   * *activity_pattern*	- Daily activity pattern category.  One of 'H' for home, 'M' for mandatory, or 'N' for non-mandatory. 
   * *imf_choice* - Individual mandatory tour frequency .  See http://analytics.mtc.ca.gov/foswiki/Main/Person
   * *inmf_choice* - Individual non-mandatory tour frequency. See http://analytics.mtc.ca.gov/foswiki/Main/Person
   * *incQ_label* - Income quartile.  One of ('Less than $30k', '$30k-$60k', '$60k-$100k', 'More than $100k')
   * *freq* - Frequency of persons

 * *AutomobileOwnership*
 * *AutoTripsVMT_perOrigDestHomeWork*
 * *AutoTripsVMT_personsHomeWork*
 * *CommuteByEmploymentLocation*
 * *CommuteByIncomeHousehold*
 * *CommuteByIncomeJob*
 * *JourneyToWork*
 * *PerTripTravelTime*
 * *TimeOfDay*
 * *TimeOfDay_personsTouring*
 * *TravelCost*
 * *TripDistance*
 * *VehicleMilesTraveled*

It also outputs updated `.rdata` versions of the Trip, Tours, Persons and Households table, 
with the extra data fields added.
  