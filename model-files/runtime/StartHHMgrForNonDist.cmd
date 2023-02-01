cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
:: Set the path
call CTRAMP\runtime\SetPath.bat

rem ############  PARAMETERS  ############
set RUNTIME=.
set JAVA_PATH=C:/Progra~1/Java/jdk1.8.0_162
set HOST_IP= localhost


start java -Xmx20g -Xmx30g -Dlog4j.configuration=log4j_hh.xml com.pb.mtc.ctramp.MtcHouseholdDataManager -hostname localhost
