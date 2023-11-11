::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunPPANetworkQAQC.bat
::
:: MS-DOS batch file to run a dummy assignment for testing projects for PPA.
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:: Set the path
call CTRAMP\runtime\SetPath.bat
:: Which conda am I running?
C:\Windows\System32\where python

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

::  Set the IP address of the host machine which sends tasks to the client machines 
set HOST_IP_ADDRESS=10.6.0.4

:: for AWS, this will be "WIN-"
SET computer_prefix=%computername:~0,4%
set INSTANCE=%COMPUTERNAME%
set MAXITERATIONS=1

:: --------TrnAssignment Setup -- Fast Configuration
:: NOTE the blank ones should have a space
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 

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
copy INPUT\telecommute_constants.csv   main\telecommute_constants.csv
copy INPUT\telecommute_constants.csv   main\telecommute_constants_00.csv


:: ------------------------------------------------------------------------------------------------------
::
:: Preprocessing
::
:: ------------------------------------------------------------------------------------------------------


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

:: ------------------------------------------------------------------------------------------------------
::
:: Non-Motorized Skims
::
:: ------------------------------------------------------------------------------------------------------

:: Translate the roadway network into a non-motorized network
runtpp CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job
if ERRORLEVEL 2 goto done

:: Build the skim tables
runtpp CTRAMP\scripts\skims\NonMotorizedSkims.job
if ERRORLEVEL 2 goto done

:: Step 4.5: Build initial transit files
python CTRAMP\scripts\skims\transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%
if ERRORLEVEL 2 goto done

set ITER=0
set PREV_ITER=0
set WGT=1.0
set PREV_WGT=0.00

:: Assign the demand matrices to the highway network
runtpp CTRAMP\scripts\assign\HwyAssign.job
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Subset taken from trnAssign.bat
::
:: ------------------------------------------------------------------------------------------------------
:trnAssign

set ALLTIMEPERIODS=AM MD PM EV EA
set TRNASSIGNITER=0
set PREVTRNASSIGNITER=NEG1
set PHTDIFFCOND=0.0001
set VOLDIFFCOND=0.005
set TRNASSIGNMODE=NORMAL
set TOTMAXTRNITERS=30
set MAXPATHTIME=240
set PCT=%%
set TRN_ERRORLEVEL=0

:: AverageNetworkVolumes.job uses PREV_ITER=1 for ITER=1
set PREV_TRN_ITER=%PREV_ITER%
IF %ITER% EQU 1 SET PREV_TRN_ITER=0

set ALLTRIPMODES=wlk_com_wlk drv_com_wlk wlk_com_drv wlk_hvy_wlk drv_hvy_wlk wlk_hvy_drv wlk_lrf_wlk drv_lrf_wlk wlk_lrf_drv wlk_exp_wlk drv_exp_wlk wlk_exp_drv wlk_loc_wlk drv_loc_wlk wlk_loc_drv
set ALLTOURMODES=wlk_trn_wlk drv_trn_wlk wlk_trn_drv
IF NOT DEFINED TRNFASTERTHANFREEFLOW (set TRNFASTERTHANFREEFLOW=0)


mkdir trn\TransitAssignment.iter%ITER%
cd trn\TransitAssignment.iter%ITER%

:copyTransitLin
:: bring in the latest transit files -- original if postprocessing
IF %ITER% EQU POSTPROC (
  FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\transitOriginal%%H.lin transit%%H_0.lin
)
IF NOT %ITER% EQU POSTPROC (
  IF %ITER% EQU 0 (
    FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\transitOriginal%%H.lin transit%%H_0.lin
  )
  :: otherwise go from where the previous iteration left off
  IF %ITER% GTR 0 (
    FOR %%H in (%ALLTIMEPERIODS%) DO copy /y ..\TransitAssignment.iter%PREV_TRN_ITER%\transit%%H.lin transit%%H_0.lin
  )
)
FOR %%H in (%ALLTIMEPERIODS%) DO (
  copy /y transit%%H_0.lin transit%%H.lin
  set LASTITER_%%H=0
  set LASTSUBDIR_%%H=Subdir0
)

:: for fast config, only do 1
:: for standard config, keep it short for initial assign
if "%TRNCONFIG%"=="FAST" (set MAXTRNITERS=0)
if "%TRNCONFIG%"=="STANDARD" (
  set MAXTRNITERS=%TOTMAXTRNITERS%
  IF %ITER% EQU 0 (set MAXTRNITERS=4)
)
IF %ITER% EQU POSTPROC (set TRNASSIGNMODE=POSTPROC)
IF %ITER% EQU %MAXITERATIONS% (set PHTDIFFCOND=0)

echo START TRNASSIGN BuildTransitNetworks %DATE% %TIME% >> ..\..\logs\feedback.rpt

:: Prepare the highway network for use by the transit network
runtpp ..\..\CTRAMP\scripts\skims\PrepHwyNet.job
if ERRORLEVEL 2 goto done

:: Create the transit networks
runtpp ..\..\CTRAMP\scripts\skims\BuildTransitNetworks.job
if ERRORLEVEL 2 goto done


:transitSubAssign

:: Assign the transit trips to the transit network
runtpp ..\..\CTRAMP\scripts\assign\TransitAssign_NetworkQAQC.job
if ERRORLEVEL 2 goto done
:: And skim
runtpp ..\..\CTRAMP\scripts\skims\TransitSkims.job
if ERRORLEVEL 2 goto done

:: Copy skims to skim folder and rename
FOR %%A in (%ALLTRIPMODES% %ALLTOURMODES%) DO (
    copy /y trnskmea_%%A.avg.iter%LASTITER_EA%.tpp ..\..\skims\trnskmea_%%A.tpp
    copy /y trnskmam_%%A.avg.iter%LASTITER_AM%.tpp ..\..\skims\trnskmam_%%A.tpp
    copy /y trnskmmd_%%A.avg.iter%LASTITER_MD%.tpp ..\..\skims\trnskmmd_%%A.tpp
    copy /y trnskmpm_%%A.avg.iter%LASTITER_PM%.tpp ..\..\skims\trnskmpm_%%A.tpp
    copy /y trnskmev_%%A.avg.iter%LASTITER_EV%.tpp ..\..\skims\trnskmev_%%A.tpp
)

cd ..
cd ..


:: Move assigned networks to a iteration-specific directory
mkdir hwy\iter%ITER%      

move hwy\LOADEA.net hwy\iter%ITER%\LOADEA.net
move hwy\LOADAM.net hwy\iter%ITER%\LOADAM.net
move hwy\LOADMD.net hwy\iter%ITER%\LOADMD.net
move hwy\LOADPM.net hwy\iter%ITER%\LOADPM.net
move hwy\LOADEV.net hwy\iter%ITER%\LOADEV.net

:: Give the default TP+ variables more intuitive names
runtpp CTRAMP\scripts\feedback\RenameAssignmentVariables.job
if ERRORLEVEL 2 goto done

:: Average the demand for this and the previous iteration and compute a speed estimate for each link 
IF %ITER% GTR 1 (
	runtpp CTRAMP\scripts\feedback\AverageNetworkVolumes.job
	if ERRORLEVEL 2 goto done
	runtpp CTRAMP\scripts\feedback\CalculateSpeeds.job
	if ERRORLEVEL 2 goto done
) ELSE (
	copy hwy\iter%ITER%\LOADEA_renamed.net hwy\iter%ITER%\avgLOADEA.net /Y
	copy hwy\iter%ITER%\LOADAM_renamed.net hwy\iter%ITER%\avgLOADAM.net /Y
	copy hwy\iter%ITER%\LOADMD_renamed.net hwy\iter%ITER%\avgLOADMD.net /Y
	copy hwy\iter%ITER%\LOADPM_renamed.net hwy\iter%ITER%\avgLOADPM.net /Y
	copy hwy\iter%ITER%\LOADEV_renamed.net hwy\iter%ITER%\avgLOADEV.net /Y
)

:: Compute network statistics to measure convergence
runtpp CTRAMP\scripts\feedback\TestNetworkConvergence.job
if ERRORLEVEL 2 goto done

:: Combine the time-of-day-specific networks into a single network
runtpp CTRAMP\scripts\feedback\MergeNetworks.job  
if ERRORLEVEL 2 goto done                

:: Place a copy of the loaded networks into the root \hwy directory for access by the next iteration
copy hwy\iter%ITER%\avgLOADEA.net hwy\avgLOADEA.net /Y
copy hwy\iter%ITER%\avgLOADAM.net hwy\avgLOADAM.net /Y
copy hwy\iter%ITER%\avgLOADMD.net hwy\avgLOADMD.net /Y
copy hwy\iter%ITER%\avgLOADPM.net hwy\avgLOADPM.net /Y
copy hwy\iter%ITER%\avgLOADEV.net hwy\avgLOADEV.net /Y

:: Delete temporary files
del hwy\iter%ITER%\x*.net


:: Create the automobile level-of-service matrices
runtpp CTRAMP\scripts\skims\HwySkims.job
if ERRORLEVEL 2 goto done

:: Create accessibility measures for use by the automobile ownership sub-model
runtpp CTRAMP\scripts\skims\Accessibility.job
if ERRORLEVEL 2 goto done


:: Close the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Close Exit

:success
ECHO FINISHED SUCCESSFULLY!

goto donedone

:: this is the done for errors
:done
ECHO ERRORED OUT!!.  

:donedone