rem -------------------------------------
rem
rem This batch file copy the inputs and scripts needed for toll calibration. 
rem It takes two user inputs, whereas the scripts are copied from travel-model-one-master on the X drive.
rem 
rem -------------------------------------


rem need user inputs here
rem -------------------------------------

rem where is network_links.dbf?
set UNLOADED_NETWORK_DBF= \\tsclient\L\RTP2021_PPA\Projects\6000_ReX_Calib\2050_TM151_PPA_BF_11_6000_ReX_Calib_01\shapefiles\network_links.dbf

rem where is TOLLCLASS Designations.xlsx?
rem (this file indicates which facilities have mandatory s2 tolls)
set TOLL_DESIGNATIONS_XLSX= \\tsclient\L\RTP2021_PPA\Projects\6000_ReX_Calib\2050_TM151_PPA_BF_11_6000_ReX_Calib_01\tollcalib_iter\TOLLCLASS_Designations.xlsx


rem copy the three toll calibration inputs 
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
