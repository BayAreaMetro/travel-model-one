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

import com.sun.jna.Pointer;

import java.io.File;
import java.util.Hashtable;

/**
 * Implements a MatrixWriter to write 64-bit matrices to a Tpplus/Cube file.
 * Uses the TpplusNativeIO64 interface
 *
 * @see com.pb.common.matrix.TpplusNativeIO
 * 
 * @author    Yegor Malinovskiy
 * @version   0.1, 8/13/2013
 * 
 */
public class TpplusMatrixWriter64 extends MatrixWriter {

    protected Logger logger = Logger.getLogger("com.pb.common.matrix");
    private int precision; 
    static TpplusNativeIO64 dllLink = TpplusNativeIO64.INSTANCE;
    int nTables; 
    Hashtable<String, Integer> nameToTableNum; 
    Pointer matrix;
    String[] matNames;

    /**
     * @param file represents the physical matrix file
     */
    public TpplusMatrixWriter64(File file) {
        this.file = file;
        precision = 4; 
    }
    
    /**
     * Sets the decimal precision TP+ uses to write.  
     * 
     * @param precision decimal precision (0-9)
     */ 
    public void setPrecision(int precision) {
        this.precision = precision; 
    }

    public Matrix writeMatrix() throws MatrixException {
        throw new UnsupportedOperationException("Use method, writeMatrix(\"index\")");
    }

    /** 
     * Writes a matrix to table 1 of a tpplus matrix file.
     *
     * @param m object
     * @throws MatrixException
     */
    public void writeMatrix( Matrix m ) throws MatrixException {
        
		Matrix[] mArray = new Matrix[1];
		mArray[0] = m;
        
        String[] names = new String[1]; 
        if (m.getName()=="") {
            names[0] = "M1"; 
        } else {
            names[0] = m.getName(); 
        }
        
        writeData( mArray , names);
    }

    /** 
     * Writes a matrix to table 1 of a tpplus matrix file.
     *
     * @param matrixName Matrix name
     * @param m object
     * @throws MatrixException
     */
	public void writeMatrix( String matrixName, Matrix m ) throws MatrixException {
         
		Matrix[] mArray = new Matrix[1];
		mArray[0] = m;
		
        String[] names = new String[1];
        names[0] = matrixName; 
        
		writeData( mArray , names);
	}

    /** 
     * Writes a list of matrices to a tpplus matrix file.
     *
     * @param m object
     * @throws MatrixException
     */
    public void writeMatrices( Matrix[] m ) throws MatrixException {
        String[] names = new String[m.length]; 
        for (int i=0; i<m.length; i++) {
            if (m[i].getName()=="") {
                names[i] = "M" + i; 
            } else {
                names[i] = m[i].getName(); 
            }
        }
        
        writeData( m , names);
    }
    
    /** 
     * Writes a list of matrices to a tpplus matrix file.
     *
     * @param matrixName a single generic name to use
     * @param m object
     * @throws MatrixException
     */
	public void writeMatrices( String matrixName, Matrix[] m ) throws MatrixException {
	    String[] names = new String[m.length]; 
        for (int i=0; i<m.length; i++) {
	        names[i] = matrixName + i; 
        }
        
		writeData( m , names);
	}

       /** 
     * Writes a list of matrices to a tpplus matrix file.
     *
     * @param matrixNames an arrat of table names to use
     * @param m object
     * @throws MatrixException
     */
    public void writeMatrices( String matrixNames[], Matrix[] m ) throws MatrixException {

        // make sure that table names array is not null.
        // use default table numbers as names if none were given.                
        String[] names = new String[m.length]; 
        if ( matrixNames == null ) {
            for (int i=0; i < m.length; i++)
                names[i] = String.format( "table %d", (i+1) ); 
        }
        else {
            for (int i=0; i < m.length; i++)
                if ( matrixNames[i] == "")
                    names[i] = String.format( "table %d", (i+1) ); 
                else
                    names[i] = matrixNames[i];

        }
        
		writeData( m , names);
        
    }
    
    
   /**
     * Writes a matrix to a tpplus matrix file.
     * 
     * @param m Matrix object
     * @param matrixName name
     * @throws MatrixException
     */
    private void writeData( Matrix[] m, String[] name ) throws MatrixException {

        // check dimensions        
		int nRows = m[0].getRowCount();
        int nCols = m[0].getColumnCount(); 
        int[] extRow = m[0].getExternalNumbers(); 
        int[] extCol = m[0].getExternalColumnNumbers(); 
        int nTables = m.length;
        if (nRows != nCols) {
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS + " Matrix must be square."); 
        }
        for (int i=0; i<nTables; i++) {
            if (m[i].getRowCount()!=nRows || m[i].getColumnCount()!=nCols) {
                throw new MatrixException(MatrixException.INVALID_DIMENSIONS + " All matrices must be same dimensions"); 
            }
        }
        
        byte[] precisionsArray = new byte[nTables];
        for(int i =0; i < nTables; i++)
        {
        	precisionsArray[i] = (byte) precision;
        }
        
		double[] matrixData = new double[nRows];

		logger.debug( "Writing to " + file.getPath() + " with " + nTables + " tables and " + nRows + " rows" );
		
        logger.debug("Creating TpplusMatrixWriter64 for file " + file.getAbsolutePath());
        try {
        	
			String error = "Error in dll linker to VoyagerFileAccess";
			int errorBuffer = 256;
			matrix = dllLink.MatWriterOpen(file.getAbsolutePath(), "", 1, nRows, nTables, precisionsArray, matNames, error, errorBuffer);

        }
        catch ( Exception e ) {
            logger.fatal( "Exception occurred calling VoyagerFileAccess.dll native method: MatWriterOpen()" );
            throw new RuntimeException( e );
        }


		
		for (int r=0; r < nRows; r++) {
			for (int i=0; i < nTables; i++) {
				for (int c=0; c < nRows; c++) {
					matrixData[c] = m[i].getValueAt(extRow[r+1], extCol[c+1]); 
				}
				dllLink.MatWriterWriteRow(matrix, i+1, r+1, matrixData);
			}
		}
		
        // close matrix file
    	dllLink.MatWriterClose(matrix);

        
//        // convert matrix names to a single, space-delimited string
//        String tableNames = ""; 
//        for (int i=0; i<nTables; i++) {
//            String nameNoSpaces = name[i].replace(' ', '_'); 
//            tableNames += nameNoSpaces + " "; 
//        }
    }
}
