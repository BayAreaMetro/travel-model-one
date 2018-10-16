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
package com.pb.common.matrix.tests;

import com.pb.common.emme2.io.Emme2DataBank;
import com.pb.common.matrix.Emme2MatrixReader;
import com.pb.common.matrix.Emme2MatrixWriter;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.MatrixWriter;

import java.io.File;
import org.apache.log4j.Logger;

/**
 * Tests the Emme2MatrixReader/Writer classes.
 *
 * @author    Tim Heier
 * @version   1.0, 2/3/2003
 */
public class TestEmme2Matrix {

    public static Logger logger = Logger.getLogger("com.pb.common.matrix");


    public static void main(String[] args) {
        
        TestEmme2Matrix tester = new TestEmme2Matrix();
        float[] values = tester.readRow("f:/hgac_2025/peak/emme2ban","mf106",311);
        
        tester.writeRow("f:/hgac_2025/peak/emme2ban","mf150",311, values);
        
        //        Matrix m = TestEmme2Matrix.readFullMatrix();
//        m.print("9.3");

//        TestEmme2Matrix.writeFullMatrix( m );
    }

    /**
     * Read a full matrix from an existing Emme2 databank.
     */
    public static Matrix readFullMatrix() {
        MatrixReader mr = MatrixReader.createReader(MatrixType.EMME2, new File("e:/hgac/95base/asn24/emme2ban"));
        Matrix m = mr.readMatrix("mf106");
        
        //Print matrix contents
        logger.info("\nFinished reading mf106 from file: emme2ban");
        logger.info("Sum = " + m.getSum());


        //Print internal zone numbering
        logger.info("\n");
        StringBuffer sb = new StringBuffer(255);
        sb.append("Internal numbers = ");
        int[] iNums = m.getInternalNumbers();
       for (int i=1; i < iNums.length; i++) {
            sb.append( iNums[i] + ",");
        }
        logger.info( sb.toString() );

        return m;
    }

    /**
     * Write matrix to an existing Emme2 databank.
     */
    public static void writeFullMatrix(Matrix m) {

        double sum = m.getSum();

        File e2 =  new File("e:/hgac/95base/asn24/emme2ban");
          
        //Overwrite existing data
        MatrixWriter mw = MatrixWriter.createWriter(MatrixType.EMME2,e2);

        int[] externals = m.getExternalNumbers();
        
        logger.info("external matrix is "+externals.length+" long");
        Matrix newMatrix =  new Matrix("new Matrix","mat",externals.length-1,externals.length-1);
        
        mw.writeMatrix("mf221", newMatrix);

        //Read matrix back in and verify the values
        MatrixReader mr = MatrixReader.createReader(MatrixType.EMME2, new File("e:/hgac/95base/asn24/emme2ban"));
        Matrix m2 = mr.readMatrix("mf221");

        double sum2 = m2.getSum();

        logger.info("sum before writing = " + String.format("%8.2f", sum) );
        logger.info("sum after  writing = " + String.format("%8.2f", sum2) );
    }
    
    public float[] readRow(String databank, String name, int ptaz){
        
        Emme2MatrixReader mr = new Emme2MatrixReader(new File(databank));
        float[] values = mr.readRow(name,ptaz);
        
        Emme2DataBank m2bank = mr.getDataBank();
        
        int[] externalNumbers = m2bank.getExternalZoneNumbers();
        
        //Print matrix contents
        logger.info("\nFinished reading "+name+" row: "+ptaz+" from file: "+databank);
        
        for(int i=0;i<values.length;++i)
            logger.info(externalNumbers[i]+","+values[i]);
        
        return values;
    }
    public void writeRow(String databank, String name, int ptaz, float[] values){
        
        Emme2MatrixWriter mw = new Emme2MatrixWriter(new File(databank));
        
        mw.writeRow(name, ptaz, values);
        
        logger.info("Finished writing values to  "+name+" row: "+ptaz+" in file: "+databank);
           
    }


}
