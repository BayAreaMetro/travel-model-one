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

import java.io.File;

/**
 * @author Greg Erhardt 
 * Created on Feb 17, 2009
 *
 */
public class TranscadMatrix extends DiskBasedMatrix {
	
	// data backed by transcad
	private TranscadIO m; 
	
    private int nRows;
    private int nCols;

    /**
     * Given an index in the values[][] array, return the external number.
     * This array is supplied by the user when non-sequential numbering is used.
     */
    public int[] externalRowNumbers;
    public int[] externalColumnNumbers;

        
    /**
     * Constructor to use if opening an existing matrix.
     * 
     * @param file
     */
    public TranscadMatrix(File file){
    	String fileName = file.toString(); 
        m = new TranscadIO(fileName); 
        
        nRows = m.getNumberOfRows(); 
        nCols = m.getNumberOfColumns(); 
        readExternalNumbers(); 
    }
    
    
    /**
     * Constructor to use if creating a new matrix.  
     * The matrix will be created empty with float value format and default compression, with
     * one matrix for each label.
     * 
     * NOTE:  This method requires TransCAD Version 5.0 r2 Build 1635 or later to work properly.
     *        Earlier methods will result in a garbage matrix getting written. 
     * 
     * @param file  The path/name of the file to create.
     * @param fileLabel  The label for the matrix file.
     * @param matrixLabels  A vector of labels for each individual matrix in the file. 
     * @param rowIds  External labels for row IDs.  (1-based, with conversion done in here)
     * @param colIds  External lablels for column IDs.  (1-based, with conversion done in here)  
     */
    public TranscadMatrix(File file,String fileLabel,String[] matrixLabels, int[] rowIds, int[] colIds){
        
    	int numberOfRows    = rowIds.length - 1; 
    	int numberOfColumns = colIds.length - 1; 
    	String fileName = file.toString(); 
    	
    	m = new TranscadIO(fileName, fileLabel, matrixLabels, 
    			numberOfRows, numberOfColumns, rowIds, colIds); 
        
        nRows = m.getNumberOfRows(); 
        nCols = m.getNumberOfColumns(); 
        readExternalNumbers(); 
    }
    
	
    /**
     * Get a row of this matrix.
     * 
     * @param rowID the external row number
     * @param matrixNumber the number of the matrix to get (1-based)
     * @return the row as a row vector
     * 
     * @throws com.pb.common.matrix.MatrixException for an invalid index
     *                  or matrix number
     */ 
	public RowVector getRow(int rowID, int matrixNumber) throws MatrixException {
        
		int singleExternal[] = {0, 1}; 
		
        float values[] = m.getRowAt(rowID, matrixNumber-1); 
        RowVector rv = new RowVector(values); 
        rv.setExternalNumbers(singleExternal, externalColumnNumbers); 
        
        return rv;
	}
	
    /**
     * Set a row of this matrix from a row vector.
     * 
     * @param rv the row vector containing the values
     * @param rowID the external row number
     * @param matrixNumber the number of the matrix to get (1-based)
     * 
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *         an invalid vector size or matrix number
     */
	public void setRow(RowVector rv, int rowID, int matrixNumber) throws MatrixException {
		
		float values[] = new float[nCols]; 
		rv.getRow(1, values); 
		
		m.setRowAt(rowID, matrixNumber-1, values); 
	}

	/**
	 * Close the matrix file.  
	 */
	public void close() {
		m.closeMatrix(); 
	}
	
	
	private void readExternalNumbers() {
		int zeroBasedRows[] = m.getRowIDs(); 
		externalRowNumbers = new int[zeroBasedRows.length+1];
		for (int i=1; i<externalRowNumbers.length; i++) {
			externalRowNumbers[i] = zeroBasedRows[i-1]; 
		}
		
		int zeroBasedCols[] = m.getColumnIDs(); 
		externalColumnNumbers = new int[zeroBasedCols.length+1]; 
		for (int i=1; i<externalColumnNumbers.length; i++) {
			externalColumnNumbers[i] = zeroBasedCols[i-1]; 
		}
	}
    

}
