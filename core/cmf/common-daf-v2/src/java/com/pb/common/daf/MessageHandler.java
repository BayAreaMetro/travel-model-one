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

import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;

/** 
 * A MessageHandler is responsible for reading and writing messages to an
 *  underlying stream.
 *
 * @author    Tim Heier
 * @version   1.0, 7/12/2002
 */
public abstract class MessageHandler {

    protected static Logger logger = org.apache.log4j.Logger.getLogger(MessageHandler.class);

    private static CompressedMessageHandler compressedHandler = new CompressedMessageHandler();
    private static UncompressedMessageHandler uncompressedHandler = new UncompressedMessageHandler();

    private static QueueManager qManager = QueueManager.getInstance();
    

    /**
     * Factory method which returns the correct handler based on the type of
     * message.
     */
    public static MessageHandler getHandler(MessageType type) {

        MessageHandler handler = null;

        if ( type.equals(MessageType.UNCOMPRESSED) ) {
            handler = uncompressedHandler;
        }
        else if ( type.equals(MessageType.COMPRESSED) ) {
            handler = compressedHandler;
        }

        return handler;
    }


    public void writeMessage(Message msg, ObjectOutputStream oout) throws Exception {
        if (logger.isDebugEnabled()) {
            logger.debug("MessageHandler, sending message id=" + msg.getId() + 
                        " from="+msg.getSender()+" to="+ msg.getRecipient());
        }
        writedMessageBytes( msg, oout );
    }


    public void readMessage(ObjectInputStream oin) throws Exception {
        Message msg = readMessageBytes( oin );

        if (logger.isDebugEnabled()) {
            logger.debug("MessageHandler, received message id=" + msg.getId() + 
                        " from="+msg.getSender()+" to="+msg.getRecipient());
        }
        processMessage( msg );
    }

    
    /**
     * Determine the desitnation node name based on:
     * 
     * MSG.Id
     * MSG.sender
     * MSG.recipient 
     * 
     */
    public static String getDestinationNode(Message msg) {
        String nodeName = null;
        
        //If message is the result of remote "remove" then send it back to a task
        if (msg.getId().equals(Message.RETURN_MSG)) {
            nodeName = TaskManager.getNodeNameForTaskName( msg.getRecipient() ); 
        }
        //Lookup node name based on a desitnation queue name - this is the normal way
        else {
            nodeName = qManager.getNodeNameforQueueName( msg.getRecipient() );
        }
        
        return nodeName;
    }
    
    
    /** 
     * Handles a message by looking at the message id. Special logic is
     * implemented to handle:
     * 
     * 1. REMOVE_MSG
     * 2. RETURN_MSG 
     * 
     * This method is called immediately after a message is read from a message
     * stream. 
     */
    protected void processMessage(Message msg) {
        String toQueueName = msg.getRecipient();
        if(logger.isDebugEnabled()) {
            logger.debug("Message Handler,processing msg," + msg.getId()+", from " + msg.getSender() + " to " + msg.getRecipient());
         }
        //Process a remote messageQueue.remove() - this code is executed on the 
        //remote node
        if (msg.getId().equals(Message.REMOVE_MSG) ) {
            processRemoveMsg(msg, toQueueName);
        }
        //Process a returned message from a remote receive - this code is executed
        //on the client node
        else if (msg.getId().equals(Message.RETURN_MSG) ) {
            processReturnMsg(msg);
        }
        else {
            MessageQueue msgQueue = qManager.getMessageQueue(msg.getRecipient());
            try {
                msgQueue.add(msg);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        
    }
    
    
    /**
     * @param msg
     * @param toQueueName
     */
    private void processRemoveMsg(Message msg, String toQueueName) {
        
        //Get a reference to the requested MessageQueue
        MessageQueue messageQueue = qManager.getMessageQueue(toQueueName);
        
        Message msgFromQueue = null;
        
        //This block optimizes the case when there are messages on the queue. In 
        //this case, a waiter does not have to be created (the else block)
        synchronized (messageQueue) {

            //If there are no messages on queue then create a waiter and add to queue
            if (messageQueue.isEmpty()) {
                Waiter waiter = new Waiter(msg);
                messageQueue.add(waiter);
            }
            //There are messages on queue, get next message 
            else {
                msgFromQueue = messageQueue.remove();
            }
        }

        //Note: The following code could be done in the else block above but it's
        //      done here to save the amount of code in the synchronized block. 

        //A message was available on the queue, send it back wrapped in a RETURN_MSG
        if (msgFromQueue != null) {
            try {
                Message returnMessage = new UncompressedMessage(Message.RETURN_MSG);
                //Swap sender,receiver 
                returnMessage.recipient = msg.getSender();
                returnMessage.sender = msg.getRecipient();
                returnMessage.setValue("message", msgFromQueue);
                
                //Send msgFromQueue wrapped in a new returnMessage
                BlockingFIFOQueue sendQueue = qManager.getSystemSendQueue();
                sendQueue.add(returnMessage);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }


    /**
     * Called when a RETURN_MSG comes back from a remote queue.
     * 
     * @param msg
     */
    private void processReturnMsg(Message msg) {
        Port port = PortManager.getInstance().findPort(msg.getRecipient(), msg.getSender());

        //Extract the original message and add it to the message box of the waiting port
        port.addMessage((Message)msg.getValue("message"));
    }


    abstract protected void writedMessageBytes(Message msg, ObjectOutputStream oout) throws Exception;
    abstract protected Message readMessageBytes(ObjectInputStream oin) throws Exception;

}
