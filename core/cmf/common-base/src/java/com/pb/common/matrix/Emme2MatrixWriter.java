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

import com.pb.common.emme2.io.Emme2DataBank;

import java.io.File;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import org.apache.log4j.Logger;


/**
 * Implementes a MatrixWriter to write matrices to an emme2ban file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 */
public class Emme2MatrixWriter extends MatrixWriter {

 
    public static final int VERSION   = 1;
    public static final int WORDSIZE  = 4;

    private Emme2DataBank dataBank;
    protected static Logger logger = Logger.getLogger(Emme2MatrixWriter.class);
 

    /**
     * @param file represents the physical matrix file
     */
    public Emme2MatrixWriter(File file) {
        this.file = file;
        openDatabank();
    }


    public void writeMatrix(Matrix m) throws MatrixException {
        throw new UnsupportedOperationException("Use method, writeMatrix(\"index\", Matrix)");
    }


    public void writeMatrix(String index, Matrix m) throws MatrixException {

        writeData( index, m );
    }

    /**
     * Open the Emme2 databank file for writing.
     */
    private void openDatabank() {

        try {
            dataBank = new Emme2DataBank( file );
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + " " + file);
        }
    }

    /**
     * Write a row to the databank in a full matrix.
     * 
     * @param matrixName  The name of the full matrix to write to.
     * @param ptaz        The ptaz to write to.
     * @param values      An float array of values to write to the databank.  The values
     * should be 0-init, dimensioned by internal columns.
     */
    public void writeRow(String matrixName, int ptaz, float[] values){
        
        int nRows = dataBank.getZonesUsed();
        int nCols = nRows;
        
        //Big enough to hold entire row, including unused zones
        byte[] byteArray = new byte[dataBank.getMaxZones()*4];
        
        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
        
        //advance byteOffset to row
        int[] internals = dataBank.getInternalZoneNumbers();
        long rowNumber = (long)internals[ptaz];
        byteOffset += (long)(rowNumber-1)*((long)byteArray.length);
        try {
            RandomAccessFile randFile = dataBank.getRandomAccessFile();
            
            randFile.seek(byteOffset);

            ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
            byteBuffer.order( ByteOrder.nativeOrder() );

            //Read float values from byte buffer
            for(int col=0; col < nCols; col++) {
                byteBuffer.putFloat(values[col]);
             }

            //Write out bytes for current row
            randFile.write( byteBuffer.array() );

            byteBuffer.clear();

        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_WRITING_FILE);
        }
    }
    /**
     * Writes a matrix to the underlying file.
     *
     *@param  m  the matrix to write
     *
     */
    private void writeData(String matrixName, Matrix m) {

         //Throws an exception if there are any errors in the matrixName
        Emme2MatrixHelper.checkMatrixName(dataBank, matrixName);

        //Check size of matrix against databank dimensions
        if ( (m.getColumnCount() > dataBank.getMaxZones()) ||
             (m.getRowCount()    > dataBank.getMaxZones()) ) {

            logger.error("Matrix is too big for databank: " + matrixName);
            throw new MatrixException("Matrix is too big for databank: " + matrixName);
        }

        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);

        long startTime = System.currentTimeMillis();

        int[] emme2ExternalNumbers = dataBank.getExternalZoneNumbers();
        //Emme2 matrices are always square so use same value for rows and columns
        int nRows = dataBank.getZonesUsed();
        int nCols = nRows;

        //Allocate a byte buffer to hold one row, must be maximum size of matrix
        ByteBuffer byteBuffer = ByteBuffer.allocate(dataBank.getMaxZones()*4);
        byteBuffer.order(ByteOrder.nativeOrder());

        try {
            RandomAccessFile randFile = dataBank.getRandomAccessFile();
            randFile.seek(byteOffset);

            //Loop through all the rows in the matrix
            for (int row=0; row < nRows; row++) {

                //Fill up byte buffer for each row
                int[] matrixInternalRowNumbers = m.getInternalRowNumbers();
                int[] matrixInternalColumnNumbers = m.getInternalColumnNumbers();
                int matrixRow = -1;
                if (emme2ExternalNumbers[row+1]<matrixInternalRowNumbers.length) {
                    matrixRow = m.getInternalRowNumber(emme2ExternalNumbers[row+1]);
                }
                if (matrixRow == -1) {
                    if (logger.isDebugEnabled()) logger.debug("Emme2 zone "+emme2ExternalNumbers[row+1]+" at index "+row+" is not represented in matrix "+m);
                }
                for(int col=0; col < nCols; col++) {
                    float value = 0;
                    int matrixColumn = -1;
                    if (emme2ExternalNumbers[col+1]<matrixInternalColumnNumbers.length) {
                        matrixColumn = m.getInternalColumnNumber(emme2ExternalNumbers[col+1]);
                    }
                    if (matrixColumn !=-1 && matrixRow !=-1) value = m.getValueAt(emme2ExternalNumbers[row+1],emme2ExternalNumbers[col+1]);
                    byteBuffer.putFloat( value );
                }

                //Write out bytes for current row
                randFile.write( byteBuffer.array() );

                byteBuffer.clear();
            }
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_WRITING_FILE);
        }

        long finishTime = System.currentTimeMillis();

        //System.out.println("readData() time = " + (finishTime-startTime));
    }

	/** Writes all tables of an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public void writeMatrices(String[] maxTables, Matrix[] m) throws MatrixException {

	}


}
