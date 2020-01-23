::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunModel.bat
::
:: MS-DOS batch file to execute the MTC travel model.  Each of the model steps are sequentially
:: called here.  
::
:: For complete details, please see http://mtcgis.mtc.ca.gov/foswiki/Main/RunModelBatch.
::
:: dto (2012 02 15) gde (2009 04 22)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:setup_model
:: Setup:: copy over CTRAMP
set GITHUB_DIR=\\tsclient\X\travel-model-one-calib1.5.2
mkdir CTRAMP\model
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\PBA40\metrics" CTRAMP\scripts\metrics
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP

:setup_inputs
:: copy over INPUTs from baseline
set MODEL_SETUP_BASE_DIR=M:\Application\Model One\RTP2021\IncrementalProgress\2015_TM151_IPA_00
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\landuse"        INPUT\landuse
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\nonres"         INPUT\nonres
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\popsyn"         INPUT\popsyn
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\warmstart"      INPUT\warmstart
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\hwy"            INPUT\hwy
c:\windows\system32\Robocopy.exe /E "%MODEL_SETUP_BASE_DIR%\INPUT\trn"            INPUT\trn
copy /Y "%MODEL_SETUP_BASE_DIR%\INPUT\params.properties"                          INPUT\params.properties

:: source of skims to copy
set SKIM_DIR=E:\Model2D-Share\Projects\2015_TM151_IPA_00

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: Set the path
call CTRAMP\runtime\SetPath.bat

set COMMPATH=E:\Model2D-Share\COMMPATH
Cluster "%COMMPATH%\CTRAMP" 1-48 Starthide Exit

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


:: --------TrnAssignment Setup
:: CHAMP has dwell  configured for buses (local and premium)
:: CHAMP has access configured for for everything
set TRNCONFIG=FAST
set COMPLEXMODES_DWELL= 
set COMPLEXMODES_ACCESS= 
set MAXITERATIONS=3

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
copy "%SKIM_DIR%\skims\HWYSKM*"           skims
copy "%SKIM_DIR%\skims\COM_HWYSKIM*"      skims
copy "%SKIM_DIR%\skims\trnskm*"           skims
copy "%SKIM_DIR%\skims\nonmotskm.tpp"     skims
copy "%SKIM_DIR%\skims\accessibility.csv" skims

:iter1

:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.20
set SEED=0

:: Prompt user to set the workplace shadow pricing parameters
@echo off
set /P c=Project Directory updated.  Update workplace shadow pricing parameters press Enter to continue...
@echo on
:: Don't care about the response


:core
rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:done