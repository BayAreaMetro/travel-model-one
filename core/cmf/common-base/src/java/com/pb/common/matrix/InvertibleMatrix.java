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
 * A matrix that can be inverted.  Also, compute its determinant,
 * norm, and condition number.
 */
public class InvertibleMatrix extends LinearSystem {
    /**
     * Constructor.
     * @param n the number of rows = the number of columns
     */
    public InvertibleMatrix(int n) {
        super(n);
    }

    /**
     * Constructor.
     * @param values the array of values
     */
    public InvertibleMatrix(float values[][]) {
        super(values);
    }

    /**
     * Compute the inverse of this matrix.
     * @return the inverse matrix
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    public InvertibleMatrix inverse() throws MatrixException {
        InvertibleMatrix inverse = new InvertibleMatrix(nRows);
        IdentityMatrix identity = new IdentityMatrix(nRows);

        // Compute each column of the inverse matrix
        // using columns of the identity matrix.
        for (int c = 0; c < nCols; ++c) {
            ColumnVector col = solve(identity.getColumn(c), true);
            inverse.setColumn(col, c);
        }

        return inverse;
    }

    /**
     * Compute the determinant.
     * @return the determinant
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    public float determinant() throws MatrixException {
        decompose();

        // Each row exchange during forward elimination flips the sign
        // of the determinant, so check for an odd number of exchanges.
        float determinant = ((exchangeCount & 1) == 0) ? 1 : -1;

        // Form the product of the diagonal elements of matrix U.
        for (int i = 0; i < nRows; ++i) {
            int pi = permutation[i];        // permuted index
            determinant *= LU.getValueAt(pi, i);
        }

        return determinant;
    }

    /**
     * Compute the Euclidean norm of this matrix.
     * @return the norm
     */
    public float norm() {
        float sum = 0;

        for (int r = 0; r < nRows; ++r) {
            for (int c = 0; c < nCols; ++c) {
                float v = values[r][c];
                sum += v * v;
            }
        }

        return (float) Math.sqrt(sum);
    }

    /**
     * Compute the condition number based on the Euclidean norm.
     * @return the condition number
     */
    public float condition() throws MatrixException {
        return norm() * inverse().norm();
    }
}