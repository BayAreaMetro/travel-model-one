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

import java.util.HashMap;
import java.util.Iterator;
import org.apache.log4j.Logger;

import com.pb.common.util.BlockingFIFOQueue;

/** 
 * This class manages Port classes. Clients needing to send messages
 *  should use the getPort() method and work with an instance of a Port. *
 *
 * @author    Tim Heier
 * @version   1.0, 9/23/2002
 */
public class PortManager {

    private static PortManager instance = new PortManager();
    protected static Logger logger = Logger.getLogger("com.pb.common.daf");

    //Map of port names to port instances. Port names are created by combining
    //the from and to port values
    protected HashMap portMap = new HashMap(100);
    
    
    /** 
     * Keep this class from being created with "new".
     */
    private PortManager() {
    }


    /** 
     * Return instances of this class. Implements singleton pattern.
     */
    public static PortManager getInstance() {
        if(logger.isDebugEnabled()) logger.debug("Getting instance of PortManager");
        return instance;
    }

    
    /** 
     * Get the name of the current task. This should return the name of the 
     * task or thread which called this method.
     */
    private String getNameOfCaller() {
        Thread t = Thread.currentThread();
        String taskName = t.getName();
        return taskName;    
    }


    /** 
     * Returns an instance of a port which can be used to send and receive
     * messages. Requires only the "to task name" for convenience. The
     * name of the current task or thread is used as the "from name".
     */
    public Port createPort(String toQueueName) {
        String fromTaskName = getNameOfCaller();

        Port port = createPort(fromTaskName, toQueueName);
        return port;
    }


    /** 
     * Returns an instance of a port which can be used to send and receive
     * messages.
     */
    public Port createPort(String fromTaskName, String toQueueName) {
        QueueManager qManager = QueueManager.getInstance();
        boolean localQueue = qManager.isQueueLocal(toQueueName);
        
        Port port = null;
        //Lookup local MessageQueue, create a local message queue port
        if (localQueue) {
            logger.info("Creating LocalPort from=" + fromTaskName + ", to=" + toQueueName);
            MessageQueue messageQueue = qManager.getMessageQueue(toQueueName);
            port = new LocalMessageQueuePort(fromTaskName, toQueueName, messageQueue);
        }
        //Get system send queue, create a remote message queue port
        else {
            logger.info("Creating RemotePort from=" + fromTaskName + ", to=" + toQueueName);
            BlockingFIFOQueue systemSendQueue = qManager.getSystemSendQueue();
            port = new RemoteMessageQueuePort(fromTaskName, toQueueName, systemSendQueue);
        }
        
        portMap.put((fromTaskName+"_"+toQueueName), port);
        
        return port;
    }

    
    /**
     * Finds an existing port based on the task and queue name values used to 
     * create the port. 
     * 
     * @param fromTaskName
     * @param toQueueName
     * @return
     */
    public Port findPort(String fromTaskName, String toQueueName) {
        if (logger.isDebugEnabled()) {
            logger.debug("Finding port from=" + fromTaskName + " to="+toQueueName);
        }
        Port port = (Port) portMap.get(fromTaskName+"_"+toQueueName);
        
        if (port == null) {
            logger.error("PortManager.findPort, no port was found");
        }
        return port;
    }
    

    /**
     * This methodis called when a task is being stopped.
     * 
     * @param fromTaskName
     * @param toQueueName
     */
    protected void removePort(String portName) {
        logger.info("Removing port=" + portName);

        Port port = (Port) portMap.remove(portName);
        
        if (port == null) {
            logger.warn("No port was found");
        }
        
    }
    
    
    public Iterator getPortIterator() {
        throw new RuntimeException("getPortIterator method not implemented yet");
    }

}