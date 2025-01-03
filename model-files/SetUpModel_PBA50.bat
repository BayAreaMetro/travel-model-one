:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Specify file locations
::
:: ------------------------------------------------------------------------------------------------------
set YEAR=%1
:: set the location of the model run folder on M; this is where the input and output directories will be copied to
set M_DIR=D:\Scenarios\%YEAR%_BaseY_BCM%YEAR%

:: Should strategies be included? AddStrategies=Yes for Project runs; AddStrategies=No for NoProject runs.
set AddStrategies=Yes

:: set the location of the Travel Model Release
:: use master for now until we create a release
set GITHUB_DIR=Z:\projects\ccta\31000190\Raghu\release_model\AlaCC_Model
set ALL_BCM_INPUTS=Z:\projects\ccta\31000190\Raghu\release_model\Alacc_Inputs
set Software_Dir=Z:\projects\ccta\31000190\Raghu\release_model\AlaCC_Software
:: HIGH or MED
set COMPUTER_SETTING=HIGH


set INPUT_TRN=%ALL_BCM_INPUTS%\trn
::Inputs for the nonres models
set INPUT_NONRES=%ALL_BCM_INPUTS%\nonres



:: set the name and location of the properties file
:: often the properties file is on master during the active application phase
set PARAMS=%GITHUB_DIR%\config\params_%YEAR%.properties


:: set the location of the overrides directory (for Blueprint strategies)
set BP_OVERRIDE_DIR=D:\Projects\BCM\2015_BaseY_BCM2015\travel-model-overrides

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Set up folder structure and copy CTRAMP
::
:: ------------------------------------------------------------------------------------------------------

for /f "delims=[] tokens=2" %%a in ('ping -4 -n 1 %ComputerName% ^| findstr [') do set HOST_IP_ADDRESS=%%a
SET HOST_IP_ADDRESS=localhost
echo HOST_IP_ADDRESS: %HOST_IP_ADDRESS%

SET computer_prefix=%computername:~0,4%
mkdir %M_DIR%
echo SET SOFTWARE_DIR=%Software_Dir%> %M_DIR%\Set_Software_Dr.cmd
echo SET COMPUTER_SETTING=%COMPUTER_SETTING%>> %M_DIR%\Set_Software_Dr.cmd
COMPUTER_SETTING
cd /d %M_DIR%
:: copy over CTRAMP
mkdir CTRAMP\model
::mkdir Software
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\RTP\metrics"   CTRAMP\scripts\metrics
::c:\windows\system32\Robocopy.exe /E "%Software_Dir%"       				   Software
copy /Y "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"                CTRAMP\scripts
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunModel.bat"                            .
copy /Y "%GITHUB_DIR%\model-files\click_to_runmodel.bat"                   .
copy /Y "%GITHUB_DIR%\model-files\RunPostProcess.bat"                      .
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                          .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\model-files\RunPrepareEmfac.bat"                     .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunMetrics.bat"                        .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunScenarioMetrics.bat"                .
copy /Y "%GITHUB_DIR%\utilities\RTP\ExtractKeyFiles.bat"                   .
copy /Y "%GITHUB_DIR%\utilities\RTP\QAQC\Run_QAQC.bat"                     .
copy /Y "%GITHUB_DIR%\utilities\check-setupmodel\Check_SetupModelLog.py"   .
copy /Y "%GITHUB_DIR%\utilities\dbf_to_csv\create_landuse_csv.R"   		   CTRAMP\scripts\preprocess

if "%COMPUTER_PREFIX%" == "WIN-" (copy "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"  "CTRAMP\scripts\notify_slack.py")
if "%COMPUTER_PREFIX%" == "WIN-"    set HOST_IP_ADDRESS=10.0.0.59

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3: copy over input from INPUT_DEVELOPMENT or the previous run
:: (or sometimes a special location for the properties file)
::
:: ------------------------------------------------------------------------------------------------------

:: networks
mkdir INPUT\hwy
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\complete_network_with_externals.net"               INPUT\hwy\complete_network_with_externals.net
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\tolls.csv"                                        	INPUT\hwy\tolls.csv

c:\windows\system32\Robocopy.exe /E "%INPUT_TRN%"                                        		INPUT\trn
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\transit.lin"                                        	INPUT\trn\transit.lin
:: popsyn and land use
mkdir popsyn
mkdir INPUT\popsyn
mkdir INPUT\landuse
copy "%ALL_BCM_INPUTS%\nonres\IZ_OZ_PCT_EXT.dat"          	INPUT\landuse\IZ_OZ_PCT_EXT.dat
copy "%ALL_BCM_INPUTS%\nonres\SD2TAZ_KF.prn"          		INPUT\landuse\SD2TAZ_KF.prn
copy "%ALL_BCM_INPUTS%\nonres\TAZ2CO.prn"          			INPUT\landuse\TAZ2CO.prn
copy "%ALL_BCM_INPUTS%\nonres\TAZ2COUNTY.prn"          		INPUT\landuse\TAZ2COUNTY.prn
copy "%ALL_BCM_INPUTS%\nonres\TAZ2SD.prn"          			INPUT\landuse\TAZ2SD.prn
copy "%ALL_BCM_INPUTS%\nonres\walkAccessBuffers.float.csv"    INPUT\landuse\walkAccessBuffers.float.csv
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\ZMAST.dbf"          			INPUT\landuse\ZMAST.dbf


copy %ALL_BCM_INPUTS%\inputs_%YEAR%\hhFile%YEAR%.csv												INPUT\popsyn\hhFile.%YEAR%.csv
copy %ALL_BCM_INPUTS%\inputs_%YEAR%\personFile%YEAR%.csv											INPUT\popsyn\personFile.%YEAR%.csv
c:\windows\system32\Robocopy.exe /E "%INPUT_NONRES%"                   							INPUT\nonres


set PREV_RUN_DIR=%ALL_BCM_INPUTS%\inputs_%YEAR%\warmstart



:: copy the temporary transit skims to M_DIR. Created skims directory.
mkdir skims
:: warmstart (copy from the previous run)
mkdir INPUT\warmstart\main
mkdir INPUT\warmstart\nonres
copy /Y "%PREV_RUN_DIR%\main\*.tpp"                                                       		INPUT\warmstart\main
copy /Y "%PREV_RUN_DIR%\nonres\*.tpp"                                                     		INPUT\warmstart\nonres


:: the properties file
copy /Y "%PARAMS%"                                                                               INPUT\params.properties

:: ------
:: Telecommute V2 strategy
:: ------
set TELECOMMUTE_CONFIG=%ALL_BCM_INPUTS%\inputs_%YEAR%\telecommute_constants_%YEAR%.csv
mkdir main
copy /Y "%TELECOMMUTE_CONFIG%" "INPUT/landuse/telecommute_constants.csv"
copy /Y "%ALL_BCM_INPUTS%\inputs_%YEAR%\telecommute_max_rate_county.csv" "INPUT/landuse/telecommute_max_rate_county.csv"
 
:end