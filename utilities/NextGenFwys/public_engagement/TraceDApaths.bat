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

:: Set default values for ORIGIN and DESTINATION
set ORIGIN=9,138,106,128,113,16,110,971,969,946,945,979,970,968,967,972,947,558,557,549,548,563,448,391,413,377,381,388,379,456,445,409,410,412,415,416,411
set DESTINATION=9,138,106,128,113,16,110,731,733,1188,1194,1190,1187,729,730,732,734,1183,1191,1193,1184,1065,1056,1058,1049,1060,1059,1050,309,304,317,315,313,312,325,531,529,681,564,559,528,526,323,320,301,524,525,487,491,485,490,488,484,479,460

:: Check if arguments are passed, otherwise use default values
if not "%1"=="" set ORIGIN=%1
if not "%2"=="" set DESTINATION=%2

runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\HwyAssign_trace.job

