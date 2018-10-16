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

public class IdentityMatrix extends SquareMatrix
{
    /**
     * Constructor.
     * @param n the number of rows == the number of columns
     */
    public IdentityMatrix(int n)
    {
        super(n);
        for (int i = 0; i < n; ++i) values[i][i] = 1;
    }

    /**
     * Convert a square matrix into an identity matrix.
     * @param sm the square matrix to convert
     */
    public static void convert(SquareMatrix sm)
    {
        for (int r = 0; r < sm.nRows; ++r) {
            for (int c = 0; c < sm.nCols; ++c) {
                sm.values[r][c] = (r == c) ? 1 : 0;
            }
        }
    }
}