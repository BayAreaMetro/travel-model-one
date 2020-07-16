
# Scripts and data used to create travel model land use inputs

## 1. This directory:

### [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R)

This script brings in all inputs and creates 2015 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one)

* Author: [@shimonisrael](https://github.com/shimonisrael)

* Input: Cached versions of ACS 2013-2017 API block group data inputs, brought in with [Import block group data.R](Import20block%20group%20data.R): 
  * [ACS 2013-2017 Block Group Vars1.csv](ACS%202013-2017%20Block%20Group%20Vars1.csv), [ACS 2013-2017 Block Group Vars2.csv](ACS%202013-2017%20Block%20Group%20Vars2.csv), and [ACS 2013-2017 Block Group Vars3.csv](ACS%202013-2017%20Block%20Group%20Vars3.csv)
  * [ESRI 2015 NAICS2 and ABAG6 noin.csv](Employment/ESRI%202015%20NAICS2%20and%20ABAG6%20noin.csv) Employment data, with net incommute removed
  * [tazData_enrollment.csv](https://github.com/BayAreaMetro/petrale/blob/master/applications/travel_model_lu_inputs/2015/School%20Enrollment/tazData_enrollment.csv) 2015 school high school and college enrollment
  * [tazData.csv](https://mtcdrive.app.box.com/file/208576797404) This file includes TAZ data from the Plan Bay Area 2040 run for 2015. 
  * [2010 to 2015 manual GQ counts](Group%20Quarters/gq_add_00051015.csv) This file includes additional GQ units manually added by MTC staff. 

* Output:  
  * [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
  * [TAZ1454 2010 District Summary.csv](TAZ1454%202010%20District%20Summary.csv)
  * [TAZ1454 2015 District Summary.csv](TAZ1454%202015%20District%20Summary.csv)
  * [TAZ1454 2015 Popsim Vars.csv](TAZ1454%202015%20Popsim%20Vars.csv)
  * [TAZ1454 2015 Popsim Vars Region.csv](TAZ1454%202015%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2015 Popsim Vars County.csv](TAZ1454%202015%20Popsim%20Vars%20County.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/892913197780752/f)

## [2. Additional Unit and HH Balancing](Additional%20Unit%20and%20HH%20Balancing)

### [2015 unit person and HH balancing.R](Additional%20Unit%20and%20HH%20Balancing/2015%20unit%20person%20and%20HH%20balancing.R)

It was our initial assumption that the output of [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R) should not have any TAZ-level housing unit and household count decreases from the 2010 tazdata used in PlanBayArea2040 (see http://data.mtc.ca.gov/data-repository/).  This script was designed to adjust those numbers to move growth within counties such that the above was true and county totals remained the same. The below Asana task describes why this approach was ultimately put on hold. While the approach works in instances where the 2015 county land use values are greater than the 2010 values, in some counties (San Mateo and Santa Clara), the 2010 values for total units exceed the 2015 values. This is true of the 2010 and 2015 land use, but not true for the underlying census data. 

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input: PBA40 2010 tazData (2010_06_003) and [TAZ1454 2015 Land Use.csv](TAZ1454%202015%20Land%20Use.csv)
* Output: [Quick Total Units and HHs Comparison.csv](Additional%20Unit%20and%20HH%20Balancing/Quick%20Total%20Units%20and%20HHs%20Comparison.csv)
* See also:
  * [Asana task](https://app.asana.com/0/13098083395690/909682345976879/f)

## [3. Deprecated](Deprecated)

This folder includes superseded scripts and data kept for archive purposes. 

### [ACS 2012-2016 create TAZ data for 2015.R](Deprecated/ACS%202012-2016%20create%20TAZ%20data%20for%202015.R)

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

### [Summarize parking by TAZ.R](Deprecated/Summarize20parking%20by%20TAZ.R)

Converts Travel Model Two MAZ parking costs to TM1 TAZ values. Given some observed inconsistencies, it was instead decided to use the Plan Bay Area 2040 published [TAZ data for 2040](https://mtcdrive.app.box.com/file/208576797404)

### [Employment](Deprecated/Employment)

This folder includes a lot of investigation of other data sets for employment - LODES, NETS, and ESRI data. In the end ESRI data was used, though, given more time, it would be valuable to compare the other datasets on TAZ-by-TAZ (or smaller geography) basis. 

### [Geography](Deprecated/Geography)

Archived land use policy-related Python geography scripts. 

## [4. Documentation](Documentation)

Documentation memo is here: [TM 1.5 TAZ 1454 Land Use Documentation Memo.docx](Documentation/TM%201.5%20TAZ%201454%20Land%20Use%20Documentation%20Memo.docx). Comprehensive documentation come from the memo, the markdown description here, and the annotated script, [ACS 2013-2017 create TAZ data for 2015.R](ACS%202013-2017%20create%20TAZ%20data%20for%202015.R).

## [5. Employment](Employment)

### [Summarize ESRI with NAICS2 and ABAG6 Equivalency 2015.R](Employment/Summarize%20ESRI%20with%20NAICS2%20and%20ABAG6%20Equivalency%202015.R)

This script summarizes summarizes ESRI business location data for both the NAICS2 and ABAG6 categories. It scales employment to a total of 4,005,318 jobs from the [REMI regional forecast](https://mtcdrive.app.box.com/file/654134152628). Net incommuters are also removed, using incommute shares to superdistricts to account for non-uniform incommuting rates around the region. 

* Author: [@shimonisrael](https://github.com/shimonisrael)
* Input:
  * [ESRI disaggregate parcel data](https://mtcdrive.app.box.com/file/655868001941)
  * [2012-2016 CTPP Places to Superdistrict Equivalency.xlsx](Employment/Incommute/2012-2016%20CTPP%20Places%20to%20Superdistrict%20Equivalency.xlsx)
  * [ACS 2013-2017 Incommute by Industry.xlsx](Employment/Incommute/ACS%202013-2017%20Incommute%20by%20Industry.xlsx)
  * [REMI regional forecast total](https://mtcdrive.app.box.com/file/654134152628)
* Output:
  * [ESRI 2015 NAICS2 and ABAG6 noin.csv](Employment/ESRI%202015%20NAICS2%20and%20ABAG6%20noin.csv)
  * [ESRI 2015 NAICS2 noincommute.csv](Employment/ESRI%202015%20NAICS2%20noincommute.csv)
* Other files:
  * [NAICS to EMPSIX equivalency](Employment/NAICS_to_EMPSIX.xlsx)

## [6. Group Quarters](Group%20Quarters)

This folder includes supplemental group quarters files. One is [2010 to 2015 manual GQ counts](Group%20Quarters/gq_add_00051015.csv), which includes additional GQ units manually added by MTC staff. Another is [GQ Research Using 2010 Data by GQ Type.xlsx](GQ%20Research%20Using%202010%20Data%20by%20GQ%20Type.xlsx), which includes research into the different types of group quarters, available for 2010 data, but not 2015.   

## [7. School Enrollment](School%20Enrollment)

### [2015_HS_enrollment_TAZ1454.ipynb](School%20Enrollment/2015_HS_enrollment_TAZ1454.ipynb)
### [2015_enrollment_MAZ_v2.2.ipynb](School%20Enrollment/2015_enrollment_MAZ_v2.2.ipynb)

These scripts summarize school enrollment for high school, part-time college, and full-time college at the TAZ level. 

* Author: [@theocharides](https://github.com/theocharides)
* Input: 
  * [PUB_schools.csv](School%20Enrollment/PUB_schools.csv)
  * [school_enrrollment_1516.csv](School%20Enrollment/school_enrollment_1516.csv)
  * [tazData.csv](School%20Enrollment/tazData.csv)
* Output:
  * [tazData_enrollment.csv](School%20Enrollment/tazData_enrollment.csv)

## [7. Workers](Workers)

The number of total employed residents is derived from ACS 2013-2017, Table B23025. The initial distribution of households by household workers comes from Table B08202 for the same period. This household distribution, however, is skewed ([relative to PUMS data](https://github.com/BayAreaMetro/PUMS-Data/tree/master/Analysis/ACS%20PUMS%202013-2017/Worker%20Research)) toward zero-worker households because its universe only includes workers at work during the ACS survey reference week. That is, workers with a job but not at work (e.g., employees who are ill, on vacation, at personal appointments, etc.) are not included here. In addition, household weights from ACS data appear to undercount workers in larger households (with more 3-plus workers), and the person weights appear more accurate. The approach used for reconciling households by number of workers relies on PUMS person weights to correct for worker undercounts. That analysis is [documented in the memo](Documentation/TM%201.5%20TAZ%201454%20Land%20Use%20Documentation%20Memo.docx) and summarized in an [Excel file](Workers/ACSPUMS_WorkerTotals_2013-2017_Comparisons.xlsx) within this folder. 





