:: This can be run from a model run directory on a modeling machine OR
:: from the model run directory on M.
::
:: However, the first time it runs it needs to run on a modeling machine
:: since the modeling output files are used. The functionality for running
:: on M is for testing variations later.
::
:: added an argument to indicate whether we are running emfac with no trucks
:: To run this batch file, use command: 
:: RunPrepareEmfac.bat SB375 WithFreight 
:: (Or, RunPrepareEmfac.bat Plan-EIR WithFreight)
::

echo on
setlocal enabledelayedexpansion

: make sure the user specifies either SB375 or Plan-EIR in the argument
IF "%1"=="" (
  ECHO Please make sure the required arguments are specified.
  ECHO First argument can be either "SB375" or "EIR""
  ECHO Second argument should always WithFreight, until further notice.
  ECHO For example, the command for running this script can be: RunPrepareEmfac.bat SB375 WithFreight 
  GOTO :end
)

IF %1==SB375    goto check_argument2
IF %1==EIR      goto check_argument2 
:: if neither, print error_message
ECHO Please make sure "SB375" or "EIR" is specified. Note that it is case-sensitive.
GOTO :end

: make sure the user specifies either NoFreight or WithFreight in the argument
:check_argument2 
IF %2==NoFreight    goto start
IF %2==WithFreight  goto start 
:: if neither, print error_message
ECHO Please make sure "NoFreight" or "WithFreight" is specified. Note that it is case-sensitive.
GOTO :end

:start
:: If we're running on the M drive, paths are relative to OUTPUT
set EMFAC_DIR=emfac
set EMFAC_SCRIPT_DIR=CTRAMP\scripts\emfac
if exist OUTPUT\ (
  set EMFAC_DIR=OUTPUT\emfac
  set EMFAC_SCRIPT_DIR=X:\travel-model-one-master\model-files\scripts\emfac
)
echo EMFAC_DIR=%EMFAC_DIR%
echo EMFAC_SCRIPT_DIR=%EMFAC_SCRIPT_DIR%
echo MODEL_YEAR=%MODEL_YEAR%
mkdir %EMFAC_DIR%\emfac_prep

:: Step One
:: input:  hwy\iter3\avgload5period_vehclasses.csv
:: output: emfac\emfac_prep\CreateSpeedBinsBetweenZones_sums.csv
if not exist %EMFAC_DIR%\emfac_prep\CreateSpeedBinsBetweenZones_sums.csv (
  python %EMFAC_SCRIPT_DIR%\betweenzonesvmt.py
)

:: Step Two
:: input:  main\trips[EA|AM|MD|PM|EV].tpp
::         skims\hwyskm[EA|AM|MD|PM|EV].tpp
::         skims\com_hwyskim[EA|AM|MD|PM|EV].tpp
:: output: emfac\emfac_prep\CreateSpeedBinsWithinZones_sums.csv
::         emfac\emfac_prep\CreateSpeedBinsWithinZones_sums_NoTrk.csv
if not exist %EMFAC_DIR%\emfac_prep\CreateSpeedBinsWithinZones_sums.csv (
  call runtpp %EMFAC_SCRIPT_DIR%\CreateSpeedBinsWithinZones.job

  rem if we want to run emfac without freight, use the "no truck" file
  if %2==NoFreight rename %EMFAC_DIR%\emfac_prep\CreateSpeedBinsWithinZones_sums.csv %EMFAC_DIR%\emfac_prep\CreateSpWithinZones_NotUsed.csv

  rem if we want to run emfac with freight, use the "with truck" files 
  if %2==WithFreight rename %EMFAC_DIR%\emfac_prep\CreateSpeedBinsWithinZones_sums_NoTrk.csv %EMFAC_DIR%\emfac_prep\CreateSpWithinZonesNoTruck_NotUsed.csv
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

if %1==SB375 (
  if %MODEL_YEAR% EQU 2005 (set emfacVersion=2007)
  if %MODEL_YEAR% EQU 2015 (set emfacVersion=2014)
  if %MODEL_YEAR% EQU 2020 (set emfacVersion=2014)
  if %MODEL_YEAR% EQU 2023 (set emfacVersion=2014)
  :: rem for SACOG's federal air quality plan
  if %MODEL_YEAR% EQU 2026 (set emfacVersion=2014)
  if %MODEL_YEAR% EQU 2035 (set emfacVersion=2014)
  if %MODEL_YEAR% EQU 2050 (set emfacVersion=2014)
)

if %1==EIR (
  if %MODEL_YEAR% EQU 2005 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2015 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2020 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2023 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2030 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2035 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2040 (set emfacVersion=2017)
  if %MODEL_YEAR% EQU 2050 (set emfacVersion=2017)
)
echo emfacVersion=%emfacVersion%

:: run the emfac prep script with arguments related to how we'll run emfac
python %EMFAC_SCRIPT_DIR%\create_EMFAC_custom_activity_file.py --analysis_type %1 --emfac %emfacVersion% --run_mode emissions --sub_area MPO-MTC --season annual --VMT_data_type totalDailyVMT --custom_hourly_speed_fractions

:: for EIR, also run SEASON=winter and EMFAC2021
if %1==EIR (
  python %EMFAC_SCRIPT_DIR%\create_EMFAC_custom_activity_file.py --analysis_type %1 --emfac %emfacVersion% --run_mode emissions --sub_area MPO-MTC --season winter --VMT_data_type totalDailyVMT --custom_hourly_speed_fractions
  python %EMFAC_SCRIPT_DIR%\create_EMFAC_custom_activity_file.py --analysis_type %1 --emfac 2021 --run_mode emissions --sub_area MPO-MTC --season annual --VMT_data_type totalDailyVMT --custom_hourly_speed_fractions

)

:end