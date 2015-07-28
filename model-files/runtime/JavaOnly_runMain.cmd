cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
set JAVA_PATH=C:\Program Files\Java\jdk1.7.0_71
set GAWK_PATH=M:\UTIL\Gawk
set TPP_PATH=C:\Program Files (x86)\Citilabs\CubeVoyager;C:\Program Files\Citilabs\VoyagerFileAPI

set RUNTIME=CTRAMP/runtime
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar

set HOST_IP=set_by_RuntimeConfiguration.py

rem ############  JPPF DRIVER  ############
start "JPPF Server" java -server -Xmx16m -Dlog4j.configuration=log4j-driver.properties -Djppf.config=jppf-driver.properties org.jppf.server.DriverLauncher

rem ############  HH MANAGER  ############
start "Household Manager" java -Xms20000m -Xmx20000m -Dlog4j.configuration=log4j_hh.xml com.pb.mtc.ctramp.MtcHouseholdDataManager -hostname %HOST_IP%

rem ############  Matrix MANAGER #########
start "Matrix Manager" java -Xms14000m -Xmx14000m -Dlog4j.configuration=log4j_mtx.xml -Djava.library.path="CTRAMP/runtime" com.pb.models.ctramp.MatrixDataServer -hostname %HOST_IP%

