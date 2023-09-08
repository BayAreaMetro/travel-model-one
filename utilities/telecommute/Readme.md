
# Telecommuting and Travel Model 1.6

In Travel Model 1.6, telecommuting (also known as working from home or WFH) has been made into a simple "submodel" of
the Coordinated Daily Activity Pattern model. For each worker (with a work location), that worker's choice to work from home is made
via a linear function based on the log of the person's household income; the model specification is additionally segmented
by home county and employment industry. These models were estimated using [post-pandemic PUMS data](https://mtcdrive.box.com/s/0vux1bzeinjz7gtvazn0wzb57p7zqpt7).

Since the worker's employment industry is unknown, the worker's work-from-home probability is
the weighted average of employment industry jobs at that worker's work location TAZ.

The work from home choice (`wfh_choice`) is stored as a person attribute, and written to the 
[disaggregate person output file](WFH model adjustment & validation).

More information can be found here:
* [Pull request #63: Implement a simple WFH model in CDAP](https://github.com/BayAreaMetro/travel-model-one/pull/63)
* [Asana task: WFH model adjustment & validation](https://app.asana.com/0/0/1205369234942623/f) - this is internal only.

## Files

* [`TelecommuteData.xlsx`](TelecommuteData.xlsx) - summary of most recent Census ACS related to telecommuting
* [`telecommute.twb`](telecommute.twb) - tableau workbook for dropping into the `main` directory of a completed model run, summarizing commute modes including WFH.

## Telecommuting Estimates (Surveys, etc.)

Further discussion can be found in [Identify/evaluate sources of post-pandemic telecommute data](https://app.asana.com/0/1204085012544660/1204893619957853/f).

| Data Source | Telecommute Estimate | Notes | Date of most recent available 
|-------------|----------------------|-------------------------------|-------|
| Census ACS ACS 1-Year Table B08301 Means of Transportation to Work | 33.0% Worked at home as primary "mode" in the reference week. <br/> Universe: Workers 16 years and over filtered to *Bay Area* counties who worked in the reference week. See [`TelecommuteData.xlsx`, ACS Summary worksheet](TelecommuteData.xslx) | From [ACS 2021 Subject Definitions](https://www2.census.gov/programs-surveys/acs/tech_docs/subject_definitions/2021_ACSSubjectDefinitions.pdf): "The data on means of transportation to work were derived from answers to Question 32 in 2021 ACS, which was asked of people who indicated in 2021 ACS Question 30a that they worked at some time during the reference week... Means of transportation to work refers to the principal mode of travel or type of conveyance that the worker usually used to get from home to work during the reference week." | 2021; <br/> 2022 release [expected on September 14, 2023](https://www.census.gov/programs-surveys/acs/news/data-releases/2022/release-schedule.html) |
| Bureau of Labor Statistics (BLS) American Time Use Survey | 33.8% of Employed persons who worked on an average day responded that they worked at home on an average day. (34.8% of Full-time workers and 28.1% of Part-Time workers.) <br/> Universe: workers, 15 years and over. | From the [June 22, 2023 News Release on ATUS 2022 Results](https://www.bls.gov/news.release/pdf/atus.pdf), Table 6 reports "Employed persons working at home, workplace, and time spent working at each location by full- and part-time status and sex, jobholding status, and educational attainment, 2022 annual averages". | 2022 |
| [U.S. Survey of Working Arrangements and Attitudes (SWAA)](https://wfhresearch.com) [time series data](https://wfhresearch.com/wp-content/uploads/2023/07/WFHtimeseries_monthly.xlsx) | Betweeen 32.6%-33.7% for March, April and May 2023.  See [WFH by city Tableau visualization](https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/Survey_of_Working_Arrangements_and_Attitudes/TimeSeries). | Citation: Barrero, Jose Maria, Nicholas Bloom, and Steven J. Davis, 2021. "Why working from home will stick," National Bureau of Economic Research Working Paper 28731. All sheets include this suggested citation information. <br/> From the workbook's README: "Time series of the amount of working from home (percent of full paid days) for: the top 10 largest cities; cities 11 to 50; other small cities and towns; and select top cities. All are 6 month centered moving averages subject to data availability. Because the underlying survey question changed in November 2020, we do a 3-month average for August to October 2020 (plotted as the October data point) and separately compute the 6-month centered moving average for November 2020 and later data. We do not have reliable data on geography prior to August 2020. We define cities using Combined Statistical Areas and obtain the list of major cities by population from: https://en.wikipedia.org/wiki/Combined_statistical_area (accessed in July 2022)." | June 2023 |
| [Census Household Pulse Survey](https://www.census.gov/programs-surveys/household-pulse-survey/data.html) | Only 13%-22% of respondents who answered the question said no. <br/> Universe: Workers in San Francisco-Oakland-Berkeley, CA Metro Area (5 Bay Area counties).  See [Respondent telework table Tableau](https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/CensusHouseholdPulseSurvey_WorkFromHome/Respondentteleworktable)| Survey question (`TWDAYS_RESP`): "In the last 7 days, have you teleworked or worked from home?" The survey is administered frequently in phases, with about 500-1,000 people answering this question in each survey week. | June 2023 |