::
:: This batch file runs a series of scripts to convert direct model output
:: to intermediate summaries, and then rolls up those summaries into a set of Benefit/Cost metrics.
::
:: Required environment variables:
:: * ITER=the iteration corresponding to the output for which we'll calculate metrics.
::   This should already be set in RunModel.bat
:: * SAMPLESHARE=the sampling used for this iteration
::   This should already be set in RunModel.bat
:: * MODEL_YEAR=the year the model represents.  Used by hwynet.py to lookup relevant emissions,
::   collisions and non-recurring delay factors.
:: * ALL_PROJECT_METRICS_DIR=the location to collect all the metrics files from projects.
::   These will be rolled up into a single dashboard.
::
:: Input files (not including those in CTRAMP)
:: * INPUT\metrics\BC_config.csv
:: * INPUT\params.properties
:: * main\householdData_%ITER%.csv
:: * main\indivTripData_%ITER%.csv
:: * main\jointTripData_%ITER%.csv
:: * nonres\tripsIx(EA|AM|MD|PM|EV).tpp
:: * nonres\tripsAirPax(EA|AM|MD|PM|EV).tpp
:: * nonres\tripstrk(EA|AM|MD|PM|EV).tpp
:: * skims\trnskm(EA|AM|MD|PM|EV)_(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk|drv).tpp
:: * skims\HWYSKM(EA|AM|MD|PM|EV).tpp
:: * skims\COM_HWYSKIM(EA|AM|MD|PM|EV).tpp
:: * skims\nonmotskm.tpp
:: * trn\trnlink[timperiod]_[acc]_[trnmode]_[egr].dbf
:: * hwy\iter%ITER%\avgload5period.net
:: * hwy\avgloadAM.net (just for bus op cost vars, nothing volume specific)
::
:: Stamp the feedback report with the date and time of the model start
echo STARTED METRICS RUN  %DATE% %TIME% >> logs\feedback.rpt

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)
IF defined MODEL_YEAR (echo Using MODEL_YEAR=%MODEL_YEAR%) else (goto error)

set ALL_PROJECT_METRICS_DIR=..\all_project_metrics

:: Location of the metrics scripts
set CODE_DIR=%CD%\CTRAMP\scripts\metrics
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

if not exist metrics\parking_costs_tour.csv (
  rem Tally parking costs from tours and trips, persons (for free parking choice)
  rem and tazdata (for parking costs)
  rem Input: updated_output\tours.rdata, updated_output\trips.rdata
  rem        landuse\tazData.csv
  rem Output: metrics\parking_costs_tour.csv,     metrics\parking_costs_tour_destTaz.csv
  rem         metrics\parking_costs_trip_destTaz, metrics\parking_costs_trip_distBins.csv
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\tallyParking.R"
)

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

if not exist main\tripsAM_no_zpv_allinc.tpp (
  rem Convert person trip tables into time/income/mode OD person trip matrices
  rem Input : main\trips(EA|AM|MD|PM|EV)inc[1-4].dat
  rem         main\trips[EA|AM|MD|PM|EV]inc[1-4]_poverty[0|1].dat
  rem         main\trips(EA|AM|MD|PM|EV)_2074.dat
  rem         main\trips(EA|AM|MD|PM|EV)_2064.dat
  rem Output: main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4].tpp
  rem         main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4]_poverty[0|1].tpp
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv__2074.tpp
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv__2064.tpp
  rem         main\trips(EA|AM|MD|PM|EV)_no_zpv_allinc.tpp
  runtpp "%CODE_DIR%\prepAssignIncome.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\transit_times_by_mode_income.csv (
  rem Reads person trip tables and skims and outputs tallies for trip attributes
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
  rem Input : main\trips(EA|AM|MD|PM|EV)(_no)?_zpv_inc[1-4].tpp
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

if not exist metrics\nonmot_times.csv (
  rem Reads trip tables and skims and outputs tallies for trip attributes
  rem Input : trips(EA|AM|MD|PM|EV)_no_zpv_inc[1-4].tpp
  rem         trips(EA|AM|MD|PM|EV)_no_zpv__2074.tpp
  rem         trips(EA|AM|MD|PM|EV)_no_zpv__2064.tpp
  rem         skims\nonmotskm.tpp
  rem Output: metrics\nonmot_times.csv
  runtpp "%CODE_DIR%\sumNonmotTimes.job"
  if ERRORLEVEL 2 goto error
)

rem Deprecating since inputs have not been refreshed, but also this does not appear to be used. See:
rem   Decide on PBA50+ refresh of CollisionLookupFINAL.xlsx (https://app.asana.com/0/0/1206847050252431/f)
rem   Decide on PBA50+ refresh of nonRecurringDelayLookup.csv (https://app.asana.com/0/0/1206847050252437/f)
rem   Decide on PBA50+ refresh of emissionsLookup.csv (https://app.asana.com/0/0/1206847050252432/f)
rem if not exist metrics\vmt_vht_metrics.csv (
  rem Summarize network links to vmt, vht, and other collision and emissions estimations
  rem Input: hwy\iter%ITER%\avgload5period_vehclasses.csv
  rem Output: metrics\vmt_vht_metrics.csv
  rem call python "%CODE_DIR%\hwynet.py" --filter %FUTURE% --year %MODEL_YEAR% hwy\iter%ITER%\avgload5period_vehclasses.csv
  rem IF ERRORLEVEL 2 goto error
rem )

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

if not exist metrics\transit_crowding.csv (
  rem Summarize transit crowding
  rem Input: \\mainmodel\MainModelShare\travel-model-one-master\utilities\RTP\metrics\transitSeatCap.csv
  rem        trn\trnlink[timeperiod]_ALLMSA.dbf
  rem Output: metrics\transit_crowding_complete.csv
  rem         metrics\transit_crowding.csv
  rem         metrics\transit_crowding.log
  call python "%CODE_DIR%\transitcrowding.py" .
)

if not exist shapefile (
  mkdir shapefile
)
cd shapefile
if not exist network_trn_links.shp (
  rem requires geopandas
  rem Export loaded network to shapefiles
  rem Input: see command
  rem Output: shapefile\network_[links|nodes].shp
  rem         shapefile\network_trn_[links|lines|nodes|route_links].shp
  call python "%CODE_DIR%\cube_to_shapefile.py" --linefile ..\INPUT\trn\transitLines.lin --loadvol_dir ..\trn --transit_crowding ..\metrics\transit_crowding_complete.csv ..\hwy\iter3\avgload5period.net
)

if not exist network_links_TAZ.csv (
  rem requires geopandas
  rem Input: shapefile\network_links.shp
  rem        M:\Data\GIS layers\TM1_taz\bayarea_rtaz1454_rev1_WGS84.shp
  rem Output: shapefile\network_links_TAZ.csv
  call python "%CODE_DIR%\correspond_link_to_TAZ.py" network_links.shp network_links_TAZ.csv
)
cd ..

:topsheet
if not exist metrics\topsheet.csv (
  rem Short summaries for across many runs
  rem Input: tazdata, popsyn files, avgload5period_vehclasses.csv, core_summaries\VehicleMilesTraveled.csv
  rem Output: metrics\topsheet.csv
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\topsheet.R"
)

rem Network Performance Assessment metrics
rem Do not crash on these but try to run them
:NPA_metrics
if not exist metrics\NPA_Metrics_Goal_1A_to_1F.csv (
  call python "%CODE_DIR%\NPA_metrics_Goal_1A_to_1F.py"
)
if not exist metrics\NPA_Metrics_Goal_2.csv (
  call python "%CODE_DIR%\NPA_metrics_Goal_2.py"
)
if not exist metrics\NPA_metrics_Goal_3A_to_3D.csv (
  call python "%CODE_DIR%\NPA_metrics_Goal_3.py"
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




