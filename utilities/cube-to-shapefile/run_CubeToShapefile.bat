REM This batch script runs the cube_to_shapefile.py script for a single project 
REM It will be copied to OUTPUT\shapefile at the end of each model run
REM To generate the loaded network shapefiles, users will need to run this batch script from a machine that has arcpy and access to mainmodel
REM Additionally, to run prepare_link_shp_for_tableau_offset.py, this script needs to be run in a python environment that has geopandas installed

set Original_path=%path%

set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts
set PYTHONPATH=%PYTHONPATH%;C:\Users\%USERNAME%\Documents\GitHub\NetworkWrangler;C:\Users\%USERNAME%\Documents\GitHub\NetworkWrangler\_static

call python \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\cube_to_shapefile.py  --trn_stop_info "M:\\Application\Model One\\Networks\\TM1_2015_Base_Network\\Node Description.xls" --linefile ..\\..\\INPUT\\trn\\transitLines.lin --loadvol_dir ..\\trn ..\\avgload5period.net --transit_crowding ..\metrics\transit_crowding_complete.csv
if ERRORLEVEL 1 goto done

REM Switch to an environment that has geopandas
REM After that, prepare_link_shp_for_tableau_offset.py takes about 20 minutes to run
set path=%Original_path%
if %username%==mtcpb  (call activate geo_env)
if %username%==ftsang (call activate geo_env)

call python \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\prepare_link_shp_for_tableau_offset.py . network_links.shp
if ERRORLEVEL 1 goto done

copy \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\RoadwaySpeedViewer.twb .

:done