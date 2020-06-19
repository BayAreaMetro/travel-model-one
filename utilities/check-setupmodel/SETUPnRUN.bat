:: ------------------------------------------------
:: this batch script run setupmodel with a log
:: a python script will check the log for error message
:: if all is good, then it will proceed with running runmodel
:: ------------------------------------------------

:: delete old output files in case they're left from a previous process
if exist setupOK.txt (del setupOK.txt) 
if exist setupOK.txt (del setupOK.txt) 

:: run setupmodel with a log
call setupmodel > setupmodel.log 2>&1

:: this script reads setupmodel.log
:: it looks for two kinds of errors: 'The system cannot find the file specified' and 'not recognized as an internal or external command'
:: it will output SetupOK.txt or SetupNOTOK.txt
set path=%path%;c:/python27
python Check_SetupModelLog.py

call runmodel
