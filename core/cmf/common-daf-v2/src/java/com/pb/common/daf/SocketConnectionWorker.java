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

import java.io.BufferedInputStream;
import java.io.ObjectInputStream;
import java.net.Socket;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 6/18/2002
 */
public class SocketConnectionWorker implements Runnable {

    Logger logger = Logger.getLogger("com.pb.common.daf");


    private ObjectInputStream oin;
    private Socket socket;
    private String sourceIP;
    private String sourceName;

    private int receiveBufferSize = 262144;  //256K bytes

    private MessageFactory messageFactory = MessageFactory.getInstance();
    private QueueManager queueManager = QueueManager.getInstance();

    public SocketConnectionWorker(Socket socket) {
        this.socket = socket;
    }


    public void run() {
        this.sourceIP = socket.getInetAddress().getHostAddress();
        this.sourceName = socket.getInetAddress().getHostName();

        try {
            //Change the size of SO_SNDBUF
            socket.setReceiveBufferSize( receiveBufferSize );
            receiveBufferSize = socket.getReceiveBufferSize();

            logger.info(Thread.currentThread().getName() + ", connection from name=" + sourceName + ", ip="+ sourceIP + 
                        ", receiveBufferSize=" + receiveBufferSize);
            
            //Create a buffered object stream equal to size of SO_SNDBUF
            oin = new ObjectInputStream(
                    new BufferedInputStream( socket.getInputStream(), receiveBufferSize ));
        }
        catch (Exception e) {
            logger.error("", e);
        }

        while (true) {
            try {
                while (true) {
                    MessageType type = (MessageType) oin.readObject();

                    MessageHandler handler = MessageHandler.getHandler( type );
                    handler.readMessage( oin );
                }
            }
            catch (java.net.SocketException e) {
                logger.error("SocketException occurred reading from " + sourceName, e);

                //Client probably terminated thread, exit thread
                if ( (e.getMessage().indexOf("Connection reset")) >= 0) {
                    logger.error("SocketConnection worker for " + sourceName + " exiting (1)");
                    return;
                }
            }
            catch (Exception e) {
                logger.error("exception occurred reading from " + sourceName, e);

                //Client probably terminated thread, exit thread
                if ( (e.getMessage().indexOf("Connection reset")) >= 0) {
                    logger.error("SocketConnection worker for " + sourceName + " exiting (2)");
                    return;
                }
            }
        }
    }

}
