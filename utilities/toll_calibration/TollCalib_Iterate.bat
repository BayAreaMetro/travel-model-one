:: ------------------------------------------------------------------------------------------------------
:: 
:: This batch file calls TollCalib_RunModel.bat multiple times
::
:: ------------------------------------------------------------------------------------------------------

:: -------------------------------------------------
:: If on AWS, HOST_IP_ADDRESS has to be set manually
:: it's the “private IP address” on the wallpaper
:: -------------------------------------------------
if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=%HOST_IP_ADDRESS%

:: -------------------------------------------------
:: User input needed here
:: if toll calibration is run for the first time, set iter to 4
:: (alternatively, in case we need to continue toll calibration after the machine is restarted, enter the next iteration number below and edit the TOLL_FILE location)
:: -------------------------------------------------

:: set iteration number, starting from 4 as we assume this is a continuation of a "normal" model run
set ITER=4

:: Location of the base run directory - the full run is needed because it needs the CTRAMP directory
set MODEL_BASE_DIR=%MODEL_BASE_DIR%

:: Name and location of the tolls.csv to be used
set TOLL_FILE=%MODEL_BASE_DIR%\hwy\tolls_iter4.csv

:: Location of the output folder "tollcalib_iter" on the L drive
set L_DIR=%L_DIR%

:: to run highway assignment only, enter 1 below; 
:: to run highway assigment + skimming + core, enter 0 below
set hwyassignONLY=0

REM set MODEL_YEAR
for /f "delims=" %%i in ('python get_model_year.py') do (
    
    set model_year=%%i

)
rem if ERRORLEVEL 1 goto done



:: -------------------------------------------------
:: check that all the paths are valid
:: -------------------------------------------------

:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
set UNLOADED_NETWORK_DBF=tollcalib_iter\network_links.dbf

:: The file indicating which facilities have mandatory s2 tolls, needed for the R script that determine toll adjustment 
set TOLL_DESIGNATIONS_XLSX=tollcalib_iter\TOLLCLASS_Designations.xlsx



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

set ITER=11
call TollCalib_RunModel

set ITER=12
call TollCalib_RunModel

set ITER=13
call TollCalib_RunModel

set ITER=14
call TollCalib_RunModel

set ITER=15
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

:done