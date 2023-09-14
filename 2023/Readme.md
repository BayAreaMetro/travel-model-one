
# Scripts and data used to create 2023 travel model land use inputs

This directory relies on a [dataset created for 2020](../2020/) which is then inflated for 2023. As new data become available for ACS in September and December, 2023, these scripts will be updated.

##  [`Create 2023 TAZ Data from 2020 Vintage.R`](Create%202023%20TAZ%20Data%20from%202020%20Vintage.R)

This script brings in all inputs and create 2023 input for [PopulationSim](https://github.com/BayAreaMetro/PopulationSim) and [tazdata](https://github.com/BayAreaMetro/modeling-website/wiki/TazData) input for [Travel Model 1.5](https://github.com/BayAreaMetro/travel-model-one).

### Inputs

* **Household- and population-based variables**: Because no good data sources exist for all of the 2023 data, population and household data were inflated from [2020 values](../2020/) to 2023 values using a ratio of county-level 2023/2020 [population forecasts](https://dof.ca.gov/wp-content/uploads/sites/352/Forecasting/Demographics/Documents/P2A_County_Total.xlsx) from the [California Department of Finance projections](https://dof.ca.gov/forecasting/demographics/projections/).
* **[Employment variables](./employment_2020_with_QCEW_pct_change_applied.csv)** are based on the [2020 employment estimates](../2020/Employment/), but modified (via [`apply_QCEW_pct_change_to_LODES_2020.py`](./apply_QCEW_pct_change_to_LODES_2020.py)) by applying the percent change in QCEW annual employment from 2020 to 2022, by county and ABAG6 industry category
* **Employed residents** (with their occupations): Scale the 2020 Employed Residents by the Bay Area regional ratio of [2023 jobs](employment_2020_with_QCEW_pct_change_applied.csv)/[2020 jobs](../2020/Employment/lodes_wac_employment.csv).
  
### Outputs:
* [TAZ1454 2023 Land Use.csv](TAZ1454%202023%20Land%20Use.csv)
* [TAZ1454 2023 District Summary.csv](TAZ1454%202023%20District%20Summary.csv)
* [TAZ1454 2023 Popsim Vars.csv](TAZ1454%202023%20Popsim%20Vars.csv)
* [TAZ1454 2023 Popsim Vars Region.csv](TAZ1454%202023%20Popsim%20Vars%20Region.csv)
* [TAZ1454 2023 Popsim Vars County.csv](TAZ1454%202023%20Popsim%20Vars%20County.csv)

See also:
  * [Asana task: Prepare 2023 land use input](https://app.asana.com/0/0/1204384692879834/f)

