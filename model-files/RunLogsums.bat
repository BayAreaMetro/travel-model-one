::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunAccessibility.bat
::
:: MS-DOS batch file to compute destination choice logsums for the MTC travel model.  This batch file
:: must be executed in the same manner as "RunModel", using the node machines in the same way.
::
:: dto (2012 06 11)
:: jef (2018 12 26)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo on
:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: Set the path
call CTRAMP\runtime\SetPath.bat

::  Set the IP address of the host machine which sends tasks to the client machines 
if %computername%==MODEL2-A            set HOST_IP_ADDRESS=10.1.1.206
if %computername%==MODEL2-B            set HOST_IP_ADDRESS=192.168.1.207
if %computername%==MODEL2-C            set HOST_IP_ADDRESS=192.168.1.208
if %computername%==MODEL2-D            set HOST_IP_ADDRESS=192.168.1.209
if %computername%==MODEL3-A            set HOST_IP_ADDRESS=10.164.0.200
if %computername%==MODEL3-B            set HOST_IP_ADDRESS=10.164.0.201
if %computername%==MODEL3-C            set HOST_IP_ADDRESS=10.164.0.202
if %computername%==MODEL3-D            set HOST_IP_ADDRESS=10.164.0.203
if %computername%==PORMDLPPW01         set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02         set HOST_IP_ADDRESS=172.24.0.102
if %computername%==WIN-FK0E96C8BNI     set HOST_IP_ADDRESS=10.0.0.154

:: ShadowPricing should come from baseline run, copied into logsums by SetUpModel.bat
:: If it's not there, this is a baseline
if not exist logsums\ShadowPricing_7.csv (
  copy main\ShadowPricing_7.csv logsums\shadowPricing_7.csv
)

:: create logsums.properties
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --logsums
if ERRORLEVEL 1 goto done

:: List unconnected zones in skims\unconnected_zones.dbf
runtpp CTRAMP\scripts\skims\FindNoAccessZones.job
if ERRORLEVEL 2 goto done

:: Filter out households in those unconnected zones
python CTRAMP\scripts\preprocess\filterUnconnectedDummyHouseholds.py
if ERRORLEVEL 1 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Execute Java
::
:: ------------------------------------------------------------------------------------------------------

if not exist logsums\indivTripData_%ITER%.csv (

  echo STARTED LOGSUMS RUN  %DATE% %TIME% >> logs\feedback.rpt

  rem run matrix manager, household manager and jppf driver
  cd CTRAMP\runtime
  call javaOnly_runMain.cmd 

  rem run jppf node
  cd CTRAMP\runtime
  call javaOnly_runNode0.cmd

  rem Execute the accessibility calculations
  java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties -Djava.library.path=%RUNTIME% com.pb.mtc.ctramp.MTCCreateLogsums logsums

  rem shut down java
  C:\Windows\SysWOW64\taskkill /f /im "java.exe"
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3: Reformat logsums
::
:: ------------------------------------------------------------------------------------------------------

set TARGET_DIR=%CD%
if not exist logsums\mandatoryAccessibilities.csv (
  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla ".\CTRAMP\scripts\core_summaries\logsumJoiner.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Accessibilities Markets
::
:: ------------------------------------------------------------------------------------------------------

if not exist core_summaries\AccessibilityMarkets.csv (
  rem Rename these to standard names
  if not exist %TARGET_DIR%\popsyn\hhFile.csv     ( copy %TARGET_DIR%\popsyn\hhFile.*.csv %TARGET_DIR%\popsyn\hhFile.csv )
  if not exist %TARGET_DIR%\popsyn\personFile.csv ( copy %TARGET_DIR%\popsyn\personFile.*.csv %TARGET_DIR%\popsyn\personFile.csv )

  call "%R_HOME%\bin\x64\Rscript.exe" --vanilla ".\CTRAMP\scripts\core_summaries\AccessibilityMarkets.R"
  IF %ERRORLEVEL% GTR 0 goto done
)

:: Complete target and message
:done
ECHO FINISHED.  
