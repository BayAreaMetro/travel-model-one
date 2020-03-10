:: ** Work in progress batch file to execute steps needed for EMFAC2014 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                           **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** New Futures Runs for Fuel Consumption and Fuel Economy Estimates                   **
:: ** These runs forward account for speed bin VMT overlap      hmb.   12/11/19.         **

call ctramp\runtime\setpath

:: Step One
call runtpp CTRAMP\scripts\emfac2\CreateSpeedBinsBetweenZns3.job

:: Step Two
call runtpp CTRAMP\scripts\emfac2\CreateSpeedBinsWithinZns2.job

:: Step Three
call gawk -f CTRAMP\scripts\emfac2\SumSpeedBins1.awk emfac2\CreateSpeedBins*.csv


move HourlyTotalCounty.csv emfac2\HourlyTotalCounty.csv
move ShareSpeedBinsAll_sums.csv emfac2\ShareSpeedBinsAll_sums.csv
move SumSpeedBinsAll_sums.csv emfac2\SumSpeedBinsAll_sums.csv
