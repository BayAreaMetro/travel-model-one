:: extract-express-lane-data.bat
:: 
:: MS-DOS batch file to execute the TP+ script extract-express-lane-data.job.
::
:: 2011 01 19 dto

set CODE_DIR=D:\files\GitHub\travel-model-one\utilities\express-lane-prices

call runtpp %CODE_DIR%\extract-express-lane-data.job

rem end: extract-express-lane-data.bat
