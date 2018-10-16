package com.pb.models.ctramp;

import gnu.cajo.invoke.Remote;

import java.lang.reflect.InvocationTargetException;
import java.net.MalformedURLException;
import java.rmi.ConnectIOException;
import java.rmi.NotBoundException;
import java.rmi.RemoteException;
import java.io.IOException;

import org.apache.log4j.Logger;

/**
 * User: Jim
 * Date: Jul 3, 2008
 * Time: 2:27:02 PM
 *
 * Utility class for applying remote methods of various types
 *
 */

public class UtilRmi implements java.io.Serializable {

    private transient Logger logger = Logger.getLogger(UtilRmi.class);
    private String connectString;

    private static int MAX_RETRY_COUNT = 100; 
    private static int MAX_RETRY_TIME = 1000; // milliseconds 
    
    
    public UtilRmi(String connectString) {
        this.connectString = connectString;
    }



    public Object method( String name, Object[] args ) {

        int connectExceptionCount = 0;
        
        Object itemObject = null;
        Object returnObject = null;

        
        while ( connectExceptionCount < MAX_RETRY_COUNT ) {

            try {
                itemObject = Remote.getItem(connectString);
                break;
            }
            catch (ConnectIOException e) {
                
                try {
                    Thread.currentThread().wait( MAX_RETRY_TIME );
                } catch (InterruptedException e1) {
                    // TODO Auto-generated catch block
                    e1.printStackTrace();
                }
                
                connectExceptionCount++;
                
            }
            catch (RemoteException e) {
                logger.error ("RemoteException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (MalformedURLException e) {
                logger.error ("MalformedURLException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (NotBoundException e) {
                logger.error ("NotBoundException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (IOException e) {
                logger.error ("IOException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (ClassNotFoundException e) {
                logger.error ("ClassNotFoundException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (InstantiationException e) {
                logger.error ("InstantiationException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (IllegalAccessException e) {
                logger.error ("IllegalAccessException exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            catch (UnsatisfiedLinkError e) {
                logger.error ("UnsatisfiedLinkError exception making RMI method call: " + connectString + "." + name + "().", e);
                throw new RuntimeException();
            }
            
        }
            
        
        if ( connectExceptionCount > 0 ) {
            logger.warn ("UtilRmi.method() timed out " + connectExceptionCount + "times connecting to: " + connectString + "." + name + "()." );
        }
        if ( connectExceptionCount == MAX_RETRY_COUNT ) {
            logger.error ("UtilRmi.method() connection was never made." );
            throw new RuntimeException();
        }

        
        
        try {
            returnObject = Remote.invoke( itemObject, name, args );
        }
        catch (InvocationTargetException e) {            
            logger.error ("InvocationTargetException exception making RMI method call.");
            if ( connectString != null )
                logger.error ("connectString = " + connectString + "." + name + "().");
            if ( name != null )
                logger.error ("name = " + name + "().");
            e.printStackTrace();
            throw new RuntimeException();
        }
        catch (Exception e) {
            logger.error ("Exception exception making RMI method call: " + connectString + "." + name + "().", e);
            throw new RuntimeException();
        }
            
        
        
        return returnObject;
        
    }
        

}
