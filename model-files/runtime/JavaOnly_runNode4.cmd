cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
:: Set the path
call CTRAMP\runtime\SetPath.bat

set HOST_IP=set_by_RuntimeConfiguration.py

rem ############  JPPF DRIVER  ############
start "Node 4" java -server -Xmx128m -Dlog4j.configuration=log4j-node4.xml -Djppf.config=jppf-node4.properties org.jppf.node.NodeLauncher
