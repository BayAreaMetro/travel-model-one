@echo off
setlocal enabledelayedexpansion

set COMBINED_DIR=AcrossScenarios
set RUN_NAME_SET=2010_04_ZZZ 2040_03_116 2040_03_127
set CODE_DIR=C:\Users\lzorn\Documents\Travel Model One Utilities\CoreSummaries
::  2040_03_129

:: save these
set OLD_PATH=%PATH%
set PATH=%CODE_DIR%;%PATH%

set R_HOME=C:\Program Files\R\R-3.1.1
set R_USER=lzorn
set R_LIBS_USER=C:\Users\lzorn\Documents\R\win-library\3.1

set RDATA=ActiveTransport ActivityPattern AutomobileOwnership CommuteByEmploymentLocation CommuteByIncomeHousehold CommuteByIncomeJob JourneyToWork PerTripTravelTime TimeOfDay TimeOfDay_personsTouring TravelCost TripDistance

for %%H in (%RUN_NAME_SET%) DO (

  set RUN_NAME=%%H
  
  rem copy the inputs from the model run directory
  call summarizeScenario.bat
  if %ERRORLEVEL% GTR 0 goto done
)

:: Create the Tablea Data Extracts covering all scenarios
:: First, create the summary dirs list
set SUMMARY_DIRS=%RUN_NAME_SET: =\summary %
set SUMMARY_DIRS=%SUMMARY_DIRS%\summary
echo %SUMMARY_DIRS%

:: Run the conversion script to aggregate all rdata files into a single tde
for %%H in (%RDATA%) DO (
  if not exist "%COMBINED_DIR%\%%H.tde" (
    python "%CODE_DIR%\RdataToTableauExtract.py" %SUMMARY_DIRS% %COMBINED_DIR% %%H.rdata
    if %ERRORLEVEL% GTR 0 goto done
    echo.
  )
)

:: Convert the avgload5period.csv
set MODELFILE_DIRS=%RUN_NAME_SET: =\modelfiles %
set MODELFILE_DIRS=%MODELFILE_DIRS%\modelfiles
echo %MODELFILE_DIRS%

if not exist "%COMBINED_DIR%\avgload5period.tde" (
  python "%CODE_DIR%\csvToTableauExtract.py" %MODELFILE_DIRS% %COMBINED_DIR% avgload5period.csv
)

:: convert the transit files
if not exist "%COMBINED_DIR%\trnline.tde" (
  FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv" --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_wlk.csv
      rem drive -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv" --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_drv_%%J_wlk.csv      
      rem walk -> transit -> drive
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv"  --append %MODELFILE_DIRS% "%COMBINED_DIR%" trnline%%H_wlk_%%J_drv.csv
    )
  )
)
:done

set PATH=%OLD_PATH%
