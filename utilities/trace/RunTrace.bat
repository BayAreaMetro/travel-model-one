:: saved backup:
::   copy CTRAMP\runtime\mtcTourBased.properties CTRAMP\runtime\mtcTourBased.properties_runVersion
::   move logs logs_runVersion
::   mkdir logs
:: create trace dir:
::   mkdir trace
::   copy main\ShadowPricing_5.csv  trace
:: updated for trace:
::   replaced main with trace
::   added Debug.Trace.HouseholdIdList=94541
::   updated log4j-node0.xml with
::   <!-- choice model info logger statements will be sent to info-FILE-2 -->
::       <logger name="tripMcLog" additivity="false">
::           <level value="debug"/>
::           <appender-ref ref="TripMC-FILE"/>
::       </logger>

:: Set the path
call CTRAMP\runtime\SetPath.bat

: iter3

:: Set the iteration parameters
set ITER=3
set SEED=0

rem run matrix manager, household manager and jppf driver
cd CTRAMP\runtime
call javaOnly_runMain.cmd 

rem run jppf node
cd CTRAMP\runtime
call javaOnly_runNode0.cmd

::  Call the MtcTourBasedModel class
java -showversion -Xmx6000m -cp %CLASSPATH% -Dlog4j.configuration=log4j.xml -Djava.library.path=%RUNTIME% -Djppf.config=jppf-clientDistributed.properties com.pb.mtc.ctramp.MtcTourBasedModel mtcTourBased -iteration %ITER% -sampleRate %SAMPLESHARE% -sampleSeed %SEED%
if ERRORLEVEL 2 goto done

:: Shut down java
C:\Windows\SysWOW64\taskkill /f /im "java.exe"

:: if we got here and didn't shutdown -- assume something went wrong
python "CTRAMP\scripts\notify_slack.py" "Finished running trace"

:donedone