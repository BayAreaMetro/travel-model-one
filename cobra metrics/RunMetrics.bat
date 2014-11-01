::
:: This batch file runs a series of scripts to convert direct model output
:: to intermediate summaries, and then rolls up those summaries into a set of Benefit/Cost metrics.
::
:: Required environment variables:
:: ITER=the iteration corresponding to the output for which we'll calculate metrics.
set ITER=1
:: SAMPLESHARE=the sampling used for this iteration
set SAMPLESHARE=0.15
:: ALL_PROJECT_METRICS_DIR=the location to collect all the metrics files from projects.
:: These will be rolled up into a single dashboard.
set ALL_PROJECT_METRICS_DIR=..

:: Required input file:  INPUT\metrics\BC_config.csv
if not exist metrics (mkdir metrics)
copy INPUT\metrics\BC_config.csv metrics

set PATH=C:\Program Files (x86)\Git\cmd;C:\Python27;C:\Python27\Scripts;C:\Program Files (x86)\Citilabs\CubeVoyager;M:\Software\Quickboards;C:\Program Files (x86)\Java\jdk1.6.0_17\bin
set CLASSPATH=.;C:\Program Files (x86)\Java\jre7\lib\ext\QTJava.zip;M:\Software\Quickboards\quickboards.jar
:: The CODE_DIR is where-ever this batch file is located
set CODE_DIR=%~dp0

if not exist metrics\autos_owned.csv (
  rem Tally auto ownership from household data
  rem Input: main\householdData_%ITER%.csv
  rem Output: metrics\autos_owned.csv
  python %CODE_DIR%\tallyAutos.py
)

if not exist main\IndivTripDataIncome.csv (
  rem Attach income to individual trips
  rem Input : main\IndivTripData_%ITER%.csv,  main\householdData_%ITER%.csv
  rem Output: main\IndivTripDataIncome.csv 
  runtpp %CODE_DIR%\joinIndivIncome.job
  IF ERRORLEVEL 2 goto error
)

if not exist main\JointTripDataIncome.csv (
  rem Attach income to joint trips
  rem Input : main\JointTripData_%ITER%.csv, main\householdData_%ITER%.csv
  rem Output: main\JointTripDataIncome.csv
  runtpp %CODE_DIR%\joinJointIncome.job
  IF ERRORLEVEL 2 goto error
)

if not exist main\tripsEV.tpp (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\(indiv|joint)TripDataIncome.csv
  rem Output: main\IndivTrips(EA|AM|MD|PM|EV)inc[1-4].dat,
  rem         main\Jointrips(EA|AM|MD|PM|EV)inc[1-4].dat
  rem         main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp,
  rem         main\trips(EA|AM|MD|PM|EV).tpp
  runtpp %CODE_DIR%\prepAssignIncome.job
  IF ERRORLEVEL 2 goto error
)

if not exist metrics (mkdir metrics)

if not exist metrics\transit_times_by_mode_income.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV).tpp, transit skims
  rem Output: metrics\transit_times.csv
  runtpp %CODE_DIR%\sumTransitTimes.job
  if ERRORLEVEL 2 goto error
)

if not exist metrics\auto_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV).tpp, hwy skims
  rem Output: metrics\auto_times.csv
  runtpp %CODE_DIR%\sumAutoTimes.job
  if ERRORLEVEL 2 goto error
)

if not exist metrics\nonmot_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV).tpp, hwy skims
  rem Output: metrics\nonmot_times.csv
  runtpp %CODE_DIR%\sumNonmotTimes.job
  if ERRORLEVEL 2 goto error
)

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volumn columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp %CODE_DIR%\net2csv_avgload5period.job
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\vmt_vht_metrics.csv (
  rem Summarize network links to vmt, vht, and other collision and emissions estimations
  rem Input: hyw\iter%ITER%\avgload5period_vehclasses.csv
  rem Output: metrics\vmt_vht_metrics.csv
  call python %CODE_DIR%\hwynet.py hwy\iter%ITER%\avgload5period_vehclasses.csv
  IF ERRORLEVEL 2 goto error
)

if not exist trn\quickboards.xls (
  rem Create quickboards summaries of transit output
  rem Input: trn\trnlink[timperiod]_[acc]_[trnmode]_[egr].dbf, quickboards.ctl
  rem Output: trn\quickboards.xls
  cd trn
  call quickboards %CODE_DIR%\quickboards.ctl quickboards.xls
  cd ..
)

:transit
if not exist metrics\transit_boards_miles.csv (
  rem Summarize quickboards output to pull daily boardings and passenger miles
  rem Input: trn\quickboards.xls
  rem Output: metrics\transit_board_miles.csv
  call python %CODE_DIR%\transit.py trn\quickboards.xls
)

python %CODE_DIR%\RunResults.py metrics %ALL_PROJECT_METRICS_DIR%

:error
echo ERRORLEVEL=%ERRORLEVEL%



