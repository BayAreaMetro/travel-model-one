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
 * A matrix or collection of matrices with values stored
 * on disk, rather than in memory.  Because I/O is inefficient, 
 * we only require that implementations be able to read or write
 * one row at a time, not necessarily individual cells.  
 * 
 * @author Greg Erhardt Created on Feb 17, 2009
 * 
 */
public abstract class DiskBasedMatrix {

	public MatrixType type;

	/**
	 * Factory method to create a concrete DiskBasedMatrix class.
	 * The matrix should already exist, and will be opened for editing.
	 * 
	 * @param type
	 *            a type-safe enumeration of matrix types.
	 * @param file
	 *            the physical file containing the matrix.
	 * @return a concrete DiskBasedMatrix.
	 * @throws MatrixException
	 */
	public static DiskBasedMatrix openMatrix(MatrixType type, File file)
			throws MatrixException {

		DiskBasedMatrix matrix;

		if (type.equals(MatrixType.TRANSCAD)) {
			matrix = new TranscadMatrix(file);
		} else {
			throw new MatrixException(MatrixException.INVALID_TYPE + ", " + type);
		}

		matrix.type = type;
		return matrix;
	}

	/**
	 * Factory method to create a concrete DiskBasedMatrix class.
	 * The matrix should already exist, and will be opened for editing.
	 * 
	 * @param fileName
	 *            the physical file containing the matrix.
	 * @return a concrete DiskBasedMatrix.
	 * @throws MatrixException
	 */
	public static DiskBasedMatrix openMatrix(String fileName)
			throws MatrixException {
		File file = new File(fileName);
		MatrixType type = MatrixReader.determineMatrixType(file);
		return openMatrix(type, file);
	}


    /**
     * Factory method to create a concrete DiskBasedMatrix class
     * from scratch.  The matrix will be created empty with float 
     * value format and default compression, with one matrix for 
     * each label.
     * 
     * @param type   The type of matrix to create. 
     * @param file   The path/name of the file to create.
     * @param fileLabel  The label for the matrix file.
     * @param matrixLabels  A vector of labels for each individual matrix in the file. 
     * @param rowIds  External labels for row IDs.  (1-based, with conversion done in here)
     * @param colIds  External lablels for column IDs.  (1-based, with conversion done in here)
     * 
     * Note: External numbering should start in externalNumbers[1] and be sorted
     *       from lowest to highest.
     */
	public static DiskBasedMatrix createMatrix(MatrixType type, File file, String fileLabel, 
			String[] matrixLabels, int[] rowIds, int[] colIds) throws MatrixException {

		DiskBasedMatrix matrix;

		if (type.equals(MatrixType.TRANSCAD)) {
			matrix = new TranscadMatrix(file, fileLabel, matrixLabels, rowIds, colIds);
		} else {
			throw new MatrixException(MatrixException.INVALID_TYPE + ", " + type);
		}

		matrix.type = type;
		return matrix;
	}
	
	
    /**
     * Factory method to create a concrete DiskBasedMatrix class
     * from scratch.  The matrix will be created empty with float 
     * value format and default compression, with one matrix for 
     * each label.
     * 
     * @param fileName  The path/name of the file to create.
     * @param fileLabel  The label for the matrix file.
     * @param matrixLabels  A vector of labels for each individual matrix in the file. 
     * @param rowIds  External labels for row IDs.  (1-based, with conversion done in here)
     * @param colIds  External lablels for column IDs.  (1-based, with conversion done in here)
     * 
     * Note: External numbering should start in externalNumbers[1] and be sorted
     *       from lowest to highest.
     */
	public static DiskBasedMatrix createMatrix(String fileName, String fileLabel, 
			String[] matrixLabels, int[] rowIds, int[] colIds) throws MatrixException {

		File file = new File(fileName);
		MatrixType type = MatrixReader.determineMatrixType(file);
		return createMatrix(type, file, fileLabel, matrixLabels, rowIds, colIds);
	}
	

    
    /*
     * All concrete DiskBasedMatrix classes must implement these methods.
     */
	
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
	abstract public RowVector getRow(int rowID, int matrixNumber) throws MatrixException; 
	
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
	abstract public void setRow(RowVector rv, int rowID, int matrixNumber) throws MatrixException;

	/**
	 * Close the matrix file.  
	 */
	abstract public void close(); 
	
}
