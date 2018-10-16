/*
 * Copyright  2007 PB
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
import org.apache.log4j.Logger;

/**
 * Implements a MatrixWriter to write matrices to a Transcad file.
 * 
 * NOTE:  In order to write non-sequential row and column IDs, you must use
 *        TransCAD Version 5.0 r2 Build 1635 or later.  Earlier methods will 
 *        result in a garbage matrix getting written. 
 *        
 *        If the IDs are sequential, we are creating a new TranscadIO using
 *        the old constructor, to maintain backwards compatibility with older
 *        versions of TransCAD.  If they are non-sequential, then we call the 
 *        newer constructor, and require that the user use the new version of 
 *        TransCAD.  Once the new version becomes the norm, we may consider
 *        removing this complication.  
 *
 * @author    Joel Freedman
 * @version   1.0, 11/2007
 */
public class TranscadMatrixWriter extends MatrixWriter {
    protected Logger logger = Logger.getLogger("com.pb.common.matrix");
    
    /**
     * @param file represents the physical matrix file
     */
    public TranscadMatrixWriter(File file) {
        this.file = file;
   }
    public Matrix writeMatrix() throws MatrixException {
        throw new UnsupportedOperationException("Use method, writeMatrix(\"index\")");
    }
    /** 
     * Writes a matrix to table 1 of a transcad matrix file.
     *
     * @param m Matrix
     * @throws MatrixException
     */
    public void writeMatrix( Matrix m ) throws MatrixException {
        int rows = m.getRowCount();
        int cols = m.getColumnCount();
        String[] labels = new String[1];
        labels[0]=m.getName();
        
        int[] rowIds = m.getExternalRowNumbers(); 
        int[] colIds = m.getExternalColumnNumbers(); 
        
        TranscadIO io; 
        if (idsAreSequential(rowIds) && idsAreSequential(colIds)) {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols);
        } else {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols,rowIds,colIds);
        }
        
        float[][] values = m.getValues();
        io.setMatrix(0, values);
        
        io.closeMatrix();
       
    }    
    /** 
     * Writes a matrix to table 1 of a transcad matrix file.
     *
     * @param name Matrix name
     * @param m object
     * @throws MatrixException
     */
    public void writeMatrix( String name, Matrix m ) throws MatrixException {
        int rows = m.getRowCount();
        int cols = m.getColumnCount();
        String[] labels = new String[1];
        labels[0]=name;

        int[] rowIds = m.getExternalRowNumbers(); 
        int[] colIds = m.getExternalColumnNumbers(); 

        TranscadIO io; 
        if (idsAreSequential(rowIds) && idsAreSequential(colIds)) {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols);
        } else {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols,rowIds,colIds);
        }
        
        float[][] values = m.getValues();
        io.setMatrix(0, values);
        
        io.closeMatrix();
       
    }    
    /** 
     * Writes an array of matrices to a transcad matrix file.
     *
     * @param m Array of matrices
     * @throws MatrixException
     */
    public void writeMatrices( Matrix[] m ) throws MatrixException {
         
        int rows = m[0].getRowCount();
        int cols = m[0].getColumnCount();
        String[] labels = new String[m.length];
        
        for(int i=0;i<m.length;++i)
            labels[i] = m[i].getName();

        int[] rowIds = m[0].getExternalRowNumbers(); 
        int[] colIds = m[0].getExternalColumnNumbers(); 

        TranscadIO io; 
        if (idsAreSequential(rowIds) && idsAreSequential(colIds)) {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols);
        } else {
        	io = new TranscadIO(file.getPath(),file.getName(),labels,rows,cols,rowIds,colIds);
        }
        
        for(int i=0;i<m.length;++i){
            float[][] values = m[i].getValues();
            io.setMatrix(i, values);
        }
        
        io.closeMatrix();


    }
    /** 
     * Writes an array of matrices to a transcad matrix file.
     *
     * @param m  Array of matrices
     * @param names An array of matrix names or labels.
     * @throws MatrixException
     */
    public void writeMatrices( String[] names, Matrix[] m ) throws MatrixException {
         
        if(names.length != m.length){
            logger.fatal("TranscadMatrixWriter.writeMatrices Error:  Matrix names not equal to matrix array length!");
            throw new RuntimeException();
        }
        int rows = m[0].getRowCount();
        int cols = m[0].getColumnCount();        
        
        int[] rowIds = m[0].getExternalRowNumbers(); 
        int[] colIds = m[0].getExternalColumnNumbers(); 

        TranscadIO io; 
        if (idsAreSequential(rowIds) && idsAreSequential(colIds)) {
        	io = new TranscadIO(file.getPath(),file.getName(),names,rows,cols);
        } else {
        	io = new TranscadIO(file.getPath(),file.getName(),names,rows,cols,rowIds,colIds);
        }
        
        for(int i=0;i<m.length;++i){
            float[][] values = m[i].getValues();
            io.setMatrix(i, values);
        }
        
        io.closeMatrix();


    }
    
    /**
     * Checks whether an array is sequential, starting from 1.   
     * 
     * @param idArray An array of IDs, 1-based.  
     * @return A boolean indicating if the array of values is sequential.  
     */
    private boolean idsAreSequential(int[] idArray) {
    	boolean areSequential = true; 
    
    	int i=1; 
    	while (areSequential && i<idArray.length) {
    		if (idArray[i] != i) areSequential = false; 
    		i++; 
    	}
    	
    	return areSequential; 
    }

}
