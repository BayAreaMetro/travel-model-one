
: rename/delete old files
ren "INPUT\metrics\emissionsLookup.csv" "emissionsLookup_old.csv" 
ren "metrics\vmt_vht_metrics.csv" "vmt_vht_metrics_old.csv"

: get the correct input
copy "C:\Users\ftsang\Box\Modeling and Surveys\Development\Travel Model 1.5\Model_inputs\_Lookup Tables\emissionsLookup.csv" "INPUT\metrics\emissionsLookup.csv"

: access python
set path=%path%;c:\python27

: set environment variables
set ITER=3
set SAMPLESHARE=1.0
set FUTURE=BackToTheFuture
set CODE_DIR=.\CTRAMP\scripts\metrics

call python "%CODE_DIR%\hwynet.py" --filter %FUTURE% hwy\iter%ITER%\avgload5period_vehclasses.csv





