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
package com.pb.common.matrix;

/**
 * A square matrix is a Matrix which has the same number of rows and columns.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class SquareMatrix extends Matrix {

    //------------------------ Contructors ------------------------
    /**
     * Constructor.
     * @param n the number of rows == the number of columns
     */
    public SquareMatrix(int n) {
        super(n, n);
    }

    /**
     * Constructor.
     * @param m the matrix (only the upper left square used)
     */
    private SquareMatrix(Matrix m) {
        set(m);
    }

    /**
     * Constructor.
     * @param values the array of values
     */
    public SquareMatrix(float values[][]) {
        setValues(values);
    }

    //------------------------ Setters ------------------------

    /**
     * Set this square matrix from another matrix.  Note that this
     * matrix will reference the values of the argument matrix.  If
     * the values are not square, only the upper left square is used.
     * @param m the 2-d array of values
     */
    private void set(Matrix m) {
        this.nRows = this.nCols = Math.min(m.nRows, m.nCols);
        this.values = m.values;
    }

    /**
     * Set this square matrix from a 2-d array of values.  If the
     * values are not square, only the upper left square is used.
     * @param values the 2-d array of values
     */
    protected void setValues(float values[][]) {
        super.setValues(values);
        nRows = nCols = Math.min(nRows, nCols);
    }

    //------------------------ Operations ------------------------

    /**
     * Add another square matrix to this matrix.
     * @param sm the square matrix addend
     * @return the sum matrix
     * @throws MatrixException for invalid size
     */
    public SquareMatrix add(SquareMatrix sm) throws MatrixException {
        return new SquareMatrix(super.add(sm));
    }

    /**
     * Subtract another square matrix from this matrix.
     * @param sm the square matrix subrrahend
     * @return the difference matrix
     * @throws MatrixException for invalid size
     */
    public SquareMatrix subtract(SquareMatrix sm)
            throws MatrixException {
        return new SquareMatrix(super.subtract(sm));
    }

    /**
     * Multiply this square matrix by another square matrix.
     * @param sm the square matrix multiplier
     * @return the product matrix
     * @throws MatrixException for invalid size
     */
    public SquareMatrix multiply(SquareMatrix sm)
            throws MatrixException {
        return new SquareMatrix(super.multiply(sm));
    }
}