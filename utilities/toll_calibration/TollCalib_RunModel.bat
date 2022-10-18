::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::
:: Toll rate calibration
:: This batch script runs hwyassign, generates loaded network (avgload5period.csv), and determines new toll rates (via TollCalib_CheckSpeeds.R)
::
:: Copy this batch script from GitHub\travel-model-one\utilities\toll_calibration to a local project directory
:: e.g. on model2-a, b, c, d, E:\Model2B-Share\Projects\2050_TM151_PPA_BF_06_TollCalibration_00
:: 
:: This batch script is called by the wrapper batch file - TollCalib_Iterate.bat
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: ------------------------------------------------------------------------------------------------------
::
:: User input (moved to wrapper batch file - TollCalib_Iterate.bat)
::
:: ------------------------------------------------------------------------------------------------------

:: to run highway assignment only, enter 1 below; 
:: to run highway assigment + skimming + core, enter 0 below
:: set hwyassignONLY=0

:: set iteration number, starting from 4 as we assume this is a continuation of a "normal" model run
:: set ITER=5
:: set MODEL_YEAR=2050

:: if %ITER%==4 (
    :: Location of the base run directory - the full run is needed because it has the CTRAMP directory
::    set MODEL_BASE_DIR=L:\RTP2021_PPA\Projects_onAWS\2050_TM151_PPA_BF_07
:: )

:: -------------------------------------------------
:: Before running - user input (part 2)
:: For the R script that determine toll adjustment
:: -------------------------------------------------

:: Unloaded network dbf, generated from cube_to_shapefile.py
:: set UNLOADED_NETWORK_DBF=L:\RTP2021_PPA\Projects\2050_TM151_PPA_baselines_before07\2050_TM151_PPA_BF_06\INPUT\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv)
:: SET BRIDGE_TOLLS_CSV=M:\Application\Model One\NetworkProjects\Bridge_Toll_Updates\tolls_2050.csv

:: The file indicating which facilities have mandatory s2 tolls
:: set TOLL_DESIGNATIONS_XLSX= M:\Application\Model One\Networks\TOLLCLASS Designations.xlsx


:: ------------------------------------------------------------------------------------------------------
::
:: Name and location of the tolls.csv to be used
::
:: ------------------------------------------------------------------------------------------------------

if %ITER% NEQ 4 (
    set TOLL_FILE=%cd%\hwy\tolls_iter%ITER%.csv
)

:: if it's iteration 4, this path is specified in TollCalib_Iterate.bat

:: ------------------------------------------------------------------------------------------------------
::
:: Step 0: set file location and folder structure
::
:: ------------------------------------------------------------------------------------------------------


:: Use this for COMMPATH
mkdir COMMPATH
set COMMPATH=%CD%\COMMPATH
echo COMMPATH is [%COMMPATH%]
"C:\Program Files\Citilabs\CubeVoyager\Cluster" "%COMMPATH%\CTRAMP" 1-48 Starthide Exit


:: Path details
set PATH=c:\windows\system32;C:\Python27;C:\Python27\Scripts
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files (x86)\Citilabs\CubeVoyager
set PYTHONPATH=X:\NetworkWrangler;X:\NetworkWrangler\_static
set GAWK_PATH=M:\Software\Gawk\bin
SET PATH=%TPP_PATH%;%GAWK_PATH%;%PATH%


:: ------------------------------------------------------------------------------------------------------
::
:: Step 1: bring in ctramp and the highway network
::
:: ------------------------------------------------------------------------------------------------------

if %ITER%==4 (
    :: Use the same CTRAMP as the BASE
    robocopy /MIR "%MODEL_BASE_DIR%\CTRAMP"           CTRAMP

    robocopy /MIR "%MODEL_BASE_DIR%\INPUT\hwy"        hwy
)

:: check that the NonDynamicTollFacilities.csv file is in the INPUT\hwy folder of the base run
if not exist %MODEL_BASE_DIR%\INPUT\hwy\NonDynamicTollFacilities.csv (
    echo %MODEL_BASE_DIR%\INPUT\hwy\NonDynamicTollFacilities.csv missing.
    goto end
)


:: use the new toll file
copy /y "%TOLL_FILE%" hwy\
copy /y "%TOLL_FILE%" hwy\tolls.csv


:: ------------------------------------------------------------------------------------------------------
::
:: Step 2: Pre-process steps
::
:: ------------------------------------------------------------------------------------------------------
:preprocess
python "CTRAMP\scripts\notify_slack.py" "Starting toll calibration *%MODEL_DIR%* Iter *%ITER%*"

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
:: Step 3: HwyAssign with trip tables from base
::
:: ------------------------------------------------------------------------------------------------------
:hwyassign

if %ITER%==4 (
    mkdir main
    copy "%MODEL_BASE_DIR%\main\trips??.tpp"         main\
    mkdir nonres
    copy "%MODEL_BASE_DIR%\nonres\tripsIx??.tpp"     nonres\
    copy "%MODEL_BASE_DIR%\nonres\tripsTrk??.tpp"    nonres\
    copy "%MODEL_BASE_DIR%\nonres\tripsAirPax??.tpp" nonres\

    mkdir logs
)

:: Stamp the feedback report with the date and time of the model start
echo STARTED HIGHWAY ASSIGNMENT  %DATE% %TIME% >> logs\feedback.rpt 

:: Assign the demand matrices to the highway network
runtpp CTRAMP\scripts\assign\HwyAssign.job
if ERRORLEVEL 2 goto done

:: Complete
echo FINISHED HIGHWAY ASSIGNMENT  %DATE% %TIME% >> logs\feedback.rpt
"C:\Program Files\Citilabs\CubeVoyager\Cluster" "%COMMPATH%\CTRAMP" 1-48 Close Exit

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Prepare the networks for the next iteration
::
:: ------------------------------------------------------------------------------------------------------

:feedback

set /a PREV_ITER=%ITER%-1
set WGT=0.33
set PREV_WGT=0.67

if %ITER%==4 (
   robocopy "%MODEL_BASE_DIR%\hwy\iter%PREV_ITER%" hwy\iter%PREV_ITER%
)

:: Move assigned networks to a iteration-specific directory
mkdir hwy\iter%ITER%      

move hwy\LOADEA.net hwy\iter%ITER%\LOADEA.net
move hwy\LOADAM.net hwy\iter%ITER%\LOADAM.net
move hwy\LOADMD.net hwy\iter%ITER%\LOADMD.net
move hwy\LOADPM.net hwy\iter%ITER%\LOADPM.net
move hwy\LOADEV.net hwy\iter%ITER%\LOADEV.net

:: Give the default TP+ variables more intuitive names
runtpp CTRAMP\scripts\feedback\RenameAssignmentVariables.job

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


:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: summarise EL and GP speeds, and generate a new toll file for the next iteration
::
:: ------------------------------------------------------------------------------------------------------
:newtoll

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.5.2

:: System variables to be passed to the R code
set PROJECT_DIR=%cd%

if "%COMPUTER_PREFIX%" == "WIN-" (
    call "%R_HOME%\bin\x64\Rscript.exe" TollCalib_CheckSpeeds.R
) else (
    call "%R_HOME%\bin\x64\Rscript.exe" "\\mainmodel\MainModelShare\travel-model-one-master\utilities\toll_calibration\TollCalib_CheckSpeeds.R"
    python "\\mainmodel\MainModelShare\travel-model-one-master\utilities\toll_calibration\TollCalib_stop.py"
)

:: copy the output back to L
if %ITER%==4 (
    mkdir %L_DIR%\tollcalib_iter
    mkdir "%L_DIR%\tollcalib_iter"
)
copy tollcalib_iter\el_gp_avg_speed_iter%ITER%.csv %L_DIR%\tollcalib_iter\el_gp_avg_speed_iter%ITER%.csv
copy tollcalib_iter\el_gp_summary_ALL.csv %L_DIR%\tollcalib_iter\el_gp_summary_ALL.csv
set /a NEXT_ITER=%ITER%+1
copy hwy\tolls_iter%NEXT_ITER%.csv %L_DIR%\tollcalib_iter\tolls_iter%NEXT_ITER%.csv
:: in case there is any space on the path of L_DIR e.g. Model One
copy hwy\tolls_iter%NEXT_ITER%.csv "%L_DIR%\tollcalib_iter\tolls_iter%NEXT_ITER%.csv"

if hwyassignONLY==1 goto end

:: ------------------------------------------------------------------------------------------------------
::
:: Step 6: Build highway skims
::
:: ------------------------------------------------------------------------------------------------------

:skims


if %ITER%==4 (
    mkdir skims
    c:\windows\system32\Robocopy.exe /E "%MODEL_BASE_DIR%\skims" skims
)

:: Create the automobile level-of-service matrices
runtpp CTRAMP\scripts\skims\HwySkims.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 7: run core i.e. execute the choice models using CT-RAMP java code
::
:: ------------------------------------------------------------------------------------------------------

:: ------------------------------------------
:: Step 7a: Set the paths
:: ------------------------------------------
:: including the location of the 64-bit java development kit
:: set JAVA_PATH=C:\Program Files\Java\jdk1.8.0_181
call CTRAMP\runtime\SetPath.bat
:: but overwrite the commpath setting
set COMMPATH=%CD%\COMMPATH

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D set HOST_IP_ADDRESS=192.168.1.209
if %computername%==PORMDLPPW01 set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02 set HOST_IP_ADDRESS=172.24.0.102
if %computername%==MAINMODEL set HOST_IP_ADDRESS=192.168.1.200
if %computername%==SATMODEL set HOST_IP_ADDRESS=192.168.1.201
if %computername%==SATMODEL4 set HOST_IP_ADDRESS=192.168.1.205

:: copy in params.properties
:: used by runtimeconfiguration.py
if %ITER%==4 (
    mkdir INPUT
    copy "%MODEL_BASE_DIR%\INPUT\params.properties"  INPUT\params.properties
)


:: copy in household and population data (and land use)
if %ITER%==4 (

    mkdir popsyn
    copy "%MODEL_BASE_DIR%\popsyn\hhFile.csv"         popsyn\hhFile.csv
    copy "%MODEL_BASE_DIR%\popsyn\personFile.csv"     popsyn\personFile.csv

    :: also need to copy popsyn to INPUT
    mkdir INPUT\popsyn
    copy "%MODEL_BASE_DIR%\popsyn\hhFile.csv"         INPUT\popsyn\hhFile.csv
    copy "%MODEL_BASE_DIR%\popsyn\personFile.csv"     INPUT\popsyn\personFile.csv

    mkdir landuse
    c:\windows\system32\Robocopy.exe /E "%MODEL_BASE_DIR%\landuse" landuse
)

:: used by core java processes
copy "%MODEL_BASE_DIR%\main\ShadowPricing_5.csv"           main\ShadowPricing_5.csv
copy "%MODEL_BASE_DIR%\main\telecommute_constants.csv"     main\telecommute_constants.csv

:: Runtime configuration: set project directory, auto operating cost, 
:: and synthesized household/population files in the appropriate places
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 goto done

:: ------------------------------------------
:: Step 7b:  Execute Java
:: ------------------------------------------

:: Set the iteration parameters
set SAMPLESHARE=0.15
set SEED=0


:core

rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

call C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: ------------------------------------------
:: Step 7c:  prepare for the next assignment
:: ------------------------------------------

if %ITER%==4 (
    copy "%MODEL_BASE_DIR%\main\trips_transitHsr??.tpp"         main\
)


:: after executing demand models, translate the trip lists to demand matrices
runtpp CTRAMP\scripts\assign\PrepAssign.job
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: the end
::
:: ------------------------------------------------------------------------------------------------------
:end
:done