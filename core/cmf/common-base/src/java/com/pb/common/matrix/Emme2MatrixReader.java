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

/**
 * Implementes a MatrixReader to read matrices from an emme2ban file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/15/2003
 */
public class Emme2MatrixReader extends MatrixReader {

    private Emme2DataBank dataBank;

    //Store header values - used by readData()
    private int version;
    private int nRows;
    private int nCols;
    private String name = "";
    private String description = "";

    /**
     * @param file represents the physical matrix file
     */
    public Emme2MatrixReader(File file) {
        this.file = file;
        openDatabank();
    }

    public Matrix readMatrix() throws MatrixException {
        throw new UnsupportedOperationException("Use method, readMatrix(\"index\")");
    }

    /**
     * Get the emme2 databank info.
     * 
     * @return The emme2 databank.
     */
    public Emme2DataBank getDataBank(){
        return dataBank;
    }
    /** Reads an entire matrix from an Emme2 databank
     *
     * @param index the short name of the matrix, eg. "mf10"
     * @return a complete matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(String index) throws MatrixException {

        return readData( index );
    }

    /**
     * Open the Emme2 databank file for reading. Instantiating the
     * Emme2DataBank class will force the underlying class to read
     * the directory and file structures.
     */
    private void openDatabank() throws MatrixException {

        try {
            dataBank = new Emme2DataBank( file, true );
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
     * Reads a matrix from the Emme2 databank and returns it.
     * @return matrix from Emme2 databank
     */
    private Matrix readData(String matrixName) throws MatrixException {

        //Throws an exception if there are any errors in the matrixName
        Emme2MatrixHelper.checkMatrixName(dataBank, matrixName);

        //temporary; will get thrown away when setting using function
        Matrix m = new Matrix();
        
        int matrixType = dataBank.matrixType(matrixName);
        
        name=matrixName;
 
         int arrayElement=0;
         if(matrixType == Emme2DataBank.MS)
             m=readScalarMatrix(matrixName);
         else if(matrixType==Emme2DataBank.MO)
            m=readOriginMatrix(matrixName);
         else if(matrixType == Emme2DataBank.MD)
            m=readDestinationMatrix(matrixName);
         else
            m=readFullMatrix(matrixName);
        return m;
    }
  
    /**
     * Read a row from the databank, and return it as a float array, dimensioned by 
     * internal numbers.
     * 
     * @param matrixName  Name of matrix to read.
     * @param ptaz        The row to read
     * @return            A float array, dimensioned by internal numbers.
     */
    public float[] readRow(String matrixName, int ptaz)  {
        
        nRows = dataBank.getZonesUsed();
        nCols = nRows;
        float[] values = new float[nRows];
        
        //Big enough to read entire row, including unused zones
        byte[] byteArray = new byte[dataBank.getMaxZones()*4];
        
        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
        
        //advance byteOffset to row
        int[] internals = dataBank.getInternalZoneNumbers();
        long rowNumber = (long)internals[ptaz];
        byteOffset += (rowNumber-1)*((long)byteArray.length);
        try {
            RandomAccessFile randFile = dataBank.getRandomAccessFile();
            
            randFile.seek(byteOffset);
            randFile.read( byteArray, 0, byteArray.length );

            ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
            byteBuffer.order( ByteOrder.nativeOrder() );

            //Read float values from byte buffer
            for(int col=0; col < nCols; col++) {
                values[col] = byteBuffer.getFloat();
                
                if(values[col]>999999)
                    values[col]=0;
            }

            byteBuffer.clear();

        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }
       
        return values;
        
    }

    /**
     * Reads a scalar matrix.
     * @param matrixName
     * @return Matrix  A full matrix filled with the scalar value.
     */
    private Matrix readScalarMatrix(String matrixName){
        
        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
         //Emme2 matrices are always square so use same value for rows and columns
         nRows = dataBank.getZonesUsed();
         nCols = nRows;

         //Arrays used in this method
         float[][] values = new float[nRows][nCols];

         //Big enough to read entire row, including unused zones
         byte[] byteArray = new byte[4];

         long startTime = System.currentTimeMillis();

         try {
             RandomAccessFile randFile = dataBank.getRandomAccessFile();
             randFile.seek(byteOffset);
             randFile.read( byteArray, 0, byteArray.length );
             ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
             byteBuffer.order( ByteOrder.nativeOrder() );

             float value = byteBuffer.getFloat();
             //Loop through all the rows in the matrix
             for (int row=0; row < nRows; row++) {
                 //Read float values from byte buffer
                 for(int col=0; col < nCols; col++) {
                     values[row][col] = value;
                    
                     if(values[row][col]>999999)
                         values[row][col]=0;
                 }

                 byteBuffer.clear();
             }
         }
         catch (Exception e) {
             throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
         }

         long finishTime = System.currentTimeMillis();

         //System.out.println("readData() time = " + (finishTime-startTime));

         Matrix m = new Matrix(name, description, values);
         m.setExternalNumbers( dataBank.getExternalZoneNumbers() );

         return m;


    }
    /** Reads matrix type mo
     * 
     * @param matrixName
     * @return Matrix
     * @throws MatrixException
     */
    private Matrix readOriginMatrix(String matrixName) throws MatrixException{
        
        //Throws an exception if there are any errors in the matrixName
        Emme2MatrixHelper.checkMatrixName(dataBank, matrixName);

        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
        
        //Emme2 matrices 
        nRows = dataBank.getZonesUsed();
        nCols = 1;

        //Arrays used in this method
        float[] values = new float[nRows];

        //Big enough to read entire row, including unused zones
        byte[] byteArray = new byte[dataBank.getMaxZones()*4];

        long startTime = System.currentTimeMillis();

        try {
            RandomAccessFile randFile = dataBank.getRandomAccessFile();
            randFile.seek(byteOffset);
            randFile.read( byteArray, 0, byteArray.length );

            ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
            byteBuffer.order( ByteOrder.nativeOrder() );

            //Loop through all the rows in the matrix
            for (int row=0; row < nRows; row++) {

                values[row] = byteBuffer.getFloat();
                 if(values[row]>999999)
                        values[row]=0;
            }

            byteBuffer.clear();
            
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }

        long finishTime = System.currentTimeMillis();

        //System.out.println("readData() time = " + (finishTime-startTime));

        Matrix m = new ColumnVector(values);
        m.setName(name);
        m.setDescription( description);
        m.setExternalNumbers( dataBank.getExternalZoneNumbers() );

        return m;
            
    }
    
    /** Reads matrix type md
      * 
      * @param matrixName
      * @return Matrix
      * @throws MatrixException
      */
     private Matrix readDestinationMatrix(String matrixName) throws MatrixException{
        
         //Throws an exception if there are any errors in the matrixName
         Emme2MatrixHelper.checkMatrixName(dataBank, matrixName);

         long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
        
         //Emme2 matrices 
         nRows = 1;
         nCols = dataBank.getZonesUsed();

         //Arrays used in this method
         float[] values = new float[nCols];

         //Big enough to read entire row, including unused zones
         byte[] byteArray = new byte[dataBank.getMaxZones()*4];

         long startTime = System.currentTimeMillis();

         try {
             RandomAccessFile randFile = dataBank.getRandomAccessFile();
             randFile.seek(byteOffset);
             randFile.read( byteArray, 0, byteArray.length );

             ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
             byteBuffer.order( ByteOrder.nativeOrder() );

             //Loop through all the cols in the matrix
             for (int col=0; col < nCols; col++) {

                 values[col] = byteBuffer.getFloat();
                    
                 if(values[col]>999999)
                         values[col]=0;
             }

             byteBuffer.clear();
            
         }
         catch (Exception e) {
             throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
         }

         long finishTime = System.currentTimeMillis();

         //System.out.println("readData() time = " + (finishTime-startTime));

         Matrix m = new RowVector(values);
         m.setName(name);
         m.setDescription( description);
         m.setExternalNumbers( dataBank.getExternalZoneNumbers() );

         return m;
            
     }
    /**
     * Reads a full matrix.
     * @param matrixName
     * @return Matrix
     */
    private Matrix readFullMatrix(String matrixName){
        
        long byteOffset = Emme2MatrixHelper.calculateByteOffset(dataBank, matrixName);
        //Emme2 matrices are always square so use same value for rows and columns
        nRows = dataBank.getZonesUsed();
        nCols = nRows;

        //Arrays used in this method
        float[][] values = new float[nRows][nCols];

        //Big enough to read entire row, including unused zones
        byte[] byteArray = new byte[dataBank.getMaxZones()*4];

        long startTime = System.currentTimeMillis();

        try {
            RandomAccessFile randFile = dataBank.getRandomAccessFile();
            randFile.seek(byteOffset);

            //Loop through all the rows in the matrix
            for (int row=0; row < nRows; row++) {

                randFile.read( byteArray, 0, byteArray.length );

                ByteBuffer byteBuffer = ByteBuffer.wrap( byteArray );
                byteBuffer.order( ByteOrder.nativeOrder() );

                //Read float values from byte buffer
                for(int col=0; col < nCols; col++) {
                    values[row][col] = byteBuffer.getFloat();
                    
                    if(values[row][col]>999999)
                        values[row][col]=0;
                }

                byteBuffer.clear();

            }
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }

        long finishTime = System.currentTimeMillis();

        //System.out.println("readData() time = " + (finishTime-startTime));

        Matrix m = new Matrix(name, description, values);
        m.setExternalNumbers( dataBank.getExternalZoneNumbers() );

        return m;

    }
    
    
    
}
