:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Specify file locations
::
:: ------------------------------------------------------------------------------------------------------
set YEAR=%1
:: set the location of the model run folder on M; this is where the input and output directories will be copied to
set M_DIR=D:\Models\BCM\%YEAR%_BaseY_BCM%YEAR%

:: Should strategies be included? AddStrategies=Yes for Project runs; AddStrategies=No for NoProject runs.
set AddStrategies=Yes

:: set the location of the Travel Model Release
:: use master for now until we create a release
set GITHUB_DIR=Z:\projects\ccta\31000190\Raghu\working_model\BCM_Model
set ALL_BCM_INPUTS=Z:\projects\ccta\31000190\Raghu\working_model\BCM_Inputs
set Software_Dir=Z:\projects\ccta\31000190\Raghu\working_model\BCM_Software
:: HIGH, MED or LOW
set COMPUTER_SETTING=HIGH


set INPUT_TRN=%ALL_BCM_INPUTS%\trn
::Inputs for the nonres models
set INPUT_NONRES=%ALL_BCM_INPUTS%\nonres


:: TODO  set the location of the previous run (where warmstart inputs will be copied):Currently set to be the calibration folder. The trip tables will be used in the 0th iteration HwyAssignment.job step
:: the INPUT folder of the previous run will also be used as the base for the compareinputs log
set PREV_RUN_DIR=%ALL_BCM_INPUTS%\warmstart

:: set the name and location of the properties file
:: often the properties file is on master during the active application phase
set PARAMS=%GITHUB_DIR%\config\params_%YEAR%.properties
:: test superdistrict-based telecommute constants
:: for no project or base years, this will get generated/stay at zero
set TELECOMMUTE_CONFIG=%GITHUB_DIR%\utilities\telecommute\telecommute_constants_2050.csv
:: for blueprint, use calibrated
:: set TELECOMMUTE_CONFIG=\\tsclient\X\travel-model-one-cdap-worktaz\utilities\telecommute\telecommute_constants_2035.csv

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
copy /Y "%GITHUB_DIR%\model-files\RunPostProcess.bat"                            .
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

:: popsyn and land use
mkdir popsyn
mkdir INPUT\popsyn
mkdir INPUT\landuse
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\IZ_OZ_PCT_EXT.dat"          	INPUT\landuse\IZ_OZ_PCT_EXT.dat
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\SD2TAZ_KF.prn"          		INPUT\landuse\SD2TAZ_KF.prn
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\TAZ2CO.prn"          			INPUT\landuse\TAZ2CO.prn
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\TAZ2COUNTY.prn"          		INPUT\landuse\TAZ2COUNTY.prn
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\TAZ2SD.prn"          			INPUT\landuse\TAZ2SD.prn
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\walkAccessBuffers.float.csv"    INPUT\landuse\walkAccessBuffers.float.csv
copy "%ALL_BCM_INPUTS%\inputs_%YEAR%\ZMAST20.dbf"          			INPUT\landuse\ZMAST20.dbf


copy %ALL_BCM_INPUTS%\inputs_%YEAR%\hhFile%YEAR%.csv												INPUT\popsyn\hhFile.%YEAR%.csv
copy %ALL_BCM_INPUTS%\inputs_%YEAR%\personFile%YEAR%.csv											INPUT\popsyn\personFile.%YEAR%.csv
c:\windows\system32\Robocopy.exe /E "%INPUT_NONRES%"                   							INPUT\nonres
::need to update the maximum telecommute rate for San Joaquin County in the telecommute_max_rate_county.csv file
::right now using the same values as Marin
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\telecommute"   		   				INPUT\landuse
:: nonres

:: copy the temporary transit skims to M_DIR. Created skims directory.
mkdir skims
:: warmstart (copy from the previous run)
mkdir INPUT\warmstart\main
mkdir INPUT\warmstart\nonres
copy /Y "%PREV_RUN_DIR%\main\*.tpp"                                                       		INPUT\warmstart\main
copy /Y "%PREV_RUN_DIR%\nonres\*.tpp"                                                     		INPUT\warmstart\nonres


:: the properties file
copy /Y "%PARAMS%"                                                                               INPUT\params.properties

:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul
:: ------------------------------------------------------------------------------------------------------
::
:: Step 4: Overrides for Blueprint Strategies
::
:: ------------------------------------------------------------------------------------------------------
if %AddStrategies%==No goto DoneAddingStrategies

:: ----------------------------------------
:: Parking tazdata update (part of En9 - Expand Transportation Demand Management Initiatives)
:: -----------------------------------------
if %MODEL_YEAR_NUM% GEQ 2035 (
  copy /Y "%INPUT_POPLU%\landuse\parking_strategy\tazData_parkingStrategy_v01.csv"  INPUT\landuse\tazData.csv
  copy /Y "%INPUT_POPLU%\landuse\parking_strategy\tazData_parkingStrategy_v01.dbf"  INPUT\landuse\tazData.dbf
)

:: another part of this strategy is to turn off free parking eligibility, which is done via the properties file.
:: see: https://github.com/BayAreaMetro/travel-model-one/blob/master/config/params_PBA50_Blueprint2050.properties#L156

:: ----------------------------------------
:: Bus on shoulder by time period
:: -----------------------------------------
:: For bus on highway shoulder, BRT is set to 3.
:: The script assumes 35 mph or congested time, whichever is less.
:: See: https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/skims/PrepHwyNet.job#L163
:: To allow the links to have different BRT values for different time periods, a few additional lines of code is added to CreateFiveHighwayNetworks.job.

if %MODEL_YEAR_NUM% GEQ 2035 (
  copy /Y  "%BP_OVERRIDE_DIR%\BusOnShoulder_by_TP\CreateFiveHighwayNetworks_BusOnShoulder.job"     CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
  copy /Y  "M:\Application\Model One\NetworkProjects\FBP_MR_018_US101_BOS\mod_links.csv"           INPUT\hwy\mod_links_BRT_FBP_MR_018_US101_BOS.csv
  copy /Y  "M:\Application\Model One\NetworkProjects\MAJ_Bay_Area_Forward_all\mod_links_BRT.csv"   INPUT\hwy\mod_links_BRT_MAJ_Bay_Area_Forward_all.csv
  copy INPUT\hwy\mod_links_BRT_FBP_MR_018_US101_BOS.csv+INPUT\hwy\mod_links_BRT_MAJ_Bay_Area_Forward_all.csv    INPUT\hwy\mod_links_BRT.csv
)

:: ------
:: Blueprint Regional Transit Fare Policy
:: ------
:: Same as PPA project 6100_TransitFare_Integration
if %MODEL_YEAR_NUM% GEQ 2035 (
  copy /Y "%BP_OVERRIDE_DIR%\Regional_Transit_Fare_Policy\TransitSkims.job"     CTRAMP\scripts\skims
)
:: means-based fare discount -- 50% off for Q1 -- are config in the parmas.properties file (see step 1)

:: ------
:: Blueprint Vision Zero
:: ------
:: Start year (freeways): 2030
:: Start year (local streets): 2025

if %MODEL_YEAR_NUM%==2025 (copy /Y "%BP_OVERRIDE_DIR%\Vision_Zero\SpeedCapacity_1hour_2025.block"            "CTRAMP\scripts\block\SpeedCapacity_1hour.block")
if %MODEL_YEAR_NUM% GEQ 2030 (copy /Y "%BP_OVERRIDE_DIR%\Vision_Zero\SpeedCapacity_1hour_2030to2050.block"   "CTRAMP\scripts\block\SpeedCapacity_1hour.block")

:: ------
:: Blueprint Per-Mile Tolling on Congested Freeways
:: ------
:: no override needed, as we confirmed that all ODs have free paths
:: see asana task: https://app.asana.com/0/572982923864207/1174201042245385

:: toll rate discount -- 50% discount for Q1 and Q2 -- are specified in the properties file (see step 1)

:: ------
:: Complete Streets
:: ------
:: no override needed since it's now in config
:: see asana task: https://app.asana.com/0/450971779231601/1186351402141779/f

:: ------
:: Bike Access 
:: ------
:: Bike/ped improvement on the San Rafael Bridge
if %MODEL_YEAR_NUM% GEQ 2025 (copy /Y "%BP_OVERRIDE_DIR%\Bike_access\CreateNonMotorizedNetwork_BikeAccess_2025-2040.job"     "CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job")
:: Bay Skyway (formerly Bay Bridge West Span Bike Path)
if %MODEL_YEAR_NUM% GEQ 2045 (copy /Y "%BP_OVERRIDE_DIR%\Bike_access\CreateNonMotorizedNetwork_BikeAccess_2045onwards.job"   "CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job")

:: ------
:: Telecommute V2 strategy
:: ------
mkdir main
copy /Y "%TELECOMMUTE_CONFIG%" "main/telecommute_constants_00.csv"
copy /Y "%TELECOMMUTE_CONFIG%" "main/telecommute_constants.csv"
 
:DoneAddingStrategies

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: Patches to Travel Model Release 
::
:: ------------------------------------------------------------------------------------------------------
:: in case the TM release is behind, this is where we copy the most up-to-date scripts from master
set GITHUB_MASTER=\\tsclient\X\travel-model-one-master

:: nothing yet

:: ------------------------------------------------------------------------------------------------------
::
:: Step 6: copy information back to the M drive for run management
::
:: ------------------------------------------------------------------------------------------------------

:: copy the INPUT folder back to M for record keeping

echo %date%
SET mm=%date:~4,2%
SET dd=%date:~7,2%
SET yy=%date:~12,2%
echo %time%
SET hh=%time:~0,2%
SET min=%time:~3,2%
SET ss=%time:~6,2%

if exist "%M_DIR%\INPUT" (
    :: do not overwrite existing INPUT folders on M 
    c:\windows\system32\Robocopy.exe /E "INPUT" "%M_DIR%\INPUT_%mm%%dd%%yy%_%hh%%min%%ss%"
) else (
    c:\windows\system32\Robocopy.exe /E "INPUT" "%M_DIR%\INPUT"
)

Set dir1="%M_DIR%\INPUT"
Set dir2="%PREV_RUN_DIR%\INPUT"
c:\windows\system32\robocopy.exe %dir1% %dir2% /e /l /ns /njs /ndl /fp /log:"%M_DIR%\CompareInputs.txt"

::----------------------------------------------
:: add folder name to the command prompt window 
::----------------------------------------------
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf

title %myfolder%


:: copy this batch file itself to M
set CopyOfSetupModel="SetUpModel_"%myfolder%".txt"
copy SetUpModel.bat "%M_DIR%\%CopyOfSetupModel%"

::-----------------------------------------------------------------------
:: create a shortcut of the project directory using a temporary VBScript
::-----------------------------------------------------------------------

set TEMP_SCRIPT="%CD%\temp_script_to_create_shortcut.vbs"
set PROJECT_DIR=%~p0
set ALPHABET=%computername:~7,1%

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %TEMP_SCRIPT%
echo sLinkFile = "%M_DIR%/model_run_on_%computername%.lnk" >> %TEMP_SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %TEMP_SCRIPT%
echo oLink.TargetPath = "M:" >> %TEMP_SCRIPT%
echo oLink.TargetPath = "\\%computername%\%PROJECT_DIR%" >> %TEMP_SCRIPT%

echo oLink.Save >> %TEMP_SCRIPT%

::C:\Windows\SysWOW64\cscript.exe /nologo %TEMP_SCRIPT%
C:\Windows\SysWOW64\cscript.exe %TEMP_SCRIPT%
del %TEMP_SCRIPT%

:end