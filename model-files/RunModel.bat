::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunModel.bat
::
:: MS-DOS batch file to execute the MTC travel model.  Each of the model steps are sequentially
:: called here.  
::
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
if %computername%==MODEL2-A            set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B            set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C            set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D            set HOST_IP_ADDRESS=192.168.1.209
if %computername%==PORMDLPPW01         set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02         set HOST_IP_ADDRESS=172.24.0.102
if %computername%==WIN-FK0E96C8BNI     set HOST_IP_ADDRESS=10.0.0.154
if %computername%==WRJMDLPPW08         set HOST_IP_ADDRESS=10.0.0.69

rem if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=10.0.0.70
rem for aws machines, HOST_IP_ADDRESS is set in SetUpModel.bat

:: for AWS, this will be "WIN-"
SET computer_prefix=%computername:~0,4%

:: Figure out the model year
::
:: note: %~p0 is the path to the current batch file
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
::set MODEL_YEAR=%myfolder:~0,4%

REM JEF WHY IS THIS HARDCODED?
set MODEL_YEAR=2015

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

set MAXITERATIONS=3
set EN7=DISABLED

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

REM JEF THIS IS NOT IN TM1.6. NEEDS TO BE INCORPORATED FOR FUTURE COMPATIBILITY
SET /A SELECT_COUNTY=6

REM New settings for dynamic zones
set INTERNAL_ZONES=2340
set EXTERNAL_ZONES=36
set TOTAL_ZONES=2376
set INTERNAL_ZONES_SQRD=5475600
set FIRST_EXTERNAL_ZONE=2341

; Bay Area HSR TAZs
set Gilroy_HSR_TAZ=1700
set SanJos_HSR_TAZ=1531
set Millbr_HSR_TAZ=1233
set SanFra_HSR_TAZ=1007


@REM goto resume
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
::
:: Logsums not nececssary for Solano/Napa models
:: mkdir logsums

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\hwy\                 hwy\
copy INPUT\trn\                 trn\
copy INPUT\landuse\             landuse\

rem rename synthetic population files to generic names!
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\
::
:: Logsums not nececssary for Solano/Napa models
:: mkdir logsums
:: copy INPUT\logsums              logsums\

:: @bmp, debugging, start from iter 1
::goto iter1

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Pre-process steps
::
:: ------------------------------------------------------------------------------------------------------

: Pre-Process

python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 (
  echo FAILED: Pre-Process - RuntimeConfiguration.py
  goto done
)

python CTRAMP\scripts\preprocess\csvToDbf.py hwy\tolls.csv hwy\tolls.dbf
if ERRORLEVEL 1 (
  echo FAILED: Pre-Process - csvToDbf.py
  goto done
)

runtpp CTRAMP\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 (
  echo FAILED: Pre-Process - SetTolls.job
  goto done
)

runtpp CTRAMP\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 (
  echo FAILED: Pre-Process - SetHovXferPenalties.job
  goto done
)

runtpp CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 (
  echo FAILED: Pre-Process - CreateFiveHighwayNetworks.job
  goto done
)

runtpp CTRAMP\scripts\preprocess\HsrTripGeneration.job
if ERRORLEVEL 2 (
  echo FAILED: Pre-Process - HsrTripGeneration.job
  goto done
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Build non-motorized level-of-service matrices
::
:: ------------------------------------------------------------------------------------------------------

: Non-Motorized Skims


runtpp CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job
if ERRORLEVEL 2 (
  echo FAILED: Non-Motorized Skims - CreateNonMotorizedNetwork.job
  goto done
)

runtpp CTRAMP\scripts\skims\NonMotorizedSkims.job
if ERRORLEVEL 2 (
  echo FAILED: Non-Motorized Skims - NonMotorizedSkims.job
  goto done
)

python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 (
  echo FAILED: Non-Motorized Skims - transitDwellAccess.py
  goto done
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4.5:  Prepare Synthetic Population
::
:: ------------------------------------------------------------------------------------------------------

:: Run PopSampler
:: JEF 
IF %SELECT_COUNTY% GTR 0 (

  runtpp CTRAMP\scripts\skims\tpp_to_csv.job
  if ERRORLEVEL 2 (
    echo FAILED: PopSampler - tpp_to_csv.job
    goto done
  )

  copy INPUT\popsyn\hhFile.csv popsyn\hhFile.csv
  copy INPUT\popsyn\personFile.csv popsyn\personFile.csv

  "%PYTHON_PATH%\python.exe" CTRAMP\scripts\preprocess\popsampler.PY landuse\sampleRateByTAZ.csv popsyn\hhFile.original.csv popsyn\personFile.original.csv skims\nonmotskm.csv landuse\tazData.csv [6,7]
  if ERRORLEVEL 2 (
    echo FAILED: PopSampler - popsampler.PY
    goto done
  )
  
)

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
:: inside this bat additional debugging messages are needed - TODO
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 (
  echo FAILED: Iteration 0 - RunIteration.bat
  goto done
)

::
:: ------------------------------------------------------------------------------------------------------
::
:: Step 7:  Prepare for iteration 1 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------
@REM :resume

: iter1
:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.15
set SEED=0

:: JEF Added override for sample share if running select county
IF %SELECT_COUNTY% GTR 0 set SAMPLESHARE=1.00

python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RuntimeConfiguration.py
  goto done
)

call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RunIteration.bat
  goto done
)
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

:: JEF Added override for sample share if running select county
IF %SELECT_COUNTY% GTR 0 set SAMPLESHARE=1.00

python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RuntimeConfiguration.py
  goto done
)

call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RunIteration.bat
  goto done
)

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
set SAMPLESHARE=0.5
set SEED=0

:: JEF Added override for sample share if running select county
IF %SELECT_COUNTY% GTR 0 set SAMPLESHARE=1.00

python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RuntimeConfiguration.py
  goto done
)

call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 (
  echo FAILED: Iteration %ITER% - RunIteration.bat
  goto done
)

:: Shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"

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

if "%COMPUTER_PREFIX%" == "WIN-" (
  python "CTRAMP\scripts\notify_slack.py" "Finished *%MODEL_DIR%*"

  rem go up a directory and sync model folder to s3
  cd ..
  "C:\Program Files\Amazon\AWSCLI\aws" s3 sync %myfolder% s3://travel-model-runs/%myfolder%
  cd %myfolder%

  rem shutdown
  python "CTRAMP\scripts\notify_slack.py" "Finished *%MODEL_DIR%* - shutting down"
  C:\Windows\System32\shutdown.exe /s

  rem shutdown takes a while so goto done
  goto donedone
)

:: Complete target and message
:done
ECHO FINISHED.  

:: if we got here and didn't shutdown -- assume something went wrong
if "%COMPUTER_PREFIX%" == "WIN-" (
  python "CTRAMP\scripts\notify_slack.py" ":exclamation: Error in *%MODEL_DIR%*"
)

:donedone