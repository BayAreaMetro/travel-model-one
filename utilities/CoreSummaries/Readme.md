
# Core Summaries

This directory consists of a set of files to compile summaries across a set of model runs.

Most of this is written to check the existence of files and run things only if things
don't exist, so to force everything to run, clear out the scenario and across-scenario dirs.

Core Summaries scripts (which proccess model results for a single model run) and their associated
documentation have been moved to [model-files/scripts/core_summaries](../../model-files/scripts/core_summaries)

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

