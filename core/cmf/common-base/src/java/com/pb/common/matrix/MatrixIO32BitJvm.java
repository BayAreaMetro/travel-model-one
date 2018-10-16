package com.pb.common.matrix;

import gnu.cajo.invoke.Remote;
import java.io.Serializable;
import java.util.HashMap;
import java.util.concurrent.TimeUnit;

import org.apache.log4j.Logger;

import com.pb.common.util.DosCommand;


public class MatrixIO32BitJvm implements Serializable {

    private Logger logger = Logger.getLogger( MatrixIO32BitJvm.class );

    private static MatrixIO32BitJvm instance = new MatrixIO32BitJvm();
    private static final Object lock = new Object();
    
    RmiMatrixReader rmiReader = null;
    RmiMatrixWriter rmiWriter = null;

    static String serverClass = "com.pb.common.matrix.RemoteMatrixDataServer";
    static String hostName = "localhost";
    static String port = "1198";
    
    private static HashMap<Integer,DosCommand> dosCmdMap = new HashMap<Integer,DosCommand>();
    private static ConsoleWatcher consoleWatcher = null;
    private static boolean watching = true;
    
    private int megaBytes = -1;
    
    
    private MatrixIO32BitJvm() {
    }
    
    /** Returns an instance to the singleton.
     */
    public static MatrixIO32BitJvm getInstance() {
        return instance;
    }
    
    /** Set size of JVM in megabytes
     */
    public void setSizeInMegaBytes( int mBytes ) {
        megaBytes = mBytes;
    }
    
    /** Set class to run in new 32 bit JVM
     */
    public void setClassToRun( String className ) {
        MatrixIO32BitJvm.serverClass = className;
    }
    
    /** Set host to run on
     */
    public void setHostToRun( String hostName ) {
        MatrixIO32BitJvm.hostName = hostName;
    }
    
    /** Set port to run on
     */
    public void setPortToRun( String port ) {
        MatrixIO32BitJvm.port = port;
    }
    
    public int getPortToRun() {
        return Integer.parseInt( MatrixIO32BitJvm.port );
    }
    
    
    public void startJVM32() {
        startJVM32( -1 );
    }

    public void startJVM32(int myPortOffset) {
        
        synchronized(lock) {

            // multiple calls on this method for any given index should not execute if a VM already exists
            if ( ! dosCmdMap.containsKey( myPortOffset ) ) {
                
                DosCommand dosCmd = new DosCommand();
                watching = true;
                consoleWatcher = new ConsoleWatcher();
                consoleWatcher.start();
                
                // get the port number to be used by RMI from the DosCommand object that was set by -Dvar on the command line.
                // setting port number on command line allows multiple VMs to be created on a single host to use RMI to communicate with localhost through different ports.
                // if none was set on command line, use the default MatrixIO32BitJvm.port, which could have been changed by the setPortToRun() method.
                String java32Port = dosCmd.getJava32Port();
                if ( java32Port == null )
                    java32Port = MatrixIO32BitJvm.port;

                if ( myPortOffset > 0 )
                    java32Port = Integer.toString( (Integer.parseInt(java32Port) + myPortOffset) );

                MatrixIO32BitJvm.port = java32Port;
                
                
                try {
                    
                    String[] JRE_ARGS = {
                        "-Xms" + (megaBytes < 0 ? 512 : megaBytes) + "m",
                        "-Xmx" + (megaBytes < 0 ? 512 : megaBytes) + "m",
                        MatrixIO32BitJvm.serverClass,
                        "-hostname",
                        MatrixIO32BitJvm.hostName,
                        "-port",
                        MatrixIO32BitJvm.port 
                    };
    
                    // this is a long running process that doesn't return
                    dosCmd.runJavaClassIn32BitJRE( JRE_ARGS );
                }
                catch ( Exception e ) {
                    logger.error ( "caught an exception executing the dos command to start 32 bit java.", e );
                    throw new RuntimeException();
                }
                
                
                // the following issues a remote method call to the RemoteMatrixdataServer object started in the 32 bit JRE.
                // if an exception is caught, likely because remopte 32 bit object has not yet been bound, there is a retry (up to 3 retries) 
                // the purpose is to make sure the remote method call is accepted before returning from this method
                // if the connection still fails after 3 seconds, this method throws a runtime exception.
                String connectString = "//" + MatrixIO32BitJvm.hostName + ":" + MatrixIO32BitJvm.port + "/" + MatrixIO32BitJvm.serverClass;

                int count = 0;
                boolean serverWaiting = true;
                while ( serverWaiting ) {
                    Object[] objArray = {};
                    try {
                    	
                        try {
                            TimeUnit.SECONDS.sleep(5);
                            count++;
                        }
                        catch (InterruptedException e1)
                        {
                            logger.error( "interrupted exception caught while waitig 5 seconds to try connecting to 32 bit remote method", e1 );
                            throw new RuntimeException();
                        }

                        Object obj = Remote.getItem(connectString);
                        String connectedString = (String)Remote.invoke(obj, "connectionTest", objArray);
                        if ( connectedString.equalsIgnoreCase("RemoteMatrixDataServer connected") )
                            serverWaiting = false;
                        else
                            logger.error( "remote method call made with: " + connectString + ", returned: " + connectedString );
                            
                    }
                    catch (Exception e) {            
                    	logger.error( "exception caught trying connectionTest with remote 32 bit process, with connectString = " + connectString, e );
                    }

                    if ( count == 5 ) {
                    	logger.error( "Stopping after 3 tries to bind to server: " + connectString + "." );
                    	logger.error( "Unable to connect to RemoteMatrixDataServer process started in 32 bit JRE." );
                        throw new RuntimeException();
                    }
                }

                dosCmdMap.put( myPortOffset, dosCmd );

            }

        }
        
    }
    

    public void startMatrixDataServer( MatrixType type ) {

        synchronized(lock) {

            String connectString = String.format("//%s:%d/%s", MatrixIO32BitJvm.hostName, Integer.parseInt(MatrixIO32BitJvm.port), MatrixIO32BitJvm.serverClass);

            //These lines will remote any matrix reader call
            while ( rmiReader == null ) {
                rmiReader = new com.pb.common.matrix.RmiMatrixReader();
            }
            rmiReader.setConnectString( connectString );
            MatrixReader.setReaderClassForType( type, rmiReader);
            
            //These lines will remote any matrix writer call
            int count=0;
            while ( rmiWriter == null ) {
                logger.info( "creating RmiMatrixWriter for: " + connectString + ", count=" + count + ", " + Thread.currentThread().getName() );
                rmiWriter = new com.pb.common.matrix.RmiMatrixWriter();
                rmiWriter.setConnectString( connectString );
                logger.info( rmiWriter.testRemote("created RmiMatrixWriter for: " + connectString + ", count=" + count + ", " + Thread.currentThread().getName()) );
                count++;
            }
            MatrixWriter.setWriterClassForType( type, rmiWriter);
            
        }
        
    }
    

    public void stopMatrixDataServer() {
        
        synchronized(lock) {

            //These lines will stop remote matrix reader calls
            MatrixReader.clearReaderClassForType(MatrixType.TPPLUS);
            rmiReader = null;
            
            //These lines will remote any matrix writer call
            MatrixWriter.clearWriterClassForType(MatrixType.TPPLUS);
            rmiWriter = null;
            
        }
        
    }
    

    public void stopJVM32() {
        stopJVM32( -1 );
    }

    public void stopJVM32( int myPortOffset ) {
        
        synchronized( lock ) {

            if ( dosCmdMap.containsKey( myPortOffset ) ) {
                watching = false;
                dosCmdMap.get(myPortOffset).destroy();
                dosCmdMap.remove( myPortOffset );
                consoleWatcher = null;
            }
            
        }
        
    }
    



    class ConsoleWatcher extends Thread implements Serializable
    {
        ConsoleWatcher() {
        }
        
        public void run() {
            
            while ( watching ) {
                
                synchronized ( lock ) {
                
                    for ( DosCommand dosCmd : dosCmdMap.values() ) {
                        String consoleOutput = dosCmd.getConsoleOutput();
                        if ( consoleOutput.length() > 0 )
                            System.out.print( consoleOutput );                    
                        
                        String errorOutput = dosCmd.getErrorOutput();
                        if ( errorOutput.length() > 0 )
                            System.out.print( errorOutput );
                    }
                    
                }
                
            }
            
        }
    }

}

