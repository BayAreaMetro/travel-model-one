:: This first runs the off model prep script, which creates model data for
:: the off-model calculation; then runs the off-model calculator.
::

echo on
setlocal enabledelayedexpansion


:start

:: Overhead
if not exist offmodel (mkdir offmodel)
set OFFMOEL_DIR=offmodel
set OFFMODEL_SCRIPT_DIR=.\CTRAMP\scripts\offmodel

echo OFFMOEL_DIR=%OFFMOEL_DIR%
echo OFFMODEL_SCRIPT_DIR=%OFFMODEL_SCRIPT_DIR%
:: echo MODEL_YEAR=%MODEL_YEAR%
mkdir %OFFMOEL_DIR%\offmodel_prep
mkdir %OFFMOEL_DIR%\offmodel_output

:: Run prep data creation script
echo %DATE% %TIME% Running offmodel prep script for bikeshare
python "%OFFMODEL_SCRIPT_DIR%\offmodel_prep.py"
echo %DATE% %TIME% ...Done

:: Run off model calculation script
:: to-do


:success
echo FINISHED OFFMODEL RUN SUCESSFULLY!
echo ENDED OFFMODEL RUN  %DATE% %TIME% >> logs\feedback.rpt

:error
echo ERRORLEVEL=%ERRORLEVEL%