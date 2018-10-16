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

/** 
 * Represents point to point communication.
 *
 * @author    Tim Heier
 * @version   1.0, 12/15/2003
 */
public class LocalMessageQueuePort extends Port {

    protected MessageQueue messageQueue;

    
    protected LocalMessageQueuePort(String fromTaskName, String toQueueName, 
                                    MessageQueue messageQueue) {
        super(fromTaskName, toQueueName);
        
        this.messageQueue = messageQueue;
    }


    public void send (Message msg) {
        msg.setSender(fromTaskName);
        msg.setRecipient(toQueueName);

        try {
            messageQueue.add(msg);
        } catch (InterruptedException e) {
            logger.error("interrupted while adding message to messageQueue");
        }
    }

    
    public Message receive() {
        if (logger.isDebugEnabled()) {
            logger.debug(this.fromTaskName + " waiting on queue=" + this.toQueueName);
        }
        Message msg = null;
        msg = messageQueue.removeWithWaiter(waiter);
        
        //No message was returned, wait until a message is placed in the message box
        if (msg == null) {
            try {
                msg = (Message) waiter.waitOnMessage();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        return msg;
    }
    
    
    public Message receive(long waitTime) {
        // TODO need to implement this method
        return null;
    }

    
    public void send(Message msg, long timeToLive) {
        // TODO need to implement this method
    }

    
    /**
     * Adds a message to the message box for this port.
     */
    public void addMessage(Message msg) {
        try {
            waiter.notifyWithMessage(msg);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        
    }

    
    public void subscribe() throws UnsupportedOperationException {
        throw new UnsupportedOperationException();
    }
    
    public void unsubscribe() throws UnsupportedOperationException {
        throw new UnsupportedOperationException();
    }


    /** Returns the number of elements in the queue
     * 
     * @return
     */
    public int getSize() {
        return messageQueue.getSize();
    }
}
