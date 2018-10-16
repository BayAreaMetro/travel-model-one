/*
 * Copyright 2005 PB Consult Inc.
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
 *   Created on Dec 13, 2005 by Joel Freedman <freedman@pbworld.com>
 */
package com.pb.common.matrix;

import org.apache.log4j.Logger;
import transcad.Matrix;

import java.io.File;
import java.io.IOException;


/**
 * This class is used for TransCAD matrix io.  Note that one TransCAD matrix file can
 * hold one or more matrices. 
 * 
 * SETUP: Need to make sure that CLASSPATH contains: 
 *           C:\Progra~1\TransCAD\GISDK\Matrices\TranscadMatrix.jar
 *           
 *        Need to make sure that PATH contains:
 *           C:\Progra~1\TransCAD
 *           C:\Progra~1\TransCAD\GISDK\Matrices\
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
 * 
 * @author Freedman
 *
 */
public class TranscadIO {
    
    Matrix m;
    protected File existing_file;
    protected static Logger logger = Logger.getLogger(TranscadIO.class);

    /**
     * Default constructor.
     *
     */
    private TranscadIO(){
    }
    
    /**
     * Constructor to use if opening an existing matrix.
     * @param fileName
     */
    public TranscadIO(String fileName){
        openMatrix(fileName);
    }
    
    
    /**
     * Constructor to use if creating a new matrix.  After this method, use setRowIDs and
     * setColumnIDs to set ID numbers for rows and columns, and then use either
     * setFloatMatrix(), setRowsAt(), and/or setColumnsAt() to set values in the matrix.
     * The matrix will be created empty with float value format and default compression, with
     * one matrix for each label.
     * 
     * @param fileName  The path/name of the file to create.
     * @param fileLabel  The label for the matrix file.
     * @param matrixLabels  A vector of labels for each individual matrix in the file. 
     * @param numberOfRows  Number of rows in each matrix.
     * @param numberOfColumns  Number of columns in each matrix.
     */
    public TranscadIO(String fileName,String fileLabel,String[] matrixLabels, int numberOfRows, int numberOfColumns){
        
        short numberOfMatrices=(short)matrixLabels.length;
        byte data_type = transcad.DATA_TYPE.FLOAT_TYPE;
        short compression = 1;

        try{
            existing_file = new java.io.File(fileName);
            if (existing_file.exists()) {
                existing_file.delete();
            }

            m = new transcad.Matrix(fileName,fileLabel,numberOfMatrices,
                numberOfRows,numberOfColumns,data_type,compression,matrixLabels);
            
            
        }catch(IOException e){
            logger.fatal("Error attempting to create new Transcad matrix "+fileName);
            throw new RuntimeException();
        }
    }
    
    
    /**
     * Constructor to use if creating a new matrix.  After this method use either
     * setFloatMatrix(), setRowsAt(), and/or setColumnsAt() to set values in the matrix.
     * The matrix will be created empty with float value format and default compression, with
     * one matrix for each label.
     * 
     * NOTE:  This method requires TransCAD Version 5.0 r2 Build 1635 or later to work properly.
     *        Earlier methods will result in a garbage matrix getting written. 
     * 
     * @param fileName  The path/name of the file to create.
     * @param fileLabel  The label for the matrix file.
     * @param matrixLabels  A vector of labels for each individual matrix in the file. 
     * @param numberOfRows  Number of rows in each matrix.
     * @param numberOfColumns  Number of columns in each matrix.
     * @param rowIds  External labels for row IDs.  (1-based, with conversion done in here)
     * @param colIds  External lablels for column IDs.  (1-based, with conversion done in here)  
     */
    public TranscadIO(String fileName,String fileLabel,String[] matrixLabels, int numberOfRows, int numberOfColumns, 
            int[] rowIds, int[] colIds){
        
        short numberOfMatrices=(short)matrixLabels.length;
        byte data_type = transcad.DATA_TYPE.FLOAT_TYPE;
        short compression = 1;

        // convert row IDs to be 0-based, and stored as longs
        long[] convertedRowIds = new long[numberOfRows];
        for (int i=0; i<convertedRowIds.length; i++) {
            convertedRowIds[i] = rowIds[i+1];
        }
        
        // convert row IDs to be 0-based, and stored as longs
        long[] convertedColIds = new long[numberOfColumns];
        for (int i=0; i<convertedColIds.length; i++) {
            convertedColIds[i] = colIds[i+1];
        }
        
        try{
            existing_file = new java.io.File(fileName);
            if (existing_file.exists()) {
                existing_file.delete();
            }

            m = new transcad.Matrix(fileName,fileLabel,numberOfMatrices,
                numberOfRows,numberOfColumns,data_type,compression,matrixLabels, 
                convertedRowIds, convertedColIds);
            
        }catch(IOException e){
            logger.fatal("Error attempting to create new Transcad matrix "+fileName);
            throw new RuntimeException();
        }
    }
    

    
    /**
     * Open the TransCAD Matrix.
     * 
     * @param fileName  Path/name of the matrix to open.
     * @throws java.lang.Throwable
     */
    protected void openMatrix(String fileName){
        
        existing_file = new java.io.File(fileName);
        if (! existing_file.exists()) {
            logger.fatal("Cannot find TransCAD matrix file: "+fileName);
            return;
        }
        try{
            m = new Matrix(fileName);       
        }catch(IOException e){
            logger.fatal("Error trying to open Trancad matrix "+fileName);
            throw new RuntimeException();
        }
        
    }
    /**
     * Close the matrix.
     *
     */
    protected void closeMatrix(){
        m.dispose();
    }
    
    /**
     * Get the number of matrices in the matrix file.
     * Must have opened matrix with openMatrix() first.
     * 
     * @return  The number of matrices in the opened matrix file.
     */
    public int getNumberOfMatrices(){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getNumberOfMatrices() call");
            throw new RuntimeException();
        }
        return m.getNCores();
    }
    
    /**
     * Get the number of rows in the matrix file.
     * Must have opened matrix with openMatrix() first.
     * 
     * @return The number of rows in the opened matrix file.
     */
    public int getNumberOfRows(){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getNumberOfRows() call");
            throw new RuntimeException();
        }
        return (int) m.getBaseNRows();
    }

    /**
     * Get the number of columns in the matrix file.
     * Must have opened matrix with openMatrix() first.
     * 
     * @return The number of columns in the opened matrix file.
     */
    public int getNumberOfColumns(){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getNumberOfColumns() call");
            throw new RuntimeException();
        }
        return (int) m.getBaseNCols();
        
    }

    /**
     * Get a vector of row IDs.
     * 
     * @return IDs for rows, 0-init.
     */
    public int[] getRowIDs(){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getRowIDs() call");
            throw new RuntimeException();
        }
        int[] row_ids;
        row_ids = new int[getNumberOfRows()];
        m.GetIDs(transcad.MATRIX_DIM.MATRIX_ROW,row_ids);
        return row_ids;
    }

    /**
     * Get a vector of column IDs.
     * 
     * @return IDs for columns, 0-init.
     */
    public int[] getColumnIDs(){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getColumnIDs() call");
            throw new RuntimeException();
        }
        int[] col_ids;
        col_ids = new int[getNumberOfColumns()];
        m.GetIDs(transcad.MATRIX_DIM.MATRIX_COL,col_ids);
        return col_ids;
    }
    
    /**
     * Get a row.
     * 
     * @param rowID  The row ID.
     * @param matrixNumber  The number of matrix (0-init) within this file to get row values for.
     * @return  A 0-init array of row float values.
     */
    public float[] getRowAt(int rowID, int matrixNumber){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getRowAt() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying getRowAt() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
            
        m.setCore(matrixNumber);
        int cols = getNumberOfColumns();
        float[] row = new float[cols];
        m.getVector(transcad.MATRIX_DIM.MATRIX_ROW, rowID,row);
        
        for(int c=0;c<cols;++c){
            if(Math.abs(row[c])>99999)
                row[c]=0;
        }
        return row;
    }
 
    /**
     * Get a column.
     * 
     * @param columnID  The column ID.
     * @param matrixNumber  The number of matrix (0-init) within this file to get col values for.
     * @return  A 0-init array of column float values.
     */
    public float[] getColumnAt(int columnID, int matrixNumber){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getColumnAt() call");
            throw new RuntimeException();
        }
        int rows=getNumberOfRows();
        float[] col = new float[rows];
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying getColumnAt() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        m.setCore(matrixNumber);
        m.getVector(transcad.MATRIX_DIM.MATRIX_COL, columnID,col);
        
        for(int r=0;r<rows;++r){
            if(Math.abs(col[r])>99999)
                col[r]=0;
        }
        return col;
    }
    /**
     * Set a row.
     * 
     * @param rowID  The row ID.
     * @param matrixNumber  The number of matrix (0-init) within this file to set row values for.
     * @param row  A 0-init array of row float values.
     */
    public void setRowAt(int rowID, int matrixNumber, float[] row){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before setRowAt() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying setRowAt() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        m.setCore(matrixNumber);
        m.setVector(transcad.MATRIX_DIM.MATRIX_ROW, rowID,row);
    }
 
    /**
     * Set a column.
     * 
     * @param columnID  The column ID.
     * @param matrixNumber  The number of matrix (0-init) within this file to set col values for.
     * @param column  A 0-init array of column float values.
     */
    public void setColumnAt(int columnID, int matrixNumber, float[] column){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before setColumnAt() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying setColumnAt() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        m.setCore(matrixNumber);
        m.setVector(transcad.MATRIX_DIM.MATRIX_COL, columnID,column);
    }
    
    /**
     * Get a 2-d float matrix of values from the Transcad matrix.
     * 
     * @param matrixNumber  The number of matrix (0-init) within this file to get values for.
     * @return A 0-init matrix of values.
     */
    public float[][] getMatrix(int matrixNumber){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getMatrix() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying getMatrix() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        m.setCore((short)matrixNumber);
        int rows = getNumberOfRows();
        int cols = getNumberOfColumns();
        
        float[][] matrix = new float[rows][cols];
        
        for(int r=0;r<rows;++r){
            m.getBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,matrix[r]);
            for(int c=0;c<cols;++c){
                if(matrix[r][c] == m.FLOAT_MISS || Math.abs(matrix[r][c])>99999)
                    matrix[r][c]=0;
            }
        }
        return matrix;
    }
    /**
     * Set a 2-d float matrix of values in the Transcad matrix.
     * 
     * @param matrixNumber  The number of matrix (0-init) within this file to set values for.
     * @param values A 0-init matrix of values.
     */
    public void setMatrix(int matrixNumber, float[][] values){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getMatrix() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying getMatrix() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        if(values.length>getNumberOfRows()){
            logger.fatal("Error: Trying setMatrix() for row number greater than number of rows");
            throw new RuntimeException();
             
        }
        m.setCore(matrixNumber);
        int rows = getNumberOfRows();
        
        for(int r=0;r<rows;++r)
            m.setBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,values[r]);
        
      }
    
    /**
     * Set label for matrix.
     * 
     * @param label  The label to set.
     * @param matrixNumber  The number of the matrix.
     */
    public void setMatrixLabel(String label, int matrixNumber){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before setMatrixLabel() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying setMatrixLabel() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        m.SetLabel(matrixNumber,label);
                
    }
    /**
     * Get label for matrix.
     * 
      * @param matrixNumber  The number of the matrix.
     * @return The label of the matrix.
    */
    public String getMatrixLabel(int matrixNumber){
        if(m==null){
            logger.fatal("Error: TransCAD matrix needs to be opened/created before getMatrixLabel() call");
            throw new RuntimeException();
        }
        if(matrixNumber>getNumberOfMatrices()-1){
            logger.fatal("Error: Trying getMatrixLabel() for matrix number greater than number of matrices");
            throw new RuntimeException();
        }
        return m.GetLabel(matrixNumber);
                
    }
    
    /**
     * Temporary (hopefully) function which corrects a bug with the output TransCAD
     * matrices. Call this function before writing output matrices to make their I/O
     * with other TransCAD macros seamless. Developed as a workaround for the CMCOG
     * software.
     *
     */
    public static void kickStart(){
    	
    	short numberOfMatrices=1;
        byte data_type = transcad.DATA_TYPE.FLOAT_TYPE;
        short compression = 1;
        
        String fileName       = "junk.mtx";
        String fileLabel      = "junk.mtx";
        int numberOfRows      = 1;
        int numberOfColumns   = 1;
        String[] matrixLabels = {"junk"};
        

        try{
            File existing_file = new java.io.File(fileName);
            if (existing_file.exists()) {
                existing_file.delete();
            }

            new transcad.Matrix(fileName,fileLabel,numberOfMatrices,
                numberOfRows,numberOfColumns,data_type,compression,matrixLabels);
            
            if(existing_file.exists()){
            	existing_file.delete();
            }
            
        }catch(IOException e){
            logger.fatal("Error attempting to create new Transcad matrix "+fileName);
            throw new RuntimeException();
        }
    }
    
    /*
    // temporary
    private static void makeCmcogMatrices(){
    	
    	int rows = 826;
        int cols = 826;
        
        String[] tables = {"DriveAlone","SharedRide2","SharedRide3"};
        
        float[][] dummyData = new float[rows][cols];
        for(int k=0;k<rows;++k){
        	for(int l=0;l<cols;++l){
        		dummyData[k][l] = 1.0f;
        	}
        }
        
        short numberOfMatrices=(short)1;
        byte data_type = transcad.DATA_TYPE.FLOAT_TYPE;
        short compression = 1;
        
        // set the file root
        String fileRoot = "c:/projects/cmcog/transcadDebug/Base2005/Interim/HBW_";
        
        // write a matrix for each table
        for(int m=0;m<tables.length;++m){
        	
        	String fileName  = fileRoot + tables[m] +".mtx";
        	String fileLabel = tables[m];
        	String[] matrixLabels = {tables[m]};
        	
        	try{
                File existing_file = new java.io.File(fileName);
                if (existing_file.exists()) {
                    existing_file.delete();
                }

                transcad.Matrix tempMatrix = new transcad.Matrix(fileName,fileLabel,numberOfMatrices,
                    rows,cols,data_type,compression,matrixLabels);
                
                String toLogger = fileName + "," + fileLabel + "," + numberOfMatrices + "," + rows + "," + 
                                  cols + "," + data_type + "," + compression + ",";
                for(int i=0;i<matrixLabels.length;++i) toLogger += matrixLabels[i] + ",";
                logger.info(toLogger); 
                
                tempMatrix.setCore(0);
                
                for(int r=0;r<rows;++r)
                	tempMatrix.setBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,dummyData[r]);
                
                tempMatrix.dispose();
                
                
            }catch(IOException e){
                logger.fatal("Error attempting to create new Transcad matrix "+fileName);
                throw new RuntimeException();
            }
        }

        
    	
    }
    
    */
    
     /**
     * Test method.
     * @param args
     * @throws java.lang.Throwable
     */
    public static void main(String args[]) throws java.lang.Throwable {
    	

        String debug;
        int i,r,c,n_rows,n_cols;
        short tc_status;
        java.io.File existing_file;

        //
        // Read a matrix from an existing TransCAD matrix file
        //

        TranscadIO io = new TranscadIO();
        
        transcad.Matrix test = new transcad.Matrix("r:\\Projects\\ohio\\data\\NewTransitSkims\\icdtOp.mtx");
        io.openMatrix("r:\\Projects\\ohio\\data\\NewTransitSkims\\icdtOp.mtx");
        int matrices = test.getNCores();
        for(i=0;i<matrices;++i){
            String name = test.GetLabel(i);
            logger.info("Matrix "+i+" is "+name);
            float[][] m = io.getMatrix(i);
            logger.info("Success reading matrix "+name);
        }
        System.exit(1);
        
        existing_file = new java.io.File("busfare.mtx");
        if (! existing_file.exists()) {
            logger.fatal("Cannot find TransCAD matrix file: busfare.mtx");
            logger.fatal("Copy busfare.mtx from the TransCAD tutorial folder to this folder and try again.");
            return;
        }
        logger.info("About to open busfare matrix");
        transcad.Matrix my = new transcad.Matrix("BUSFARE.MTX");
        io.openMatrix("BUSFARE.MTX");
        logger.info("Opened busfare matrix");
        
        my.setCore((short)0);
        n_rows = (int) my.getBaseNRows();
        n_cols = (int) my.getBaseNCols();

        logger.info("Rows = " + n_rows + " Cols = " + n_cols);
        logger.info("Rows = "+ io.getNumberOfRows() + " Cols = " + io.getNumberOfColumns());
        
        // Get row IDs and verify
        int[] row_ids;
        row_ids = new int[n_rows];
        my.GetIDs(transcad.MATRIX_DIM.MATRIX_ROW,row_ids);
        int[] rowIDsFromIO = io.getRowIDs();
        for (r=0;r<=n_rows-1;r++) {
            logger.info("row " + r + " row_id = " + row_ids[r]+" row_id_io = " + rowIDsFromIO[r]);
        }

        // Get col IDs and verify
        int[] col_ids;
        col_ids = new int[n_cols];
        my.GetIDs(transcad.MATRIX_DIM.MATRIX_COL,col_ids);
        int[] colIDsFromIO = io.getColumnIDs();
        for (r=0;r<=n_cols-1;r++) {
            logger.info("col " + r + " col_id = " + col_ids[r]+" col_id_io = " + colIDsFromIO[r]);
        }

        float[] column;
        float[] row;
        column = new float[n_rows];
        row = new float[n_cols];
        double sum_columns, sum_rows;
        sum_columns = 0;
        sum_rows = 0;

        for (r=0;r<n_rows;r++) {
            tc_status = my.getBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,row);
            for (c=0;c<n_cols;c++) {
                sum_rows = sum_rows + row[c];
            }
        }

        for (c=0;c<n_cols;c++) {
            tc_status = my.getBaseVector(transcad.MATRIX_DIM.MATRIX_COL,c,column);
            for (r=0;r<n_rows;r++) {
                sum_columns = sum_columns + column[r];
            }
        }

        //sum the float matrix from this class
        float[][] m = io.getMatrix(0);
        double sum=0;
         for(r=0;r<m.length;++r)
            for(c=0;c<m[r].length;++c)
                sum += m[r][c];
 
        logger.info(" Sum Rows = " + java.lang.String.valueOf(sum_rows));
        logger.info(" Sum Columns = " + java.lang.String.valueOf(sum_columns));
        logger.info(" Sum Matrix from IO = " + sum);

 
        //
        // Copy this matrix to another file
        //

        String new_file = "MyMatrix.mtx"; 
        existing_file = new java.io.File(new_file);
        if (existing_file.exists()) {
            existing_file.delete();
        }
        boolean copied = my.Copy(new_file,null);
        my.dispose();
        my = null;


        my = new transcad.Matrix("MyMatrix.MTX");
        n_rows = (int) my.getBaseNRows();
        n_cols = (int)  my.getBaseNCols();

        // 
        // Write values to the matrix
        //

        tc_status = my.setCore(1);
        for (r=0;r<n_rows;r++) {
            column[r] = (float) (1 + r); 
        }
        for (c=1;c<n_cols-1;c++) {
            tc_status = my.setBaseVector(transcad.MATRIX_DIM.MATRIX_COL,c,column);
        }

        tc_status = my.setCore(1);
        for (c=0;c<n_cols;c++) {
            row[c] = (float)(n_cols - c);
        }
        for (r=1;r<n_rows-1;r++) {
            tc_status = my.setBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,row);
        }
                
        float float_value = my.getElementFloat(n_rows-1,n_cols-1);

        debug = my.toString();
        
        String label = my.GetLabel(1);
        logger.info("Core 1 label is " + label);

        label = "new " + label;
        my.SetLabel(1,label);
        logger.info("Core 1 label is now " + my.GetLabel(1));
        
        logger.info(debug);
        
        // logger.info(status);

        my.dispose();
        my = null;

        //
        // Create a new matrix
        //

        String[] CoreNames = { "Core One" , "Core Two" , "Core Three" };
        new_file = "MyNewMatrix.mtx";
        String MatrixLabel = "My New Matrix";
        short n_cores = 3;
        short compression = 1;
        byte data_type = transcad.DATA_TYPE.FLOAT_TYPE;
        existing_file = new java.io.File(new_file);
        if (existing_file.exists()) {
            existing_file.delete();
        }
        my = new transcad.Matrix(new_file,MatrixLabel,n_cores,n_rows,n_cols,data_type,compression,CoreNames);

        debug = my.toString();
        //status = my.getStatusString();


        logger.info(debug);

        // logger.info(status);

        // Do something with the matrix
        tc_status = my.setCore(1);

        r = 2;
        tc_status = my.setBaseVector(transcad.MATRIX_DIM.MATRIX_ROW,r,row);

        c = 2;
        tc_status = my.setBaseVector(transcad.MATRIX_DIM.MATRIX_COL,c,column);

        my.dispose();
        my = null;
        
        //test IO matrix creation
        int rows = 100;
        int cols = 100;
        
        String[] labels = {"m 1", "m 2"};
        TranscadIO newIO = new TranscadIO("test.mtx","test",labels, rows, cols);
        float[][] m2 = new float[rows][cols];
        float[][] m3 = new float[rows][cols];
        for(r=0;r<rows;++r)
            for(c=0;c<cols;++c){
                m2[r][c]=r*100+c;
                m3[r][c] = m2[r][c]*m2[r][c];
            }
        newIO.setMatrix(0,m2);
        newIO.setMatrix(1,m3);
        logger.info("Success");
        
      
        
        // make some matrices for use with cmcog
        // makeCmcogMatrices();
        
        
        
    }

}

