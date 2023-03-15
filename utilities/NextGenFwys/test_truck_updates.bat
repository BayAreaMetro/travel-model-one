SETLOCAL EnableDelayedExpansion

:: Tests truck IX update (moves small percentage of IX/EX travel from auto to truck)

set MODEL_DIR=\\MODEL2-C\Model2C-Share\Projects\2015_TM152_NGF_04
set CODE_DIR=\\tsclient\E\GitHub\travel-model-one-truck-updates
:: test rerunning iteration 3 steps
set ITER=3

:: Figure out the model folder
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf

:: copy required inputs
mkdir nonres
copy %MODEL_DIR%\nonres\ixDailyx4.tpp            nonres\
copy %MODEL_DIR%\nonres\tripsHsr??.tpp           nonres\
copy %MODEL_DIR%\nonres\truckkfact.k22.z1454.mat nonres\
copy %MODEL_DIR%\nonres\truckFF.dat              nonres\
copy %MODEL_DIR%\nonres\tripsAirPax??.tpp        nonres\

mkdir landuse
copy %MODEL_DIR%\landuse\tazdata.dbf landuse\

mkdir CTRAMP\scripts\block
copy %MODEL_DIR%\CTRAMP\scripts\block\hwyparam.block              CTRAMP\scripts\block\
copy %MODEL_DIR%\CTRAMP\scripts\block\SpeedCapacity_1hour.block   CTRAMP\scripts\block\
copy %MODEL_DIR%\CTRAMP\scripts\block\HwyIntraStep.block          CTRAMP\scripts\block\
copy %MODEL_DIR%\CTRAMP\scripts\block\FreeFlowSpeed.block         CTRAMP\scripts\block\
copy %MODEL_DIR%\CTRAMP\scripts\block\SpeedFlowCurve.block        CTRAMP\scripts\block\

mkdir skims
copy %MODEL_DIR%\skims\hwyskm*.tpp      skims\
copy %MODEL_DIR%\skims\com_hwyskim*.tpp skims\

mkdir hwy
copy %MODEL_DIR%\hwy\avgload??.net  hwy\

mkdir main
copy %MODEL_DIR%\main\trips??.tpp   main\

mkdir logs

:: paths from SetPath.bat
SET COMMPATH=X:\COMMPATH
if "%COMPUTER_PREFIX%" == "WIN-" (  SET COMMPATH=D:\COMMPATH)
if %computername%==MODEL2-A      (  set COMMPATH=E:\Model2A-Share\COMMPATH)
if %computername%==MODEL2-B      (  set COMMPATH=E:\Model2B-Share\COMMPATH)
if %computername%==MODEL2-C      (  set COMMPATH=E:\Model2C-Share\COMMPATH)
if %computername%==MODEL2-D      (  set COMMPATH=E:\Model2D-Share\COMMPATH)
:: Assuming PATH is already set to include runtpp and python3 that has pandas

:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

:nonres

:: Apply diurnal factors to the fixed internal/external demand matrices
runtpp "%CODE_DIR%\model-files\scripts\nonres\IxTimeOfDay.job"
if ERRORLEVEL 2 goto done

:: Apply a value toll choice model for the interna/external demand
runtpp "%CODE_DIR%\model-files\scripts\nonres\IxTollChoice.job"
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle generation models
runtpp "%CODE_DIR%\model-files\scripts\nonres\TruckTripGeneration.job"
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle distribution models
runtpp "%CODE_DIR%\model-files\scripts\nonres\TruckTripDistribution.job"
if ERRORLEVEL 2 goto done

:: Apply the commercial vehicle diurnal factors
runtpp "%CODE_DIR%\model-files\scripts\nonres\TruckTimeOfDay.job"
if ERRORLEVEL 2 goto done

:: Apply a value toll choice model for eligibile commercial demand
runtpp "%CODE_DIR%\model-files\scripts\nonres\TruckTollChoice.job"
if ERRORLEVEL 2 goto done

:: Assign the demand matrices to the highway network
runtpp "%CODE_DIR%\model-files\scripts\assign\HwyAssign.job"
if ERRORLEVEL 2 goto done

:: Move assigned networks to a iteration-specific directory
mkdir hwy\iter%ITER%      

move hwy\LOADEA.net hwy\iter%ITER%\LOADEA.net
move hwy\LOADAM.net hwy\iter%ITER%\LOADAM.net
move hwy\LOADMD.net hwy\iter%ITER%\LOADMD.net
move hwy\LOADPM.net hwy\iter%ITER%\LOADPM.net
move hwy\LOADEV.net hwy\iter%ITER%\LOADEV.net

:: Give the default TP+ variables more intuitive names
runtpp "%CODE_DIR%\model-files\scripts\feedback\RenameAssignmentVariables.job"

:: For this test, we don't want to average because we only did 1 iterations and that will make truck volumes too low
set PREV_ITER=2
set PREV_WGT=0.0
set WGT=1.0

mkdir hwy\iter2
copy %MODEL_DIR%\hwy\iter2\avgload??.net hwy\iter2\

runtpp "%CODE_DIR%\model-files\scripts\feedback\AverageNetworkVolumes.job"
if ERRORLEVEL 2 goto done
runtpp "%CODE_DIR%\model-files\scripts\feedback\CalculateSpeeds.job"
if ERRORLEVEL 2 goto done

:: Combine the time-of-day-specific networks into a single network
runtpp "%CODE_DIR%\model-files\scripts\feedback\MergeNetworks.job"
if ERRORLEVEL 2 goto done     

:: create hwy\iter%ITER%\avgload5period_vehclasses.csv
runtpp "%CODE_DIR%\utilities\RTP\metrics\net2csv_avgload5period.job"
IF ERRORLEVEL 2 goto error

mkdir validation_truck
copy hwy\iter3\avgload5period_vehclasses.csv validation_truck

cd validation_truck
python "%CODE_DIR%\utilities\prepare-validation-data\RoadwayValidation.py" -m 2015 -t 2014 2015 2016
IF ERRORLEVEL 2 goto error
copy "%CODE_DIR%\utilities\prepare-validation-data\Truck Validation.twb" "TruckValidation_%myfolder%.twb"

cd ..

:done

:: Close the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Close Exit