
# Scripts and data used to create 2020 TAZ data

Note that given that 2020 was the start of the COVID pandemic, the data situation is signifiantly complicated.
Additionally, travel behavior during this year varied widely between February (before lockdowns) and after.
As such, we have not prioritized doing travel modeling for this year, and this 2020 dataset primarily serves
to inform the [2023 TAZ data](../2023/).

## [`ACS 2017-2021 create TAZ data for 2020.R`](ACS%202017-2021%20create%20TAZ%20data%20for%202020.R)

### Input
* **Household- and population-based variables** are tabulated from the 2020 decennial [Demographic and Housing Characteristics File (DHC)](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html) data where available and [ACS 2017-2021](https://www.census.gov/newsroom/press-kits/2022/acs-5-year.html) data otherwise. These data rely on the [Tidycensus R Package](https://walker-data.com/tidycensus/)
    * Todo: link to specific tables
* **[Employment variables](Employment/lodes_wac_employment.csv)** are tabulated from Longitudinal Employer-Household Dynamics (LEHD) Origin-Destination Employment Statistics (LODES) Workplace Area Characteristics (WAC) summarized to TAZs and the six TM1 employment categories via [`lodes_wac_to_TAZ.py`](Employment/lodes_wac_to_TAZ.py).
* **Employed residents**: 
  * Due to pandemic data issues associated with ACS 2020, the number of regional employed residents is derived by taking an average of 2019 and 2021 data, [Table B23025: Employment Status for the population 16 years and over](https://data.census.gov/table?text=B23025&g=050XX00US06001,06013,06041,06055,06075,06081,06085,06095,06097&tid=ACSDT1Y2021.B23025). The initial distribution of households by household workers comes from Table B08202 for the same period.
  * This household distribution, however, is skewed ([relative to PUMS data](https://github.com/BayAreaMetro/PUMS-Data/blob/master/Analysis/ACS%20PUMS%202017-2021/ACS%202017-2021%20PUMS%20HH%20and%20Person%20Worker%20Research.R)) toward zero-worker households because its universe only includes workers at work during the ACS survey reference week. That is, workers with a job but not at work (e.g., employees who are ill, on vacation, at personal appointments, etc.) are not included here.
  * In addition, household weights from ACS data appear to undercount workers in larger households (with more 3-plus workers), and the person weights appear more accurate. The approach used for reconciling households by number of workers relies on PUMS person weights to correct for worker undercounts. That analysis is summarized in an [Excel file](Workers/ACSPUMS_WorkerTotals_2017-2021_Comparisons.xlsx). 
  * Other data, including school enrollment, parking cost information, and acreage come unchanged from the "Census2015" tab of the [Plan Bay Area 2050 TAZ dataset](https://mtcdrive.box.com/s/q6sfcp52bqifb24r9ntvvmg82cj1wdu3).

#### Output:
* [TAZ Land Use File 2020.rdata](TAZ%20Land%20Use%20File%202020.rdata)
* [TAZ1454 2015 District Summary.csv](TAZ1454%202015%20District%20Summary.csv)
* [TAZ1454 2020 District Summary.csv](TAZ1454%202020%20District%20Summary.csv)
* [TAZ1454 2020 Land Use.csv](TAZ1454%202020%20Land%20Use.csv)
* [TAZ1454 2020 Popsim Vars County.csv](TAZ1454%202020%20Popsim%20Vars%20County.csv)
* [TAZ1454 2020 Popsim Vars Region.csv](TAZ1454%202020%20Popsim%20Vars%20Region.csv)
* [TAZ1454 2020 Popsim Vars.csv](TAZ1454%202020%20Popsim%20Vars.csv)
* [TAZ1454_Ethnicity.csv](TAZ1454_Ethnicity.csv)

See also:
  * [Asana task: Create 2020 land use file v1](https://app.asana.com/0/310827677834656/1204790289402872/f)
