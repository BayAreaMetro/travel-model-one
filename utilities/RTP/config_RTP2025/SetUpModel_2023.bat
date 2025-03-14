:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Specify file locations
::
:: ------------------------------------------------------------------------------------------------------

:: set the location of the model run folder on M; this is where the input and output directories will be copied to
set M_DIR=M:\Application\Model One\RTP2025\IncrementalProgress\2023_TM161_IPA_27
:: Should strategies be included? AddStrategies=Yes for Project runs; AddStrategies=No for NoProject runs.
set AddStrategies=No
set EN7=DISABLED

:: set the location of the Travel Model Release
set GITHUB_DIR=X:\travel-model-one-v1.6.1_develop

:: set the location of the networks (make sure the network version, year and variant are correct)
set INPUT_NETWORK=M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\Networks\BlueprintNetworks_v21\net_2023_Baseline

:: set the location of the populationsim and land use inputs (make sure the land use version and year are correct) 
set INPUT_POPLU=M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\LandUse_n_Popsyn\2023_v12

:: draft blueprint was s23; final blueprint is s24; final blueprint no project is s25.
:: note that UrbanSimScenario relates to the land use scenario to which the TM output will be applied (not the input land use scenario for the TM)
set UrbanSimScenario=s24

:: set the location of the input directories for non resident travel, logsums and metrics
set NONRES_INPUT_DIR=M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\nonres\nonres_06
set LOGSUMS_INPUT_DIR=M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\logsums_dummies
set METRICS_INPUT_DIR=M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\metrics\metrics_01

:: set the location of the previous run (where warmstart inputs will be copied)
:: the INPUT folder of the previous run will also be used as the base for the compareinputs log
set PREV_RUN_DIR=M:\Application\Model One\RTP2025\IncrementalProgress\2023_TM161_IPA_26

:: set the name and location of the properties file
:: often the properties file is on master during the active application phase
set PARAMS=X:\travel-model-one-v1.6.1_develop\utilities\RTP\config_RTP2025\params_2023.properties

:: set the location of the overrides directory (for Blueprint strategies)
set BP_OVERRIDE_DIR=NA

:: --------------------------------------------
:: before setting up the folder structure and copying CTRAMP
:: check that the model run folder on the M drive has the same name as the folder on the modeling server
:: --------------------------------------------

REM Split the path into parts using backslash as the delimiter for M_DIR
for %%A in ("%M_DIR%") do (
    set "runid_OnM=%%~nA"
)

REM Split the path into parts using backslash as the delimiter for the current directory
REM which is the full model run directory on the modeling server
for %%A in ("%CD%") do (
    set "runid_OnFullRun=%%~nA"
)

IF "%runid_OnM%"=="%runid_OnFullRun%" (
    goto :continue
) else (
    goto :errormessage1
)

:errormessage1
@echo off
echo The model run folder on the M drive:        %runid_OnM%
echo The model run folder of the full model run: %runid_OnFullRun%
echo ERROR: The model run folder on the M drive does not have the same name as the full model run
@echo on
goto :end

:continue


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
c:\windows\system32\Robocopy.exe /NP /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /NP /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /NP /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /NP /E "%GITHUB_DIR%\utilities\RTP\metrics"   CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR\utilities\cube-to-shapefile\cube_to_shapefile.py"         CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR\utilities\cube-to-shapefile\correspond_link_to_TAZ.py"    CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunModel.bat"                            .
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                          .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\model-files\RunPrepareEmfac.bat"                     .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunMetrics.bat"                        .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunScenarioMetrics.bat"                .
copy /Y "%GITHUB_DIR%\utilities\RTP\ExtractKeyFiles.bat"                   .

if "%COMPUTER_PREFIX%" == "WIN-"    set HOST_IP_ADDRESS=10.0.0.59

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3: copy over input from INPUT_DEVELOPMENT or the previous run
:: (or sometimes a special location for the properties file)
::
:: ------------------------------------------------------------------------------------------------------

:: networks
c:\windows\system32\Robocopy.exe /NP /E "%INPUT_NETWORK%\hwy"                                        INPUT\hwy
c:\windows\system32\Robocopy.exe /NP /E "%INPUT_NETWORK%\trn"                                        INPUT\trn

:: popsyn and land use
c:\windows\system32\Robocopy.exe /NP /E "%INPUT_POPLU%\popsyn"                                       INPUT\popsyn
c:\windows\system32\Robocopy.exe /NP /E "%INPUT_POPLU%\landuse"                                      INPUT\landuse
copy /Y "%GITHUB_DIR%\utilities\telecommute\telecommute_max_rate_county.csv"                         INPUT\landuse\telecommute_max_rate_county.csv

:: nonres
c:\windows\system32\Robocopy.exe /E "%NONRES_INPUT_DIR%"                                         INPUT\nonres

:: logsums and metrics
c:\windows\system32\Robocopy.exe /E "%LOGSUMS_INPUT_DIR%"                                        INPUT\logsums
c:\windows\system32\Robocopy.exe /E "%METRICS_INPUT_DIR%"                                        INPUT\metrics

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
:: Step 3a: copy the air passenger trip matrices for the model year
::
:: ------------------------------------------------------------------------------------------------------


:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=%myfolder:~0,4%

set /a MODEL_YEAR_NUM=%MODEL_YEAR% 2>nul

::  Copy the air passenger trip matrices for the model year
if %MODEL_YEAR_NUM%==2015 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2015b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2015b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2015b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2015b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2015b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2023 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2023b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2023b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2023b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2023b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2023b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2025 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2025b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2025b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2025b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2025b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2025b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2030 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2030b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2030b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2030b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2030b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2030b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2035 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2035b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2035b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2035b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2035b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2035b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2040 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2040b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2040b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2040b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2040b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2040b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2045 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2045b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2045b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2045b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2045b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2045b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)
if %MODEL_YEAR_NUM%==2050 (
    copy /Y "%NONRES_INPUT_DIR%\airpax\2050b_tripsAirPaxEA.tpp"  INPUT\nonres\tripsAirPaxEA.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2050b_tripsAirPaxAM.tpp"  INPUT\nonres\tripsAirPaxAM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2050b_tripsAirPaxMD.tpp"  INPUT\nonres\tripsAirPaxMD.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2050b_tripsAirPaxPM.tpp"  INPUT\nonres\tripsAirPaxPM.tpp
    copy /Y "%NONRES_INPUT_DIR%\airpax\2050b_tripsAirPaxEV.tpp"  INPUT\nonres\tripsAirPaxEV.tpp
)

:: error handling:
:: generate an error message in setupmodel.log if tripsAirPaxAM.tpp is missing
copy /Y INPUT\nonres\tripsAirPaxAM.tpp  INPUT\nonres\tripsAirPaxAM.tpp



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

:DoneAddingStrategies

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: Patches to Travel Model Release 
::
:: ------------------------------------------------------------------------------------------------------
:: in case the TM release is behind, this is where we copy the most up-to-date scripts from master
set GITHUB_MASTER=X:\travel-model-one-master

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
    c:\windows\system32\Robocopy.exe /NP /E "INPUT" "%M_DIR%\INPUT_%mm%%dd%%yy%_%hh%%min%%ss%"
) else (
    c:\windows\system32\Robocopy.exe /NP /E "INPUT" "%M_DIR%\INPUT"
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



:: ------------------------------------------------------------------------------------------------------
::
:: Step 7: log the git commit and git status of GITHUB_DIR
::
:: ------------------------------------------------------------------------------------------------------
set CURRENT_DIR=%CD%
cd /d %GITHUB_DIR%
git log -1
git status
cd /d %CURRENT_DIR%



:end