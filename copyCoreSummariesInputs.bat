
set RUN_NAME=2010_04_ZZZ

:: destination directory - on the local disk
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%

set POPSYN_DIR=\\mainmodel\MainModelShare\Projects\%RUN_NAME%.archived\popsyn\
set OUTPUT_DIR=M:\Development\Travel Model One\Version 04\%RUN_NAME%\OUTPUT


copy "%POPSYN_DIR%\hhFile.p2011s3a1.2010.csv"  "%TARGET_DIR%
copy "%OUTPUT_DIR%\householdData_3.csv"        "%TARGET_DIR%"
copy "%OUTPUT_DIR%\tazData.csv"                "%TARGET_DIR%"
