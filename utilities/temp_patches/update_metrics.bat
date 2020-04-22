:: set ITER, SAMPLESHARE, FUTURE

:: update metrics
::
:: copy over updated lookups
copy /Y "\\tsclient\C\Users\lzorn\Box\Modeling and Surveys\Development\Travel Model 1.5\Model_inputs\*.csv" INPUT\metrics
:: copy over updated scripts
copy /Y \\tsclient\X\travel-model-one-master\utilities\RTP\metrics\* CTRAMP\scripts\metrics
copy /Y \\tsclient\X\travel-model-one-master\utilities\RTP\RunMetrics.bat .

:: clear old results
del metrics\*
del hwy\iter%ITER%\avgload5period_vehclasses.csv

runtpp CTRAMP\scripts\metrics\temp_create_av.job

RunMetrics.bat