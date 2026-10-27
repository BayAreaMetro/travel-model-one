@echo off

cd /d %~dp0

if not exist logs mkdir logs

set LOGFILE=logs\scenario_metrics.log
echo =====================================
echo Running Scenario Metrics
echo =====================================
echo.

uv run createScenarioMetrics.py --config config\scenario_metrics.json


if errorlevel 1 (
    echo.
    echo Metrics failed.
    pause
    exit /b 1
)

echo.
echo Metrics completed successfully.
pause
