
## Data Sources and Notes

Further discussion can be found in [Create 2020 land use file](https://app.asana.com/0/310827677834656/1204790289402872/f) > [Update employment data](https://app.asana.com/0/0/1204885735452348/f)

Based on the below table, the [2020 TAZ-level employment](lodes_wac_employment.csv) is based on the Longitudinal Employer-Household Dynamics (LEHD) [Origin-Destination Employment Statistics (LODES)](https://lehd.ces.census.gov/data/#lodes) Workplace Area Characteristics (WAC) file, summarized to TAZs via [`lodes_wac_to_TAZ.py`](lodes_wac_to_TAZ.py).

| Data Source | Spatial Level | Temporal Level | Data nuances | Data Availability/Cost | Data Location |
| ------------|------------------|----------------|--------------|------------------------|---------------|
| REMI | county | annual | | | 
| National Establishment Time Series (NETS) | | | | We have budget for this but haven't [purchased since 2015](https://mtcdrive.box.com/s/4rz51iqw5wahh18dekhgumj3qe6sk1v2), so it would take time to acquire. | [Box](https://mtcdrive.box.com/s/4rz51iqw5wahh18dekhgumj3qe6sk1v2) |
| ESRI Business Data | point | annual | | Included with our Business Analyst license. 2021 data available. 2022 possibly available; 2023 aggregate data may be available | `M:\Data\BusinessData` |
| Employment Development Department (EDD) - [Current Employment Statistics (CES)](https://data.edd.ca.gov/Industry-Information-/Current-Employment-Statistics-CES-/r4zm-kdcg) | county | monthly | "Current Employment by Industry (CES) data reflect jobs by "place of work." It does not include the self-employed, unpaid family workers, and private household employees. Jobs located in the county or the metropolitan area that pay wages and salaries are counted although workers may live outside the area. Jobs are counted regardless of the number of hours worked. Individuals who hold more than one job (i.e. multiple job holders) may be counted more than once. The employment figure is an estimate of the number of jobs in the area (regardless of the place of residence of the workers) rather than a count of jobs held by the residents of the area." | Free; Jan 1990 through May 2023 but 2022 & 2023 are missing 6 out of 9 Bay Area counties | `M:\Data\ CurrentEmploymentData` |
| Longitudinal Employer-Household Dynamics (LEHD) [Origin-Destination Employment Statistics (LODES)](https://lehd.ces.census.gov/data/#lodes) | census block | annual | LODES provides counts of unemployment insurance covered wage and salary jobs, as reported by state labor market information offices and by OPM (for 2010 onwards). The state data, covering employers in the private sector and state and local government, account for approximately 95 percent of wage and salary jobs. Examples of job types beyond the scope of LEHD earnings records are: the military and other security-related federal agencies, postal workers, some employees at nonprofits and religious institutions, informal workers, and the self-employed. | Available for 2020 and before. | `M:\Data\ Census\LEHD\ Workplace Area Characteristics (WAC)` |
| Bureau of Labor Statistics (BLS) [Quarterly Census of Employment and Wages (QCEW)](https://www.bls.gov/cew/) | county | quarterly | "QCEW produces a comprehensive tabulation of data on the number of establishments, monthly employment and quarterly wages for workers covered by State unemployment insurance (UI) laws and Federal workers covered by the Unemployment Compensation for Federal Employees (UCFE) program.  Establishment counts and wage data are available quarterly and annually. Employment data are available monthly and annually." | Free; through 2022. | `M:\Data\QCEW`|
