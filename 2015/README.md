
# Scripts and data used to create travel model land use inputs

## This directory:

### [ACS 2013-2017 create TAZ data for 2015.R](ACS%2013-2017%create%TAZ%data%for%2015.R)

This script brings in all inputs and creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one)

* Author: [@shimonisrael](https://github.com/shimonisrael)

* Input: Cached versions of ACS 2013-2017 API block group data inputs, brought in with [Import block group data.R](Import%block%group%data.R): 
  * [ACS 2013-2017 Block Group Vars1.csv](ACS%202013-2017%20Block%20Group%20Vars1.csv), [ACS 2013-2017 Block Group Vars2.csv](ACS%202013-2017%20Block%20Group%20Vars2.csv), and [ACS 2013-2017 Block Group Vars3.csv](ACS%202013-2017%20Block%20Group%20Vars3.csv)
  * [ESRI 2015 NAICS2 and ABAG6 noin.csv](Employment/ESRI%2015%NAICS2%and%ABAG6%noin.csv) employment data, with net incommute removed
  * [tazData_enrollment.csv](School%Enrollment/tazData_enrollment.csv) 2015 school high school and college enrollment

* Output:  
  * [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
  * [TAZ1454 2010 District Summary.csv](TAZ1454%202010%20District%20Summary.csv)
  * [TAZ1454 2015 District Summary.csv](TAZ1454%202015%20District%20Summary.csv)
  * [TAZ1454 2015 Popsim Vars.csv](TAZ1454%202015%20Popsim%20Vars.csv)
  * [TAZ1454 2015 Popsim Vars Region.csv](TAZ1454%202015%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2015 Popsim Vars County.csv](TAZ1454%202015%20Popsim%20Vars%20County.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/892913197780752/f)

## [Additional Unit and HH Balancing](Additional%Unit%and%HH%Balancing)

### [2015 unit person and HH balancing.R](Additional%Unit%and%HH%Balancing/2015%unit%person%and%HH%balancing.R)

It was our initial assumption that the output of [ACS 2013-2017 create TAZ data for 2015.R](ACS%2013-2017%create%TAZ%data%for%2015.R) should not have any TAZ-level housing unit and household count decreases from the 2010 tazdata used in PlanBayArea2040 (see http://data.mtc.ca.gov/data-repository/).  This script was designed to adjust those numbers to move growth within counties such that the above was true and county totals remained the same. The below Asana task describes why this approach was ultimately put on hold. While the approach works in instances where the 2015 county land use values are greater than the 2010 values, in some counties (San Mateo and Santa Clara), the 2010 values for total units exceed the 2015 values. This is true of the 2010 and 2015 land use, but not true for the underlying census data. 

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: PBA40 2010 tazData (2010_06_003) and [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
* Output: [Quick Total Units and HHs Comparison.csv](Additional%Unit%and%HH%Balancing/Quick%Total%Units%and%HHs%Comparison.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/909682345976879/f)

## [Deprecated](Deprecated)

This folder includes superseded scripts and data kept for archive purposes. 

### [ACS 2012-2016 create TAZ data for 2015.R](Deprecated/ACS%2012-2016%create%TAZ%data%for%2015.R)

Creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one). 

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: 2012-2016 ACS 5-year Estimates, block to TAZ1454 geography lookup
* Notes: superseded by [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R) as new ACS data became available. 
* See also: [Asana task](https://app.asana.com/0/13098083395690/864065795026327/f)

### [basis.py](Deprecated/basis.py)

* Author: [@fscottfoti](https://github.com/fscottfoti)

`basis.py` is a script used to operate on this data.  There are several modes of operation (use the --mode command line option), analagous to baus.py in the bayarea_urbansim directory.  The modes include:

* `merge_gp_data` which merges the general plan data from each jurisdiction into a single file (edit the code to pick which output format you'd prefer)
* `diagnose_merge` which is used to find rows in zoning_lookup.csv which are currently assigned to parcels, which do not occur in the general plan shapefiles.  There are currently about 190 rows which are missing which are written to [missing_zoning_ids.csv](https://github.com/oaklandanalytics/badata/blob/master/missing_zoning_ids.csv) - this csv includes an attribute "Parcel Count" which is the number of parcels which have that id.  These missing shapes are an issue because these zones will not be assigned in future merges of the parcels and general plan shapes.

### [Summarize parking by TAZ.R](Deprecated/Summarize%parking%by%TAZ.R)

Converts Travel Model Two MAZ parking costs to TM1 TAZ values. Given some observed inconsistencies, it was instead decided to use the Plan Bay Area 2040 published [TAZ data for 2040](https://mtcdrive.app.box.com/file/208576797404)

### [Employment](Deprecated/Employment)

This folder includes a lot of investigation of other data sets for employment - LODES, NETS, and ESRI data. In the end ESRI data was used, though, given more time, it would be valuable to compare the other datasets on TAZ-by-TAZ (or smaller geography) basis. 

## [Documentation](Documentation)

Documentation memo: [TM 1.5 TAZ 1454 Land Use Documentation Memo.docx](Documentation/TM%201.5%20TAZ%201454%20Land%20Use%20Documentation%20Memo.docx)

## [Employment](Employment)




