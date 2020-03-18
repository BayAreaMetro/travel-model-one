:: ** Work in progress batch file to execute steps needed for EMFAC2014 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                           **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** New Futures Runs for Fuel Consumption and Fuel Economy Estimates                   **
:: ** These runs forward account for speed bin VMT overlap      hmb.   12/11/19.         **

call  ctramp\runtime\setpath
mkdir emfac_output

:: Step One
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsBetweenZones.job

:: Step Two
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsWithinZones.job

:: Step Three
call gawk -f CTRAMP\scripts\emfac\SumSpeedBins1.awk emfac_output\CreateSpeedBins*.csv


move HourlyTotalCounty.csv emfac_output\HourlyTotalCounty.csv
move ShareSpeedBinsAll_sums.csv emfac_output\ShareSpeedBinsAll_sums.csv
move SumSpeedBinsAll_sums.csv emfac_output\SumSpeedBinsAll_sums.csv