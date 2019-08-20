:: ------------------------------------------
:: Set file paths and iteration number, and run the R script that calculates EL and GP speed
:: ------------------------------------------

set ITER=3

:: Location of the base run directory
:: Either the directory with the full run, or the directory with the extracted outputs
set PROJECT_DIR=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_preCalib_01

:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
:: (okay to borrow it from a different Future as long as we're sure the unloaded network is the same across Futures)
set UNLOADED_NETWORK_DBF=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv), also needed for the R script that determine toll adjustment
SET BRIDGE_TOLLS_CSV=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\Bridge_Toll_Updates_2_2pct\tolls_2050.csv

:: The file indicating which facilities have mandatory s2 tolls
set TOLL_DESIGNATIONS_XLSX=D:\Projects\2050_TM151_PPA_RT_11_3000_ExpLanes_TollCalib_01\TollCalib_input\TOLLCLASS_Designations.xlsx

:: set R location
set R_HOME=C:\Program Files\R\R-3.5.2

:: check if it's being run on AWS
:: if the prefix will be "WIN-"
SET computer_prefix=%computername:~0,4%

if "%COMPUTER_PREFIX%" == "WIN-" (
    call "%R_HOME%\bin\x64\Rscript.exe" "\\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_CheckSpeeds.R"
) else (
    call "%R_HOME%\bin\x64\Rscript.exe" "\\mainmodel\MainModelShare\travel-model-one-master\utilities\check-network\TollCalib_CheckSpeeds.R"
)