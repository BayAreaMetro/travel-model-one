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
package com.pb.common.matrix.ui;

import com.pb.common.matrix.Matrix;

import javax.swing.table.AbstractTableModel;

/**
 * Provides an implementation of the AbstractTableModel which partially
 * implements the TableModel interface. This model determines how data
 * elements from the underlying matrix will be shown in a Table.
 * 
 * @author    Tim.Heier
 * @version   1.0, 10/22/2004
 */
public class MatrixDataModel extends AbstractTableModel {

    Matrix theMatrix;
    
    public MatrixDataModel(Matrix m) {
        this.theMatrix = m;
    }
    
    public int getRowCount() {
        return theMatrix.getRowCount();
    }

    public int getColumnCount() {
        return theMatrix.getColumnCount();
    }

    public Object getValueAt(int rowIndex, int columnIndex) {
        return Float.toString(theMatrix.getValueAt(theMatrix.externalRowNumbers[rowIndex+1], theMatrix.externalColumnNumbers[columnIndex+1]));
    }

    public String getColumnName(int columnIndex) {
        return String.valueOf(theMatrix.externalColumnNumbers[columnIndex+1]);
    }

    public int getExternalRowNumber(int i) {
        return theMatrix.getExternalRowNumber(i);
    }

    public int getExternalColNumber(int i) {
        return theMatrix.getExternalColumnNumber(i);
    }
}
