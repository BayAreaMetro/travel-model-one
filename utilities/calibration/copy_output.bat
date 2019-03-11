SETLOCAL EnableDelayedExpansion

set MODEL_DIR=A:\TM150_Calibration\2015_TM150_calib11
set TARGET_DIR=M:\Development\Travel Model One\Calibration\Version 1.5.0\2015_TM150_calib11
set CODE_DIR=X:\travel-model-one-calibration\utilities\calibration
set ITER=1
set SAMPLESHARE=0.2

mkdir "%TARGET_DIR%"
cd "%TARGET_DIR%"

:export_skims

mkdir OUTPUT\skims
cd OUTPUT\skims

set TIMEPERIOD=MD
set TABLE=DISTDA

set SKIMFILE=HWYSKM%TIMEPERIOD%
if not exist %SKIMFILE%_%TABLE%.csv (
  runtpp "%CODE_DIR%\extract_skim_table.job"
  IF ERRORLEVEL 2 goto done
)

set TABLE=TIMEDA
if not exist %SKIMFILE%_%TABLE%.csv (
  runtpp "%CODE_DIR%\extract_skim_table.job"
  IF ERRORLEVEL 2 goto done
)

:: all transit skims
set COMMPATH=C:\Users\lzorn\Documents\scratch\COMMPATH
if not exist trnskmam_wlk_loc_wlk.csv (
  runtpp "%CODE_DIR%\extract_trnskim_tables.job"
  IF ERRORLEVEL 2 goto done
)

:: todo: update to read consolidated transit skims
:: if not exist skim_OD_districts.csv  Rscript --vanilla "%CODE_DIR%\skim_district_summary.R"
cd ..\..

mkdir OUTPUT\main
copy %MODEL_DIR%\main\aoResults.csv            OUTPUT\main
copy %MODEL_DIR%\main\wsLocResults_%ITER%.csv  OUTPUT\main
copy %MODEL_DIR%\main\cdapResults.csv          OUTPUT\main
copy %MODEL_DIR%\main\indivTourData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\jointTourData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\indivTripData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\jointTripData_%ITER%.csv OUTPUT\main

mkdir OUTPUT\calibration
Rscript --vanilla "%CODE_DIR%\01_usual_work_school_location_TM.R"
Rscript --vanilla "%CODE_DIR%\02_auto_ownership_TM.R"
Rscript --vanilla "%CODE_DIR%\04_daily_activity_pattern_TM.R"
Rscript --vanilla "%CODE_DIR%\11_tour_mode_choice_TM.R"
Rscript --vanilla "%CODE_DIR%\15_trip_mode_choice_TM.R"

:done