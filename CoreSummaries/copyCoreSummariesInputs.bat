::
:: Parameters (environment variables):
::   RUN_NAME    : run name (e.g. 2010_04_ZZZ).  Often part of RUN_DIR. Used for TARGET_DIR.
::   RUN_DIR     : location model run (e.g. B:\Projects\%RUN_NAME%.archived)
::   ITER        : iteration files to use (e.g. 3 for final iteration, 1 for first iteration)
::   POPSYN_HH   : synthesized household file (e.g. hhFile.p2011s3a1.2010)
::   POPSYN_PERS : synthesized persons file (e.g. personFile.p2011s3a1.2010)
::   TARGET_DIR  : destination directory for all files
::
:: This script copies over all the files required to create core summaries from the RUN_DIR
:: to the destination directory, TARGET_DIR
::
:: Files are only copied if they don't exist yet in the target directory.
::
:: @echo off
setlocal enabledelayedexpansion

if not exist %TARGET_DIR%            (mkdir %TARGET_DIR%)
if not exist %TARGET_DIR%\modelfiles (mkdir %TARGET_DIR%\modelfiles)

if not exist "%TARGET_DIR%\modelfiles\%POPSYN_HH%.csv"     ( copy "%RUN_DIR%\popsyn\%POPSYN_HH%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\%POPSYN_PERS%.csv"   ( copy "%RUN_DIR%\popsyn\%POPSYN_PERS%.csv"   "%TARGET_DIR%\modelfiles" )

if not exist "%TARGET_DIR%\modelfiles\tazData.csv"                    ( copy "%RUN_DIR%\INPUT\landuse\tazData.csv"         "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\householdData_%ITER%.csv"       ( copy "%RUN_DIR%\main\householdData_%ITER%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\personData_%ITER%.csv"          ( copy "%RUN_DIR%\main\personData_%ITER%.csv"        "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\indivTripData_%ITER%.csv"       ( copy "%RUN_DIR%\main\indivTripData_%ITER%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\indivTourData_%ITER%.csv"       ( copy "%RUN_DIR%\main\indivTourData_%ITER%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\jointTripData_%ITER%.csv"       ( copy "%RUN_DIR%\main\jointTripData_%ITER%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\jointTourData_%ITER%.csv"       ( copy "%RUN_DIR%\main\jointTourData_%ITER%.csv"     "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\wsLocResults_%ITER%.csv"        ( copy "%RUN_DIR%\main\wsLocResults_%ITER%.csv"      "%TARGET_DIR%\modelfiles" )
if not exist "%TARGET_DIR%\modelfiles\avgload5period.csv"             ( copy "%RUN_DIR%\hwy\iter%ITER%\avgload5period.csv" "%TARGET_DIR%\modelfiles" )

set TIMEPERIODS=EA AM MD PM EV
FOR %%H in (%TIMEPERIODS%) DO (
  if not exist "%TARGET_DIR%\modelfiles\ActiveTimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\ActiveTimeSkimsDatabase%%H.csv" "%TARGET_DIR%\modelfiles"
  )
  if not exist "%TARGET_DIR%\modelfiles\CostSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\CostSkimsDatabase%%H.csv" "%TARGET_DIR%\modelfiles"
  )
  if not exist "%TARGET_DIR%\modelfiles\DistanceSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\DistanceSkimsDatabase%%H.csv" "%TARGET_DIR%\modelfiles"
  )
  
  if not exist "%TARGET_DIR%\modelfiles\TimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\TimeSkimsDatabase%%H.csv" "%TARGET_DIR%\modelfiles"
  )
  
  FOR %%J in (loc lrf exp hvy com) DO (
    rem walk -> transit -> walk
    if not exist "%TARGET_DIR%\modelfiles\trnline%%H_wlk_%%J_wlk.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_wlk_%%J_wlk.csv" "%TARGET_DIR%\modelfiles"
    )
    rem drive -> transit -> walk
    if not exist "%TARGET_DIR%\modelfiles\trnline%%H_drv_%%J_wlk.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_drv_%%J_wlk.csv" "%TARGET_DIR%\modelfiles"
    )
    rem walk -> transit -> drive
    if not exist "%TARGET_DIR%\modelfiles\trnline%%H_wlk_%%J_drv.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_wlk_%%J_drv.csv" "%TARGET_DIR%\modelfiles"
    )
  )
)

endlocal

:done