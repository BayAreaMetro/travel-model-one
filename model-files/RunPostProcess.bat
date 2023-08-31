::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunModel.bat
::
:: MS-DOS batch file to execute the Alameda / Contra Costa bi-county travel model (BCM). 
:: BCM is derivative of MTC Travel Model 1.5 
:: Each of the model steps are sequentially called here.  
::
:: For complete details, please see http://mtcgis.mtc.ca.gov/foswiki/Main/RunModelBatch.
::
:: dto (2012 02 15) gde (2009 04 22)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------
for /f "delims=[] tokens=2" %%a in ('ping -4 -n 1 %ComputerName% ^| findstr [') do set HOST_IP_ADDRESS=%%a
SET HOST_IP_ADDRESS=localhost
echo HOST_IP_ADDRESS: %HOST_IP_ADDRESS%

:: Set local vs distributed run type. Only local option is implemented for BCM
set RUNTYPE=LOCAL
set MODEL_DIR=%CD%
:: Set the path
call CTRAMP\runtime\SetPath.bat

:: Set the location of the model scripts
SET BASE_SCRIPTS=CTRAMP\scripts

:: Start the cube cluster
Cluster "CTRAMP" 1-%NUMBER_OF_PROCESSORS% Starthide Exit

:: Settings for sending notifications to Slack -- requires a Slack account
set computer_prefix=%computername:~0,4%
set INSTANCE=%COMPUTERNAME%

:: Figure out the model year

set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%
set MODEL_YEAR_SHORT=%MODEL_YEAR:~2,2%
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

set PROJECT=%myfolder:~11,3%

set FUTURE_ABBR=%myfolder:~15,2%
set FUTURE=X

echo %PROJECT%=

:: FUTURE ------------------------- make sure FUTURE_ABBR is one of the five [RT,CG,BF] -------------------------
:: The long names are: BaseYear ie 2015, Blueprint aka PBA50, CleanAndGreen, BackToTheFuture, or RisingTidesFallingFortunes

if %PROJECT%==IPA (SET FUTURE=PBA50)
if %PROJECT%==DBP (SET FUTURE=PBA50)
if %PROJECT%==FBP (SET FUTURE=PBA50)
if %PROJECT%==EIR (SET FUTURE=PBA50)
if %PROJECT%==SEN (SET FUTURE=PBA50)
if %PROJECT%==STP (SET FUTURE=PBA50)
if %PROJECT%==NGF (SET FUTURE=PBA50)
if %PROJECT%==PPA (
  if %FUTURE_ABBR%==RT (set FUTURE=RisingTidesFallingFortunes)
  if %FUTURE_ABBR%==CG (set FUTURE=CleanAndGreen)
  if %FUTURE_ABBR%==BF (set FUTURE=BackToTheFuture)
)

echo %FUTURE%=

set SAMPLESHARE=0.10
set ITER=3

runtpp CTRAMP\scripts\database\SkimsDatabase.job
if ERRORLEVEL 2 goto done
goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 12:  Prepare inputs for EMFAC
::
:: ------------------------------------------------------------------------------------------------------

::skip this step as the MergeNetwork.job already creates the avgload5period_vehclasses.csv (avgload5period.csv)
skip run_emfac
if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volumn columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "CTRAMP\scripts\metrics\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)
: run_emfac
:: Run Prepare EMFAC
call RunPrepareEmfac.bat SB375 WithFreight

:: ------------------------------------------------------------------------------------------------------
::
:: Step 13:  Build destination choice logsums
::
:: ------------------------------------------------------------------------------------------------------

: logsums

:: call RunAccessibility
:: if ERRORLEVEL 2 goto done

call RunLogsums
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 14:  Core summaries
::
:: ------------------------------------------------------------------------------------------------------

: core_summaries

call RunCoreSummaries
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 15:  Cobra Metrics
::
:: ------------------------------------------------------------------------------------------------------

call RunMetrics
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 16:  Scenario Metrics
::
:: ------------------------------------------------------------------------------------------------------

call RunScenarioMetrics
if ERRORLEVEL 2 goto done

:done