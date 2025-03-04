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
mkdir core_summaries
mkdir emfac_prep
mkdir extractor
mkdir metrics
mkdir updated_output

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
set ref_run="2035_TM160_DBP_Plan_08b"
copy ..\%ref_run%\hwy\                 hwy\
copy ..\%ref_run%\trn\                 trn\
copy ..\%ref_run%\landuse\             landuse\
copy ..\%ref_run%\popsyn\              popsyn\
copy ..\%ref_run%\nonres\              nonres\
copy ..\%ref_run%\main\                main\
copy ..\%ref_run%\nonres\              nonres\
copy ..\%ref_run%\logsums\             logsums\
copy ..\%ref_run%\core_summaries\      core_summaries\
copy ..\%ref_run%\database\            database\
copy ..\%ref_run%\metrics\             metrics\
copy ..\%ref_run%\skims\               skims\
copy ..\%ref_run%\updated_output\      updated_output\



:: ------------------------------------------------------------------------------------------------------
::
:: Step 17:  Off-model Calculation (only for 2035 and 2050)
::
:: ------------------------------------------------------------------------------------------------------

if "%runOffModel%"=="Yes" (
  call RunOffmodel
  if ERRORLEVEL 2 goto done                         .
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 18:  Directory clean up
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