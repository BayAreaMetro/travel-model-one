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

import com.pb.common.util.FIFOQueue;

/** 
 * An object that queue messages and keep a list of waiting receivers.
 *
 * @author    Tim Heier
 * @version   1.0, 1/23/2004
 */
public class MessageQueue {

    protected static Logger logger = Logger.getLogger(MessageQueue.class);
    
    private String name;
    private int size;
    private FIFOQueue waiterQueue;
    private FIFOQueue msgQueue;
    
    
    private MessageQueue() { }
    

    public MessageQueue(String name, int size) {
        this.name = name;
        this.size = size;
        
        waiterQueue = new FIFOQueue(size);
        msgQueue = new FIFOQueue(size);
    }

    /**
     * Adds a message to the message queue. If there are no waiters, the message
     * is added to the message queue for the next receive() call. If there are
     * waiters, then the next waiter is taken from the wait queue and the 
     * messsage is returned to it's message box. Presumably, the waiter should
     * be waiting on this msgBox. 
     * 
     * @param msg
     */
    public synchronized void add(Message msg) throws InterruptedException {
        
        
        //If no waiters, add message to queue        
        if (waiterQueue.isEmpty()) {
            if(logger.isDebugEnabled()) logger.debug("MessageQueue,adding msg,"+ msg.getId()+",to msgQueue " + name);
            msgQueue.add(msg);
        }
        //Waiters are present, get next waiter queue and add message 
        else {
            //Remove either the system sendQueue or a queue local to a port 
            Waiter waiter = (Waiter) waiterQueue.remove();
            if(logger.isDebugEnabled()) logger.debug("MessageQueue,removing waiterQueue,"+ msg.getId());
            waiter.notifyWithMessage(msg);
            if(logger.isDebugEnabled()) logger.debug("MessageQueue,notifying waiter with msg,"+ msg.getId());
        }
    }

    
    /**
     * Removes a message from the queue. If no messages are available then through
     * an exception.
     * 
     * @return
     */
    public synchronized Message remove() {
        Message msg = null;

        //If no messages are available - throw an exception
        if (! msgQueue.isEmpty()) {
            msg = (Message) msgQueue.remove();
        }

        return msg;
    }
    
    
    /**
     * Removes a message from the queue. If no messages are available then a
     * null message is returned and the waiter parameter is used as a call-back
     * mechanism. The waiter will be notified when a message is available.
     * 
     * @param waiter
     * @return
     */
    public synchronized Message removeWithWaiter(Waiter waiter) {
        Message msg = null;

        //If no messages, add message box to waiter queue
        if (msgQueue.isEmpty()) {
            waiterQueue.add(waiter);
        }
        //Messages are persent, get next message and return
        else {
            msg = (Message) msgQueue.remove();
        }

        //Will return a null message when no message was available and
        //message box is added to waiter queue
        return msg;
    }
    
    
    /**
     * Add a waiter object to waiter queue.
     * 
     * @param waiter
     */
    public synchronized void add(Waiter waiter) {
        waiterQueue.add(waiter);
    }
    
    
    /**
     * @return Returns the name of the queue.
     */
    public String getName() {
        return name;
    }

    
    public synchronized boolean isEmpty() {
        return (msgQueue.isEmpty());
    }

    /** return the size of the underlying queue. This is the number of
     * elements in the queue.
     *
     * @return number of elements in queue
     */
    public int getSize() {
        return msgQueue.getSize();
    }

}
