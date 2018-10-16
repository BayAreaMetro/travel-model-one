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
public interface CollapsedMatrix {

    void createMatrix(short[] columns,int rows);
    
    float getValue(int row, int column,short[][] lookupMatrix,int[] internalNumbers);
    
    void setValue(int row, int column, float value,short[][] lookupMatrix,int[] internalNumbers);
    
    Matrix expandMatrix(short[][] lookupMatrix,int originalRows,int originalCols,int[] externalNumbers);
    
    void collapseMatrix(Matrix m,short[][] lookupMatrix,short[] columns);
}
