cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
:: Set the path
call CTRAMP\runtime\SetPath.bat

set HOST_IP=set_by_RuntimeConfiguration.py

rem ############  JPPF DRIVER  ############
start "JPPF Server" java -server -Xmx16m -Dlog4j.configuration=log4j-driver.properties -Djppf.config=jppf-driver.properties org.jppf.server.DriverLauncher

rem ############  HH MANAGER  ############
start "Household Manager" java -Xms20000m -Xmx20000m -Dlog4j.configuration=log4j_hh.xml com.pb.mtc.ctramp.MtcHouseholdDataManager -hostname %HOST_IP%

rem ############  Matrix MANAGER #########
start "Matrix Manager" java -Xms14000m -Xmx14000m -Dlog4j.configuration=log4j_mtx.xml -Djava.library.path="CTRAMP/runtime" com.pb.models.ctramp.MatrixDataServer -hostname %HOST_IP%
