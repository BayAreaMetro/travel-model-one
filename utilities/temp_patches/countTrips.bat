
:: set ITER, SAMPLESHARE, FUTURE

del main\trips*.dat
del main\tripsAM_no_zpv_allinc.tpp
del metrics\auto_times.csv

call CTRAMP\runtime\SetPath.bat
call RunMetrics.bat

