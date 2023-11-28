REM This batch script runs the respective Trace...Paths.bat scripts for driving and transit for the specified model runs below:
REM 2035_TM152_NGF_NP10_Path1a_02, 2035_TM152_NGF_NP10_Path4_02, 2035_TM152_NGF_NP10
REM Note: make sure to update paths based on mapped drives on the respective modeling server being used to run this batch script
REM Note: make sure to update the Origin and Destination lists
REM Note: make sure to update the OD version number
@echo off

ORIGIN="9,138,106,128,113,16,110,971,969,946,945,979,970,968,967,972,947,558,557,549,548,563,448,391,413,377,381,388,379,456,445,409,410,412,415,416,411"

DESTINATION="9,138,106,128,113,16,110,731,733,1188,1194,1190,1187,729,730,732,734,1183,1191,1193,1184,1065,1056,1058,1049,1060,1059,1050,309,304,317,315,313,312,325,531,529,681,564,559,528,526,323,320,301,524,525,487,491,485,490,488,484,479,460"

VersionNumber=11


:: PRODUCE THE DRIVEN TRACE FILES
:: saved on \\model3-a\Model3A-Share
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceDApaths.bat 

:: Clean the DApath.log and DAtollpath.log output files in HwyAssign_trace folder
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02

if exist HwyAssign_trace (

	cd HwyAssign_trace 

	copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\HwyAssign_trace_to_csv.py" "HwyAssign_trace_to_csv.py"*
)

python HwyAssign_trace_to_csv.py


:: RENAME HWYASSIGN_TRACE FOLDER
ren "X:\Projects\2035_TM152_NGF_NP10_Path1a_02\HwyAssign_trace" "HwyAssign_trace_v%VersionNumber%"


:: CREATE A FOLDER IN L: DRIVE TO STORE ALL THE RELEVANT FILES
if not exist L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\transit paths (v%VersionNumber%) mkdir L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\transit paths (v%VersionNumber%)


:: CREATE A SUBFOLDER TO MOVE DA PATHS TO
mkdir L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\transit paths (v%VersionNumber%)\DA paths


:: COPY DAPATHS TO SUBFOLDER
L:
cd L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\transit paths (v%VersionNumber%)\DA paths
copy /y "X:\Projects\2035_TM152_NGF_NP10_Path1a_02\HwyAssign_trace_v%VersionNumber%\DApath.csv" "DApath.csv"*
copy /y "X:\Projects\2035_TM152_NGF_NP10_Path1a_02\HwyAssign_trace_v%VersionNumber%\DAtollpath.csv" "DAtollpath.csv"*


:: PRODUCE THE TRANSIT TRACE FILES
:: saved on \\model3-a\Model3A-Share
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 

:: saved on \\MODEL2-C\Model2C-Share
Z:
cd Z:\Projects\2035_TM152_NGF_NP10_Path4_02
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 

:: saved on \\MODEL2-D\Model2D-Share
F:
cd F:\Projects\2035_TM152_NGF_NP10
Set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
call X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TraceTransitPaths.bat 


:: CLEAN TRANSIT TRACE FILES
X:
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_lin_to_csv.py" "Convert_lin_to_csv.py"*
python Convert_lin_to_csv.py
cd X:\Projects\2035_TM152_NGF_NP10_Path1a_02\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_PRN_to_CSV.py" "Convert_PRN_to_CSV.py"*
python Convert_PRN_to_CSV.py %ORIGIN% %DESTINATION% %VersionNumber%

Z:
cd Z:\Projects\2035_TM152_NGF_NP10_Path4_02\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_lin_to_csv.py" "Convert_lin_to_csv.py"*
python Convert_lin_to_csv.py
cd Z:\Projects\2035_TM152_NGF_NP10_Path4_02\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_PRN_to_CSV.py" "Convert_PRN_to_CSV.py"*
python Convert_PRN_to_CSV.py %ORIGIN% %DESTINATION% %VersionNumber%

F:
cd F:\Projects\2035_TM152_NGF_NP10\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_lin_to_csv.py" "Convert_lin_to_csv.py"*
python Convert_lin_to_csv.py
cd F:\Projects\2035_TM152_NGF_NP10\trn\TransitAssignment.iter3
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Convert_PRN_to_CSV.py" "Convert_PRN_to_CSV.py"*
python Convert_PRN_to_CSV.py %ORIGIN% %DESTINATION% %VersionNumber%


:: COPY FILES TO L: DRIVE
L:
cd L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\transit paths (v%VersionNumber%)
copy /y "X:\Projects\2035_TM152_NGF_NP10_Path1a_02\trn\TransitAssignment.iter3\tables_v%VersionNumber%\cleaned tables\TPPL_2035_TM152_NGF_NP10_Path1a_02.csv" "TPPL_2035_TM152_NGF_NP10_Path1a_02.csv"*
copy /y "Z:\Projects\2035_TM152_NGF_NP10_Path4_02\trn\TransitAssignment.iter3\tables_v%VersionNumber%\cleaned tables\TPPL_2035_TM152_NGF_NP10_Path4_02.csv" "TPPL_2035_TM152_NGF_NP10_Path4_02.csv"*
copy /y "F:\Projects\2035_TM152_NGF_NP10\trn\TransitAssignment.iter3\tables_v%VersionNumber%\cleaned tables\TPPL_2035_TM152_NGF_NP10.csv" "TPPL_2035_TM152_NGF_NP10.csv"*
copy /y "L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\network_nodes_TAZ\network_nodes_TAZ_2035_TM152_NGF_NP10_Path1a_02.csv" "network_nodes_TAZ_2035_TM152_NGF_NP10_Path1a_02.csv"*
copy /y "L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\network_nodes_TAZ\network_nodes_TAZ_2035_TM152_NGF_NP10_Path4_02.csv" "network_nodes_TAZ_2035_TM152_NGF_NP10_Path4_02.csv"*
copy /y "L:\Application\Model_One\NextGenFwys\metrics\Engagament Visualizations\network_nodes_TAZ\network_nodes_TAZ_2035_TM152_NGF_NP10.csv" "network_nodes_TAZ_2035_TM152_NGF_NP10.csv"*
copy /y "X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\Engagament Visualizations.twb" "Engagament Visualizations.twb"*


:: LOOKUP TRANSIT FARES AND PRODUCE LISTS OF ODS FOR DRIVE TO TRANSIT PORTIONS 
X:
cd X:\travel-model-one-master\utilities\NextGenFwys\public_engagement
python Lookup_transit_fare_using_OD_pairs_and_modes.py %ORIGIN% %DESTINATION% %VersionNumber%
cd X:\travel-model-one-master\utilities\NextGenFwys\public_engagement
python Extract_new_OD_pairs_to_trace_from_drive_to_transit.py %VersionNumber%


pause