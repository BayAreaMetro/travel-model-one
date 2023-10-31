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

set ORIGIN=312,301,304,1049,1190,1205,1183,729,734,732,730,1196,1184,1209,1193,492,491,492,491,490,489,488,487,486,485,484,479,460,1058,1050,1207,1202,1059,315,1060,317,1186,1199,1056,1065,309,731,733,1208,1189,1206,1198,1201,1192,1187,313,320,323,325,1204
set DESTINATION=603,602,579,563,561,557,556,555,554,550,549,548,547,546,492,491,490,489,488,487,486,485,484,479,460,435,407,402,401,400,399,398,397,396,377,376,375,374,373,347,41,39,38,37,36,35,27,25,24
runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\HwyAssign_trace.job

