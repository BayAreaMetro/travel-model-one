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

:: Set the path
call CTRAMP\runtime\SetPath.bat

:: Set the location of the model scripts
SET BASE_SCRIPTS=CTRAMP\scripts

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-8 Starthide Exit

:: Settings for sending notifications to Slack -- requires a Slack account
set computer_prefix=%computername:~0,4%
set INSTANCE=%COMPUTERNAME%

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


echo on
echo turn echo back on

:: slack notification disabled
:: python "CTRAMP\scripts\notify_slack.py" "Starting *%MODEL_DIR%*"

set MAXITERATIONS=3
:: --------TrnAssignment Setup -- Standard Configuration
:: CHAMP has dwell  configured for buses (local and premium)
:: CHAMP has access configured for everything
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
mkdir nonres\tm15
:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\hwy\                 hwy\
copy INPUT\trn\                 trn\
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\hhFile.%MODEL_YEAR%.csv              		popsyn\hhFile.%MODEL_YEAR%.csv
copy INPUT\popsyn\personFile.%MODEL_YEAR%.csv              	popsyn\personFile.%MODEL_YEAR%.csv
copy INPUT\nonres\tm15\              nonres\tm15\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\
copy INPUT\logsums              logsums\
copy INPUT\warmstart\skims\      skims\
:: Use interim network inputs until the networks are regenerated with all project card updates
copy INPUT\hwy\complete_network_SJQ_externals.net                 hwy\complete_network.net


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

::convert the landuse file from dbf to csv
"%R_HOME%"\RScript.exe --vanilla %BASE_SCRIPTS%\preprocess\create_landuse_csv.R %MODEL_DIR%/landuse/ > create_landuse_csv.log 2>&1
if ERRORLEVEL 1 goto done
:: Preprocess input network to: 
::    1 - fix space issue in CNTYPE
::    2 - add a FEET field based on DISTANCE
runtpp %BASE_SCRIPTS%\preprocess\preprocess_input_net.job
IF ERRORLEVEL 2 goto done

:: Write a batch file with number of zones
runtpp %BASE_SCRIPTS%\preprocess\writeZoneSystems.job
if ERRORLEVEL 2 goto done

::Run the batch file
call zoneSystem.bat

:: Build sequential numberings
runtpp %BASE_SCRIPTS%\preprocess\zone_seq_net_builder.job
if ERRORLEVEL 2 goto done

:: Create all necessary input files based on updated sequential zone numbering
"%PYTHON_PATH%"\python %BASE_SCRIPTS%\preprocess\zone_seq_disseminator.py .
IF ERRORLEVEL 1 goto done

:: Write out the intersection and taz XY
runtpp %BASE_SCRIPTS%\preprocess\taz_densities.job
if ERRORLEVEL 2 goto done

:: Calculate pop and emp density fields density fields. The output csv file is used in the SetCapClass.job script later.
"%PYTHON_PATH%"\python %BASE_SCRIPTS%\preprocess\createTazDensityFile.py 
IF ERRORLEVEL 1 goto done

:: Set the prices in the roadway network (convert csv to dbf first)
python CTRAMP\scripts\preprocess\csvToDbf.py hwy\tolls.csv hwy\tolls.dbf
IF ERRORLEVEL 1 goto done

:: Set the prices in the roadway network
runtpp CTRAMP\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 goto done

:: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
runtpp CTRAMP\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 goto done

:: Create areatype and capclass fields in network
runtpp %BASE_SCRIPTS%\preprocess\SetCapClass.job
if ERRORLEVEL 2 goto done

:: Create time-of-day-specific 
runtpp CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 goto done

:: Create taz networks
runtpp %BASE_SCRIPTS%\preprocess\BuildTazNetworks.job
if ERRORLEVEL 2 goto done


:: Create HSR trip tables to/from Bay Area stations
:: Starting with input trip tables for 2025 (opening year for the Gilroy and San Jose stations), 2029 (opening
:: year for Millbrae and San Francisco stations), and 2040 (future modeled year), the script will assume zero
:: trips before the opening year for the relevant station and interpolate the number of trips afterwards.
:: skip for 2015
::runtpp CTRAMP\scripts\preprocess\HsrTripGeneration.job
::if ERRORLEVEL 2 goto done

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

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4.5: Build initial transit files
::
:: ------------------------------------------------------------------------------------------------------

:: Python path specific to network management procedures
set PYTHONPATH=%USERPROFILE%\Documents\GitHub\NetworkWrangler;%USERPROFILE%\Documents\GitHub\NetworkWrangler\_static

::renumber the duplicated stop ids in the transt line file
python CTRAMP\scripts\preprocess\renumber_duplicated_transit_stops.py
python CTRAMP\scripts\preprocess\list_all_transit_nodes.py
python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 goto done

:: Prepare the highway network for use by the transit network
runtpp %BASE_SCRIPTS%\skims\PrepHwyNet.job
if ERRORLEVEL 2 goto done

:: There are some issues with the transit network creation. Skipping the steps.
goto convert_nonres
:: this is an extra step created to add pnr nodes to the network manually. Skipping.
goto transit_network
:: Create list of PNR lots
runtpp %BASE_SCRIPTS%\preprocess\CreatePnrList.job
if ERRORLEVEL 2 goto done

:transit_network

:: Create the transit networks
runtpp CTRAMP\scripts\skims\BuildTransitNetworks.job
if ERRORLEVEL 2 goto done

:: skip transit skimming and create nonres trip matrices from tm 1.5
goto convert_nonres

call zoneSystem.bat
:: Build the transit skims
runtpp CTRAMP\scripts\skims\TransitSkims.job
if ERRORLEVEL 2 goto done

:convert_nonres

runtpp CTRAMP\scripts\assign\convertTM15Matrices.job
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

:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.01
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: Runtime configuration: update telecommute constants using iter1 results
python CTRAMP\scripts\preprocess\updateTelecommuteConstants.py
if ERRORLEVEL 1 goto done
:: copy over result for use
copy /Y main\telecommute_constants_0%ITER%.csv main\telecommute_constants.csv

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
set SAMPLESHARE=0.05
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: Runtime configuration: update telecommute constants using iter2 results
python CTRAMP\scripts\preprocess\updateTelecommuteConstants.py
if ERRORLEVEL 1 goto done
:: copy over result for use
copy /Y main\telecommute_constants_0%ITER%.csv main\telecommute_constants.csv

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
set SAMPLESHARE=0.20
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: Shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"


:: update telecommute constants one more time just to evaluate the situation
python CTRAMP\scripts\preprocess\updateTelecommuteConstants.py

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

:: slack notification disabled
:: python "CTRAMP\scripts\notify_slack.py" "Finished *%MODEL_DIR%*"

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
:: slack notification disabled
:: python "CTRAMP\scripts\notify_slack.py" ":exclamation: Error in *%MODEL_DIR%*"

:donedone