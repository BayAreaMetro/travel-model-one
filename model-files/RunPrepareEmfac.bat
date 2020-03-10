:: ** Work in progress batch file to execute steps needed for EMFAC2011 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                          **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** San Rafael Bridge Updated Conformity Runs    hmb.   3/27/15.                       **

call ctramp\runtime\setpath

:: Step One
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsBetweenZones.job

:: Step Two
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsWithinZones.job

:: Step Three
call gawk -f CTRAMP\scripts\emfac\SumSpeedBins1.awk emfac\CreateSpeedBins*.csv


move HourlyTotalCounty.csv emfac\HourlyTotalCounty.csv
move ShareSpeedBinsAll_sums.csv emfac\ShareSpeedBinsAll_sums.csv
move SumSpeedBinsAll_sums.csv emfac\SumSpeedBinsAll_sums.csv
