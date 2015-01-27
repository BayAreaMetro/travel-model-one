::
::  Parameters (environment variables):
::    CODE_DIR    : Location of CoreSummaries directory with the R and python code
::                  (e.g. C:\Users\lzorn\Documents\travel-model-one)
::    R_HOME      : Location of R (e.g. C:\Program Files\R\R-3.1.1)
::    R_USER      : User.  (e.g same value as %USERNAME%)
::    R_LIBS_USER : Location of R Libs (e.g. C:\Users\%R_USER%\Documents\R\win-library\3.1)
::    RUN_NAME    : run name (e.g. 2010_04_ZZZ)
::    RDATA       : The output .rdata files (e.g. ActiveTransport ActivityPattern AutomobileOwnership...)
::
::  Uses the RUN_NAME to set ITER, RUN_DIR
::  (Todo: Should these be in a better location?  Like M:\Application\Model One\Model Run Directory.xlsx?
::
:: @echo off
setlocal enabledelayedexpansion

set ITER=0

:: look these up?
echo RUN_NAME=%RUN_NAME%
if "%RUN_NAME%" == "2000_03_YYY" (
  set ITER=3
  set RUN_DIR=B:\Projects\2000_03_YYY.archived
)
if "%RUN_NAME%" == "2005_03_YYY" (
  set ITER=3
  set RUN_DIR=B:\Projects\2005_03_YYY.archived
)

if "%RUN_NAME%" == "2010_03_YYY" (
  set ITER=3
  set RUN_DIR=B:\Projects\2010_03_YYY.archived
)
if "%RUN_NAME%" == "2010_04_ZZZ" (
  set ITER=3
  set RUN_DIR=B:\Projects\%RUN_NAME%.archived
)

if "%RUN_NAME%" == "2020_03_116" (
  set ITER=3
  set RUN_DIR=B:\Projects\2020_03_116.archived
)

if "%RUN_NAME%" == "2030_03_116" (
  set ITER=3
  set RUN_DIR=B:\Projects\2030_03_116.archived
)

if "%RUN_NAME%" == "2040_03_116" (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_116.archived
)

if "%RUN_NAME%" EQU "2040_03_127" (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_127.archived
)

if "%RUN_NAME%" EQU "2040_03_129" (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_129.archived
)

echo ITER=!ITER!=%ITER%
if %ITER% EQU 0 (
  echo Did not understand RUN_NAME [%RUN_NAME%].
  goto done
) else (
  echo RUN_NAME    = %RUN_NAME%
  echo RUN_DIR     = %RUN_DIR%
)

:: Input files will be copied into here
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%

:: Copy the inputs from the model run directory into the TARGET_DIR
call "%CODE_DIR%\utilities\CoreSummaries\copyCoreSummariesInputs.bat"

:: See if we're missing any summaries
if not exist "%TARGET_DIR%\core_summaries" ( mkdir "%TARGET_DIR%\core_summaries" )

set NEED_SUMMARY=0
for %%X in (%RDATA%) DO (
  if not exist "%TARGET_DIR%\core_summaries\%%X.csv"             ( set /a NEED_SUMMARY+=1 )
)
echo Missing %NEED_SUMMARY% summaries in %TARGET_DIR%\core_summaries

:: If we need to, create the core summaries.
if %NEED_SUMMARY% GTR 0 (
  echo %DATE% %TIME% Running summary script for %RUN_NAME%
  
  rem delete this just in case, so we don't move an old one by accident
  if exist CoreSummaries.html ( del CoreSummaries.html )
  
  rem No .Rprofile -- we set the environment variables here.
  set OLD_CODE_DIR=%CODE_DIR%
  set CODE_DIR=%CODE_DIR%\model-files\scripts\core_summaries
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\model-files\scripts\core_summaries\knit_CoreSummaries.R"
  set CODE_DIR=%OLD_CODE_DIR%
  IF %ERRORLEVEL% GTR 0 goto done
  echo %DATE% %TIME% ...Done
  
  move CoreSummaries.html "%TARGET_DIR%\core_summaries"
  
  rem This will make all the tdes stale
  for %%X in (%RDATA%) DO (
    del "%TARGET_DIR%\core_summaries\%%X.tde"
  )
)
echo.

:: convert the summaries to tde for just this dir
for %%X in ("%TARGET_DIR%\core_summaries\*.rdata") DO (
  if not exist "%TARGET_DIR%\core_summaries\%%~nX.tde" (
    python "%CODE_DIR%\model-files\scripts\core_summaries\RdataToTableauExtract.py" "%TARGET_DIR%\core_summaries" "%TARGET_DIR%\core_summaries" %%~nxX
    if %ERRORLEVEL% GTR 0 goto done
    
    echo.
  )
)

:: convert the avgload5period.csv
if not exist "%TARGET_DIR%\core_summaries\avgload5period.tde" (
  python "%CODE_DIR%\model-files\scripts\core_summaries\csvToTableauExtract.py" "%TARGET_DIR%\hwy\iter%ITER%" "%TARGET_DIR%\core_summaries" avgload5period.csv
  if %ERRORLEVEL% GTR 0 goto done
  
  echo.
)

:trnline
:: convert the transit files
if not exist "%TARGET_DIR%\core_summaries\trnline.tde" (
  FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\model-files\scripts\core_summaries\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\model-files\scripts\core_summaries\reference-transit-modes.csv" --append "%TARGET_DIR%\trn" "%TARGET_DIR%\core_summaries" trnline%%H_wlk_%%J_wlk.csv
      rem drive -> transit -> walk
      python "%CODE_DIR%\model-files\scripts\core_summaries\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\model-files\scripts\core_summaries\reference-transit-modes.csv" --append "%TARGET_DIR%\trn" "%TARGET_DIR%\core_summaries" trnline%%H_drv_%%J_wlk.csv      
      rem walk -> transit -> drive
      python "%CODE_DIR%\model-files\scripts\core_summaries\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\model-files\scripts\core_summaries\reference-transit-modes.csv"  --append "%TARGET_DIR%\trn" "%TARGET_DIR%\core_summaries" trnline%%H_wlk_%%J_drv.csv
    )
  )
)


endlocal

:done