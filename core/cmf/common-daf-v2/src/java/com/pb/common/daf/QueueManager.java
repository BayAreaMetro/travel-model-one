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

import com.pb.common.util.BlockingFIFOQueue;

import java.util.HashMap;
import org.apache.log4j.Logger;

/** Manages queues of messages.
 *
 * @author    Tim Heier
 * @version   1.0, 6/18/2002
 */
public class QueueManager {

    private static Logger logger = Logger.getLogger("com.pb.common.daf");

    private String thisNodeName;
    private int defaultQueueSize;
    private BlockingFIFOQueue systemSendQueue;
    
    //Map queueNames to nodeName
    protected static HashMap queueNameToNodeName = new HashMap();
    
    //Map queueName to a messageQueue instance
    private HashMap messageQueueMap = new HashMap(30);
    
    private static QueueManager instance = new QueueManager();
    
    private QueueManager() {
        readProperties();
        systemSendQueue = new BlockingFIFOQueue( defaultQueueSize );
    }


    /** 
     * Return instances of this class.
     *
     */
    public static QueueManager getInstance() {
        if(logger.isDebugEnabled()) logger.debug("Getting instance of QueueManager");
        return instance;
    }

    
    /** 
     * Creates message queues based on a supplied list of queue definitions.
     */
    public void createMessageQueues(QueueDef[] queueDefs) {

        //Loop through all of the queue definitions
        for (int i=0; i < queueDefs.length; i++) {
            String queueName = queueDefs[i].name;
            String queueNodeName = queueDefs[i].nodeName;
            int queueSize = queueDefs[i].size;

            //Populate map of queueName to nodeName
            queueNameToNodeName.put(queueName, queueNodeName);
            
            //If queue is supposed to be on this node then create it
            if (queueNodeName.equalsIgnoreCase(thisNodeName)) {
                logger.info("Creating queue=" + queueName);
                MessageQueue msgQueue = new MessageQueue(queueName, queueSize);
                MessageQueue previousQueue = (MessageQueue) messageQueueMap.put(queueName, msgQueue);

                //Check if queue already existed
                if (previousQueue != null) {
                    logger.error("Message queue existed, overwriting");
                }
            }
        }
        
    }

    
    /** 
     * Remove message queues based on a supplied list of queue definitions.
     */
    protected void removeMessageQueues(QueueDef[] queueDefs) {

        //Loop through all of the queue definitions
        for (int i=0; i < queueDefs.length; i++) {
            String queueName = queueDefs[i].name;
            String queueNodeName = queueDefs[i].nodeName;

            //Remove queueNames from map
            queueNameToNodeName.remove(queueName);
            
            //If queue is on this node then remove it
            if (queueNodeName.equalsIgnoreCase(thisNodeName)) {
                logger.info("Removing queue=" + queueName);
                MessageQueue previousQueue = (MessageQueue) messageQueueMap.remove(queueName);

                //Check if queue already existed
                if (previousQueue == null) {
                    logger.error(queueName + ", queue did not exist");
                }
            }
        }
        
    }

    
    /** 
     * Return the name of the node given a queue.
     */
    protected String getNodeNameforQueueName(String queueName ) {
        String nodeName = (String) queueNameToNodeName.get(queueName);
        
        if (nodeName == null) {
            logger.error("QueueManager.getNodeNameforQueue, nodeName is null for queueName="+queueName);
            logger.error("queueNameToNodeName=" + queueNameToNodeName);
        }
        
        return nodeName;        
    }
    
    
    public boolean isQueueLocal(String toQueueName) {
        boolean localFlag = false;

        String nodeName = (String) queueNameToNodeName.get(toQueueName);
        
        //Queue name does not exist - might be a typo
        if (nodeName == null) {
            logger.error("QueueManager.isQueueLocal, nodeName is null for queueName=" + toQueueName);
        }
        else if (nodeName.equalsIgnoreCase(thisNodeName)) {
            localFlag = true;
        }
        return localFlag;
    }
    

    /** 
     * Returns the system send queue. Currently, the transport layer needs
     *  this method.
     *
     * Note: All remote tasks share a single outbound queue at this time.
     */
    protected BlockingFIFOQueue getSystemSendQueue() {
        return systemSendQueue;
    }


    /** 
     * Returns a MessageQueue reference given a queue name. This method will only
     * return MessageQueues located in this node.
     *
     * Note: All remote tasks share a single outbound queue at this time.
     */
    public MessageQueue getMessageQueue(String queueName) {
        MessageQueue messageQueue = (MessageQueue) messageQueueMap.get(queueName);

        if (messageQueue == null) {
            logger.error("QueueManager.getMessageQueue, messageQueue is null for queueName="
                            +queueName);
        }

        return messageQueue;
    }


    private void readProperties() {
        this.defaultQueueSize  = DAF.getDefaultQueueSize();
        this.thisNodeName = DAF.getNodeName();
    }


    /** 
     * Allows classes outside this package to view the status of the queue.
     */
    public boolean isSendQueueFull() {
        return systemSendQueue.isFull();
    }


}
