:: ** Work in progress batch file to execute steps needed for EMFAC2014 input            **
:: ** Now only running"SumSpeedBins1.awk" script version which accounts for the          **
:: ** entire 9 County VMT [not Air Basin only] including Eastern Solano and Northern     **
:: ** Sonoma Counties.   ** With Original Speed Bin Ranges  **                           **
:: ** Based on Model One Version 0.3 Year [Forecast Yr]_03_YYY Run for VMT Calibration   **
:: ** New Futures Runs for Fuel Consumption and Fuel Economy Estimates                   **
:: ** These runs forward account for speed bin VMT overlap      hmb.   12/11/19.         **

:: added an argument to indicate whether we are running emfac with no trucks
:: To run this batch file, use command: 
:: RunPrepareEmfac.bat SB375 WithFreight 
:: (Or, RunPrepareEmfac.bat Plan-EIR WithFreight)


: make sure the user specifies either SB375 or Plan-EIR in the argument
IF "%1"=="" (ECHO Hi! Please make sure the required arguments are specified.
             ECHO First argument can be either "SB375" or "Plan-EIR""
             ECHO Second argument should always WithFreight, until further notice.
             ECHO For example, the command for running this script can be: RunPrepareEmfac.bat SB375 WithFreight 
             GOTO :end)

IF %1==SB375    goto check_argument2
IF %1==Plan-EIR  goto check_argument2 
:: if neither, print error_message
ECHO Hi! Please make sure "SB375" or "Plan-EIR" is specified. Note that it is case-sensitive."
GOTO :end

: make sure the user specifies either NoFreight or WithFreight in the argument
:check_argument2 
IF %2==NoFreight    goto start
IF %2==WithFreight  goto start 
:: if neither, print error_message
ECHO Hi! Please make sure "NoFreight" or "WithFreight" is specified. Note that it is case-sensitive."
GOTO :end
 
:start
call  ctramp\runtime\setpath
mkdir emfac_prep

:: Step One
python ctramp\scripts\emfac\betweenzonesvmt.py

:: Step Two
call runtpp CTRAMP\scripts\emfac\CreateSpeedBinsWithinZones.job

:: Step Three

: if we want to run emfac without freight, use the "no truck" file
if %2==NoFreight rename emfac_prep\CreateSpeedBinsWithinZones_sums.csv CreateSpWithinZones_NotUsed.csv

:: if we want to run emfac with freight, use the "with truck" files 
if %2==WithFreight rename emfac_prep\CreateSpeedBinsWithinZones_sums_NoTrk.csv CreateSpWithinZonesNoTruck_NotUsed.csv

:: --------------------------------------------------------------------------------------------
:: copy the EMFAC relevant custom activity template based on analysis year and SB375/notSB375
:: --------------------------------------------------------------------------------------------
:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

:: MODEL YEAR ------------------------- make sure it's numeric --------------------------------
set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul
if %MODEL_YEAR_NUM%==%MODEL_YEAR% (
  echo Numeric model year [%MODEL_YEAR%]
) else (
  echo Couldn't determine numeric model year from project dir [%PROJECT_DIR%]
  echo Guessed [%MODEL_YEAR%]
  exit /b 2
)
:: MODEL YEAR ------------------------- make sure it's in [2000,3000] -------------------------
if %MODEL_YEAR% LSS 2000 (
  echo Model year [%MODEL_YEAR%] is less than 2000
  exit /b 2
)
if %MODEL_YEAR% GTR 3000 (
  echo Model year [%MODEL_YEAR%] is greater than 3000
  exit /b 2
)

:: Figure out the EMFAC version
:: See Asana task "EMFAC version for next SCS": https://app.asana.com/0/310827677834656/820983836362952

:: SB375
::-----
:: Year 2005 - Emfac2007
:: Year 2020 - Emfac2014 / Emfac2007 as sensitivity test
:: Year 2035 - Emfac2014 / Emfac2007 as sensitivity test
:: Year 2050 - Emfac2014 (strictly speaking not needed, but we sometimes review the results from this)

:: Plan/EIR GHG + Emissions
::---------
:: Year 2015 - Emfac2017 (only if this is selected as EIR baseline)
:: Year 2020 - Emfac2017 (likely EIR baseline)
:: Year 2030 - Emfac2017 (AQ conformity)
:: Year 2035 - Emfac2017 (EIR, w/ and w/o clean car policies--not sure of relevance going forward)
:: Year 2040 - Emfac2017 (AQ Conformity)
:: Year 2050 - Emfac2017 (AQ Conformity + EIR)

if %1==SB375 if %MODEL_YEAR%==2005 (set emfacVersion=Emfac2007)
if %1==SB375 if %MODEL_YEAR%==2020 (set emfacVersion=Emfac2014)
if %1==SB375 if %MODEL_YEAR%==2035 (set emfacVersion=Emfac2014)
if %1==SB375 if %MODEL_YEAR%==2050 (set emfacVersion=Emfac2014)

if %1==Plan-EIR if %MODEL_YEAR%==2015 (set emfacVersion=Emfac2017)
if %1==Plan-EIR if %MODEL_YEAR%==2020 (set emfacVersion=Emfac2017)
if %1==Plan-EIR if %MODEL_YEAR%==2030 (set emfacVersion=Emfac2017)
if %1==Plan-EIR if %MODEL_YEAR%==2035 (set emfacVersion=Emfac2017)
if %1==Plan-EIR if %MODEL_YEAR%==2040 (set emfacVersion=Emfac2017)
if %1==Plan-EIR if %MODEL_YEAR%==2050 (set emfacVersion=Emfac2017)

:: as an example, the custom activity template for SB375 and analysis year 2035 is named as ByVehFuel_Emfac2014_SB375_Yr2035_11Subareas
set emfac_input_template=ByVehFuel_%emfacVersion%_%1_Yr%MODEL_YEAR%_11Subareas.xlsx
copy "CTRAMP\scripts\emfac\Custom_Activity_Templates\%emfac_input_template%" emfac_prep\%emfac_input_template%

:: run them emfac input template prep script
python CTRAMP\scripts\emfac\emfac_prep.py



:end