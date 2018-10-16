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
 * A row oriented matrix class.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 *
 */
public class RowVector extends Matrix {

    //------------------------ Contructors ------------------------

    /**
     * Constructor.
     * @param n the number of elements
     */
    public RowVector(int n) {
        super(1, n);
    }

    /**
     * Constructor.
     * @param values the array of values
     */
    public RowVector(float values[]) {
        setValues(values);
        initExternalNumbers();
    }

    /**
     * Constructor.
     * @param m the matrix (only the first row used)
     */
    private RowVector(Matrix m) {
        set(m);
    }

    //------------------------ Getters ------------------------

    /**
     * Return the row vector's size.
     */
    public int size() {
        return nCols;
    }

    /**
     * Copy the values of this matrix.
     * @return the copied values
     */
    public float[] copyValues1D() {
        float v[] = new float[nCols];

        for (int c = 0; c < nCols; ++c) {
            v[c] = values[0][c];
        }

        return v;
    }

    /**
     * Return the i'th value of the vector.
     * @param col the index
     * @return the value
     */
    public float getValueAt(int col) throws MatrixException {
    	int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
        	logger.info("Cannot get value in column " + c + " of RowVector " + name);
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        return values[0][c];
    }

    /**
     * Return the i'th value of the vector. Overrides method in base class.
     * @param col the index
     * @return the value
     */
    public float getValueAt(int row, int col) throws MatrixException {
        return getValueAt(col);
    }

    /**
     * Returns the sum of a row in the matrix. For a RowVector this is the
     * sum of the entire matrix.
     * @param row the index for the row to be summed (ignored)
     * @return the sum of the selected row
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getRowSum(int row) throws MatrixException {
        throw new UnsupportedOperationException("This method is not applicable to a Row Vector - call getSum() instead");
    }

    /**
     * Returns the sum of the elements in the vector.. For a RowVector this is the
     * sum of the entire matrix.
     * @return the sum of the vector elements
     */
    public double getSum() throws MatrixException {
        return super.getSum();
    }

    //------------------------ Setters ------------------------

    /**
     * Set this row vector from a matrix. Only the first row is used.
     * @param m the matrix
     */
    private void set(Matrix m) {
        this.nRows = 1;
        this.nCols = m.nCols;
        this.values = m.values;
    }

    /**
     * Set this row vector from an array of values.
     * @param values the array of values
     */
    protected void setValues(float values[]) {
        this.nRows = 1;
        this.nCols = values.length;
        this.values = new float[1][];

        this.values[0] = values;
    }

    /**
     * Set the i'th value of the vector.
     * @param col the index
     * @param value the value
     */
    public void setValueAt(int col, float value) throws MatrixException {
    	int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
        	logger.info("Cannot set value in column " + c + " of RowVector " + name);
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        values[0][c] = value;
    }

    /**
     * Set the i'th value of the vector. Overrides method in base class.
     * @param row the index - ignored
     * @param col the index
     * @param value the value
     */
    public void setValueAt(int row, int col, float value) throws MatrixException {
        throw new UnsupportedOperationException("This method is not applicable to a Row Vector - call setValueAt(col, value) instead");
    }

    /**
     * Add the additionalValue to the existing value of element.
     * @param jtaz the column index
     * @param additionalValue the value
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public void addToValueAt(int jtaz, float additionalValue) throws MatrixException {
    	float existingValue = getValueAt(jtaz); 
    	float totalValue = existingValue + additionalValue; 
    	setValueAt(jtaz, totalValue); 
    }
    
    //------------------------ Operations ------------------------

    /**
     * Add another row vector to this row vector.
     * @param rv the other row vector
     * @return the sum row vector
     * @throws MatrixException for invalid size
     */
    public RowVector add(RowVector rv) throws MatrixException {
        return new RowVector(super.add(rv));
    }

    /**
     * Subtract another row vector from this row vector.
     * @param rv the other row vector
     * @return the sum row vector
     * @throws MatrixException for invalid size
     */
    public RowVector subtract(RowVector rv) throws MatrixException {
        return new RowVector(super.subtract(rv));
    }

    /**
     * Compute the Euclidean norm.
     * @return the norm
     */
    public float getNorm() {
        double t = 0;
        for (int c = 0; c < nCols; ++c) {
            float v = values[0][c];
            t += v * v;
        }

        return (float) Math.sqrt(t);
    }

    /**
     * Print the vector values.
     */
    public void print() {
        for (int c = 0; c < nCols; ++c) {
            System.out.print("  " + values[0][c]);
        }
        System.out.println();
    }
}