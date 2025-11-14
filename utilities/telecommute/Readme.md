
# Telecommuting and Travel Model 1.6.1

In Travel Model 1.6, telecommuting (also known as working from home or WFH) has been made into a simple "submodel" of
the Coordinated Daily Activity Pattern model. For each worker (with a work location), that worker's choice to work from home is made
via a logit model estimated from BATS 2023 data in [estimate_WFH_from_BATS2023.ipynb](estimate_WFH_from_BATS2023.ipynb):
https://github.com/BayAreaMetro/travel-model-one/blob/7dc0bd81ec3c9c4cfa55fe36b38d3c878b7ef79d/utilities/telecommute/estimate_WFH_from_BATS2023.ipynb#L2559-L2586
The model is implemented via the [CoordinatedDailyActivityPattern.xls](https://github.com/BayAreaMetro/travel-model-one/blob/v1.6.1_develop/model-files/model/CoordinatedDailyActivityPattern.xls) UEC.

Since the worker's employment industry is unknown, the worker's employment industry is first picked based upon the the industry mix 
at that worker's work location TAZ.

Additionally, in order to calibrate the overall WFH levels, there are two additional configuration options.
These are specified in the `params.properties` configuration file:
https://github.com/BayAreaMetro/travel-model-one/blob/7dc0bd81ec3c9c4cfa55fe36b38d3c878b7ef79d/utilities/RTP/config_RTP2025/params_2023.properties#L15-L21
The first constant, `WFH_Calibration_constant` is for calibrating overall WFH rates. The second constant, `WFH_Calibration_eastbay_SF` is a
factor that gets multiplied to term used for people who live in the East Bay and work in San Francisco, or the reverse. This term was
scaled up in order to address high volumes across the Bay Bridge and in the BART transbay tube.

These configuration constants are based passed through to [`mtcTourBased.properties`](https://github.com/BayAreaMetro/travel-model-one/blob/7dc0bd81ec3c9c4cfa55fe36b38d3c878b7ef79d/model-files/runtime/mtcTourBased.properties#L152-L156) via [`RuntimeConfiguration.py`](https://github.com/BayAreaMetro/travel-model-one/blob/7dc0bd81ec3c9c4cfa55fe36b38d3c878b7ef79d/model-files/scripts/preprocess/RuntimeConfiguration.py#L323-L325).

The work from home choice (`wfh_choice`) is stored as a person attribute, and written to the 
[disaggregate person output file](https://github.com/BayAreaMetro/modeling-website/wiki/Person).

More information can be found here:
* [Pull request #63: Implement a simple WFH model in CDAP](https://github.com/BayAreaMetro/travel-model-one/pull/63)
* [Asana task: WFH model adjustment & validation](https://app.asana.com/0/0/1205369234942623/f) - internal only.
* [Asana task: Estimate WFH binomial logit model using BATS2023](https://app.asana.com/0/15119358130897/1208621825395379/f) - internal only.
* [Asana task: Implement WFH binomial logit model from BATS2023](https://app.asana.com/0/15119358130897/1208642687328266/f) - internal only.

## Strategy EN7: Expand Commute Trip Reduction Programs at Major Employers

Strategy EN7: Expand Commute Trip Reduction Programs at Major Employers, is implemented as an additional work-from-home
probability boost for workers based on their work place superdistrict: if the auto mode share is greater than the target auto mode share
in that superdistrict *and* the work from home rate in that superdistrict is less than the estimated maximum, then an additional EN7 WFH
probability boost is applied.  

EN7 boosts are enabled by setting the `EN7` environment variable to `ENABLED`; otherwise it should be set to `DISABLED`.

The EN7 WFH boost is configured in [`mtcTourBased.properties`](../../model-files/runtime/mtcTourBased.properties):

https://github.com/BayAreaMetro/travel-model-one/blob/5b1101241f27b95625b590c028911f49e0846cb8/model-files/runtime/mtcTourBased.properties#L284-L292

At the end of each global iteration, the version used for that iteration is saved and 
[`updateTelecommute_forEN7.py`](../../model-files/scripts/preprocess/updateTelecommute_forEN7.py) updates the probability boosts (if needed) in the
properties file.

## Additional Files

* [`TelecommuteData.xlsx`](TelecommuteData.xlsx) - summary of most recent Census ACS related to telecommuting
* [`telecommute.twb`](telecommute.twb) - tableau workbook for dropping into the `main` directory of a completed model run, summarizing commute modes including WFH.
* [`en7_summary_copyToMain.twb`](en7_summary_copyToMain.twb) - tableau workbook for dropping into the `main` directory of a model run, summarizing the effects of EN7 WFH boosts.

## Telecommuting Estimates (Surveys, etc.)

Further discussion can be found in [Identify/evaluate sources of post-pandemic telecommute data](https://app.asana.com/0/1204085012544660/1204893619957853/f).

| Data Source | Telecommute Estimate | Notes | Date of most recent available 
|-------------|----------------------|-------------------------------|-------|
| Census ACS ACS 1-Year Table B08301 Means of Transportation to Work | 33.0% Worked at home as primary "mode" in the reference week (2021); 24.9% Worked at home as primary "mode" in the reference week (2022). <br/> Universe: Workers 16 years and over filtered to *Bay Area* counties who worked in the reference week. See [`TelecommuteData.xlsx`, ACS Summary worksheet](TelecommuteData.xslx) | From [ACS 2021 Subject Definitions](https://www2.census.gov/programs-surveys/acs/tech_docs/subject_definitions/2021_ACSSubjectDefinitions.pdf): "The data on means of transportation to work were derived from answers to Question 32 in 2021 ACS, which was asked of people who indicated in 2021 ACS Question 30a that they worked at some time during the reference week... Means of transportation to work refers to the principal mode of travel or type of conveyance that the worker usually used to get from home to work during the reference week." | 2021; <br/> 2022 release [expected on September 14, 2023](https://www.census.gov/programs-surveys/acs/news/data-releases/2022/release-schedule.html) |
| Bureau of Labor Statistics (BLS) American Time Use Survey | (2022) 33.8% of Employed persons who worked on an average day responded that they worked at home on an average day. (34.8% of Full-time workers and 28.1% of Part-Time workers.) <br/> Universe: workers, 15 years and over. | From the [June 22, 2023 News Release on ATUS 2022 Results](https://www.bls.gov/news.release/pdf/atus.pdf), Table 6 reports "Employed persons working at home, workplace, and time spent working at each location by full- and part-time status and sex, jobholding status, and educational attainment, 2022 annual averages". | 2022 |
| [U.S. Survey of Working Arrangements and Attitudes (SWAA)](https://wfhresearch.com) [time series data](https://wfhresearch.com/wp-content/uploads/2023/07/WFHtimeseries_monthly.xlsx) | Betweeen 32.6%-33.7% for March, April and May 2023.  See [WFH by city Tableau visualization](https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/Survey_of_Working_Arrangements_and_Attitudes/TimeSeries). | Citation: Barrero, Jose Maria, Nicholas Bloom, and Steven J. Davis, 2021. "Why working from home will stick," National Bureau of Economic Research Working Paper 28731. All sheets include this suggested citation information. <br/> From the workbook's README: "Time series of the amount of working from home (percent of full paid days) for: the top 10 largest cities; cities 11 to 50; other small cities and towns; and select top cities. All are 6 month centered moving averages subject to data availability. Because the underlying survey question changed in November 2020, we do a 3-month average for August to October 2020 (plotted as the October data point) and separately compute the 6-month centered moving average for November 2020 and later data. We do not have reliable data on geography prior to August 2020. We define cities using Combined Statistical Areas and obtain the list of major cities by population from: https://en.wikipedia.org/wiki/Combined_statistical_area (accessed in July 2022)." | June 2023 |
| [Census Household Pulse Survey](https://www.census.gov/programs-surveys/household-pulse-survey/data.html) | Only 13%-22% of respondents who answered the question said no. <br/> Universe: Workers in San Francisco-Oakland-Berkeley, CA Metro Area (5 Bay Area counties).  See [Respondent telework table Tableau](https://10ay.online.tableau.com/t/metropolitantransportationcommission/views/CensusHouseholdPulseSurvey_WorkFromHome/Respondentteleworktable)| Survey question (`TWDAYS_RESP`): "In the last 7 days, have you teleworked or worked from home?" The survey is administered frequently in phases, with about 500-1,000 people answering this question in each survey week. | June 2023 |
