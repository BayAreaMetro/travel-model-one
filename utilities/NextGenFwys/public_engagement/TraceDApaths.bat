:: Batch file for outputting the AM drive-alone non tolled path and drive-alone tolled path for selected ODs
:: On our modeling machines, it takes about 45 minutes to generate a set of paths for one pair of OD
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

set ORIGIN=1,100,1000
set DESTINATION=234,456
runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\HwyAssign_trace.job

