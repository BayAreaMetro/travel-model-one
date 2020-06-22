:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Specify file locations
::
:: ------------------------------------------------------------------------------------------------------

:: set the location of the model run folder on M; this is where the input and output directories will be copied to
set M_DIR=M:\Application\Model One\RTP2021\Blueprint\2050_TM152_DBP_PlusCrossing_07

:: Should strategies be included? AddStrategies=Yes for Project runs; AddStrategies=No for NoProject runs.
set AddStrategies=Yes

:: set the location of the Travel Model Release
set GITHUB_DIR=\\tsclient\X\travel-model-one-1.5.2.1

:: set the location of the networks (make sure the network version, year and variant are correct)
set INPUT_NETWORK=M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_15\net_2050_Blueprint Plus Crossing

:: set the location of the populationsim and land use inputs (make sure the land use version and year are correct) 
set INPUT_POPLU=M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\PopSyn_n_LandUse\POPLU_v170_01\2050
set UrbanSimScenario=s23

:: set the location of the "input development" directory where other inputs are stored
set INPUT_DEVELOPMENT_DIR=M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT

:: set the location of the previous run (where warmstart inputs will be copied)
:: the INPUT folder of the previous run will also be used as the base for the compareinputs log
set PREV_RUN_DIR=M:\Application\Model One\RTP2021\Blueprint\2050_TM152_DBP_PlusCrossing_06

:: set the name and location of the properties file
:: often the properties file is on master during the active application phase
set PARAMS=\\tsclient\X\travel-model-one-master\config\params_PBA50_Blueprint2050.properties

:: set the location of the overrides directory (for Blueprint strategies)
set BP_OVERRIDE_DIR=\\tsclient\M\Application\Model One\RTP2021\Blueprint\travel-model-overrides

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Set up folder structure and copy CTRAMP
::
:: ------------------------------------------------------------------------------------------------------

SET computer_prefix=%computername:~0,4%

:: copy over CTRAMP
mkdir CTRAMP\model
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\RTP\metrics"   CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"                CTRAMP\scripts
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunModel.bat"                            .
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                          .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunMetrics.bat"                        .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunScenarioMetrics.bat"                .
copy /Y "%GITHUB_DIR%\utilities\RTP\ExtractKeyFiles.bat"                   .
::copy /Y "%GITHUB_DIR%\utilities\check-setupmodel\Check_SetupModelLog.py"   .

if "%COMPUTER_PREFIX%" == "WIN-" (copy "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"  "CTRAMP\scripts\notify_slack.py")
if "%COMPUTER_PREFIX%" == "WIN-"    set HOST_IP_ADDRESS=10.0.0.59

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3: copy over input from INPUT_DEVELOPMENT or the previous run
:: (or sometimes a special location for the properties file)
::
:: ------------------------------------------------------------------------------------------------------

:: networks
c:\windows\system32\Robocopy.exe /E "%INPUT_NETWORK%\hwy"                                        INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%INPUT_NETWORK%\trn"                                        INPUT\trn

:: popsyn and land use
c:\windows\system32\Robocopy.exe /E "%INPUT_POPLU%\popsyn"                                       INPUT\popsyn
c:\windows\system32\Robocopy.exe /E "%INPUT_POPLU%\landuse"                                      INPUT\landuse

:: nonres
c:\windows\system32\Robocopy.exe /E "%INPUT_DEVELOPMENT_DIR%\nonres\nonres_00"                   INPUT\nonres

:: logsums and metrics
c:\windows\system32\Robocopy.exe /E "%INPUT_DEVELOPMENT_DIR%\logsums_dummies"                    INPUT\logsums
c:\windows\system32\Robocopy.exe /E "%INPUT_DEVELOPMENT_DIR%\metrics"                            INPUT\metrics

:: warmstart (copy from the previous run)
mkdir INPUT\warmstart\main
mkdir INPUT\warmstart\nonres
copy /Y "%PREV_RUN_DIR%\OUTPUT\main\*.tpp"                                                       INPUT\warmstart\main
copy /Y "%PREV_RUN_DIR%\OUTPUT\nonres\*.tpp"                                                     INPUT\warmstart\nonres
del INPUT\warmstart\nonres\ixDaily2015.tpp
del INPUT\warmstart\nonres\ixDailyx4.tpp 

:: the properties file
copy /Y "%PARAMS%"                                                                               INPUT\params.properties

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4: Overrides for Blueprint Strategies
::
:: ------------------------------------------------------------------------------------------------------
if %AddStrategies%==No goto DoneAddingStrategies
:: ------
:: Blueprint Regional Transit Fare Policy
:: ------
:: Same as PPA project 6100_TransitFare_Integration
copy /Y "%BP_OVERRIDE_DIR%\Regional_Transit_Fare_Policy\TransitSkims.job"     CTRAMP\scripts\skims

:: means-based fare discount -- 50% off for Q1 -- are config in the parmas.properties file (see step 1)

:: ------
:: Blueprint Vision Zero
:: ------
:: Start year (freeways): 2030
:: Start year (local streets): 2025

:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul

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
:: https://app.asana.com/0/403262763383022/1160600926245407
:: implemented as an UEC override for now; pass the bike constant via params when there is time
copy /Y "%BP_OVERRIDE_DIR%\Complete_Streets_Network\ModeChoice_%MODEL_YEAR_NUM%.xls"         CTRAMP\model\ModeChoice.xls
copy /Y "%BP_OVERRIDE_DIR%\Complete_Streets_Network\TripModeChoice_%MODEL_YEAR_NUM%.xls"     CTRAMP\model\TripModeChoice.xls

:DoneAddingStrategies

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: Patches to Travel Model Release 
::
:: ------------------------------------------------------------------------------------------------------
:: in case the TM release is behind, this is where we copy the most up-to-date scripts from master
set GITHUB_MASTER=\\tsclient\X\travel-model-one-master

:: runmodel is behind
:: because I took out the lines related to UseTollDist
copy /Y "%GITHUB_MASTER%\model-files\RunModel.bat"                            .

:: some minor updates to trips.rdata for the tnc electrification calculator
copy /y "%GITHUB_MASTER%\model-files\scripts\core_summaries\CoreSummaries.R"              CTRAMP\scripts\core_summaries\

:: some minor updates to ExtractKeyFiles
copy /Y "%GITHUB_MASTER%\utilities\RTP\ExtractKeyFiles.bat"                               .

:: added AV share =30% to auto_ownership UECs
copy /y "%GITHUB_MASTER%\model-files\model\AutoOwnership.xls"                             CTRAMP\model\AutoOwnership.xls

:: add run_qaqc.bat
copy /Y "%GITHUB_MASTER%\utilities\RTP\QAQC\Run_QAQC.bat"                                 .

:: add a process to check setupmodel
copy /Y "%GITHUB_MASTER%\utilities\check-setupmodel\Check_SetupModelLog.py"               .

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
robocopy.exe %dir1% %dir2% /e /l /ns /njs /ndl /fp /log:"%M_DIR%\CompareInputs.txt"

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
set CopyOfSetupModel="SetUpModel_" %myfolder%".txt"
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