cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
set JAVA_PATH=C:\Program Files\Java\jdk1.6.0_16
set JAVA_PATH_32=C:\Program Files (x86)\Java\jre7
set GAWK_PATH=M:\UTIL\Gawk
set TPP_PATH=C:\Program Files (x86)\Citilabs\CubeVoyager

set RUNTIME=CTRAMP/runtime
set OLD_PATH=%PATH%
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin;%OLD_PATH%
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar
::set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-1.8/jppf-1.8-gui/lib/*;%RUNTIME%/mtc.jar

set HOST_IP=192.168.1.200

rem ############  JPPF DRIVER  ############

start java -server -Xmx16m -Dlog4j.configuration=log4j-driver.properties -Djppf.config=jppf-driver.properties org.jppf.server.DriverLauncher

rem ############  HH MANAGER  ############
start java -Xms20000m -Xmx20000m -Dlog4j.configuration=log4j_hh.xml com.pb.mtc.ctramp.MtcHouseholdDataManager -hostname %HOST_IP%

rem ############  Matrix MANAGER #########
start java -Xms14000m -Xmx14000m -Dlog4j.configuration=log4j_mtx.xml -DJAVA_32_LOG4J=log4j_mtx_32.xml -DJAVA_HOME_32="%JAVA_PATH_32%" -DJAVA_32_PORT=1181 -Djava.library.path="%RUNTIME%" com.pb.models.ctramp.MatrixDataServer -hostname %HOST_IP%

set PATH=%OLD_PATH%