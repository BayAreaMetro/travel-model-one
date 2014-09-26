@echo off
setlocal enabledelayedexpansion

set COMBINED_DIR=AcrossScenarios
set RUN_NAME_SET=2010_04_ZZZ 2040_03_116 2040_03_127

:: Set to 1 if running from the original model run directory
:: (e.g. subdirs = CTRAMP, database, hwy, INPUT, landuse, etc...)
:: Set to 0 if if running from from results directory
:: (e.g. M:\Application\, subdirs=INPUT,OUTPUT)
set ORIGINAL_RUNDIR=0

IF %USERNAME%==lzorn (
  rem I AM SPECIAL
  set CODE_DIR=C:\Users\lzorn\Documents\Travel Model One Utilities\CoreSummaries
  set R_HOME=C:\Program Files\R\R-3.1.1
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.1
) ELSE (
  set CODE_DIR=D:\files\GitHub\Travel-Model-One-Utilities\CoreSummaries
  set R_HOME=C:\Program Files\R\R-3.1.1
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%USERNAME%\Documents\R\win-library\3.0
)

:: save these
set OLD_PATH=%PATH%
set PATH=%CODE_DIR%;%PATH%

set RDATA=ActiveTransport ActivityPattern AutomobileOwnership CommuteByEmploymentLocation CommuteByIncomeHousehold CommuteByIncomeJob JourneyToWork PerTripTravelTime TimeOfDay TimeOfDay_personsTouring TravelCost TripDistance VehicleMilesTraveled

:: Create the Tablea Data Extracts covering all scenarios
:: First, create the summary dirs list
IF %ORIGINAL_RUNDIR% EQU 1 (
  set SUMMARY_DIRS=%RUN_NAME_SET: =\core_summaries %
  set SUMMARY_DIRS=%SUMMARY_DIRS%\core_summaries
) ELSE (
  set SUMMARY_DIRS=%RUN_NAME_SET: =\OUTPUT\core_summaries %
  set SUMMARY_DIRS=%SUMMARY_DIRS%\OUTPUT\core_summaries
)
echo SUMMARY_DIRS=[%SUMMARY_DIRS%]

:: Run the conversion script to aggregate all rdata files into a single tde
for %%H in (%RDATA%) DO (
  if not exist "%COMBINED_DIR%\%%H.tde" (
    python "%CODE_DIR%\RdataToTableauExtract.py" %SUMMARY_DIRS% "%COMBINED_DIR%" %%H.rdata
    if %ERRORLEVEL% GTR 0 goto done
    echo.
  )
)

:: Convert the avgload5period.csv
IF %ORIGINAL_RUNDIR% EQU 1 (
  set MODELFILE_DIRS=%RUN_NAME_SET: =\hwy\iter3 %
  set MODELFILE_DIRS=%MODELFILE_DIRS%\hwy\iter3
) ELSE (
  set MODELFILE_DIRS=%RUN_NAME_SET: =\OUTPUT %
  set MODELFILE_DIRS=%MODELFILE_DIRS%\OUTPUT
)
echo MODELFILE_DIRS=[%MODELFILE_DIRS%]

if not exist "%COMBINED_DIR%\avgload5period.tde" (
  python "%CODE_DIR%\csvToTableauExtract.py" %MODELFILE_DIRS% "%COMBINED_DIR%" avgload5period.csv
)

:: convert the transit files
IF %ORIGINAL_RUNDIR% EQU 1 (
  set MODELFILE_DIRS=%RUN_NAME_SET: =\trn %
  set MODELFILE_DIRS=%MODELFILE_DIRS%\trn
) ELSE (
  set MODELFILE_DIRS=%RUN_NAME_SET: =\OUTPUT\trn %
  set MODELFILE_DIRS=%MODELFILE_DIRS%\OUTPUT\trn
)
echo MODELFILE_DIRS=[%MODELFILE_DIRS%]

if not exist "%COMBINED_DIR%\trnline.tde" (
  FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_wlk.csv
      rem drive -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv" --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_drv_%%J_wlk.csv      
      rem walk -> transit -> drive
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\reference-transit-modes.csv"  --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_drv.csv
    )
  )
)
:done

set PATH=%OLD_PATH%
