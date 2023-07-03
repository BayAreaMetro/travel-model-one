cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
:: Set the path
call CTRAMP\runtime\SetPath.bat

echo Started: %date% %time%
start java -Xmx20g -Xmx30g -Dlog4j.configuration=log4j_hh.xml com.pb.mtc.ctramp.MtcHouseholdDataManager -hostname localhost
timeout /t 8
echo Waited: %date% %time%