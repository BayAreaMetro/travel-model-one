::-----------------------------------------------------------------------------------------------
:: Set environment variable
::-----------------------------------------------------------------------------------------------

:: set environment variables that vary by model runs
:: FUTURE = PBA50, CleanAndGreen, BackToTheFuture, or RisingTidesFallingFortunes
set FUTURE=CleanAndGreen
set M_DIR=M:\Application\Model One\RTP2021\ProjectPerformanceAssessment\TestProjects\2050_TM125_PPA_CG_00

:: set environment variables that vary by users
set BOX_USER=C:\Users\ftsang
set GITHUB_DIR=C:\Users\ftsang\Documents\GitHub\travel-model-one\utilities\RTP\metrics

:: access python (should be the same setup for most users)
set path=%path%;c:\python27

:: set environment variables that are constant across model runs
set ITER=3


::-----------------------------------------------------------------------------------------------
:: The batch file will figure out the model year based on the directory name 
:: These command lines are borrowed from runmodel.bat
::-----------------------------------------------------------------------------------------------
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

:: MODEL YEAR ------------------------- make sure it's numeric --------------------------------
set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul
if %MODEL_YEAR_NUM%==%MODEL_YEAR% (
  echo Numeric model year [%MODEL_YEAR%]
) else (
  echo Couldn't determine numeric model year from project dir [%PROJECT_DIR%]
  echo Guessed [%MODEL_YEAR%]
  exit /b 2
)
:: MODEL YEAR ------------------------- make sure it's in [2000,3000] -------------------------
if %MODEL_YEAR% LSS 2000 (
  echo Model year [%MODEL_YEAR%] is less than 2000
  exit /b 2
)
if %MODEL_YEAR% GTR 3000 (
  echo Model year [%MODEL_YEAR%] is greater than 3000
  exit /b 2
)


::-----------------------------------------------------------------------------------------------
:: Rename old files and rerun the script
:: the current working directory should be the project direcotry on the servers
::-----------------------------------------------------------------------------------------------

:: rename old files
ren "INPUT\metrics\collisionLookup.csv" "collisionLookup_old.csv"
ren "INPUT\metrics\emissionsLookup.csv" "emissionsLookup_old.csv"
ren "INPUT\metrics\nonRecurringDelayLookup.csv" "nonRecurringDelayLookup_old.csv"
 
ren "metrics\vmt_vht_metrics.csv" "vmt_vht_metrics_old.csv"

:: get the correct inputs
copy "%BOX_USER%\Box\Modeling and Surveys\Development\Travel Model 1.5\Model_inputs\_Lookup Tables\collisionLookup.csv" INPUT\metrics\collisionLookup.csv
copy "%BOX_USER%\Box\Modeling and Surveys\Development\Travel Model 1.5\Model_inputs\_Lookup Tables\emissionsLookup.csv" INPUT\metrics\emissionsLookup.csv
copy "%BOX_USER%\Box\Modeling and Surveys\Development\Travel Model 1.5\Model_inputs\_Lookup Tables\nonRecurringDelayLookup.csv" INPUT\metrics\nonRecurringDelayLookup.csv

:: get the correct script
ren CTRAMP\scripts\metrics\hwynet.py hwynet_old.py
copy "%GITHUB_DIR%\hwynet.py" CTRAMP\scripts\metrics\hwynet.py

:: run hwynet.py
call python ".\CTRAMP\scripts\metrics\hwynet.py" --filter %FUTURE% --year %MODEL_YEAR% hwy\iter%ITER%\avgload5period_vehclasses.csv

:: after running the script, copy the input and output to M
:: input
ren "%M_DIR%\INPUT\metrics\collisionLookup.csv" collisionLookup_old.csv
ren "%M_DIR%\INPUT\metrics\emissionsLookup.csv" emissionsLookup_old.csv
ren "%M_DIR%\INPUT\metrics\nonRecurringDelayLookup.csv" nonRecurringDelayLookup_old.csv
copy "INPUT\metrics\collisionLookup.csv" "%M_DIR%\INPUT\metrics\collisionLookup.csv"
copy "INPUT\metrics\emissionsLookup.csv" "%M_DIR%\INPUT\metrics\emissionsLookup.csv"
copy "INPUT\metrics\nonRecurringDelayLookup.csv" "%M_DIR%\INPUT\metrics\nonRecurringDelayLookup.csv"

:: output
ren "%M_DIR%\OUTPUT\metrics\vmt_vht_metrics.csv" vmt_vht_metrics_old.csv
copy .\metrics\vmt_vht_metrics.csv "%M_DIR%\OUTPUT\metrics\vmt_vht_metrics.csv"

REM done!

