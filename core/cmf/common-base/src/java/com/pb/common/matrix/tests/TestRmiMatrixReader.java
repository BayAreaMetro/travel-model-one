package com.pb.common.matrix.tests;

import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.RmiMatrixReader;
import com.pb.common.util.DosCommand;

import java.io.File;


public class TestRmiMatrixReader {

    static final String[] JRE_ARGS = {
        "com.pb.common.matrix.RemoteMatrixDataServer",
        "-hostname",
        "localhost",
        "-port",
        "1198"
    };
/*
    static final String[] JRE_ARGS = {
        "-cp",
        "c:\\jim\\util\\svn_workspace\\cmf\\common-base\\build\\classes;c:\\jim\\util\\svn_workspace\\cmf\\common-base\\lib\\cajo.jar;c:\\jim\\util\\svn_workspace\\third-party\\logging-log4j-1.2.9\\log4j-1.2.9.jar",
        "-Djava.library.path=/jim/util/svn_workspace/cmf/common-base/bin",
        "-Dlog4j.configuration=log4j.xml",
        "com.pb.common.matrix.RemoteMatrixDataServer",
        "-hostname",
        "localhost",
        "-port",
        "1198"
    };
*/
    DosCommand dosCmd = null;
    
    
    public static void main(String args[]) {

        // start the server
        TestRmiMatrixReader testObj = new TestRmiMatrixReader();
        testObj.startMatrixDataServer();
        
        //These lines will remote any matrix reader call
        RmiMatrixReader rmiReader = null;
        while ( rmiReader == null )
            rmiReader = new com.pb.common.matrix.RmiMatrixReader();
        
        rmiReader.setConnectString("//localhost:1198/RemoteMatrixDataServer");
        MatrixReader.setReaderClassForType(MatrixType.TPPLUS, rmiReader);
        //MatrixReader.setReaderClassForType(MatrixType.TRANSCAD, rmiReader);

        try {
            
            MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS, new File("/jim/projects/baylanta/data/outputs/sovffm05.skm"));
            Matrix matrix = mr.readMatrix("distance");

            System.out.println("m[ 1, 1]= " + matrix.getValueAt(1,1));
            System.out.println("m[ 5, 5]= " + matrix.getValueAt(5,5));
            System.out.println("m[50,50]= " + matrix.getValueAt(50,50));

        }
        catch ( RuntimeException e) {
            e.printStackTrace();
            System.out.println ( "errors occurred." );
        }

        
        testObj.stopMatrixDataServer();
        
        System.out.println("\ndone with test.");
    }

    
    private void startMatrixDataServer() {
        dosCmd = new DosCommand();
        
        try {
            dosCmd.runJavaClassIn32BitJRE( JRE_ARGS );
        }
        catch ( RuntimeException e ) {
            System.out.println ( "caught the exception." );
        }

        String consoleOutput = dosCmd.getConsoleOutput();
        if ( consoleOutput.length() > 0 )
            System.out.println( consoleOutput );

    }
    
    private void stopMatrixDataServer() {
        dosCmd.destroy();
    }
    
}

