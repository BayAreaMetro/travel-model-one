/*
 * Copyright 2007 PB Americas
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
 * Created on Oct 19, 2006 by Andrew Stryker <stryker@pbworld.com>
 */

package com.pb.common.matrix;

import static java.lang.Math.abs;
import static java.lang.Math.max;
import static java.lang.Math.min;

import org.apache.log4j.Logger;

/**
 * Standard two dimensional matrix balancing using iterative proportional
 * fitting.
 * 
 * The balancing algorithm closes when the any of the the three termination
 * criteria are met. The criteria are: 1) number of iterations, 2) allowable
 * absolute error, and 3) allowable relative error. At least one termination
 * criterion must be set and the algorithm will complain if the maximum
 * iterations is not set.
 * 
 * @author Andrew Stryker
 * @version 0.2
 */
public class MatrixBalancer {
    private Logger logger = Logger.getLogger(MatrixBalancer.class);

    private Matrix seed;

    private RowVector columnTargets;

    private ColumnVector rowTargets;

    private double maxRelativeError = 0;

    private boolean maxRelativeErrorSet = false;

    private double maxAbsoluteError = 0;

    private boolean maxAbsoluteErrorSet = false;

    private int maxIterations = 20;

    private boolean maxIterationsSet = false;

    private double relativeError;

    private double absoluteError;

    private int iteration;

    /**
     * Set allowable balancing error as a difference ratio.
     * 
     * @param maxRelativeError
     */
    public void setMaximumRelativeError(double maxRelativeError) {
        this.maxRelativeError = maxRelativeError;
        maxRelativeErrorSet = true;
    }

    /**
     * Set allowable balancing error as a difference ratio.
     * 
     * @param maxAbsoluteError
     */
    public void setMaximumAbsoluteError(double maxAbsoluteError) {
        this.maxAbsoluteError = maxAbsoluteError;
        maxAbsoluteErrorSet = true;
    }

    /**
     * Set maximum number of iterations.
     * 
     * @param maxIterations
     */
    public void setMaximumIterations(int maxIterations) {
        this.maxIterations = maxIterations;
        maxIterationsSet = true;
    }

    /**
     * Set the seed matrix.
     * 
     * Using this method preserves the orginal matrix.
     * 
     * @param seed matrix
     */
    public void setSeed(Matrix seed) {
        this.seed = (Matrix) seed.clone();
    }

    /**
     * Set the targets.
     * 
     */
    public void setTargets(ColumnVector rowTargets, RowVector columnTargets) {
        this.rowTargets = rowTargets;
        this.columnTargets = columnTargets;
    }

    /**
     * Balance a seed matrix to row and column targets.
     * 
     * A seed matrix, row and column targets, and termination criteria must be
     * set prior to calling this method.
     */
    public void balance() {
        seed = balance(seed, rowTargets, columnTargets);
    }

    /**
     * Balance a seed matrix to a row and column targets.
     * 
     * Calling this method avoids cloning but will overwrite the seed matrix.
     * Use with caution. Termination criteria must be set prior to calling this
     * method.
     * 
     * @param seed matrix
     * @param row targets
     * @param column targets
     */
    public Matrix balance(Matrix seed, ColumnVector rowTargets,
            RowVector columnTargets) {
        checkTargetTotals(rowTargets, columnTargets);
        checkClosureSet();
        iteration = 1;

        logger.debug("Beginning matrix balancing using iterative proportional "
                + "fitting.");

        while (!isClosed()) {
            logger.debug("Iteration " + iteration);

            seed = balance(seed, rowTargets);
            seed = balance(seed, columnTargets);
            computeErrors(seed, rowTargets);

            logger.debug("Balancing relative error: " + relativeError
                    + ", absolute error: " + absoluteError);
            iteration += 1;
        }

        return seed;
    }

    /**
     * Report closure conditions and throw an excpetion if none are set.
     */
    private void checkClosureSet() {
        if (!(maxIterationsSet || maxRelativeErrorSet || maxAbsoluteErrorSet)) {
            String msg = "No closure criteria set.";

            logger.error(msg);
            throw new MatrixException(msg);
        }

        if (maxIterationsSet) {
            logger.info("Maximum number of iterations set to " + maxIterations);
        } else {
            logger.warn("No maximum number of iterations set.");
        }

        if (maxRelativeErrorSet) {
            logger.info("Minimum relative error set to " + maxRelativeError);
        } else {
            logger.warn("Minimum relative error not set.");
        }

        if (maxAbsoluteErrorSet) {
            logger.info("Minimum absolute error set to " + maxAbsoluteError);
        } else {
            logger.warn("Minimum absolute error not set.");
        }
    }

    /**
     * @return closoure status
     */
    private boolean isClosed() {
        boolean closure = false;

        if (maxIterationsSet && iteration > maxIterations) {
            logger.info("Reached iteration maximum.");
            closure = true;
        }

        if (iteration > 1) {
            if (maxRelativeErrorSet && relativeError < maxRelativeError) {
                logger.info("Reached minimum relative error.");
                closure = true;
            }
            if (maxAbsoluteErrorSet && absoluteError < maxAbsoluteError) {
                logger.info("Reached minimum absolute error.");
                closure = true;
            }
        }

        if (closure) {
            logger.info("Closed in " + iteration + " iterations.");
            logger.info("Final relative error: " + relativeError);
            logger.info("Final absoute error: " + absoluteError);
        }

        return closure;
    }

    /**
     * Check to see that the Column and Row Targets sums are within the error.
     */
    private void checkTargetTotals(ColumnVector rowTargets,
            RowVector columnTargets) {
        double rowTargetSum = rowTargets.getSum();
        double colTargetSum = columnTargets.getSum();
        double diffPercent = relativeDifference(rowTargetSum, colTargetSum);

        if (diffPercent > maxRelativeError) {
            String message = "Row targets sum (" + rowTargetSum + ")"
                    + " does not match column target sum (" + colTargetSum
                    + ")";

            logger.error(message);
            throw new MatrixException(message);
        }
    }

    /**
     * @param x
     * @param y
     * @return relative difference
     */
    private double relativeDifference(double x, double y) {
        return abs(x - y) / min(x, y);
    }

    /**
     * Balance to row targets.
     */
    private Matrix balance(Matrix seed, ColumnVector rowTargets) {
        int[] extRowNumbers = seed.getExternalRowNumbers();

        for (int r = 1; r < extRowNumbers.length; ++r) {
            int row = extRowNumbers[r];
            float rowSum = seed.getRowSum(row);
            float factor;
            if (rowSum == 0) {
                if (rowTargets.getValueAt(row) == 0) {
                    factor = 0;
                } else {
                    throw new RuntimeException("Row " + row
                            + ":  Seed row adds to 0 but target is NOT zero.");
                }
            } else {
                factor = rowTargets.getValueAt(row) / rowSum;
            }

            logger.debug("Scaling factor for row " + row + ": " + factor);

            scaleRow(seed, row, factor);
        }

        return seed;
    }

    /**
     * Scale a row.
     * 
     * @param seed
     * @param row
     * @param factor
     */
    private void scaleRow(Matrix seed, int row, float factor) {
        int[] extColNumbers = seed.getExternalColumnNumbers();
        for (int c = 1; c < extColNumbers.length; ++c) {
            int col = extColNumbers[c];
            float value = seed.getValueAt(row, col) * factor;

            seed.setValueAt(row, col, value);
        }
    }

    /**
     * Balance to column targets.
     */
    private Matrix balance(Matrix seed, RowVector columnTargets) {
        int[] extColNumbers = seed.getExternalColumnNumbers();

        for (int c = 1; c < extColNumbers.length; ++c) {
            int col = extColNumbers[c];
            float colSum = seed.getColumnSum(col);
            float factor;

            if (colSum == 0) {
                if (columnTargets.getValueAt(col) == 0) {
                    factor = 0;
                } else {
                    throw new RuntimeException(
                            "Column "
                                    + col
                                    + ":  Seed column adds to 0 but target is NOT zero.");
                }
            } else {
                factor = columnTargets.getValueAt(col) / colSum;
            }

            logger.debug("Scaling factor for column " + col + ": " + factor);

            scaleColumn(seed, col, factor);
        }
        return seed;
    }

    /**
     * Scale a column.
     * 
     * @param seed
     * @param col
     * @param factor
     */
    private void scaleColumn(Matrix seed, int col, float factor) {
        int[] extRowNumbers = seed.getExternalRowNumbers();
        for (int r = 1; r < extRowNumbers.length; ++r) {
            int row = extRowNumbers[r];
            float value = seed.getValueAt(row, col) * factor;

            seed.setValueAt(row, col, value);
        }
    }

    /**
     * Compute balancing error on rows.
     */
    private void computeErrors(Matrix seed, ColumnVector rowTargets) {
        int[] extRowNumbers = seed.getExternalRowNumbers();
        relativeError = 0;
        absoluteError = 0;

        for (int r = 1; r < extRowNumbers.length; ++r) {
            int row = extRowNumbers[r];
            float targetSum = rowTargets.getValueAt(row);
            float seedRowSum = seed.getRowSum(row);
            double relative;
            if (targetSum == 0 && seedRowSum == 0) {
                relative = 0;
            } else {
                relative = relativeDifference(targetSum, seedRowSum);
            }
            double absolute = abs(targetSum - seedRowSum);

            relativeError = max(relative, relativeError);
            absoluteError = max(absolute, absoluteError);

            logger.debug("Relative error on row " + row + ": " + relative
                    + ", absolute error: " + absoluteError);
        }
    }

    /**
     * Get the relative balancing error.
     */
    public double getRelativeError() {
        return relativeError;
    }

    /**
     * Get the absolute balancing absolute error.
     */
    public double getAbsoluteError() {
        return absoluteError;
    }

    /**
     * Get the current number of balancing iterations.
     */
    public int getIteration() {
        return iteration;
    }

    /**
     * Get the balanced matrix.
     * 
     * @return balanced matrix
     */
    public Matrix getBalancedMatrix() {
        return seed;
    }

    /**
     * Scale row targets sum to column target sum.
     */
    public static void scaleRowTargets(ColumnVector rowTargets,
            RowVector columnTargets) {
        rowTargets
                .scale((float) (columnTargets.getSum() / rowTargets.getSum()));
    }

    /**
     * Scale column targets sum to row target sum.
     */
    public static void scaleColumnTargets(ColumnVector rowTargets,
            RowVector columnTargets) {
        columnTargets.scale((float) (rowTargets.getSum() / columnTargets
                .getSum()));
    }

    /**
     * Scale targets to the average sum.
     */
    public static void scaleTargetsToAvg(ColumnVector rowTargets,
            RowVector columnTargets) {
        float avg = (float) ((rowTargets.getSum() + columnTargets.getSum()) / 2.0);
        columnTargets.scale((float) (avg / columnTargets.getSum()));
        rowTargets.scale((float) (avg / rowTargets.getSum()));
    }
}
