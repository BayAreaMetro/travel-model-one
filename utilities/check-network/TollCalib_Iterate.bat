:: ------------------------------------------------------------------------------------------------------
:: 
:: This batch file calls TollCalib_RunModel.bat multiple times
::
:: ------------------------------------------------------------------------------------------------------

:: -------------------------------------------------
:: If on AWS, HOST_IP_ADDRESS has to be set manually
:: it's the “private IP address” on the wallpaper
:: -------------------------------------------------
if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=10.0.0.69

:: -------------------------------------------------
:: If toll calibration is run for the first time (usually iteration 4)
:: (Or, in case we need to continue toll calibration after the machine is shut down, then enter the next iteration number below and edit the TOLL_FILE location)
:: -------------------------------------------------

:: set iteration number, starting from 4 as we assume this is a continuation of a "normal" model run
set ITER=4

:: Location of the base run directory - the full run is needed because it needs the CTRAMP directory
set MODEL_BASE_DIR=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_preCalib_01

:: Name and location of the tolls.csv to be used
set TOLL_FILE=%MODEL_BASE_DIR%\hwy\tolls_iter4.csv

:: Location of the output folder "tollcalib_iter"
set L_DIR=\\tsclient\L\RTP2021_PPA\Projects\3000_ExpLanes_Calib\2050_TM151_PPA_RT_11_3000_EXPLanes_Calib_01

:: -------------------------------------------------
:: User input for all iterations
:: -------------------------------------------------

:: to run highway assignment only, enter 1 below; 
:: to run highway assigment + skimming + core, enter 0 below
set hwyassignONLY=0
set MODEL_YEAR=2050


:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
set UNLOADED_NETWORK_DBF=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv), also needed for the R script that determine toll adjustment
SET BRIDGE_TOLLS_CSV=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\Bridge_Toll_Updates_2_2pct\tolls_2050.csv

:: The file indicating which facilities have mandatory s2 tolls
set TOLL_DESIGNATIONS_XLSX=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\TOLLCLASS_Designations.xlsx

:: -------------------------------------------------
:: check that all the paths are valid
:: -------------------------------------------------

if exist %MODEL_BASE_DIR% (
    echo base run directory exists!
) else (
    echo base run directory missing!
    goto end
)

if exist %TOLL_FILE% (
    echo toll file exists!
) else (
    echo toll file missing!
    goto end
)

if exist %UNLOADED_NETWORK_DBF% (
    echo unloaded network exists!
) else (
    echo unloaded network missing!
    goto end
)

if exist %BRIDGE_TOLLS_CSV% (
    echo bridge toll file exists!
) else (
    echo bridge toll file missing!
    goto end
)

if exist %TOLL_DESIGNATIONS_XLSX% (
    echo toll designation excel file exists!
) else (
    echo toll designation excel file missing!
    goto end
)

:: also check if it's being run on AWS
:: if so, this will be "WIN-"
SET computer_prefix=%computername:~0,4%

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
:: If it's an AWS machine, shut down the machine automatically when done
:: -------------------------------------------------


if "%COMPUTER_PREFIX%" == "WIN-" (
  rem shutdown
  C:\Windows\System32\shutdown.exe /s
)


:: -------------------------------------------------
:: end process if any of the input files are missing
:: -------------------------------------------------
:end

