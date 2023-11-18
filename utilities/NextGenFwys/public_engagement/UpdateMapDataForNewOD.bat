REM This batch script runs the respective Trace...Paths.bat scripts for driving and transit for the specified model runs below:
REM 2035_TM152_NGF_NP10_Path1a_02, 2035_TM152_NGF_NP10_Path4_02, 2035_TM152_NGF_NP10
REM Note: make sure to update paths based on mapped drives on the respective modeling server being used to run this batch script
REM Note: make sure to update the Origin and Destination lists
REM Note: make sure to update the OD version number
@echo off

ORIGIN="9,138,106,128,113,16,110,971,969,946,945,979,970,968,967,972,947,558,557,549,548,563,448,391,413,377,381,388,379,456,445,409,410,412,415,416,411"

DESTINATION="9,138,106,128,113,16,110,731,733,1188,1194,1190,1187,729,730,732,734,1183,1191,1193,1184,1065,1056,1058,1049,1060,1059,1050,309,304,317,315,313,312,325,531,529,681,564,559,528,526,323,320,301,524,525,487,491,485,490,488,484,479,460"

VersionNumber=11

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

pause