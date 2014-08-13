echo on
set RUN_NAME=2010_04_ZZZ

:: destination directory - on the local disk
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%
set TIMEPERIODS=EA AM MD PM EV

:: look these up?
if %RUN_NAME% EQU 2010_03_YYY (
  set CITER=3
  set RUN_DIR=B:\Projects\2010_03_YYY.archived
  set POPSYN_HH=hhFile.p2011s3a.2010
  set POPSYN_PERS=personFile.p2011s3a1.2010
  set RUN_DESC=Year 2010 (version 0.3)
)
if %RUN_NAME% EQU 2010_04_ZZZ (
  set CITER=3
  set RUN_DIR=B:\Projects\%RUN_NAME%.archived
  set POPSYN_HH=hhFile.p2011s3a1.2010
  set POPSYN_PERS=personFile.p2011s3a1.2010
)

if %RUN_NAME% EQU 2020_03_116 (
  :: use for testing -- short files
  set CITER=1
  set RUN_DIR=B:\Projects\2020_03_116.archived
  set POPSYN_HH=hhFile.p2011s6g.2020
  set POPSYN_PERS=personFile.p2011s6g.2020
)

if %RUN_NAME% EQU 2040_03_116 (
  set CITER=3
  set RUN_DIR=B:\Projects\2040_03_116.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, Plan (version 0.3)
)

if %RUN_NAME% EQU 2040_03_127 (
  set CITER=3
  set RUN_DIR=B:\Projects\2040_03_127.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, TIP 2015 (version 0.3)
)

if %RUN_NAME% EQU 2040_03_129 (
  set CITER=3
  set RUN_DIR=B:\Projects\2040_03_129.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, RTP 2013 (version 0.3)
)

if not exist %TARGET_DIR% (mkdir %TARGET_DIR%)

if not exist "%TARGET_DIR%\%POPSYN_HH%.csv"     ( copy "%RUN_DIR%\popsyn\%POPSYN_HH%.csv"     "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\%POPSYN_PERS%.csv"   ( copy "%RUN_DIR%\popsyn\%POPSYN_PERS%.csv"   "%TARGET_DIR%" )

if not exist "%TARGET_DIR%\tazData.csv"                     ( copy "%RUN_DIR%\INPUT\landuse\tazData.csv"             "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\householdData_%CITER%.csv"       ( copy "%RUN_DIR%\main\householdData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\personData_%CITER%.csv"          ( copy "%RUN_DIR%\main\personData_%CITER%.csv"           "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTripData_%CITER%.csv"       ( copy "%RUN_DIR%\main\indivTripData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTourData_%CITER%.csv"       ( copy "%RUN_DIR%\main\indivTourData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTripData_%CITER%.csv"       ( copy "%RUN_DIR%\main\jointTripData_%CITER%.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTourData_%CITER%.csv"       ( copy "%RUN_DIR%\main\jointTourData_%CITER%.csv"        "%TARGET_DIR%" )

FOR %%H in (%TIMEPERIODS%) DO (
  if not exist "%TARGET_DIR%\ActiveTimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\ActiveTimeSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )
  if not exist "%TARGET_DIR%\CostSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\CostSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )
  if not exist "%TARGET_DIR%\DistanceSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\DistanceSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )  
)

:: "C:\Program Files\R\R-3.1.1\bin\x64\Rscript.exe" knit_CoreSummaries.R
:done