::
:: Example batch file to create a requested summary.
:: Set SCRIPT and run in the target directory
::
set R_HOME=C:\Program Files\R\R-3.1.1
set ITER=3
set TARGET_DIR=%CD%
set CODE_DIR=C:\Users\lzorn\Documents\Travel-Model-One-Utilities\CoreSummaries\DataRequests
:: leave off the .Rmd
set SCRIPT=Trips_origSD_destSD_departhour_tripmode

call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\knit_Rmd.R"

move "%SCRIPT%.html" "%TARGET_DIR%\core_summaries"
del "%SCRIPT%.md"