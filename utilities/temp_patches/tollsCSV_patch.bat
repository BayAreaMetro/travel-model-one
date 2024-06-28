# -------------------------------------------------------------------------------
# rem this script is a temp patch for the tolls.csv for the express lane scenarios for RTP025 PPA
# -------------------------------------------------------------------------------

rem before running the scripts, specify R version
if "%computername%" == "FTSANG-VM" (
  set R_HOME=C:\Program Files\R\R-4.3.2
)
if "%computername%" == "MODEL3-C" (
  set R_HOME=C:\Program Files\R\R-4.2.1
)

rem cd /d "C:\Users\ftsang\Box\Plan Bay Area 2050+\Performance and Equity\Project Performance\Express_lane_networks"
rem cd /d L:\RTP2025_PPA\Projects\Express_lane_networks
cd /d L:\Application\Model_One\NextGenFwys_Round2\INPUT_DEVELOPMENT\Networks

setlocal enabledelayedexpansion

for /d %%f in (

NGF_Networks_NGFround2_P6_14\NGF_R2_R2P6_Dual_Express_Lanes_network_2035

)    do    (


cd %%f
mkdir shapefile

set NET_INFILE=hwy\freeflow.net
set NODE_OUTFILE=shapefile\network_nodes.shp
set LINK_OUTFILE=shapefile\network_links.shp
runtpp X:\travel-model-one-master\utilities\cube-to-shapefile\export_network.job

set WORKING_DIR=%CD%
set SCENARIO=%%f
call "%R_HOME%\bin\x64\Rscript.exe" "X:\travel-model-one-master\utilities\check-network\tolls_check.R"

cd ..\..

)

endlocal
