::
:: This batch file runs a series of scripts to convert direct model output
:: to intermediate summaries, and then rolls up those summaries into a set of Benefit/Cost metrics.
::
:: Required environment variables:
:: * ITER=the iteration corresponding to the output for which we'll calculate metrics.
::   This should already be set in RunModel.bat
:: * SAMPLESHARE=the sampling used for this iteration
::   This should already be set in RunModel.bat
:: * ALL_PROJECT_METRICS_DIR=the location to collect all the metrics files from projects.
::   These will be rolled up into a single dashboard.
::

:: Stamp the feedback report with the date and time of the model start
echo STARTED METRICS RUN  %DATE% %TIME% >> logs\feedback.rpt

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)

set ALL_PROJECT_METRICS_DIR=..\all_project_metrics
:: * Location of R
set R_HOME=C:\Program Files\R\R-3.1.1

:: Location of the metrics scripts
set CODE_DIR=.\CTRAMP\scripts\metrics
:: Location of the model files
set TARGET_DIR=%CD%

:: Required input file:  INPUT\metrics\BC_config.csv
if not exist metrics (mkdir metrics)
copy INPUT\metrics\BC_config.csv metrics


if not exist metrics\autos_owned.csv (
  rem Tally auto ownership from household data
  rem Input: main\householdData_%ITER%.csv
  rem Output: metrics\autos_owned.csv
  python "%CODE_DIR%\tallyAutos.py"
)

if not exist main\indivTripDataIncome_%ITER%.csv (
  rem Attach income to individual trips.  Uses 2 processes.
  rem Input : main\householdData_%ITER%.csv,
  rem         main\indivTripData_%ITER%.csv, main\jointTripData_%ITER%.csv
  rem Output: main\indivTripDataIncome.csv,  main\JointTripDataIncome.csv
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\joinTripsWithIncome.R"
  IF ERRORLEVEL 2 goto error
)

if not exist main\tripsEVinc1.tpp (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\(indiv|joint)TripDataIncome.csv
  rem Output: main\(indiv|join)Trips(EA|AM|MD|PM|EV)inc[1-4].dat,
  rem         main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp,
  rem         main\trips(EA|AM|MD|PM|EV)allinc.tpp
  runtpp "%CODE_DIR%\prepAssignIncome.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics (mkdir metrics)

if not exist metrics\transit_times_by_mode_income_final.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)allinc.tpp, transit skims
  rem Output: metrics\transit_times_by_acc_mode_egr_final.csv,
  rem         metrics\transit_times_by_mode_income_final.csv
  set SKIMTYPE=final
  runtpp "%CODE_DIR%\sumTransitTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist metrics\transit_times_by_mode_income_iter%ITER%.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)allinc.tpp, transit skims
  rem Output: metrics\transit_times_by_acc_mode_egr_iter%ITER%.csv,
  rem         metrics\transit_times_by_mode_income_iter%ITER%.csv
  set SKIMTYPE=iter%ITER%
  runtpp "%CODE_DIR%\sumTransitTimes.job"
  if ERRORLEVEL 2 goto error

  rem these are primary
  copy metrics\transit_times_by_acc_mode_egr_iter%ITER%.csv  metrics\transit_times_by_acc_mode_egr.csv
  copy metrics\transit_times_by_mode_income_iter%ITER%.csv   metrics\transit_times_by_mode_income.csv
)

if not exist metrics\auto_times_final.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp, hwy skims
  rem Output: metrics\auto_times_final.csv
  set SKIMTYPE=final
  runtpp "%CODE_DIR%\sumAutoTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist metrics\auto_times_iter%ITER%.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp, hwy skims
  rem Output: metrics\auto_times_iter%ITER%.csv
  set SKIMTYPE=iter%ITER%
  runtpp "%CODE_DIR%\sumAutoTimes.job"
  if ERRORLEVEL 2 goto error

  rem these are primary
  copy metrics\auto_times_iter%ITER%.csv metrics\auto_times.csv
)

if not exist metrics\nonmot_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV)inc[1-4].tpp, non-mot skims
  rem Output: metrics\nonmot_times.csv
  runtpp "%CODE_DIR%\sumNonmotTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volumn columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "%CODE_DIR%\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\vmt_vht_metrics.csv (
  rem Summarize network links to vmt, vht, and other collision and emissions estimations
  rem Input: hyw\iter%ITER%\avgload5period_vehclasses.csv
  rem Output: metrics\vmt_vht_metrics.csv
  call python "%CODE_DIR%\hwynet.py" hwy\iter%ITER%\avgload5period_vehclasses.csv
  IF ERRORLEVEL 2 goto error
)

if not exist trn\quickboards.xls (
  rem Create quickboards summaries of transit output
  rem Input: trn\trnlink[timperiod]_[acc]_[trnmode]_[egr].dbf, quickboards.ctl
  rem Output: trn\quickboards.xls
  call "%CODE_DIR%\quickboards.bat" "%CODE_DIR%\quickboards.ctl" quickboards.xls
  if ERRORLEVEL 1 goto error
  move quickboards.xls trn
 )

:transit
if not exist metrics\transit_boards_miles.csv (
  rem Summarize quickboards output to pull daily boardings and passenger miles
  rem Input: trn\quickboards.xls
  rem Output: metrics\transit_board_miles.csv
  call python "%CODE_DIR%\transit.py" trn\quickboards.xls
)

if not exist metrics\bus_opcost.csv (
  rem Summarize bus operating costs from pavement
  rem Input: trn\trnlink[am|md|pm|ev|ea]_wlk_com_wlk.dbf,
  rem        hwy\avgloadAM.net,
  rem        INPUT\params.properties,
  rem Output: metrics\bus_opcost.csv
  call python "%CODE_DIR%\bus_opcost.py"
)

if not exist "%ALL_PROJECT_METRICS_DIR%" (mkdir "%ALL_PROJECT_METRICS_DIR%")
python "%CODE_DIR%\RunResults.py" metrics "%ALL_PROJECT_METRICS_DIR%"

:cleanup
move *.PRN logs

:success
echo FINISHED METRICS SUCESSFULLY!
echo ENDED METRICS RUN  %DATE% %TIME% >> logs\feedback.rpt

:error
echo ERRORLEVEL=%ERRORLEVEL%




