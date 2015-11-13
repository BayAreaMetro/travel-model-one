cd ..
cd ..
mkdir logs

rem ############  PARAMETERS  ############
:: Set the path
call CTRAMP\runtime\SetPath.bat

set HOST_IP=set_by_RuntimeConfiguration.py

rem ############  JPPF DRIVER  ############
start "Node 3" java -server -Xmx128m -Dlog4j.configuration=log4j-node3.xml -Djppf.config=jppf-node3.properties org.jppf.node.NodeLauncher
