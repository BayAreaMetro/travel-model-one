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

/**
 * A collection of matrix utility functions.
 *
 * @author    Tim Heier
 * @version   1.0, 5/11/2003
 *
 */
public class MatrixUtil {

    /**
     * Print the matrix values to system.out.
     *
     * @param matrix matrix to print
     * @param format controls the display format (e.g. 8.3 or 6.0)
     */
    public static void print(Matrix matrix, String format) {
        for (int r = 0; r < matrix.getRowCount(); ++r) {
            System.out.printf("%4d:", matrix.getExternalRowNumber(r));

            for (int c = 0; c < matrix.getColumnCount(); ++c) {
                System.out.printf(format, matrix.values[r][c]);
            }
            System.out.println();
        }
    }

}
