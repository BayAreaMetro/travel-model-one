
setlocal enabledelayedexpansion

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)

:: Location of the github dir
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one-v05
:: Location of the model files
set TARGET_DIR=%CD%
:: Location of the output
if not exist metrics\ITHIM (mkdir metrics\ITHIM)

if not exist updated_output\trips.rdata (
  rem CoreSummaries script
  rem Rename these to standard names
  copy popsyn\hhFile.*.csv     popsyn\hhFile.csv
  copy popsyn\personFile.*.csv popsyn\personFile.csv

  if not exist core_summaries ( mkdir core_summaries )

  set OLD_CODE_DIR=%CODE_DIR%
  set CODE_DIR=%CODE_DIR%\model-files\scripts\core_summaries
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\model-files\scripts\core_summaries\knit_CoreSummaries.R"
  set CODE_DIR=%OLD_CODE_DIR%
  IF %ERRORLEVEL% GTR 0 goto error

  move CoreSummaries.html core_summaries
  move CoreSummaries.md   core_summaries

)

if not exist metrics\ITHIM\percapita_daily_dist_time.csv (
  rem Input:  updated_output\trips.rdata
  rem         updated_output\persons.rdata
  rem Output: metrics\ITHIM\percapita_daily_dist_time.csv
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\utilities\PBA40\ITHIM\knit_PerCapitaDailyTravelDistanceTime.R"
  IF %ERRORLEVEL% GTR 0 goto error

  move PerCapitaDailyTravelDistanceTime.html metrics\ITHIM
  move PerCapitaDailyTravelDistanceTime.md   metrics\ITHIM
)

if not exist main\indivTripDataIncome_%ITER%.csv (
  rem Attach income to individual trips.  Uses 2 processes.
  rem Input : main\householdData_%ITER%.csv,
  rem         main\indivTripData_%ITER%.csv, main\jointTripData_%ITER%.csv
  rem Output: main\indivTripDataIncome.csv,  main\JointTripDataIncome.csv
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\utilities\PBA40\metrics\joinTripsWithIncome.R"
  IF %ERRORLEVEL% GTR 0 goto error
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
  python "%CODE_DIR%\utilities\PBA40\metrics\countTrips.py"
  if ERRORLEVEL 2 goto error
)

:: from metrics
if not exist main\tripsEVinc1.tpp (
  rem Convert trip tables into time/income/mode OD matrices
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].dat,
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat,
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem Output: main\trips(EA|AM|MD|PM|EV)inc[1-4].tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_2074.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)_2064.tpp,
  rem         main\trips(EA|AM|MD|PM|EV)allinc.tpp
  runtpp "%CODE_DIR%\utilities\PBA40\metrics\prepAssignIncome.job"
  IF ERRORLEVEL 2 goto error
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
  runtpp "%CODE_DIR%\utilities\PBA40\metrics\sumAutoTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist metrics\nonmot_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV)inc[1-4].tpp
  rem         trips(EA|AM|MD|PM|EV)_2074.tpp
  rem         trips(EA|AM|MD|PM|EV)_2064.tpp
  rem         skims\nonmotskm.tpp
  rem Output: metrics\nonmot_times.csv
  runtpp "%CODE_DIR%\utilities\PBA40\metrics\sumNonmotTimes.job"
  if ERRORLEVEL 2 goto error
)

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volume columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "%CODE_DIR%\utilities\PBA40\metrics\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\vmt_vht_metrics.csv (
  rem Summarize network links to vmt, vht, and other collision and emissions estimations
  rem Input:  hwy\iter%ITER%\avgload5period_vehclasses.csv
  rem Output: metrics\vmt_vht_metrics.csv
  call python "%CODE_DIR%\utilities\PBA40\metrics\hwynet.py" hwy\iter%ITER%\avgload5period_vehclasses.csv
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv (
  rem Summarizes distance traveled by facility type for autos and trucks, by person and vehicles
  rem Input:  hwy\iter%ITER%\vgload5period_vehclasses.csv
  rem Output: metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv
  call python "%CODE_DIR%\utilities\PBA40\ITHIM\DistanceTraveledByFacilityType_auto.py"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv (
  rem Summarizes distance traveled by facility type for transit, by person miles
  rem Input:  main\trips(EA|AM|MD|PM|EV)allinc.tpp
  rem         skims\trnskm(EA|AM|MD|PM|EV)__(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk|drv)_temp.tpp
  rem Output: metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv
  runtpp "%CODE_DIR%\utilities\PBA40\ITHIM\sumTransitDistance.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\DistanceTraveledByFacilityType_transitveh.csv (
  rem Summarizes distance traveled by facility type for transit, by person miles
  rem Input:  trn\trnline(EA|AM|MD|PM|EV)__(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk|drv).csv
  rem Output: metrics\ITHIM\DistanceTraveledByFacilityType_transitveh.csv
  call python "%CODE_DIR%\utilities\PBA40\ITHIM\DistanceTraveledByFacilityType_transitveh.py"
  IF ERRORLEVEL 2 goto error
)
:error
