rem
rem Share Model Results to Box
rem

:: The location of R and R libraries
set R_HOME=C:\Program Files\R\R-3.2.3
set R_LIB=C:/Users/mtcpb/Documents/R/win-library/3.2

set CODE_DIR=C:\Users\lzorn\Documents\travel-model-one-v05\model-files
set BOX_DIR=C:\Users\lzorn\Box\Share Data\plan-bay-area-2040
set MODEL_ID=2010_06_003
set MODEL_DIR=D:\Projects\2010_06_003
set ZIPPER=C:\Program Files\7-Zip\7z.exe
set ITER=3

if not exist "%BOX_DIR%\%MODEL_ID%" (mkdir "%BOX_DIR%\%MODEL_ID%")

rem ==== INPUTS =======

if not exist "%BOX_DIR%\%MODEL_ID%\tazData.csv" (copy /Y "%MODEL_DIR%\INPUT\landuse\tazData.csv" "%BOX_DIR%\%MODEL_ID%\tazData.csv")

if not exist "%BOX_DIR%\%MODEL_ID%\householdData.zip" ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\householdData.zip" "%MODEL_DIR%\INPUT\popsyn\hhFile*.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\personData.zip"    ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\personData.zip"    "%MODEL_DIR%\INPUT\popsyn\personFile*.csv")

rem ==== OUTPUTS =======

rem main

if not exist "%BOX_DIR%\%MODEL_ID%\householdData.zip"  ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\householdData.zip" "%MODEL_DIR%\main\householdData_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\personData.zip"     ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\personData.zip"    "%MODEL_DIR%\main\personData_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\wsLocResults.zip"   ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\wsLocResults.zip"  "%MODEL_DIR%\main\wsLocResults_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\indivTourData.zip"  ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\indivTourData.zip" "%MODEL_DIR%\mainindivTourData_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\indivTripData.zip"  ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\indivTripData.zip" "%MODEL_DIR%\mainindivTripData_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\jointTourData.zip"  ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\jointTourData.zip" "%MODEL_DIR%\mainjointTourData_%ITER%.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\jointTripData.zip"  ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\jointTripData.zip" "%MODEL_DIR%\mainjointTripData_%ITER%.csv")

rem database

if not exist "%BOX_DIR%\%MODEL_ID%\SimpleTimeSkims.zip"     ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\SimpleTimeSkims.zip"     "%MODEL_DIR%\database\TimeSkimsDatabase*.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\SimpleDistanceSkims.zip" ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\SimpleDistanceSkims.zip" "%MODEL_DIR%\database\TimeDistanceDatabase*.csv")
if not exist "%BOX_DIR%\%MODEL_ID%\SimpleCostSkims.zip"     ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\SimpleCostSkims.zip"     "%MODEL_DIR%\database\TimeCostDatabase*.csv")

rem loaded roadway
if not exist "%BOX_DIR%\%MODEL_ID%\avgload5period.zip"      ("%ZIPPER%" a "%BOX_DIR%\%MODEL_ID%\avgload5period.zip"  "%MODEL_DIR%\hwy\iter%ITER%\avgload5period.net" "%MODEL_DIR%\hwy\iter%ITER%\avgload5period.csv" "%MODEL_DIR%\hwy\iter%ITER%\avgload5period.shp" "%MODEL_DIR%\hwy\iter%ITER%\avgload5period.shx" "%MODEL_DIR%\hwy\iter%ITER%\avgload5period.dbf")

rem transit

if not exist "%MODEL_DIR%\trn\trnline.csv"      (call "%R_HOME%\bin\x64\Rscript.exe" "%CODE_DIR%\scripts\core_summaries\ConsolidateLoadedTransit.R")
if not exist "%BOX_DIR%\%MODEL_ID%\trnline.csv" (copy /Y "%MODEL_DIR%\trn\trnline.csv" "%BOX_DIR%\%MODEL_ID%\trnline.csv")

:done