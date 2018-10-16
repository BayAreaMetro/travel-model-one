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

import java.util.HashSet;
import java.util.Set;

import org.apache.log4j.Logger;
import org.junit.Test;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.RowVector;

import static org.junit.Assert.*;

/**
 * JUnit style tests for the Matrix class.
 * 
 * @author Andrew Stryker
 * @version 0.1
 */
public class MatrixTest {
    private Logger logger = Logger.getLogger(MatrixTest.class);

    /**
     * Test initialization with an array.
     */
    @Test
    public void testArrayInitialization() {
        logger.info("Testing to see that values are indexed correctly when"
                + " a Matrix is initialized using an array.");
        float[][] values = { { 1, 2 }, { 3, 4 } };
        Matrix matrix = new Matrix(values);

        for (int r = 0; r < matrix.getRowCount(); ++r) {
            int row = r + 1;

            for (int c = 0; c < matrix.getColumnCount(); ++c) {
                int col = c + 1;
                try {
                    assertEquals(values[r][c], matrix.getValueAt(row, col));
                } catch (NullPointerException e) {
                    String eMsg = "NullPointerException.";

                    logger.error(eMsg);
                    fail(eMsg);
                }
            }
        }

    }

    /**
     * Test creating an external number array from a Set.
     */
    @Test
    public void testCreateExternalNumbers() {
        Set<Integer> set = new HashSet<Integer>();
        int[] expect = { 0, 1, 3 };
        int[] test;

        logger.info("Testing Matrix.");

        set.add(1);
        set.add(3);

        test = Matrix.createExternalNumbers(set);

        assertEquals("Array length", expect.length, test.length);

        compareIntArrays(expect, test);
    }

    /**
     * Test getting a square sub-matrix.
     */
    @Test
    public void testSubMatrixSet() {
        Set<Integer> set = new HashSet<Integer>();
        Matrix full = create1FilledMatrix(10, 10);
        Matrix sub;
        int[] expectedExternalNumbers;
        int[] subExternalNumbers;

        set.add(3);
        set.add(4);
        set.add(5);

        expectedExternalNumbers = Matrix.createExternalNumbers(set);
        sub = full.getSubMatrix(set);
        subExternalNumbers = sub.getExternalNumbers();

        assertEquals("Number of rows", set.size(), sub.getRowCount());
        assertEquals("Number of columns", set.size(), sub.getColumnCount());
        assertEquals("Sum", (double) (set.size() * set.size()), sub.getSum());

        compareIntArrays(expectedExternalNumbers, subExternalNumbers);
    }

    /**
     * Test getting a rectangular sub-matrix.
     */
    @Test
    public void testSubMatrixSetSet() {
        Set<Integer> rows = new HashSet<Integer>();
        Set<Integer> cols = new HashSet<Integer>();
        Matrix full = create1FilledMatrix(10, 10);
        Matrix sub;

        rows.add(3);
        rows.add(4);
        rows.add(5);

        cols.add(7);
        cols.add(8);

        sub = full.getSubMatrix(rows, cols);

        assertEquals("Number of rows", rows.size(), sub.getRowCount());
        assertEquals("Number of columns", cols.size(), sub.getColumnCount());
        assertEquals("Sum", (double) (rows.size() * cols.size()), sub.getSum());
    }

    /**
     * Test scaling a matrix.
     * 
     * Note: this test was written when debugging ACOM for Ohio.
     */
    @Test
    public void testScale() {
        RowVector rowVector = new RowVector(5);
        int[] extNumbers = { 0, 2, 3, 5, 8, 11 };

        assertEquals("Wrong number of rows", 1, rowVector.getRowCount());
        assertEquals("Wrong number of columns", 5, rowVector.getColumnCount());

        rowVector.setExternalNumbers(extNumbers);

        assertEquals("Wrong number of rows", 1, rowVector.getRowCount());
        assertEquals("Wrong number of columns", 5, rowVector.getColumnCount());

        rowVector.fill(1f);
        rowVector.scale(10f);

        assertEquals("Unexpected sum", 50.0, rowVector.getSum());
    }

    /**
     * Utility method to create a 1-filled matrix.
     */
    protected static Matrix create1FilledMatrix(int rows, int cols) {
        Matrix matrix = new Matrix("Test matrix", "A " + rows + " x " + cols
                + " test matrix", rows, cols);

        matrix.fill(1f);

        return matrix;
    }

    /**
     * @param expect
     * @param test
     */
    private void compareIntArrays(int[] expect, int[] test) {
        for (int i = 0; i < expect.length; ++i) {
            assertEquals("Value in position " + i, expect[i], test[i]);
        }
    }

}
