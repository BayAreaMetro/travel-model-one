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

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.MatrixUtil;
import com.pb.common.matrix.MatrixWriter;
import org.apache.log4j.Logger;

import java.io.File;

/**
 * Tests the BinaryMatrixWriter class.
 *
 * @author    Tim Heier
 * @version   1.0, 1/19/2003
 */
public class TestBinaryMatrix {
    static Logger logger = Logger.getLogger("com.pb.common.matrix.tests");

    public static final String matrix1FileName = "testmatrix1.binary";
    public static final String matrix2FileName = "testmatrix2.binary";
    public static final String exsitingFileName = "testmatrix-old.binary";

    public static void main(String[] args) {
        logger.info("Test Description: ");
        logger.info("\tSquare matrix with same external zones in both rows and columns");
        logger.info("\tFirst we will write the matrix as a binary file, then read it back in");
        Matrix m1 = TestBinaryMatrix.createMatrix1();
        TestBinaryMatrix.writeMatrix( m1, matrix1FileName);

        //Read new matrix back in
        TestBinaryMatrix.readMatrix(matrix1FileName);

        //Read old matrix in
        //TestBinaryMatrix.readMatrix(exsitingFileName);

        logger.info("Test Description: ");
        logger.info("\tNon-square matrix with different external zones in rows and columns");
        logger.info("\tFirst we will write the matrix as a binary file, then read it back in");
        Matrix m2 = TestBinaryMatrix.createMatrix2();
        TestBinaryMatrix.writeMatrix( m2, matrix2FileName);

        //Read new matrix back in
        TestBinaryMatrix.readMatrix(matrix2FileName);


    }

    /**
     *  Create a matrix with a few sample values.
     */
    public static Matrix createMatrix1() {
        int size = 10;
        Matrix m = new Matrix("test matrix 1",
                "A description should go here.\nIt can be as long as you want.",
                size,size);

        //Skip zone #2
        int[] zoneNumbers = { 0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11 };
        m.setExternalNumbers(zoneNumbers);

        m.setValueAt(4, 3, (float)4.3);
        m.setValueAt(6, 5, (float)6.5);
        m.setValueAt(10, 11, (float)10.11);

        logger.info("createMatrix()");
        logger.info("Sum=" + String.format("%7.2f", m.getSum()));
        MatrixUtil.print(m, "%7.2f");

        return m;
    }

    /**
     *  Create a matrix with a few sample values.
     */
    public static Matrix createMatrix2() {
        Matrix m = new Matrix("test matrix 2",
                "A description should go here.\nIt can be as long as you want.",
                5,10);

        //Skip zone #2
        int[] rowNumbers = { 0, 2, 4, 6, 8, 10 };
        int[] colNumbers = { 0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19 };

        m.setExternalNumbers(rowNumbers, colNumbers);

        m.setValueAt(4, 3, (float)4.3);
        m.setValueAt(6, 5, (float)6.5);
        m.setValueAt(10, 11, (float)10.11);

        logger.info("createMatrix()");
        logger.info("Sum=" + String.format("%7.2f", m.getSum()));
        MatrixUtil.print(m, "%7.2f");

        return m;
    }

    /**
     *  Read the matrix from an existing binary file
     */
    public static Matrix readMatrix(String fileName) {
        MatrixReader mw = MatrixReader.createReader(MatrixType.BINARY, new File(fileName));

        long startTime = System.currentTimeMillis();
        Matrix m = mw.readMatrix();
        logger.info("readMatrix() "+fileName+", "+m.getRowCount()*m.getColumnCount()*4+" bytes, "+(System.currentTimeMillis()-startTime)/1000.0 +" secs");

        MatrixUtil.print(m, "%7.2f");
        logger.info("Sum=" + String.format("%7.2f", m.getSum()));

        //Try getting single values
        logger.info("Value[ 4, 3] = " + m.getValueAt(4,3));
        logger.info("Value[ 6, 5] = " + m.getValueAt(6,5));
        logger.info("Value[10,11] = " + m.getValueAt(10,11));

        //Print out row and column numbering for inspection
        int[] externalRowNums = m.getExternalRowNumbers();
        int[] externalColumnNums = m.getExternalColumnNumbers();

        String msg = "";

        for (int i=1; i < externalRowNums.length; i++) {
            msg += "" + externalRowNums[i] + ",";
        }
        logger.info("External row numbers:");
        logger.info(msg);

        msg = "";
        for (int i=1; i < externalColumnNums.length; i++) {
            msg += "" + externalColumnNums[i] + ",";
        }
        logger.info("External column numbers:");
        logger.info(msg);

//        logger.info("Internal numbers:");
//        int[] iNums = m.getInternalNumbers();
//        for (int i=1; i < iNums.length; i++) {
//            System.out.print(iNums[i] + ",");
//        }
//        logger.info("");

        return m;
    }

    /**
     *  Write the matrix out to a new binary file
     */
    public static void writeMatrix(Matrix m, String fileName) {
    	MatrixWriter mw = MatrixWriter.createWriter(MatrixType.BINARY, new File(fileName));

        long startTime = System.currentTimeMillis();
        mw.writeMatrix( m );
        logger.info("writeMatrix() "+fileName+", "+m.getRowCount()*m.getColumnCount()*4+" bytes, "+(System.currentTimeMillis()-startTime)/1000.0 +" secs");
    }

}
