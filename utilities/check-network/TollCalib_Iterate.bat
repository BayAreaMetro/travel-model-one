:: ------------------------------------------------------------------------------------------------------
:: 
:: This batch file calls TollCalib_RunModel.bat multiple times
::
:: ------------------------------------------------------------------------------------------------------

:: -------------------------------------------------
:: If toll calibration is run for the first time (usually iteration 4)
:: -------------------------------------------------

:: set iteration number, starting from 4 as we assume this is a continuation of a "normal" model run
set ITER=4

:: Location of the base run directory - the full run is needed because it needs the CTRAMP directory
set MODEL_BASE_DIR=L:\RTP2021_PPA\Projects_onAWS\2050_TM151_PPA_RT_09

:: Name and location of the tolls.csv to be used
set TOLL_FILE=L:\RTP2021_PPA\Projects\2050_TM151_PPA_RT_09\tolls_iter4.csv

:: -------------------------------------------------
:: User input for all iterations
:: -------------------------------------------------

:: to run highway assignment only, enter 1 below; 
:: to run highway assigment + skimming + core, enter 0 below
set hwyassignONLY=0
set MODEL_YEAR=2050


:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
set UNLOADED_NETWORK_DBF=L:\RTP2021_PPA\Projects\2050_TM151_PPA_RT_09\OUTPUT\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv), also needed for the R script that determine toll adjustment
SET BRIDGE_TOLLS_CSV=M:\Application\Model One\NetworkProjects\Bridge_Toll_Updates\tolls_2050.csv

:: The file indicating which facilities have mandatory s2 tolls
set TOLL_DESIGNATIONS_XLSX=M:\Application\Model One\Networks\TOLLCLASS Designations.xlsx

:: -------------------------------------------------
:: check that all the paths are valid
:: -------------------------------------------------

if exist %MODEL_BASE_DIR% (
    rem goto runiter4
    echo file exists!
) else (
    rem goto end
    echo file missing!
)

if exist %TOLL_FILE% (
    rem goto runiter4
    echo file exists!
) else (
    rem goto end
    echo file missing!
)

if exist %UNLOADED_NETWORK_DBF% (
    rem goto runiter4
    echo file exists!
) else (
    rem goto end
    echo file missing!
)

if exist %BRIDGE_TOLLS_CSV% (
    rem goto runiter4
    echo file exists!
) else (
    rem goto end
    echo file missing!
)

if exist %TOLL_DESIGNATIONS_XLSX% (
    rem goto runiter4
    echo file exists!
) else (
    rem goto end
    echo file missing!
)

:: -------------------------------------------------
:: Run iteration 4
:: -------------------------------------------------
:runiter4

call TollCalib_RunModel

:: -------------------------------------------------
:: For iteration 5+
:: -------------------------------------------------
set ITER=5
call TollCalib_RunModel

set ITER=6
call TollCalib_RunModel

set ITER=7
call TollCalib_RunModel

set ITER=8
call TollCalib_RunModel

set ITER=9
call TollCalib_RunModel

set ITER=10
call TollCalib_RunModel

:: -------------------------------------------------
:: end process if any of the input files are missing
:: -------------------------------------------------
:end

