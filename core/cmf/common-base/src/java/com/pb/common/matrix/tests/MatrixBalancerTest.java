/*
 * Copyright 2006 PB Consult Inc.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 * 
 * Created on Oct 20, 2006 by Andrew Stryker <stryker@pbworld.com>
 */

package com.pb.common.matrix.tests;

import com.pb.common.matrix.ColumnVector;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixBalancer;
import com.pb.common.matrix.RowVector;
import org.apache.log4j.Logger;
import static org.junit.Assert.assertTrue;
import org.junit.Test;

import static java.lang.Math.abs;
import static java.lang.Math.min;

/**
 * @author Andrew Stryker
 * @version 0.1
 */
public class MatrixBalancerTest {
    private Logger logger = Logger.getLogger(MatrixBalancerTest.class);

    private MatrixBalancer balancer;

    /**
     *
     */
    public MatrixBalancerTest() {
        balancer = new MatrixBalancer();
    }

    /**
     * Test method for {@link com.pb.common.matrix.MatrixBalancer#balance()}.
     */
    @Test
    public void testBalance1() {
        Matrix matrix;
        Matrix seedMatrix;
        int[] extRowNumbers = { 0, 1, 3, 5 };
        int[] extColNumbers = { 0, 1, 2, 4 };
        float[] rTargets = { 30, 10, 60 };
        ColumnVector rowTargets = new ColumnVector(rTargets);
        float[] cTargets = { 20, 30, 50 };
        RowVector colTargets = new RowVector(cTargets);
        float[][] seed = { { 0.60653066f, 0.367879441f, 0.135335283f },
                { 0.367879441f, 0.60653066f, 0.367879441f },
                { 0.135335283f, 0.367879441f, 0.60653066f } };
        float maxError = 0.0001f;
        float[][] balanced = { { 13.549249f, 10.424804f, 6.025766f },
                { 1.9667238f, 4.1133013f, 3.9199646f },
                { 4.484028f, 15.461895f, 40.054268f } };

        logger.info("Testing the general balancing case.");

        seedMatrix = new Matrix(seed);
        seedMatrix.setExternalNumbers(extRowNumbers, extColNumbers);

        rowTargets.setExternalNumbers(extRowNumbers, extColNumbers);
        colTargets.setExternalNumbers(extRowNumbers, extColNumbers);

        balancer.setMaximumAbsoluteError(maxError);
        balancer.setMaximumRelativeError(0.0001);
        balancer.setSeed(seedMatrix);
        balancer.setTargets(rowTargets, colTargets);
        balancer.balance();
        matrix = balancer.getBalancedMatrix();
        for(int r=1; r<extRowNumbers.length; r++){
            for (int c=1; c<extColNumbers.length; c++){
                System.out.print(matrix.getValueAt(extRowNumbers[r],extColNumbers[c]) + ", ");
            }
            System.out.println();
        }

        for (int r = 0; r < seedMatrix.getRowCount(); ++r) {
            int row = extRowNumbers[r + 1];

            for (int c = 0; c < seedMatrix.getColumnCount(); ++c) {
                int col = extColNumbers[c + 1];
                float expect = balanced[r][c];
                float actual = matrix.getValueAt(row, col);

                logger.info("At (" + row + ", " + col + ") expecting " + expect
                        + " and computed " + actual);

                float error;
                    if(expect == 0.0f && actual ==0.0f){
                        error = 0.0f;
                    } else {
                        error = abs(expect - actual) / min(expect, actual);
                    }

                    assertTrue("Unexpected value at " + row + ", " + col,
                            error < maxError);
            }
        }
    }

    /**
     * Test method for {@link com.pb.common.matrix.MatrixBalancer#balance()}.
     */
    @Test
    public void testBalance2() {
        Matrix seedMatrix;
        int[] extRowNumbers = { 0, 1, 3, 5 };
        int[] extColNumbers = { 0, 1, 2, 4 };
        float[] rTargets = { 30, 10, 60 };
        ColumnVector rowTargets = new ColumnVector(rTargets);
        float[] cTargets = { 20, 30, 50 };
        RowVector colTargets = new RowVector(cTargets);
        float[][] seed = { { 0.0f, 0.0f, 0.0f },
                { 0.367879441f, 0.60653066f, 0.367879441f },
                { 0.135335283f, 0.367879441f, 0.60653066f } };
        float maxError = 0.0001f;

        logger.info("Test2:  One seed row is 0, but target in that row is NOT");

        seedMatrix = new Matrix(seed);
        seedMatrix.setExternalNumbers(extRowNumbers, extColNumbers);

        rowTargets.setExternalNumbers(extRowNumbers, extColNumbers);
        colTargets.setExternalNumbers(extRowNumbers, extColNumbers);

        balancer.setMaximumAbsoluteError(maxError);
        balancer.setMaximumRelativeError(0.0001);
        balancer.setSeed(seedMatrix);
        balancer.setTargets(rowTargets, colTargets);
        try {
            balancer.balance();
        } catch (RuntimeException e) {
            logger.info("Exception expected - matrix cannot be balanced without adjusting the seed matrix");
        }

    }

    /**
     * Test method for {@link com.pb.common.matrix.MatrixBalancer#balance()}.
     */
    @Test
    public void testBalance3() {
        Matrix seedMatrix;
        int[] extRowNumbers = { 0, 1, 3, 5 };
        int[] extColNumbers = { 0, 1, 2, 4 };
        float[] rTargets = { 30, 10, 60 };
        ColumnVector rowTargets = new ColumnVector(rTargets);
        float[] cTargets = { 20, 30, 50 };
        RowVector colTargets = new RowVector(cTargets);
        float[][] seed = { { 0.0f, 0.367879441f, 0.135335283f },
                { 0.0f, 0.60653066f, 0.367879441f },
                { 0.0f, 0.367879441f, 0.60653066f } };
        float maxError = 0.0001f;

        logger.info("Test 3:  One seed column is 0, but target in that column is NOT");

        seedMatrix = new Matrix(seed);
        seedMatrix.setExternalNumbers(extRowNumbers, extColNumbers);

        rowTargets.setExternalNumbers(extRowNumbers, extColNumbers);
        colTargets.setExternalNumbers(extRowNumbers, extColNumbers);

        balancer.setMaximumAbsoluteError(maxError);
        balancer.setMaximumRelativeError(0.0001);
        balancer.setSeed(seedMatrix);
        balancer.setTargets(rowTargets, colTargets);
        try {
            balancer.balance();
        } catch (RuntimeException e) {
            logger.info("Exception expected - matrix cannot be balanced without adjusting the seed matrix");
        }

    }

    /**
         * Test method for {@link com.pb.common.matrix.MatrixBalancer#balance()}.
         */
        @Test
        public void testBalance4() {
            Matrix matrix;
            Matrix seedMatrix;
            int[] extRowNumbers = { 0, 1, 3, 5 };
            int[] extColNumbers = { 0, 1, 2, 4 };
            float[] rTargets = { 30, 0, 60 };
            ColumnVector rowTargets = new ColumnVector(rTargets);
            float[] cTargets = { 20, 30, 40 };
            RowVector colTargets = new RowVector(cTargets);
            float[][] seed = { { 0.60653066f, 0.367879441f, 0.135335283f },
                    { 0.367879441f, 0.60653066f, 0.367879441f },
                    { 0.135335283f, 0.367879441f, 0.60653066f } };
            float maxError = 0.0001f;
            float[][] balanced = { { 14.432368f, 10.993365f, 4.572222f },
                    { 0.0f, 0.0f, 0.0f },
                    { 5.567633f, 19.006636f, 35.427776f } };

            logger.info("Testing the general balancing case.");

            seedMatrix = new Matrix(seed);
            seedMatrix.setExternalNumbers(extRowNumbers, extColNumbers);

            rowTargets.setExternalNumbers(extRowNumbers, extColNumbers);
            colTargets.setExternalNumbers(extRowNumbers, extColNumbers);

            balancer.setMaximumAbsoluteError(maxError);
            balancer.setMaximumRelativeError(0.0001);
            balancer.setSeed(seedMatrix);
            balancer.setTargets(rowTargets, colTargets);
            balancer.balance();
            matrix = balancer.getBalancedMatrix();
            for(int r=1; r<extRowNumbers.length; r++){
                for (int c=1; c<extColNumbers.length; c++){
                    System.out.print(matrix.getValueAt(extRowNumbers[r],extColNumbers[c]) + ", ");
                }
                System.out.println();
            }

            for (int r = 0; r < seedMatrix.getRowCount(); ++r) {
                int row = extRowNumbers[r + 1];

                for (int c = 0; c < seedMatrix.getColumnCount(); ++c) {
                    int col = extColNumbers[c + 1];
                    float expect = balanced[r][c];
                    float actual = matrix.getValueAt(row, col);

                    logger.info("At (" + row + ", " + col + ") expecting " + expect
                            + " and computed " + actual);

                    float error;
                    if(expect == 0.0f && actual ==0.0f){
                        error = 0.0f;
                    } else {
                        error = abs(expect - actual) / min(expect, actual);
                    }

                    assertTrue("Unexpected value at " + row + ", " + col,
                            error < maxError);
                }
            }
        }


    public static void main (String[] args){
        MatrixBalancerTest mbt = new MatrixBalancerTest();
        mbt.testBalance1();

        mbt.testBalance2();

        mbt.testBalance3();

        mbt.testBalance4();

    }

}
