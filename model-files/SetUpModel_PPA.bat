
:: ------------------------------------------------------------------------------------------------------
::
:: Step 0:  Set up folder structure and copy inputs from base and non-base
::
:: ------------------------------------------------------------------------------------------------------

SET computer_prefix=%computername:~0,4%

:: copy over CTRAMP
set GITHUB_DIR=C:\mtc_transit_2050\TM15_initial_setup\travel-model-one
mkdir CTRAMP\model
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\RTP\metrics"   CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"                CTRAMP\scripts
copy /Y "%GITHUB_DIR%\model-files\RunModel.bat"                            .
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                          .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunMetrics.bat"                        .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunScenarioMetrics.bat"                .
copy /Y "%GITHUB_DIR%\utilities\RTP\ExtractKeyFiles.bat"                   .

if "%COMPUTER_PREFIX%" == "WIN-"    (copy "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"  "CTRAMP\scripts\notify_slack.py")
if "%COMPUTER_PREFIX%" == "WIN-"    set HOST_IP_ADDRESS=10.0.0.33

:: copy over INPUTs from baseline
set MODEL_SETUP_BASE_DIR=C:\mtc_transit_2050\TM15_initial_setup\2015_TM152_IPA_19
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\landuse"                       INPUT\landuse
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\logsums"                       INPUT\logsums
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\metrics"                       INPUT\metrics
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\nonres"                        INPUT\nonres
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\popsyn"                        INPUT\popsyn
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\warmstart"                     INPUT\warmstart
copy /Y "%MODEL_SETUP_BASE_DIR%\INPUT\params.properties"                                         INPUT\params.properties

:: copy over ShadowPricing file from baseline
:: needed for all project runs; not needed for baseline runs
copy /Y "%MODEL_SETUP_BASE_DIR%\OUTPUT\main\ShadowPricing_7.csv"                                 INPUT\logsums

:: copy over project specific inputs
set MODEL_SETUP_DIR=C:\mtc_transit_2050\TM15_initial_setup\2015_TM152_IPA_19\INPUT
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_DIR%\hwy"                           INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_DIR%\trn"                           INPUT\trn

@REM :: set the location of the output folder; this is where the extractor directory will be copied to
@REM set M_DIR=%MODEL_SETUP_DIR%

@REM :: copy this batch file itself to M
@REM copy SetUpModel.bat "%M_DIR%\SetUpModel.bat"

::-----------------------------------------------------------------------
:: add folder name to the command prompt window 
::-----------------------------------------------------------------------
@REM set MODEL_DIR=%CD%
@REM set PROJECT_DIR=%~p0
@REM set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
@REM :: get the base dir only
@REM for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf

@REM title %myfolder%


::-----------------------------------------------------------------------
:: create a shortcut of the project directory using a temporary VBScript
::-----------------------------------------------------------------------

@REM set TEMP_SCRIPT="%CD%\temp_script_to_create_shortcut.vbs"
@REM set PROJECT_DIR=%~p0
@REM set ALPHABET=%computername:~7,1%

@REM echo Set oWS = WScript.CreateObject("WScript.Shell") >> %TEMP_SCRIPT%
@REM echo sLinkFile = "%M_DIR%/model_run_on_%computername%.lnk" >> %TEMP_SCRIPT%
@REM echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %TEMP_SCRIPT%
@REM echo oLink.TargetPath = "M:" >> %TEMP_SCRIPT%
@REM echo oLink.TargetPath = "\\%computername%\%PROJECT_DIR%" >> %TEMP_SCRIPT%

@REM echo oLink.Save >> %TEMP_SCRIPT%

@REM ::C:\Windows\SysWOW64\cscript.exe /nologo %TEMP_SCRIPT%
@REM C:\Windows\SysWOW64\cscript.exe %TEMP_SCRIPT%
@REM del %TEMP_SCRIPT%