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
package com.pb.common.calculator;

import com.pb.common.matrix.Matrix;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.io.Serializable;

/**
 * Provides generic matrix calculator functionality. See the class
 * MatrixCalculatorTest in com.pb.common.calculator.tests for more
 * information on how to use this class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */

public class MatrixCalculator implements VariableTable,  Serializable {

    private final boolean debug = true;

    private Expression expression;
    private int rowNumber, colNumber;
    private int nRows, nCols, maxSize;

    //Holds list of name/matrix entries
    private HashMap matrixMap = new HashMap();

    //Holds index value for each matrix
    private ArrayList matrixIndex = new ArrayList();

    //Holds a reference to each matrix
    private ArrayList matrixList = new ArrayList();

    Matrix resultMatrix;

    private MatrixCalculator() {

    }

    public MatrixCalculator(String expressionString, HashMap matrixMap) {
        setExpression(expressionString, matrixMap);
    }

    public void setExpression(String expressionString, HashMap matrixMap) {
        this.expression = new Expression(expressionString, this);
        addMatrices(matrixMap);
        parse();
    }

    protected void parse() {
        createMatrixIndex();
        expression.parse();
    }

    public Matrix solve() {

        calculateDimensions();

        resultMatrix = new Matrix(nRows, nCols);

        for (rowNumber=1; rowNumber <= nRows; rowNumber++) {
            for (colNumber=1; colNumber <= nCols; colNumber++) {
                double value = expression.solve();
                resultMatrix.setValueAt(rowNumber, colNumber, (float)value);
            }
        }

        return resultMatrix;
    }

    /** All all matrices to matrix calculator
     *
     * @param matrixMap list of matrices to add
     */
    public void addMatrices(HashMap matrixMap) {

        //Iterate over keys and add each matrix
        Iterator it = matrixMap.keySet().iterator();
        while ( it.hasNext() ) {
            String name = (String) it.next();
            addMatrix(name, (Matrix) matrixMap.get(name));
        }
    }

    public void addMatrix(String name, Matrix m) {
        matrixMap.put(name, m);
    }

    public Matrix getMatrix(String name, Matrix m) {
        return (Matrix) matrixMap.get(name);
    }

    public HashMap getMatrixList() {
        return matrixMap;
    }

    public Matrix removeMatrix(String name, Matrix m) {
        return (Matrix) matrixMap.remove(name);
    }

    /**
     * Iterate over matrices and build a linear list of matrices
     */
    private void createMatrixIndex() {

        matrixIndex.clear();
        matrixList.clear();

        //Iterate over matrix map and build two parallel lists, one for
        //indexing use and one for looking up a matrix
        Iterator it = matrixMap.keySet().iterator();
        while ( it.hasNext() ) {
            String name = (String) it.next();
            matrixIndex.add( name );
            matrixList.add( matrixMap.get(name) );
        }

        if (debug) {
            for (int i=0; i < matrixIndex.size(); i++) {
                String name = (String) matrixIndex.get(i);
                System.out.println("createMatrixIndex, name="+name+", index="+i);
            }
        }

    }

    /**
     * Iterate over matrices and find maximum dimensions
     */
    private void calculateDimensions() {

        nRows = 0;
        nCols = 0;

        Iterator it = matrixMap.keySet().iterator();
        while ( it.hasNext() ) {
            String name = (String) it.next();
            Matrix m = (Matrix) matrixMap.get(name);

            nRows = Math.max(nRows, m.getRowCount());
            nCols = Math.max(nCols, m.getColumnCount());
        }

        maxSize = Math.max(nRows, nCols);

        if (debug) {
            System.out.println("calculateDimensions, nRows="+nRows+", nCols="+nCols);
        }
    }


    //------------------------ Variable Table Methods ------------------------

    /**
     * Called to get an index value for a variable
     */
    public final int getIndexValue(String variableName) {

        int index = -1;

        //Do a linear search to find requested variable name and return
        //the index into the matrixlist array
        for (int i=0; i < matrixIndex.size(); i++) {
            String name = (String) matrixIndex.get(i);
            if (name.equalsIgnoreCase(variableName)) {
                index = i;
                break;
            }
        }

        if (index == -1) {
            System.out.println("getIndexValue, name="+variableName+", index="+index+", not found in variable table");
        }

        return index;
    }

    /**
     * Called to get a value for an indexed variable
     */
    public final double getValueForIndex(int variableIndex) {

        Matrix m = (Matrix) matrixList.get(variableIndex);
        return m.getValueAt(rowNumber, colNumber);
    }

    /**
     * Called to get an index value for an assignment variable
     */
    public final int getAssignmentIndexValue(String s) {

        return getIndexValue( s );
    }


    /**
     * Called to set a value for a given variable name
     */
    public final void setValue(String variableName, double variableValue) {

        int index = getIndexValue( variableName );

        Matrix m = (Matrix) matrixList.get( index );
        m.setValueAt(rowNumber, colNumber, (float)variableValue);
    }

    /**
     * Called to set a value for a given variable index
     */
    public final void setValue(int variableIndex, double variableValue) {

        Matrix m = (Matrix) matrixList.get( variableIndex );
        m.setValueAt(rowNumber, colNumber, (float)variableValue);
    }

    /**
     * Called to get an index value for a given variable index
     */
    public final double getValueForIndex(int variableIndex, int arrayIndex) {
        throw new UnsupportedOperationException();
    }
    
}
