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

:: set this to the source of your skims and shadow pricing file so we can skip regenerating these
set SKIM_DIR=E:\Model2D-Share\Projects\2020_TM152_TRR_03

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: Set the path
call CTRAMP\runtime\SetPath.bat
:: Which conda am I running?
C:\Windows\System32\where python

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A            set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B            set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C            set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D            set HOST_IP_ADDRESS=192.168.1.209
if %computername%==MODEL3-A            set HOST_IP_ADDRESS=10.164.0.200
if %computername%==MODEL3-B            set HOST_IP_ADDRESS=10.164.0.201
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
:: Step 6: Copy over roadway and transit skim files from SKIM_DIR
::
:: ------------------------------------------------------------------------------------------------------

:: copy skims and shadowPricing
:copy_skims
copy "%SKIM_DIR%\skims\HWYSKM*"           skims
copy "%SKIM_DIR%\skims\COM_HWYSKIM*"      skims
copy "%SKIM_DIR%\skims\trnskm*"           skims
copy "%SKIM_DIR%\skims\nonmotskm.tpp"     skims
copy "%SKIM_DIR%\skims\accessibility.csv" skims
copy "%SKIM_DIR%\main\ShadowPricing_7.csv"   main
copy "%SKIM_DIR%\main\trips_transitHsr*.tpp" main

:: Runtime configuration: setup initial telecommute constants
python CTRAMP\scripts\preprocess\updateTelecommuteConstants.py
if ERRORLEVEL 1 goto done
:: copy over result for use
copy /Y main\telecommute_constants_0%ITER%.csv main\telecommute_constants.csv


:: ------------------------------------------------------------------------------------------------------
::
:: Step 7:  Prepare for iteration 1 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter1

:: Set the iteration parameters - use higher sample share
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.50
set SEED=0

:: Prompt user to set the workplace shadow pricing parameters
@echo off
set /P c=Project Directory updated.  Update workplace shadow pricing parameters and PARAM.properties. press Enter to continue...
@echo on
:: Don't care about the response

:core
rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: If demand models were executed, translate the trip lists to demand matrices
runtpp CTRAMP\scripts\assign\PrepAssign.job
if ERRORLEVEL 2 goto done

:: this is the first time so run it as iter0
set ITER=0

:trnAssignSkim
:: copy a local version for easier restarting
copy CTRAMP\scripts\skims\trnAssign.bat trnAssign_iter%ITER%.bat
call trnAssign_iter%ITER%.bat
if ERRORLEVEL 2 goto done

:: copy the files over for consolidation
copy trn\TransitAssignment.iter0\Subdir0\trnlinkEA_ALL.dbf trn\trnlinkEA_ALLMSA.dbf
copy trn\TransitAssignment.iter0\Subdir0\trnlinkAM_ALL.dbf trn\trnlinkAM_ALLMSA.dbf
copy trn\TransitAssignment.iter0\Subdir0\trnlinkMD_ALL.dbf trn\trnlinkMD_ALLMSA.dbf
copy trn\TransitAssignment.iter0\Subdir0\trnlinkPM_ALL.dbf trn\trnlinkPM_ALLMSA.dbf
copy trn\TransitAssignment.iter0\Subdir0\trnlinkEV_ALL.dbf trn\trnlinkEV_ALLMSA.dbf

set TARGET_DIR=%CD%

:: create trn\trnline.csv
if not exist "trn\trnline.csv" (
  call "%R_HOME%\bin\x64\Rscript.exe" "CTRAMP\scripts\core_summaries\ConsolidateLoadedTransit.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

: cleanup

:: Move all the TP+ printouts to the \logs folder
copy *.prn logs\*.prn

:: Close the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Close Exit

:: Delete all the temporary TP+ printouts and cluster files
del *.prn
del *.script.*
del *.script

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!

python "CTRAMP\scripts\notify_slack.py" "Finished RunThroughTrnAssign.bat in *%MODEL_DIR%*"

if "%COMPUTER_PREFIX%" == "WIN-" (
  
  rem go up a directory and sync model folder to s3
  cd ..
  "C:\Program Files\Amazon\AWSCLI\aws" s3 sync %myfolder% s3://travel-model-runs/%myfolder%
  cd %myfolder%

  rem shutdown
  python "CTRAMP\scripts\notify_slack.py" "Finished RunThroughTrnAssign.bat in *%MODEL_DIR%* - shutting down"
  C:\Windows\System32\shutdown.exe /s
)

:: no errors
goto donedone

:: this is the done for errors
:done
ECHO FINISHED.  

:: if we got here and didn't shutdown -- assume something went wrong
python "CTRAMP\scripts\notify_slack.py" ":exclamation: Error in RunThroughTrnAssign.bat *%MODEL_DIR%*"

:donedone