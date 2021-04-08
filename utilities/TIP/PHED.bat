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
copy X:\travel-model-one-master\utilities\TIP\freeflow_links.prj freeflow_links.prj
copy X:\travel-model-one-master\utilities\TIP\freeflow_links.shp.xml freeflow_links.shp.xml

:: join the free flow links with the file with the urbanized area boundaries
:: ----------------------------------------------------------------
set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts

python "X:\travel-model-one-master\utilities\cube-to-shapefile\correspond_link_to_TAZ.py" "%SCENARIO_DIR%\INPUT\hwy\forPHED\freeflow_links.shp" "%SCENARIO_DIR%\INPUT\hwy\forPHED\freeflow_links_UA.csv" --shapefile "M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\PHED\SelectedUrbanizedAreas\FiveUZA_NAD1983UTMzone10N.shp"  --shp_id NAME10

:: run the R script that calculates the PHED metric
:: ----------------------------------------------------------------
:: set R location
set R_HOME=C:\Program Files\R\R-3.5.2

call "%R_HOME%\bin\x64\Rscript.exe" X:\travel-model-one-master\utilities\TIP\federal_metric_PHED_TM1.5.R