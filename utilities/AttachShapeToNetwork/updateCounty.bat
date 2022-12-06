::
:: update county for loaded networks
::
:: Run this from M:\Application\Model One\RTP2017\Scenarios
::
@echo on
setlocal enabledelayedexpansion

set CODE_DIR=X:\travel-model-one-master
set COUNTY_FILE=M:\Development\Travel Model One\Version 05\Adding City to Master Network\Cityshapes\Counties_NAD_1983_UTM_Zone_10N.shp
::set MODEL_DIRS=2015_06_002 2040_06_690 2040_06_694 2040_06_691 2040_06_693 2040_06_696 2020_06_694 2035_06_694
set MODEL_DIRS=2040_06_694_Amd2_V2 2035_06_694_Amd2_V2 2030_06_694_Amd2_V2

call "%CODE_DIR%\model-files\runtime\SetPath.bat"

for %%H in (%MODEL_DIRS%) DO (
  set MODEL_DIR=%%H
  echo MODEL DIRECTORY is [!MODEL_DIR!]

  if not exist !MODEL_DIR!\OUTPUT\avgload5period_wcounty.net (
    python "%CODE_DIR%\utilities\AttachShapeToNetwork\attachShapeToNetwork.py" -s NAME -c COUNTY !MODEL_DIR!\OUTPUT\avgload5period.net "%COUNTY_FILE%" !MODEL_DIR!\OUTPUT\avgload5period_wcounty.net
    if ERRORLEVEL 1 goto done
  )

  if not exist !MODEL_DIR!\OUTPUT\avgload5period_wcounty.csv (
    runtpp "%CODE_DIR%\utilities\AttachShapeToNetwork\net2csv.job"
    if ERRORLEVEL 2 goto done
  )
)

:combine1
goto combine2

set COMBINED_DIR=Across-Alternatives-2040-Round-14-Amd1
set RUN_NAME_SET=2015_06_002 2040_06_690 2040_06_694 2040_06_694_Amd2 2040_06_691 2040_06_693 2040_06_697

:: Convert the avgload5period.csv
set HWYFILE_DIRS=%RUN_NAME_SET: =\OUTPUT %
set HWYFILE_DIRS=%HWYFILE_DIRS%\OUTPUT

echo Reading avgload5period_wcounty.csv files from HWYFILE_DIRS=
echo   [%HWYFILE_DIRS%]
copy /Y %COMBINED_DIR%\ScenarioKey.csv .

:combine2
set COMBINED_DIR=Across-Alternatives-Round-15-Proposed-Plan-Amd2
set RUN_NAME_SET=2015_06_002 2020_06_694 2030_06_694 2030_06_694_Amd1 2030_06_694_Amd2 2035_06_694 2035_06_694_Amd1 2035_06_694_Amd2 2040_06_694 2040_06_694_Amd1 2040_06_694_Amd2

:: Convert the avgload5period.csv
set HWYFILE_DIRS=%RUN_NAME_SET: =\OUTPUT %
set HWYFILE_DIRS=%HWYFILE_DIRS%\OUTPUT

echo Reading avgload5period_wcounty.csv files from HWYFILE_DIRS=
echo   [%HWYFILE_DIRS%]
copy /Y %COMBINED_DIR%\ScenarioKey.csv .

:done