
rem ------------------------------------------------------------------------------------------
rem
rem Often, while waiting for the pre-toll-calibration run to complete, the analyst may perform further QAQC of the network and correct errors in the network.
rem If these errors are NOT significant, the analyst might choose not to rerun the pre-toll-calibration run, 
rem and proceed with the toll calibration procedure using the updated network.
rem
rem In such cases, prior to starting the toll calibration procedure, 
rem analysts will need to swap the freeflow.net and tolls.csv in the pre-toll-calibration run (aka the base run)
rem 
rem The following commands perform these network swapping steps.
rem 
rem ------------------------------------------------------------------------------------------



rem ---------------------------------------------
rem User inputs
rem ---------------------------------------------

set PreTollCalibRun=\\MODEL2-B\Model2B-Share\Projects\2035_TM160_NGFr2_NP04_Path6_01_pretollcalib
set NewNetwork=L:\Application\Model_One\NextGenFwys_Round2\INPUT_DEVELOPMENT\Networks\NGF_Networks_NGFround2_P6_13\NGF_R2_R2P6_Dual_Express_Lanes_network_2035


rem ---------------------------------------------
rem Typically, there is not need to change the following.
rem
rem Commands to replace the freeflow.net and tolls.csv in pre-toll-calibration run (aka the base run):
rem ---------------------------------------------

rem ------------------------
rem freeflow.net
rem ------------------------

rem -------------
rem in /hwy
rem -------------

rem save a copy of the original freeflow.net
copy %PreTollCalibRun%\hwy\freeflow.net %PreTollCalibRun%\hwy\freeflow_used_in_pre_toll_calibration.net

rem replace it with the revised freeflow.net
copy %NewNetwork%\hwy\freeflow.net %PreTollCalibRun%\hwy\freeflow.net

rem -------------
rem in /INPUT/hwy
rem -------------
rem save a copy of the original freeflow.net
copy %PreTollCalibRun%\INPUT\hwy\freeflow.net %PreTollCalibRun%\INPUT\hwy\freeflow_used_in_pre_toll_calibration.net

rem replace it with the revised freeflow.net
copy %NewNetwork%\hwy\freeflow.net %PreTollCalibRun%\INPUT\hwy\freeflow.net

rem ------------------------
rem tolls.csv
rem ------------------------

rem -------------
rem in /hwy
rem -------------

rem save a copy of the original tolls.csv
copy %PreTollCalibRun%\hwy\tolls.csv %PreTollCalibRun%\hwy\tolls_used_in_pre_toll_calibration.csv

rem replace it with the revised freeflow.net
copy %NewNetwork%\hwy\tolls.csv %PreTollCalibRun%\hwy\tolls.csv


rem -------------
rem in /INPUT/hwy
rem -------------

rem save a copy of the original tolls.csv
copy %PreTollCalibRun%\INPUT\hwy\tolls.csv %PreTollCalibRun%\INPUT\hwy\tolls_used_in_pre_toll_calibration.csv

rem replace it with the revised freeflow.net
copy %NewNetwork%\hwy\tolls.csv %PreTollCalibRun%\INPUT\hwy\tolls.csv

pause