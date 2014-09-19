
# Core Summaries

This directory consists of a set of files to compile summaries across a set of model runs.

Most of this is written to check the existence of files and run things only if things
don't exist, so to force everything to run, clear out the scenario and across-scenario dirs.

The files contained are as follows (from the top down):

### [summarizeAcrossScenarios.bat]

This file sets up some environment variables such as what scenarios we will summarize,
where this code is setup, and where the combined (across scenarios) data files should reside.

It then goes through each scenario and calls [summarizeScenario.bat]

After those summaries are complete, it creates a Tableau Data Extract for each summary type,
which combines the data across scenarios.  The Tableau workbook then loads data across all the
scenarios, with worksheets showing across-scenario summaries (non-white tabs) or
per-scenario summaries (with white tabs).

### summarizeScenario.bat

This script summarizes a single scenario.

(It starts with a mapping from scenario name (e.g. 2010_04_ZZZ) to some directory locations,
but this mapping will likely be elsewhere or removed.)

It works by
 * copying the files required via [copyCoreSummariesInputs.bat]
 * running the R script, CoreSummaries.Rmd, if needed (if any of the summary outputs don't exist)
 * converting the resulting `.rdata` files to Tableau Data Extracts
 * converting a couple of other csv files to Tablea Data Extracts

### copyCoreSummariesInputs.bat

This copies required files from the variously specified input directories to a single place.

If Core Summaries scripts happen as part of a model run, this will likely be unnecessary and
the summary scripts can just refer to the inputs in their original locations.

### CoreSummaries.Rmd

This R script is the bulk of the process.  It reads Trips, Tours, Persons and Households,
joining them together and joining them with skims in order to create summaries of interest.

It outputs numerious summaries both as `.csv` files and as `.rdata` files.  The
Tableau data extracts are converted from the `.rdata` files because the binary format
is more compressed and also contains information about data types.

It also outputs updated `.rdata` versions of the Trip, Tours, Persons and Households table, 
with the extra data fields added.
  