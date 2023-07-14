# Scripts and data used to create 2023 travel model land use inputs

### [`apply_QCEW_pct_change_to_LODES_2020.py`](apply_QCEW_pct_change_to_LODES_2020.py)

See [Employment data summary](../2020/Employment); based on the available data sources as of July 2023,
the 2023 TAZ employment is based on the 2020 version, 
but modified by applying the percent change in QCEW annual employment from 2020 to 2022, by county and
ABAG6 industry category.

* Input: [../2020/Employment/lodes_wac_employment.csv](../2020/Employment/lodes_wac_employment.csv)
* Output: [employment_2020_with_QCEW_pct_change_applied.csv](employment_2020_with_QCEW_pct_change_applied.csv)
