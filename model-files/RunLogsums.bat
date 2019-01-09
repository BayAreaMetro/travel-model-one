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
if %computername%==PORMDLPPW01 set HOST_IP_ADDRESS=172.24.0.101
if %computername%==PORMDLPPW02 set HOST_IP_ADDRESS=172.24.0.102

:: create logsums.properties
python CTRAMP\scripts\preprocess\RuntimeConfiguration.py --logsums
if ERRORLEVEL 1 goto done

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Execute Java
::
:: ------------------------------------------------------------------------------------------------------

:: Stamp the feedback report with the date and time of the model start
echo STARTED LOGSUMS RUN  %DATE% %TIME% >> logs\feedback.rpt

rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

:: Execute the accessibility calculations
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties -Djava.library.path=%RUNTIME% com.pb.mtc.ctramp.MTCCreateLogsums logsums

:: shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: Complete target and message
:done
ECHO FINISHED.  
