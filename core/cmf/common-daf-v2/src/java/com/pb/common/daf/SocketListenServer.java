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

import java.net.ServerSocket;
import java.net.Socket;
import org.apache.log4j.Logger;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 6/18/2002
 */

public class SocketListenServer implements Runnable {

    private Logger logger = Logger.getLogger("com.pb.common.daf");

    private int id = 0;
    private int listenPort;

    public SocketListenServer(int listenPort) {
        this.listenPort = listenPort;
    }


    /**
    * Remove log events from queue as they become available.
    */
    public void run() {

        try{
            ServerSocket ss = new ServerSocket( listenPort );

            while (true) {
                logger.info( "Listening for connections on port=" + listenPort);
                Socket socket = ss.accept();
                id++;

                String workerName = "SocketConnectionWorker_" + id;
                Thread t = new Thread(new SocketConnectionWorker(socket), workerName );
                //t.setPriority(Thread.NORM_PRIORITY+1);
                t.start();
            }
        }
        catch(Exception e) {
            logger.error("", e);
        }
    }

}
