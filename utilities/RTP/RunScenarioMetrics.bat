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
  rem Input : INPUT\params.properties
  rem         main\(indiv|joint)TripDataIncome_%ITER%.csv
  rem         main\jointTourData_%ITER%.csv
  rem         main\personData_%ITER%.csv
  rem         database\ActiveTimeSkimsDatabase(EA|AM|MD|PM|EV).csv
  rem Output: main\trips(EA|AM|MD|PM|EV)inc[1-4].dat
  rem         main\trips[EA|AM|MD|PM|EV]inc[1-4]_poverty[0|1].dat
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem         metrics\unique_active_travelers.csv
  python "%CODE_DIR%\countTrips.py"
  if ERRORLEVEL 2 goto error
)

if not exist main\tripsEV_no_zpv_allinc.tpp (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].dat
  rem         main\trips[EA|AM|MD|PM|EV]inc[1-4]_poverty[0|1].dat
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem Output: main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4].tpp
  rem         main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4]_poverty[0|1].tpp
  rem         main\trips(EA|AM|MD|PM|EV)_2074.tpp
  rem         main\trips(EA|AM|MD|PM|EV)_2064.tpp
  rem         main\trips(EA|AM|MD|PM|EV)allinc.tpp
  runtpp "%CODE_DIR%\prepAssignIncome.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\transit_times_by_mode_income.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : CTRAMP\scripts\block\trnParam.block
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv_allinc.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4]_poverty[0|1].tpp
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv__2074.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv__2064.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv__2064.tpp,
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

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volumn columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "%CODE_DIR%\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\scenario_metrics.csv (
  rem Creates scenario metrics, including travel costs, access to jobs, 
  rem goods movement delay, non-auto mode share, road operating cost and VMT
  rem Input: (travel costs)
  rem          metrics\transit_times_by_mode_income.csv
  rem          metrics\auto_times.csv
  rem          main\householdData_{ITER}.csv
  rem        (access to jobs v2)
  rem          database\TimeSkimsDatabaseAM.csv
  rem          landuse\tazData.csv
  rem          INPUT\metrics\taz1454_epcPBA50plus_2024_02_23.csv
  rem          INPUT\metrics\taz1454_hraPBA50plus_2024_02_23.csv
  rem          INPUT\metrics\taz1454_urban_suburban_rural.csv
  rem        (goods movement delay)
  rem          hwy\iter3\avgload5period_vehclasses.csv
  rem          landuse\tazData.csv
  rem        (non auto mode share)
  rem          main\indivTripData_3.csv
  rem          main\jointTripData_3.csv
  rem        (roads cost and vmt)
  rem          hwy\iter3\avgload5period_vehclasses.csv
  rem   rem Output: metrics\scenario_metrics.csv
  python "%CODE_DIR%\scenarioMetrics.py"
)

:error