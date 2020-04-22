:: ** Work in progress batch file to execute steps needed for EMFAC2014 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                           **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** New Futures Runs for Fuel Consumption and Fuel Economy Estimates                   **
:: ** These runs forward account for speed bin VMT overlap      hmb.   12/11/19.         **

:: added an argument to indicate whether we are running emfac for SB375 (no trucks)
:: To run this batch file, use command: 
:: RunPrepareEmfac.bat SB375
:: (Or, RunPrepareEmfac.bat Conformity)

call  ctramp\runtime\setpath
mkdir emfac_prep

:: Step One
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsBetweenZones.job

:: Step Two
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsWithinZones.job

:: Step Three

:: use the "no truck" files if the run is for SB375
if %1==SB375 rename emfac_prep\CreateSpeedBinsBetweenZones_sums.csv CreateSpBetweenZones_NotUsed.csv
if %1==SB375 rename emfac_prep\CreateSpeedBinsWithinZones_sums.csv CreateSpWithinZones_NotUsed.csv

:: use the "with truck" files if the run is for conformity
if %1==conformity rename emfac_prep\CreateSpeedBinsBetweenZones_sums_NoTrk.csv CreateSpBetweenZonesNoTruck_NotUsed.csv
if %1==conformity rename emfac_prep\CreateSpeedBinsWithinZones_sums_NoTrk.csv CreateSpWithinZonesNoTruck_NotUsed.csv

call gawk -f CTRAMP\scripts\emfac\SumSpeedBins1.awk emfac_prep\CreateSpeedBins*.csv


move HourlyTotalCounty.csv emfac_prep\HourlyTotalCounty.csv
move ShareSpeedBinsAll_sums.csv emfac_prep\ShareSpeedBinsAll_sums.csv
move SumSpeedBinsAll_sums.csv emfac_prep\SumSpeedBinsAll_sums.csv