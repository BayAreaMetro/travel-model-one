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

import org.apache.log4j.Logger;


/** 
 * Represents a task waiting on a message to be added to a MessageQueue.
 *
 * @author    Tim Heier
 * @version   1.0, 3/4/2004
 */
public class Waiter {

    protected static Logger logger = Logger.getLogger("com.pb.common.daf");
    
    protected Message removeMessage;
    protected BlockingFIFOQueue msgBox = new BlockingFIFOQueue(1);

    
    /**
     * Constructor used by a local task waiting on a message queue
     */
    public Waiter() {
        this.removeMessage = null;
    }
    
    
    /**
     * Constructor used by a remote task waiting on a message queue
     * 
     * @param removeMessage the original remove message sent by the remote task
     */
    public Waiter(Message removeMessage) {
        this.removeMessage = removeMessage;
    }

    
    public Message waitOnMessage() throws InterruptedException {
        Message msg = (Message) msgBox.remove();
        return msg;
    }
    
    
    public void notifyWithMessage(Message msgFromQueue) throws InterruptedException {
        
        //Waiting task is a local task and waiting on the msgBox queue
        if (removeMessage == null) {
            msgBox.add(msgFromQueue);
        }
        //Waiting task is a remote task
        else {
            try {
                Message returnMessage = new UncompressedMessage(Message.RETURN_MSG);
                //Swap sender,receiver 
                returnMessage.recipient = removeMessage.getSender();
                returnMessage.sender = msgFromQueue.getRecipient();
                returnMessage.setValue("message", msgFromQueue);
                
                //Send msgFromQueue wrapped in a new returnMessage
                BlockingFIFOQueue sendQueue = QueueManager.getInstance().getSystemSendQueue();
                sendQueue.add(returnMessage);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            
        }
        
                
    }
}
