::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunModel.bat
::
:: MS-DOS batch file to execute the MTC travel model.  Each of the model steps are sequentially
:: called here.  
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

:: Set the path
call CTRAMP\runtime\SetPath.bat

:: Keep a record of the installed Python packages and their versions
call CTRAMP\runtime\pip_list.bat  > pip_list.log 2>&1

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A            set HOST_IP_ADDRESS=10.1.1.206
if %computername%==MODEL2-B            set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C            set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D            set HOST_IP_ADDRESS=192.168.1.209
if %computername%==MODEL3-A            set HOST_IP_ADDRESS=10.164.0.200
if %computername%==MODEL3-B            set HOST_IP_ADDRESS=10.164.0.201
if %computername%==MODEL3-C            set HOST_IP_ADDRESS=10.164.0.202
if %computername%==MODEL3-D            set HOST_IP_ADDRESS=10.164.0.203
if %computername%==PORMDLPPW01         set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02         set HOST_IP_ADDRESS=172.24.0.102
if %computername%==WIN-FK0E96C8BNI     set HOST_IP_ADDRESS=10.0.0.154
rem if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=10.0.0.70
rem for aws machines, HOST_IP_ADDRESS is set in SetUpModel.bat

:: for AWS, this will be "WIN-"
SET computer_prefix=%computername:~0,4%
set INSTANCE=%COMPUTERNAME%
if "%COMPUTER_PREFIX%" == "WIN-" (
  rem figure out instance
  for /f "delims=" %%I in ('"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command (wget http://169.254.169.254/latest/meta-data/instance-id).Content"') do set INSTANCE=%%I
)

:: Figure out the model year
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

set PROJECT=%myfolder:~11,3%
set FUTURE_ABBR=%myfolder:~15,2%
set FUTURE=X

:: FUTURE ------------------------- make sure FUTURE_ABBR is one of the five [RT,CG,BF] -------------------------
:: The long names are: BaseYear ie 2015, Blueprint aka PBA50, CleanAndGreen, BackToTheFuture, or RisingTidesFallingFortunes

if %PROJECT%==IPA (SET FUTURE=PBA50)
if %PROJECT%==DBP (SET FUTURE=PBA50)
if %PROJECT%==FBP (SET FUTURE=PBA50)
if %PROJECT%==EIR (SET FUTURE=PBA50)
if %PROJECT%==SEN (SET FUTURE=PBA50)
if %PROJECT%==STP (SET FUTURE=PBA50)
if %PROJECT%==NGF (SET FUTURE=PBA50)
if %PROJECT%==TIP (SET FUTURE=PBA50)
if %PROJECT%==TRR (SET FUTURE=PBA50)
if %PROJECT%==PPA (
  if %FUTURE_ABBR%==RT (set FUTURE=RisingTidesFallingFortunes)
  if %FUTURE_ABBR%==CG (set FUTURE=CleanAndGreen)
  if %FUTURE_ABBR%==BF (set FUTURE=BackToTheFuture)
)

echo on
echo FUTURE = %FUTURE%

echo off
if %FUTURE%==X (
  echo on
  echo Couldn't determine FUTURE name.
  echo Make sure the name of the project folder conform to the naming convention.
  exit /b 2
)

:: EN7 ------------------------- make sure EN7 is one of [ENABLED,DISABLED] -------------------------
:: see https://github.com/BayAreaMetro/travel-model-one/tree/tm16_en7/utilities/telecommute
IF "%EN7%"=="" (
  echo EN7 is not configured; set EN7 environment variable to ENABLED or DISABLED
  goto done
)
IF "%EN7%"=="ENABLED" (
  echo EN7 is ENABLED
) ELSE (
  IF "%EN7%"=="DISABLED" (
    echo EN7 is DISABLED
  ) ELSE (
    echo EN7 value is not allowed; set EN7 environment variable to ENABLED or DISABLED
    goto done
  )
)

echo on
echo turn echo back on

python "CTRAMP\scripts\notify_slack.py" "Starting *%MODEL_DIR%*"

set MAXITERATIONS=3
:: --------TrnAssignment Setup -- Standard Configuration
:: CHAMP has dwell  configured for buses (local and premium)
:: CHAMP has access configured for for everything
:: set TRNCONFIG=STANDARD
:: set COMPLEXMODES_DWELL=21 24 27 28 30 70 80 81 83 84 87 88
:: set COMPLEXMODES_ACCESS=21 24 27 28 30 70 80 81 83 84 87 88 110 120 130

:: --------TrnAssignment Setup -- Fast Configuration
:: NOTE the blank ones should have a space
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Create the directory structure
::
:: ------------------------------------------------------------------------------------------------------

:: Create the working directories
mkdir hwy
mkdir trn
mkdir skims
mkdir landuse
mkdir popsyn
mkdir nonres
mkdir main
mkdir logs
mkdir database
mkdir logsums

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\hwy\                 hwy\
copy INPUT\trn\                 trn\
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\
copy INPUT\logsums              logsums\

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Pre-process steps
::
:: ------------------------------------------------------------------------------------------------------

: Pre-Process

:: Runtime configuration: set project directory, auto operating cost, 
:: and synthesized household/population files in the appropriate places
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 goto done

if %PROJECT%==NGF (
    :: In NGF, because of the extensive tolling system, some TAZs may no longer have a free path
    :: This will cause choice models that rely on non-toll distances or times to fail
    :: To avoid this problem, their UECs are updated to use toll distances and times
    :: Choice models that are updated: AutoOwnership.xls, IndividualMandatoryTourFrequency.xls, and TourDepartureAndDuration.xls
   python CTRAMP\scripts\preprocess\updateUECsToUseTollDist.py
   if ERRORLEVEL 1 goto done
)

:: Set the prices in the roadway network (convert csv to dbf first)
python CTRAMP\scripts\preprocess\csvToDbf.py hwy\tolls.csv hwy\tolls.dbf
IF ERRORLEVEL 1 goto done

:: Set the prices in the roadway network
runtpp CTRAMP\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 goto done

:: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
runtpp CTRAMP\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 goto done

:: Create time-of-day-specific 
runtpp CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 goto done

:: Create HSR trip tables to/from Bay Area stations
runtpp CTRAMP\scripts\preprocess\HsrTripGeneration.job
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Build non-motorized level-of-service matrices
::
:: ------------------------------------------------------------------------------------------------------

: Non-Motorized Skims

:: Translate the roadway network into a non-motorized network
runtpp CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job
if ERRORLEVEL 2 goto done

:: Build the skim tables
runtpp CTRAMP\scripts\skims\NonMotorizedSkims.job
if ERRORLEVEL 2 goto done

:: Step 4.5: Build initial transit files
python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 5:  Prepare for Iteration 0
::
:: ------------------------------------------------------------------------------------------------------

: iter0

:: Set the iteration parameters
set ITER=0
set PREV_ITER=0
set WGT=1.0
set PREV_WGT=0.00


:: ------------------------------------------------------------------------------------------------------
::
:: Step 6:  Execute the RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 7:  Prepare for iteration 1 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter1

:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.15
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 8:  Prepare for iteration 2 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter2

:: Set the iteration parameters
set ITER=2
set PREV_ITER=1
set WGT=0.50
set PREV_WGT=0.50
set SAMPLESHARE=0.30
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 9:  Prepare for iteration 3 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter3

:: Set the iteration parameters
set ITER=3
set PREV_ITER=2
set WGT=0.33
set PREV_WGT=0.67
set SAMPLESHARE=0.50
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: Shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: ------------------------------------------------------------------------------------------------------
::
:: Step 11:  Build simplified skim databases
::
:: ------------------------------------------------------------------------------------------------------

: database

runtpp CTRAMP\scripts\database\SkimsDatabase.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 12:  Prepare inputs for EMFAC
::
:: ------------------------------------------------------------------------------------------------------

if not exist hwy\iter%ITER%\avgload5period_vehclasses.csv (
  rem Export network to csv version (with vehicle class volumn columns intact)
  rem Input : hwy\iter%ITER%\avgload5period.net
  rem Output: hwy\iter%ITER%\avgload5period_vehclasses.csv
  runtpp "CTRAMP\scripts\metrics\net2csv_avgload5period.job"
  IF ERRORLEVEL 2 goto error
)

:: Run Prepare EMFAC
call RunPrepareEmfac.bat SB375 WithFreight

:: ------------------------------------------------------------------------------------------------------
::
:: Step 13:  Build destination choice logsums
::
:: ------------------------------------------------------------------------------------------------------

rem for the NextGenFwy Project, we don't need to run logsums
if %PROJECT%==NGF goto core_summaries

: logsums

:: call RunAccessibility
:: if ERRORLEVEL 2 goto done

:: call RunLogsums
:: if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 14:  Core summaries
::
:: ------------------------------------------------------------------------------------------------------

:core_summaries

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

if %PROJECT%==NGF (
   call RunNextGenFwysMetrics.bat
   if ERRORLEVEL 2 goto done
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 17:  Directory clean up
::
:: ------------------------------------------------------------------------------------------------------


:: Extract key files
call extractkeyfiles
c:\windows\system32\Robocopy.exe /E extractor "%M_DIR%\OUTPUT"


: cleanup

:: Move all the TP+ printouts to the \logs folder
copy *.prn logs\*.prn
copy *.log logs\*.log

:: Close the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Close Exit

:: Delete all the temporary TP+ printouts and cluster files
del *.prn
del *.script.*
del *.script

:: run QA/QC for PBA50
call Run_QAQC

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!

python "CTRAMP\scripts\notify_slack.py" "Finished *%MODEL_DIR%*"

if "%COMPUTER_PREFIX%" == "WIN-" (
  
  rem go up a directory and sync model folder to s3
  cd ..
  "C:\Program Files\Amazon\AWSCLI\aws" s3 sync %myfolder% s3://travel-model-runs/%myfolder%
  cd %myfolder%

  rem shutdown
  python "CTRAMP\scripts\notify_slack.py" "Finished *%MODEL_DIR%* - shutting down"
  C:\Windows\System32\shutdown.exe /s
)

:: no errors
goto donedone

:: this is the done for errors
:done
ECHO FINISHED.  

:: if we got here and didn't shutdown -- assume something went wrong
python "CTRAMP\scripts\notify_slack.py" ":exclamation: Error in *%MODEL_DIR%*"

:donedone