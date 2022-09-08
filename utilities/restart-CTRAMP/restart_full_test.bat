:: use
set PIVOT_FROM=\\MODEL2-C\Model2C-Share\Projects\2015_TM152_NGF_04
set GITHUB_DIR=\\mainmodel\MainModelShare\travel-model-one-restart-ctramp

:setup_model
:: Setup:: copy over CTRAMP from GITHUB_DIR and INPUT from PIVOT_FROM
c:\windows\system32\Robocopy.exe /E "%PIVOT_FROM%\INPUT"        INPUT
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files"  CTRAMP
copy /Y "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"     CTRAMP\scripts

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: Set the path
call CTRAMP\runtime\SetPath.bat

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A set HOST_IP_ADDRESS=192.168.1.206
if %computername%==MODEL2-B set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D set HOST_IP_ADDRESS=192.168.1.209

set FUTURE=PBA50
:: Figure out the model year
set MODEL_DIR=%CD%
set PROJECT_DIR=%~p0
set PROJECT_DIR2=%PROJECT_DIR:~0,-1%
:: get the base dir only
for %%f in (%PROJECT_DIR2%) do set myfolder=%%~nxf
:: the first four characters are model year
set MODEL_YEAR=2015

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Create the directory structure
::
:: ------------------------------------------------------------------------------------------------------

:: Create the working directories
mkdir hwy
mkdir trn
mkdir skims
mkdir landuse
mkdir popsyn
mkdir nonres
mkdir main
mkdir logs

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\

copy "%PIVOT_FROM%\main\telecommute_constants.csv" main\

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2: copy the skims
::
:: ------------------------------------------------------------------------------------------------------

:PreProcess

:: Runtime configuration: set project directory, auto operating cost, 
:: and synthesized household/population files in the appropriate places
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5:  Prepare for Iteration 0
::
:: ------------------------------------------------------------------------------------------------------

:: copy skims
:copy_skims
copy "%PIVOT_FROM%\skims\HWYSKM*"           skims
copy "%PIVOT_FROM%\skims\COM_HWYSKIM*"      skims
copy "%PIVOT_FROM%\skims\trnskm*"           skims
copy "%PIVOT_FROM%\skims\nonmotskm.tpp"     skims
copy "%PIVOT_FROM%\skims\accessibility.csv" skims

:iter1

:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.20
set SEED=0

python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:core
rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

:: rerun the baseline

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

:: save main output files from baseline
mkdir main\baseline
copy main\*.csv main\baseline\
:: save log files from baseline
mkdir logs\baseline
copy logs\*.log logs\baseline\

:: modify the skims
copy "%GITHUB_DIR%\utilities\restart-CTRAMP\restart_test_modify_skims.job" .
set TIME_PERIOD=EA
runtpp restart_test_modify_skims.job
if ERRORLEVEL 1 goto done
copy /y skims\HWYSKMEA_mod.tpp skims\HWYSKMEA.tpp

set TIME_PERIOD=AM
runtpp restart_test_modify_skims.job
if ERRORLEVEL 1 goto done
copy /y skims\HWYSKMAM_mod.tpp skims\HWYSKMAM.tpp

set TIME_PERIOD=MD
runtpp restart_test_modify_skims.job
if ERRORLEVEL 1 goto done
copy /y skims\HWYSKMMD_mod.tpp skims\HWYSKMMD.tpp

set TIME_PERIOD=PM
runtpp restart_test_modify_skims.job
if ERRORLEVEL 1 goto done
copy /y skims\HWYSKMPM_mod.tpp skims\HWYSKMPM.tpp

set TIME_PERIOD=EV
runtpp restart_test_modify_skims.job
if ERRORLEVEL 1 goto done
copy /y skims\HWYSKMEV_mod.tpp skims\HWYSKMEV.tpp

set INSTANCE=%COMPUTERNAME%
python CTRAMP\scripts\notify_slack.py "Restart testing - TODO: disable desired submodels"

:: Prompt user to disable submodels and set RestartWithHhServer=stl
@echo off
set /P c=Disable desired submodels in the properties file and set RestartWithHhServer. Hit any key to continue...
@echo on
:: Don't care about the response

:: Restart the core
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

C:\Windows\SysWOW64\taskkill /f /im "java.exe"

set INSTANCE=%COMPUTERNAME%
python CTRAMP\scripts\notify_slack.py "Finished restart test"

:done