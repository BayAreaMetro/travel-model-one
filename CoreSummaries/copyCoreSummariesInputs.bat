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

if not exist %TARGET_DIR% (mkdir %TARGET_DIR%)

if not exist "%TARGET_DIR%\%POPSYN_HH%.csv"     ( copy "%RUN_DIR%\popsyn\%POPSYN_HH%.csv"     "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\%POPSYN_PERS%.csv"   ( copy "%RUN_DIR%\popsyn\%POPSYN_PERS%.csv"   "%TARGET_DIR%" )

if not exist "%TARGET_DIR%\tazData.csv"                    ( copy "%RUN_DIR%\INPUT\landuse\tazData.csv"        "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\householdData_%ITER%.csv"       ( copy "%RUN_DIR%\main\householdData_%ITER%.csv"    "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\personData_%ITER%.csv"          ( copy "%RUN_DIR%\main\personData_%ITER%.csv"       "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTripData_%ITER%.csv"       ( copy "%RUN_DIR%\main\indivTripData_%ITER%.csv"    "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\indivTourData_%ITER%.csv"       ( copy "%RUN_DIR%\main\indivTourData_%ITER%.csv"    "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTripData_%ITER%.csv"       ( copy "%RUN_DIR%\main\jointTripData_%ITER%.csv"    "%TARGET_DIR%" )
if not exist "%TARGET_DIR%\jointTourData_%ITER%.csv"       ( copy "%RUN_DIR%\main\jointTourData_%ITER%.csv"    "%TARGET_DIR%" )

set TIMEPERIODS=EA AM MD PM EV
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
  
  if not exist "%TARGET_DIR%\TimeSkimsDatabase%%H.csv" (
    copy "%RUN_DIR%\database\TimeSkimsDatabase%%H.csv" "%TARGET_DIR%"
  )
)

:done