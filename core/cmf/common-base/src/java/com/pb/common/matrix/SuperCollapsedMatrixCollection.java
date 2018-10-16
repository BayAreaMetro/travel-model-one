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

/** A class that collapses 0-cells out of Matrix objects 
    and stores them in a collection, which can be held
    in memory. The class can be used for storing a set of
    transit matrices, for example, so that unconnected zone-pairs do not take 
    up memory space unnecessarily.  The user can add
    matrices, get matrices and get values.
    
    This class stores matrices in char arrays, except for matrices that
    are explicitly created by the user. Those are stored as float arrays.
 *  
 * @author Joel Freedman
 */
public class SuperCollapsedMatrixCollection extends MatrixCollection {

    //for each row
    protected short[] columns;
    //in total
    protected int totalCells;
    
    protected int originalRows;
    protected int originalCols;

    //lookupMatrix is always square, initialized to 0
    //replaced with the column position for non-zero values
    protected short[][] lookupMatrix;
    protected int[] internalNumbers;
    protected int[] externalNumbers;
    boolean debug;
    /**
    Sets up lookup tables based on Matrix m, and stores Matrix m in collection.
    
    @param  m  A Matrix to be used as the key for this set of collapsed matrices.
    Zero values in this matrix will not be stored in this or any subsequent matrix added to 
    this object with the add method.
    @param deb Sets debug to true or false for collection.
    **/
    public SuperCollapsedMatrixCollection(Matrix m, boolean deb) {

        debug = deb;
        addKeyMatrix(m);
    }

    /**
    Sets up lookup tables based on Matrix m, and stores Matrix m in collection.
     
    @param  m  A Matrix to be used as the key for this set of collapsed matrices.
    Zero values in this matrix will not be stored in this or any subsequent matrix added to 
    this object with the add method.
    **/
    public SuperCollapsedMatrixCollection(Matrix m) {

        addKeyMatrix(m);
    }
    /**
     * Sets debug for collection
     * @param deb The debug mode = true/false
     */

    public void setDebug(boolean deb){
        debug=deb;
    }
    /**
    Add key matrix. Will throw an exception if collection is not empty.
    
    @param  m  A Matrix to be used as the key for this set of collapsed matrices.
    Zero values in this matrix will not be stored in this or any subsequent matrix added to 
    this object with the add method.
    **/

    //TODO test for non-square matrix.
    public void addKeyMatrix(Matrix m) {

        if (debug)
            System.out.println(
                "Setting lookup arrays with matrix " + m.getName());

        originalRows=m.getRowCount();
        originalCols=m.getColumnCount();
        lookupMatrix = new short[m.getRowCount()][m.getColumnCount()];
        float[] inRow = new float[m.getColumnCount()];
        columns = new short[m.getColumnCount()];
        internalNumbers = (int[]) m.getInternalNumbers().clone();
        externalNumbers = (int[]) m.getExternalNumbers().clone();

        for (int i = 0; i < m.getRowCount(); ++i) {

            //get row from ivt matrix
            m.getRow((externalNumbers[i+1]), inRow);
            for (int j = 0; j < m.getColumnCount(); ++j) {

                float value = inRow[j];
                lookupMatrix[i][j]=-9999;

                //set lookup matrix
                if (value > 0.0 && value < 99999.9) {
                    lookupMatrix[i][j] = columns[i];
                    ++columns[i];
                    ++totalCells;
                }
            } // end for columns
        } //end for rows
        inRow=null;
        
        addMatrix(m);
        
    };

    /** addMatrix:  Adds a char matrix to collection.  Must be same size
    *   as compressed matrix passed in constructor or in addKeyMatrix.
    *   Only values for cells where key matrix is not 0 will be stored.
    *@param  m  The matrix to add to the collection
    *
    */
    public void addMatrix(Matrix m) {

        CollapsedCharMatrix cm = new CollapsedCharMatrix();
        cm.collapseMatrix(m,lookupMatrix,columns);
        String nameCopy= new String(m.getName());
        matrices.put(nameCopy, cm);
        m=null;
    }
    /**
     * addMatrix
     * Creates a new matrix and adds it to the collection.  This matrix
     * will be stored as collapsed float.
     */
    public void addMatrix(String name, int rows, int cols){
        
        CollapsedFloatMatrix fm = new CollapsedFloatMatrix();
        fm.createMatrix(columns,rows);
        matrices.put(name,fm);
    }    

     /** 
    Returns the value stored in the cell.
    
    @param  row     The user zone number of the origin taz
    @param  column  The user zone number of the destination taz
    @param  name   The name of the matrix- must be the name of the original
                             compressed matrix file passed to either the constructor
                             or the addMatrix() method.
    
    **/
    public float getValue(int row, int column, String name) {

        CollapsedMatrix matrix = (CollapsedMatrix) matrices.get(name);
        return matrix.getValue(row,column,lookupMatrix,internalNumbers);
        
    }
    /** 
    Sets a value stored in the cell.
    
    @param  row     The user zone number of the origin taz
    @param  column  The user zone number of the destination taz
    @param  name   The name of the matrix- must be the name of the original
                             compressed matrix file passed to either the constructor
                             or the addMatrix() method.
    @param value    The value to set                         
    
    **/
    public void setValue(int row, int column, String name, float value) {


        CollapsedMatrix matrix = (CollapsedMatrix) matrices.get(name);
        matrix.setValue(row,column,value,lookupMatrix,internalNumbers);

    }
    /**
     * Get total cells in key matrix for this collection
     * @return int total connected cells
     */
    public int getTotalCells(){
        return totalCells;
    }
    /** 
    Get a matrix from the collection. 
    *@param name  The matrix to get from the collection.
    *
    */
    public Matrix getMatrix(String name){
        
        CollapsedMatrix cMatrix = (CollapsedMatrix) matrices.get(name);

        Matrix m = cMatrix.expandMatrix(lookupMatrix,originalRows,originalCols,externalNumbers);
        m.setName(name);
        m.setDescription(name);
        return m;
        
         
    } 
 
}
