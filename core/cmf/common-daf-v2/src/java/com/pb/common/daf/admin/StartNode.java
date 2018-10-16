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
package com.pb.common.daf.admin;

import com.pb.common.daf.ApplicationDef;
import com.pb.common.daf.ApplicationManager;
import com.pb.common.daf.DAF;
import com.pb.common.matrix.MatrixIO32BitJvm;
import com.pb.common.matrix.MatrixType;
import com.pb.common.util.Convert;
import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.ServerSocket;
import java.net.Socket;

/** This class loads the DAF framework. No applications are loaded 
 * this way.
 *
 * @author    Tim Heier
 * @version   1.0, 9/28/2002
 */
public class StartNode {

    private static Logger logger = Logger.getLogger("com.pb.common.daf.admin");
    
    private int adminPort;

    // turn this on to read/write TP+ matrices using a 32-bit server
    private static MatrixIO32BitJvm ioVm32Bit = null;
    
    
    public StartNode() {
        DAF.getInstance();
        this.adminPort = DAF.getNodeDef().getAdminPort();

        // starts server for reading/writing TP+ matrices
        boolean useMatrixServer = DAF.getUse32BitMatrixIoServer(); 
        if (useMatrixServer) {
        	start32BitMatrixIoServer(MatrixType.TPPLUS, 0); 
        }
    }

    
    public void listen() {
        
        logger.info("Listening on administrative port=" + adminPort);
        
        //Create a server socket
        ServerSocket ss = null;
        try {
            ss = new ServerSocket(adminPort);
        } catch (IOException e) {
            logger.error("creating server socket", e);
            System.exit(1);
        }
        
        while(true) {
            // Wait for connection from client.
            Socket socket;
            try {
                socket = ss.accept();
                logger.info("ServerSocket has accepted the connection from CommandProcessor");
            } catch (IOException e) {
                logger.error("during socket accept", e);
                continue;
            }
            //Read commands
            try {
                BufferedReader rd = 
                    new BufferedReader(new InputStreamReader(socket.getInputStream()));
                logger.info("StartNode class has successfully created a BufferedReader");
                
                //Read only the first line with the command on it
                String str = rd.readLine();
                logger.info("The following line has just been read in from the socket: " + str);
                
                if (str.equalsIgnoreCase("startcluster")) {
                    startCluster(rd);
                }
                else if (str.equalsIgnoreCase("startapplication")) {
                    startApplication(rd);
                }
                else if (str.equalsIgnoreCase("stopapplication")) {
                    stopApplication(rd);
                }
                else if (str.equalsIgnoreCase("stopnode")) {
                    stopNode(rd);
                }
                else {
                    logger.error("unknown command = " + str);
                }
                rd.close();
                socket.close();
            } catch (Exception e) {
                logger.error("exception during listen loop", e);
            }
            
        }
        
    }
    
    
    private void startCluster(BufferedReader rd) {
        String str;
        try {
            while ((str = rd.readLine()) != null) {
                //Shouldn't be any more input
            }
            
            //The startNode method will establish the network connections
            DAF.startNode();
            
        } catch (Exception e) {
            logger.error("startcluster command failed", e);
        }
        
    }

    
    private void startApplication(BufferedReader rd) {
        String str;
        String base64String = "";
                
        try {
            //Read all available lines
            while ((str = rd.readLine()) != null) {
                base64String += str;
            }
            ApplicationDef appDef = (ApplicationDef) Convert.toObject(base64String);
            logger.info("Received startApplication=" + appDef.getName());
//            logger.debug("base64String = " + base64String);
            
            logger.info("appDef="+appDef.toString());
            ApplicationManager.getInstance().startApplication(appDef);

        } catch (IOException e) {
            logger.error("startapplication command failed", e);
        }
    }
    
    
    private void stopApplication(BufferedReader rd) {
        String str;
        String base64String = "";
        
        try {
            //Read all available lines
            while ((str = rd.readLine()) != null) {
                base64String += str;
            }
            ApplicationDef appDef = (ApplicationDef) Convert.toObject(base64String);
            logger.info("Received stopApplication=" + appDef.getName());
//            logger.debug("base64String = " + base64String);
            
            logger.info("appDef="+appDef.toString());
            ApplicationManager.getInstance().stopApplication(appDef);

        } catch (IOException e) {
            logger.error("stopapplication command failed", e);
        }
    }

    
    // can do other clean-up too
    private void stopNode(BufferedReader rd) {
        // stops server for reading/writing TP+ matrices
        stop32BitMatrixIoServer(0); 
    }


    /**
     * Starts a 32-bit server to read/write TP+ matrices
     * 
     * @param mType type of matrix 
     * @param portOffset port offset
     */
    private static void start32BitMatrixIoServer(MatrixType mType, int portOffset)
    {
    	// start the matrix I/O server process
    	ioVm32Bit = MatrixIO32BitJvm.getInstance();
    	ioVm32Bit.setSizeInMegaBytes(768); 
    	ioVm32Bit.startJVM32(portOffset);

    	// establish that matrix reader and writer classes will use the RMI versions
    	// for TPPLUS format matrices
    	ioVm32Bit.startMatrixDataServer(mType);
    	logger.info("matrix data server 32 bit process started.");

    }

    /**
     * Stops a 32-bit server used to read/write TP+ matrices
     * 
     * @param portOffset port offset
     */
    public static void stop32BitMatrixIoServer(int portOffset)
    {
    	
    	if (ioVm32Bit != null) {
    		// stop the matrix I/O server process
    		ioVm32Bit.stopMatrixDataServer();
	
    		// close the JVM in which the RMI reader/writer classes were running
    		ioVm32Bit.stopJVM32(portOffset);
    		logger.info("matrix data server 32 bit process stopped.");
    	}
    }
    

    
    /**
     * Used to run a node from the command-line.
     * 
     * @param args
     */
    public static void main (String[] args) {
        StartNode node = new StartNode();
        node.listen();
    }
    
}