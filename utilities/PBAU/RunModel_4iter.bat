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

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jdk1.7.0_71

:: The location of the GAWK binary executable files
set GAWK_PATH=M:\UTIL\Gawk

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files (x86)\Citilabs\CubeVoyager

:: The location of the MTC.JAR file
set RUNTIME=CTRAMP/runtime

:: Add these variables to the PATH environment variable, moving the current path to the back
set OLD_PATH=%PATH%
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%OLD_PATH%

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar

::  Set the IP address of the host machine which sends tasks to the client machines 
set HOST_IP_ADDRESS=192.168.1.200


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
mkdir database

:: Stamp the feedback report with the date and time of the model start
echo STARTED MODEL RUN  %DATE% %TIME% >> logs\feedback.rpt 

:: Move the input files, which are not accessed by the model, to the working directories
copy INPUT\hwy\                 hwy\
copy INPUT\trn\transit_lines\   trn\
copy INPUT\trn\transit_fares\   trn\ 
copy INPUT\trn\transit_support\ trn\
copy INPUT\landuse\             landuse\
copy INPUT\popsyn\              popsyn\
copy INPUT\nonres\              nonres\
copy INPUT\warmstart\main\      main\
copy INPUT\warmstart\nonres\    nonres\


:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Pre-process steps
::
:: ------------------------------------------------------------------------------------------------------

: Pre-Process

:: Runtime configuration: set project directory, auto operating cost, 
:: and synthesized household/population files in the appropriate places
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py
if ERRORLEVEL 1 goto done

:: Make sure java isn't running already
CTRAMP\runtime\pslist.exe java
if %ERRORLEVEL% EQU 0 goto done
CTRAMP\runtime\pslist.exe \\satmodel java
if %ERRORLEVEL% EQU 0 goto done
CTRAMP\runtime\pslist.exe \\satmodel2 java
if %ERRORLEVEL% EQU 0 goto done
CTRAMP\runtime\pslist.exe \\satmodel3 java
if %ERRORLEVEL% EQU 0 goto done
CTRAMP\runtime\pslist.exe \\satmodel4 java
if %ERRORLEVEL% EQU 0 goto done

if not exist satmodel.txt goto done
set /p nothing= < satmodel.txt
cd CTRAMP\runtime
set RUNTIMEDIR=%CD%

:: Run the java processes locally and verify
.\PsExec.exe JavaOnly_runMain.cmd
.\PsExec.exe JavaOnly_runNode0.cmd
.\pslist.exe java
if %ERRORLEVEL% NEQ 0 goto done

:: For remote - it's more complicated.  PsExec starts a process that doesn't have access to M: or MAINMODELSHARE
:: So we need to use a helper
copy /Y psexec_helper.bat %TEMP%
C:
cd %TEMP%

:: satmodel
%RUNTIMEDIR%\PsExec.exe \\satmodel -u SATMODEL\MTCPB -p %nothing% -i 2 -c -f %TEMP%\psexec_helper.bat %RUNTIMEDIR% .\JavaOnly_runNode1.cmd
%RUNTIMEDIR%\pslist.exe \\satmodel java
if %ERRORLEVEL% NEQ 0 goto done

:: satmodel2
%RUNTIMEDIR%\PsExec.exe \\satmodel2 -u SATMODEL2\MTCPB -p %nothing% -i 2 -c -f %TEMP%\psexec_helper.bat %RUNTIMEDIR% .\JavaOnly_runNode2.cmd
%RUNTIMEDIR%\pslist.exe \\satmodel2 java
if %ERRORLEVEL% NEQ 0 goto done

:: satmodel3
%RUNTIMEDIR%\PsExec.exe \\satmodel3 -u SATMODEL3\MTCPB -p %nothing% -i 2 -c -f %TEMP%\psexec_helper.bat %RUNTIMEDIR% .\JavaOnly_runNode3.cmd
%RUNTIMEDIR%\pslist.exe \\satmodel3 java
if %ERRORLEVEL% NEQ 0 goto done

:: satmodel4
%RUNTIMEDIR%\PsExec.exe \\satmodel4 -u SATMODEL4\MTCPB -p %nothing% -i 2 -c -f %TEMP%\psexec_helper.bat %RUNTIMEDIR% .\JavaOnly_runNode4.cmd
%RUNTIMEDIR%\pslist.exe \\satmodel4 java
if %ERRORLEVEL% NEQ 0 goto done

M:
cd %RUNTIMEDIR%
cd ..
cd ..

:: Set the prices in the roadway network
runtpp CTRAMP\scripts\preprocess\SetTolls.job
if ERRORLEVEL 2 goto done

:: Set a penalty to dummy links connecting HOV/HOT lanes and general purpose lanes
runtpp CTRAMP\scripts\preprocess\SetHovXferPenalties.job
if ERRORLEVEL 2 goto done

:: Create time-of-day-specific 
runtpp CTRAMP\scripts\preprocess\CreateFiveHighwayNetworks.job
if ERRORLEVEL 2 goto done

:: Add pavement cost adjustment for state of good repair work
runtpp CTRAMP\scripts\preprocess\AddPavementCost.job
if ERRORLEVEL 2 goto done



:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Build non-motorized level-of-service matrices
::
:: ------------------------------------------------------------------------------------------------------

: Non-Motorized Skims

:: Translate the roadway network into a non-motorized network
runtpp CTRAMP\scripts\skims\CreateNonMotorizedNetwork.job
if ERRORLEVEL 2 goto done

:: Build the skim tables
runtpp CTRAMP\scripts\skims\NonMotorizedSkims.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 5:  Prepare for Iteration 0
::
:: ------------------------------------------------------------------------------------------------------

: iter0

:: Set the iteration parameters
set ITER=0
set PREV_ITER=0
set WGT=1.0
set PREV_WGT=0.00


:: ------------------------------------------------------------------------------------------------------
::
:: Step 6:  Execute the RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 7:  Prepare for iteration 1 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter1

:: Set the iteration parameters
set ITER=1
set PREV_ITER=1
set WGT=1.0
set PREV_WGT=0.00
set SAMPLESHARE=0.15
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 7.1:  Prepare for iteration 2 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter2

:: Set the iteration parameters
set ITER=2
set PREV_ITER=1
set WGT=0.50
set PREV_WGT=0.50
set SAMPLESHARE=0.25
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 7.2:  Prepare for iteration 3 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter3

:: Set the iteration parameters
set ITER=3
set PREV_ITER=2
set WGT=0.33
set PREV_WGT=0.67
set SAMPLESHARE=0.50
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 7.2.1:  Run transit assignment and metrics for iter3 outputs
::
:: ------------------------------------------------------------------------------------------------------
runtpp CTRAMP\scripts\assign\TransitAssign.job
if ERRORLEVEL 2 goto done

:: use zero cost transters
move CTRAMP\model\accessibility_utility.xls                  CTRAMP\model\accessibility_utility_original.xls
copy CTRAMP\model\accessibility_utility_zeroCostTransfer.xls CTRAMP\model\accessibility_utility.xls

call RunAccessibility
if ERRORLEVEL 2 goto done

call RunMetrics
if ERRORLEVEL 2 goto done

:: save iter3 outputs
move accessibilities accessibilities_iter%ITER%
move core_summaries  core_summaries_iter%ITER%
move metrics         metrics_iter%ITER%

:: just in case -- save metrics inputs from this iteration
for %%H in (EA AM MD PM EV) DO (
  copy nonres\tripsIx%%H.tpp              nonres\tripsIx%%H_iter%ITER%.tpp
  copy nonres\tripsAirPax%%H.tpp          nonres\tripsAirPax%%H_iter%ITER%.tpp
  copy nonres\tripstrk%%H.tpp             nonres\tripstrk%%H_iter%ITER%.tpp
  for %%G in (com hvy exp lrf loc) DO (
    copy skims\trnskm%%H_wlk_%%G_wlk.tpp  skims\trnskm%%H_wlk_%%G_wlk_iter%ITER%.tpp
    copy skims\trnskm%%H_drv_%%G_wlk.tpp  skims\trnskm%%H_drv_%%G_wlk_iter%ITER%.tpp
    copy skims\trnskm%%H_wlk_%%G_drv.tpp  skims\trnskm%%H_wlk_%%G_drv_iter%ITER%.tpp

    copy trn\trnlink%%H_wlk_%%G_wlk.dbf   trn\trnlink%%H_wlk_%%G_wlk_iter%ITER%.dbf
    copy trn\trnlink%%H_drv_%%G_wlk.dbf   trn\trnlink%%H_drv_%%G_wlk_iter%ITER%.dbf
    copy trn\trnlink%%H_wlk_%%G_drv.dbf   trn\trnlink%%H_wlk_%%G_drv_iter%ITER%.dbf
  )
  copy skims\HWYSKM%%H.tpp                skims\HWYSKM%%H_iter%ITER%.tpp
  copy skims\COM_HWYSKIM%%H.tpp           skims\COM_HWYSKIM%%H_iter%ITER%.tpp
)


:: ------------------------------------------------------------------------------------------------------
::
:: Step 7.3:  Prepare for iteration 4 and execute RunIteration batch file
::
:: ------------------------------------------------------------------------------------------------------

: iter4

:: Set the iteration parameters
set ITER=4
set PREV_ITER=3
set WGT=0.33
set PREV_WGT=0.67
set SAMPLESHARE=0.50
set SEED=0

:: Runtime configuration: set the workplace shadow pricing parameters
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --iter %ITER%
if ERRORLEVEL 1 goto done

:: Call RunIteration batch file
call CTRAMP\RunIteration.bat
if ERRORLEVEL 2 goto done

:: This file is invalid - its from iter3.  Flush to make RunMetrics regenerate it.
del main\tripsEVinc1.tpp

:: ------------------------------------------------------------------------------------------------------
::
:: Step 9: Kill processes
::
:: ------------------------------------------------------------------------------------------------------
CTRAMP\runtime\pskill.exe java
CTRAMP\runtime\pskill.exe \\satmodel java
CTRAMP\runtime\pskill.exe \\satmodel2 java
CTRAMP\runtime\pskill.exe \\satmodel3 java
CTRAMP\runtime\pskill.exe \\satmodel4 java

:: ------------------------------------------------------------------------------------------------------
::
:: Step 10:  Assign transit trips to the transit network
::
:: ------------------------------------------------------------------------------------------------------

: trnAssign

runtpp CTRAMP\scripts\assign\TransitAssign.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 11:  Build simplified skim databases
::
:: ------------------------------------------------------------------------------------------------------

: database

runtpp CTRAMP\scripts\database\SkimsDatabase.job
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 12:  Build destination choice logsums
::
:: ------------------------------------------------------------------------------------------------------

: logsums

call RunAccessibility
if ERRORLEVEL 2 goto done


:: ------------------------------------------------------------------------------------------------------
::
:: Step 13:  Core summaries
::
:: ------------------------------------------------------------------------------------------------------

: core_summaries
::
:: call RunCoreSummaries
:: if ERRORLEVEL 2 goto done
::

:: ------------------------------------------------------------------------------------------------------
::
:: Step 14:  Cobra Metrics
::
:: ------------------------------------------------------------------------------------------------------

call RunMetrics
if ERRORLEVEL 2 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 15:  Directory clean up
::
:: ------------------------------------------------------------------------------------------------------


: cleanup

:: Put the PATH back the way you found it
set PATH=%OLD_PATH%

:: Move all the TP+ printouts to the \logs folder
copy *.prn logs\*.prn

:: Delete all the temporary TP+ printouts and cluster files
del *.prn
del *.script.*
del *.script

:: ------------------------------------------------------------------------------------------------------
::
:: Step 16:  Extractor
::
:: ------------------------------------------------------------------------------------------------------
call ExtractKeyFiles
if ERRORLEVEL 2 goto done

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!

:: Complete target and message
:done
ECHO FINISHED.  
