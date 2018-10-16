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

import java.io.Serializable;
import java.util.HashMap;

/** A class that stores rectangular matrices in memory.
 *  matrices can be retrieved or their values
 *  can be retrieved.
 *
 * @author Joel Freedman
 */
public class MatrixCollection implements Serializable {

    HashMap matrices = new HashMap(100);

     /**
     Default constructor
     **/
     public MatrixCollection(){
     }
     /**
     Constructor to add matrix
     **/
     public MatrixCollection(Matrix m){
        addMatrix(m);
    }

    @Override
    public String toString() {
        return "" + matrices;
    }

    /**
     * Adds a matrix to collection.
     * 
     * @param m
     *            The matrix to add to the collection.
     * 
     */
	public void addMatrix(Matrix m) throws MatrixException{

	    //make sure name is valid
	    if(m.getName().compareTo("")==0){
	        System.out.println("Attempting to add matrix with no name to MatrixCollection");
            throw new MatrixException("");
        }
        if(matrices.containsKey(m.getName())){
            matrices.remove(m.getName());
        }
        matrices.put(m.getName(),m);
	}
	 /**
     * addMatrix
     * Creates a new matrix and adds it to the collection.
     */
    public void addMatrix(String name, int rows, int cols){

        Matrix m = new Matrix(name,"",rows,cols);

        if(matrices.containsKey(name)){
            matrices.remove(name);
        }
        matrices.put(name,m);
    }

	/**
	Get a matrix from the collection.
	*@param name  The matrix to get from the collection.
	*
	*/
	public Matrix getMatrix(String name){

        return (Matrix) matrices.get(name);
	}

	/** getValue():  Returns the value stored in the cell.
	*
	*@param  row      The row to return
	*@param  column   The column to return
	*@param  name     The name of the matrix
	*
	*/
	public float getValue(int row, int column, String name){

		Matrix m = (Matrix) matrices.get(name);
		if (m == null) throw new RuntimeException("Matrix " + name + " is null.");
        return m.getValueAt(row, column);

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

        Matrix m = (Matrix) matrices.get(name);

        m.setValueAt(row, column, value);

    }
    /** Get the Hashmap back
     */
    public HashMap getHashMap(){
        return matrices;
    }

    /**
     * Get the number of matrices in this collection
     *
     * @return The number of matrices in the collection.
     */
    public int getNumberOfMatrices(){
        return matrices.size();
    }
}


































