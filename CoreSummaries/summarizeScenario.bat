::
::  Parameters (environment variables):
::   RUN_NAME    : run name (e.g. 2010_04_ZZZ).  Often part of RUN_DIR. Used for TARGET_DIR.
::
::  Uses the RUN_NAME to set ITER, RUN_DIR, POPSYN_HH, POPSYN_PERS, RUN_DESC
::  (Todo: Should these be in a better location?  Like M:\Application\Model One\Model Run Directory.xlsx?
::
echo off

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
call copyCoreSummariesInputs.bat

:: See if we're missing any summaries
set NEED_SUMMARY=0
if not exist "%TARGET_DIR%\summary\ActiveTransport.csv"             ( set /a NEED_SUMMARY+=1 )
if not exist "%TARGET_DIR%\summary\ActivityPattern.csv"             ( set /a NEED_SUMMARY+=1 )
if not exist "%TARGET_DIR%\summary\AutomobileOwnership.csv"         ( set /a NEED_SUMMARY+=1 )
if not exist "%TARGET_DIR%\summary\CommuteByEmploymentLocation.csv" ( set /a NEED_SUMMARY+=1 )
echo Missing %NEED_SUMMARY% summaries in %TARGET_DIR%\summary

:: If we need to, create the core summaries.
if %NEED_SUMMARY% GTR 0 (
  echo %DATE% %TIME% Running summary script for %RUN_NAME%
  rem No .Rprofile -- we set the environment variables here.
  rem "C:\Program Files\R\R-3.1.1\bin\x64\Rscript.exe" --no-init-file knit_CoreSummaries.R
  rem IF %ERRORLEVEL% GTR 0 goto done
  echo %DATE% %TIME% ...Done
  
  copy CoreSummaries.html "%TARGET_DIR%\summary"
)

echo.

:done