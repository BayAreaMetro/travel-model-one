:: Batch file for outputting the AM drive-alone non tolled path and drive-alone tolled path for selected ODs
:: On our modeling machines, it takes about 45 minutes to complete one highway assignment iteration
:: The time taken doesn't change significantly when we increase the number of OD paths to be printed out 
:: The output paths can be found in 
:: The output file are %MODEL_DIR%\HwyAssign_trace\DApath_I%ORIGIN%_J%DESTINATION%.log and %MODEL_DIR%\HwyAssign_trace\DAtollpath_I%ORIGIN%_J%DESTINATION%.log  

:: ------------------------------
:: initial setup
:: user to change to the full model run directory in the command prompt e.g. A:\Projects\2035_TM152_NGF_NP10_Path2a_02
:: ------------------------------

set MODEL_DIR=%CD%

:: create a directory for the outputs
mkdir HwyAssign_trace

:: set commpath
if %computername%==MODEL2-A      (  set COMMPATH=E:\Model2A-Share\COMMPATH)
if %computername%==MODEL2-B      (  set COMMPATH=E:\Model2B-Share\COMMPATH)
if %computername%==MODEL2-C      (  set COMMPATH=E:\Model2C-Share\COMMPATH)
if %computername%==MODEL2-D      (  set COMMPATH=E:\Model2D-Share\COMMPATH)
if %computername%==MODEL3-A      (  set COMMPATH=E:\Model3A-Share\COMMPATH)
if %computername%==MODEL3-B      (  set COMMPATH=E:\Model3B-Share\COMMPATH)
if %computername%==MODEL3-C      (  set COMMPATH=E:\Model3C-Share\COMMPATH)
if %computername%==MODEL3-D      (  set COMMPATH=E:\Model3D-Share\COMMPATH)

:: start Cube Cluter 
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit


:: ------------------------------
:: specify selected ODs below
:: use comma seperated values
:: ------------------------------

set ORIGIN=410,972,146,478,820,767,558,607,234,16,742,1178,81,296,355,315,677,1145,1098,1176,1083,189,991,700,1421,1448,1270,1246,1366,1336,1402,1291,1412,1311
set DESTINATION=4,971,115,75,429,1019,558,871,355,311,257,608,1061,212,460,1113,777,188,1361,1146,742,1262,1439,1224,1299,1204,660,1342,1430,1168,707,1413,1310,1399
runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\HwyAssign_trace.job

