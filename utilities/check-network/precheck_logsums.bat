::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::
:: check_logsums
::
:: utility to generate preliminary logsum diff maps prior to full model run
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: ------------------------------------------------------------------------------------------------------
::
:: Step 0: set file location and folder structure
::
:: ------------------------------------------------------------------------------------------------------


:: Location of travel-model-one local repo
set CODE_DIR=X:\travel-model-one-1.5.1

:: The location of the project (hwy and trn) to be QA-ed
set PROJ_DIR=Z:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects\1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3_01

:: Location of BASE MODEL_DIR
set MODEL_BASE_DIR=\\MODEL2-A\Model2A-Share\Projects\2050_TM151_PPA_RT_00

:: this is where the results will be saved
set LOGSUMS_CHECK_DIR=%PROJ_DIR%\logsum_precheck

:: Path details
set PATH=%PATH%;C:\Python27;C:\Python27\Scripts
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files (x86)\Citilabs\CubeVoyager
set PYTHONPATH=%PYTHONPATH%;X:\NetworkWrangler;X:\NetworkWrangler\_static
set GAWK_PATH=Z:\Software\Gawk\bin
SET PATH=%TPP_PATH%;%GAWK_PATH%;%PATH%

:: Step 0: create the logsums check dir and go to it
if not exist "%LOGSUMS_CHECK_DIR%" (
  mkdir "%LOGSUMS_CHECK_DIR%"
)
cd "%LOGSUMS_CHECK_DIR%"

:: used by BuildTransitNetworks.job
set MODEL_DIR=%LOGSUMS_CHECK_DIR%

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1: bring in the working transit network, highway network and other inputs
::
:: ------------------------------------------------------------------------------------------------------

mkdir trn
mkdir hwy
mkdir logsums
mkdir landuse
mkdir popsyn
mkdir main
mkdir skims
mkdir logs
mkdir INPUT

:: Stamp the feedback report with the date and time of the model start
echo STARTED LOGSUMS PRECHECK  %DATE% %TIME% >> logs\feedback.rpt 

copy "%PROJ_DIR%\trn"                                                    trn\
copy "%PROJ_DIR%\hwy\tolls.csv"                                          hwy\
copy "%PROJ_DIR%\hwy\freeflow.net"                                       hwy\
copy "%MODEL_BASE_DIR%\INPUT\logsums\*"                                  logsums\
copy "%MODEL_BASE_DIR%\INPUT\landuse\*"                                  landuse\
copy "%MODEL_BASE_DIR%\popsyn\hhFile.csv"                                popsyn\hhFile.csv
copy "%MODEL_BASE_DIR%\popsyn\personFile.csv"                            popsyn\personFile.csv
copy "%MODEL_BASE_DIR%\INPUT\warmstart\main\*"                           main\
robocopy /MIR "%CODE_DIR%\model-files"                                   CTRAMP

:: copy in custom CTRAMP
:: used by runtimeconfiguration.py and then by logsums java processes
copy /y "%MODEL_BASE_DIR%\CTRAMP\scripts\block\hwyparam.block"  "CTRAMP\scripts\block"

:: updated script that is in master but not in 1.5.1 yet
copy /y "X:\travel-model-one-master\model-files\scripts\preprocess\RuntimeConfiguration.py"  "CTRAMP\scripts\preprocess\RuntimeConfiguration.py"

:: copy in params.properties
:: used by runtimeconfiguration.py and then by logsums java processes
copy "%MODEL_BASE_DIR%\INPUT\params.properties"      INPUT\params.properties

:: copy in shadow price from base - double check that this step is necessary
:: used by logsums java processes
copy "%MODEL_BASE_DIR%\main\ShadowPricing_7.csv"     main\ShadowPricing_7.csv

:: copy household and population files from base
:: used by AccessibilityMarkets.R
copy "%MODEL_BASE_DIR%\main\householdData_3.csv"     main\householdData_3.csv
copy "%MODEL_BASE_DIR%\main\personData_3.csv"        main\personData_3.csv


:: Figure out the model year
:: used by logsums.properties
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



:: ------------------------------------------------------------------------------------------------------
::
:: Step 2: build the transit network
::
:: ------------------------------------------------------------------------------------------------------

:: Set the prices in the roadway network (convert csv to dbf first)
python "%CODE_DIR%\model-files\scripts\preprocess\csvToDbf.py" hwy\tolls.csv hwy\tolls.dbf
IF ERRORLEVEL 1 goto done

:: == Assumes this script is an input ==
::   Input: hwy\freeflow.net
::  Output: hwy\withTolls.net
:: Summary: Sets the prices in the roadway network
::          Based on columns TOLLCLASS, DISTANCE
::          Updates columns: TOLL[EA,AM,MD,PM,EV]_[DA,S2,S3,VSM,SML,MED,LRG]
runtpp "%CODE_DIR%\model-files\scripts\preprocess\SetTolls.job"
if ERRORLEVEL 2 goto done

::   Input: hwy\withTolls.net
::  Output: hwy\withHovXferPenalties.net (copied back into withTolls.net)
:: Summary: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
::          Based on columns FT, A, B, DISTANCE
::          Updates column: HovXPen
runtpp "%CODE_DIR%\model-files\scripts\preprocess\SetHovXferPenalties.job"
if ERRORLEVEL 2 goto done

::   Input: hwy\withTolls.net
::  Output: hwy\avgload[EA,AM,MD,PM,EV].net
:: Summary: Creates time-of-day-specific networks
:: == use input version if available ==
if exist "%PROJ_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job" (
  runtpp "%PROJ_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job"
)
if not exist "%PROJ_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job" (
  runtpp "%CODE_DIR%\model-files\scripts\preprocess\CreateFiveHighwayNetworks.job"
)
if ERRORLEVEL 2 goto done

::   Input: hwy\avgload[EA,AM,MD,PM,EV].net
::          trn\transit_support_nodes.dat
::          trn\[express_bus,light_rail,ferry,heavy_rail,commuter_rail]_neti_access_links.dat
::          trn\[express_bus,light_rail,ferry,heavy_rail,commuter_rail]_neti_xfer_links.dat
::  Output: trn\[EA,AM,MD,PM,EV]_transit_background.net
::          trn\[EA,AM,MD,PM,EV]_temporary_transit_background_accesslinks.net
::          trn\[EA,AM,MD,PM,EV]_temporary_transit_background_transferlinks.net
:: Summary: Prepare the highway network for use by the transit network
runtpp "%CODE_DIR%\model-files\scripts\skims\PrepHwyNet.job"
if ERRORLEVEL 2 goto done

if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims" (mkdir "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims")
if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\reverselinks.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\reverselinks.awk" "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\reverselinks.awk"
)
if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\select_pnrs.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\select_pnrs.awk" "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\select_pnrs.awk"
)
if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\createLocalBusKNRs.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\createLocalBusKNRs.awk" "%LOGSUMS_CHECK_DIR%\ctramp\scripts\skims\createLocalBusKNRs.awk"
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Build transit skims
::
:: ------------------------------------------------------------------------------------------------------

:: --------TrnAssignment Setup -- Fast Configuration
:: NOTE the blank ones should have a space
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 
python "%CODE_DIR%\model-files\scripts\skims\transitDwellAccess.py" NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% complexAccess %COMPLEXMODES_ACCESS%

copy /y trn\transitOriginalEA.lin transitEA.lin
copy /y trn\transitOriginalAM.lin transitAM.lin
copy /y trn\transitOriginalMD.lin transitMD.lin
copy /y trn\transitOriginalPM.lin transitPM.lin
copy /y trn\transitOriginalEV.lin transitEV.lin

::   Input: trn\[EA,AM,MD,PM,EV]_temporary_transit_background_accesslinks.net
::          trn\[EA,AM,MD,PM,EV]_temporary_transit_background_transferlinks.net
::          trn\[light_rail,ferry,heavy_rail,commuter_rail].zac
::          trn\walk_access.sup
::          trn\transit_lines.block
::  Output: trn\[EA,AM,MD,PM,EV]_walk_links.dbf
::          trn\[EA,AM,MD,PM,EV]_walk_[acc,egr]links.dat
::          trn\[EA,AM,MD,PM,EV]_drive_links.dbf
::          trn\[EA,AM,MD,PM,EV]_drive_[acc,egr]links.dat
::          trn\[EA,AM,MD,PM,EV]_transit_links.dbf
::          trn\[EA,AM,MD,PM,EV]_transit_suplinks.dat
::          trn\[EA,AM,MD,PM,EV]_transit_suplinks_[walk,express_bus,light_rail,ferry,heavy_rail,commuter_rail].dat
::          trn\[EA,AM,MD,PM,EV]_bus_acclinks_KNR.dat
:: Summary: Create the transit networks
runtpp "%CODE_DIR%\model-files\scripts\skims\BuildTransitNetworks.job"
if ERRORLEVEL 2 goto done

:here
:: Summary: Create the public transport level-of-service matrices (run again if Cube fails)
if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\block" (mkdir "%LOGSUMS_CHECK_DIR%\ctramp\scripts\block")
for %%A in (transit_combined_headways.block transferprohibitors_wlk_trn_wlk.block transferprohibitors_drv_trn_wlk.block transferprohibitors_wlk_trn_drv.block) do (
  if not exist "%LOGSUMS_CHECK_DIR%\ctramp\scripts\block\%%A" (
    copy "%CODE_DIR%\model-files\scripts\block\%%A" "%LOGSUMS_CHECK_DIR%\ctramp\scripts\block\%%A"
  )
)


set TRNASSIGNITER=0
set PREVTRNASSIGNITER=NEG1

start Cluster "%PROJ_DIR%\CTRAMP" 1-16 Start
set COMMPATH=%PROJ_DIR%
:: give it a few seconds
timeout 5

runtpp "%CODE_DIR%\model-files\scripts\skims\TransitSkims.job"
if ERRORLEVEL 2 goto done

:: copy the skims into the skims directory
copy *.tpp skims\????????????????????.tpp
del *.tpp

:: Add time step to the feedback report file
echo FINISHED TRANSIT SKIMMING SKIMMING %ITER%  %DATE% %TIME% >> logs\feedback.rpt 

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
echo FINISHED HIGHWAY SKIMMING %ITER%  %DATE% %TIME% >> logs\feedback.rpt 


:: ------------------------------------------------------------------------------------------------------
::
:: Step 6:  Run logsums
::
:: batch script adapted from RunLogsums.bat
::
:: ------------------------------------------------------------------------------------------------------

echo on

:: ------------------------------------------------------------------------------------------------------
:: Step 6a: Set the path
:: ------------------------------------------------------------------------------------------------------
:: including the location of the 64-bit java development kit and R (but other paths could be useful)
:: set JAVA_PATH=C:\Program Files\Java\jdk1.8.0_181
call CTRAMP\runtime\SetPath.bat


::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D set HOST_IP_ADDRESS=192.168.1.209
if %computername%==PORMDLPPW01 set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02 set HOST_IP_ADDRESS=172.24.0.102
if %computername%==MAINMODEL set HOST_IP_ADDRESS=192.168.1.200

:: create logsums.properties
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --logsums
if ERRORLEVEL 1 goto done

:: ------------------------------------------------------------------------------------------------------
:: Step 6b:  Execute Java
:: ------------------------------------------------------------------------------------------------------

if not exist logsums\indivTripData_%ITER%.csv (

  echo STARTED LOGSUMS RUN  %DATE% %TIME% >> logs\feedback.rpt

  rem run matrix manager, household manager and jppf driver
  cd CTRAMP\runtime
  call javaOnly_runMain.cmd 

  rem run jppf node
  cd CTRAMP\runtime
  call javaOnly_runNode0.cmd

  rem Execute the accessibility calculations
  java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties -Djava.library.path=%RUNTIME% com.pb.mtc.ctramp.MTCCreateLogsums logsums

  rem shut down java
  C:\Windows\SysWOW64\taskkill /f /im "java.exe"
)


:: ------------------------------------------------------------------------------------------------------
:: Step 6c: Reformat logsums
:: ------------------------------------------------------------------------------------------------------

:: pretend it is iter3
:: Set the iteration parameters
set ITER=3
set SAMPLESHARE=1.00

set TARGET_DIR=%CD%
if not exist logsums\mandatoryAccessibilities.csv (
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla ".\CTRAMP\scripts\core_summaries\logsumJoiner.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

:: Add time step to the feedback report file
echo FINISHED RUNNING LOGSUMS %ITER%  %DATE% %TIME% >> logs\feedback.rpt 


:: ------------------------------------------------------------------------------------------------------
:: Step 6d:  Accessibilities Markets
:: ------------------------------------------------------------------------------------------------------

if not exist core_summaries\AccessibilityMarkets.csv (
  rem Rename these to standard names
  if not exist %TARGET_DIR%\popsyn\hhFile.csv     ( copy %TARGET_DIR%\popsyn\hhFile.*.csv %TARGET_DIR%\popsyn\hhFile.csv )
  if not exist %TARGET_DIR%\popsyn\personFile.csv ( copy %TARGET_DIR%\popsyn\personFile.*.csv %TARGET_DIR%\popsyn\personFile.csv )

  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla ".\CTRAMP\scripts\core_summaries\AccessibilityMarkets.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

:: Add time step to the feedback report file
echo FINISHED ACCESSIBILITY MARKETS %ITER%  %DATE% %TIME% >> logs\feedback.rpt 


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

:end
:: Last Step:  Stamp the time of completion to the feedback report file
echo FINISHED LOGSUMS PRECHECK %ITER%  %DATE% %TIME% >> logs\feedback.rpt 
