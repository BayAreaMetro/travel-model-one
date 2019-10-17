::
::

:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

:: MODEL YEAR ------------------------- make sure it's numeric --------------------------------
set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul
if %MODEL_YEAR_NUM%==%MODEL_YEAR% (
  echo Numeric model year [%MODEL_YEAR%]
) else (
  echo Couldn't determine numeric model year from project dir [%PROJECT_DIR%]
  echo Guessed [%MODEL_YEAR%]
  exit /b 2
)
:: MODEL YEAR ------------------------- make sure it's in [2000,3000] -------------------------
if %MODEL_YEAR% LSS 2000 (
  echo Model year [%MODEL_YEAR%] is less than 2000
  exit /b 2
)
if %MODEL_YEAR% GTR 3000 (
  echo Model year [%MODEL_YEAR%] is greater than 3000
  exit /b 2
)

set FUTURE_ABBR=%myfolder:~15,2%
echo FUTURE SHORT NAME = %FUTURE_ABBR%
set FUTURE=X
echo FUTURE TEMPORARY LONG NAME = X

:: FUTURE ------------------------- make sure FUTURE_ABBR is one of the three [RT,CG,BF] -------------------------
:: The long names are: PBA50, CleanAndGreen, BackToTheFuture, or RisingTidesFallingFortunes

if %MODEL_YEAR% EQU 2015 (
  set Future=PBA50
)

echo off
if %FUTURE_ABBR%==RT (
  set FUTURE=RisingTidesFallingFortunes
)

echo off
if %FUTURE_ABBR%==CG (
   set FUTURE=CleanAndGreen
)

echo off
if %FUTURE_ABBR%==BF (
  set FUTURE=BackToTheFuture
)

echo on
echo FUTURE LONG NAME = %FUTURE%

echo off
if %FUTURE%==X (
  echo on
  echo Couldn't determine FUTURE name.
  echo Make sure the name of the project folder conform to the naming convention.
  exit /b 2
)

echo on
echo turn echo back on

:: test if title works in batch file
:: title %myfolder%

:: now just wait
TIMEOUT /t 99999 

