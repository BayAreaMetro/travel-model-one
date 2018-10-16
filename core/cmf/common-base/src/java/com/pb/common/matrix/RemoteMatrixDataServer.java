package com.pb.common.matrix;

import gnu.cajo.invoke.Remote;
import gnu.cajo.utils.ItemServer;

import com.pb.common.util.CommandLine;

import java.io.File;
import java.util.concurrent.TimeUnit;


import org.apache.log4j.Logger;

public class RemoteMatrixDataServer {


    public String connectionTest() {
        return "RemoteMatrixDataServer connected";
    }

    public String connectionTest2( String arg ) {
        return "RemoteMatrixDataServer test2: " + arg;
    }

    public String connectionTest3( String[] arg ) {
        return "RemoteMatrixDataServer test3: names.length = " + arg.length;
    }

    public String connectionTest4( Matrix[] arg ) {
        return "RemoteMatrixDataServer test4: m.length = " + arg.length;
    }

    public void testRemote(MatrixType type, File file, String matrixName) {
        MatrixReader mr = MatrixReader.createReader(type, file);
        mr.testRemote(matrixName);
    }

    public Matrix readMatrix(MatrixType type, File file, String matrixName) {
        MatrixReader mr = MatrixReader.createReader(type, file);
        return mr.readMatrix(matrixName);
    }

    public void writeMatrix(MatrixType type, File file, Matrix m, String matrixName) {
        MatrixWriter mw = MatrixWriter.createWriter(type, file);
        mw.writeMatrix(matrixName, m);
    }

    public void writeMatrices(MatrixType type, File file, Matrix[] m, String[] matrixName) {
        MatrixWriter mw = MatrixWriter.createWriter(type, file);
        mw.writeMatrices(matrixName, m);
    }

    public static void main(String args[]) throws Exception {

        Logger logger = Logger.getLogger( RemoteMatrixDataServer.class );

        CommandLine cmdline = new CommandLine(args);

        //Read ipAddress from command-line
        String hostname = "localhost";
        String ipValue = cmdline.value("hostname");
        if ( (ipValue != null) && (ipValue.length() > 0) ){
            hostname = ipValue;
        }

        //Read port from command-line
        int port = 1198;
        String portValue = cmdline.value("port");
        if ( (portValue != null) && (portValue.length() > 0) ){
            port = Integer.parseInt(portValue);
        }

        // bind this concrete object with the cajo library objects for managing RMI
        boolean serverWaiting = true;
        int count = 0;
        while ( serverWaiting ) {
            try {
                Remote.config( hostname, port, null, 0 );
                ItemServer.bind( new RemoteMatrixDataServer(), "com.pb.common.matrix.RemoteMatrixDataServer" );
                serverWaiting = false;
            }
            catch ( Exception e ) {
                TimeUnit.SECONDS.sleep(10);
                e.printStackTrace();
                logger.error( "try number" + count++ );
            }
            if ( count == 3 ) {
                logger.error( "RemoteMatrixDataServer stopping after 3 tries to bind to "  + hostname +":"+ port + "." );
                throw new RuntimeException();
            }
        }

        logger.error("RemoteMatrixDataServer started on: " + hostname +":"+ port);
    }
}
