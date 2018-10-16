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

import com.pb.common.matrix.ColumnVector;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixUtil;
import com.pb.common.matrix.RowVector;
import org.apache.log4j.Logger;

/**
 * Tests class and methods in the matrix package.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class TestMatrix {

    private static Logger logger = Logger.getLogger(TestMatrix.class);


    public TestMatrix() {
    }


    public void run() {

    }


    /**
     * Create a full matrix and set some sample values into it.
     */
    public void testMatrix1() {
        logger.info("Test Description: ");
        logger.info("\tThis matrix is a 10 x 10 matrix that has no special external numbering");
        logger.info("\tsystem.  We will define the matrix, set some values, print the matrix and");
        logger.info("\tthe matrix statistics and then get the value in row 5, column 5");
        Matrix m1 = new Matrix(10,10);
        m1.setValueAt(1, 1, (float)1.1);
        m1.setValueAt(5, 5, (float)5.5);
        m1.setValueAt(10, 10, (float)10.10);

        logger.info("\n--------- Full matrix ---------");
        MatrixUtil.print(m1, "%7.2f");

        m1.logMatrixStats();

        //Get values from the matrix

        logger.info("Value at (5,5) should be 5.5.  Result:  " + m1.getValueAt(5,5));

        logger.info("Multiply matrix by a factor of 2");
        Matrix m12 = m1.multiply(2);
        MatrixUtil.print(m12, "%7.2f");
        logger.info("End of TestMatrix1\n\n");

    }

    /**
     * Create a full matrix and set some sample values into it.
     */
    public void testMatrix1a() {
        logger.info("Test Description: ");
        logger.info("\tThis matrix is a 10 x 10 matrix that has a special external numbering");
        logger.info("\tsystem.  We will define the matrix, set some values, print the matrix and");
        logger.info("\tthe matrix statistics and then get the value in row 5, column 5");
        Matrix m1a = new Matrix(10,10);
        int[] externalRowNumbers = {0,2,4,6,8,10,12,14,16,18,20};    //indexing starts at 1.
        int[] externalColumnNumbers = {0,3,5,7,9,11,13,15,17,19,21};  //indexing starts at 1.
        m1a.setExternalNumbers(externalRowNumbers, externalColumnNumbers);

        m1a.setValueAt(2, 3, (float)1.1);
        m1a.setValueAt(10, 11, (float)5.5);
        m1a.setValueAt(20, 21, (float)10.10);

        logger.info("\n--------- Full matrix ---------");
        MatrixUtil.print(m1a, "%7.2f");

        m1a.logMatrixStats();

        //Get values from the matrix

        logger.info("Value at (10,11) should be 5.5.  Result:  " + m1a.getValueAt(10,11));
        logger.info("End of TestMatrix1\n\n");

    }

    /**
     * Create a full matrix and set some sample values into it.
     */
    public void testMatrix2() {
        logger.info("Test Description: ");
        logger.info("\tThis matrix is a 5 x 10 matrix that has no special external numbering");
        logger.info("\tsystem.  We will define the matrix, set some values, print the matrix and");
        logger.info("\tthe matrix statistics and then get the value in row 5, column 5");
        Matrix m2 = new Matrix(5,10);
        m2.setValueAt(1, 1, (float)1.1);
        m2.setValueAt(5, 5, (float)5.5);
        m2.setValueAt(5, 10, (float)10.10);

        logger.info("\n--------- Full matrix ---------");
        MatrixUtil.print(m2, "%7.2f");

        m2.logMatrixStats();

        //Get values from the matrix

        logger.info("Value at (5,5) should be 5.5.  Result:  " + m2.getValueAt(5,5));

        logger.info("Multiply matrix by a factor of 2");
        Matrix m22 = m2.multiply(2);
        MatrixUtil.print(m22, "%7.2f");
        logger.info("End of TestMatrix2\n\n");

    }

    /**
     * Create a full matrix and set some sample values into it.
     */
    public void testMatrix3() {
        logger.info("Test Description: ");
        logger.info("\tThis matrix is a 5 x 10 matrix that has a special external numbering");
        logger.info("\tsystem (even row numbers, odd column numbers).  We must now explicitly");
        logger.info("\tset the external row and column numbers after defining the matrix.  ");
        logger.info("\tThen we will set some values, print the matrix and");
        logger.info("\tthe matrix statistics and then get the value in row 5, column 5");
        Matrix m3 = new Matrix(5,10);
        int[] externalRowNumbers = {0,2,4,6,8,10};    //indexing starts at 1.
        int[] externalColumnNumbers = {0,3,5,7,9,11,13,15,17,19,21};  //indexing starts at 1.
        m3.setExternalNumbers(externalRowNumbers, externalColumnNumbers);

        m3.setValueAt(2, 3, (float)1.1);
        m3.setValueAt(10, 11, (float)5.5);
        m3.setValueAt(10, 21, (float)10.10);

        logger.info("\n--------- Full matrix ---------");
        MatrixUtil.print(m3, "%7.2f");

        m3.logMatrixStats();

        //Get values from the matrix

        logger.info("Value at (10,11) should be 5.5.  Result:  " + m3.getValueAt(10,11));
        logger.info("End of TestMatrix3\n\n");

    }


    /**
     * Create a row oriented matrix and set some sample values into it.
     */
    public void testRowVector1() {
        logger.info("Test Description:");
        logger.info("\tThis is a 10 element vector with no special external numbering");
        logger.info("\tsystem.  The vector will be created, values will be set and then");
        logger.info("\tvalues will be gotten from a position in the vector");
        RowVector m1 = new RowVector(10);
        Matrix m2 = null;
        //method on RowVector
        m1.setValueAt(1, (float)1.0);
        m1.setValueAt(5, (float)5.0);
        m1.setValueAt(10, (float)10.0);

        try {
            logger.info("Getting a value at (1,5) should throw an exception");
            m1.getValueAt(1,5);
        } catch (Exception e) {
            logger.info("It did!" , e);
        }

        logger.info("Getting the value at column 5 should return 5.0.  Result: " + m1.getValueAt(5));

        //method on Matrix
        try {
            logger.info("Setting the value at row 0, column 9 should throw an exception");
            m1.setValueAt(0, 9, (float)9.9);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        logger.info("Setting the value at column 9 should be OK");
        m1.setValueAt(9, (float)9.9);

        logger.info("When multiplying the vector by 2, we should get 2 times the original values");
        m2 = m1.multiply(2);



        logger.info("\n--------- RowVector ---------");
        MatrixUtil.print(m1, "%7.2f");
        MatrixUtil.print(m2, "%7.2f");

        logger.info("End of RowVector test 1\n\n");
    }

    /**
     * Create a row oriented matrix and set some sample values into it.
     */
    public void testRowVector2() {
        logger.info("Test Description:");
        logger.info("\tThis is a 10 element row vector with special external numbering");
        logger.info("\tsystem.  The vector will be created, values will be set and then");
        logger.info("\tvalues will be gotten from a position in the vector");
        RowVector m1 = new RowVector(10);
        m1.setExternalNumbers(new int[]{0,3,6,9,12,15,18,21,24,27,30});
        Matrix m2 = null;
        //method on RowVector

        try {
            logger.info("Trying to set the value at '1' should throw an exception");
            m1.setValueAt(1, (float)1.0);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        m1.setValueAt(3,(float)3.0);
        m1.setValueAt(15, (float)5.0);
        m1.setValueAt(30, (float)10.0);

        try {
            logger.info("Getting a value at (3,15) should throw an exception");
            m1.getValueAt(1,5);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        logger.info("Getting the value at zone 15 should return 5.0.  Result: " + m1.getValueAt(15));

        //method on Matrix
        try {
            logger.info("Setting the value at row 0, column 9 should throw an exception");
            m1.setValueAt(0, 9, (float)9.9);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        logger.info("Setting the value at external zone 9 should be OK");
        m1.setValueAt(9, (float)9.9);

        logger.info("When multiplying the vector by 2, we should get 2 times the original values");
        m2 = m1.multiply(2);

        logger.info("\n--------- RowVector ---------");
        MatrixUtil.print(m1, "%7.2f");
        MatrixUtil.print(m2, "%7.2f");
    }

    /**
     * Create a column oriented matrix and set some sample values into it.
     */
    public void testColumnVector1() {
        logger.info("Test Description:");
        logger.info("\tThis is a 10 element column vector with no special external numbering");
        logger.info("\tsystem.  The vector will be created, values will be set and then");
        logger.info("\tvalues will be gotten from a position in the vector");
        ColumnVector m1 = new ColumnVector(10);
        Matrix m2 = null;
        //method on RowVector
        m1.setValueAt(1, (float)1.0);
        m1.setValueAt(5, (float)5.0);
        m1.setValueAt(10, (float)10.0);
        logger.info("Values set at 1, 5 and 10");

        //method on Matrix
        try {
            logger.info("Setting a value at (0,9) should throw an exception");
            m1.setValueAt(0, 9, (float)9.9);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        try {
            logger.info("Getting a value at (1,5) should throw an exception");
            m1.getValueAt(1,5);
        } catch (Exception e){
            logger.info("It did",e);
        }

        logger.info("Getting a value from external zone 5 should return 5.0.  Result: " + m1.getValueAt(5));

        logger.info("When multiplying the vector by 2, we should get 2 times the original values");
        m2 = m1.multiply(2);


        logger.info("\n--------- ColumnVector ---------");
        MatrixUtil.print(m1, "%7.2f");
        MatrixUtil.print(m2, "%7.2f");
    }

    /**
     * Create a column oriented matrix and set some sample values into it.
     */
    public void testColumnVector2() {
        logger.info("Test Description:");
        logger.info("\tThis is a 10 element column vector with a special external numbering");
        logger.info("\tsystem.  The vector will be created, values will be set and then");
        logger.info("\tvalues will be gotten from a position in the vector");
        ColumnVector m1 = new ColumnVector(10);
        m1.setExternalNumbers(new int[]{0,5,10,15,20,25,30,35,40,45,50});
        Matrix m2 = null;
        //method on ColumnVector

        try {
            logger.info("Setting a value at 1 should throw an exception (not an external number");
            m1.setValueAt(1, (float)1.0);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        m1.setValueAt(5,(float)5.0);
        m1.setValueAt(25, (float)25.0);
        m1.setValueAt(50, (float)50.0);
        logger.info("Values set at 5, 25 and 50");

        //method on Matrix
        try {
            logger.info("Setting a value at (0,45) should throw an exception");
            m1.setValueAt(0, 45, (float)45.45);
        } catch (Exception e) {
            logger.info("It did!",e);
        }

        try {
            logger.info("Getting a value at (1,5) should throw an exception");
            m1.getValueAt(1,5);
        } catch (Exception e){
            logger.info("It did",e);
        }

        logger.info("Getting a value from external zone 5 should return 5.0.  Result: " + m1.getValueAt(5));

        logger.info("When multiplying the vector by 2, we should get 2 times the original values");
        m2 = m1.multiply(2);


        logger.info("\n--------- ColumnVector ---------");
        MatrixUtil.print(m1, "%7.2f");
        MatrixUtil.print(m2, "%7.2f");
    }

    public void testDotProduct1(){
        Matrix m = new Matrix(3,5);
        m.setValueAt(1,1,(float)1.0);
        m.setValueAt(2,2,(float)2.2);
        m.setValueAt(3,3,(float)3.3);
        m.setValueAt(3,4,(float)3.4);
        m.setValueAt(3,5,(float)3.5);

        RowVector rv = new RowVector(3);
        rv.setValueAt(1,(float)1.0);
        rv.setValueAt(2,(float)1.0);
        rv.setValueAt(3,(float)1.0);

        ColumnVector cv = new ColumnVector(5);
        cv.setValueAt(1,(float)1.0);
        cv.setValueAt(2,(float)1.0);
        cv.setValueAt(3,(float)1.0);
        cv.setValueAt(4,(float)1.0);
        cv.setValueAt(5,(float)1.0);

        logger.info("Result of a 1x3 row vector times a 3x5 matrix should be a 1x5 row vector");
        RowVector dot1 = m.multiply(rv);
        MatrixUtil.print(dot1, "%7.2f");

        logger.info("Result of a 3x5 matrix times a 5x1 column vector should be a 3x1 column vector");
        ColumnVector dot2 = m.multiply(cv);
        MatrixUtil.print(dot2, "%7.2f");

    }



    public static void main(String[] args) {

        TestMatrix test = new TestMatrix();
        test.testMatrix1();
        test.testMatrix2();
        test.testMatrix3();
        test.testRowVector1();
        test.testRowVector2();
        test.testColumnVector1();
        test.testColumnVector2();
        test.testDotProduct1();


    }

}
