:: build_transit_network
::
:: utility to build a working transit nework to find coding bugs
::
:: 2015 07 22 dto


:: Location of travel-model-one local repo (probably including this dir)
set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one

:: Location of INPUT and CTRAMP directory and where this test will run
set MODEL_TOP_DIR=C:\Users\lzorn\Documents\scratch\net_test

:: Location of BASE MODEL_DIR
set MODEL_BASE_DIR=\\MODEL2-C\Model2C-Share\Projects\2050_TM151_PPA_CG_00

:: copy in INPUT and CTRAMP
c:\windows\system32\Robocopy.exe /E "%MODEL_BASE_DIR%\INPUT" "%MODEL_TOP_DIR%\INPUT"
c:\windows\system32\Robocopy.exe /E "%CODE_DIR%\model-files" "%MODEL_TOP_DIR%\CTRAMP"
:: copy in custom CTRAMP
copy /y "%MODEL_BASE_DIR%\CTRAMP\scripts\block\hwyparam.block"  "%MODEL_TOP_DIR%\CTRAMP\scripts\block"

:: this is where we'll do this work
set TRN_CHECK_DIR=%MODEL_TOP_DIR%\INPUT\trn_check

:: Path details
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files (x86)\Citilabs\CubeVoyager
set GAWK_PATH=M:\Software\Gawk\bin
SET PATH=%TPP_PATH%;%GAWK_PATH%;%PATH%

:: Step 0: create the trn check dir and go to it
if not exist "%TRN_CHECK_DIR%" (
  mkdir "%TRN_CHECK_DIR%"
)
cd "%TRN_CHECK_DIR%"

:: used by BuildTransitNetworks.job
set MODEL_DIR=%TRN_CHECK_DIR%

:: Step 1: bring in the working transit network and highway network
mkdir trn
mkdir hwy
mkdir main
mkdir skims
mkdir logs

copy "%MODEL_TOP_DIR%\INPUT\trn"                  trn\
copy "%MODEL_TOP_DIR%\INPUT\hwy\freeflow.net"     hwy\
copy "%MODEL_TOP_DIR%\INPUT\hwy\tolls.csv"        hwy\
copy "%MODEL_TOP_DIR%\INPUT\warmstart\main\*"     main\
robocopy /MIR "%MODEL_TOP_DIR%\CTRAMP"            CTRAMP

:: Step 2: build the transit network

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
if exist "%MODEL_TOP_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job" (
  runtpp "%MODEL_TOP_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job"
)
if not exist "%MODEL_TOP_DIR%\CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job" (
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

if not exist "%TRN_CHECK_DIR%\ctramp\scripts\skims" (mkdir "%TRN_CHECK_DIR%\ctramp\scripts\skims")
if not exist "%TRN_CHECK_DIR%\ctramp\scripts\skims\reverselinks.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\reverselinks.awk" "%TRN_CHECK_DIR%\ctramp\scripts\skims\reverselinks.awk"
)
if not exist "%TRN_CHECK_DIR%\ctramp\scripts\skims\select_pnrs.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\select_pnrs.awk" "%TRN_CHECK_DIR%\ctramp\scripts\skims\select_pnrs.awk"
)
if not exist "%TRN_CHECK_DIR%\ctramp\scripts\skims\createLocalBusKNRs.awk" (
  copy "%CODE_DIR%\model-files\scripts\skims\createLocalBusKNRs.awk" "%TRN_CHECK_DIR%\ctramp\scripts\skims\createLocalBusKNRs.awk"
)

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
if not exist "%TRN_CHECK_DIR%\ctramp\scripts\block" (mkdir "%TRN_CHECK_DIR%\ctramp\scripts\block")
for %%A in (transit_combined_headways.block transferprohibitors_wlk_trn_wlk.block transferprohibitors_drv_trn_wlk.block transferprohibitors_wlk_trn_drv.block) do (
  if not exist "%TRN_CHECK_DIR%\ctramp\scripts\block\%%A" (
    copy "%CODE_DIR%\model-files\scripts\block\%%A" "%TRN_CHECK_DIR%\ctramp\scripts\block\%%A"
  )
)

set TRNASSIGNITER=0
set PREVTRNASSIGNITER=NEG1

start Cluster "%MODEL_TOP_DIR%\CTRAMP" 1-16 Start
set COMMPATH=%MODEL_TOP_DIR%
:: give it a few seconds
timeout 5

runtpp "%CODE_DIR%\model-files\scripts\skims\TransitSkims.job"
if ERRORLEVEL 2 goto done

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

