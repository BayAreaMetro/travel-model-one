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

import org.apache.log4j.Logger;

import java.io.File;

/**
 * Implementes a MatrixReader to read matrices from a Transcad file.
 *
 * @author    Joel Freedman
 * @version   1.0, 3/2006
 */
public class TranscadMatrixReader extends MatrixReader {

    protected static Logger logger = Logger.getLogger(TranscadMatrixReader.class);
    
	/**
	 * @param file represents the physical matrix file
	 */
	public TranscadMatrixReader(File file) {
		this.file = file;
	}


    public Matrix readMatrix() throws MatrixException {
        throw new UnsupportedOperationException("Use method, readMatrix(\"" +
                "name\")");
    }

	/**
     * Reads one matrix from a Transcad matrix file
     *
     * @param table
     *            the short name or table number of the matrix
     * @return a complete matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(int table) throws MatrixException {

    	// create the transcadIO object
    	TranscadIO transcadIO = new TranscadIO(file.getPath());

    	// get the ids
        int[] transcadRowIDs = transcadIO.getRowIDs();
        int[] transcadColumnIDs = transcadIO.getColumnIDs();
        Matrix matrix = null;

        try {
            // read the tables in the file and set the Matrix array
            float[][] values = transcadIO.getMatrix(table);
            String label = transcadIO.getMatrixLabel(table);
            matrix = new Matrix(label, label, values);

            // move the external row number array up by one.
            int nRows = transcadIO.getNumberOfRows();
            int[] externalRowNumbers = new int[nRows + 1];
            for (int r = 0; r < nRows; r++) {
                externalRowNumbers[r + 1] = transcadRowIDs[r];
            }

            // move the external column number array up by one.
            int nCols = transcadIO.getNumberOfColumns();
            int[] externalColumnNumbers = new int[nCols + 1];
            for (int r = 0; r < nCols; r++) {
                externalColumnNumbers[r + 1] = transcadColumnIDs[r];
            }

            matrix.setExternalNumbers(externalRowNumbers, externalColumnNumbers);
        } catch (Exception e) {

            logger.fatal("Error: Cannot find matrix " + table
                    + " in Transcad file " + file.getPath());
            throw new RuntimeException(e);
        }

        // close the transcad file
        transcadIO.closeMatrix();

    	return matrix;

    }

    /**
     * Reads one matrix from a Transcad matrix file
     *
     * @param name
     *            the short name or table number of the matrix
     * @return a complete matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(String name) throws MatrixException {

    	// create the transcadIO object
    	TranscadIO transcadIO = new TranscadIO(file.getPath());

        int numberOfMatrices = transcadIO.getNumberOfMatrices();
        logger.info("Reading matrix "+name);

        int matrixToRead = -1;
        for (int i = 0; i < numberOfMatrices; ++i) {
            if (name.compareToIgnoreCase(transcadIO.getMatrixLabel(i)) == 0) {
                matrixToRead = i;
            }
        }

        if (matrixToRead == -1) {
            logger.fatal("Error: Cannot find matrix " + name
                    + " in Transcad file " + file.getPath());
            throw new RuntimeException();
        }

        Matrix matrix = readMatrix(matrixToRead);

        transcadIO.closeMatrix();

        return matrix;
    }

	/** Reads an entire matrix from a transcad matrix file
	 *
	 * @return a complete matrix
	 * @throws MatrixException
	 */
	public Matrix[] readMatrices() throws MatrixException {

        TranscadIO io = new TranscadIO(file.getPath());
        int[] transcadIDs = io.getRowIDs();
        int numberOfMatrices = io.getNumberOfMatrices();

        //move the external number array up by one.
        int nCols = io.getNumberOfColumns();
        int[] externalNumbers = new int[nCols + 1];
        for (int r=0; r < nCols; r++) {
            externalNumbers[r+1] = transcadIDs[r];
        }

        //read the tables in the file and set the Matrix array
        Matrix[] m = new Matrix[numberOfMatrices];
        for(int i=0;i<numberOfMatrices;++i){
            float[][] values = io.getMatrix(i);
            String label = io.getMatrixLabel(i);
            m[i] = new Matrix(label,label, values);
            m[i].setExternalNumbers(externalNumbers);
        }
        
        io.closeMatrix();
        
        return m;
    }

    public static void main(String args[]) throws java.lang.Throwable {
        
   
        TranscadMatrixReader tmr = new TranscadMatrixReader(new File("c:\\projects\\software development\\transcad help\\junk.mtx"));
        logger.info("Reading matrix 2");
        Matrix m = tmr.readMatrix(2);
        float ivt = m.getValueAt(10,9);
        logger.info("ivt at 10,9 = "+ivt);
        ivt = m.getValueAt(9,9);
        logger.info("ivt at 9,9 = "+ivt);
        ivt = m.getValueAt(10,10);
        logger.info("ivt at 10,10 = "+ivt);
        ivt = m.getValueAt(297,296);
        logger.info("ivt at 297,296 = "+ivt);
        ivt = m.getValueAt(297,297);
        logger.info("ivt at 297,297 = "+ivt);
        
    }

        
    /**
     * 
     */

}
