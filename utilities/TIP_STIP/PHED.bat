:: ----------------------------------------------------------------
:: batch file for generating the PHED metric
:: ----------------------------------------------------------------
:: This batch file takes only one argument -- the full file path of the model run output directory on M
:: See an example DOS command below:
:: e.g. X:\travel-model-one-master\utilities\TIP\PHED.bat "M:\Application\Model One\RTP2021\Blueprint\2040_TM152_FBP_Plus_21"
:: Note that the quotes are needed for the argument, because of the blank space between "Model" and "One"
:: When it's done, the output file can be found in: [full file path of the model run output directory on M]\OUTPUT\metrics\federal_metric_PHED.csv

:: More general background about what the PHED metric is can be found at the top of the R script
:: https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/TIP/federal_metric_PHED_TM1.5.r#L6-L19

:: User input (via command line argument)
:: ----------------------------------------------------------------
set SCENARIO_DIR=%1

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

:remove quotes
Set SCENARIO_DIR_NoQuotes=%SCENARIO_DIR:"=%

python "X:\travel-model-one-master\utilities\cube-to-shapefile\correspond_link_to_TAZ.py" "%SCENARIO_DIR_NoQuotes%\INPUT\hwy\forPHED\freeflow_links.shp" "%SCENARIO_DIR_NoQuotes%\INPUT\hwy\forPHED\freeflow_links_UA.csv" --shapefile "X:\travel-model-one-master\utilities\TIP\SelectedUrbanizedAreas\FiveUZA_NAD1983UTMzone10N.shp"  --shp_id NAME10

:: run the R script that calculates the PHED metric
:: ----------------------------------------------------------------
:: set R location
set R_HOME=C:\Program Files\R\R-3.5.2

call "%R_HOME%\bin\x64\Rscript.exe" X:\travel-model-one-master\utilities\TIP\federal_metric_PHED_TM1.5.R