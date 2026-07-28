SETLOCAL EnableDelayedExpansion

set MODEL_DIR=\\MODEL2-B\Model2B-Share\Projects\2015_TM152_IPA_17
set TARGET_DIR=M:\Development\Travel Model One\Calibration\Version 1.5.2\2015_TM152_IPA_17
set CODE_DIR=X:\travel-model-one-calib1.5.2\utilities\calibration
rem start at 00 when INPUT or skims are updated
set CALIB_ITER=00

echo CALIB_ITER=%CALIB_ITER%

mkdir "%TARGET_DIR%"
cd "%TARGET_DIR%"

if "%CALIB_ITER%"=="00" (
  echo Exporting skims
  set ITER=3
  set SAMPLESHARE=0.5
) else (
  set ITER=1
  set SAMPLESHARE=0.2
  goto do_calib_iter
)

:export_skims

mkdir OUTPUT_00\skims
cd OUTPUT_00\skims

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
Cluster "%COMMPATH%\CTRAMP" 1-15 Starthide Exit

if not exist trnskmam_wlk_loc_wlk.csv (
  runtpp "%CODE_DIR%\extract_trnskim_tables.job"
  IF ERRORLEVEL 2 goto done
)

:: todo: update to read consolidated transit skims
:: if not exist skim_OD_districts.csv  Rscript --vanilla "%CODE_DIR%\skim_district_summary.R"
cd ..\..

:: goto here for just a calib iteration
:do_calib_iter

mkdir OUTPUT_%CALIB_ITER%
mkdir OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\aoResults.csv            OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\wsLocResults_%ITER%.csv  OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\cdapResults.csv          OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\indivTourData_%ITER%.csv OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\jointTourData_%ITER%.csv OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\indivTripData_%ITER%.csv OUTPUT_%CALIB_ITER%\main
copy %MODEL_DIR%\main\jointTripData_%ITER%.csv OUTPUT_%CALIB_ITER%\main

mkdir OUTPUT_%CALIB_ITER%\calibration
Rscript --vanilla "%CODE_DIR%\01_usual_work_school_location_TM.R"
Rscript --vanilla "%CODE_DIR%\02_auto_ownership_TM.R"
Rscript --vanilla "%CODE_DIR%\04_daily_activity_pattern_TM.R"
Rscript --vanilla "%CODE_DIR%\09_nonwork_destination_choice_TM.R"
Rscript --vanilla "%CODE_DIR%\11_tour_mode_choice_TM.R"
Rscript --vanilla "%CODE_DIR%\15_trip_mode_choice_TM.R"

:done