set MODEL_DIR=F:\Projects\2015_TM150_calib3
set TARGET_DIR=M:\Development\Travel Model One\Calibration\Version 1.5.0\2015_TM150_calib3
set CODE_DIR=%USERPROFILE%\Documents\travel-model-one-transit\utilities\calibration
set ITER=2
set SAMPLESHARE=0.30

mkdir "%TARGET_DIR%"
cd "%TARGET_DIR%"

mkdir OUTPUT\main
copy %MODEL_DIR%\main\aoResults.csv            OUTPUT\main
copy %MODEL_DIR%\main\wsLocResults_%ITER%.csv  OUTPUT\main
copy %MODEL_DIR%\main\cdapResults.csv          OUTPUT\main
copy %MODEL_DIR%\main\indivTourData_%ITER%.csv OUTPUT\main
copy %MODEL_DIR%\main\jointTourData_%ITER%.csv OUTPUT\main

mkdir OUTPUT\skims
cd OUTPUT\skims
set TIMEPERIOD=MD
set TABLE=DISTDA

runtpp "%CODE_DIR%\extract_skim_table.job"
cd ..\..

mkdir OUTPUT\calibration
Rscript --vanilla "%CODE_DIR%\01_usual_work_school_location_TM.R"
Rscript --vanilla "%CODE_DIR%\02_auto_ownership_TM.R"
Rscript --vanilla "%CODE_DIR%\04_daily_activity_pattern_TM.R"
Rscript --vanilla "%CODE_DIR%\11_tour_mode_choice_TM.R"
