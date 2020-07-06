:: ------------------------------------------------
:: this batch script run setupmodel with a log
:: a python script will check the log for error message
:: if all is good, then it will proceed with running runmodel
:: ------------------------------------------------


:: run setupmodel with a log
call setupmodel > setupmodel.log 2>&1

:: this script reads setupmodel.log
:: it looks for two kinds of errors: 'The system cannot find the file specified' and 'not recognized as an internal or external command'
set path=%path%;c:/python27
python Check_SetupModelLog.py
if ERRORLEVEL 1 goto done

call runmodel

:: if there is an error, do not run model
:done