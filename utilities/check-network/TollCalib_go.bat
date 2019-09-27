rem -------------------------------------
rem
rem This batch file copies the inputs and scripts needed for toll calibration. 
rem It requires two user inputs (re. network_links.dbf and TOLLCLASS_Designations.xlsx)
rem Scripts are copied from travel-model-one-master on the X drive.
rem 
rem -------------------------------------


rem need user inputs here
rem -------------------------------------

rem where is network_links.dbf?
set UNLOADED_NETWORK_DBF= \\tsclient\L\RTP2021_PPA\Projects\3000_ExpLanes_Calib\2050_TM151_PPA_RT_14_3000_ExpLanes_Calib_00\OUTPUT\shapefiles\network_links.dbf

rem where is TOLLCLASS Designations.xlsx?
rem (this file indicates which facilities have mandatory s2 tolls)
set TOLL_DESIGNATIONS_XLSX= \\tsclient\L\RTP2021_PPA\Projects\TOLLCLASS_Designations.xlsx

rem if this is being run on aws, what's the Private IP Address?
if %computername%==WIN-A4SJP19GCV5     set HOST_IP_ADDRESS=10.0.0.70

rem what is the location of the base run (i.e. pre toll calibration) directory - the full run is needed because it needs the CTRAMP directory
set MODEL_BASE_DIR=D:\Projects\2050_TM151_PPA_CG_14_3000_ExpLanes_Calib_00

:: Where do you want the toll calibration outputs to be stored?
:: (this shoudl be the location of the output folder "tollcalib_iter" on the L drive)
set L_DIR=\\tsclient\L\RTP2021_PPA\Projects\3000_ExpLanes_Calib\2050_TM151_PPA_CG_14_3000_ExpLanes_TollCalib_00


rem copy the two toll calibration inputs 
rem -------------------------------------
mkdir tollcalib_iter

copy %UNLOADED_NETWORK_DBF%      tollcalib_iter\network_links.dbf
copy %TOLL_DESIGNATIONS_XLSX%    tollcalib_iter\TOLLCLASS_Designations.xlsx


rem copy the five toll calibration scripts 
rem -------------------------------------

copy \\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_checkITER3.bat TollCalib_checkITER3.bat

copy \\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_Iterate.bat TollCalib_Iterate.bat

copy \\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_RunModel.bat TollCalib_RunModel.bat

copy \\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_CheckSpeeds.R TollCalib_CheckSpeeds.R

copy \\tsclient\X\travel-model-one-master\utilities\check-network\TollCalib_stop.py TollCalib_stop.py

rem generate a tolls_iter4.csv
rem -------------------------------------
call TollCalib_checkITER3.bat

rem iterate
rem -------------------------------------
call TollCalib_iterate.bat


