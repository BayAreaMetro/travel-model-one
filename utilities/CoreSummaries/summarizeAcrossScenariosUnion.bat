::
:: This version of summarizeAcrossScenarios.bat does not bother creating the extracts but instead copies the text files
:: over to use the union feature of Tableau
::

@echo on
setlocal enabledelayedexpansion

set COMBINED_DIR=across_rounds_v06_union
set RUN_NAME_SET=Horizon_Round1\2015_TM151_PPA_09 Horizon_Round1\2050_TM151_FU1_RT_01 Horizon_Round1\2050_TM151_FU1_CG_02 Horizon_Round1\2050_TM151_FU1_BF_02 Horizon_Round2\2050_TM151_FU2_RT_05 Horizon_Round2\2050_TM151_FU2_CG_04 Horizon_Round2\2050_TM151_FU2_BF_04

mkdir %COMBINED_DIR%

:: Set to 1 if running from the original model run directory
:: (e.g. subdirs = CTRAMP, database, hwy, INPUT, landuse, etc...)
:: Set to 0 if if running from from results directory
:: (e.g. M:\Application\, subdirs=INPUT,OUTPUT)
set ORIGINAL_RUNDIR=0

set CODE_DIR=X:\travel-model-one-master\model-files\scripts\core_summaries

IF %USERNAME%==lzorn (
  rem I AM SPECIAL
  set R_HOME=C:\Program Files\R\R-3.5.1
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.5
) ELSE (
  IF %USERNAME%==ftsang (
      set R_HOME=C:\Program Files\R\R-3.4.4
      set R_USER=%USERNAME%
      set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.4
  ) ELSE (
  set R_HOME=C:\Program Files\R\R-3.5.2
  set R_USER=%USERNAME%
  set R_LIBS_USER=C:\Users\%R_USER%\Documents\R\win-library\3.5
  )
)

:: copy over core_summary csv files
set FILES=ActiveTransport ActivityPattern AutomobileOwnership CommuteByEmploymentLocation CommuteByIncomeHousehold CommuteByIncomeJob JourneyToWork PerTripTravelTime TimeOfDay TimeOfDay_personsTouring TravelCost TripDistance VehicleMilesTraveled

for %%F in (%FILES%) DO (
  echo %%F
  for %%R in (%RUN_NAME_SET%) DO (
    echo %%R
    echo %%~nxR
    copy %%R\OUTPUT\core_summaries\%%F.csv %COMBINED_DIR%\%%F_%%~nxR.csv
  )
)

:: copy over avgload5period.csv files
for %%R in (%RUN_NAME_SET%) DO (
  echo %%R
  echo %%~nxR
  copy %%R\OUTPUT\avgload5period.csv %COMBINED_DIR%\avgload5period_%%~nxR.csv
)
  
:: copy over trnline.csv and trnlink.csv files
for %%R in (%RUN_NAME_SET%) DO (
  echo %%R
  echo %%~nxR
  copy %%R\OUTPUT\trn\trnline.csv %COMBINED_DIR%\trnline_%%~nxR.csv
  copy %%R\OUTPUT\trn\trnlink.csv %COMBINED_DIR%\trnlink_%%~nxR.csv
)

:done

:: c:\windows\system32\Robocopy.exe /E "X:\travel-model-one-master\utilities\CoreSummaries\tableau"       %COMBINED_DIR%
