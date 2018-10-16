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

/** 
 * Represents point to point communication.
 *
 * @author    Tim Heier
 * @version   1.0, 12/15/2003
 */
public class RemoteMessageQueuePort extends Port {

    protected BlockingFIFOQueue sendQueue;
    
    
    protected RemoteMessageQueuePort(String fromTaskName, String toQueueName, 
                                    BlockingFIFOQueue sendQueue) {
        super(fromTaskName, toQueueName);
        
        this.sendQueue = sendQueue;
    }


    public void send (Message msg) {
        msg.setSender(fromTaskName);
        msg.setRecipient(toQueueName);

        sendMessage(msg);
    }

    
    public Message receive() {
        Message msg = null;
        
        //Queue is remote, send a "remove" message and wait on message box
        Message removeMsg = MessageFactory.getInstance().createMessage();
        removeMsg.setSender(fromTaskName);
        removeMsg.setRecipient(toQueueName);
        removeMsg.setId(Message.REMOVE_MSG);
        
        //send a receive message to remote queue, wait on msgBox
        sendMessage(removeMsg);
        
        //No message was returned, wait until a message is placed in the message box
        if (msg == null) {
            try {
                if (logger.isDebugEnabled()) {
                    logger.debug(this.fromTaskName + " waiting on queue=" + this.toQueueName);
                }
                msg = (Message) waiter.waitOnMessage();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        return msg;
    }
    
    
    /**
     * Send message using system message queue.
     *  
     * @param msg
     */
    private void sendMessage(Message msg) {
        if ( sendQueue.isFull() ) {
            logger.error("sendQueue is full, discarding message=" + msg.getId() );
        }
        else {
            try {
                sendQueue.add( msg );
            }
            catch (Exception e) {
                logger.error("", e);
            }
        }
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
            if (logger.isDebugEnabled()) {
                logger.debug("adding message on port=" + this.name);
            }
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

    public int getSize() {
        return sendQueue.getSize();
    }

    
}
