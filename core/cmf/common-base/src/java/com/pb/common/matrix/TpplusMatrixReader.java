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
import java.util.Hashtable;

/**
 * Implementes a MatrixReader to read matrices from a Tpplus file.
 * 
 * @see com.pb.common.matrix.TpplusNativeIO
 *
 * @author    Tim Heier
 * @version   1.0, 3/28/2003
 * @author    Greg Erhardt
 * @version   2.0, 7/16/2007
 */
public class TpplusMatrixReader extends MatrixReader {

    protected Logger logger = Logger.getLogger("com.pb.common.matrix");
    
    int nTables; 
    Hashtable<String, Integer> nameToTableNum; 

	/**
	 * @param file represents the physical matrix file
	 */
	public TpplusMatrixReader(File file) {

        if ( ! file.canRead() ) {
            logger.fatal( "TPPLUS file: " + file.getPath() + " cannot be read." );
            throw (new RuntimeException() );
        }
        
		this.file = file;
        logger.debug("Creating TpplusMatrixReader for file " + file.getAbsolutePath());
        try {
            nTables = TpplusNativeIO.tppGetNumberOfTablesNative(file.getAbsolutePath());
        }
        catch ( Exception e ) {
            logger.fatal( "Exception occurred calling tppionative.dll native method: getNumberofOfTables()." );
            throw new RuntimeException( e );
        }
        readMatrixNames(); 
	}


    public Matrix readMatrix() throws MatrixException {
        throw new UnsupportedOperationException("Use method, readMatrix(\"table\")");
    }
    
    
    /**
     * 
     * @return the number of individual tables in the file
     */
    public int getNumTables() {
        return nTables; 
    }
    
    /**
     * 
     * @return the number of rows in the file
     */
    public int getNumRows() {
        int nRows = TpplusNativeIO.tppGetNumberOfRowsNative( file.getAbsolutePath() );
        return nRows; 
    }

    /**
     * Reads all the matrix tables from a tpplus matrix file.
     * 
     * @return an array of complete matrices
     * @throws MatrixException
     */
    public Matrix[] readMatrices() throws MatrixException {
        
        Matrix[] m = new Matrix[nTables]; 
        for (int i=1; i<=nTables; i++) { 
            m[i-1] = readData(i);
        } 
        
		return m;
	}
    

    /**
     * Reads a matrix table from a tpplus matrix file.
     * 
     * @param tableName The name of the table to read. 
     * @return a complete matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(String tableName) throws MatrixException {
        Integer table; 
        if (nameToTableNum.containsKey(tableName)) {
            table = nameToTableNum.get(tableName); 
            logger.info( Thread.currentThread().getName() + " reading matrix " + file.getPath() + " from file with table name " + tableName );
        } else {
            try {
                table = Integer.parseInt(tableName); 
                logger.info( Thread.currentThread().getName() + " reading matrix " + file.getPath() + " from file at position " + table); 
            } catch (NumberFormatException e) {
                if (nTables==1) { 
                    table = 1; 
                    logger.info("No matrix in " + file.getPath() + " with name " + tableName 
                                + " so reading matrix 1");
                } else {
                    logger.fatal("ERROR attempting to read tpplus matrix " + file.getPath()); 
                    throw new MatrixException(MatrixException.INVALID_TABLE_NAME + " " + tableName); 
                }
            }        
        } 
        
        Matrix m = readData(table);  
        return m; 
    }
    
    /**
     * Reads a matrix table from a tpplus matrix file.
     * 
     * @param table The number of the table to read (1-based). 
     * @return a complete matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(int table) throws MatrixException {
        Matrix m = readData(table); 
        return m; 
    }
    
    /**
     * Creates a hash map from the table name to the index.  
     *
     */
    private void readMatrixNames() {
        nameToTableNum = new Hashtable<String, Integer>();
        for (int i=1; i<=nTables; i++) {
            String name = TpplusNativeIO.tppGetTableNameNative (file.getAbsolutePath(), i);
            nameToTableNum.put(name, new Integer(i)); 
            logger.debug("name=" + name + " i=" + i); 
        }
    }
    
    /**
     * Reads a single table name. 
     * 
     * @param table index of the table (1-based). 
     * @return name of the table
     */
    private String getMatrixName(int table) {
        
        String name = TpplusNativeIO.tppGetTableNameNative (file.getAbsolutePath(), table); 
        logger.debug("table=" + table + " name="+name); 
        
        return name; 
    }
    
    /**
     * Creates a default list of external numbers, 1 through nRows.
     * 
     * @param nRows Number of rows. 
     * @return An array with default external numbers. 
     */
    private int[] createDefaultExternalNumbers(int nRows) {
        int[] externalNumbers = new int[nRows+1];
        for (int r=1; r <= nRows; r++) {
            externalNumbers[r] = r;
        }
        
        return externalNumbers; 
    }


    /**
     * Reads a matrix table from a tpplus matrix file.
     * 
     * @param table The number of the table to read (1-based). 
     * @return a complete matrix
     * @throws MatrixException
     */
    private Matrix readData(int table) throws MatrixException {

        if (table < 1 || table > nTables) {
            throw new MatrixException(MatrixException.INVALID_INDEX + " " + table); 
        }
        int nRows = TpplusNativeIO.tppGetNumberOfRowsNative( file.getAbsolutePath() );
        logger.debug(file.getAbsoluteFile() + " has " + nRows + " rows, reading table " + table + " of " + nTables);
        
        
        double[] matrixData = new double[nRows*nRows];
    
         TpplusNativeIO.tppReadTableNative ( file.getAbsolutePath(), matrixData, table);
        
        Matrix m = new Matrix(nRows, nRows); 
        int[] externalNumbers = createDefaultExternalNumbers(nRows); 
        m.setExternalNumbers(externalNumbers); 
        int i = 0;
        for (int r=1; r <= nRows; r++) {
                for (int c=1; c <= nRows; c++) {
                    m.setValueAt(externalNumbers[r], externalNumbers[c], (float)matrixData[i]);
                    i++;
                }
        }        

        String mName = getMatrixName(table); 
        m.setName(mName);         

        logger.debug( "The sum of matrix[" + table + "] is " + m.getSum());      

        return m;
    }
}
