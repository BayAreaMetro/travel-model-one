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

import com.pb.common.daf.*;
import com.pb.common.util.BooleanLock;
import com.pb.common.util.ResourceUtil;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

/**
 * @author Christi Willison
 * @version Mar 18, 2004
 */
public class ServerTask extends Task{

    Logger serverTaskLogger = Logger.getLogger(ServerTask.class);
    protected static BooleanLock signal = new BooleanLock(false);
    ResourceBundle testdafRb = null;
    
//  Worker Node Tasks: Depending on the type of messages you want to send
    //you need to have a work task defined.  This test application can
    //send any combination of setup, pinkslip, maildeliver or 
    //shootthemessenger messages depending on how it is configured.
    //The onStart method will check to make sure the app has been configured
    //correctly.  Sending a setup message requires a master task on node0,
    //a setup work task on all worker nodes and a setup result processor task on
    //node0.  The same is true for all other types of messages.
    ArrayList setUpWorkTasks = new ArrayList();
    ArrayList psWorkTasks = new ArrayList();
    ArrayList mdWorkTasks = new ArrayList();
    ArrayList stmWorkTasks = new ArrayList();
    
    //Node0 Tasks:  There should be a single master task and a
    //single setupResult task on node0.  The other
    //results tasks are defined depending on what
    //types of messages are being sent.  If you have a
    //PSWorkTask defined then you must have a PSResultTask and 
    //a pinkSlipWorkQueue as well as a PSResultsQueue.
    ArrayList masterTasks = new ArrayList();
    ArrayList setUpResultTasks = new ArrayList();
    ArrayList psResultTasks = new ArrayList();
    ArrayList mdResultTasks = new ArrayList();
    ArrayList stmResultTasks = new ArrayList();
    
    //Queues: There should be a work queue for each worker node
    //however the application might be configured to only
    //send 1 type of message in which case the other
    //queues would not be defined and therefore their list
    //will be empty.
    ArrayList setUpWorkQueues = new ArrayList();
    ArrayList pinkSlipWorkQueues = new ArrayList();
    ArrayList mailDeliveryWorkQueues = new ArrayList();
    ArrayList shootTheMessengerWorkQueues = new ArrayList();
    ArrayList resultProcessorQueues = new ArrayList();
    
    static int nPinkSlips = 10;
    static int nLetters = 10;
    static int nBullets = 10;
    
    int nIterations = 1000;
    
    boolean sendingPinkSlips = false;
    boolean sendingLetters = false;
    boolean sendingBullets = false;
    
    public void onStart(){
        serverTaskLogger.info( "***" + getName() + " started.");
                
        
        testdafRb = ResourceUtil.getResourceBundle("testdaf_msgCrazy");
        
        ArrayList tasks = ResourceUtil.getList(testdafRb, "taskList");
        Iterator iter = tasks.iterator();
        while(iter.hasNext()){
            String taskName = (String) iter.next();
            if(taskName.indexOf("Master")>=0) {
                masterTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to masterTasks");
            }else if(taskName.indexOf("SetupResult")>=0){
                setUpResultTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to setUpResultTasks");
            }else if(taskName.indexOf("PSResult")>=0){
                psResultTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to psResultTasks");
            }else if(taskName.indexOf("MDResult")>=0){
                mdResultTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to mdResultTasks");
            }else if(taskName.indexOf("STMResult")>=0){
                stmResultTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to stmResultTasks");
            }else if(taskName.indexOf("SetupWork") >=0){
                setUpWorkTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to setUpWorkTasks");
            }else if(taskName.indexOf("MDWork")>=0) {
                mdWorkTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to mdWorkTasks");
            }else if(taskName.indexOf("STMWork")>=0) {
                stmWorkTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to stmWorkTasks");
            }else if(taskName.indexOf("PSWork")>=0){
                psWorkTasks.add(taskName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(taskName + " added to psWorkTasks");
            }
        }
        ArrayList queues = ResourceUtil.getList(testdafRb, "queueList");
        if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug("Total queues " + queues.size());
        iter = queues.iterator();
        while(iter.hasNext()){
            String queueName = (String) iter.next();
            if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug("Queue Name : " + queueName);
            if(queueName.indexOf("SetupWork") >=0){
                setUpWorkQueues.add(queueName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(queueName + " added to setUpWorkQueues");
            }else if(queueName.indexOf("PSWork")>=0) {
                pinkSlipWorkQueues.add(queueName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(queueName + " added to pinkSlipWorkQueues");
            }else if(queueName.indexOf("MDWork")>=0) {
                mailDeliveryWorkQueues.add(queueName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(queueName + " added to mailDeliveryWorkQueues");
            }else if(queueName.indexOf("STMWork")>=0) {
                shootTheMessengerWorkQueues.add(queueName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(queueName + " added to shootTheMessengerWorkQueues");
            }else if(queueName.indexOf("ResultsQueue")>=0){
                resultProcessorQueues.add(queueName);
                if(serverTaskLogger.isDebugEnabled()) serverTaskLogger.debug(queueName + " added to resultProcessorQueues");
            }
        }
        serverTaskLogger.info(getName() + " onStart() ended");
    }

    public void doWork(){
        long startTime = System.currentTimeMillis();
        //Read in from the properties file the number of nodes
        //so that we know how many worker ports we need
        int nNodes = Integer.parseInt(ResourceUtil.getProperty(testdafRb,"nNodes"));
        int nWorkQueues = nNodes-1;
        serverTaskLogger.info("Number of worker nodes");
        
        //check configuration file
        if(setUpWorkTasks.size() != nWorkQueues || setUpResultTasks.size() == 0 || !resultProcessorQueues.contains("SetupResultsQueue")){
            serverTaskLogger.fatal("Check setUpWorkTask configuation");
            serverTaskLogger.fatal("setUpWorkTasks size: " + setUpWorkTasks.size());
            serverTaskLogger.fatal("setUpResultTasks size: " + setUpResultTasks.size());
            serverTaskLogger.fatal("resultsProcessorQueues contains 'SetupResultsQueue': " + resultProcessorQueues.contains("SetupResultsQueue"));
            System.exit(1);
        }
        
        if(psWorkTasks.size() > 0 && (psResultTasks.size() == 0 || pinkSlipWorkQueues.size() ==0 || !resultProcessorQueues.contains("PSResultsQueue"))){
            serverTaskLogger.fatal("Check pinkSlipWorkTask configuation");
            serverTaskLogger.fatal("psWorkTasks size: " + psWorkTasks.size());
            serverTaskLogger.fatal("psResultTasks size: " + psResultTasks.size());
            serverTaskLogger.fatal("pinkSlipWorkQueues size: " + pinkSlipWorkQueues.size());
            serverTaskLogger.fatal("resultsProcessorQueues contains 'PSResultsQueue': " + resultProcessorQueues.contains("PSResultsQueue"));
            System.exit(1);
        }else if(psWorkTasks.size() > 0){
            sendingPinkSlips = true;
            serverTaskLogger.info("Application is configured to send Pink Slips.");
        }
        
        if(mdWorkTasks.size() > 0 && (mdResultTasks.size() == 0 || mailDeliveryWorkQueues.size() ==0 || !resultProcessorQueues.contains("MDResultsQueue"))){
            serverTaskLogger.fatal("Check mailDeliveryWorkTask configuation");
            serverTaskLogger.fatal("mdWorkTasks size: " + mdWorkTasks.size());
            serverTaskLogger.fatal("mdResultTasks size: " + mdResultTasks.size());
            serverTaskLogger.fatal("mailDeliveryWorkQueues size: " + mailDeliveryWorkQueues.size());
            serverTaskLogger.fatal("resultsProcessorQueues contains 'MDResultsQueue': " + resultProcessorQueues.contains("MDResultsQueue"));
            System.exit(1);
        }else if(mdWorkTasks.size() > 0){
            sendingLetters = true;
            serverTaskLogger.info("Application is configured to send Letters");
        }
        
        if(stmWorkTasks.size() > 0 && (stmResultTasks.size()== 0 || shootTheMessengerWorkQueues.size()==0 || !resultProcessorQueues.contains("STMResultsQueue"))){
            serverTaskLogger.fatal("Check shootTheMesengerWorkTask configuation");
            serverTaskLogger.fatal("stmWorkTasks size: " + stmWorkTasks.size());
            serverTaskLogger.fatal("stmResultTasks size: " + stmResultTasks.size());
            serverTaskLogger.fatal("shootTheMessengerWorkQueues size: " + shootTheMessengerWorkQueues.size());
            serverTaskLogger.fatal("resultsProcessorQueues contains 'STMResultsQueue': " + resultProcessorQueues.contains("STMResultsQueue"));
            System.exit(1);
        }else if(stmWorkTasks.size() > 0){
            sendingBullets = true;
            serverTaskLogger.info("Application is configured to send Bullets");
        }

        PortManager pManager = PortManager.getInstance();
        MessageFactory mFactory = MessageFactory.getInstance();
        Message[] msgs;

        //Get ports to the worker queues to communicate with a queue
        Port[] SetupWorkPorts = new Port[nWorkQueues];
        for(int i=0;i<nWorkQueues;i++){
            SetupWorkPorts[i] = pManager.createPort((String)setUpWorkQueues.get(i));
        }

        Port[] PSWorkPorts = null;
        if(sendingPinkSlips){
            PSWorkPorts = new Port[nWorkQueues]; //the Server task will always be on node 0
            for(int i=0;i<nWorkQueues;i++){             //work queues will always start on node 1 (and be numbered 1...n)
                PSWorkPorts[i] = pManager.createPort((String) pinkSlipWorkQueues.get(i)); //
            }
        }
        
        Port[] MDWorkPorts = null;
        if(sendingLetters){
            MDWorkPorts = new Port[nWorkQueues];
            for(int i=0;i<nWorkQueues;i++){
                MDWorkPorts[i] = pManager.createPort((String) mailDeliveryWorkQueues.get(i));
            }
        }
        
        Port[] STMWorkPorts = null;
        if(sendingBullets){
            STMWorkPorts = new Port[nWorkQueues];
            for(int i=0;i<nWorkQueues;i++){
                STMWorkPorts[i] = pManager.createPort((String) shootTheMessengerWorkQueues.get(i));
            }
        }
        

        //Set up all nodes
        msgs = createSetupMessages(mFactory,nWorkQueues);
        sendWorkToWorkQueues(msgs,SetupWorkPorts,nWorkQueues);

        //Wait for a signal from SetupResultsProcessorTask that all nodes
        //are set up.
        long waitTime = System.currentTimeMillis();
        try {
        	serverTaskLogger.info( "ServerTask for all Setup Messagess to be received by SetupResultProcessor Task.");
        	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " before state change.");
        	signal.waitUntilStateIs(true,0);
            signal.setValue(false);
   //         signal.waitUntilStateChanges(0);
        	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " after state change.");
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        serverTaskLogger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime)/1000.0 + " secs for " +
                        "nodes to set up");

        //Now send messages first to the PinkSlip workers and then to the
        //MailDelivery workers and see if the app hangs.
        int iter = 1;
        while(iter <= nIterations){  //criteria includes meritMeasure and nIterations
            long iterationTime = System.currentTimeMillis();
            serverTaskLogger.info("*******************************************************************************************");
            serverTaskLogger.info("*   Starting iteration "+ (iter));
            serverTaskLogger.info("*******************************************************************************************");

//            //Now send work to the PSWorkQueue (Pink Slips)
//            msgs = createPinkSlipWorkMessages(mFactory, iter);
//            sendWorkToWorkQueues(msgs,PSWorkPorts,nWorkQueues);
//            
//            //Wait for a signal from PSResultProcessorTask that all calcs
//            //are complete and saved in the local node's memory (ie. node 0's memory)
//            waitTime = System.currentTimeMillis();
//            try {
//                signal.waitUntilStateIs(true,0);
//                signal.setValue(false);
//            } catch (InterruptedException e) {
//                e.printStackTrace();

            if(sendingPinkSlips){
                msgs = createPinkSlipWorkMessages(mFactory, iter);
                serverTaskLogger.info("Sending Pink Slip Messages");
                sendWorkToWorkQueues(msgs,PSWorkPorts,nWorkQueues);
                
                //Wait for a signal from PSResultProcessorTask that all calcs
                //are complete and saved in the local node's memory (ie. node 0's memory)
                waitTime = System.currentTimeMillis();
                try {
                	serverTaskLogger.info( "ServerTask waiting to hear all PinkSlips received by PSResultProcessor Task in iteration " + (iter+1) + ".");
                	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " before state change.");
                  signal.waitUntilStateIs(true,0);
                  signal.setValue(false);
//                    signal.waitUntilStateChanges(0);
                	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " after state change.");
                } catch (InterruptedException e) {
                	serverTaskLogger.error( "caught InterruptedException sending PinkSlips", e);
                }
                serverTaskLogger.info("GO ON SIGNAL RECEIVED: Waited "+  (System.currentTimeMillis()-waitTime)/1000.0 + " secs for " +
                            "for Pink Slips to be processed");

            }
            

            //send work to the MDWorkQueues (Mail Delivery)
            if(sendingLetters){
                msgs = createMailDeliveryWorkMessages(mFactory, iter);
                serverTaskLogger.info("Sending Letters");
                sendWorkToWorkQueues(msgs,MDWorkPorts,nWorkQueues);
                
                //Wait for a signal from PSResultProcessorTask that all calcs
                //are complete and saved in the local node's memory (ie. node 0's memory)
                waitTime = System.currentTimeMillis();
                try {
                	serverTaskLogger.info( "ServerTask waiting to hear all Letters received by MDResultProcessor Task in iteration " + (iter+1) + ".");
                	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " before state change." );
                    signal.waitUntilStateIs(true,0);
                    signal.setValue(false);
//                      signal.waitUntilStateChanges(0);
                	serverTaskLogger.info( "value of BooleanLock signal.value = " + signal.getValue() + " after state change.");
                } catch (InterruptedException e) {
                	serverTaskLogger.error( "caught InterruptedException sending Letters", e);
                }
                serverTaskLogger.info("GO ON SIGNAL RECEIVED: Waited "+ (System.currentTimeMillis()-waitTime)/1000.0 + " secs " +
                            "for all Letters to be processed");
            }
            

            serverTaskLogger.info("*********************************************************************************************");
            serverTaskLogger.info("*   End of iteration "+ (iter)+".  Time in seconds: "+(System.currentTimeMillis()-iterationTime)/1000.0);
            serverTaskLogger.info("*********************************************************************************************");
            
            iter++;
        }
        
        //Have the workers shoot the messenger.
        if(sendingBullets){
            msgs = createShootTheMessengerWorkMessages(mFactory);
            sendWorkToWorkQueues(msgs, STMWorkPorts, nWorkQueues);
            try {
                signal.waitUntilStateIs(true,0);
                signal.setValue(false);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            serverTaskLogger.info("Waited "+ (System.currentTimeMillis()-waitTime)/1000.0 + " secs for bullets ");
        }
        
        
        serverTaskLogger.info("Total Time in seconds: "+((System.currentTimeMillis()-startTime)/1000));
        File doneFile = new File(ResourceUtil.getProperty(testdafRb,"done.file"));
        if(!doneFile.exists()){
            try {
                doneFile.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        serverTaskLogger.info("Done File has been written");
        return;
    }

    private Message[] createSetupMessages(MessageFactory mFactory, int nWorkQueues){
        Message[] messages =  new Message[nWorkQueues];
        for(int i=0;i<messages.length;i++){
            Message msg = mFactory.createMessage();
            msg.setId("SetupMessage");
            messages[i]=msg;
        }
        return messages;
    }


    private Message[] createPinkSlipWorkMessages(MessageFactory mFactory, int iter){
        Message[] messages = new Message[nPinkSlips];
        String iterString = (new Integer(iter)).toString();
        int count=1;
        while (count <= nPinkSlips) {
            String c = (new Integer(count)).toString();
            Message msg = mFactory.createMessage();
            msg.setId("Iteration,"+iterString+",PSWorkMessage_fromServer," + c);
            msg.setValue("Slip Number", c);
            msg.setValue("Iteration", iterString);
            messages[count-1]=msg;
            count++;
        }
        return messages;
    }

    private Message[] createMailDeliveryWorkMessages(MessageFactory mFactory, int iter){
        Message[] messages = new Message[nLetters];
        String iterString = (new Integer(iter)).toString();
        int count=1;
        while (count <= nLetters) {
            String c = (new Integer(count)).toString();
            Message msg = mFactory.createMessage();
            msg.setId("Iteration,"+iterString+",MDWorkMessage_fromServer,"+ c);
            msg.setValue("Letter Number", c );
            msg.setValue("Iteration", iterString);
            messages[count-1]=msg;
            count++;
        }
        return messages;
    }
    
    private Message[] createShootTheMessengerWorkMessages(MessageFactory mFactory){
        Message[] messages = new Message[nBullets];
        int count=1;
        while (count <= nBullets) {
            String c = (new Integer(count)).toString();
            Message msg = mFactory.createMessage();
            msg.setId("STMWorkMessage_"+ c + "_fromServer");
            msg.setValue( "Bullet Number", c );
            messages[count-1]=msg;
            count++;
        }
        return messages;
    }

    private void sendWorkToWorkQueues(Message[] msgs, Port[] WorkPorts, int nWorkQueues){
        long sendTime = System.currentTimeMillis();
        for(int m=0;m<msgs.length;m++){
            //get a message from the array
            Message msg = msgs[m];
            int count = m+1;

            //Send the message
            if(serverTaskLogger.isDebugEnabled()) {
                serverTaskLogger.debug( getName() + " sent " + msg.getId() + ", to " + WorkPorts[(count%nWorkQueues)].getName());
            }
            WorkPorts[(count%nWorkQueues)].send(msg); //will cycle through the ports
                                                        //till all messages are sent
        }
        serverTaskLogger.info("All messages have been sent.  Time in secs: "+ (System.currentTimeMillis()-sendTime)/1000.0);
    }

    public static void signalResultsProcessed() {
        signal.setValue(true);
//        signal.flipValue();
    }
    
    public static boolean readFlag(ResourceBundle rb, String flagName, boolean defaultValue) {
        String stringVal = ResourceUtil.getProperty(rb, flagName);
        if (stringVal == null) return defaultValue;
        boolean retVal = defaultValue;
        if (defaultValue == true) {
            if (stringVal.equalsIgnoreCase("false")) {
                retVal = false;
            }
        } else {
            if (stringVal.equalsIgnoreCase("true")) {
                retVal = true;
            }
        }
        return retVal;
    }

}
