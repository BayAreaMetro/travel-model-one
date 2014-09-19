::
::  Parameters (environment variables):
::   RUN_NAME    : run name (e.g. 2010_04_ZZZ).  Often part of RUN_DIR. Used for TARGET_DIR.
::
::  Uses the RUN_NAME to set ITER, RUN_DIR, POPSYN_HH, POPSYN_PERS, RUN_DESC
::  (Todo: Should these be in a better location?  Like M:\Application\Model One\Model Run Directory.xlsx?
::
:: @echo off
setlocal enabledelayedexpansion

set ITER=0

:: look these up?
if %RUN_NAME% EQU 2010_03_YYY (
  set ITER=3
  set RUN_DIR=B:\Projects\2010_03_YYY.archived
  set POPSYN_HH=hhFile.p2011s3a.2010
  set POPSYN_PERS=personFile.p2011s3a1.2010
  set RUN_DESC=Year 2010 (version 0.3)
)
if %RUN_NAME% EQU 2010_04_ZZZ (
  set ITER=3
  set RUN_DIR=B:\Projects\%RUN_NAME%.archived
  set POPSYN_HH=hhFile.p2011s3a1.2010
  set POPSYN_PERS=personFile.p2011s3a1.2010
)

if %RUN_NAME% EQU 2020_03_116 (
  :: use for testing -- short files
  set ITER=1
  set RUN_DIR=B:\Projects\2020_03_116.archived
  set POPSYN_HH=hhFile.p2011s6g.2020
  set POPSYN_PERS=personFile.p2011s6g.2020
)

if %RUN_NAME% EQU 2040_03_116 (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_116.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, Plan (version 0.3)
)

if %RUN_NAME% EQU 2040_03_127 (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_127.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, TIP 2015 (version 0.3)
)

if %RUN_NAME% EQU 2040_03_129 (
  set ITER=3
  set RUN_DIR=B:\Projects\2040_03_129.archived
  set POPSYN_HH=hhFile.p2011s6g.2040
  set POPSYN_PERS=personFile.p2011s6g.2040
  set RUN_DESC=Year 2040, RTP 2013 (version 0.3)
)

if %ITER% EQU 0 (
  echo Did not understand RUN_NAME [%RUN_NAME%].
  goto done
) else (
  echo RUN_NAME    = %RUN_NAME%
  echo RUN_DIR     = %RUN_DIR%
  echo RUN_DESC    = %RUN_DESC%
  echo POPSYN_HH   = %POPSYN_HH%
  echo POPSYN_PERS = %POPSYN_PERS%
)

:: Input files will be copied into here
set TARGET_DIR=C:\Users\lzorn\Documents\%RUN_NAME%

:: Copy the inputs from the model run directory into the TARGET_DIR
call "%CODE_DIR%\copyCoreSummariesInputs.bat"

:: See if we're missing any summaries
if not exist "%TARGET_DIR%\summary" ( mkdir "%TARGET_DIR%\summary" )

set NEED_SUMMARY=0
for %%X in (%RDATA%) DO (
  if not exist "%TARGET_DIR%\summary\%%X.csv"             ( set /a NEED_SUMMARY+=1 )
)
echo Missing %NEED_SUMMARY% summaries in %TARGET_DIR%\summary

:: If we need to, create the core summaries.
if %NEED_SUMMARY% GTR 0 (
  echo %DATE% %TIME% Running summary script for %RUN_NAME%
  
  rem delete this just in case, so we don't move an old one by accident
  if exist CoreSummaries.html ( del CoreSummaries.html )
  
  rem No .Rprofile -- we set the environment variables here.
  echo "%R_HOME%\bin\x64\Rscript.exe"
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\knit_CoreSummaries.R"
  IF %ERRORLEVEL% GTR 0 goto done
  echo %DATE% %TIME% ...Done
  
  move CoreSummaries.html "%TARGET_DIR%\summary"
  
  rem This will make all the tdes stale
  for %%X in (%RDATA%) DO (
    del "%TARGET_DIR%\summary\%%X.tde"
  )
)
echo.

:: convert the summaries to tde for just this dir
for %%X in ("%TARGET_DIR%\summary\*.rdata") DO (
  if not exist "%TARGET_DIR%\summary\%%~nX.tde" (
    python "%CODE_DIR%\RdataToTableauExtract.py" "%TARGET_DIR%\summary" "%TARGET_DIR%\summary" %%~nxX
    if %ERRORLEVEL% GTR 0 goto done
    
    echo.
  )
)

:: convert the avgload5period.csv
if not exist "%TARGET_DIR%\summary\avgload5period.tde" (
  python "%CODE_DIR%\csvToTableauExtract.py" "%TARGET_DIR%\modelfiles" "%TARGET_DIR%\summary" avgload5period.csv
  if %ERRORLEVEL% GTR 0 goto done
  
  echo.
)

:: convert the transit files
if not exist "%TARGET_DIR%\summary\trnline.tde" (
  FOR %%H in (EA AM MD PM EV) DO (
    FOR %%J in (loc lrf exp hvy com) DO (
      rem walk -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv" --append "%TARGET_DIR%\modelfiles" "%TARGET_DIR%\summary" trnline%%H_wlk_%%J_wlk.csv
      rem drive -> transit -> walk
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv" --append "%TARGET_DIR%\modelfiles" "%TARGET_DIR%\summary" trnline%%H_drv_%%J_wlk.csv      
      rem walk -> transit -> drive
      python "%CODE_DIR%\csvToTableauExtract.py" --header "name,mode,owner,frequency,line time,line dist,total boardings,passenger miles,passenger hours,path id" --output trnline.tde --join "%CODE_DIR%\tableau\reference-transit-modes.csv"  --append "%TARGET_DIR%\modelfiles" "%TARGET_DIR%\summary" trnline%%H_wlk_%%J_drv.csv
    )
  )
)

endlocal

:done