# Longitudinal VMT per Capita and per Worker Summaries
This directory contains scripts that summarize observed and estimated vehicle-miles traveled per capita and per worker.  The intent of the `long-obs-est-vmt-per-capita.Rmd` and `long-obs-est-vmt-per-worker.Rmd` scripts are to create input files for the `Longitudinal VMT per Capita Observed and Estimated` and `Longitudinal VMT per Worker Observed and Estimated` Tableau workbooks.  The data files that are created by the `R` scripts are available in the `observed-estimated-vmt` folder [here](https://mtcdrive.box.com/share-data).  Also available in this location are packaged versions of the above-referenced Tableau workbooks that can be viewed with [Tableau Reader](http://www.tableau.com/products/reader).

Two important notes regarding the summaries of observed data are as follows:

1.  Household travel surveys have well-known biases against recording travel (see, e.g., this [research note](http://www.rita.dot.gov/bts/sites/rita.dot.gov.bts/files/publications/journal_of_transportation_and_statistics/volume_08_number_03/html/paper_07/index.html) from the Bureau of Transportations Statistics).  We expect the travel we capture in surveys to be under-reported.  In these summaries, the simulated data shows consistently higher amounts of travel than the observed data.  This outcome is expected.

2.  The household travel surveys summarized in these workbooks used a county-level sampling frame.  As such, the data is not intended to accurately represent travelers at sub-county geographies.  The summaries in the Tableau workbook present the data at sub-county geographies.  This is a mis-use of the data that we intentionally carry out to transparently describe the data.

