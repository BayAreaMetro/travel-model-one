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

import org.apache.log4j.Logger;


/** Represents a communication port used by a Task to send/receive
 * messages to other tasks.
 *
 * @author    Tim Heier
 * @version   1.0, 4/18/2002
 */
public abstract class Port {

    protected Logger logger = Logger.getLogger("com.pb.common.daf");

    protected QueueManager qManager = QueueManager.getInstance();

    protected String name;
    protected String fromTaskName;
    protected String toQueueName;

    protected Waiter waiter = new Waiter();
    protected boolean localQueue = false;
    
    protected long timeToLive = DAF.getTimeToLive();
    protected long receiveWaitTime = DAF.getReceiveWaitTime();
    
    protected int receiveCount = 0;
    protected int sendCount = 0;

    
    private Port() {
    }

    
    protected Port(String fromTaskName, String toQueueName) {
        this.fromTaskName = fromTaskName;
        this.toQueueName = toQueueName;
        this.name = fromTaskName + "_" + toQueueName;
    }

    public int getSendCount() {
        return sendCount;
    }

    
    public int getReceiveCount() {
        return receiveCount;
    }
    
    
    /**
     * @return Returns the name.
     */
    public String getName() {
        return name;
    }

    
    /** Takes a message off the receive queue for a named task. This method
     * will block if there are no messages available.
     */
    public abstract Message receive();

    public abstract Message receive(long waitTime);
    
    public abstract void send (Message m); 

    public abstract void send(Message msg, long timeToLive);
    
    public abstract void addMessage(Message m);
    
    public abstract void subscribe();

    public abstract void unsubscribe();

    
}
