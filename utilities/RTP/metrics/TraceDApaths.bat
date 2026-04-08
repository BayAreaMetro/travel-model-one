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


:: Route	Origin	Destination
:: Antioch_SF	1187	17
:: Vallejo_SF	1223	17
:: SanJose_SF	558	17
:: Oakland_SanJose	967	434
:: Oakland_SF	946	17
:: Livermore-SJ	721	555
:: Santa Rosa - SF Financial Dist	1376	24
:: Antioch-Oakland	1187	981
:: Fairfield-Dublin	1266	733
:: Oakland-Palo Alto	967	358

set ORIGIN=1187,1223,558,967,946,721,1376,1187,1266,967
set DESTINATION=17,434,555,24,981,733,358
runtpp E:\Model3D-Share\Projects\2050_TM161_FBP_Plan_16_trace\CTRAMP\scripts\assign\HwyAssign_trace.job
