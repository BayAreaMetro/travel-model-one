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
package com.pb.common.logging;

import org.apache.log4j.spi.LoggingEvent;

import java.net.Socket;
import java.net.SocketException;
import java.io.*;
import java.text.SimpleDateFormat;
import java.text.Format;

/**
 * This class represents a connection from a client running Log4j.
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2005
 *
 */
public class LogClientHandler implements Runnable
{
    private Socket socket;
    private boolean logToConsole;

    //Used to print messages to the LogServer file
    private PrintWriter serverLogWriter = null;

    //Used to log client messages
    private PrintWriter clientLogWriter = null;


    public LogClientHandler(Socket socket, PrintWriter serverLogWriter, PrintWriter clientLogWriter,
                            boolean logToConsole) {
        this.socket = socket;
        this.logToConsole = logToConsole;
        this.serverLogWriter = serverLogWriter;
        this.clientLogWriter = clientLogWriter;

        new Thread(this).start();
    }

    public void run() {

        ObjectInputStream inStream = null;
        try {
            inStream = new ObjectInputStream(new BufferedInputStream(socket.getInputStream()));

            String remoteHost = socket.getRemoteSocketAddress().toString();
            try {
                remoteHost = socket.getInetAddress().getHostName();
            }
            catch (Exception e) {
                //do nothing remoteHost will contain the ip address instead of the host name
            }
            //Format date to look like Log4j timestamp
            Format formatter = new SimpleDateFormat("dd-MMM-yyyy HH:mm:sss");

            while (true)
            {
                LoggingEvent event = (LoggingEvent)inStream.readObject();
                String ts = formatter.format(event.timeStamp);
                String str = ts + ", " + remoteHost + ", [" + event.getThreadName() + "], " +
                                event.getLevel().toString() + ", " + event.getMessage();
                clientLogWriter.println(str);
                clientLogWriter.flush();

                if (logToConsole) {
                    System.out.println(str);
                }
            }
        }
        catch (SocketException e) {
            if (e.getMessage().contains("Connection reset"))
            {
                //do nothing, don't print the message, normal condition
            }
            else
            {
                //something unexpected happened so print the exception message and exit
                serverLogWriter.println(e.toString());
                serverLogWriter.println("[LogClientHandler] something unexpected happened exiting, client="+
                                        socket.getRemoteSocketAddress());
                return;
            }
        }
        catch (Exception e) {
            serverLogWriter.println(e.toString());
            serverLogWriter.println("[LogClientHandler] something unexpected happened exiting, client="+
                                        socket.getRemoteSocketAddress());
            return;
        }
        finally {
            if (inStream != null) {
                try {
                    inStream.close();
                } catch (IOException e) {
                    //swallow it
                }
            }
        }
    }
}
