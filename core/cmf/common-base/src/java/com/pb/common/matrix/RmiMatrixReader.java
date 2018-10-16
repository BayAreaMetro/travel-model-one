package com.pb.common.matrix;

import java.io.IOException;
import java.io.Serializable;
import java.lang.reflect.InvocationTargetException;
import java.rmi.NotBoundException;

import org.apache.log4j.Logger;

import gnu.cajo.invoke.Remote;

public class RmiMatrixReader extends MatrixReader implements Serializable {

    private Logger logger = Logger.getLogger( RmiMatrixReader.class );

    String connectString = "//localhost:1198/com.pb.common.matrix.RemoteMatrixDataServer";

    public void testRemote(String name) throws MatrixException {

        Object[] objArray = { this.type, this.file, name };
        try {
            Object obj = Remote.getItem(connectString);
            Remote.invoke(obj, "testRemote", objArray);
        }
        catch (UnsatisfiedLinkError e) {
            logger.error ("Error in RMI call to testRemote().");
            throw e;
        }
        catch (InvocationTargetException e) {
            logger.error ("Error in RMI call to testRemote().");
            throw new MatrixException(e);
        }
        catch (InstantiationException e) {
            throw new MatrixException(e);
        }
        catch (NotBoundException e) {
            throw new MatrixException(e);
        }
        catch (ClassNotFoundException e) {
            throw new MatrixException(e);
        }
        catch (IllegalAccessException e) {
            throw new MatrixException(e);
        }
        catch (IOException e) {
            throw new MatrixException(e);
        }
        catch (Exception e) {
            logger.error ("Other Error in RMI call to testRemote");
            logger.error ("using connectString: " + connectString);
            logger.error ("file type: " + this.type.toString());
            logger.error ("file name: " + this.file.getName());
            logger.error ("table name: " + name);
            throw new RuntimeException(e);
        }
    }

    public Matrix readMatrix(String name) throws MatrixException {

        Object[] objArray = { this.type, this.file, name };
        try {
            Object obj = Remote.getItem(connectString);
            Matrix matrix = (Matrix) Remote.invoke(obj, "readMatrix", objArray);
            return matrix;
        }
        catch (UnsatisfiedLinkError e) {
            logger.error ("Error in RMI call to read matrix.  Could not load native dll.");
            throw e;
        }
        catch (InvocationTargetException e) {
            throw new MatrixException(e);
        }
        catch (InstantiationException e) {
            throw new MatrixException(e);
        }
        catch (NotBoundException e) {
            throw new MatrixException(e);
        }
        catch (ClassNotFoundException e) {
            throw new MatrixException(e);
        }
        catch (IllegalAccessException e) {
            throw new MatrixException(e);
        }
        catch (IOException e) {
            throw new MatrixException(e);
        }
        catch (RuntimeException e) {
            logger.error ("RuntimeException in RMI call to read matrix");
            logger.error ("using connectString: " + connectString);
            logger.error ("file type: " + this.type.toString());
            logger.error ("file name: " + this.file.getName());
            logger.error ("table name: " + name);
            throw e;
        }
        catch (Exception e) {
            logger.error ("Other Error in RMI call to read matrix");
            logger.error ("using connectString: " + connectString);
            logger.error ("file type: " + this.type.toString());
            logger.error ("file name: " + this.file.getName());
            logger.error ("table name: " + name);
            throw new RuntimeException(e);
        }
    }

    public Matrix readMatrix() throws MatrixException {
        return readMatrix( "noName" );
    }

    public Matrix[] readMatrices() throws MatrixException {
        throw new RuntimeException("method has not been implemented");
    }

    public void setConnectString(String connectString) {
        this.connectString = connectString;
    }
    
}
