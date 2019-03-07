
:: ------------------------------------------------------------------------------------------------------
::
:: Step 0:  Set up folder structure and copy inputs from base and non-base
::
:: ------------------------------------------------------------------------------------------------------

:: copy over CTRAMP
set GITHUB_DIR=\\mainmodel\MainModelShare\travel-model-one-1.25.1
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
set MODEL_SETUP_BASE_DIR=Z:\Application\Model One\RTP2021\Scenarios\2030_TM125_FU1_BF_02\INPUT
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\logsums"                       INPUT\logsums
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\metrics"                       INPUT\metrics
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\nonres"                        INPUT\nonres
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\warmstart"                     INPUT\warmstart
copy /Y "%MODEL_SETUP_BASE_DIR%\params.properties"                                         INPUT\params.properties

:: copy over project specific INPUTs 
set MODEL_SETUP_NONBASE_DIR=Z:\Application\Model One\RTP2021\ProjectPerformanceAssessment\Projects\baseline_BF_00\network_2030
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_NONBASE_DIR%\hwy"                        INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_NONBASE_DIR%\trn"                        INPUT\trn

:: copy over land use and pop syn INPUTs 
set MODEL_SETUP_NONBASE_DIR2=Z:\Application\Model One\RTP2021\ProjectPerformanceAssessment\TestProjects\2030_TM125_PPA_BF_00
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_NONBASE_DIR2%\landuse"                   INPUT\landuse
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\popsyn"                        INPUT\popsyn

:: set the location of the output folder; this is where the extractor directory will be copied to
set M_DIR=%MODEL_SETUP_NONBASE_DIR2%

:: copy this batch file itself to M
copy SetUpModel.bat %M_DIR%\SetUpModel.bat