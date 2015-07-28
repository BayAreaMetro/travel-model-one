cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
set JAVA_PATH=C:\Program Files\Java\jdk1.7.0_71
set GAWK_PATH=M:\UTIL\Gawk
set TPP_PATH=C:\Program Files (x86)\Citilabs\CubeVoyager

set RUNTIME=CTRAMP/runtime
set PATH=%RUNTIME%;%JAVA_PATH%/bin;%TPP_PATH%;%GAWK_PATH%/bin
set CLASSPATH=%RUNTIME%/config;%RUNTIME%;%RUNTIME%/config/jppf-2.4/jppf-2.4-admin-ui/lib/*;%RUNTIME%/mtc.jar

set HOST_IP=set_by_RuntimeConfiguration.py

rem ############  JPPF DRIVER  ############
start "Node 2" java -server -Xmx128m -Dlog4j.configuration=log4j-node2.xml -Djppf.config=jppf-node2.properties org.jppf.node.NodeLauncher
