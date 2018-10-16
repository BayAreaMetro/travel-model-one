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

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.io.PrintWriter;
import java.net.Socket;
import java.util.Date;
import java.util.HashMap;

/** 
 * Takes messages off the system send queue and sends them to other
 * DAF nodes.
 *
 * @author    Tim Heier
 * @version   1.0, 9/23/2002
 */

public class SocketSender implements Runnable {

    private Logger logger = Logger.getLogger("com.pb.common.daf");

    private QueueManager qManager = QueueManager.getInstance();
    
    private NodeDef[] nodeDefinitions;
    private BlockingFIFOQueue sendQueue;
    private long retryTime;
    private File connectionErrorFile; 

    private HashMap nodeToStreamMap = new HashMap();
    private int sendBufferSize = 262144;  //256K bytes

    /** 
     * Keep the default constructor from being called.
     */
    private SocketSender() { }


    public SocketSender(NodeDef[] nodeDefinitions, BlockingFIFOQueue sendQueue, int retryTime) {
        this(nodeDefinitions, sendQueue, retryTime, new File("C:/ConnectionErrorFile.txt")); 
    }    

    public SocketSender(NodeDef[] nodeDefinitions, BlockingFIFOQueue sendQueue, int retryTime, 
            File connectionErrorFile) {
        this.nodeDefinitions = nodeDefinitions;
        this.sendQueue = sendQueue;
        this.retryTime  = retryTime;
        this.connectionErrorFile = connectionErrorFile; 
    }


    /** 
     * Remove messages from the queue as they become available. First, create
     * the connections to each node on the local thread and not the thread which
     * created this class.
     */
    public void run() {
        //Open a socket connection to each remote node
        for (int i=0; i < nodeDefinitions.length; i++) {
            openConnection( nodeDefinitions[i] );
        }

        while (true) {
            Message msg = null;
            try {
                msg = (Message) sendQueue.remove();
            }
            catch (Exception e) {
                logger.error("exception while removing message from sendQueue", e);
            }
            
            send( msg );
        }
    }


    /** 
     * Send message to remote node. Delegate to a message handler based on
     * the message type.
     */
    public void send(Message msg) {
        boolean messageSent = false;

        while (! messageSent) {
            try {
                String nodeName = MessageHandler.getDestinationNode(msg);
                
//                if (logger.isDebugEnabled()) {
//                    logger.debug("SocketSender, destination node=" + nodeName + 
//                            " from="+msg.getSender()+" to="+msg.getRecipient());
//                }
                
                ObjectOutputStream oout = (ObjectOutputStream) nodeToStreamMap.get( nodeName );
                if (oout == null) {
                    logger.error("send() stream is null for nodeName = " + nodeName);
                    throw new Exception("Connection reset for nodeName="+nodeName+"?");
                }

                //Write the message type followed by the payload
                oout.writeObject( msg.getType() );

                MessageHandler handler = MessageHandler.getHandler( msg.getType() );
                handler.writeMessage( msg, oout );

                //Clean up
                oout.flush();
                oout.reset();
                messageSent = true;
            }
            catch (Throwable t) {
                //Remote host was probably not available or buffer may be full.
                //Or, bos is null if remote host was not available when client started.
                //handleError();
                logger.error(msg.sender + " could not send message to " + msg.getRecipient() ,  t);

                //If client terminated, try to open connection again
                if ( (t.getMessage().indexOf("Connection reset")) >= 0) {
                    logger.error("reconnecting to " + msg.getRecipient() );
                    
                    //Get nodeName from QueueManager, given a queueName
                    String nodeName = 
                        QueueManager.getInstance().getNodeNameforQueueName(msg.getRecipient());
                    
                    //Get nodeDef from DAF, given a nodeName 
                    NodeDef nodeDef = DAF.getNodeDef(nodeName);
                    
                    //Open connection
                    openConnection( nodeDef );
                }
            }
        }
    }


    /** 
     * Send message to remote node. Delegate to a message handler based on
     * the message type.
     */

    //TODO remove this method
//    public void broadcastSend(Message msg) {
//        boolean messageSent = false;
//
//        String nodeName = null;
//        ObjectOutputStream oout = null;
//        
//        while (! messageSent) {
//            try {
//
//                NodeDef[] nodeDefinitions = DAF.getRemoteNodeDefinitions();
//                
//                //Send message to each node
//                for (int i=0; i < nodeDefinitions.length; i++) {
//                
//                    nodeName = nodeDefinitions[i].name;
//                    
//                    logger.debug("broadcasting msg.id="+msg.getId()+", to node="+nodeName);
//
//                    oout = (ObjectOutputStream) nodeToStreamMap.get( nodeName );
//
//                    if (oout == null) {
//                        logger.error("broadcastSend() oout was null for nodeName = " + nodeName);
//                        throw new Exception("Connection reset?");
//                    }
//
//                    //Write the message type followed by the payload
//                    oout.writeObject( msg.getType() );
//    
//                    MessageHandler handler = MessageHandler.getHandler( msg.getType() );
//                    handler.writeMessage( msg, oout );
//
//                    //Clean up
//                    oout.flush();
//                    oout.reset();
//                }
//
//                messageSent = true;
//            }
//            catch (Throwable t) {
//                //Remote host was probably not available or buffer may be full.
//                //Or, bos is null if remote host was not available when client started.
//                //handleError();
//                logger.error("could not send message", t);
//
//                //If client terminated, try to open connection again
//                if ( (t.getMessage().indexOf("Connection reset")) >= 0) {
//                    logger.error( "reconnecting to " + msg.getRecipient() );
//                    openConnection( DAF.getNodeDef( msg.getRecipient() ) );
//                }
//            }
//        }
//    }


    /** 
     * Open a socket to a remote node.
     */
    private void openConnection( NodeDef aNode ) {
        //Convenience variables - saves typing
        String nodeName = aNode.name;
        String hostName = aNode.address;
        int remotePort = aNode.messagePort;

        int connectionAttempts = 0;

        aNode.connected = false;

        logger.info("connecting to " + nodeName + "=" + hostName + ":" + remotePort);

        while (! aNode.connected) {
            try {
                connectionAttempts++;
                Socket socket = new Socket( hostName, remotePort );
                logger.info("SocketSender got a connection to " + hostName + ":" + remotePort);

                //Change the size of SO_SNDBUF
                socket.setSendBufferSize( sendBufferSize );
                sendBufferSize = socket.getSendBufferSize();

                //Set buffer size equal to SO_SNDBUF
                ObjectOutputStream oout = new ObjectOutputStream (
                        new BufferedOutputStream( socket.getOutputStream(), sendBufferSize ));
                 logger.info("SocketSender created an ObjectOutputStream on " + hostName + ":" + remotePort);
                //Keep a reference to the socket
                nodeToStreamMap.put( nodeName, oout );

                aNode.connected = true;
                logger.info("SocketSender connected to " + nodeName + ", sendBufferSize=" + sendBufferSize);
            }
            catch (Throwable t) {
                logger.warn("SocketSender could not connect to " + nodeName, t);
            }

            //Wait for value of retryTime to try and connect again
            if (! aNode.connected) {

                //If last 10 tries failed then log an error
                if (connectionAttempts == 10) {
                    logger.error("could not connect to " + nodeName);
                    connectionAttempts = 0;
                    
                    // write a file, so the application knows to close down and try again
                    try {
                        logger.error("Writing error to: " + connectionErrorFile); 
                        PrintWriter writer = new PrintWriter(new FileWriter(connectionErrorFile));
                        writer.println("Could not establish connection " + new Date());
                        writer.close();
                    } catch (IOException e) {
                        logger.error("Could not write connectionErrorFile -- try connecting again");
                    }
                }

                try {
                    Thread.sleep( retryTime );
                }
                catch (Exception e) {
                    logger.error("interrupted while sleeping", e);
                }
            }
        }
    }

    
    public int getQueueSize() {
        return sendQueue.getSize();
    }

    
    public boolean isQueueFull() {
        return sendQueue.isFull();
    }

}
