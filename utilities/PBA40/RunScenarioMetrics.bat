::
:: This batch file runs a series of scripts to convert direct model output
:: to intermediate summaries, and then rolls up those summaries into a set of SCENARIO metrics.
::
:: It's similar to RunMetrics.bat and uses many of the same scripts
::
:: Stamp the feedback report with the date and time of the model start
echo STARTED METRICS RUN  %DATE% %TIME% >> logs\feedback.rpt

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)

:: Location of the metrics scripts
set CODE_DIR=.\CTRAMP\scripts\metrics
:: Location of the model files
set TARGET_DIR=%CD%

if not exist main\indivTripDataIncome_%ITER%.csv (
  rem Attach income to individual trips.  Uses 2 processes.
  rem Input : main\householdData_%ITER%.csv,
  rem         main\indivTripData_%ITER%.csv, main\jointTripData_%ITER%.csv
  rem Output: main\indivTripDataIncome.csv,  main\JointTripDataIncome.csv
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\joinTripsWithIncome.R"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics (mkdir metrics)

if not exist main\tripsEVinc1.dat (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\(indiv|joint)TripDataIncome_%ITER%.csv
  rem         main\jointTourData_%ITER%.csv
  rem         main\personData_%ITER%.csv
  rem         database\ActiveTimeSkimsDatabase(EA|AM|MD|PM|EV).csv
  rem Output: main\trips(EA|AM|MD|PM|EV)inc[1-4].dat
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem         metrics\unique_active_travelers.csv
  python "%CODE_DIR%\countTrips.py"
  if ERRORLEVEL 2 goto error
)

if not exist main\tripsEVinc1.tpp (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].dat,
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat,
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem Output: main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_2074.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_2064.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)allinc.tpp
  runtpp "%CODE_DIR%\prepAssignIncome.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\transit_times_by_mode_income.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)allinc.tpp,
  rem         skims\trnskm(EA|AM|MD|PM|EV)_(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk|drv).tpp
  rem Output: metrics\transit_times_by_acc_mode_egr.csv,
  rem         metrics\transit_times_by_mode_income.csv
  runtpp "%CODE_DIR%\sumTransitTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist metrics\auto_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp
  rem         nonres\tripsIx(EA|AM|MD|PM|EV).tpp
  rem         nonres\tripsAirPax(EA|AM|MD|PM|EV).tpp
  rem         nonres\tripstrk(EA|AM|MD|PM|EV).tpp
  rem         skims\HWYSKM(EA|AM|MD|PM|EV).tpp
  rem         skims\COM_HWYSKIM(EA|AM|MD|PM|EV).tpp
  rem         CTRAMP\scripts\block\hwyParam.block
  rem Output: metrics\auto_times.csv
  runtpp "%CODE_DIR%\sumAutoTimes.job"
  if ERRORLEVEL 2 goto error
)

python "%CODE_DIR%\scenarioMetrics.py