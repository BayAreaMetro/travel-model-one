set MODEL_DIR=A:\TM150_Calibration\2015_TM150_calib5
set TARGET_DIR=M:\Development\Travel Model One\Calibration\Version 1.5.0\2015_TM150_calib5
set CODE_DIR=X:\travel-model-one-calibration\utilities\calibration
set ITER=1
set SAMPLESHARE=0.20

mkdir "%TARGET_DIR%"
cd "%TARGET_DIR%"

mkdir OUTPUT\main
copy %MODEL_DIR%\main\aoResults.csv            OUTPUT\main
copy %MODEL_DIR%\main\wsLocResults_%ITER%.csv  OUTPUT\main
copy %MODEL_DIR%\main\cdapResults.csv          OUTPUT\main
copy %MODEL_DIR%\main\indivTourData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\jointTourData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\indivTripData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\jointTripData_%ITER%.csv OUTPUT\main

:export_skims

mkdir OUTPUT\skims
cd OUTPUT\skims
set TIMEPERIOD=MD
set TABLE=DISTDA

set SKIMFILE=HWYSKM%TIMEPERIOD%
if not exist %SKIMFILE%_%TABLE%.csv  runtpp "%CODE_DIR%\extract_skim_table.job"

:: ferry skims
set TABLE=ivtFerry
FOR %%H in (EA AM MD PM EV) DO (
   set SKIMFILE=trnskm%%H_wlk_lrf_drv
   if not exist %SKIMFILE%_%TABLE%.csv  runtpp "%CODE_DIR%\extract_skim_table.job"
   set SKIMFILE=trnskm%%H_drv_lrf_wlk
   if not exist %SKIMFILE%_%TABLE%.csv  runtpp "%CODE_DIR%\extract_skim_table.job"
   set SKIMFILE=trnskm%%H_wlk_lrf_wlk
   if not exist %SKIMFILE%_%TABLE%.csv  runtpp "%CODE_DIR%\extract_skim_table.job"
)

cd ..\..

mkdir OUTPUT\calibration
Rscript --vanilla "%CODE_DIR%\01_usual_work_school_location_TM.R"
Rscript --vanilla "%CODE_DIR%\02_auto_ownership_TM.R"
Rscript --vanilla "%CODE_DIR%\04_daily_activity_pattern_TM.R"
Rscript --vanilla "%CODE_DIR%\11_tour_mode_choice_TM.R"
Rscript --vanilla "%CODE_DIR%\14_trip_mode_choice_TM.R"

:done