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
package com.pb.common.daf.admin;

import com.pb.common.daf.ApplicationDef;
import com.pb.common.daf.ApplicationManager;
import com.pb.common.daf.DAF;
import com.pb.common.daf.NodeDef;
import com.pb.common.util.CommandLine;
import com.pb.common.util.Convert;
import org.apache.log4j.Logger;

import java.io.BufferedWriter;
import java.io.OutputStreamWriter;
import java.net.Socket;
import java.util.HashMap;

/** 
 * Processes administrative commands.
 *
 * http://localhost:7000/daf?command=startcluster
 * http://localhost:7000/daf?command=startapplication&name=testapp
 * http://localhost:7000/daf?command=stopapplication&name=testapp
 *
 * @author    Tim Heier
 * @version   1.0, 1/23/2004
 */
public class CommandProcessor {

    private Logger logger = Logger.getLogger("com.pb.common.daf.admin");
    
    public static String START_CLUSTER = "startcluster";
    public static String START_APPLICATION = "startapplication";
    public static String STOP_APPLICATION = "stopapplication";
    public static String LIST_APPLICATIONS = "listapplications";
    public static String STOP_NODE = "stopnode"; 
    public static String NAME= "name";
        
    private HashMap paramMap;
    
    
    private CommandProcessor() {
        
    }
    
    
    public CommandProcessor(HashMap paramMap) {
        this.paramMap = paramMap;
    }
    
    
    public void processCommand() {
        String command = (String) paramMap.get("command");
        
        if (command == null)
            throw new RuntimeException("command is null");
        
        logger.debug("processCommand, command=" +command);
        
        if (command.equalsIgnoreCase(START_CLUSTER)) {
            startCluster();
        }
        else
        if (command.equalsIgnoreCase(START_APPLICATION)) {
            startApplication();
        }
        else 
        if (command.equalsIgnoreCase(STOP_APPLICATION)) {
            stopApplication();
        }
        else 
        if (command.equalsIgnoreCase(STOP_NODE)) {
            stopNode();
        }
    }

    
    private void startCluster() {
        String[] strArray = { START_CLUSTER };
        sendMessage(strArray);
    }
    
    
    //1. Read application file and create an object
    //2. Serialize object to a byte array
    //3. Encode byte array to a base64 string
    //4. Send message to each node in cluster
    private void startApplication() {
        String name = (String) paramMap.get(NAME);
        
        ApplicationManager appManager = ApplicationManager.getInstance();
        ApplicationDef appDef = null;
        try {
            appDef = appManager.readApplicationDef(name);
        } catch (Exception e) {
            System.out.println("Error reading ApplicationDef for " + name);
            e.printStackTrace();
            return;
        }
        String appDefAsString = Convert.toString(appDef);
        
        String[] strArray = { START_APPLICATION, appDefAsString};
        sendMessage(strArray);
    }


    /**
     * Similar to startApplication() method.
     *
     */
    private void stopApplication() {
        String name = (String) paramMap.get(NAME);
        
        ApplicationManager appManager = ApplicationManager.getInstance();
        ApplicationDef appDef = null;
        try {
            appDef = appManager.readApplicationDef(name);
        } catch (Exception e) {
            System.out.println("Error reading ApplicationDef for " + name);
            e.printStackTrace();
            return;
        }
        String appDefAsString = Convert.toString(appDef);
        
        String[] strArray = { STOP_APPLICATION, appDefAsString};
        sendMessage(strArray);
    }
    

    private void stopNode() {
        String[] strArray = { STOP_NODE };
        sendMessage(strArray);
    }
    
    /**
     * Lists applications running in each node.
     *
     */
    private void listApplications() {
        String[] strArray = { LIST_APPLICATIONS };
        sendMessage(strArray);
    }
    
    
    /**
     * Send a message to every node in the cluster.
     * 
     * @param strArray
     */
    private void sendMessage(String[] strArray) {
        NodeDef[] nodeDef = DAF.getAllNodeDefinitions();

        //Loop through all the nodes in the cluster
        for (int i=0; i < nodeDef.length; i++) {
            String address = nodeDef[i].getAddress();
            int port = nodeDef[i].getAdminPort();
            
            logger.info("Command Processor sendMessage [" + nodeDef[i].getName() + "] = " + address + ":" + port);

            //Create a socket without a timeout
            try {
                // This constructor will block until the connection succeeds
                Socket socket = new Socket(address, port);
                logger.info("CommandProcessor got a connection to " + address + ":" + port);

                BufferedWriter wr = 
                    new BufferedWriter(new OutputStreamWriter(socket.getOutputStream()));
                logger.info("CommandProcessor created a BufferedWriter on " + address + ":" + port);
                
                for (int j=0; j < strArray.length; j++) {
                    wr.write(strArray[j]);
                    wr.newLine();
                }
                wr.flush();
                wr.close();
                
            } catch (Exception e) {
                logger.error("CommandProcessor threw an exception", e);
            }
        }
    }
    
    
    /**
     * Print out information on running this sevice
     */
    private static void usage() {
        System.out.println("\n"+
                "usage: java " + CommandProcessor.class.getName() + " <arguments> [options]\n" +
                "\n" +
                "arguments:\n" +
                "  -propFile <file>               location of daf properties file\n" +
                "\n" +
                "options:\n" +
                "  -startCluster                  start a cluster based on daf.properties file\n" +
                "  -startApplication <name>       start an application\n" +
                "  -stopApplication <name>        stop an application\n" +
                "  -listApplications              list of running applications\n" +
                "  -tasks                         list of running tasks\n" +
                "  -queues                        list queues\n" +
                "  -queue=<queue>                 number of messages on queue\n" +
                "  -help                          displays this help.\n" +
                "\n" +
                "sample: " + CommandProcessor.class.getName() + "-start-application=testapp");
    }
    
    
    public static void main(String[] args) {

        CommandLine cmdline = new CommandLine(args);
        String propFile = cmdline.value("propFile");

//        if (propFile == null || cmdline.exists("help")) {
//            usage();
//        }
//        String previousValue = System.setProperty("propFile", propFile);
        String previousValue = System.setProperty("nodeName", "adminNode");
        DAF.getInstance();
        
        HashMap paramMap = new HashMap();
        
        if (cmdline.exists("startCluster")) {
            paramMap.put("command", START_CLUSTER);
        } 
        else if (cmdline.exists("startApplication")) {
            paramMap.put("command", START_APPLICATION);
            paramMap.put("name", cmdline.value("startApplication"));
        } 
        else if (cmdline.exists("stopApplication")) {
            paramMap.put("command", STOP_APPLICATION);
            paramMap.put("name", cmdline.value("stopApplication"));
//        } else if (cmdline.exists("queue")) {
//            queueCount(url, cmdline.value("queue"));
//        } else if (cmdline.exists("topic") && (cmdline.exists("name"))) {
//            topicCount(url, cmdline.value("topic"), cmdline.value("name"));
//        } else if (cmdline.exists("remove")) {
//            remove(url, cmdline.value("name"));
//        } else if (cmdline.exists("exists")) {
//            destinationExists(url, cmdline.value("exists"));
        } else {
            usage();
            System.exit(1);
        }

        CommandProcessor cp = new CommandProcessor(paramMap);
        cp.processCommand();
    }
    
    
}
