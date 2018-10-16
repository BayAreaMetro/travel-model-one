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

import java.io.*;

/**
 * Implementes a MatrixWriter to write matrices to a binary matrix file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 */
public class BinaryMatrixWriter extends MatrixWriter {

    //Version 2 separates external row and column number arrays
    public static final int VERSION   = 2;
    public static final int WORDSIZE  = 4;

    private RandomAccessFile randFile;


    /**
     * @param file represents the physical matrix file
     */
    public BinaryMatrixWriter(File file) {
        this.file = file;
    }

    public void writeMatrix(Matrix m) throws MatrixException {
        writeMatrix("", m);
    }

    public void writeMatrix(String index, Matrix m) throws MatrixException {
        createBinaryFile();
        writeData( m );
    }

	/** Writes all tables of an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public void writeMatrices(String[] maxTables, Matrix[] m) throws MatrixException {
        throw new MatrixException("method not implemented yet");
	}

    /**
    * Creates the binary file overwriting the file if it exists.
    */
    private boolean createBinaryFile() {
        long length = 0;
        boolean fileExists = false;

        try {
            //Find out if we are overwriting an existing file
            randFile = new RandomAccessFile(file, "rw");
            length = randFile.length();
            if (length != 0)
                fileExists = true;

            randFile.setLength(0L);
        }
        catch (Exception e) {
            e.printStackTrace();
        }
        return fileExists;
    }

    /**
     * Writes a matrix to the underlying file.
     *
     *@param  m  the matrix to write
     *
     */
    private void writeData(Matrix m) {
        //Write header information - version 2 writes out external row and column
        //numbers separately
        try {
            randFile.writeInt(VERSION);
            randFile.writeInt(m.nRows);
            randFile.writeInt(m.nCols);
            randFile.writeInt(m.externalRowNumbers.length);
            randFile.writeInt(m.externalColumnNumbers.length);
            randFile.writeUTF(m.name);
            randFile.writeUTF(m.description);
            for (int i=1; i < m.externalRowNumbers.length; i++) {
                randFile.writeInt(m.externalRowNumbers[i]);
            }
            for (int i=1; i < m.externalColumnNumbers.length; i++) {
                randFile.writeInt(m.externalColumnNumbers[i]);
            }
        }
        catch (IOException e) {
            throw new MatrixException(e, "Error while writing matrix data");
        }

        long startTime = System.currentTimeMillis();

        //Write matrix data values out.
        try {
            //Create a byte array output stream to buffer bytes for one row.
            ByteArrayOutputStream baos = new ByteArrayOutputStream( m.nCols * WORDSIZE );
            DataOutputStream dout = new DataOutputStream(baos);

            for (int row=0; row < m.nRows; row++) {

                //Write contents of a row to the byte array.
                for(int col=0; col < m.nCols; col++) {
                    dout.writeFloat(m.values[row][col]);
                }
                dout.flush();

                //Create a byte array.
                byte byteArray[] = baos.toByteArray();
                randFile.write(byteArray, 0, byteArray.length);

                //Reset stream to use again
                baos.reset();
            }

            //Close underlying file
            randFile.close();
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_WRITING_FILE);
        }

        long finishTime = System.currentTimeMillis();

        //System.out.println("writeData() time = " + (finishTime-startTime));
    }

}
