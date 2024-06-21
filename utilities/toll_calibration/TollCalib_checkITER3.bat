:: ------------------------------------------
:: Set file paths and iteration number, and run the R script that calculates EL and GP speed
:: 
:: ------------------------------------------

set ITER=3

:: User input needed here
:: Location of the base run directory
:: Either the directory with the full run, or the directory with the extracted outputs
set PROJECT_DIR=%MODEL_BASE_DIR%


:: the rest doesn't require user inputs if TollCalib_setup.bat is run
:: otherwise user may need to specify the locations of UNLOADED_NETWORK_DBF, TOLL_DESIGNATIONS_XLSX and NonDynamicTollFacilities_CSV

:: Unloaded network dbf, generated from cube_to_shapefile.py, needed for the R script that determine toll adjustment 
:: (okay to borrow it from a different Future as long as we're sure the unloaded network is the same across Futures)
set UNLOADED_NETWORK_DBF=tollcalib_iter\network_links.dbf

:: The file indicating which facilities have mandatory s2 tolls
set TOLL_DESIGNATIONS_XLSX=tollcalib_iter\TOLLCLASS_Designations.xlsx

:: The file indicating which facilities is not dynamically tolled
:: Make sure NonDynamicTollFacilities.csv is copied to INPUT/hwy and hwy in the pre-toll-calibration run (aka the base run) 
copy %NonDynamicTollFacilities_CSV% %PROJECT_DIR%\INPUT\hwy
copy %NonDynamicTollFacilities_CSV% %PROJECT_DIR%\hwy

:: set R location
set R_HOME=C:\Program Files\R\R-3.5.2
set R_LIB=C:\Users\mtcpb\Documents\R\win-library\3.5
if "%COMPUTER_PREFIX%" == "WIN-" (
  set R_LIB=C:\Users\Administrator\Documents\R\win-library\3.5
)
if "%computername%" == "MODEL3-A" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-B" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-C" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)
if "%computername%" == "MODEL3-D" (
  set R_HOME=C:\Program Files\R\R-4.2.1
  set R_LIB=C:\Users\mtcpb\AppData\Local\R\win-library\4.2
)

:: summarize express lane speeds and generate a new tolls.csv 
call "%R_HOME%\bin\x64\Rscript.exe" TollCalib_CheckSpeeds.R

IF %ERRORLEVEL% NEQ 0 goto done

copy %PROJECT_DIR%\tollcalib_iter\el_gp_summary_ALL.csv tollcalib_iter\el_gp_summary_ALL.csv

:done
echo TollCalib_checkITER3 done with errorlevel %ERRORLEVEL%
