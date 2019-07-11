::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::
:: precheck_network
::
:: Utility to generate preliminary skims prior to full model run (subset of precheck_logsums.bat)
:: Designed to be run on a model2-[abcd] machine in a project subdir
:: e.g. L:\RTP2021_PPA\Projects\2308_Valley_Link\2050_TM151_PPA_RT_07_2308_Valley_Link_01\network_precheck
::
:: the Tableau can be viewed in the directory, logsum_diff_map stored in the project directory
:: 
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@echo on

:: add goto here if resuming

:: ------------------------------------------------------------------------------------------------------
::
:: Before running precheck - user input
::
:: ------------------------------------------------------------------------------------------------------


:: Location of BASE MODEL_DIR full run
set MODEL_BASE_DIR=\\MODEL2-C\Model2C-Share\Projects\2050_TM151_PPA_RT_07

:: The location of the project (hwy and trn) to be QA-ed
set PROJ_DIR=L:\RTP2021_PPA\Projects\2308_Valley_Link\2050_TM151_PPA_RT_07_2308_Valley_Link_01


:: ------------------------------------------------------------------------------------------------------
::
:: Step 0: set file location and folder structure
::
:: ------------------------------------------------------------------------------------------------------

:: The location in which we're running the PRECHECK (shortmodel)
:: e.g. %PROJ_DIR%\precheck
mkdir "%PROJ_DIR%\network_precheck"
cd "%PROJ_DIR%\network_precheck"
set MODEL_DIR=%CD%

:: Use this for COMMPATH
mkdir COMMPATH
set COMMPATH=%CD%\COMMPATH
"C:\Program Files\Citilabs\CubeVoyager\Cluster" "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

:: Path details
set PATH=c:\windows\system32;C:\Python27;C:\Python27\Scripts
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files (x86)\Citilabs\CubeVoyager
set PYTHONPATH=X:\NetworkWrangler;X:\NetworkWrangler\_static
set GAWK_PATH=M:\Software\Gawk\bin
SET PATH=%TPP_PATH%;%GAWK_PATH%;%PATH%

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1: bring in the working transit network, highway network and other inputs
::
:: ------------------------------------------------------------------------------------------------------

mkdir logs

:: Stamp the feedback report with the date and time of the model start
echo STARTED NETWORK PRECHECK  %DATE% %TIME% >> logs\feedback.rpt 

robocopy /MIR "%PROJ_DIR%\trn"                    trn
robocopy /MIR "%PROJ_DIR%\hwy"                    hwy
robocopy /MIR "%MODEL_BASE_DIR%\INPUT\landuse"    landuse


:: Use the same CTRAMP as the BASE
mkdir CTRAMP\scripts\assign
robocopy /MIR "%MODEL_BASE_DIR%\CTRAMP"           CTRAMP

:: wait a bit
timeout 5

:: go fewer iterations to save time
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "(gc CTRAMP\scripts\assign\HwyAssign.job) -replace 'parameters maxiters = 1000', 'parameters maxiters = 100' | Out-File -encoding ASCII CTRAMP\scripts\assign\HwyAssign.job"


:: ------------------------------------------------------------------------------------------------------
::
:: Step 2: Pre-process steps
::
:: ------------------------------------------------------------------------------------------------------
:preprocess

:: Set the prices in the roadway network (convert csv to dbf first)
python "CTRAMP\scripts\preprocess\csvToDbf.py" hwy\tolls.csv hwy\tolls.dbf
IF ERRORLEVEL 1 goto done

::   Input: hwy\freeflow.net
::  Output: hwy\withTolls.net
:: Summary: Sets the prices in the roadway network
::          Based on columns TOLLCLASS, DISTANCE
::          Updates columns: TOLL[EA,AM,MD,PM,EV]_[DA,S2,S3,VSM,SML,MED,LRG]
runtpp "CTRAMP\scripts\preprocess\SetTolls.job"
if ERRORLEVEL 2 goto done

::   Input: hwy\withTolls.net
::  Output: hwy\withHovXferPenalties.net (copied back into withTolls.net)
:: Summary: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
::          Based on columns FT, A, B, DISTANCE
::          Updates column: HovXPen
runtpp "CTRAMP\scripts\preprocess\SetHovXferPenalties.job"
if ERRORLEVEL 2 goto done

::   Input: hwy\withTolls.net
::  Output: hwy\avgload[EA,AM,MD,PM,EV].net
:: Summary: Creates time-of-day-specific networks
runtpp "CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job"
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Build non-motorized level-of-service matrices
::
:: ------------------------------------------------------------------------------------------------------

:nonmot

mkdir skims

:: Translate the roadway network into a non-motorized network
runtpp CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job
if ERRORLEVEL 2 goto done

:: Build the skim tables
runtpp CTRAMP\scripts\skims\NonMotorizedSkims.job
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4: HwyAssign with trip tables from base
::
:: ------------------------------------------------------------------------------------------------------
:hwyassign

mkdir main
copy "%MODEL_BASE_DIR%\main\trips??.tpp"         main\
mkdir nonres
copy "%MODEL_BASE_DIR%\nonres\tripsIx??.tpp"     nonres\
copy "%MODEL_BASE_DIR%\nonres\tripsTrk??.tpp"    nonres\
copy "%MODEL_BASE_DIR%\nonres\tripsAirPax??.tpp" nonres\

:: Assign the demand matrices to the highway network
runtpp CTRAMP\scripts\assign\HwyAssign.job
if ERRORLEVEL 2 goto done

echo FINISHED HIGHWAY ASGN  %DATE% %TIME% >> logs\feedback.rpt 

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: HwyAssign with trip tables from base
::
:: ------------------------------------------------------------------------------------------------------
:trnAssignSkim

set ITER=0
set MAXITERATIONS=3
:: --------TrnAssignment Setup -- Fast Configuration
:: NOTE the blank ones should have a space
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 

:: Step 4.5: Build initial transit files
python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 goto done

:: copy a local version for easier restarting
copy CTRAMP\scripts\skims\trnAssign.bat trnAssign_iter%ITER%.bat
call trnAssign_iter%ITER%.bat
if ERRORLEVEL 2 goto done

echo FINISHED TRN ASSIGN SKIMMING  %DATE% %TIME% >> logs\feedback.rpt 

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5:  Build highway skims
::
:: ------------------------------------------------------------------------------------------------------

:hwyskims

:: Create the automobile level-of-service matrices
runtpp CTRAMP\scripts\skims\HwySkims.job
if ERRORLEVEL 2 goto done

:: Create accessibility measures for use by ...
runtpp CTRAMP\scripts\skims\Accessibility.job
if ERRORLEVEL 2 goto done

:: Add time step to the feedback report file
echo FINISHED HIGHWAY SKIMMING  %DATE% %TIME% >> logs\feedback.rpt 

:: Complete
goto victory

:done
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem Failure
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
goto end

:victory
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem Victory
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
rem ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"C:\Program Files\Citilabs\CubeVoyager\Cluster" "%COMMPATH%\CTRAMP" 1-48 Close Exit

:end
:: Last Step:  Stamp the time of completion to the feedback report file
echo FINISHED NETWORK PRECHECK  %DATE% %TIME% >> logs\feedback.rpt 
