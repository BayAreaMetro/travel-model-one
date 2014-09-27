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

if not exist "%TARGET_DIR%"                 (mkdir "%TARGET_DIR%"         )
if not exist "%TARGET_DIR%\popsyn"          (mkdir "%TARGET_DIR%\popsyn"  )
if not exist "%TARGET_DIR%\landuse"         (mkdir "%TARGET_DIR%\landuse" )
if not exist "%TARGET_DIR%\main"            (mkdir "%TARGET_DIR%\main"    )
if not exist "%TARGET_DIR%\hwy"             (mkdir "%TARGET_DIR%\hwy"     )
if not exist "%TARGET_DIR%\hwy\iter%ITER%"  (mkdir "%TARGET_DIR%\hwy\iter%ITER%")
if not exist "%TARGET_DIR%\database"        (mkdir "%TARGET_DIR%\database")
if not exist "%TARGET_DIR%\trn"             (mkdir "%TARGET_DIR%\trn"     )

if not exist "%TARGET_DIR%\popsyn\hhFile.csv"       ( copy "%RUN_DIR%\popsyn\hhFile*.csv"         "%TARGET_DIR%\popsyn\hhFile.csv"     )
if not exist "%TARGET_DIR%\popsyn\personFile.csv"   ( copy "%RUN_DIR%\popsyn\personFile.*.csv"    "%TARGET_DIR%\popsyn\personFile.csv" )

if not exist "%TARGET_DIR%\landuse\tazData.csv"               ( copy "%RUN_DIR%\INPUT\landuse\tazData.csv"         "%TARGET_DIR%\landuse"   )
if not exist "%TARGET_DIR%\main\householdData_%ITER%.csv"     ( copy "%RUN_DIR%\main\householdData_%ITER%.csv"     "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\personData_%ITER%.csv"        ( copy "%RUN_DIR%\main\personData_%ITER%.csv"        "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\indivTripData_%ITER%.csv"     ( copy "%RUN_DIR%\main\indivTripData_%ITER%.csv"     "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\indivTourData_%ITER%.csv"     ( copy "%RUN_DIR%\main\indivTourData_%ITER%.csv"     "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\jointTripData_%ITER%.csv"     ( copy "%RUN_DIR%\main\jointTripData_%ITER%.csv"     "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\jointTourData_%ITER%.csv"     ( copy "%RUN_DIR%\main\jointTourData_%ITER%.csv"     "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\main\wsLocResults_%ITER%.csv"      ( copy "%RUN_DIR%\main\wsLocResults_%ITER%.csv"      "%TARGET_DIR%\main"      )
if not exist "%TARGET_DIR%\hwy\iter%ITER%\avgload5period.csv" ( copy "%RUN_DIR%\hwy\iter%ITER%\avgload5period.csv" "%TARGET_DIR%\hwy\iter%ITER%")

set TIMEPERIODS=EA AM MD PM EV
FOR %%H in (%TIMEPERIODS%) DO (
  if not exist "%TARGET_DIR%\database\ActiveTimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\ActiveTimeSkimsDatabase%%H.csv" "%TARGET_DIR%\database"
  )
  if not exist "%TARGET_DIR%\database\CostSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\CostSkimsDatabase%%H.csv" "%TARGET_DIR%\database"
  )
  if not exist "%TARGET_DIR%\database\DistanceSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\DistanceSkimsDatabase%%H.csv" "%TARGET_DIR%\database"
  )
  
  if not exist "%TARGET_DIR%\database\TimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\TimeSkimsDatabase%%H.csv" "%TARGET_DIR%\database"
  )
  
  FOR %%J in (loc lrf exp hvy com) DO (
    rem walk -> transit -> walk line files
    if not exist "%TARGET_DIR%\trn\trnline%%H_wlk_%%J_wlk.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_wlk_%%J_wlk.csv" "%TARGET_DIR%\trn"
    )
    rem drive -> transit -> walk line files
    if not exist "%TARGET_DIR%\trn\trnline%%H_drv_%%J_wlk.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_drv_%%J_wlk.csv" "%TARGET_DIR%\trn"
    )
    rem walk -> transit -> drive line files
    if not exist "%TARGET_DIR%\trn\trnline%%H_wlk_%%J_drv.csv" (
      copy "%RUN_DIR%\trn\trnline%%H_wlk_%%J_drv.csv" "%TARGET_DIR%\trn"
    )
    rem walk -> transit -> walk link files
    if not exist "%TARGET_DIR%\trn\trnlink%%H_wlk_%%J_wlk.dbf" (
      copy "%RUN_DIR%\trn\trnlink%%H_wlk_%%J_wlk.dbf" "%TARGET_DIR%\trn"
    )
    rem drive -> transit -> walk link files
    if not exist "%TARGET_DIR%\trn\trnlink%%H_drv_%%J_wlk.dbf" (
      copy "%RUN_DIR%\trn\trnlink%%H_drv_%%J_wlk.dbf" "%TARGET_DIR%\trn"
    )
    rem walk -> transit -> drive link files
    if not exist "%TARGET_DIR%\trn\trnlink%%H_wlk_%%J_drv.dbf" (
      copy "%RUN_DIR%\trn\trnlink%%H_wlk_%%J_drv.dbf" "%TARGET_DIR%\trn"
    )
  )
)

endlocal

:done