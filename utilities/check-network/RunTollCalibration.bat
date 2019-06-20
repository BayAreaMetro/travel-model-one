::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::
:: toll rate calibration
:: runs hwyassign, generate loaded network (avgload5period.csv), and determine new toll rates
::
:: can be run from a project directory in model2-a, b, c, d
:: e.g. E:\Model2B-Share\Projects\2050_TM151_PPA_BF_06_TollCalibration_00
:: 
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: ------------------------------------------------------------------------------------------------------
::
:: Before running - user input
::
:: ------------------------------------------------------------------------------------------------------

:: set iteration number, starting from 4 as we assume this is a continuation of a "normal" model run
set ITER=4
set PREV_ITER=3

if %ITER%==4 (
    :: Location of BASE MODEL_DIR full run
    set MODEL_BASE_DIR=\\model2-d\Model2D-Share\Projects\2050_TM151_PPA_BF_06
)

:: Name and location of the new tolls.csv
:: set TOLL_FILE=L:\RTP2021_PPA\Projects\2050_TM151_PPA_BF_06\INPUT\hwy\tolls_iterX.csv
:: set TOLL_FILE=E:\Model2B-Share\Projects\2050_TM151_PPA_BF_06_TollCalibration_00\hwy\tolls_iter4.csv
set TOLL_FILE=%cd%\hwy\tolls_iter%ITER%.csv

:: -------------------------------------------------
:: Before running - user input (part 2)
:: For the R script that determine toll adjustment
:: -------------------------------------------------

:: Unloaded network dbf, generated from cube_to_shapefile.py
set UNLOADED_NETWORK_DBF=L:\RTP2021_PPA\Projects\2050_TM151_PPA_BF_06\INPUT\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv)
SET BRIDGE_TOLLS_CSV=M:\Application\Model One\NetworkProjects\Bridge_Toll_Updates\tolls_2050.csv


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

:: use the new toll file
copy /y "%TOLL_FILE%" hwy\
copy /y "%TOLL_FILE%" hwy\tolls.csv


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

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.5.2
set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.5

:: System variables to be passed to the R code
set PROJECT_DIR=%cd%

call "%R_HOME%\bin\x64\Rscript.exe" "\\mainmodel\MainModelShare\travel-model-one-master\utilities\check-network\calibrate_el_tolls.R"
