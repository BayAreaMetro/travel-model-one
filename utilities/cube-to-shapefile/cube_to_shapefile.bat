REM this is the command to generate shapefiles for a particular project

:: run this from [M_DIR]\OUTPUT\shapefile
:: e.g. M:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects\1_Crossings3\2050_TM151_PPA_RT_01_1_Crossings3_00\OUTPUT\shapefile



:: first set to use arcgis version of python so we can use arcpy
set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts

python \\mainmodel\MainModelShare\travel-model-one-master\utilities\cube-to-shapefile\cube_to_shapefile.py --linefile ..\..\trn\transitLines.lin --trn_stop_info "M:\Application\Model One\Networks\TM1_2015_Base_Network\Node Description.xls" --loadvol_dir ..\trn ..\avgload5period.net
