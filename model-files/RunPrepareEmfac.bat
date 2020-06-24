:: ** Work in progress batch file to execute steps needed for EMFAC2014 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                           **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** New Futures Runs for Fuel Consumption and Fuel Economy Estimates                   **
:: ** These runs forward account for speed bin VMT overlap      hmb.   12/11/19.         **

:: added an argument to indicate whether we are running emfac with no trucks
:: To run this batch file, use command: 
:: RunPrepareEmfac.bat WithFreight
:: (Or, RunPrepareEmfac.bat NoFreight)

: make sure the user specifies either NoFreight or WithFreight in the argument
IF %1==NoFreight    goto :start
IF %1==WithFreight  goto :start 
:: if neither, print error_message
ECHO User Error: Please make sure "NoFreight" or "WithFreight" is specified. Note that it is case-sensitive."
GOTO :end
 
:start
call  ctramp\runtime\setpath
mkdir emfac_prep

:: Step One
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsBetweenZones.job

:: Step Two
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsWithinZones.job

:: Step Three

:: if we want to run emfac without freight, use the "no truck" file
if %1==NoFreight rename emfac_prep\CreateSpeedBinsBetweenZones_sums.csv CreateSpBetweenZones_NotUsed.csv
if %1==NoFreight rename emfac_prep\CreateSpeedBinsWithinZones_sums.csv CreateSpWithinZones_NotUsed.csv

:: if we want to run emfac with freight, use the "with truck" files 
if %1==WithFreight rename emfac_prep\CreateSpeedBinsBetweenZones_sums_NoTrk.csv CreateSpBetweenZonesNoTruck_NotUsed.csv
if %1==WithFreight rename emfac_prep\CreateSpeedBinsWithinZones_sums_NoTrk.csv CreateSpWithinZonesNoTruck_NotUsed.csv

call gawk -f CTRAMP\scripts\emfac\SumSpeedBins1.awk emfac_prep\CreateSpeedBins*.csv


move HourlyTotalCounty.csv emfac_prep\HourlyTotalCounty.csv
move ShareSpeedBinsAll_sums.csv emfac_prep\ShareSpeedBinsAll_sums.csv
move SumSpeedBinsAll_sums.csv emfac_prep\SumSpeedBinsAll_sums.csv

:end