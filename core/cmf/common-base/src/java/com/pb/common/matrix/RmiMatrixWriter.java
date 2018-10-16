package com.pb.common.matrix;

import java.io.Serializable;

import org.apache.log4j.Logger;

import gnu.cajo.invoke.Remote;

public class RmiMatrixWriter extends MatrixWriter implements Serializable {

    private Logger logger = Logger.getLogger( RmiMatrixWriter.class );

    String connectString = "//localhost:1199/com.pb.common.matrix.RemoteMatrixDataServer";

    public void writeMatrix(Matrix matrix) throws MatrixException {
        String name = "none";
        writeMatrix(name, matrix);
    }

    public void writeMatrix(String name, Matrix matrix) throws MatrixException {

        Object[] objArray = { this.type, this.file, matrix, name };
        try {
            Object obj = Remote.getItem(connectString);
            Remote.invoke(obj, "writeMatrix", objArray);
        }
        catch (Exception e) {            
            logger.error( "[" + Thread.currentThread().getName() + "]" + "Error in RMI call to writeMatrix(String name, Matrix matrix)." );
            logger.error( "[" + Thread.currentThread().getName() + "]" + "file name=" + this.file );
            logger.error( "[" + Thread.currentThread().getName() + "]" + "matrix table name=" + name );
            logger.error( "[" + Thread.currentThread().getName() + "]" + "connectString=" + connectString );
            e.printStackTrace();
            throw new RuntimeException(e);
        }
    }

    public void writeMatrices(String[] name, Matrix[] matrix) throws MatrixException {

        Object[] objArray = { this.type, this.file, matrix, name };
        try {
            Object obj = Remote.getItem(connectString);
            Remote.invoke(obj, "writeMatrices", objArray);
        }
        catch (Exception e) {            
            logger.error( String.format("[" + Thread.currentThread().getName() + "]" + "Error in RMI call to writeMatrices(String[] name, Matrix[] matrix) for matrix[0] with name=%s.", name[0]) );
            logger.error( "[" + Thread.currentThread().getName() + "]" + "type=" + this.type);
            logger.error( "[" + Thread.currentThread().getName() + "]" + "file name=" + this.file);
            logger.error( "[" + Thread.currentThread().getName() + "]" + "connectString=" + connectString );
            e.printStackTrace();
            throw new RuntimeException(e);
        }
    }

    public void setConnectString(String connectString) {
        this.connectString = connectString;
    }
    
    public String testRemote( String arg )
    {
        Object[] objArray = { arg };
        try {
            Object obj = Remote.getItem(connectString);
            return "RmiMatrixWriter.testRemote() returning:  " + (String)Remote.invoke(obj, "connectionTest2", objArray);
        }
        catch (Exception e) {            
            logger.error( String.format("[" + Thread.currentThread().getName() + "]" + "Error in testRemote()" ) );
            e.printStackTrace();
            throw new RuntimeException(e);
        }
    }

}
