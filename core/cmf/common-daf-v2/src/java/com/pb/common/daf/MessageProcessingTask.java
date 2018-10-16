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

/** 
 * A task that presents a message processing interface to a user. This is more of
 * an event driven style of working with messages. A subclass needs to implement
 * the onMessage() method which will be called each time a message is received.
 * 
 * Note: The message processing is sequential. The onMessage() method will be
 * called when a message is received and when processing from the previous message
 * is complete. 
 *
 * @author    Tim Heier
 * @version   1.0, 8/8/2003
 */
public abstract class MessageProcessingTask extends Task {

    protected PortManager pManager = PortManager.getInstance();
    protected MessageFactory mFactory = MessageFactory.getInstance();

    protected Port defaultPort;

    //Keep of a map of queueName->Ports that this task has sent messages to 
    protected HashMap portMap = new HashMap(100);


    /*
     * @see com.pb.common.daf.Task#doWork()
     */
    public void doWork() {

        while (!stopRequested) {
            Message msg = defaultPort.receive();
            
            //Message is null if timeout occurred
            if (msg == null) {  
                continue;
            }
            onMessage(msg);
        }
        
        //Remove ports used by this task from PortManager
        Iterator iter = portMap.keySet().iterator();
        while (iter.hasNext()) {
            String portName = (String) iter.next();
            pManager.removePort(portName);
        }
    
        portMap = null;
        defaultPort = null;
        pManager = null;
        mFactory = null;
    }

    
    /**
     * This method should be overriden by any subclasses to really processs
     * messages.
     * 
     * @param msg
     */
    public void onMessage(Message msg) {
        //Override method and add functionality
    }

    
    /**
     * Helper method to make creating new messages easy.
     *
     * @return  a new message
     */
    public Message createMessage() {
        return mFactory.createMessage();
    }


    /**
     * Send a message to a specific queue.
     *
     * @param toQueueName  name of queue to send message to
     * @param msg  message to send to task
     */
    public void sendTo(String toQueueName, Message msg) {
        Port port = (Port) portMap.get( toQueueName );

        //Create a new port and keep it in the queue->port mapping
        if (port == null) {
            port = pManager.createPort( name, toQueueName );
            portMap.put( toQueueName, port );
        }
        port.send( msg );
    }


    /**
     * Sets a queue that this task will remove messages from. The queue name
     * is usually set as a default in a properties file.
     *
     * @param toQueueName
     */
    public void setDefaultQueue(String toQueueName) {
        defaultPort = pManager.createPort(name, toQueueName);
    }

}
