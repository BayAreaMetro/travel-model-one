/*
 * Copyright  2013 PB Consult Inc.
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
import com.sun.jna.Pointer;
import java.io.File;
import java.util.Hashtable;

/**
 * Implements a MatrixReader to read 64-bit matrices to a Tpplus/Cube file.
 * Uses the TpplusNativeIO64 interface
 *
 * @see com.pb.common.matrix.TpplusNativeIO64
 * 
 * @author    Yegor Malinovskiy
 * @version   0.1, 5/2/2013
 * 
 */
public class TpplusMatrixReader64 extends MatrixReader {

    protected Logger logger = Logger.getLogger("com.pb.common.matrix");
    static TpplusNativeIO64 dllLink = TpplusNativeIO64.INSTANCE;
    int nTables; 
    Hashtable<String, Integer> nameToTableNum; 
    Pointer matrix;
    String[] matNames;

	/**
	 * @param file represents the physical matrix file
	 */
	public TpplusMatrixReader64(File file) {

        if ( ! file.canRead() ) {
            logger.fatal( "TPPLUS file: " + file.getPath() + " cannot be read." );
            throw (new RuntimeException() );
        }
        
		this.file = file;
        logger.debug("Creating TpplusMatrixReader64 for file " + file.getAbsolutePath());

	}
	
    /**
     * Closes the .dll linkage to the matrix file
     * 
     */
    public void closeFile() {
    	dllLink.MatReaderClose(matrix);
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
        int nRows = dllLink.MatReaderGetNumZones(matrix);
        return nRows; 
    }
	
    
    /**
     * Reads all the matrix tables from a tpplus matrix file.
     * 
     * @return an array of complete matrices
     * @throws MatrixException
     */
    public Matrix[] readMatrices() throws MatrixException {
        
        Matrix[] m = new Matrix[nTables+1]; 
        for (int i=1; i<=nTables; i++) { //Enforce 1-based
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
        
    	// attempt to open file through dll linker 
        try {
        	
			String error = "Error in dll linker to VoyagerFileAccess";
			int errorBuffer = 256;
			String fp = file.getAbsolutePath();
        	matrix = dllLink.MatReaderOpen(fp, error, errorBuffer);    	
            nTables = dllLink.MatReaderGetNumMats(matrix);
        }
        catch ( Exception e ) {
            logger.fatal( "Exception occurred calling VoyagerFileAccess.dll native method: MatReaderGetNumMats()." );
            throw new RuntimeException( e );
        }
        
        // load matrix names into Hashtable 'nameToTableNum'
        readMatrixNames(); 
        
        if (nameToTableNum.containsKey(tableName)) {
            table = nameToTableNum.get(tableName); 
            logger.info( Thread.currentThread().getName() + " reading tpplus64 matrix " + file.getPath() + " from file with table name " + tableName );
        } else {
            try {
                table = Integer.parseInt(tableName); 
                logger.info( Thread.currentThread().getName() + " reading tpplus64 matrix " + file.getPath() + " from file at position " + table); 
            } catch (NumberFormatException e) {
                if (nTables==1) { 
                    table = 1; 
                    logger.info("No tpplus64 matrix in " + file.getPath() + " with name " + tableName 
                                + " so reading matrix 1");
                } else {
                    logger.fatal("ERROR attempting to read tpplus64 matrix " + file.getPath()); 
                    throw new MatrixException(MatrixException.INVALID_TABLE_NAME + " " + tableName); 
                }
            }        
        } 
        
        Matrix m = readData(table);  
        
        // close matrix file
    	dllLink.MatReaderClose(matrix);

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
        
        matNames = new String[nTables+1];
        dllLink.MatReaderGetMatrixNames(matrix, matNames);
        
        for (int i=nTables-1; i>=0; i--) {
            String name = matNames[i];
            matNames[i+1] = name;//Enforce 1-based
            nameToTableNum.put(name, new Integer(i+1)); 
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
        
        String name = matNames[table]; 
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
        int nRows = getNumRows();
        logger.debug(file.getAbsoluteFile() + " has " + nRows + " rows, reading table " + table + " of " + nTables);
        
        double[] rowBuffer=new double[nRows];
        Matrix m = new Matrix(nRows, nRows); 
        int[] externalNumbers = createDefaultExternalNumbers(nRows); 
        m.setExternalNumbers(externalNumbers); 
        for (int r=0; r < nRows; r++) {
        		dllLink.MatReaderGetRow(matrix, table, r+1, rowBuffer);
                for (int c=1; c <= nRows; c++) {
                    m.setValueAt(externalNumbers[r+1], externalNumbers[c], (float)rowBuffer[c-1]);
                }
        }        

        String mName = getMatrixName(table); 
        m.setName(mName);         

        logger.debug( "The sum of matrix[" + table + "] is " + m.getSum());      

        return m;
    }
}

