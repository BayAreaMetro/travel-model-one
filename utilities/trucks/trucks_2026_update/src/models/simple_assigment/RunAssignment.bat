@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: 1. Setup Base Paths (Everything relative to Root)
:: ============================================================================
:: Get the directory where the script lives, then go up one to get Root
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\..\.."
set "ROOT_DIR=%CD%"
popd

:: Input Arguments
set "SCENARIO=%~1"
set "SCENARIO_INPUTS=%~2"

:: Check if scenario name was provided
if "%SCENARIO%"=="" (
    echo ERROR: No scenario name provided.
    exit /b 1
)

:: Define all paths starting from %ROOT_DIR%
set ITER=WSP_RUN
set "UNZIP_FNAME=2023_TM161_IPA_35"
set "BASE_ZIP=%ROOT_DIR%\data\external\mtc\2023_TM161_IPA_35_20260217.zip"
::set "UNZIP_FNAME=TM16_TEMPLATE_FOR_RunAssigment"
::set "BASE_ZIP=%ROOT_DIR%\data\interim\mock_data\TM16_TEMPLATE_FOR_RunAssigment.zip"
set "RUN_DIR=%ROOT_DIR%\models\assignment\%SCENARIO%"
set "MODEL_DIR=%RUN_DIR%\%UNZIP_FNAME%"
set "LOG_FILE=%ROOT_DIR%\data\logs\%SCENARIO%.log"
set "OUTPUT_DIR=%ROOT_DIR%\data\interim\tm16_outputs\%SCENARIO%"

:: ============================================================================
:: 2. Pre-flight Checks & Log Init
:: ============================================================================
if not exist "%ROOT_DIR%\data\logs" mkdir "%ROOT_DIR%\data\logs"

echo Initializing Scenario: %SCENARIO% > "%LOG_FILE%"
echo Time: %DATE% %TIME% >> "%LOG_FILE%"

if not exist "%BASE_ZIP%" (
    echo ERROR: Base ZIP not found
    exit /b 1
)

:: ============================================================================
:: 3. Prepare Environment 
:: ============================================================================
echo Preparing directory: %RUN_DIR%
if exist "%RUN_DIR%" rmdir /s /q "%RUN_DIR%"
mkdir "%RUN_DIR%"
mkdir "%OUTPUT_DIR%"

echo Extracting base model...
tar -xf "%BASE_ZIP%" -C "%RUN_DIR%"
if errorlevel 1 goto error

:: ============================================================================
:: 4. Overlay Scenario Files (While still at Root)
:: ============================================================================
set "TARGET_INPUT_DIR=%MODEL_DIR%\nonres"

if "%SCENARIO_INPUTS%"=="" (
    echo INFO: No input path provided. Running baseline. >> "%LOG_FILE%"
) else (
    :: We check if the path is relative to root OR an absolute path
    set "FINAL_INPUT_PATH="
    if exist "%ROOT_DIR%\%SCENARIO_INPUTS%" set "FINAL_INPUT_PATH=%ROOT_DIR%\%SCENARIO_INPUTS%"
    if exist "%SCENARIO_INPUTS%" if not defined FINAL_INPUT_PATH set "FINAL_INPUT_PATH=%SCENARIO_INPUTS%"

    if defined FINAL_INPUT_PATH (
        echo Applying scenario files from: !FINAL_INPUT_PATH! >> "%LOG_FILE%"
        xcopy "!FINAL_INPUT_PATH!\*.tpp" "%TARGET_INPUT_DIR%\" /E /I /Y >> "%LOG_FILE%"
    ) else (
		echo Root directory: %ROOT_DIR%
		echo ERROR: Scenario path %SCENARIO_INPUTS% not found. >> "%LOG_FILE%"
		echo ERROR: Scenario path %SCENARIO_INPUTS% not found.
		exit /b 1
    )
)

:: ============================================================================
:: 5. Run the Model (The only time we change directory)
:: ============================================================================
if not exist "%MODEL_DIR%" (
    echo ERROR: Model directory %MODEL_DIR% not found after extraction. >> "%LOG_FILE%"
    goto error
)

echo Swapping to model directory to run...
pushd "%MODEL_DIR%"


echo Running Truck Toll Choice Model... 
runtpp CTRAMP\scripts\nonres\TruckTollChoice.job >> "%LOG_FILE%" 2>&1
if errorlevel 2 popd & goto error

echo Running Assignment... 
runtpp CTRAMP\scripts\assign\HwyAssign.job >> "%LOG_FILE%" 2>&1
if errorlevel 2 popd & goto error


:: Move assigned networks to a iteration-specific directory
mkdir hwy\iter%ITER%

move hwy\LOADEA.net hwy\iter%ITER%\LOADEA.net
move hwy\LOADAM.net hwy\iter%ITER%\LOADAM.net
move hwy\LOADMD.net hwy\iter%ITER%\LOADMD.net
move hwy\LOADPM.net hwy\iter%ITER%\LOADPM.net
move hwy\LOADEV.net hwy\iter%ITER%\LOADEV.net

:: Give the default TP+ variables more intuitive names
echo Running RenameAssignmentVariables... 
runtpp CTRAMP\scripts\feedback\RenameAssignmentVariables.job
copy hwy\iter%ITER%\LOADEA_renamed.net hwy\iter%ITER%\avgLOADEA.net /Y
copy hwy\iter%ITER%\LOADAM_renamed.net hwy\iter%ITER%\avgLOADAM.net /Y
copy hwy\iter%ITER%\LOADMD_renamed.net hwy\iter%ITER%\avgLOADMD.net /Y
copy hwy\iter%ITER%\LOADPM_renamed.net hwy\iter%ITER%\avgLOADPM.net /Y
copy hwy\iter%ITER%\LOADEV_renamed.net hwy\iter%ITER%\avgLOADEV.net /Y

:: Compute network statistics to measure convergence
echo Test Network Convergence... 
runtpp CTRAMP\scripts\feedback\TestNetworkConvergence.job
if ERRORLEVEL 2 goto done

:: Combine the time-of-day-specific networks into a single network
echo Running Merge Networks... 
runtpp CTRAMP\scripts\feedback\MergeNetworks.job
if ERRORLEVEL 2 goto done

:: Place a copy of the loaded networks into the root \hwy directory for access by the next iteration
copy hwy\iter%ITER%\avgLOADEA.net hwy\avgLOADEA.net /Y
copy hwy\iter%ITER%\avgLOADAM.net hwy\avgLOADAM.net /Y
copy hwy\iter%ITER%\avgLOADMD.net hwy\avgLOADMD.net /Y
copy hwy\iter%ITER%\avgLOADPM.net hwy\avgLOADPM.net /Y
copy hwy\iter%ITER%\avgLOADEV.net hwy\avgLOADEV.net /Y

:: ============================================================================
:: 6. Capture Outputs & Return
:: ============================================================================
echo Collecting outputs... >> "%LOG_FILE%"
if exist "hwy" (
    copy "hwy\avgLOAD??.net" "%OUTPUT_DIR%\" >> "%LOG_FILE%" 2>&1
)

if exist "hwy" (
    copy "hwy\iter%ITER%\LOAD??.net" "%OUTPUT_DIR%\" >> "%LOG_FILE%" 2>&1
)

popd
echo Scenario %SCENARIO% completed successfully.
exit /b 0

:error
echo ERROR: Scenario %SCENARIO% failed. Check %LOG_FILE%
exit /b 2