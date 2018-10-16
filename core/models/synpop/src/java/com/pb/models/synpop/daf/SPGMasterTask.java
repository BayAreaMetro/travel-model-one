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
package com.pb.models.synpop.daf;

import com.pb.common.daf.*;
import com.pb.common.util.BooleanLock;
import com.pb.common.util.ResourceUtil;
import com.pb.models.synpop.SPG;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Date;
import java.util.HashMap;
import java.util.ResourceBundle;

/**
 * SPGMasterTask is a class that runs the SPG2 process
 * in DAF mode.
 *
 * @author Christi Willison
 * @version 1.0,  May 14, 2009
 */
public class SPGMasterTask extends Task {

    protected static BooleanLock signal = new BooleanLock(false);

    Logger logger = Logger.getLogger(SPGMasterTask.class);
    ResourceBundle spgRb = null;
    ResourceBundle spg2dafRb = null;

    private SPG spg;
    private int baseYear;
    private int timeInterval;
    private MessageFactory mFactory;
    private Port[] hhWorkPorts;
    private Port resultProcessorPort;
    private int nWorkQueues;


    public SPGMasterTask() {
        super();
    }

    public void onStart(){
        long startTime = createSPG2Object();
        logger.info("Setup is complete. Time in seconds: "+((System.currentTimeMillis()-startTime)/1000));

        logger.info("*******************************************************************************************");
        logger.info("*   Beginning SPG2");
        logger.info("*******************************************************************************************");
    }

    private long createSPG2Object() {
        logger.info( "***" + getName() + " started");
        logger.info("Creating a Project specific SPG object");
        long startTime = System.currentTimeMillis();

        logger.info("Reading RunParams.properties file");
        ResourceBundle runParamsRb = ResourceUtil.getResourceBundle("RunParams");
        timeInterval = Integer.parseInt(ResourceUtil.getProperty(runParamsRb,"timeInterval"));
        logger.info("\tTime Interval: " + timeInterval);
        baseYear = ResourceUtil.getIntegerProperty(runParamsRb,"baseYear",1990);
        logger.info("\tBase Year: " + baseYear);
        String pathToSpgRb = ResourceUtil.getProperty(runParamsRb,"pathToAppRb");
        logger.info("\tResourceBundle Path: " + pathToSpgRb);
        String pathToGlobalRb = ResourceUtil.getProperty(runParamsRb,"pathToGlobalRb");
        logger.info("\tResourceBundle Path: " + pathToGlobalRb);

        spg2dafRb = ResourceUtil.getResourceBundle("spg2daf");
        spgRb = ResourceUtil.getPropertyBundle(new File(pathToSpgRb));
        ResourceBundle globalRb = ResourceUtil.getPropertyBundle(new File(pathToGlobalRb));

        HashMap spgPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap( spgRb );
        HashMap globalPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap(globalRb);

        String spgClassName = (String) spgPropertyMap.get("SPGNew.class");
        logger.info("SPG will be using the " + spgClassName + " for the SPG2 algorithm");

        Class spgClass = null;
        spg = null;
        try {
            spgClass = Class.forName(spgClassName);
            spg = (SPG) spgClass.newInstance();
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        } catch (InstantiationException e) {
            logger.fatal("Can't create new instance of SPGNew of type "+spgClass.getName());
            e.printStackTrace();
            throw new RuntimeException(e);
        } catch (IllegalAccessException e) {
            logger.fatal("Can't create new instance of SPGNew of type "+spgClass.getName());
            e.printStackTrace();
            throw new RuntimeException(e);
        }

        spg.spgNewInit( spgPropertyMap, globalPropertyMap,
                Integer.toString(baseYear), Integer.toString(baseYear + timeInterval) );
        return startTime;
    }

    public void doWork(){
        long runtime = System.currentTimeMillis();

        nWorkQueues = setUpQueues();

        //initialize the SPG object
        logger.info("MasterTask: Starting SPG2 for " + Integer.toString(baseYear + timeInterval));
        logger.info("MasterTask: Reading files necessary for spg2");
        spg.setupSpg2();

        logger.info("MasterTask: Sending HH Array Size to the ResultsQueue");
        long waitTime2 = System.currentTimeMillis();
        sendHHArraySizeMsg();
        waitForGoOnSignal();
        logger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime2)/1000.0 + " secs for " +
                        "the hh array size message to be processed");

        logger.info("MasterTask: Calculating Regional Dollars Per Job");
        spg.getRegionalDollarsPerJob();

        logger.info("MasterTask: Sending HH work to work queues");
        waitTime2 = System.currentTimeMillis();
        sendHHWorkToWorkQueues();
        waitForGoOnSignal();
        logger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime2)/1000.0 + " secs for " +
                        "workers to assign a TAZ to all households");
        spg.getRegionalDollarsPerJob();

        logger.info("MasterTask: Sending write output file message to results queue");
        waitTime2 = System.currentTimeMillis();
        sendWriteSPG2OutputFileMessage();
        waitForGoOnSignal();
        logger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime2)/1000.0 + " secs for " +
                        "results queue to write output file.");

        logger.info("MasterTask: Sending HH summary request to work queues");
        waitTime2 = System.currentTimeMillis();
        sendHHSummaryRequestToWorkQueues();
        waitForGoOnSignal();
        logger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime2)/1000.0 + " secs for " +
                        "hh summary files to be processed");

        logger.info("MasterTask: Writing HH Output Attributes From PUMS to disk");
        spg.writeHHOutputAttributesFromPUMS(Integer.toString(baseYear));

        writeDoneFile();
        logger.info("SPG2 IS FINISHED. Runtime: "+  (System.currentTimeMillis()-runtime)/1000.0);
    }

    private void sendHHArraySizeMsg() {
        Message msg = mFactory.createMessage();
        msg.setId(MESSAGE_IDS.RP_ASSIGNER_HH_ARRAY_SIZE_ID);
        msg.setValue(MESSAGE_IDS.RP_ARRAY_SIZE, spg.getHhArraySize());
        resultProcessorPort.send(msg);

    }

    private void sendHHWorkToWorkQueues() {

        String[] incSizeLabels = spg.incSize.getIncomeSizeLabels();
        Message[] msgs = new Message[spg.numIncomeSizes];

        for (int i = 0; i < spg.numIncomeSizes; i++) {
            Message msg = mFactory.createMessage();
            msg.setId(MESSAGE_IDS.HA_WORK_MESSAGE_ID);
            msg.setValue(MESSAGE_IDS.CATEGORY, i);
            msg.setValue(MESSAGE_IDS.CATEGORY_LABEL, incSizeLabels[i]);
            msg.setValue(MESSAGE_IDS.REGION_DOLLARS, spg.regionLaborDollarsPerJob);
            msgs[i] = msg;
        }

        sendWorkToWorkQueues(msgs, hhWorkPorts, nWorkQueues);
    }

    private void sendWriteSPG2OutputFileMessage() {
        Message msg = mFactory.createMessage();
        msg.setId(MESSAGE_IDS.RP_WRITE_SPG2_OUTPUT_FILE_MESSAGE_ID);
        resultProcessorPort.send(msg);
    }


    private void sendHHSummaryRequestToWorkQueues() {
        Message[] msgs = new Message[nWorkQueues];

        for (int i = 0; i < nWorkQueues; i++) {
            Message msg = mFactory.createMessage();
            msg.setId(MESSAGE_IDS.HA_SEND_SUMMARIES_ID);
            msgs[i] = msg;
        }

        sendWorkToWorkQueues(msgs, hhWorkPorts, nWorkQueues);
    }


    private int setUpQueues() {
        int nNodes = Integer.parseInt(ResourceUtil.getProperty(spg2dafRb, "nNodes"));
        nWorkQueues = nNodes -1;
        PortManager pManager = PortManager.getInstance();
        mFactory = MessageFactory.getInstance();

        hhWorkPorts = new Port[nWorkQueues];
        for(int i=0;i<nWorkQueues;i++) {   //work queues will always start on node 1 (and be numbered 1...n)
            hhWorkPorts[i] = pManager.createPort("WorkQueue_"+ (i+1));

        }

        resultProcessorPort = pManager.createPort("ResultsQueue");

        return nWorkQueues;
    }


    private void waitForGoOnSignal() {
        long waitTime;
        //Wait here until we get a signal from SDResultsProcessorTask that all calcs
        //are complete
        waitTime = System.currentTimeMillis();
        try {
            signal.waitUntilStateIs(true,0);
            signal.setValue(false);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        logger.debug("GO ON SIGNAL RECEIVED: Waited "+ (System.currentTimeMillis()-waitTime)/1000.0 + " secs for workers ");
    }




    private void sendWorkToWorkQueues(Message[] msgs, Port[] workPorts, int nWorkQueuesToSendTo){
        long sendTime = System.currentTimeMillis();
        for(int m=0;m<msgs.length;m++){
            //get a message from the array
            Message msg = msgs[m];
            int count = m+1;

            //Send the message
            if(logger.isDebugEnabled()) {
                logger.debug( getName() + " sent " + msg.getId() + " to " + workPorts[(count%nWorkQueuesToSendTo)].getName());
            }
            workPorts[(count%nWorkQueuesToSendTo)].send(msg); //will cycle through the ports
                                                        //till all messages are sent
        }
        logger.info("All messages have been sent.  Time in secs: "+ (System.currentTimeMillis()-sendTime)/1000.0);
    }

    public static void signalResultsProcessed() {
        signal.setValue(true);
    }


    private void writeDoneFile(){

        // check to see if any debug files were created. This indicates that
            // there were tours that could
            // not find destinations or stops that couldn't find locations, etc.
            File doneFile = null;
            try {
                doneFile = new File(ResourceUtil.getProperty(spgRb, "spg2.done.file"));
                // Signal to the File Monitor that the model is finished.
                logger.info("Signaling to the File Monitor that the model is finished");
                PrintWriter writer = new PrintWriter(new FileWriter(doneFile));
                writer.println("spg daf is done." + new Date());
                writer.close();
                logger.info("spg daf is done.");
            } catch (IOException e) {
                String errMsg = "Could not write done file.";
                logger.fatal(errMsg);
                throw new RuntimeException(errMsg);
            }
    }

}
