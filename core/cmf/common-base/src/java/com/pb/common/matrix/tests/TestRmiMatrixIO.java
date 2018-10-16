package com.pb.common.matrix.tests;

import com.pb.common.matrix.MatrixIO32BitJvm;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixWriter;

import java.io.File;

import org.apache.log4j.Logger;


public class TestRmiMatrixIO {

    static Logger logger = Logger.getLogger(TestRmiMatrixIO.class);

    static final String INPUT_MATRIX_FILENAME =  "/jim/projects/baylanta/data/outputs/sovffm05.skm";
    static final String INPUT_MATRIX_TABLENAME =  "distance";
    
    static final boolean USE_RMI = true;
//    static final boolean USE_RMI = false;

    private void runTest( String[] fileNameArgs ) {
        
        String inputMatrixFileName = null;
        String inputMatrixTableName = null;
        String tempMatrixFileName = null;
        
        if ( fileNameArgs.length == 2 ) {
            inputMatrixFileName = fileNameArgs[0];
            inputMatrixTableName = fileNameArgs[1];
        }
        else {
            inputMatrixFileName = INPUT_MATRIX_FILENAME;
            inputMatrixTableName = INPUT_MATRIX_TABLENAME;
        }
        tempMatrixFileName = inputMatrixFileName + "_revised";

        
        
        MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS, new File( inputMatrixFileName ));
        System.out.println ( "created an object of " + mr.getClass().getName() + " for reading matrix data." ); 
        mr.testRemote( inputMatrixTableName );

        mr = MatrixReader.createReader(MatrixType.TPPLUS, new File( inputMatrixFileName ));
        System.out.println ( "created an object of " + mr.getClass().getName() + " for reading matrix data." ); 
        Matrix matrix = mr.readMatrix( inputMatrixTableName );

        // report initial matrix values
        System.out.println("m[ 1, 1]= " + matrix.getValueAt(1,1));
        System.out.println("m[ 5, 5]= " + matrix.getValueAt(5,5));
        System.out.println("m[50,50]= " + matrix.getValueAt(50,50));

        // change matrix values
        matrix.setValueAt(1,1, 5*matrix.getValueAt(1,1));
        matrix.setValueAt(5,5, 7*matrix.getValueAt(5,5));
        matrix.setValueAt(50,50, 70 + matrix.getValueAt(50,50));
        System.out.println("5 * m[ 1, 1]= " + matrix.getValueAt(1,1));
        System.out.println("7 * m[ 5, 5]= " + matrix.getValueAt(5,5));
        System.out.println("m[50,50] + 70 = " + matrix.getValueAt(50,50));
        
        // write out revised matrix
        MatrixWriter mw = MatrixWriter.createWriter(MatrixType.TPPLUS, new File(tempMatrixFileName));
        System.out.println ( "created an object of " + mw.getClass().getName() + " for writing matrix data." ); 
        mw.writeMatrix("revised", matrix);
        

        // read back the revised values and report
        mr = MatrixReader.createReader(MatrixType.TPPLUS, new File(tempMatrixFileName));
        System.out.println ( "created an object of " + mr.getClass().getName() + " for reading matrix data." );
        
        // a 
        matrix = mr.readMatrix("revised");

        // report initial matrix values
        System.out.println("revised m[ 1, 1]= " + matrix.getValueAt(1,1));
        System.out.println("revised m[ 5, 5]= " + matrix.getValueAt(5,5));
        System.out.println("revised m[50,50]= " + matrix.getValueAt(50,50));
    }

    public static void main(String args[]) {

        MatrixIO32BitJvm ioVm32Bit = null;
        try {
            
            if ( USE_RMI ) {
                // start the 32 bit JVM used specifically for running matrix io classes
                ioVm32Bit = MatrixIO32BitJvm.getInstance();
                ioVm32Bit.startJVM32();
                
                // establish that matrix reader and writer classes will use the RMI versions for TPPLUS format matrices
                ioVm32Bit.startMatrixDataServer( MatrixType.TPPLUS );
            }

            TestRmiMatrixIO testObj = new TestRmiMatrixIO();
            testObj.runTest( args );
        
            if ( USE_RMI ) {
                
                // establish that matrix reader and writer classes will not use the RMI versions any longer.
                // local matrix i/o, as specified by setting types, is now the default again.
                ioVm32Bit.stopMatrixDataServer();
                
                // close the JVM in which the RMI reader/writer classes were running
                ioVm32Bit.stopJVM32(0);
                System.out.println ( "\n32 bit java JRE has been stopped." );
            }
            
            
            // run test again, should use local matrix i/o methods only.
            testObj.runTest( args );

        }
        catch (UnsatisfiedLinkError e) {
            logger.error("stopping due to UnsatisfiedLinkError");
            if ( USE_RMI )
                ioVm32Bit.stopJVM32();
        }
        catch (Exception e) {
            logger.error("stopping due to catching other Exception", e);
            if ( USE_RMI )
                ioVm32Bit.stopJVM32();
        }

        System.out.println("\ndone with test.");
    }

}

