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

:: Set the path
call CTRAMP\runtime\SetPath.bat

::  Set the Java classpath (locations where Java needs to find configuration and JAR files)
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/accessibility.jar

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
echo STARTED ACCESSIBILITY RUN  %DATE% %TIME% >> logs\feedback.rpt

:: Execute the accessibility calculations
call java -showversion -Xms18000m -Xmx18000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -DJAVA_HOME_32="%JAVA_PATH_32%" -DJAVA_32_PORT=1181 -Djppf.config=jppf-clientDistributed.properties -Djava.library.path=%RUNTIME% com.pb.mtc.ctramp.MtcAccessibilityLogsums accessibilities
if not exist nonMandatoryAccessibities.csv (
  echo ERROR generating accessibilities
  set ERRORLEVEL=2
  goto done
)

:: Moved the statically-named outputs to the accessibilities folder
copy nonMandatoryAccessibities.csv accessibilities\nonMandatoryAccessibilities.csv
copy MandatoryAccessibities.csv accessibilities\mandatoryAccessibilities.csv
del *access*.csv

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3:  Accessibilities Markets
::
:: ------------------------------------------------------------------------------------------------------

rem delete this just in case, so we don't move an old one by accident
if exist AccessibilityMarkets.html ( del AccessibilityMarkets.html )

set CODE_DIR=.\CTRAMP\scripts\core_summaries
set TARGET_DIR=%CD%

:: Rename these to standard names
copy %TARGET_DIR%\popsyn\hhFile.*.csv %TARGET_DIR%\popsyn\hhFile.csv
copy %TARGET_DIR%\popsyn\personFile.*.csv %TARGET_DIR%\popsyn\personFile.csv

call "%R_HOME%\bin\x64\Rscript.exe" --vanilla "%CODE_DIR%\knit_AccessibilityMarkets.R"
IF %ERRORLEVEL% GTR 0 goto done

move AccessibilityMarkets.html "%TARGET_DIR%\core_summaries"
move AccessibilityMarkets.md "%TARGET_DIR%\core_summaries"

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4:  Done
::
:: ------------------------------------------------------------------------------------------------------

:: Success target and message
:success
ECHO FINISHED SUCCESSFULLY!
echo ENDED ACCESSIBILITY RUN  %DATE% %TIME% >> logs\feedback.rpt

:: Complete target and message
:done
ECHO FINISHED.  
