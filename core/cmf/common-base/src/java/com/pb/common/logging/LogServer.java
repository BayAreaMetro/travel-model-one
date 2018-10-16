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

import com.pb.common.util.CommandLine;

import java.net.ServerSocket;
import java.net.Socket;
import java.io.PrintWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.text.Format;
import java.text.SimpleDateFormat;
import java.util.Date;

/**
 * This class listens for log events on a socket connection from a Log4j
 * client. The Log4J client should use the SocketAppender and specify
 * the IP address and port that this process is running on.
 *
 * This is a self-running class and will start an internal thread from
 * the constructor. See the example in main() method below.
 *
 * The default port number is 7001. This value can be supplied on the
 * command-line if a different value is desired. It must match the port
 * number used by the SocketAppender in the log4j.xml file.
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2005
 *
 */
public class LogServer implements Runnable
{
    //Defaults
    public static int LOG4J_PORT  = 7001;
    public static String CLIENTLOG_NAME = "ClientErrors.log";

    //Used by LogServer class to write messages - passed from caller in constructor
    PrintWriter serverLogWriter = null;

    //Used to log client messages
    PrintWriter clientLogWriter = null;

    //Instance variables
    public int log4jPort;
    public boolean logToConsole;
    public static ServerSocket serverSocket;

    //Format date to look like Log4j timestamp
    Format formatter = new SimpleDateFormat("dd-MMM-yyyy HH:mm:ss:SSS");

    /**
     * This is a self-running class and an internal thread is started to
     * run the class.
     *
     */
    public LogServer(boolean logToConsole, int log4jPort, String logFileName, boolean shouldAppend,
                     PrintWriter serverLogWriter) throws IOException
    {
        this.logToConsole = logToConsole;
        this.log4jPort = log4jPort;

        //use serverLogWriter provided if not null, otherwise send general logging to console
        if (serverLogWriter != null) {
            this.serverLogWriter = serverLogWriter;
        }
        else {
            this.serverLogWriter = new PrintWriter(System.out, true);
        }

        //open client log file
        clientLogWriter = new PrintWriter(new FileWriter(logFileName, shouldAppend), true);

        try {
            //listen to the port specified
            serverSocket = new ServerSocket(log4jPort);
            new Thread(this).start();
        }
        catch(Exception e) {
            serverLogWriter.println(e.toString());
        }
    }

    /**
     * Convenience constructor used when a serverLogWriter is not provided.
     *
     */
    public LogServer(boolean logToConsole, int portNumber, String logFileName)
           throws IOException {

        this(logToConsole, portNumber, logFileName, false, null);
    }

    /**
     * Convenience constructor used when default values are acceptable.
     *
     */
    public LogServer() throws IOException {
        this(false, LogServer.LOG4J_PORT, LogServer.CLIENTLOG_NAME, false, null);
    }

    /**
     * Convenience method to print messages to the Server Log file and the console
     * 
     * @param message
     */
    public void printMessage(String message) {

        //Add date/time to file entry
        String t = formatter.format(new Date());
        serverLogWriter.println(t + ", " + message);

        if (logToConsole)
            System.out.println(message);
    }

    /**
     * Provides access to underlying log file.
     *
     * @param message
     * @return true if message was written with no exception, otherwise false
     */
    public boolean log(String message) {

        boolean result = false;
        try {
            //Add date/time to file entry
            String t = formatter.format(new Date());
            clientLogWriter.println(t + ", " + message);
            result = true;
        }
        catch (Exception e) {
            serverLogWriter.println(e);
        }
        return result;
    }

    //Socket server is running on a separate thread
    public void run() {
        try {
            printMessage("LogServer listening on " + log4jPort);

            while(true) {
                Socket socket = serverSocket.accept();
                printMessage("accepted connection from: " + socket.getRemoteSocketAddress());

                //each handler will run on a separate thread
                LogClientHandler handler =
                        new LogClientHandler(socket, serverLogWriter, clientLogWriter, logToConsole);
            }
        }
        catch(Exception e) {
            serverLogWriter.println(e.toString());
        }
    }

    /**
     * Use this method to run the LogServer class from the command-line in
     * a stand alone Java VM.
     *
     * Starts with default values:
     * usage: java LogServer
     *
     * Configures all values: 
     * usage: java LogServer -log4jPort 7001 -fileName ClientErrors.log -logToConsole
     *
     * @param args supplied by system
     */
    public static void main(String args[])
    {
        CommandLine cmdline = new CommandLine(args);
 
        //Look for "log4jPort" value on command-line
        int log4jPort = LogServer.LOG4J_PORT;
        if (cmdline.exists("log4jPort")) {
            String portStr = cmdline.value("log4jPort");
            if (portStr.length() == 0) {
                System.err.println("Error, value for \"log4jPort\" eg. -log4jPort 7001");
                return;
            }
            log4jPort = Integer.parseInt(cmdline.value("log4jPort"));
        }

        //Look for "fileName" value on command-line
        String logFile = LogServer.CLIENTLOG_NAME;
        if (cmdline.exists("fileName")) {
            String fileStr = cmdline.value("fileName");
            if (fileStr.length() == 0) {
                System.err.println("Error, missing value for \"fileName\" eg. -fileName ClientError.log");
                return;
            }
            logFile = cmdline.value("fileName");
        }
 
        //Look for "LogToConsole" flag on command-line
        boolean logToConsole = false;
        if (cmdline.exists("logToConsole")) {
            logToConsole = true;
        }

        try {
            LogServer server = new LogServer(logToConsole, log4jPort, logFile);
        } catch (IOException e) {
            e.printStackTrace();
        }

    }
}
