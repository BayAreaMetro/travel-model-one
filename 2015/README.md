
# Scripts related to creating Travel Model Land Use Inputs

### ACS 2012-2016 create TAZ data for 2015.R

Creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one)

* Author: @shimonisrael
* Input: 2012-2016 ACS 5-year Estimates, block to TAZ1454 geography lookup
* Output: 
  * [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
  * [TAZ1454 2010 District Summary.csv](TAZ1454%202010%20District%20Summary.csv)
  * [TAZ1454 2015 District Summary.csv](TAZ1454%202015%20District%20Summary.csv)
  * [TAZ1454 2015 Popsim Vars.csv](TAZ1454%202015%20Popsim%20Vars.csv)
  * [TAZ1454 2015 Popsim Vars Region.csv](TAZ1454%202015%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2015 Popsim Vars County.csv](TAZ1454%202015%20Popsim%20Vars%20County.csv)
* Notes: Superceded by [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R)
* See also: [Asana task](https://app.asana.com/0/13098083395690/864065795026327/f)

### ACS 2013-2016 create TAZ data for 2015.R

Creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one)

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: 2013-2017 ACS 5-year Estimates
* Output:
  * [ACS 2013-2017 Block Group Vars1.csv](ACS%202013-2017%20Block%20Group%20Vars1.csv), [ACS 2013-2017 Block Group Vars2.csv](ACS%202013-2017%20Block%20Group%20Vars2.csv) and [ACS 2013-2017 Block Group Vars3.csv](ACS%202013-2017%20Block%20Group%20Vars3.csv)
  * [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
  * [TAZ1454 2010 District Summary.csv](TAZ1454%202010%20District%20Summary.csv)
  * [TAZ1454 2015 District Summary.csv](TAZ1454%202015%20District%20Summary.csv)
  * [TAZ1454 2015 Popsim Vars.csv](TAZ1454%202015%20Popsim%20Vars.csv)
  * [TAZ1454 2015 Popsim Vars Region.csv](TAZ1454%202015%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2015 Popsim Vars County.csv](TAZ1454%202015%20Popsim%20Vars%20County.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/892913197780752/f)
  * Documentation memo: [TM 1.5 TAZ 1454 Land Use Documentation Memo.docx](TM%201.5%20TAZ%201454%20Land%20Use%20Documentation%20Memo.docx)

### 2015 unit person and HH balancing.R

Given the output of [ACS 2013-2016 create TAZ data for 2015.R](ACS 2013-2016 create TAZ data for 2015.R), assumes that the housing unit and household counts don't decrease from the 2010 tazdata used in PlanBayArea2040 (see http://data.mtc.ca.gov/data-repository/).  This script adjusts those numbers to move growth within counties so that no TAZ loses households or housing units.

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: PBA40 2010 tazData (2010_06_003) and [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
* Output: [Adjusted TAZ1454 2015 Land Use.csv](Adjusted%20TAZ1454%202015%20Land%20Use.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/909682345976879/f)

### basis.py

* Author: [@fscottfoti](https://github.com/fscottfoti)

`scripts/basis.py` is a script used to operate on this data.  There are several modes of operation (use the --mode command line option), analagous to baus.py in the bayarea_urbansim directory.  The modes include:

* `merge_gp_data` which merges the general plan data from each jurisdiction into a single file (edit the code to pick which output format you'd prefer)
* `diagnose_merge` which is used to find rows in zoning_lookup.csv which are currently assigned to parcels, which do not occur in the general plan shapefiles.  There are currently about 190 rows which are missing which are written to [missing_zoning_ids.csv](https://github.com/oaklandanalytics/badata/blob/master/missing_zoning_ids.csv) - this csv includes an attribute "Parcel Count" which is the number of parcels which have that id.  These missing shapes are an issue because these zones will not be assigned in future merges of the parcels and general plan shapes.

