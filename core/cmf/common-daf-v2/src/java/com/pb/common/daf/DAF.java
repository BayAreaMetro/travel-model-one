/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.daf;

import com.pb.common.util.ResourceUtil;

import java.io.File;
import java.util.ArrayList;
import java.util.ResourceBundle;
import java.util.Date;
import org.apache.log4j.Logger;

/** This class loads the DAF framework. Calling the getInstance() method
 *  will cause the dependent classes to be loaded.
 *
 * e.g. DAF.getInstance() will startup a node.
 *
 * @author    Tim Heier
 * @version   1.0, 8/19/2002
 */

public class DAF {

    protected static Logger logger = Logger.getLogger("com.pb.common.daf");

    protected static int adminServerPort;
    protected static String adminServerContentDir;
    
    protected static int connectionRetryTime;
    protected static int defaultQueueSize;

    protected static NodeDef thisNodeDef;
    protected static String nodeName;
    
    //Describes each node in the system - does not change in size
    protected static NodeDef[] nodeDefinitions;
    
    private static long timeToLive = Integer.MAX_VALUE;
    private static long receiveWaitTime = 5000;
    
    // file for nodes to write errors with connections
    protected static File connectionErrorFile; 
    
    // for TP+ matrix IO
    private static boolean use32BitMatrixIoServer = false; 
    
    private static DAF instance = new DAF();


    private DAF() {
        logger.info("Max memory="+ Runtime.getRuntime().maxMemory());
        logger.info("Total memory="+ Runtime.getRuntime().totalMemory());
        printMemoryUsage();
        readProperties();
    }


    //----------------------- Public Methods ----------------------------------
    //Used by application code
    //
    
    /** 
     * Returns an instance to the singleton.
     */
    public static DAF getInstance() {
        return instance;
    }


    public static void startNode() {
        logger.info("=====================================");
        logger.info("        " + nodeName + " is starting");
        logger.info("     " + new Date());        
        logger.info("=====================================");
        init();
    }

    
    public static void printMemoryUsage() {
        System.gc();
        logger.info("Free memory="+ Runtime.getRuntime().freeMemory());
    }
    
    
    //------------------ Convenience Methods ----------------------------------
    //Used in DAF package only
    //

    /** 
     * Return the names of the tasks running in the local node.
     */
    public static ArrayList getLocalTasks() {

        ArrayList localTaskList = new ArrayList();
        ArrayList appDefList = ApplicationManager.getInstance().getAppDefList();

        //Loop through the running applications
        for (int i=0; i < appDefList.size(); i++) {
                        
            TaskDef[] taskDefinitions = ((ApplicationDef)appDefList.get(i)).taskDefinitions;
            
            //Loop through the tasks in each application
            for (int j=0; j < taskDefinitions.length; j++) {
                
                //Compare the node name where the task is running to this node
                if (taskDefinitions[j].nodeName.equals( thisNodeDef.name )) {
                    localTaskList.add( taskDefinitions[j].name );
                }
            }
        }

        logger.debug("DAF.getLocalTasks, localTaskList="+localTaskList);

        return localTaskList;
    }


    /** 
     * Return a reference to the local node definition.
     */
    public static NodeDef getNodeDef() {
        return thisNodeDef;
    }


    /** 
     * Return a list of the remote nodes, i.e. omit the local node from list.
     */
    public static NodeDef[] getRemoteNodeDefinitions() {
        NodeDef[] remoteNodes = new NodeDef[nodeDefinitions.length - 1];

        for (int j=0, i=0; i < nodeDefinitions.length; i++) {

            if (! nodeDefinitions[i].name.equals( thisNodeDef.name ) ) {
                remoteNodes[j++] = nodeDefinitions[i];
            }
        }

        return remoteNodes;
    }


    /** 
     * Return a list of all nodes in cluster.
     */
    public static NodeDef[] getAllNodeDefinitions() {
        return nodeDefinitions;
    }


    /** 
     * Return a node definition, given a node name.
     */
    public static NodeDef getNodeDef( String nodeName ) {
        NodeDef aNode = null;
        
        //Loop over the list of nodes
        for (int i=0; i < nodeDefinitions.length; i++) {
            if (nodeDefinitions[i].name.equals( nodeName )) {
                aNode = nodeDefinitions[i];
                break;
            }
        }

        return aNode;
    }


    //----------------------- Private Methods ----------------------------------
    //Used internally by this class
    //

    /** 
     * Starts system level tasks
     */
    private static void startSystemTasks() {
    
//        TaskManager.runTask( new StartApplicationHandler() );
//        TaskManager.runTask( new StopApplicationHandler() );
//        
//        TaskManager.runTask(null, "StartApplicationHandler", 
//                "com.pb.commmon.daf.StartApplicationHandler", 
//                Constants.TOPIC_APPLICATION_START, false);
//        
//        TaskManager.runTask(null, "StopApplicationHandler", 
//                "com.pb.commmon.daf.StopApplicationHandler", 
//                Constants.TOPIC_APPLICATION_STOPT, false);
        
//        Task task = null;
//        try {
//            Class statClass = Class.forName("com.pb.tlumip.pc.tasks.StatListener");
//            task = (Task) statClass.newInstance();
//        }
//        catch (ClassNotFoundException e) {
//            e.printStackTrace();
//        }
//        catch (IllegalAccessException e) {
//            e.printStackTrace();
//        }
//        catch (InstantiationException e) {
//            e.printStackTrace();
//        }
//        TaskManager.runTask( task );
    }


    /** 
     * Load DAF by loading singleton classes.
     */
    private static void init() {
        QueueManager.getInstance();
        MessageFactory.getInstance();
        PortManager.getInstance();
        TCPTransport.getInstance();
    }


    private void readProperties() {
        logger.debug("DAF.readProperties...");
        
        ResourceBundle rb = null;
        
        //Look for a properties file named "daf" in classpath
        String propFileName = System.getProperty("propFile");
        if (propFileName == null) {
            propFileName = "daf";
            rb = ResourceUtil.getResourceBundle( propFileName );
        }
        //Read a property file from user-specified location
        else {
            rb = ResourceUtil.getPropertyBundle( new File(propFileName) );
        }

        //Read nodeName property, it must be set to continue
        nodeName = ResourceUtil.getProperty(rb, "nodeName");
        if ( (nodeName == null) || (nodeName.length() < 1) ) {
            logger.error("\"nodeName\" property not found. Set in properties file or on command-line");
            logger.error("eg. -DnodeName=<node-name>");
            System.exit(1);
        }

        //Admin Server properties
        adminServerPort = Integer.parseInt( ResourceUtil.getProperty(rb, "adminServerPort", "7000") );
        adminServerContentDir = ResourceUtil.getProperty(rb, "adminServerContentDir");
        String connectionErrorString = ResourceUtil.getProperty(rb, "connectionErrorFile", "c:/ConnectionErrorFile.txt");
        connectionErrorFile = new File(connectionErrorString); 
        
        //Read General properties
        connectionRetryTime = Integer.parseInt( ResourceUtil.getProperty(rb, "connectonRetryTime", "1000") );
        defaultQueueSize = Integer.parseInt( ResourceUtil.getProperty(rb, "defaultQueueSize", "1000") );
        timeToLive = Long.parseLong(ResourceUtil.getProperty(rb, "timeToLive"));
        receiveWaitTime = Long.parseLong(ResourceUtil.getProperty(rb, "receiveWaitTime"));
        
        //determine whether to use 32-bit matrix server
        use32BitMatrixIoServer = ResourceUtil.getBooleanProperty(rb, "use32BitMatrixIoServer", false);
        
        //Log the values
        logger.info("nodeName=" + nodeName);
        logger.info("adminServerPort=" + adminServerPort);
        logger.info("adminServerContentDir=" + adminServerPort);
        logger.info("connectionErrorFile=" + connectionErrorFile); 
        logger.info("connectionRetryTime=" + connectionRetryTime);
        logger.info("defaultQueueSize=" + defaultQueueSize);
        logger.info("timeToLive=" + timeToLive);
        logger.info("receiveWaitTime=" + receiveWaitTime);
        logger.info("use32BitMatrixIoServer=" + use32BitMatrixIoServer); 
        
        readNodeDefinitions( rb );

        for (int i=0; i < nodeDefinitions.length; i++) {
            logger.info(nodeDefinitions[i].toString() );
        }
    
    }


    /** 
     * Read the definition for each node.
     */
    private void readNodeDefinitions(ResourceBundle rb) {

        String thisNodeName = ResourceUtil.getProperty( rb, "nodeName" );

        if (thisNodeName == null) {
            logger.error("daf.nodeName is not set, exiting...");
            System.exit(1);
        }

        ArrayList nodeNames  = ResourceUtil.getList (rb, "nodeList");
        nodeDefinitions = new NodeDef[ nodeNames.size() ];

        //Read properties for each node 
        for (int i=0; i < nodeNames.size(); i++) {
            String nodeName = (String) nodeNames.get(i);
            String addressKey = nodeName + ".address";
            String messagePortKey = nodeName + ".messagePort";
            String adminPortKey = nodeName + ".adminPort";
            
            String address = ResourceUtil.getProperty( rb, addressKey );
            int messagePort = Integer.parseInt( ResourceUtil.getProperty( rb, messagePortKey ) );
            int adminPort = Integer.parseInt( ResourceUtil.getProperty( rb, adminPortKey ) );
            
            nodeDefinitions[i] = new NodeDef( nodeName, address, messagePort, adminPort );

            //Remember the current node for convenience
            if (nodeName.equals( thisNodeName ) ) {
                thisNodeDef = nodeDefinitions[i];
            }
        }

    }


    /** 
     * Adds a task name to the list of tasks for this node. If it exists then
     * no action is taken.
     */
/*
    private synchronized static void addTaskName(String taskName) {

        //Check if this task is listed in local node properties
        ArrayList localTasks = DAF.getLocalTasks();

        boolean onList = false;
        for (int i=0; i < localTasks.size(); i++) {
            if ( taskName.equals( (String)localTasks.get(i)) ) {
                onList = true;
            }
        }
        if (! onList) {
            nodeProperties[thisNodeIndex].taskList.add("taskName");
        }
    }
*/

    /** 
     * Load DAF from command-line, start tasks in properties file.
     */
    public static void main (String[] args) {
        DAF.getInstance();
    }

    
    /**
     * @return receiveWaitTime.
     */
    public static long getReceiveWaitTime() {
        return receiveWaitTime;
    }

    
    /**
     * @return timeToLive.
     */
    public static long getTimeToLive() {
        return timeToLive;
    }

    
    /**
     * @return nodeName.
     */
    public static String getNodeName() {
        return nodeName;
    }

    /**
     * 
     * @return node names for all nodes in the cluster.
     */
    public static String[] getNodeNames() {
        String[] nodeNames = new String[nodeDefinitions.length];
        
        for (int j=0, i=0; i < nodeDefinitions.length; i++) {
            nodeNames[i] = nodeDefinitions[i].name;    
        }
        return nodeNames;
    }

    
    /**
     * @return Returns the defaultQueueSize.
     */
    public static int getDefaultQueueSize() {
        return defaultQueueSize;
    }

    /**
     * @return Returns the adminServerPort.
     */
    public static int getAdminServerPort() {
        return adminServerPort;
    }

    /**
     * @return Returns the adminServerContentDir.
     */
    public static String getAdminServerContentDir() {
        return adminServerContentDir;
    }
    
    /**
     * @return whether or not to open a 32-bit matrix IO server for TP+ IO
     */
    public static boolean getUse32BitMatrixIoServer() {
    	return use32BitMatrixIoServer; 
    }

}