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

import java.io.File;

import org.apache.log4j.Logger;

import com.pb.common.util.BlockingFIFOQueue;

/** This class manages the low leverl details of the TCP connections to other
 *  DAF nodes. It also sends and receives messages over TCP connections. *
 *
 * @author    Tim Heier
 * @version   1.0, 5/18/2002
 */
public class TCPTransport {
    static Logger logger = Logger.getLogger(TCPTransport.class);
    //Set from external properties
    private int connectionRetryTime;
    private int messagePort;
    private NodeDef[] remoteNodeDefs;
    private File connectionErrorFile; 

    private SocketListenServer  socketServer;
    private SocketSender sendWorker;

    private static TCPTransport instance = new TCPTransport();


    private TCPTransport() {
        readProperties();
        startSocketListenServer();
        startSocketSender();
    }


    public static TCPTransport getInstance() {
        if(logger.isDebugEnabled()) logger.debug("Getting instance of TCPTransport");
        return instance;
    }


    private void readProperties() {
        connectionRetryTime = DAF.connectionRetryTime;
        messagePort = DAF.getNodeDef().messagePort;
        remoteNodeDefs = DAF.getRemoteNodeDefinitions();
        connectionErrorFile = DAF.connectionErrorFile; 
    }

    private void startSocketListenServer() {
        socketServer = new SocketListenServer( messagePort );

        //Start on separate thread
        Thread server = new Thread( socketServer, "SocketConnectionServer" );
        server.start();
    }


    private void startSocketSender() {
        QueueManager qManager = QueueManager.getInstance();
        BlockingFIFOQueue sendQueue = qManager.getSystemSendQueue();

        sendWorker = new SocketSender(remoteNodeDefs, sendQueue, connectionRetryTime, connectionErrorFile);

        //Start sendWorker as separate thread
        Thread sender = new Thread( sendWorker, "SocketSender" );
        sender.start();
    }

}
