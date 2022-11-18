REM This batch script runs the cube_to_shapefile.py script for a single project
REM It will be copied to OUTPUT\shapefile at the end of each model run
REM To generate the loaded network shapefiles, users will need to run this batch script from a machine that has arcpy and access to mainmodel
REM Todo: It also copies the TransitUtilizationViewer.twb file from github and renames it to TransitUtilizationViewer.twb

set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts
set PYTHONPATH=%PYTHONPATH%;C:\Users\%USERNAME%\Documents\GitHub\NetworkWrangler;C:\Users\%USERNAME%\Documents\GitHub\NetworkWrangler\_static

python \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\cube_to_shapefile.py  --trn_stop_info "M:\\Application\Model One\\Networks\\TM1_2015_Base_Network\\Node Description.xls" --linefile ..\\..\\INPUT\\trn\\transitLines.lin --loadvol_dir ..\\trn ..\\avgload5period.net --transit_crowding ..\metrics\transit_crowding_complete.csv

copy \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\RoadwaySpeedViewer.twb .