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
/*
 * Created on Dec 15, 2004
 *
 * An interface for a collapsed matrix to be stored in the matrix collection.
 */
package com.pb.common.matrix;

/**
 * @author Freedman
 *
 */
public class CollapsedFloatMatrix implements CollapsedMatrix{

    float[][] matrix;
    
    public void createMatrix(short[] columns,int rows){
        matrix = new float[rows][];
        for (int i = 0; i < rows; ++i) {
            //initialize memory for row in matrix
            matrix[i] = new float[columns[i]];
        }
    }
    
    public float getValue(int row, int column,short[][] lookupMatrix,int[] internalNumbers){
        int i = internalNumbers[row];
        int j = internalNumbers[column];
        
        if(lookupMatrix[i][j]==-9999)
            return 0;
        return matrix[i][lookupMatrix[i][j]];

    }
    
    public void setValue(int row, int column, float value,short[][] lookupMatrix,int[] internalNumbers){
        int i = internalNumbers[row];
        int j = internalNumbers[column];

        matrix[i][lookupMatrix[i][j]]= value;
    }
    
    public Matrix expandMatrix(short[][] lookupMatrix,int originalRows,int originalCols,int[] externalNumbers){
        Matrix m = new Matrix(originalRows, originalCols);
        
        for(int i=0;i<lookupMatrix.length;++i){

            float[] row = new float[originalCols];
            
            for(int j=0;j<lookupMatrix[i].length;++j){

                float value=0;                
                if(lookupMatrix[i][j]!=-9999)
                    value=matrix[i][lookupMatrix[i][j]];
                
                row[j]=value;        
            }
            m.setRow(row, externalNumbers[i+1]);
        }
        m.setExternalNumbers(externalNumbers);
        return m;
    }
    
    public void collapseMatrix(Matrix m,short[][] lookupMatrix,short[] columns){
        createMatrix(columns,m.nRows);
        float[] inRow = new float[m.getColumnCount()];
        int[] externalNumbers = m.getExternalNumbers();
        
        for (int i = 0; i < m.getRowCount(); ++i) {
            //get row
            m.getRow((externalNumbers[i+1]), inRow);

            //write data to matrix
            for (int j = 0; j < m.getColumnCount(); ++j) {
                if (lookupMatrix[i][j] != -9999) {
                    matrix[i][lookupMatrix[i][j]] = inRow[j];
                }
            }
        }
    }
}
