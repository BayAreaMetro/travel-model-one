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

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.RandomAccessFile;

import org.apache.log4j.Logger;


/**
 * Implementes a MatrixReader to read matrices from a binary matrix file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 */
public class BinaryMatrixReader extends MatrixReader {

    private RandomAccessFile randFile;
    static Logger logger = Logger.getLogger("com.pb.common.matrix");

    //Store header values - used by readData()
    private int version;
    private int nRows;
    private int nCols;
    private String name = "";
    private String description = "";
    private int[] externalRowNumbers;
    private int[] externalColumnNumbers;

    /**
     * @param file represents the physical matrix file
     */
    public BinaryMatrixReader(File file) {
        this.file = file;
        openBinaryFile();
    }

    public Matrix readMatrix() throws MatrixException {
        return readMatrix("");
    }

    public Matrix readMatrix(String index) throws MatrixException {
        readHeader();
        return readData();
    }

    private void openBinaryFile() {
        try {
            randFile = new RandomAccessFile(file, "r");
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + ", "+ file);
        }
    }

	/** Reads and returns an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public Matrix[] readMatrices() throws MatrixException {
		Matrix[] m = null;
        
		return m;
	}


    /**
    * Read matrix information from binary file.
    */
    private void readHeader() {
        int nExternalRows;
        int nExternalColumns;

        try {
            randFile.seek(0L);

            //Read matrix information - version 2 reads external row and column
            //numbers separately
            version = randFile.readInt();
            nRows = randFile.readInt();
            nCols = randFile.readInt();
            nExternalRows = randFile.readInt();

            if (version == 2) {
                nExternalColumns = randFile.readInt();
            } else {
                nExternalColumns = nExternalRows;
            }
            name = randFile.readUTF();
            description = randFile.readUTF();

            externalRowNumbers = new int[nExternalRows];
            for (int i=1; i < nExternalRows; i++) {
                externalRowNumbers[i] = randFile.readInt();
            }

            if (version == 2) {
                externalColumnNumbers = new int[nExternalColumns];
                for (int i=1; i < nExternalColumns; i++) {
                    externalColumnNumbers[i] = randFile.readInt();
                }
            }
            else {
                externalColumnNumbers = externalRowNumbers.clone();
            }
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }
    }

    /**
    * Returns a matrix.
    *
    */
    private Matrix readData() {
        int len;
        float[][] values = new float[nRows][nCols];
        byte[] byteArray = new byte[(nCols)*BinaryMatrixWriter.WORDSIZE];

        long startTime = System.currentTimeMillis();
        try {
            for (int row=0; row < nRows; row++) {
                len = randFile.read(byteArray);  //Perform one read from disk

                //Create a data input stream to read from byte array.
                DataInputStream din = new DataInputStream(new ByteArrayInputStream(byteArray));

                //Read float values from byte array
                for(int col=0; col < nCols; col++) {            
                    values[row][col] = din.readFloat();
                }
                din.close();
            }
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }

        long finishTime = System.currentTimeMillis();
        //System.out.println("readData() time = " + (finishTime-startTime));

        Matrix m = new Matrix(name, description, values); 
        m.setExternalNumbers(externalRowNumbers, externalColumnNumbers);

        return m;
    }
}
