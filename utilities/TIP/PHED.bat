:: ----------------------------------------------------------------
:: batch file generates the PHED metric
:: ----------------------------------------------------------------

:: user inputs
:: ----------------------------------------------------------------
set SCENARIO_DIR=M:\Application\Model One\RTP2021\Blueprint\2050_TM152_FBP_PlusCrossing_20

:: export from cube to shape
:: ----------------------------------------------------------------
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
set PATH=%path%;%TPP_PATH%

cd /d "%SCENARIO_DIR%\INPUT\hwy"
mkdir forPHED

set NET_INFILE=freeflow.net
set NODE_OUTFILE=forPHED\freeflow_nodes.shp
set LINK_OUTFILE=forPHED\freeflow_links.shp

runtpp X:\travel-model-one-master\utilities\cube-to-shapefile\export_network.job

:: add projection
:: ----------------------------------------------------------------
copy M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\PHED\freeflow_links.prj freeflow_links.prj
copy M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\PHED\freeflow_links.shp.xml freeflow_links.shp.xml

:: join the free flow links with the file with the city boundaries
:: ----------------------------------------------------------------
set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts
set SCENARIO_DIR=M:\Application\Model One\RTP2021\Blueprint\2050_TM152_FBP_PlusCrossing_21

cd /d %SCENARIO_DIR%
python "X:\travel-model-one-master\utilities\cube-to-shapefile\correspond_link_to_TAZ.py" "%SCENARIO_DIR%\INPUT\hwy\forPHED\freeflow_links.shp" "%SCENARIO_DIR%\INPUT\hwy\forPHED\freeflow_links_cities.csv" --shapefile "M:\Development\Travel Model One\Version 05\Adding City to Master Network\Cityshapes\PBA_Cities_NAD_1983_UTM_Zone_10N.shp"  --shp_id name

:: run the R script that calculates the PHED metric
:: ----------------------------------------------------------------

