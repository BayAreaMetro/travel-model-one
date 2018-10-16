/*
 * Copyright 2006 PB Consult Inc.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 * 
 * Created on Jun 27, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
package com.pb.common.matrix.tests;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.NDimensionalMatrixDouble;

import org.junit.Test;

import static org.junit.Assert.*;

public class NDimensionalMatrixDoubleTest {

    @Test
    public void testCreateNDMatrixFromMatrix() {
        int zones = 5;
        Matrix matrix = createMatrrix(zones);
        NDimensionalMatrixDouble ndmatrix = NDimensionalMatrixDouble
                .createNDMatrixFromMatrix(matrix);

        for (int r = 0; r < zones; ++r) {
            int row = r + 1;
            for (int c = 0; c < zones; ++c) {
                int col = c + 1;
                int[] loc = { r, c };

                assertEquals((double) matrix.getValueAt(row, col), ndmatrix
                        .getValue(loc));
            }
        }
    }

    /**
     * @param zones
     * @return
     */
    private Matrix createMatrrix(int zones) {
        Matrix matrix = new Matrix(zones, zones);

        for (int row = 1; row <= zones; ++row) {
            for (int col = 1; col <= zones; ++col) {
                float value = row + (zones - col);
                matrix.setValueAt(row, col, value);
            }
        }
        return matrix;
    }

    @Test
    public void testGetValuesAsMatrix() {
        int zones = 3;
        Matrix inMatrix = createMatrrix(zones);
        NDimensionalMatrixDouble nDMatrixDouble = NDimensionalMatrixDouble
                .createNDMatrixFromMatrix(inMatrix);
        Matrix outMatrix = nDMatrixDouble.getValuesAsMatrix();

        assertEquals(inMatrix.getRowCount(), outMatrix.getRowCount());
        assertEquals(inMatrix.getColumnCount(), outMatrix.getColumnCount());
        
        for (int r = 0; r < inMatrix.getRowCount(); ++r) {
            int row = r + 1;
            
            for (int c = 0; c < inMatrix.getColumnCount(); ++c) {
                int col = c + 1;
                
                assertEquals(inMatrix.getValueAt(row, col), outMatrix
                        .getValueAt(row, col));
            }
        }
    }

}
