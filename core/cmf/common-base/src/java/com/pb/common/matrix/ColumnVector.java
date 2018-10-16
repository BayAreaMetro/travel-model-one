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
 * A column oriented matrix class.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 *
 */
public class ColumnVector extends Matrix {

    //------------------------ Contructors ------------------------

    /**
     * Constructor.
     * @param n the number of elements
     */
    public ColumnVector(int n) {
        super(n, 1);
    }

    /**
     * Constructor.
     * @param values the array of values
     */
    public ColumnVector(float values[]) {
        setValues(values);
        initExternalNumbers();
    }

    /**
     * Constructor.
     * @param m the matrix (only the first column used)
     */
    private ColumnVector(Matrix m) {
        set(m);
    }

    //------------------------ Getters ------------------------

    /**
     * Return this column vector's size.
     */
    public int size() {
        return nRows;
    }

    /**
     * Return the i'th value of the vector.
     * @param itaz the index
     * @return the value
     */
    public float getValueAt(int itaz) throws MatrixException {
    	int r = getInternalRowNumber(itaz);

        if ((r < 0) || (r >= nRows)) {
        	logger.info("Cannot get value in row " + r + " of ColumnVector " + name);
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }
        
    	return values[r][0];
    }

    /**
     * Return the i'th value of the vector. Overrides method in base class.
     * @param row the index
     * @param col the index - ignored
     * @return the value
     */
    public float getValueAt(int row, int col) throws MatrixException {
        return super.getValueAt(row, 1);
    }

    /**
     * Copy the values of this matrix.
     * @return the copied values
     */
    public float[] copyValues1D() {
        float v[] = new float[nRows];

        for (int r = 0; r < nRows; ++r) {
            v[r] = values[r][0];
        }

        return v;
    }

    /**
     * Returns the sum of a column in the matrix. For a ColumnVector this
     * is the sum of the entire matrix.
     * @param col the index for the column to be summed - ignored
     * @return the sum of the selected column
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getColumnSum(int col) throws MatrixException {
        throw new UnsupportedOperationException("Use getSum() instead.");
    }

    //------------------------ Setters ------------------------

    /**
     * Set this column vector from a matrix.
     * Only the first column is used.
     * @param m the matrix
     */
    private void set(Matrix m) {
        this.nRows = m.nRows;
        this.nCols = 1;
        this.values = m.values;
    }

    /**
     * Set this column vector from an array of values.
     * @param values the array of values
     */
    protected void setValues(float values[]) {
        this.nRows = values.length;
        this.nCols = 1;
        this.values = new float[nRows][1];

        for (int r = 0; r < nRows; ++r) {
            this.values[r][0] = values[r];
        }
    }

    /**
     * Set the value of the i'th element.
     * @param itaz the index
     * @param value the value
     */
    //public void set(int i, float value) { values[i-1][0] = value; }

    public void setValueAt(int itaz, float value) throws MatrixException {
    	int r = getInternalRowNumber(itaz);

        if ((r < 0) || (r >= nRows)) {
        	logger.info("Cannot set value in row " + r + " of ColumnVector " + name);
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        values[r][0] = value;
    }

    public void setValueAt(int row, int col, float value) throws MatrixException {
        throw new UnsupportedOperationException("Use setValueAt(row, value) instead.");
    }

    //------------------------ Operations ------------------------

    /**
     * Add another column vector to this column vector.
     * @param cv the other column vector
     * @return the sum column vector
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public ColumnVector add(ColumnVector cv) throws MatrixException {
        return new ColumnVector(super.add(cv));
    }

    /**
     * Subtract another column vector from this column vector.
     * @param cv the other column vector
     * @return the sum column vector
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public ColumnVector subtract(ColumnVector cv)
            throws MatrixException {
        return new ColumnVector(super.subtract(cv));
    }

    /**
     * Compute the Euclidean norm.
     * @return the norm
     */
    public float norm() {
        double t = 0;

        for (int r = 0; r < nRows; ++r) {
            float v = values[r][0];
            t += v * v;
        }

        return (float) Math.sqrt(t);
    }

    /**
     * Print the vector values.
     */
    public void print() {
        for (int r = 0; r < nRows; ++r) {
            System.out.print("  " + values[r][0]);
        }
        System.out.println();
    }
}