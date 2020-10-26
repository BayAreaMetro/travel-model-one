::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunCoreSummaries.bat
::
:: MS-DOS batch file to run core summaries scripts to process output of MTC travel model. 
::
:: lmz (2014 11 12)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: @echo off
setlocal enabledelayedexpansion

:: Overhead
set R_USER=mtcpb
set RDATA=ActiveTransport ActivityPattern AutomobileOwnership CommuteByEmploymentLocation CommuteByIncomeHousehold CommuteByIncomeJob JourneyToWork PerTripTravelTime TimeOfDay TimeOfDay_personsTouring TravelCost TripDistance VehicleMilesTraveled
set CODE_DIR=.\CTRAMP\scripts\core_summaries

:: Model run environment variables
set ITER=3
set TARGET_DIR=%CD%

:: Rename these to standard names
copy %TARGET_DIR%\popsyn\hhFile.*.csv %TARGET_DIR%\popsyn\hhFile.csv
copy %TARGET_DIR%\popsyn\personFile.*.csv %TARGET_DIR%\popsyn\personFile.csv

:: See if we're missing any summaries
if not exist "%TARGET_DIR%\core_summaries" ( mkdir "%TARGET_DIR%\core_summaries" )

set NEED_SUMMARY=0
for %%X in (%RDATA%) DO (
  if not exist "%TARGET_DIR%\core_summaries\%%X.csv"             ( set /a NEED_SUMMARY+=1 )
)
echo Missing %NEED_SUMMARY% summaries in %TARGET_DIR%\core_summaries

:: If we need to, create the core summaries.
if %NEED_SUMMARY% GTR 0 (
  echo %DATE% %TIME% Running summary script for %RUN_NAME%
  
  rem No .Rprofile -- we set the environment variables here.
  echo "%R_HOME%\bin\x64\Rscript.exe"
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\CoreSummaries.R"
  IF %ERRORLEVEL% GTR 0 goto done
  echo %DATE% %TIME% ...Done
  
  rem This will make all the tdes stale
  for %%X in (%RDATA%) DO (
    del "%TARGET_DIR%\core_summaries\%%X.tde"
  )
)
echo.

if not exist core_summaries\TelecommuteByIncome.csv (
  rem A core summary output of people with jobs/work locations who don't do work tours by income quantile
  rem Input : main\wsLocResults_%ITER%.csv, and
  rem         main\personData_%ITER%.csv,
  rem Output: core_summaries\TelecommuteByIncome.csv,
  python CTRAMP\scripts\core_summaries\TelecommuteByIncome.py
  if %ERRORLEVEL% GTR 0 goto done
)

:: convert the avgload5period.csv
if not exist "%TARGET_DIR%\core_summaries\avgload5period.tde" (
  python "%CODE_DIR%\csvToTableauExtract.py" "%TARGET_DIR%\hwy\iter%ITER%" "%TARGET_DIR%\core_summaries" avgload5period.csv
  if %ERRORLEVEL% GTR 0 goto done
  
  echo.
)

:: create trn\trnline.csv
if not exist "%TARGET_DIR%\trn\trnline.csv" (
  call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\ConsolidateLoadedTransit.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

endlocal

:done