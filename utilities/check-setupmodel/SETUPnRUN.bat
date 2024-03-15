:: ------------------------------------------------
:: This batch script runs setupmodel and records stdout and stderr to setupmodel.log
:: It then runs Check_SetupModelLog.py to check the log for error messages
:: if all is good, then it will proceed with running runmodel
::
:: It requires python to be in your path
:: ------------------------------------------------

:: copy the Check script
copy X:\travel-model-one-master\utilities\check-setupmodel\Check_SetupModelLog.py .
IF ERRORLEVEL 1 goto done

:: run setupmodel with a log
call setupmodel > setupmodel.log 2>&1

:: this script reads setupmodel.log
:: it looks for two kinds of errors: 'The system cannot find the file specified' and 'not recognized as an internal or external command'
python Check_SetupModelLog.py
if ERRORLEVEL 1 goto done

call runmodel

:: if there is an error, do not run model
:done