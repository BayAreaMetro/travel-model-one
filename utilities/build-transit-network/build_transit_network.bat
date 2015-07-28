:: build_transit_network
::
:: utility to build a working transit nework to find coding bugs
::
:: 2015 07 22 dto

set NETWORK_CODING_DIR="M:\Application\Model One\RTP2017\Project Performance Assessment\Baseline Network"
set SCRIPT_DIR="D:\files\GitHub\travel-model-one\model-files"

:: Path details
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files (x86)\Citilabs\CubeVoyager
set GAWK_PATH=D:\files\Gawk\bin
SET PATH=%TPP_PATH%;%GAWK_PATH%;%PATH%

:: Step 1: bring in the working transit network and highway network
mkdir trn
mkdir hwy
mkdir skims
mkdir logs

copy %NETWORK_CODING_DIR%\trn\transit_lines\   trn\
copy %NETWORK_CODING_DIR%\trn\transit_fares\   trn\ 
copy %NETWORK_CODING_DIR%\trn\transit_support\ trn\

copy %NETWORK_CODING_DIR%\2015U_June22.net hwy\freeflow.net

:: Step 2: build the transit network

:: Set the prices in the roadway network
runtpp %SCRIPT_DIR%\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 goto done

:: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
runtpp %SCRIPT_DIR%\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 goto done

:: Create time-of-day-specific 
runtpp %SCRIPT_DIR%\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 goto done

:: Prepare the highway network for use by the transit network
runtpp %SCRIPT_DIR%\scripts\skims\PrepHwyNet.job
if ERRORLEVEL 2 goto done

:: Create the transit networks
runtpp %SCRIPT_DIR%\scripts\skims\BuildTransitNetworks.job
if ERRORLEVEL 2 goto done

:: Create the public transport level-of-service matrices (run again if Cube fails)
start Cluster M:\COMMPATH\CTRAMP 1-16 Start
runtpp %SCRIPT_DIR%\scripts\skims\TransitSkims.job
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

