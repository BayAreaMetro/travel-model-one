
setlocal enabledelayedexpansion

IF defined ITER (echo Using ITER=%ITER%) else (goto error)
IF defined SAMPLESHARE (echo Using SAMPLESHARE=%SAMPLESHARE%) else (goto error)
IF defined R_HOME (echo USing R_HOME=%R_HOME%) else (goto error)

:: Location of the github dir
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one-v05
:: Location of the model files
set TARGET_DIR=%CD%
:: Location of the output
if not exist metrics\ITHIM (mkdir metrics\ITHIM)

if not exist updated_output\trips.rdata (
  rem CoreSummaries script
  rem Rename these to standard names
  if not exist popsyn\hhFile.csv     (copy popsyn\hhFile.*.csv     popsyn\hhFile.csv    )
  if not exist popsyn\personFile.csv (copy popsyn\personFile.*.csv popsyn\personFile.csv)

  if not exist core_summaries ( mkdir core_summaries )

  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\model-files\scripts\core_summaries\CoreSummaries.R"
  IF %ERRORLEVEL% GTR 0 goto error
)

if not exist database\IthimSkimsDatabaseAM.csv (
  rem Input:  skims\trnskm(EA|AM|MD|PM|EV)_wlk_trn_wlk.tpp
  rem         skims\trnskm(EA|AM|MD|PM|EV)_wlk_trn_wlk_temp.tpp
  rem         ctramp\scripts\block\hwyparam.block
  rem Output: database\IthimSkimsDatabase(EA|AM|MD|PM|EV).csv
  runtpp "%CODE_DIR%\utilities\RTP\ITHIM\SkimsDatabaseITHIM.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\percapita_daily_dist_time.csv (
  rem Input:  updated_output\trips.rdata
  rem         updated_output\persons.rdata
  rem         database\IthimSkimsDatabase(EA|AM|MD|PM|EV).csv
  rem Output: metrics\ITHIM\percapita_daily_dist_time.csv
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\utilities\RTP\ITHIM\PerCapitaDailyTravelDistanceTime.R"
  IF %ERRORLEVEL% GTR 0 goto error
)

if not exist metrics\ITHIM\PMT_PHTinc1.csv (
  rem Input:  main\trips[EA,AM,MD,PM,EV]inc[1-4].tpp
  rem         skims\HWYSKM[EA,AM,MD,PM,EV].tpp
  rem Output: metrics\ITHIM\PMT_PHTinc[1-4].csv
  runtpp "%CODE_DIR%\utilities\RTP\ITHIM\PMT_PHT_byinc.job"
  IF ERRORLEVEL 2 goto error
)

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volume columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "%CODE_DIR%\utilities\RTP\metrics\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\vmt_vht_metrics.csv (
  rem Summarize network links to vmt, vht, and other collision and emissions estimations
  rem Input:  hwy\iter%ITER%\avgload5period_vehclasses.csv
  rem Output: metrics\vmt_vht_metrics.csv
  call python "%CODE_DIR%\utilities\RTP\metrics\hwynet.py" hwy\iter%ITER%\avgload5period_vehclasses.csv
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\emissions.csv (
  rem Reformats emissions for ITHIM
  rem Input:  metrics\vmt_vht_metrics.csv
  rem Output: metrics\ITHIM\emissions.csv
  call python "%CODE_DIR%\utilities\RTP\ITHIM\reformatEmissions.py"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv (
  rem Summarizes distance traveled by facility type for autos and trucks, by person and vehicles
  rem Input:  hwy\iter%ITER%\vgload5period_vehclasses.csv
  rem Output: metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv
  call python "%CODE_DIR%\utilities\RTP\ITHIM\DistanceTraveledByFacilityType_auto.py"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv (
  rem Summarizes person miles, person hours and vehicle miles traveled for transit vehicles.
  rem Input:  hwy\iter%ITER%\vgload5period_vehclasses.csv
  rem         trn\trnlink(EA|AM|MD|PM|EV)__(wlk|drv)_(com|hvy|exp|lrf|loc)_(wlk|drv).csv
  rem Output: metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv
  call python "%CODE_DIR%\utilities\RTP\ITHIM\DistanceTraveledByFacilityType_transit.py"
  IF ERRORLEVEL 2 goto error
)

if not exist metrics\ITHIM\results.csv (
  rem Rolls up all output files into a single output file for simplicity
  rem Input:  metrics\ITHIM\percapita_daily_dist_time.csv
  rem         metrics\ITHIM\DistanceTraveledByFacilityType_auto+truck.csv
  rem         metrics\ITHIM\DistanceTraveledByFacilityType_transit.csv
  rem Output: metrics\ITHIM\results.csv
  call python "%CODE_DIR%\utilities\RTP\ITHIM\rollupITHIM.py"
)
:error
