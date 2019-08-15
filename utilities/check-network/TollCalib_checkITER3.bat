:: ------------------------------------------
:: Set file paths and iteration number, and run the R script that calculates EL and GP speed
:: ------------------------------------------

set ITER=3

:: Location of the base run directory - the full run is needed because it needs the CTRAMP directory
set PROJECT_DIR=D:\Projects\2050_TM151_PPA_CG_11_3000_ExpLanes_Calib_00

:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
:: (okay to borrow it from a different Future as long as we're sure the unloaded network is the same across Futures)
set UNLOADED_NETWORK_DBF=\\tsclient\L\RTP2021_PPA\Projects\3000_ExpLanes_Calib\2050_TM151_PPA_RT_11_3000_ExpLanes_Calib_00\OUTPUT\shapefiles\network_links.dbf

:: The file containing the bridge tolls (i.e. the first half of toll.csv), also needed for the R script that determine toll adjustment
SET BRIDGE_TOLLS_CSV=\\tsclient\M\Application\Model One\NetworkProjects\Bridge_Toll_Updates_2_2pct\tolls_2050.csv

:: The file indicating which facilities have mandatory s2 tolls
set TOLL_DESIGNATIONS_XLSX=\\tsclient\M\Application\Model One\Networks\TOLLCLASS Designations.xlsx

set R_HOME=C:\Program Files\R\R-3.5.2
:: set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.5

call "%R_HOME%\bin\x64\Rscript.exe" "\\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_CheckSpeeds.R"
