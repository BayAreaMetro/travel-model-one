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
 * Solve a system of linear equations using LU decomposition.
 */
public class LinearSystem extends SquareMatrix {
    private static final float TOLERANCE = Epsilon.floatValue();

    /** max iters for improvement = twice # of significant digits */
    private static final int MAX_ITER;

    static {
        int i = 0;
        float t = TOLERANCE;
        while (t < 1) {
            ++i;
            t *= 10;
        }
        MAX_ITER = 2 * i;
    }

    protected SquareMatrix LU;
    /** decomposed matrix A = LU */
    protected int permutation[];
    /** row index permutation vector */
    protected int exchangeCount;     /** row exchange count */

    /**
     * Constructor.
     * @param n the number of rows = the number of columns
     */
    public LinearSystem(int n) {
        super(n);
        reset();
    }

    /**
     * Constructor.
     * @param values the array of values
     */
    public LinearSystem(float values[][]) {
        super(values);
    }

    /**
     * Set the values of the matrix.
     * @param values the 2-d array of values
     */
    protected void setValues(float values[][]) {
        super.setValues(values);
        reset();
    }

    /**
     * Set the value of element [r,c] in the matrix. Overrides method in base class.
     * @param r the row index, 0..nRows
     * @param c the column index, 0..nRows
     * @param value the value
     * @throws com.pb.common.matrix.MatrixException for invalid index
     */
    public void setValueAt(int r, int c, float value) throws MatrixException {
        super.setValueAt(r, c, value);
        reset();
    }

    /**
     * Set a row of this matrix from a row vector.
     * @param rv the row vector
     * @param r the row index
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *                                an invalid vector size
     */
    public void setRow(RowVector rv, int r) throws MatrixException {
        super.setRow(rv, r);
        reset();
    }

    /**
     * Set a column of this matrix from a column vector.
     * @param cv the column vector
     * @param c the column index
     * @throws com.pb.common.matrix.MatrixException for an invalid index or
     *                                an invalid vector size
     */
    public void setColumn(ColumnVector cv, int c) throws MatrixException {
        super.setColumn(cv, c);
        reset();
    }

    /**
     * Reset. Invalidate LU and the permutation vector.
     */
    protected void reset() {
        LU = null;
        permutation = null;
        exchangeCount = 0;
    }

    /**
     * Solve Ax = b for x using the Gaussian elimination algorithm.
     * @param b the right-hand-side column vector
     * @param improve true to improve the solution
     * @return the solution column vector
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    public ColumnVector solve(ColumnVector b, boolean improve) throws MatrixException {
        // Validate b's size.
        if (b.nRows != nRows) {
            throw new MatrixException(
                    MatrixException.INVALID_DIMENSIONS);
        }

        decompose();

        // Solve Ly = b for y by forward substitution.
        // Solve Ux = y for x by back substitution.
        ColumnVector y = forwardSubstitution(b);
        ColumnVector x = backSubstitution(y);

        // Improve and return x.
        if (improve) improve(b, x);
        return x;
    }

    /**
     * Print the decomposed matrix LU.
     * @param width the column width
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    public void printDecomposed(int width) throws MatrixException {
        decompose();

        String format = "%" + width + "f";

        for (int r = 0; r < nRows; ++r) {
            int pr = permutation[r];    // permuted row index

            System.out.printf("Row %3d:", r+1);

            for (int c = 0; c < nCols; ++c) {
                System.out.printf(format, LU.values[pr][c]);
            }
            System.out.println();
        }
    }

    /**
     * Compute the upper triangular matrix U and lower triangular
     * matrix L such that A = L*U.  Store L and U together in
     * matrix LU.  Compute the permutation vector permutation of
     * the row indices.
     * @throws com.pb.common.matrix.MatrixException for a zero row or
     *                                a singular matrix
     */
    protected void decompose() throws MatrixException {

        // Return if the decomposition is valid.
        if (LU != null) return;

        // Create a new LU matrix and permutation vector.
        // LU is initially just a copy of the values of this system.
        LU = new SquareMatrix(this.copyValues2D());
        permutation = new int[nRows];

        float scales[] = new float[nRows];

        // Loop to initialize the permutation vector and scales.
        for (int r = 0; r < nRows; ++r) {
            permutation[r] = r;     // initially no row exchanges

            // Find the largest row element.
            float largestRowElmt = 0;
            for (int c = 0; c < nRows; ++c) {
                float elmt = Math.abs(LU.getValueAt(r, c));
                if (largestRowElmt < elmt) largestRowElmt = elmt;
            }

            // Set the scaling factor for row equilibration.
            if (largestRowElmt != 0) {
                scales[r] = 1 / largestRowElmt;
            } else {
                throw new MatrixException(MatrixException.ZERO_ROW);
            }
        }

        // Do forward elimination with scaled partial row pivoting.
        forwardElimination(scales);

        // Check bottom right element of the permuted matrix.
        if (LU.getValueAt(permutation[nRows - 1], nRows - 1) == 0) {
            throw new MatrixException(MatrixException.SINGULAR);
        }
    }

    /**
     * Do forward elimination with scaled partial row pivoting.
     * @param scales the scaling vector
     * @throws com.pb.common.matrix.MatrixException for a singular matrix
     */
    private void forwardElimination(float scales[]) throws MatrixException {
        // Loop once per pivot row 0..nRows-1.
        for (int rPivot = 0; rPivot < nRows - 1; ++rPivot) {
            float largestScaledElmt = 0;
            int rLargest = 0;

            // Starting from the pivot row rPivot, look down
            // column rPivot to find the largest scaled element.
            for (int r = rPivot; r < nRows; ++r) {

                // Use the permuted row index.
                int pr = permutation[r];
                float absElmt = Math.abs(LU.getValueAt(pr, rPivot));
                float scaledElmt = absElmt * scales[pr];

                if (largestScaledElmt < scaledElmt) {

                    // The largest scaled element and
                    // its row index.
                    largestScaledElmt = scaledElmt;
                    rLargest = r;
                }
            }

            // Is the matrix singular?
            if (largestScaledElmt == 0) {
                throw new MatrixException(MatrixException.SINGULAR);
            }

            // Exchange rows if necessary to choose the best
            // pivot element by making its row the pivot row.
            if (rLargest != rPivot) {
                int temp = permutation[rPivot];
                permutation[rPivot] = permutation[rLargest];
                permutation[rLargest] = temp;

                ++exchangeCount;
            }

            // Use the permuted pivot row index.
            int prPivot = permutation[rPivot];
            float pivotElmt = LU.getValueAt(prPivot, rPivot);

            // Do the elimination below the pivot row.
            for (int r = rPivot + 1; r < nRows; ++r) {

                // Use the permuted row index.
                int pr = permutation[r];
                float multiple = LU.getValueAt(pr, rPivot) / pivotElmt;

                // Set the multiple into matrix L.
                LU.setValueAt(pr, rPivot, multiple);

                // Eliminate an unknown from matrix U.
                if (multiple != 0) {
                    for (int c = rPivot + 1; c < nCols; ++c) {
                        float elmt = LU.getValueAt(pr, c);

                        // Subtract the multiple of the pivot row.
                        elmt -= multiple * LU.getValueAt(prPivot, c);
                        LU.setValueAt(pr, c, elmt);
                    }
                }
            }
        }
    }

    /**
     * Solve Ly = b for y by forward substitution.
     * @param b the column vector b
     * @return the column vector y
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    private ColumnVector forwardSubstitution(ColumnVector b) throws MatrixException {
        ColumnVector y = new ColumnVector(nRows);

        // Do forward substitution.
        for (int r = 0; r < nRows; ++r) {
            int pr = permutation[r];     // permuted row index
            float dot = 0;
            for (int c = 0; c < r; ++c) {
                dot += LU.getValueAt(pr, c) * y.getValueAt(c);
            }
            y.setValueAt(r, b.getValueAt(pr) - dot);
        }

        return y;
    }

    /**
     * Solve Ux = y for x by back substitution.
     * @param y the column vector y
     * @return the solution column vector x
     * @throws com.pb.common.matrix.MatrixException if an error occurred
     */
    private ColumnVector backSubstitution(ColumnVector y) throws MatrixException {
        ColumnVector x = new ColumnVector(nRows);

        // Do back substitution.
        for (int r = nRows - 1; r >= 0; --r) {
            int pr = permutation[r];     // permuted row index
            float dot = 0;
            for (int c = r + 1; c < nRows; ++c) {
                dot += LU.getValueAt(pr, c) * x.getValueAt(c);
            }
            x.setValueAt(r, (y.getValueAt(r) - dot) / LU.getValueAt(pr, r));
        }

        return x;
    }

    /**
     * Iteratively improve the solution x to machine accuracy.
     * @param b the right-hand side column vector
     * @param x the improved solution column vector
     * @throws com.pb.common.matrix.MatrixException if failed to converge
     */
    private void improve(ColumnVector b, ColumnVector x) throws MatrixException {
        // Find the largest x element.
        float largestX = 0;
        for (int r = 0; r < nRows; ++r) {
            float absX = Math.abs(x.values[r][0]);
            if (largestX < absX) largestX = absX;
        }

        // Is x already as good as possible?
        if (largestX == 0) return;

        ColumnVector residuals = new ColumnVector(nRows);

        // Iterate to improve x.
        for (int iter = 0; iter < MAX_ITER; ++iter) {

            // Compute residuals = b - Ax.
            // Must use double precision!
            for (int r = 0; r < nRows; ++r) {
                double dot = 0;
                float row[] = values[r];
                for (int c = 0; c < nRows; ++c) {
                    double elmt = getValueAt(r, c);
                    dot += elmt * x.getValueAt(c);      // dbl.prec. *
                }
                double value = b.getValueAt(r) - dot;   // dbl.prec. -
                residuals.setValueAt(r, (float) value);
            }

            // Solve Az = residuals for z.
            ColumnVector z = solve(residuals, false);

            // Set x = x + z.
            // Find largest the largest difference.
            float largestDiff = 0;
            for (int r = 0; r < nRows; ++r) {
                float oldX = x.getValueAt(r);
                x.setValueAt(r, oldX + z.getValueAt(r));

                float diff = Math.abs(x.getValueAt(r) - oldX);
                if (largestDiff < diff) largestDiff = diff;
            }

            // Is any further improvement possible?
            if (largestDiff < largestX * TOLERANCE) return;
        }

        // Failed to converge because A is nearly singular.
        throw new MatrixException(MatrixException.NO_CONVERGENCE);
    }
}