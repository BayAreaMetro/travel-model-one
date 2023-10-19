
### [ACS 2012-2016 create TAZ data for 2015.R](ACS%202012-2016%20create%20TAZ%20data%20for%202015.R)

Creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one). 

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: 2012-2016 ACS 5-year Estimates, block to TAZ1454 geography lookup
* Notes: superseded by [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R) as new ACS data became available. 
* See also: [Asana task](https://app.asana.com/0/13098083395690/864065795026327/f)

### [basis.py](basis.py)

* Author: [@fscottfoti](https://github.com/fscottfoti)

`basis.py` is a script used to operate on this data.  There are several modes of operation (use the --mode command line option), analagous to baus.py in the bayarea_urbansim directory.  The modes include:

* `merge_gp_data` which merges the general plan data from each jurisdiction into a single file (edit the code to pick which output format you'd prefer)
* `diagnose_merge` which is used to find rows in zoning_lookup.csv which are currently assigned to parcels, which do not occur in the general plan shapefiles.  There are currently about 190 rows which are missing which are written to [missing_zoning_ids.csv](https://github.com/oaklandanalytics/badata/blob/master/missing_zoning_ids.csv) - this csv includes an attribute "Parcel Count" which is the number of parcels which have that id.  These missing shapes are an issue because these zones will not be assigned in future merges of the parcels and general plan shapes.

### [Summarize parking by TAZ.R](Summarize20parking%20by%20TAZ.R)

Converts Travel Model Two MAZ parking costs to TM1 TAZ values. Given some observed inconsistencies, it was instead decided to use the Plan Bay Area 2040 published [TAZ data for 2040](https://mtcdrive.app.box.com/file/208576797404)

### [Employment](Employment)

This folder includes a lot of investigation of other data sets for employment - LODES, NETS, and ESRI data. In the end ESRI data was used, though, given more time, it would be valuable to compare the other datasets on TAZ-by-TAZ (or smaller geography) basis. 

### [Geography](Geography)

Archived land use policy-related Python geography scripts.