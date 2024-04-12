::
:: This batch script runs additional scripts to generate metrics for the NextGenFwys study.
::

:: Stamp the feedback report with the date and time of the model start
echo STARTED NGFS METRICS  %DATE% %TIME% >> logs\feedback.rpt

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)
IF defined MODEL_YEAR (echo Using MODEL_YEAR=%MODEL_YEAR%) else (goto error)

:: Location of the metrics scripts
set CODE_DIR=.\CTRAMP\scripts\metrics
:: for testing
:: set CODE_DIR=E:\GitHub\travel-model-one\utilities\NextGenFwys\metrics

if not exist %CODE_DIR%\extract_cost_skims.job (
   copy X:\travel-model-one-master\utilities\NextGenFwys\metrics\extract_cost_skims.job
)

if not exist %CODE_DIR%\travel-cost-by-income-driving-households.r (
   copy X:\travel-model-one-master\utilities\NextGenFwys\metrics\travel-cost-by-income-driving-households.r
)

:: Location of the model files
set TARGET_DIR=%CD%

if not exist skims\trnskm_cost_ev.csv (
  rem Extract detailed cost skims
  rem Input:  roadway and transit skims
  rem Output: skims\HWYSKM_cost_[EA,AM,MD,PM,EV].csv
  rem         skims\trnskm_cost_[EA,AM,MD,PM,EV].csv
  runtpp "%CODE_DIR%\extract_cost_skims.job"
  IF ERRORLEVEL 2 goto error
)

if not exist core_summaries\travel-cost-hhldtraveltype.csv (
  rem Summarize transportation costs by income, home_taz, hhld_travel type
  rem Input:  updated_output\trips.rdata
  rem         skims\HWYSKM_cost_[EA,AM,MD,PM,EV].csv
  rem         skims\trnskm_cost_[EA,AM,MD,PM,EV].csv
  rem Output: core_summaries\travel-cost-hhldtraveltype.csv
  rem         core_summaries\travel-cost-hhldtraveltype-[auto,transit].csv
  rem         updated_output\trips_with_detailed_cost.rdata
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\travel-cost-by-income-driving-households.r"
  IF ERRORLEVEL 2 goto error
)

:success
echo FINISHED RunNextGenFwysMetrics successfully!
echo ENDED NGFS METRICS  %DATE% %TIME% >> logs\feedback.rpt

:error
echo ERRORLEVEL=%ERRORLEVEL%
