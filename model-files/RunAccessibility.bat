::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:: RunAccessibility.bat
::
:: MS-DOS batch file to compute destination choice logsums for the MTC travel model.  This batch file
:: must be executed in the same manner as "RunModel", using the node machines in the same way.
::
:: dto (2012 06 11)
::
::~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Set the necessary path variables
::
:: ------------------------------------------------------------------------------------------------------

:: The location of the 64-bit java development kit
set JAVA_PATH=C:\Program Files\Java\jdk1.7.0_71
:: This is required by MtcAccessibilityLogsums below, which will try to start up a 32-bit matrix manager process
:: However, if the matrix manager fails to start, it'll just read the matrices directly which is fine.
set JAVA_PATH_32=C:\this_does_not_exit

:: The location of the GAWK binary executable files
set GAWK_PATH=M:\UTIL\Gawk

:: The location of the RUNTPP executable from Citilabs
set TPP_PATH=C:\Program Files (x86)\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI

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
:: Step 2:  Execute Java
::
:: ------------------------------------------------------------------------------------------------------

:: Create the working directories
mkdir accessibilities

:: Stamp the feedback report with the date and time of the model start
echo STARTED ACCESSIBILITY RUN  %DATE% %TIME% >> logs\logsums.rpt 

:: Execute the accessibility calculations
call java -showversion -Xms18000m -Xmx18000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -DJAVA_HOME_32="%JAVA_PATH_32%" -DJAVA_32_PORT=1181 -Djppf.config=jppf-clientDistributed.properties -Djava.library.path=%RUNTIME% com.pb.mtc.ctramp.MtcAccessibilityLogsums accessibilities

:: Moved the statically-named outputs to the accessibilities folder
copy nonMandatoryAccessibities.csv accessibilities\nonMandatoryAccessibilities.csv
copy MandatoryAccessibities.csv accessibilities\mandatoryAccessibilities.csv
del *access*.csv

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Done
::
:: ------------------------------------------------------------------------------------------------------

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!
echo ENDED ACCESSIBILITY RUN  %DATE% %TIME% >> logs\logsums.rpt

:: Complete target and message
:done
ECHO FINISHED.  
