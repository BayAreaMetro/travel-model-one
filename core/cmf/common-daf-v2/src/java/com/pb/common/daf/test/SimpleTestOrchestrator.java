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
package com.pb.common.daf.test;

import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.FileWriter;

/**
 * SimpleTestOrchestrator is a class that ...
 *
 * @author Kimberly Grommes
 * @version 1.0, Jan 3, 2008
 *          Created by IntelliJ IDEA.
 */
public class SimpleTestOrchestrator {
    static Logger logger = Logger.getLogger(SimpleTestOrchestrator.class);
    File commandFile;
    File appDone;
    String appName;
    String nodeName;

    private long startNodeSleepTime = 10000;
    private long startClusterApplicationSleepTime = 20000;
    private long fileCheckSleepTime = 55;

    public static String START_NODE = "StartNode";
    public static String START_CLUSTER = "StartCluster";
    public static String START_APPLICATION = "StartApplication";
    public static String STOP_NODE = "StopNode";

    public static void main(String[] args) {

        try {

            SimpleTestOrchestrator to = new SimpleTestOrchestrator();
            to.appName = args[0];
            to.nodeName = args[1];
            logger.info("Node to Start Cluster: "+ to.nodeName);

            to.run();

            logger.info(to.appName + " is complete");

        } catch (Exception e) {
            logger.fatal("An application threw the following error");
            throw new RuntimeException("An application threw the following error", e);
        }
    }




    public void run(){
        //get the path to the command file and make sure the file exists
        String rootDir = "/osmp_gui/java_files/daf";
        logger.info("CommandFile Path: "+ rootDir);
        commandFile = getCommandFile(rootDir);

        //construct the path to the $appName_done.txt file
        //and delete the file if it already exists
        String doneFile = rootDir + "/" +  appName + "_done.txt";
        logger.info("DoneFile Path: " + doneFile);
        appDone = new File(doneFile);
        deleteAppDoneFile();

        //begin the daf application by writing the correct
        //commands to the command file
        logger.info("Starting nodes, cluster and application.  Waiting " + startNodeSleepTime + " ms for nodes to start");
        writeCommands();

        logger.info("Ending application");
        //end daf application by writing 'StopNode' into the command file
        cleanUpAndExit();

    }

    private File getCommandFile(String cmdFilePath){
        File cmdFile = new File(cmdFilePath+"/commandFile.txt");
        if(!cmdFile.exists()){
            logger.info("The file used by the FileMonitor class does not exist - creating file");
            try {
                cmdFile.createNewFile();
            } catch (IOException e) {
                logger.fatal(cmdFile.getAbsolutePath() + " could not be created");
                e.printStackTrace();
                System.exit(10);
            }
        }
        logger.info("Command file has been found");
        return cmdFile;
    }

    private void deleteAppDoneFile(){
        if(appDone.exists()){
            logger.info("Deleting the "+appName+"_done.txt file");
            appDone.delete();

            if(appDone.exists()) logger.info(appDone.getAbsolutePath() + " file still exists.");
        }
    }

    private void writeCommands(){
        writeCommandToCmdFile(START_NODE);
        try {
            Thread.sleep(startNodeSleepTime);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        writeCommandToCmdFile(START_CLUSTER);
        try {
            Thread.sleep(startClusterApplicationSleepTime);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        writeCommandToCmdFile(START_APPLICATION);

        logger.info("Wait here for the application to finish");
        long waitTime = System.currentTimeMillis();
        waitForAppDoneOrErrorCondition();
        logger.info("Application has finished. Time in seconds: "+(System.currentTimeMillis()-waitTime)/1000.0);
    }



    private void writeCommandToCmdFile(String entry){
        logger.info("Writing '"+ entry + "' to command file");
        PrintWriter writer;
        try {
            writer = new PrintWriter(new FileWriter(commandFile));

            if(entry.equals(START_CLUSTER)){
                writer.println(START_CLUSTER);
                writer.println(nodeName);

            }else if(entry.equals(START_APPLICATION)){
                writer.println(START_APPLICATION);
                writer.println(nodeName);
                writer.println(appName.toLowerCase());

            }else{
                writer.println(entry); //all other commands have just a single entry with no arguments
            }

            writer.close();

        } catch (IOException e) {
            logger.fatal("Could not open command file or was not able to write to it - check file properties");
            e.printStackTrace();
        }

    }

    private void waitForAppDoneOrErrorCondition(){
        boolean stopRequested = false;

        while(! stopRequested) {
            try {
                Thread.sleep(fileCheckSleepTime);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }

            //Check that the file exists
            if (appDone.exists()) {
                stopRequested=true;
            }
        }
    }

    private void cleanUpAndExit(){
        writeCommandToCmdFile(STOP_NODE);
        try {
            Thread.sleep(startNodeSleepTime);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }


}
