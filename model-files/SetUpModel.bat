
:: ------------------------------------------------------------------------------------------------------
::
:: Step 0:  Set up folder structure and copy inputs from base and non-base
::
:: ------------------------------------------------------------------------------------------------------

:: copy over CTRAMP
set GITHUB_DIR=\\mainmodel\MainModelShare\travel-model-1.5.0
mkdir CTRAMP\model
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\PBA40\metrics" CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                    .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\utilities\PBA40\RunMetrics.bat"                      .
copy /Y "%GITHUB_DIR%\utilities\PBA40\RunScenarioMetrics.bat"              .
copy /Y "%GITHUB_DIR%\utilities\PBA40\ExtractKeyFiles.bat"                 .

:: copy over INPUTs from baseline
set MODEL_SETUP_BASE_DIR=Z:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects\2050_TM150_PPA_BF_00\INPUT
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\landuse"                       INPUT\landuse
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\logsums"                       INPUT\logsums
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\metrics"                       INPUT\metrics
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\nonres"                        INPUT\nonres
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\popsyn"                        INPUT\popsyn
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\warmstart"                     INPUT\warmstart
copy /Y "%MODEL_SETUP_BASE_DIR%\params.properties"                                         INPUT\params.properties

:: copy over project specific INPUTs 
set MODEL_SETUP_NONBASE_DIR=Z:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects\1_Crossings5\2050_TM150_PPA_BF_00_1_Crossings5
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_NONBASE_DIR%\hwy"                        INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_NONBASE_DIR%\trn"                        INPUT\trn

:: set the location of the output folder; this is where the extractor directory will be copied to
set M_DIR=%MODEL_SETUP_NONBASE_DIR%

:: copy this batch file itself to M
copy SetUpModel.bat "%M_DIR%\SetUpModel.bat"



::-----------------------------------------------------------------------
:: add folder name to the command prompt window 
::-----------------------------------------------------------------------
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf

title %myfolder%


::-----------------------------------------------------------------------
:: create a shortcut of the project directory using a temporary VBScript
::-----------------------------------------------------------------------

set TEMP_SCRIPT="%CD%\temp_script_to_create_shortcut.vbs"
set PROJECT_DIR=%~p0
set ALPHABET=%computername:~7,1%

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %TEMP_SCRIPT%
echo sLinkFile = "%M_DIR%/model_run_on_%computername%.lnk" >> %TEMP_SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %TEMP_SCRIPT%
echo oLink.TargetPath = "\\%computername%\Model2%alphabet%-Share\%PROJECT_DIR%" >> %TEMP_SCRIPT%
echo oLink.TargetPath = "Z:" >> %TEMP_SCRIPT%
echo oLink.TargetPath = "\\%computername%\Model2%alphabet%-Share\%PROJECT_DIR%" >> %TEMP_SCRIPT%

echo oLink.Save >> %TEMP_SCRIPT%

::C:\Windows\SysWOW64\cscript.exe /nologo %TEMP_SCRIPT%
C:\Windows\SysWOW64\cscript.exe %TEMP_SCRIPT%
del %TEMP_SCRIPT%