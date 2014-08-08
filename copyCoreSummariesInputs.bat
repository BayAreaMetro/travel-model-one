echo on
set RUN_NAME=2020_03_116

:: destination directory - on the local disk
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%
set TIMEPERIODS=EA AM MD PM EV

if %RUN_NAME% EQU 2010_04_ZZZ (
  set CITER=3
  set RUN_DIR=B:\Projects\%RUN_NAME%.archived
  set POPSYN_HH=hhFile.p2011s3a1.2010
  set POPSYN_PERS=personFile.p2011s3a1.2010
)

if %RUN_NAME% EQU 2020_03_116 (
  set CITER=1
  set RUN_DIR=B:\Projects\2020_03_116.archived
  set POPSYN_HH=hhFile.p2011s6g.2020
  set POPSYN_PERS=personFile.p2011s6g.2020
)

if not exist %TARGET_DIR% (mkdir %TARGET_DIR%)

if not exist "%TARGET_DIR%\%POPSYN_HH%.csv"     ( copy "%RUN_DIR%\popsyn\%POPSYN_HH%.csv"     "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\%POPSYN_PERS%.csv"   ( copy "%RUN_DIR%\popsyn\%POPSYN_PERS%.csv"   "%TARGET_DIR%" )

if not exist "%TARGET_DIR%\tazData.csv"               ( copy "%RUN_DIR%\INPUT\landuse\tazData.csv"             "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\householdData_3.csv"       ( copy "%RUN_DIR%\main\householdData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\personData_3.csv"          ( copy "%RUN_DIR%\main\personData_%CITER%.csv"           "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTripData_3.csv"       ( copy "%RUN_DIR%\main\indivTripData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTripData_3.csv"       ( copy "%RUN_DIR%\main\jointTripData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTourData_3.csv"       ( copy "%RUN_DIR%\main\jointTourData_%CITER%.csv"        "%TARGET_DIR%" )

FOR %%H in (%TIMEPERIODS%) DO (
  if not exist "%TARGET_DIR%\ActiveTimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\ActiveTimeSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )
)

:done