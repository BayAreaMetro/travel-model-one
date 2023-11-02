
:: batch file for printing out transit paths
:: current working directory should be the directory of the full model on a modeling server e.g. E:\Model2D-Share\Projects\2035_TM152_NGF_NP10


:: in a full model run, the following is done in setupmodel.bat
:: --------------------------------------------------------------------------
:: MODEL_DIR is needed in TransitAssign.job
set MODEL_DIR=%CD%


:: in a full model run, the following is done in \CTRAMP\runtime\setpath.bat
:: --------------------------------------------------------------------------
:: set commpath
if %computername%==MODEL2-A      (  set COMMPATH=E:\Model2A-Share\COMMPATH)
if %computername%==MODEL2-B      (  set COMMPATH=E:\Model2B-Share\COMMPATH)
if %computername%==MODEL2-C      (  set COMMPATH=E:\Model2C-Share\COMMPATH)
if %computername%==MODEL2-D      (  set COMMPATH=E:\Model2D-Share\COMMPATH)
if %computername%==MODEL3-A      (  set COMMPATH=E:\Model3A-Share\COMMPATH)
if %computername%==MODEL3-B      (  set COMMPATH=E:\Model3B-Share\COMMPATH)
if %computername%==MODEL3-C      (  set COMMPATH=E:\Model3C-Share\COMMPATH)
if %computername%==MODEL3-D      (  set COMMPATH=E:\Model3D-Share\COMMPATH)

:: set the location of the RUNTPP executable from Citilabs
set PATH=%PATH%;C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI


:: in a full model run, the following is done in runmodel.bat
:: --------------------------------------------------------------------------
:: Start the cube cluster
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

:: run transit assignment in iteration 3 with trace
set iter=3
cd trn\TransitAssignment.iter%ITER%
runtpp X:\travel-model-one-master\utilities\NextGenFwys\public_engagement\TransitAssign_NGFtrace.job
