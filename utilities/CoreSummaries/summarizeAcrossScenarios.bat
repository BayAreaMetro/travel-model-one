
@echo on
setlocal enabledelayedexpansion

set COMBINED_DIR=across_rounds_v06
set RUN_NAME_SET=Horizon_Round1\2015_TM151_PPA_09 Horizon_Round1\2050_TM151_FU1_RT_01 Horizon_Round1\2050_TM151_FU1_CG_02 Horizon_Round1\2050_TM151_FU1_BF_02 Horizon_Round2\2050_TM151_FU2_RT_05 Horizon_Round2\2050_TM151_FU2_CG_04 Horizon_Round2\2050_TM151_FU2_BF_04

copy %COMBINED_DIR%\ScenarioKey.csv ScenarioKey.csv

:: Set to 1 if running from the original model run directory
:: (e.g. subdirs = CTRAMP, database, hwy, INPUT, landuse, etc...)
:: Set to 0 if if running from from results directory
:: (e.g. M:\Application\, subdirs=INPUT,OUTPUT)
set ORIGINAL_RUNDIR=0

set CODE_DIR=X:\travel-model-one-master\model-files\scripts\core_summaries

IF %USERNAME%==lzorn (
  rem I AM SPECIAL
  set R_HOME=C:\Program Files\R\R-3.5.1
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.5
) ELSE (
  IF %USERNAME%==ftsang (
      set R_HOME=C:\Program Files\R\R-3.4.4
      set R_USER=%USERNAME%
      set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.4
  ) ELSE (
  set R_HOME=C:\Program Files\R\R-3.5.2
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.5
  )
)


:: save these
set OLD_PATH=%PATH%
set PATH=%CODE_DIR%;%PATH%

set RDATA=ActiveTransport ActivityPattern AutomobileOwnership CommuteByEmploymentLocation CommuteByIncomeHousehold CommuteByIncomeJob JourneyToWork PerTripTravelTime TimeOfDay TimeOfDay_personsTouring TravelCost TripDistance VehicleMilesTraveled
:: set RDATA=JourneyToWork

:: Create the Tablea Data Extracts covering all scenarios
:: First, create the summary dirs list
set SUMMARY_DIRS=%RUN_NAME_SET: =\core_summaries %
set SUMMARY_DIRS=%SUMMARY_DIRS%\core_summaries
:: insert OUTPUT into paths
IF %ORIGINAL_RUNDIR%==0 (
  set SUMMARY_DIRS=%SUMMARY_DIRS:\core_summaries=\OUTPUT\core_summaries%
)
echo Reading Rdata files from SUMMARY_DIRS=
echo   [%SUMMARY_DIRS%]

:: Run the conversion script to aggregate all rdata files into a single tde
for %%H in (%RDATA%) DO (
  if not exist "%COMBINED_DIR%\%%H.tde" (
    python "%CODE_DIR%\RdataToTableauExtract.py" %SUMMARY_DIRS% "%COMBINED_DIR%" %%H.rdata
    if %ERRORLEVEL% GTR 0 goto done
    echo.
  )
)

:: Convert the avgload5period.csv
set HWYFILE_DIRS=%RUN_NAME_SET: =\hwy\iter3 %
set HWYFILE_DIRS=%HWYFILE_DIRS%\hwy\iter3
IF %ORIGINAL_RUNDIR%==0 (
  set HWYFILE_DIRS=%HWYFILE_DIRS:\hwy\iter3=\OUTPUT %
)
echo Reading avgload5period.csv files from HWYFILE_DIRS=
echo   [%HWYFILE_DIRS%]

if not exist "%COMBINED_DIR%\avgload5period.tde" (
  python "%CODE_DIR%\csvToTableauExtract.py" %HWYFILE_DIRS% "%COMBINED_DIR%" avgload5period.csv
)

:: convert the transit files
set TRNFILE_DIRS=%RUN_NAME_SET: =\trn %
set TRNFILE_DIRS=%TRNFILE_DIRS%\trn
IF %ORIGINAL_RUNDIR%==0 (
  set TRNFILE_DIRS=%TRNFILE_DIRS:\trn=\OUTPUT\trn%
)
echo Reading trnline*.csv files from TRNFILE_DIRS=
echo   [%TRNFILE_DIRS%]

if not exist "%COMBINED_DIR%\trnline.tde" (
FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append %TRNFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_wlk.csv
      IF %ERRORLEVEL% GTR 0 goto done
      rem drive -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append %TRNFILE_DIRS% "%COMBINED_DIR%" trnline%%H_drv_%%J_wlk.csv      
      IF %ERRORLEVEL% GTR 0 goto done
      rem walk -> transit -> drive
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv"  --append %TRNFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_drv.csv
      IF %ERRORLEVEL% GTR 0 goto done
    )
  )
)

goto done
if not exist "%COMBINED_DIR%\trnlink.tde" (
  FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink.tde --append --timeperiod %%H --join "%CODE_DIR%\reference-transit-modes.csv" %TRNFILE_DIRS% "%COMBINED_DIR%" trnlink%%H_wlk_%%J_wlk.dbf
      IF %ERRORLEVEL% GTR 0 goto done
      rem drive -> transit -> walk
      python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink.tde --append --timeperiod %%H --join "%CODE_DIR%\reference-transit-modes.csv" %TRNFILE_DIRS% "%COMBINED_DIR%" trnlink%%H_drv_%%J_wlk.dbf
      IF %ERRORLEVEL% GTR 0 goto done
      rem walk -> transit -> drive
      python "%CODE_DIR%\RdataToTableauExtract.py" --output trnlink.tde --append --timeperiod %%H --join "%CODE_DIR%\reference-transit-modes.csv" %TRNFILE_DIRS% "%COMBINED_DIR%" trnlink%%H_wlk_%%J_drv.dbf
      IF %ERRORLEVEL% GTR 0 goto done
    )
  )
)
:done

set PATH=%OLD_PATH%

c:\windows\system32\Robocopy.exe /E "X:\travel-model-one-master\utilities\CoreSummaries\tableau"       %COMBINED_DIR%
