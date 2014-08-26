setlocal enabledelayedexpansion

::set RUN_NAME=2010_04_ZZZ
set COMBINED_DIR=C:\Users\lzorn\Documents\AcrossScenarios
set RUN_NAME_SET=2010_04_ZZZ 2040_03_116
:: 2040_03_127 2040_03_129

for %%H in (%RUN_NAME_SET%) DO (

  set RUN_NAME=%%H
  rem copy the inputs from the model run directory
  call summarizeScenario.bat
  if %ERRORLEVEL% GTR 0 goto done

  rem create the combined version
)

:done