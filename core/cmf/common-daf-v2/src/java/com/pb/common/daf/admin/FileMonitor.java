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

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;

/**
 * 
 * @author Tim
 *
 */
public class FileMonitor implements Runnable {

    private File fileToMonitor;
    private File nodePropsFile;
    
    private Thread internalThread;
    private volatile boolean stopRequested;
    
    private CommandRunner runner = null;
    private String nodeName;  //populate when StartNode command is run
    
    
    public FileMonitor(File fileToMonitor, File nodePropsFile) {
        this.fileToMonitor = fileToMonitor;
        this.nodePropsFile = nodePropsFile;
        
        //Do this before trying to start
        readPropsFile();
        
        stopRequested = false;
        internalThread = new Thread(this);
        internalThread.setDaemon(false);
        internalThread.start();
    }
    
    public void readPropsFile() {

        //Check for existance of startnode.properties
        if (! nodePropsFile.exists()) {
            System.out.println(nodePropsFile.getAbsolutePath() + ", does not exist");
            System.exit(2);
        }

////      Look for a properties file named "daf" in classpath
//        ResourceBundle dafPropsBundle = null;
//        String propFileName = System.getProperty("propFile");
//        if (propFileName == null) {
//            propFileName = "daf";
//            dafPropsBundle = ResourceUtil.getResourceBundle( propFileName );
//        }
//        //Read a property file from user-specified location
//        else {
//        	dafPropsBundle = ResourceUtil.getPropertyBundle( new File(propFileName) );
//        }
    }    
    
    
    public void run() {
        if (Thread.currentThread() != internalThread) {
            throw new RuntimeException("only the internal thread is allowed " +
                    "to invoke run()");
        }

        System.out.println("**Monitoring file: " + fileToMonitor.getAbsoluteFile());

        long startTime;
        //System.out.println("Outside 'while' loop, file has not been read");
        if(!fileToMonitor.exists()){
            startTime = fileToMonitor.lastModified();
            //System.out.println("\tFile does not exist.  Start time = " + startTime);
        }else{
            startTime = fileToMonitor.lastModified();
            //System.out.println("\tFile exists.  Start time = " + startTime);
        }

        //Bogus... try opening the file to refresh the file attributes
        try {
            FileReader reader = new FileReader(fileToMonitor);
            reader.ready();  //do this so compiler doesn't optimize code away
            reader.close();
        } catch (IOException e) {
            //System.out.println("Outside 'while' loop, exception was thrown and caught. ");
        }

        //System.out.print("Outside 'while' loop, file HAS been read.  ");
        if(!fileToMonitor.exists()){
            startTime = fileToMonitor.lastModified();
            //System.out.println("File does NOT exist.  Start time = " + startTime);
        }else{
            startTime = fileToMonitor.lastModified();
            //System.out.println("File EXISTS.  Start time = " + startTime);
        }

        while(! stopRequested) {
            try {
                Thread.sleep(2000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }

            //Bogus... try opening the file to refresh the file attributes
            try {
                FileReader reader = new FileReader(fileToMonitor);
                reader.ready();  //do this so compiler doesn't optimize code away
                reader.close();
                //System.out.print("Inside 'while' loop, file HAS been read.  ");
            } catch (IOException e) {
                //do nothing
            }

            long currentTime;
            if(!fileToMonitor.exists()){
                currentTime = fileToMonitor.lastModified();
                //System.out.println("File does NOT exist.  Current time = " + currentTime);
            }else{
                currentTime = fileToMonitor.lastModified();
                //System.out.println("File EXISTS.  Current time = " + currentTime);
            }

            long diffTime = (currentTime - startTime);

            //If file has been modified then read file
            if (diffTime != 0) {
                startTime = currentTime;
                readFile();
            }
        }
        System.out.println("**Stopping monitor");
    }
    
    protected void readFile() {
        try {
            BufferedReader in = new BufferedReader(new FileReader(fileToMonitor));
            ArrayList commands = new ArrayList();
            String str;
            while ((str = in.readLine()) != null) {
                commands.add(str);
            }
            in.close();

            //in rare cases, the file monitor detects a change to the file
            //but the file is empty (not sure exactly how this happens, but
            //it does happen) and so the node should just re-read the file
            //This potentially could set up an infinite loop.  The file
            //monitor is hopefully going away so this is a "hacky" fix
            //for the moment.
            if(commands.size() == 0){
                readFile();
                return;
            }

            processValues(commands);

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    protected void processValues(ArrayList commands) {
        
        //Echo arguements back
        System.out.println("**Commands");
        for(int i=0; i < commands.size(); i++) {
            System.out.println((String)commands.get(i));
        }
        System.out.println("**");

        if (commands.size() == 0) {
            //sometimes this happens again, for some reason
            readFile();
            return;
        }
        String command = (String) commands.get(0);
        if (command.equalsIgnoreCase("StartNode")) {
            startNode();
        }
        if (command.equalsIgnoreCase("StartCluster")) {
            startCluster(commands);
        }
        if (command.equalsIgnoreCase("StartApplication")) {
            startApplication(commands);
        }
        if (command.equalsIgnoreCase("StopNode")) {
            stopNode();
        }
        if (command.equalsIgnoreCase("StopMonitor")) {
            stopRequested = true;
        }
    }

    protected void startNode() {

        //Check and see if it's running first
        if (runner != null) {
            System.out.println("**ERROR: Node is already running"); 
            return;
        }

        //Read values from startnode.properties file first
        ArrayList items = new ArrayList();
        BufferedReader in;
        try {
            in = new BufferedReader(new FileReader(nodePropsFile));
            String line;
            while ((line = in.readLine()) != null) {
                //Pull out the nodeName when the node is started - used in StartCluster
                int start = line.indexOf("nodeName=");
                if (start > 0) {
                    this.nodeName = line.substring(11); 
                }
                items.add(line);
            }
            in.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        System.out.println("**Monitor assigned to nodeName: " + nodeName);

        //Convert to an array
        int size = items.size();
        String[] args = new String[size];
        for (int i=0; i < items.size(); i++) {
            args[i] = (String) items.get(i);
        }
        
        CommandLauncher launcher = new CommandLauncher(new File("stdout.text"));
        runner = new CommandRunner(launcher, args);
    }

    protected void stopNode() {
    	
    	// do nothing if not running
    	if (runner != null) {
    		runner.killProcess();
    	}
        runner = null;
    }

    //Will send the "startcluster" message to all of the nodes in the cluster as
    //defined in the daf.properties in the classpath of this class
    protected void startCluster(ArrayList commands) {

        //Make sure node is running
        if (runner == null) {
            System.out.println("**ERROR: Node is not running");
            return;
        }

        if (commands.size() < 2) {
            System.out.println("**ERROR: An arguement is missing from in the commandfile");
            return;
        }
        //Run the StartCluster command from one of the FileMonitor processes. Do
        //it from the one specified in the commandfile
        String nodeName = (String) commands.get(1);
        if (this.nodeName.equalsIgnoreCase(nodeName)) {
            System.out.println("**Running StartCluster command from monitor on node: " + nodeName);

            //Set nodeName so DAF does not complain
            System.setProperty("nodeName", "monitorNode");

            HashMap paramMap = new HashMap();
            paramMap.put("command", CommandProcessor.START_CLUSTER);

            CommandProcessor cp = new CommandProcessor(paramMap);
            cp.processCommand();
        }
    }

    protected void startApplication(ArrayList commands) {
        if (runner == null) {
            System.out.println("**ERROR: Node is not running");
            return;
        }

        if (commands.size() < 3) {
            System.out.println("**ERROR: An arguement is missing from the commandfile");
            return;
        }
        String nodeName = (String) commands.get(1);
        String applicationName = (String) commands.get(2);
        //Run the StartApplication command from one of the FileMonitor processes. Do
        //it from the one specified in the commandfile
        if (this.nodeName.equalsIgnoreCase(nodeName)) {
            System.out.println("**Running StartApplication command from monitor on node: " + nodeName);
        
            //Set nodeName so DAF does not complain
            System.setProperty("nodeName", "monitorNode");
    
            HashMap paramMap = new HashMap();
            paramMap.put("command", CommandProcessor.START_APPLICATION);
            paramMap.put("name", applicationName);
    
            CommandProcessor cp = new CommandProcessor(paramMap);
            cp.processCommand();
        }
    }

    public static void main(String[] args) {
    
        if (args.length < 2) {
            System.out.println("");
            System.out.println("USAGE: java com.pb.common.daf.admin.FileMonitor  <fileToMonitor>  <startnode.properties>");
            System.out.println("");
            System.out.println("Additionally, the startnode properties file which defines the java command");
            System.out.println("that the node will run");
            System.out.println("");
            System.exit(1);
        }
        
        File fileToMonitor = new File(args[0]);
        File nodePropsFile = new File(args[1]);
        
        FileMonitor fm = new FileMonitor(fileToMonitor, nodePropsFile);
    }
    
}
