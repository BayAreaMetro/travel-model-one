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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Set;

import org.apache.log4j.Logger;

/**
 * The matrix class.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 *
 * Notes on internal vs. external numbering:
 *
 * externalNumbers:  Given an internal number(row), return an actual External number -TAZ
 * internalNumbers:  Given an actual Taz number - return position in the values[][] array
 *
 *
 * Note: Both arrays start at [1].
 *
 * /
// * example: centroids 3,4,6 are skipped:
// *
// *  externalNumbers:     internalNumbers:
// *       pos    ext           pos    int
// *         1      1             1      0
// *         2      2             2      1
// *         3      5             3      -1
// *         4      7             4      -1
// *                              5      2
// *                              6      -1
// *                              7      3
// *
// */
public class Matrix implements java.io.Serializable {

    static Logger logger = Logger.getLogger("com.pb.common.matrix");
    protected String name = "";
    protected String description = "";

    protected int nRows;
    protected int nCols;
    protected float values[][];

    /**
     * Given an index in the values[][] array, return the external number.
     * This array is supplied by the user when non-sequential numbering is used.
     */
    public int[] externalRowNumbers;
    public int[] externalColumnNumbers;

    /**
     * Given an external number, return the position in the values[] arrray.
     * This array is calculated based on the externalNumbers array.
     */
    protected int[] internalRowNumbers;
    protected int[] internalColumnNumbers;

    /**
     * Flag which is true when external row and column values are the same.
     */
    boolean externalRowColValuesEqual = true;

    //------------------------ Contructors ------------------------

    /**
     * Prevent outside classes from instantiating the default constructor.
     */
    protected Matrix() {
    }

    /**
     * Constructor.
     * @param name the name of the matrix
     * @param description a description for the matrix
     * @param rowCount the number of rows
     * @param colCount the number of columns
     */
    public Matrix(String name, String description, int rowCount, int colCount) {
        this.name = name;
        this.description = description;

        nRows = (rowCount > 0) ? rowCount : 1;
        nCols = (colCount > 0) ? colCount : 1;
        values = new float[nRows][nCols];

        initExternalNumbers();
    }

    /**
     * Constructor.
     * @param rowCount the number of rows
     * @param colCount the number of columns
     */
    public Matrix(int rowCount, int colCount) {
        this("", "", rowCount, colCount);
    }

    /**
     * Constructor.
     * @param name the name of the matrix
     * @param description a description for the matrix
     * @param values the 2-d array of values
     */
    public Matrix(String name, String description, float values[][]) {
        this.name = name;
        this.description = description;

        setValues(values);
        initExternalNumbers();
    }

    /**
     * Constructor.
     * @param values the 2-d array of values
     */
    public Matrix(float values[][]) {
        this("", "", values);
    }

    @Override
    public String toString() {
        return this.name;
    }

    /**
     * Initialize the externalNumbers array with sequential numbers. This is
     * the default numbering scheme.
     */
    protected void initExternalNumbers() {

        int[] externalRowNumbers = new int[nRows+1];
        for (int i=1; i < nRows+1; i++) {
            externalRowNumbers[i] = i;
        }

        int[] externalColNumbers = new int[nCols+1];
        for (int i=1; i < nCols+1; i++) {
            externalColNumbers[i] = i;
        }

        if(nRows == nCols)
            setExternalNumbers( externalRowNumbers );
        else
            setExternalNumbers(externalRowNumbers, externalColNumbers);
    }

    //------------------------ Getters ------------------------

    /**
     * Get the name of this matrix.
     * @return the name of the matrix
     */
    public String getName() {
        return name;
    }

    /**
     * Get the description of this matrix.
     * @return the description of the matrix
     */
    public String getDescription() {
        return description;
    }

    /**
     * Get the row count.
     * @return the row count
     */
    public int getRowCount() {
        return nRows;
    }

    /**
     * Get the column count.
     * @return the column count
     */
    public int getColumnCount() {
        return nCols;
    }

    /**
     * Get the external element numbering for this matrix. This is often used
     * for zone numbers which skip values.
     *
     * Note: External numbering starts in externalNumbers[1].
     *
     * @return external list of numbers.
     */
    public int[] getExternalNumbers() {
        if (! externalRowColValuesEqual) {
            throw new MatrixException("row and column numbers are not equal. use getExternalRowNumbers() or getExternalColumnNumbers() instead");
        }
        return externalRowNumbers;
    }

    public int[] getExternalRowNumbers() {
        return externalRowNumbers;
    }

    public int[] getExternalColumnNumbers() {
        return externalColumnNumbers;
    }

    public int[] getExternalRowNumbersZeroBased() {
    	int[] temp = new int[externalRowNumbers.length-1];
    	for(int i=1;i<externalRowNumbers.length;i++){
    		temp[i-1]=externalRowNumbers[i];
    	}
        return temp;
    }

    public int[] getExternalColumnNumbersZeroBased() {
    	int[] temp = new int[externalColumnNumbers.length-1];
    	for(int i=1;i<externalColumnNumbers.length;i++){
    		temp[i-1]=externalColumnNumbers[i];
    	}
        return temp;
    }

    /**
     * Returns an iterator of external numbers for the matrix.
     *
     * @return an iterator of external numbers.
     */
    public Iterator getExternalNumberIterator() {
        if (! externalRowColValuesEqual) {
            throw new MatrixException("row and column numbers are not equal. use getExternalRowNumbers() or getExternalColumnNumbers() instead");
        }
        int[] externalNumbers = getExternalNumbers();

        return new ExternalNumberIterator(externalNumbers);
    }

    /**
     * Get the internal element numbering for this matrix.
     *
     * Note: Internal numbering starts in internalNumbers[1].
     *
     * @return internal list of numbers.
     */
    public int[] getInternalNumbers() {
        if (! externalRowColValuesEqual) {
            throw new MatrixException("row and column numbers are not equal. use getInternalRowNumbers() or getInternalColumnNumbers() instead");
        }
        return internalRowNumbers;
    }

    public int[] getInternalRowNumbers() {
        return internalRowNumbers;
    }

    public int[] getInternalColumnNumbers() {
        return internalColumnNumbers;
    }

    /**
     * Get the value of element [r,c] in the matrix.
     * @param itaz the row index
     * @param jtaz the column index
     * @return the value
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getValueAt(int itaz, int jtaz) throws MatrixException {
        int r = getInternalRowNumber(itaz);
        int c = getInternalColumnNumber(jtaz);

        if ((r < 0) || (r >= nRows) || (c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX +" itaz="+itaz+",row="+r+
                    ";  jtaz="+jtaz+", col="+c);
        }

        return values[r][c];
    }


    /**
     * Get a row of this matrix.
     * @param row the row index
     * @return the row as a row vector
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public RowVector getRow(int row) throws MatrixException {
        int r = getInternalRowNumber(row);

        if ((r < 0) || (r >= nRows)) {
            throw new MatrixException(MatrixException.INVALID_INDEX +", "+r);
        }

        RowVector rv = new RowVector(nCols);
        for (int c = 0; c < nCols; ++c) {
            rv.values[0][c] = this.values[r][c];
        }

        return rv;
    }

    /**
     * Get a row of this matrix. Store values in buffer supplied by user.
     * @param row the row index
     * @param rowBuffer the buffer to be used for row data
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public void getRow(int row, float[] rowBuffer) throws MatrixException {
        int r = getInternalRowNumber(row);

        if ((r < 0) || (r >= nRows)) {
            throw new MatrixException(MatrixException.INVALID_INDEX +", "+r);
        }

        if (rowBuffer.length != nCols) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        //Fill user supplied buffer with row values
        for (int c = 0; c < nCols; ++c) {
            rowBuffer[c] = this.values[r][c];
        }
    }

    /**
     * Returns the sum of a row in the matrix.
     * @param row the index for the column to be summed
     * @return the sum of the selected row
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getRowSum(int row) throws MatrixException {
        int r = getInternalRowNumber(row);

        if ((r < 0) || (r >= nRows)) {
            throw new MatrixException(MatrixException.INVALID_INDEX +", "+r);
        }

        double sum = 0.0;
        for (int c = 0; c < nCols; ++c) {
            sum += values[r][c];
        }

        return (float) sum;
    }

    /**
     * Get a total for all the rows in this matrix.
     * @return the row totals as a column vector
     */
    public ColumnVector getRowTotals() {

        double rowTotals[] = new double[nRows];

        //Sum values in a double array
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                rowTotals[r] += this.values[r][c];
            }
        }

        //Convert values from double to float
        float[] floatValues = new float[nCols];
        for (int r = 0; r < nRows; ++r) {
            floatValues[r] = (float) rowTotals[r];
        }

        //Create a ColumnVector to return
        ColumnVector rv = new ColumnVector(floatValues);
        return rv;
    }

    /**
     * Get a total for all the rows in this matrix.
     * @param rowTotals the buffer to store the row totals in
     */
    public void getRowTotals(double[] rowTotals) throws MatrixException {

        if (rowTotals.length != nRows) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        Arrays.fill(rowTotals, 0.0);  //clear out the array

        //Sum values in the user supplied array
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                rowTotals[r] += this.values[r][c];
            }
        }
    }

    /**
     * Get a column of this matrix.
     * @param col the column index
     * @return the column as a column vector
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public ColumnVector getColumn(int col) throws MatrixException {
        int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        ColumnVector cv = new ColumnVector(nRows);
        for (int r = 0; r < nRows; ++r) {
            cv.values[r][0] = this.values[r][c];
        }

        return cv;
    }

    /**
     * Get a column of this matrix. Store values in buffer supplied by user.
     * @param col the row index
     * @param colBuffer the buffer to be used for row data
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public void getColumn(int col, float[] colBuffer) throws MatrixException {
        int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        if (colBuffer.length != nRows) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        //Fill user supplied buffer with column values
        for (int r = 0; r < nRows; ++r) {
            colBuffer[r] = this.values[r][c];
        }
    }

    /**
     * Returns the minimum value of a column in the matrix.
     * @param col the index for the column to be summed
     * @return the minimum of the selected column
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getColumnMin(int col) throws MatrixException {
        int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        double min = values[0][c];
        for (int r = 1; r < nRows; ++r) {
        	min = Math.min(min, values[r][c]);
        }

        return (float) min;
    }

    /**
     * Returns the sum of a column in the matrix.
     * @param col the index for the column to be summed
     * @return the sum of the selected column
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public float getColumnSum(int col) throws MatrixException {
        int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        double sum = 0.0;
        for (int r = 0; r < nRows; ++r) {
            sum += values[r][c];
        }

        return (float) sum;
    }

    /**
     * Get a total for all the columns in this matrix.
     * @return the column totals as a row vector
     */
    public RowVector getColumnTotals() {

        double columnTotals[] = new double[nCols];

        //Sum values in a double array
        for (int c = 0; c < nCols; ++c) {
            for (int r = 0; r < nRows; ++r) {
                columnTotals[c] += this.values[r][c];
            }
        }

        //Convert values from double to float
        float[] floatValues = new float[nCols];
        for (int c = 0; c < nCols; ++c) {
            floatValues[c] = (float) columnTotals[c];
        }

        //Create a ColumnVector to return
        RowVector rv = new RowVector(floatValues);
        return rv;
    }

    /**
     * Get a total for all the columns in this matrix.
     * @param columnTotals the buffer to store the column totals in
     */
    public void getColumnTotals(double[] columnTotals) throws MatrixException {

        if (columnTotals.length != nCols) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        Arrays.fill(columnTotals, 0.0);  //clear out the array

        //Sum values in the user supplied array
        for (int c = 0; c < nCols; ++c) {
            for (int r = 0; r < nRows; ++r) {
                columnTotals[c] += this.values[r][c];
            }
        }
    }

    /**
     * Return a reference to the values of this matrix.
     * @return the values
     */
    public float[][] getValues() {
        return values;
    }

    /**
     * Copy the values of this matrix.
     * @return the copied values
     */
    public float[][] copyValues2D() {
        float v[][] = new float[nRows][nCols];

        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                v[r][c] = values[r][c];
            }
        }

        return v;
    }

    /**
     * Computes the sum of the matrix by adding all the values in the matrix.
     * @return the sum of all values in the matrix
     */
    public double getSum() {
        double sum = 0.0;
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                sum += values[r][c];
            }
        }
        return sum;
    }

    /**
     * Finds the maximum value of the matrix.
     * @return the maximum value of the matrix
     */
    public float getMax() {
        float max=values[0][0];
        for (int r=0;r<nRows;r++){
            for(int c=0;c<nCols;c++){
                if(max < values[r][c])
                    max = values[r][c];
            }
        }
        return max;
    }

    /**
     * Finds the minimum value of the matrix.
     * @return the minimum value of the matrix
     */
    public float getMin() {
        float min=values[0][0];
        for (int r=0;r<nRows;r++){
            for(int c=0;c<nCols;c++){
                if(min > values[r][c])
                    min = values[r][c];
            }
        }
        return min;
    }

    /**
     * Counts the number of values=0 in the matrix.
     * @return the number of values=0 in the matrix
     */
    public int getZeroCount() {
        int nZeros=0;
        for (int r=0;r<nRows;r++){
            for(int c=0;c<nCols;c++){
                if(values[r][c]==0.0f)
                    nZeros++;
            }
        }
        return nZeros;
    }

    /**
     * Return the internal position in the values[][] array based on an external
     * row or col number. Assumes row and column numbers are the same. An Exception
     * is thrown if they are not.
     *
     * @return the internal row or col number
     */
    public int getInternalNumber(int externalRowNumber) {
        if (! externalRowColValuesEqual) {
            throw new MatrixException("row and column numbers are not equal. use getInternalRowNumber() or getInternalColumnNumber() instead");
        }
        return (internalRowNumbers[externalRowNumber]);
    }

    /**
     * Return the internal position in the values[][] array based on an external
     * row number.
     *
     * @return the internal row or col number
     */
    public int getInternalRowNumber(int externalRowNumber) {
        return (internalRowNumbers[externalRowNumber]);
    }

    /**
     * Return the internal position in the values[][] array based on an external
     * row number.
     *
     * @return the internal row or col number
     */
    public int getInternalColumnNumber(int externalColumnNumber) {
        return (internalColumnNumbers[externalColumnNumber]);
    }

    /**
     * Return an external row/col number based on an array postion in the values[][] array.
     * Used for printing out matrix values. Assumes row and column numbers are the same. An Exception
     * is thrown if they are not.
     *
     * @return the external row or col number
     */
    public int getExternalNumber(int internalNumber) {
        if (! externalRowColValuesEqual) {
            throw new MatrixException("row and column numbers are not equal. use getExternalRowNumber() or getExternalColumnNumber() instead");
        }

        //Array is zero based, must add one
        return (externalRowNumbers[internalNumber+1]);
    }

    /**
     * Return an external row number based on an array postion in the values[][] array.
     * Used for printing out matrix values.
     *
     * @return the external row number
     */
    public int getExternalRowNumber(int internalRowNumber) {
        //Array is zero based, must add one
        return (externalRowNumbers[internalRowNumber+1]);
    }

    /**
     * Return an external column number based on an array postion in the values[][] array.
     * Used for printing out matrix values.
     *
     * @return the external column number
     */
    public int getExternalColumnNumber(int internalColumnNumber) {
        //Array is zero based, must add one
        return (externalColumnNumbers[internalColumnNumber+1]);
    }

    //------------------------ Setters ------------------------

    /**
     * Set the name of this matrix.
     * @param name the name of the matrix
     */
    public void setName(String name) {
        this.name = name;
    }

    /**
     * Set the description of this matrix.
     * @param description the description of the matrix
     */
    public void setDescription(String description) {
        this.description = description;
    }

    /**
     * Set the external element numbering for this matrix. This is often used
     * for non-sequential numbering. (i.e. skipping zone numbers.)
     *
     * This is a convenience method to be used when the row and column number is
     * the same.
     *
     * Note: External numbering should start in externalNumbers[1] and be sorted
     *       from lowest to highest.
     *
     * @param externalNumbers list of external numbers.
     */
    public void setExternalNumbers(int[] externalNumbers) throws MatrixException {
            setExternalNumbers(externalNumbers, externalNumbers);
    }

    /**
	 * Set the external element numbering for this matrix. This is often used
	 * for non-sequential numbering. (i.e. skipping zone numbers.)
     *
     * This method should be used when the row and column numbering is different.
	 *
	 * Note: External numbering should start in externalNumbers[1] and be sorted
	 *       from lowest to highest.
	 *
     * @param externalRowNumbers list of external numbers.
     * @param externalColumnNumbers list of external numbers.
	 */
	public void setExternalNumbers(int[] externalRowNumbers, int[] externalColumnNumbers) throws MatrixException {

        int highestRowNumber = 0;
        int highestColumnNumber = 0;

		//Copy values from user array
        int rowLen = externalRowNumbers.length;
        int colLen = externalColumnNumbers.length;

        this.externalRowNumbers = new int[rowLen];
        this.externalColumnNumbers = new int[colLen];



        //Assign external row numbers
		try {
			for (int i=1; i < rowLen; i++) {
                this.externalRowNumbers[i] = externalRowNumbers[i];
				highestRowNumber = Math.max(highestRowNumber, externalRowNumbers[i]);
			}
		}
		catch (RuntimeException e) {
			throw new MatrixException(e, "Error assigning external row numbers.");
		}

        //Assign external column numbers
        try {
            for (int i=1; i < colLen; i++) {
                this.externalColumnNumbers[i] = externalColumnNumbers[i];
                highestColumnNumber = Math.max(highestColumnNumber, externalColumnNumbers[i]);
            }
        }
        catch (RuntimeException e) {
            throw new MatrixException(e, "Error assigning external column numbers.");
        }

        checkExternalRowColValuesAreEqual();

        //Initialize the internal numbering by storing the position of each external number
        this.internalRowNumbers = new int[highestRowNumber+1];
        this.internalColumnNumbers = new int[highestColumnNumber+1];

		//-1 denotes unused row/col numbers in a sequence
        Arrays.fill(this.internalRowNumbers,  -1);
        Arrays.fill(this.internalColumnNumbers,  -1);

        //needed by Row and Column vectors
        this.internalRowNumbers[0] = 0;
        this.internalColumnNumbers[0] = 0;

        //Build internal row/column number arrays - Given an external number
        //return the internal position
        for (int i=1; i < rowLen; i++) {
            this.internalRowNumbers[ this.externalRowNumbers[i] ] = i-1;
        }
        for (int i=1; i < colLen; i++) {
            this.internalColumnNumbers[ this.externalColumnNumbers[i] ] = i-1;
        }

    }

    /**
     * Set the external element numbering for this matrix. This is often used
     * for non-sequential numbering. (i.e. skipping zone numbers.)
     *
     * Note: External numbering should start in externalNumbers[0] and be sorted
     *       from lowest to highest.
     *
     * @param externalNumbers list of external numbers.
     */
    public void setExternalNumbersZeroBased(int[] externalNumbers) throws MatrixException {
        setExternalNumbersZeroBased(externalNumbers, externalNumbers);
    }

    /**
	 * Set the external element numbering for this matrix. This is often used
	 * for non-sequential numbering. (i.e. skipping zone numbers.)
	 *
	 * Note: External numbering should start in externalNumbers[0] and be sorted
	 *       from lowest to highest.
	 *
     * @param externalRowNumbers list of external row numbers.
     * @param externalColumnNumbers list of external column numbers.
	 */
	public void setExternalNumbersZeroBased(int[] externalRowNumbers, int[] externalColumnNumbers) throws MatrixException {

        int highestRowNumber = 0;
        int highestColumnNumber = 0;

		//Copy values from user array
        int rowLen = externalRowNumbers.length+1;
        int colLen = externalColumnNumbers.length+1;

        this.externalRowNumbers = new int[rowLen];
        this.externalColumnNumbers = new int[colLen];

        //Assign external row numbers
        try {
			for (int i=1; i < rowLen; i++) {
				this.externalRowNumbers[i] = externalRowNumbers[i-1];
				highestRowNumber = Math.max(highestRowNumber, externalRowNumbers[i-1]);
			}
		}
		catch (RuntimeException e) {
			throw new MatrixException(e, "Error assigning external row numbers.");
		}

        //Assign external column numbers
        try {
			for (int i=1; i < colLen; i++) {
				this.externalColumnNumbers[i] = externalColumnNumbers[i-1];
				highestColumnNumber = Math.max(highestColumnNumber, externalColumnNumbers[i-1]);
			}
		}
		catch (RuntimeException e) {
			throw new MatrixException(e, "Error assigning external column numbers.");
		}

        checkExternalRowColValuesAreEqual();

        //Initialize the internal numbering by storing the position of each external number
        this.internalRowNumbers = new int[highestRowNumber+1];
        this.internalColumnNumbers = new int[highestColumnNumber+1];

		//-1 denotes unused row/col numbers in a sequence
        Arrays.fill(this.internalRowNumbers,  -1);
        Arrays.fill(this.internalColumnNumbers,  -1);

        //needed by Row and Column vectors
        this.internalRowNumbers[0] = 0;
        this.internalColumnNumbers[0] = 0;

        // this.externals[] is ones-based
        for (int i=1; i < rowLen; i++) {
            this.internalRowNumbers[ this.externalRowNumbers[i] ] = i-1;
        }
        // this.externals[] is ones-based
        for (int i=1; i < colLen; i++) {
            this.internalColumnNumbers[ this.externalColumnNumbers[i] ] = i-1;
        }
	}

    //check if external row and column numbers are the same
    private void checkExternalRowColValuesAreEqual() {
        int rowLen = this.externalRowNumbers.length;
        int colLen = this.externalColumnNumbers.length;

        externalRowColValuesEqual = true;
        if (rowLen == colLen) {
            for (int i=0; i < rowLen; i++) {
                if (this.externalRowNumbers[i] != this.externalColumnNumbers[i]) {
                    externalRowColValuesEqual = false;
                    break;
                }
            }
        }
        else {
            externalRowColValuesEqual = false;
        }

    }

    /**
     * Set the value of element [r,c].
     * @param itaz the row index
     * @param jtaz the column index
     * @param value the value
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public void setValueAt(int itaz, int jtaz, float value) throws MatrixException {
    	int r = getInternalRowNumber(itaz);
        int c = getInternalColumnNumber(jtaz);

        if ((r < 0) || (r >= nRows) || (c < 0) || (c >= nCols)) {
        	logger.info("Cannot set value in row " + r + " column " + c + " of matrix " + name);
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        values[r][c] = value;
    }

    /**
     * Add double values to a matrix "safely."  Since a matrix holds floats, double values
     * beyond the precision of a float may get cast to unexpected/undesired values.  This method allows the user to set
     * "infinity" proxies; that is, double values that are beyond the range of floats (too large - positive/negative)
     * are set to a specified value.
     *
     * @param itaz
     * @param jtaz
     * @param value
     * @param negativeInfinityValue
     * @param positiveInfinityValue
     * @throws MatrixException
     */
    public void setDoubleValueAt(int itaz, int jtaz, double value, float negativeInfinityValue, float positiveInfinityValue) throws MatrixException {
        float floatValue;
        if (value < -1*Float.MAX_VALUE)
            floatValue = negativeInfinityValue;
        else if (value > Float.MAX_VALUE)
            floatValue = positiveInfinityValue;
        else
            floatValue = (float) value;
        setValueAt(itaz,jtaz,floatValue);
    }


    /**
     * Add the additionalValue to the existing value of element [r,c].
     * @param itaz the row index
     * @param jtaz the column index
     * @param additionalValue the value
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     */
    public void addToValueAt(int itaz, int jtaz, float additionalValue) throws MatrixException {
    	float existingValue = getValueAt(itaz, jtaz);
    	float totalValue = existingValue + additionalValue;
    	setValueAt(itaz, jtaz, totalValue);
    }

    /**
     * Set this matrix from a 2-d array of values.
     * If the rows do not have the same length, then the matrix
     * column count is the length of the shortest row.
     * @param values the 2-d array of values
     */
    protected void setValues(float values[][]) {
        this.nRows = values.length;
        if (values.length==1) this.nCols = values[0].length;
        else this.nCols = values[1].length;
        this.values = values;

        for (int r = 1; r < nRows; ++r) {
            nCols = Math.min(nCols, values[r].length);
        }
    }

    /**
     * Set a row of this matrix from a row vector.
     * @param rv the row vector
     * @param row the row index
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *                                        an invalid vector size
     */
    public void setRow(RowVector rv, int row) throws MatrixException {
        int r = getInternalRowNumber(row);

        if ((r < 0) || (r >= nRows)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }
        if (nCols != rv.nCols) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        for (int c = 0; c < nCols; ++c) {
            this.values[r][c] = rv.values[0][c];
        }
    }

    /**
     * Set a row of this matrix from a float array.
     * @param rowValues the new values for a row
     * @param row the row index
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *                                        an invalid vector size
     */
    public void setRow(float[] rowValues, int row) throws MatrixException {
        int r = getInternalRowNumber(row);

        if ((r < 0) || (r >= nRows)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }

        if (rowValues.length != nCols) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        for (int c = 0; c < nCols; ++c) {
            this.values[r][c] = rowValues[c];
        }
    }

    /**
     * Set a column of this matrix from a column vector.
     * @param cv the column vector
     * @param col the column index
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *                                        an invalid vector size
     */
    public void setColumn(ColumnVector cv, int col) throws MatrixException {
        int c = getInternalColumnNumber(col);

        if ((c < 0) || (c >= nCols)) {
            throw new MatrixException(MatrixException.INVALID_INDEX);
        }
        if (nRows != cv.nRows) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        for (int r = 0; r < nRows; ++r) {
            this.values[r][c] = cv.values[r][0];
        }
    }

    /**
     * Fills all matrix cells with a new value.
     * @param value the new value for each cell in the matrix
     */
    public void fill (float value) {

        //Fill each cell with the new value
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                values[r][c] = value;
            }
        }
    }

    /**
     * Scales the values in the matrix by a value. This is done by multiplying
     * each cell in the matrix by a constant value.
     * Note: This operation happens in place.
     * @param value the new value for each cell in the matrix
     */
    public void scale (float value) {

        //Multiply each value with the new value
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                values[r][c] *= value;
            }
        }
    }

    //------------------------ Operations ------------------------

    /**
     * Return the transpose of this matrix.
     * @return the transposed matrix
     */
    public Matrix getTranspose() {

        float tv[][] = new float[nCols][nRows];  // transposed values

        // Set the values of the transpose.
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                tv[c][r] = values[r][c];
            }
        }

        Matrix returnMatrix = new Matrix(tv);
        returnMatrix.setExternalNumbers(this.getExternalColumnNumbers(), this.getExternalRowNumbers());

        return returnMatrix;
    }

    /**
     * Add another matrix to this matrix.
     * @param m the matrix addend
     * @return the sum matrix
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public Matrix add(Matrix m) throws MatrixException {
        // Validate m's size.
        if ((nRows != m.nRows) && (nCols != m.nCols)) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        Matrix sv = new Matrix(getRowCount(), getColumnCount());
        sv.setExternalNumbers(getExternalRowNumbers(), getExternalColumnNumbers());

        // Compute values of the sum.
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                sv.values[r][c] = values[r][c] + m.values[r][c];
            }
        }

        return sv;
    }

    /**
     * Subtract another matrix from this matrix.
     * @param m the matrix subrrahend
     * @return the difference matrix
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public Matrix subtract(Matrix m) throws MatrixException {
        // Validate m's size.
        if ((nRows != m.nRows) && (nCols != m.nCols)) {
            throw new MatrixException(
                    MatrixException.INVALID_DIMENSIONS);
        }

        Matrix dv = new Matrix(nRows, nCols);
        dv.setExternalNumbers(getExternalRowNumbers(), getExternalColumnNumbers());

        // Compute values of the difference.
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                dv.values[r][c] = values[r][c] - m.values[r][c];
            }
        }

        return dv;
    }

    /**
     * Multiply this matrix by a constant.
     * @param k the constant
     * @return the product matrix
     */
    public Matrix multiply(float k) {
        Matrix pv = new Matrix(nRows, nCols);
        pv.setExternalNumbers(getExternalRowNumbers(), getExternalColumnNumbers());

        // Compute values of the product.
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                pv.values[r][c] = k * values[r][c];
            }
        }

        return pv;
    }

    /**
     *
     * Multiply this matrix by another matrix.  (in the case of nxm * mxs, the
     * resulting matrix will be nxs and will have the first matrix's external
     * row numbers and the second matrix's external column numbers.)
     * @param m the matrix multiplier
     * @return the product matrix
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    //TODO test this method.
    public Matrix multiply(Matrix m) throws MatrixException {
        // Validate m's dimensions.
        if (nCols != m.nRows) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
        }

        Matrix pv = new Matrix(nRows, nCols);
        pv.setExternalNumbers(getExternalRowNumbers(), m.getExternalColumnNumbers());

        // Compute values of the product.
        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < m.nCols; ++c) {
                float dot = 0;
                for (int k = 0; k < nCols; ++k) {
                    dot += values[r][k] * m.values[k][c];
                }
                pv.values[r][c] = dot;
            }
        }

        return pv;
    }

    /**
     * Multiply this matrix by a column vector: this*cv
     * @param cv the column vector
     * @return the product column vector
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public ColumnVector multiply(ColumnVector cv) throws MatrixException {
        // Validate cv's size.
        if (nCols != cv.nRows) {
            throw new MatrixException(
                    MatrixException.INVALID_DIMENSIONS);
        }

        ColumnVector pv = new ColumnVector(nRows);
        pv.setExternalNumbers(getExternalRowNumbers());

        // Compute the values of the product.
        for (int r = 0; r < nRows; ++r) {
            float dot = 0;
            for (int c = 0; c < nCols; ++c) {
                dot += values[r][c] * cv.values[c][0];
            }
            pv.values[r][0] = dot;
        }

        return pv;
    }

    /**
     * Multiply a matrix by a row vector: rv*this
     *  (a 1x3 can multiply a 3x5 - but a 1x3 cannot mulitply a 5x3)
     * @param rv the row vector
     * @return the product row vector
     * @throws com.pb.common.matrix.MatrixException for invalid size
     */
    public RowVector multiply(RowVector rv) throws MatrixException {
        // Validate rv's size.
        if (nRows != rv.nCols) {
            throw new MatrixException(
                    MatrixException.INVALID_DIMENSIONS);
        }

        RowVector pv = new RowVector(nCols);
        pv.setExternalNumbers(getExternalColumnNumbers());

        // Compute the values of the product.
        for (int c = 0; c < getColumnCount(); ++c) {
            float dot = 0;
            for (int r = 0; r < nRows; ++r) {
                dot += rv.values[0][r] * values[r][c];
            }
            pv.values[0][c] = dot;
        }

        return pv;
    }


    /**
     * Make a deep copy of this matrix object. A deep copy includes a complete
     * copy of all the data.
     */
    @Override
    public Object clone() {

        float[][] newValues = new float[nRows][nCols];

        //Copy values from existing matrix into new values array
        for (int i=0; i < this.nRows; i++) {
            for (int j=0; j < this.nCols; j++) {
                newValues[i][j] = this.values[i][j];
            }
        }

        //Create new matrix with new values array
        Matrix m = new Matrix(this.name, this.description, newValues);
        m.setExternalNumbers(this.externalRowNumbers, this.externalColumnNumbers);

        return m;
    }

    /**
     * Write a statistic report of the matrix showing sum, min, max
     * and number of zero values to the debug logger.
     */
    public void logMatrixStats(){

        double sum = getSum();
        float min = getMin();
        float max = getMax();
        int nZeros= getZeroCount();

        logger.info( "The sum of the matrix values is " + sum);
        logger.info( "The minimum value is " + min );
        logger.info( "The maximum value is " + max);
        logger.info( "The number of zero values is " + nZeros);
    }


    /**
     * Write a summary statistic report of the matrix values to the info logger.
     */
    public void logMatrixStatsToInfo(){
        logMatrixStatsToLogger( logger );
    }

    public void logMatrixStatsToInfo( Logger myLogger ){
        logMatrixStatsToLogger( myLogger );
    }

    private void logMatrixStatsToLogger( Logger logger ){

    	int minExtR = 999999999;
    	int maxExtR = 0;
    	int minExtC = 999999999;
    	int maxExtC = 0;
    	int negativeInfinityCount = 0;
    	int positiveInfinityCount = 0;
    	int nanCount = 0;
    	int zeroCount = 0;
    	int negativeCount = 0;
    	int positiveCount = 0;
    	int[] onePercentBins = new int[100+1];
    	float[] onePercentValues = new float[100+1];
    	float sumNegative = 0.0f;
    	float sumPositive = 0.0f;

        float[] sortValues = new float[nRows*nCols];

        ArrayList<int[]> negInfRowColList = new ArrayList<int[]>();

        int k = 0;

        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
            	if ( this.externalRowNumbers[r+1] < minExtR )
            		minExtR = this.externalRowNumbers[r+1];
            	else if ( this.externalRowNumbers[r+1] > maxExtR )
            		maxExtR = this.externalRowNumbers[r+1];
            	if ( this.externalColumnNumbers[c+1] < minExtC )
            		minExtC = this.externalColumnNumbers[c+1];
            	else if ( this.externalColumnNumbers[c+1] > maxExtC )
            		maxExtC = this.externalColumnNumbers[c+1];

            	if ( values[r][c] == Float.NEGATIVE_INFINITY) {
            	    int[] rowCol = new int[2];
                    rowCol[0] = externalRowNumbers[r+1];
                    rowCol[1] = externalColumnNumbers[c+1];
                    negInfRowColList.add( rowCol );
            		negativeInfinityCount++;
            	}
            	else if ( values[r][c] == Float.POSITIVE_INFINITY) {
            		positiveInfinityCount++;
            	}
            	else if ( values[r][c] == Float.NaN) {
            		nanCount++;
            	}
            	else if ( values[r][c] == 0) {
            		sortValues[k++] = values[r][c];
            		zeroCount++;
            	}
            	else if ( values[r][c] < 0) {
            		sortValues[k++] = values[r][c];
            		negativeCount++;
            		sumNegative += values[r][c];
            	}
            	else if ( values[r][c] > 0) {
            		sortValues[k++] = values[r][c];
            		positiveCount++;
            		sumPositive += values[r][c];
            	}

            }
        }

        Arrays.sort( sortValues, 0, k );

        int bin = 0;
        if (k != 0 ) {
            for (int i=0; i < k; i++) {
                bin = (int)(100.0*((double)i/k));
                if(bin < 0) logger.info("k: " + k + " i: " + i + " bin: " + 100*i/k);
                onePercentBins[bin]++;
                onePercentValues[bin] = sortValues[i];

            }
        }


        logger.info( "Summary Statistics");
        logger.info( "Matrix Name is " + getName() );
        logger.info( "Matrix Description is " + getDescription() );

        logger.info( "" );
        logger.info( "The number of rows is " + nRows);
        logger.info( "The number of columns is " + nCols);
        logger.info( "The range of external row numbers is [" + minExtR + "," + maxExtR + "].");
        logger.info( "The range of external column numbers is [" + minExtC + "," + maxExtC + "].");
        logger.info( "The number of NEG_INFINITY valued cells is " + negativeInfinityCount);
        if ( negativeInfinityCount > 0 )
            logger.info( "      NEG_INFINITY cells: [ " + getStatsLogListString(negInfRowColList) + " ].");
        logger.info( "The number of POS_INFINITY valued cells is " + positiveInfinityCount);
        logger.info( "The number of NaN valued cells is " + nanCount);
        logger.info( "The number of zero valued cells is " + zeroCount);
        logger.info( "The number of negative, non-zero valued cells is " + negativeCount);
        logger.info( "The number of positive, non-zero valued cells is " + positiveCount);
        logger.info( "The number of all finite valued cells is " + (zeroCount + negativeCount + positiveCount) );
        logger.info( "The total number of matrix cells is " + (nRows*nCols) );

        logger.info( "" );
        logger.info( "The minimum finite cell value is " + sortValues[0] );
        logger.info( "The 5th percentile finite cell value is " + onePercentValues[5] );
        logger.info( "The 25th percentile finite cell value is " + onePercentValues[25] );
        logger.info( "The 50th percentile finite cell value is " + onePercentValues[50] );
        logger.info( "The 75th percentile finite cell value is " + onePercentValues[75] );
        logger.info( "The 95th percentile finite cell value is " + onePercentValues[95] );
        logger.info( "The maximum finite cell value is " + sortValues[k-1] );

        logger.info( "" );
        logger.info( "The total of negative finite cell values is " + sumNegative );
        logger.info( "The total of positive finite cell values is " + sumPositive );
        logger.info( "The total of finite cell values is " + (sumNegative + sumPositive) );
        logger.info( "The mean finite cell value is " + ((sumNegative + sumPositive)/(zeroCount + negativeCount + positiveCount)) );

    }

    /**
     * Write a summary statistic report of the matrix values to the console output.
     */
    public void logMatrixStatsToConsole(){

    	int minExtR = 999999999;
    	int maxExtR = 0;
    	int minExtC = 999999999;
    	int maxExtC = 0;
    	int negativeInfinityCount = 0;
    	int positiveInfinityCount = 0;
    	int nanCount = 0;
    	int zeroCount = 0;
    	int negativeCount = 0;
    	int positiveCount = 0;
    	int[] onePercentBins = new int[100+1];
    	float[] onePercentValues = new float[100+1];
    	float sumNegative = 0.0f;
    	float sumPositive = 0.0f;

        float[] sortValues = new float[nRows*nCols];

        int k = 0;

        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
            	if ( this.externalRowNumbers[r+1] < minExtR )
            		minExtR = this.externalRowNumbers[r+1];
            	else if ( this.externalRowNumbers[r+1] > maxExtR )
            		maxExtR = this.externalRowNumbers[r+1];
            	if ( this.externalColumnNumbers[c+1] < minExtC )
            		minExtC = this.externalColumnNumbers[c+1];
            	else if ( this.externalColumnNumbers[c+1] > maxExtC )
            		maxExtC = this.externalColumnNumbers[c+1];

            	if ( values[r][c] == Float.NEGATIVE_INFINITY) {
            		negativeInfinityCount++;
            	}
            	else if ( values[r][c] == Float.POSITIVE_INFINITY) {
            		positiveInfinityCount++;
            	}
            	else if ( values[r][c] == Float.NaN) {
            		nanCount++;
            	}
            	else if ( values[r][c] == 0) {
            		sortValues[k++] = values[r][c];
            		zeroCount++;
            	}
            	else if ( values[r][c] < 0) {
            		sortValues[k++] = values[r][c];
            		negativeCount++;
            		sumNegative += values[r][c];
            	}
            	else if ( values[r][c] > 0) {
            		sortValues[k++] = values[r][c];
            		positiveCount++;
            		sumPositive += values[r][c];
            	}

            }
        }

        Arrays.sort( sortValues, 0, k );

        int bin = 0;
        if (k != 0 ) {
            for (int i=0; i < k; i++) {
                bin = (int)(100.0*((double)i/k));
                if(bin < 0) System.out.println("k: " + k + " i: " + i + " bin: " + 100*i/k);
                onePercentBins[bin]++;
                onePercentValues[bin] = sortValues[i];

            }
        }


        System.out.println( "Summary Statistics");
        System.out.println( "Matrix Name is " + getName() );
        System.out.println( "Matrix Description is " + getDescription() );

        System.out.println( "" );
        System.out.println( "The number of rows is " + nRows);
        System.out.println( "The number of columns is " + nCols);
        System.out.println( "The range of external row numbers is [" + minExtR + "," + maxExtR + "].");
        System.out.println( "The range of external column numbers is [" + minExtC + "," + maxExtC + "].");
        System.out.println( "The number of NEG_INFINITY valued cells is " + negativeInfinityCount);
        System.out.println( "The number of POS_INFINITY valued cells is " + positiveInfinityCount);
        System.out.println( "The number of NaN valued cells is " + nanCount);
        System.out.println( "The number of zero valued cells is " + zeroCount);
        System.out.println( "The number of negative, non-zero valued cells is " + negativeCount);
        System.out.println( "The number of positive, non-zero valued cells is " + positiveCount);
        System.out.println( "The number of all finite valued cells is " + (zeroCount + negativeCount + positiveCount) );
        System.out.println( "The total number of matrix cells is " + (nRows*nCols) );

        System.out.println( "" );
        System.out.println( "The minimum finite cell value is " + sortValues[0] );
        System.out.println( "The 5th percentile finite cell value is " + onePercentValues[5] );
        System.out.println( "The 25th percentile finite cell value is " + onePercentValues[25] );
        System.out.println( "The 50th percentile finite cell value is " + onePercentValues[50] );
        System.out.println( "The 75th percentile finite cell value is " + onePercentValues[75] );
        System.out.println( "The 95th percentile finite cell value is " + onePercentValues[95] );
        System.out.println( "The maximum finite cell value is " + sortValues[k-1] );

        System.out.println( "" );
        System.out.println( "The total of negative finite cell values is " + sumNegative );
        System.out.println( "The total of positive finite cell values is " + sumPositive );
        System.out.println( "The total of finite cell values is " + (sumNegative + sumPositive) );
        System.out.println( "The mean finite cell value is " + ((sumNegative + sumPositive)/(zeroCount + negativeCount + positiveCount)) );

    }


    private String getStatsLogListString( ArrayList<int[]> negInfRowColList ) {
        String returnString = "";

        int[] rowCol = negInfRowColList.get( 0 );
        returnString += "(" + rowCol[0] + "," + rowCol[1] + ")";

        for ( int i=1; i < negInfRowColList.size(); i++ ) {
            rowCol = negInfRowColList.get( i );
            returnString += ", (" + rowCol[0] + "," + rowCol[1] + ")";
        }

        return returnString;

    }

    public void printArray(int[] arrayToPrint){
        for (int c = 0; c < arrayToPrint.length; ++c) {
                System.out.printf("%7d", arrayToPrint[c]);
            }
            System.out.println();
    }

    public void printArray(float[] arrayToPrint){
        for (int c = 0; c < arrayToPrint.length; ++c) {
                System.out.printf("%7.2f", arrayToPrint[c]);
            }
            System.out.println();
    }

    /**
     * Get a square sub-matrix.
     *
     * @param externalNumbers a 1-indexed array of zones to use for the
     *            sub-matrix
     */
    public Matrix getSubMatrix(int[] externalNumbers) {
        return getSubMatrix(externalNumbers, externalNumbers);
    }

    /**
     * Get a rectuangular sub-matrix.
     *
     * @param rowExternalNumbers a 1-indexed array of row zones
     * @param colExternalNumbers a 1-indexed array of column zones
     */
    public Matrix getSubMatrix(int[] rowExternalNumbers,
            int[] colExternalNumbers) {
        Matrix matrix = new Matrix(rowExternalNumbers.length - 1,
                colExternalNumbers.length - 1);
        matrix.setExternalNumbers(rowExternalNumbers, colExternalNumbers);

        for (int r = 1; r < rowExternalNumbers.length; ++r) {
            int row = rowExternalNumbers[r];

            for (int c = 1; c < colExternalNumbers.length; ++c) {
                int col = colExternalNumbers[c];
                float value = getValueAt(row, col);

                matrix.setValueAt(row, col, value);
            }
        }

        return matrix;
    }

    /**
     * Get a square sub-matrix.
     *
     * @param set set of zones in the sub-matrix
     */
    public Matrix getSubMatrix(Set<Integer> set) {
        return getSubMatrix(createExternalNumbers(set));
    }

    /**
     * Get a rectangular sub-matrix.
     *
     * @param rowSet set of rows in the sub-matrix
     * @param colSet set of columns in the sub-matrix
     */
    public Matrix getSubMatrix(Set<Integer> rowSet, Set<Integer> colSet) {
        return getSubMatrix(createExternalNumbers(rowSet),
                createExternalNumbers(colSet));
    }

    /**
     * Create an array of external numbers from a Set.
     */
    public static int[] createExternalNumbers(Set<Integer> set) {
        int[] extArray;
        int i;

        if (set.contains(0)) {
            extArray = new int[set.size()];
            i = 0;
        } else {
            extArray = new int[set.size() + 1];
            i = 1;
        }

        for (int n : set) {
            extArray[i] = n;
            i += 1;
        }

        Arrays.sort(extArray);

        return extArray;
    }

    /**
     * Set the intrazonals to 1/2 distance to nearest neighbor
     *
     */
    public void setIntrazonalToHalfNearestNeighbor(){
        for (int r = 0; r <  getRowCount(); ++r) {
            float minRowValue=Float.MAX_VALUE;
            for (int c = 0; c < getColumnCount(); ++c) {
               if(r!=c)
                   minRowValue = Math.min(minRowValue, values[r][c]);
            }

            if(r<getColumnCount())
                values[r][r]=(float)0.5*minRowValue;
           }
    }
}