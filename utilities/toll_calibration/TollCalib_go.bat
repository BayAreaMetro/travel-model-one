rem -------------------------------------
rem
rem This batch file copies the inputs and scripts needed for toll calibration. 
rem It requires six pieces of information
rem Scripts are copied from travel-model-one-master on the X drive.
rem 
rem -------------------------------------


rem need user inputs here
rem -------------------------------------

rem where is TOLLCLASS Designations.xlsx?
rem (this file indicates which facilities have mandatory s2 tolls)
set TOLL_DESIGNATIONS_XLSX=\\tsclient\L\RTP2021_PPA\Projects\TOLLCLASS_Designations.xlsx

rem if this is being run on aws, what's the Private IP Address?
if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=10.0.0.70

rem what is the location of the base run (i.e. pre toll calibration) directory - the full run is needed because it needs the CTRAMP directory
set MODEL_BASE_DIR=E:\Model2C-Share\Projects\2050_TM151_PPA_BF_17_preTollCalib

:: Where do you want the toll calibration outputs to be stored?
:: (this shoudl be the location of the output folder "tollcalib_iter" on the L drive)
set L_DIR=L:\RTP2021_PPA\Projects\2050_TM151_PPA_BF_17_preTollCalib

:: Configure target speed and max toll
set target_speed=45 
set max_toll=5


rem copy the two toll calibration inputs 
rem -------------------------------------
mkdir tollcalib_iter

copy %TOLL_DESIGNATIONS_XLSX%    tollcalib_iter\TOLLCLASS_Designations.xlsx


rem copy the five toll calibration scripts 
rem -------------------------------------

copy \\tsclient\X\travel-model-one-master\utilities\toll_calibration\TollCalib_checkITER3.bat TollCalib_checkITER3.bat

copy \\tsclient\X\travel-model-one-master\utilities\toll_calibration\TollCalib_Iterate.bat TollCalib_Iterate.bat

copy \\tsclient\X\travel-model-one-master\utilities\toll_calibration\TollCalib_RunModel.bat TollCalib_RunModel.bat

copy \\tsclient\X\travel-model-one-master\utilities\toll_calibration\TollCalib_CheckSpeeds.R TollCalib_CheckSpeeds.R

copy \\tsclient\X\travel-model-one-master\utilities\toll_calibration\TollCalib_stop.py TollCalib_stop.py

rem generate network_links.dbf
rem -------------------------------------
copy \\tsclient\X\travel-model-one-master\utilities\cube-to-shapefile\export_network.job  tollcalib_iter\export_network.job

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI
:: Add these variables to the PATH environment variable, moving the current path to the back
set PATH=%path%;%TPP_PATH%

set NET_INFILE=%MODEL_BASE_DIR%\INPUT\hwy\freeflow.net
set NODE_OUTFILE=tollcalib_iter\network_nodes.shp
set LINK_OUTFILE=tollcalib_iter\network_links.shp
runtpp tollcalib_iter\export_network.job

rem generate a tolls_iter4.csv
rem -------------------------------------
call TollCalib_checkITER3.bat

rem iterate
rem -------------------------------------
call TollCalib_iterate.bat

