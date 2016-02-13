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

::  Set the IP address of the host machine which sends tasks to the client machines 
set HOST_IP_ADDRESS=192.168.1.206


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
mkdir sgr

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\hwy\                 hwy\
copy INPUT\trn\transit_lines\   trn\
copy INPUT\trn\transit_fares\   trn\ 
copy INPUT\trn\transit_support\ trn\
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\
copy INPUT\sgr\                 sgr\


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

:: Prompt user to start java machines now that the project directory is set
@echo off
set /P c=Project Directory updated.  Please start java processes (main and nodes) and press Enter to continue...
@echo on
:: Don't care about the response

:: Set the prices in the roadway network
runtpp CTRAMP\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 goto done

:: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
runtpp CTRAMP\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 goto done

:: Create time-of-day-specific 
runtpp CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 goto done

:: Add pavement cost adjustment for state of good repair work
runtpp CTRAMP\scripts\preprocess\AddPavementCost.job
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
set SAMPLESHARE=1.00
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 10:  Assign transit trips to the transit network
::
:: ------------------------------------------------------------------------------------------------------

: trnAssign

runtpp CTRAMP\scripts\assign\TransitAssign.job
if ERRORLEVEL 2 goto done


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
:: Step 12:  Build destination choice logsums
::
:: ------------------------------------------------------------------------------------------------------

: logsums

call RunAccessibility
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 13:  Core summaries
::
:: ------------------------------------------------------------------------------------------------------

: core_summaries

call RunCoreSummaries
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 14:  Cobra Metrics
::
:: ------------------------------------------------------------------------------------------------------

call RunMetrics
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 15:  Scenario Metrics
::
:: ------------------------------------------------------------------------------------------------------

call RunScenarioMetrics
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 16:  Directory clean up
::
:: ------------------------------------------------------------------------------------------------------


: cleanup

:: Put the PATH back the way you found it
set PATH=%OLD_PATH%

:: Move all the TP+ printouts to the \logs folder
copy *.prn logs\*.prn

:: Delete all the temporary TP+ printouts and cluster files
del *.prn
del *.script.*
del *.script

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!

:: Complete target and message
:done
ECHO FINISHED.  
