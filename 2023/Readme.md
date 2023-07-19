
# Scripts and data used to create travel model land use inputs

## This directory relies on a dataset created for 2020 and then inflated for 2023. As new data become available for ACS in September and December, 2023, these scripts will be updated:

### [ACS 2017-2021 create TAZ data for 2020.R](../2020/ACS%202017-2021%20create%20TAZ%20data%20for%202020.R)

### [Create 2023 TAZ Data from 2020 Vintage.R](Create%202023%20TAZ%20Data%20from%202020%20Vintage.R)

These scripts bring in all inputs and creates 2023 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one)

* Inputs: Input for the 2023 dataset is a mix of different types of variables: 
  * Household- and population-based variables are brought into the [main 2020 script](https://github.com/BayAreaMetro/petrale/blob/main/applications/travel_model_lu_inputs/2020/ACS%202017-2021%20create%20TAZ%20data%20for%202020.R) using 2020 decennial [Demographic and Housing Characteristics File (DHC)](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html) data where available and [ACS 2017-2021](https://www.census.gov/newsroom/press-kits/2022/acs-5-year.html) data otherwise. These data rely on the [Tidycensus R Package](https://walker-data.com/tidycensus/)
  * For employment data, see [`apply_QCEW_pct_change_to_LODES_2020.py`](apply_QCEW_pct_change_to_LODES_2020.py). Also, see [Employment data summary](../2020/Employment); based on the available data sources as of July 2023, the 2023 TAZ employment is based on the 2020 version, but modified by applying the percent change in QCEW annual employment from 2020 to 2022, by county and ABAG6 industry category.
  [../2020/Employment/lodes_wac_employment.csv](../2020/Employment/lodes_wac_employment.csv)
  * Due to data issues associated with ACS 2020, the number of regional employed residents is derived by taking an average of 2019 and 2021 data, Table B23025. The initial distribution of households by household workers comes from Table B08202 for the same period. This household distribution, however, is skewed ([relative to PUMS data](https://github.com/BayAreaMetro/PUMS-Data/blob/master/Analysis/ACS%20PUMS%202017-2021/ACS%202017-2021%20PUMS%20HH%20and%20Person%20Worker%20Research.R)) toward zero-worker households because its universe only includes workers at work during the ACS survey reference week. That is, workers with a job but not at work (e.g., employees who are ill, on vacation, at personal appointments, etc.) are not included here. In addition, household weights from ACS data appear to undercount workers in larger households (with more 3-plus workers), and the person weights appear more accurate. The approach used for reconciling households by number of workers relies on PUMS person weights to correct for worker undercounts. That analysis is summarized in an [Excel file](../2020/Workers/ACSPUMS_WorkerTotals_2017-2021_Comparisons.xlsx). 
  * Because no good data sources exist for all of the 2023 data, population and household data were inflated from 2020 to 2023 values using a ratio of county-level 2023/2020 [population forecasts](https://dof.ca.gov/wp-content/uploads/sites/352/Forecasting/Demographics/Documents/P2A_County_Total.xlsx) from the [California Department of Finance projections](https://dof.ca.gov/forecasting/demographics/projections/). Similarly, employed residents (with their occupations) for 2023 were estimated from the Bay Area regional ratio of [2023](employment_2020_with_QCEW_pct_change_applied.csv)/[2020](../2020/Employment/lodes_wac_employment.csv) jobs.
  * Other data, including school enrollment, parking cost information, and acreage come unchanged from the "Census2015" tab of the [Plan Bay Area 2050 TAZ dataset](https://mtcdrive.box.com/s/q6sfcp52bqifb24r9ntvvmg82cj1wdu3)
* Outputs:
  * [employment_2020_with_QCEW_pct_change_applied.csv](employment_2020_with_QCEW_pct_change_applied.csv)
  * [TAZ1454 2020 Land Use.csv](../2020/TAZ1454%202020%20Land%20Use.csv)
  * [TAZ1454 2023 Land Use.csv](TAZ1454%202023%20Land%20Use.csv)
  * [TAZ1454 2015 District Summary.csv](../2020/TAZ1454%202015%20District%20Summary.csv)
  * [TAZ1454 2020 District Summary.csv](../2020/TAZ1454%202020%20District%20Summary.csv)
  * [TAZ1454 2023 District Summary.csv](TAZ1454%202023%20District%20Summary.csv)
  * [TAZ1454 2020 Popsim Vars.csv](../2020/TAZ1454%202020%20Popsim%20Vars.csv)
  * [TAZ1454 2020 Popsim Vars Region.csv](../2020/TAZ1454%202020%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2020 Popsim Vars County.csv](../2020/TAZ1454%202020%20Popsim%20Vars%20County.csv)
  * [TAZ1454 2023 Popsim Vars.csv](TAZ1454%202023%20Popsim%20Vars.csv)
  * [TAZ1454 2023 Popsim Vars Region.csv](TAZ1454%202023%20Popsim%20Vars%20Region.csv)
  * [TAZ1454 2023 Popsim Vars County.csv](TAZ1454%202023%20Popsim%20Vars%20County.csv)
* See also:
  * [Asana task for 2023 (2020 task is linked in task description)](https://app.asana.com/0/310827677834656/1204829066162039/f)

