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

import org.apache.log4j.Logger;

import static java.lang.Math.*;
import java.text.DecimalFormat;

/**
 * Standard two dimensional matrix balancing using iterative proportional
 * fitting.
 *
 * The balancing algorithm closes when the any of the the three termination
 * criteria are met. The criteria are: 1) number of iterations, 2) allowable
 * relative error. At least one termination criterion must be set and the
 * algorithm will complain if the maximum iterations is not set.
 *
 * To Balance a matrix create a new "MatrixBalancerRM" and call ".balance();"
 *  The following variables have to be set:
 *    Matrix seedmat: Seed of Matrix (Default = 1)
 *    ColumnVector rowTargets: Target values the rows have to match
 *    RowVector colTargets: Target values the columns have to match
 *    MatrixBalancerRM.ADJUST adjust: Procedure to adjust target sums, select on of the following
 *        MatrixBalancerRM.ADJUST.NONE                no adjustments, totals of rows and sums have to match
 *        MatrixBalancerRM.ADJUST.ROW_TARGETS         Row targets are adjusted to match column total
 *        MatrixBalancerRM.ADJUST.COLUMN_TARGETS      Column targets are adjusted to match row total
 *        MatrixBalancerRM.ADJUST.BOTH_USING_AVERAGE  Column targets and row targets are adjusted to the average total
 *  At least one of following variables has to be set:
 *    int maxIterations: Maximum number of iterations (maxIterations >= 1)
 *    double maxRelativeError: Maximum relative error tolerated (0 <= maxRelativeError <= 1)
 *
 *  There are three constructors available:
 *  Case 1: Set relative Error
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, adjust);
 *  Case 2: Set maximum number of iterations
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxIterations, adjust);
 *  Case 3: Set relative Error and maximum of iterations
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
 *
 *  To balance the matrix call:
 *    Matrix new_matrix_name = matrix_object.balance();
 *
 * @author Andrew Stryker
 * Changed by Kimberly Grommes, Christi Willison, Rolf Moeckel, May 2007
 * @version 1.0
 */

public class MatrixBalancerRM {

    private Logger logger = Logger.getLogger(MatrixBalancerRM.class);
    private Matrix seed;
    private RowVector columnTargets;
    private ColumnVector rowTargets;
    private double maxRelativeError = 0;
    private boolean maxRelativeErrorSet = false;
    private int maxIterations = 20;
    private boolean maxIterationsSet = false;
    public static enum ADJUST {NONE, ROW_TARGETS, COLUMN_TARGETS, BOTH_USING_AVERAGE}
    ADJUST userAdjustChoice;
    
    /**
     * **
     * Set constructor of MatrixBalancerRM
     * Case 1: set maxRelativeError
     * @param seed Seed matrix
     * @param rowTargets Row target values
     * @param columnTargets Column target values
     * @param maxRelativeError Maximum relative error
     * @param adjust Adjust target values to match (NONE, ROW_TARGETS, COLUMN_TARGETS, BOTH_USING_AVERAGE)
     */
    public MatrixBalancerRM(Matrix seed, ColumnVector rowTargets, RowVector columnTargets, double maxRelativeError, ADJUST adjust){

        this.seed = seed;
        this.columnTargets = columnTargets;
        this.rowTargets = rowTargets;
        this.maxRelativeError = maxRelativeError;
        maxRelativeErrorSet = true;
        this.userAdjustChoice = adjust;
    }


    /**
     * Set constructor of MatrixBalancerRM
     * Case 2: set maxIterations
     * @param seed Seed matrix
     * @param rowTargets Row target values
     * @param columnTargets Column target values
     * @param maxIterations Maximum relative error
     * @param adjust Adjust target values to match (NONE, ROW_TARGETS, COLUMN_TARGETS, BOTH_USING_AVERAGE)
     */
    public MatrixBalancerRM(Matrix seed, ColumnVector rowTargets, RowVector columnTargets, int maxIterations, ADJUST adjust){

        this.seed = seed;
        this.columnTargets = columnTargets;
        this.rowTargets = rowTargets;
        this.maxIterations = maxIterations;
        maxIterationsSet = true;
        this.userAdjustChoice = adjust;
    }


    /**
     * Set constructor of MatrixBalancerRM
     * Case 3: set maxRelativeError and maxIterations
     * @param seed Seed matrix
     * @param rowTargets Row target values
     * @param columnTargets Column target values
     * @param maxRelativeError Maximum relative error
     * @param maxIterations Maximum relative error
     * @param adjust Adjust target values to match (NONE, ROW_TARGETS, COLUMN_TARGETS, BOTH_USING_AVERAGE)
     */
    public MatrixBalancerRM(Matrix seed, ColumnVector rowTargets, RowVector columnTargets,  double maxRelativeError, int maxIterations, ADJUST adjust){

        this.seed = seed;
        this.columnTargets = columnTargets;
        this.rowTargets = rowTargets;
        this.maxRelativeError = maxRelativeError;
        maxRelativeErrorSet = true;
        this.maxIterations = maxIterations;
        maxIterationsSet = true;
        this.userAdjustChoice = adjust;
    }


    /**
     * Balance a seed matrix to a row and column targets.
     *
     * Calling this method avoids cloning but will overwrite the seed matrix.
     * Use with caution. Termination criteria must be set prior to calling this
     * method.
     * @return seed
     * @param log Logger
     *
     */
    public Matrix balance(Logger log) {

        adjustTargetTotals();
        checkClosureSet();
        double relativeError = 0.0;
        int iteration = 0;
        log.info("Beginning matrix balancing using iterative proportional "
                + "fitting.");
        while (!isClosed(iteration, relativeError)) {
            iteration += 1;
            testSeedOnValidity();
            balanceRowTargets();
            testSeedOnValidity();
            balanceColumnTargets();
            //           relativeError = computeErrorsRows(seed, rowTargets);
            relativeError = computeErrorsRows();
            log.info("Iteration " + iteration + ". Balancing relative error: " + relativeError);
        }
        return seed;
    }


    public Matrix balance() {

        adjustTargetTotals();
        checkClosureSet();
        double relativeError = 0.0;
        int iteration = 0;
        logger.debug("Beginning matrix balancing using iterative proportional "
                + "fitting.");
        while (!isClosed(iteration, relativeError)) {
            iteration += 1;
            logger.debug("Iteration " + iteration);
            testSeedOnValidity();
            balanceRowTargets();
            testSeedOnValidity();
            balanceColumnTargets();
            //           relativeError = computeErrorsRows(seed, rowTargets);
            relativeError = computeErrorsRows();
            logger.debug("Balancing relative error: " + relativeError);
        }
        return seed;
    }


    /**
     * Report closure conditions and throw an excpetion if none are set.
     */
    private void checkClosureSet() {

        if (!(maxIterationsSet || maxRelativeErrorSet)) {
            String msg = "No closure criteria set.";
            logger.error(msg);
            throw new MatrixException(msg);
        }
        if (maxIterationsSet) {
            logger.debug("Maximum number of iterations set to " + maxIterations);
        } else {
            logger.warn("No maximum number of iterations set.");
        }
        if (maxRelativeErrorSet) {
            logger.debug("Minimum relative error set to " + maxRelativeError);
        } else {
            logger.warn("Minimum relative error not set.");
        }
    }


    /**
     * Check if criteria to stop iterations is reached
     * @param iteration Number of iterations
     * @param relativeError Current relative error
     * @return sets boolean value if process shall be closed or not
     */
    private boolean isClosed(int iteration, double relativeError) {

        boolean closure = false;
        if (maxIterationsSet && iteration == maxIterations) {
            logger.debug("Reached iteration maximum.");
            closure = true;
        }
        if (iteration > 1) {
            if (maxRelativeErrorSet && relativeError < maxRelativeError) {
                logger.debug("Reached minimum relative error.");
                closure = true;
            }
        }
        if (closure) {
            DecimalFormat twoPlaces = new DecimalFormat("0.0E0");
            logger.debug("Closed after " + iteration + " iterations with final relative error: " + twoPlaces.format(relativeError));
//            System.out.format("%d iterations, %10.7f relative error.", iteration, relativeError);
//            System.out.println();
        }
        return closure;
    }


    /**
     * Check to see that the Column and Row Targets sums are within the error.
     */
    private void adjustTargetTotals() {

        double rowTargetSum = rowTargets.getSum();
        double colTargetSum = columnTargets.getSum();
        double diffPercent = relativeDifference(rowTargetSum, colTargetSum);
        if (diffPercent > maxRelativeError) {
            if(userAdjustChoice.equals(ADJUST.COLUMN_TARGETS)){
                scaleColumnTargets();
                logger.debug("Adjusted columns.");
            }
            else if (userAdjustChoice.equals(ADJUST.ROW_TARGETS)) {
                scaleRowTargets();
                logger.debug("Adjusted rows.");
            }
            else if (userAdjustChoice.equals(ADJUST.BOTH_USING_AVERAGE)) {
                scaleTargetsToAvg();
                logger.debug("Adjusted columns and rows using their average.");
            }
            else if (userAdjustChoice.equals(ADJUST.NONE)) {
                String message = "Row targets sum (" + rowTargetSum + ")"
                        + " does not match column target sum (" + colTargetSum
                        + ". Change setting of MatrixBalancerRM.ADJUST.)";
                logger.error(message);
                throw new MatrixException(message);
            }
        }
    }


    /**
     * @param x x value
     * @param y y value
     * @return relative difference
     */
    private double relativeDifference(double x, double y) {

        return abs(x - y) / min(x, y);
    }


    /**
     * Balance to row targets.
     */
    private void balanceRowTargets() {

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
                if (Float.isInfinite(factor)) factor = 0.5f * Float.MAX_VALUE; 
                if (Float.isNaN(factor)) factor = 1; 
            }
            logger.debug("Scaling factor for row " + row + ": " + factor);
            scaleRow(row, factor);
        }
    }


    /*
     * This methods checks if any row or column of the seed matrix sums up to 0 while the target is non-0
     * If so, the entire matrix is increased by 0.00001 to avoid a fatal error
     */
    private void testSeedOnValidity() {

        int[] extRowNumbers = seed.getExternalRowNumbers();
        int[] extColumnNumbers = seed.getExternalColumnNumbers();
        boolean[] adjustRow = new boolean[seed.getRowCount() + 1];
        boolean[] adjustColumn = new boolean[seed.getColumnCount() + 1];

        // analyze if there are rows or columns that have a target != 0 but seed values of 0
        for (int i = 1; i < extRowNumbers.length; i++) {
            int taz = extRowNumbers[i];
            if (seed.getRowSum(taz) == 0 && rowTargets.getValueAt(taz) != 0) {
                adjustRow[i] = true;
                logger.warn("Target for row " + taz + " is non-zero but seed values are 0, seed values were increased to 0.001");
            } else adjustRow[i] = false;
        }
        for (int j = 1; j < extColumnNumbers.length; j++) {
            int taz = extColumnNumbers[j];
            if (seed.getColumnSum(taz) == 0 && columnTargets.getValueAt(taz) != 0) {
                adjustColumn[j] = true;
                logger.warn("Target for column " + taz + " is non-zero but seed values are 0, seed values were increased to 0.001");
            } else adjustColumn[j] = false;
        }

        // adjust seed values where necessary
        for (int i = 1; i < extRowNumbers.length; i++) {
            for (int j = 1; j < extColumnNumbers.length; j++) {
                if (adjustRow[i] || adjustColumn[j]) seed.setValueAt(extRowNumbers[i], extColumnNumbers[j], 0.001f);
            }
        }
    }


    /**
     * Scale a row.
     * @param row Row to be scaled
     * @param factor Scaling factor
     */

    private void scaleRow(int row, float factor) {

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
    private void balanceColumnTargets() {

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
                if (Float.isInfinite(factor)) factor = 0.5f * Float.MAX_VALUE; 
                if (Float.isNaN(factor)) factor = 1; 
            }
            logger.debug("Scaling factor for column " + col + ": " + factor);
            scaleColumn(col, factor);
        }
    }


    /**
     * Scale a column.
     * @param col Column to be scaled
     * @param factor Scaling factor
     */
    private void scaleColumn(int col, float factor) {

        int[] extRowNumbers = seed.getExternalRowNumbers();
        for (int r = 1; r < extRowNumbers.length; ++r) {
            int row = extRowNumbers[r];
            float value = seed.getValueAt(row, col) * factor;
            seed.setValueAt(row, col, value);
        }
    }


    /**
     * Compute balancing error on rows.
     * @return Current relative error
     */
    private double computeErrorsRows() {

        int[] extRowNumbers = seed.getExternalRowNumbers();
        double relativeError = 0.0;
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
            relativeError = max(relative, relativeError);
            logger.debug("Relative error on row " + row + ": " + relative);
        }
        return relativeError;
    }


    /**
     * Scale row targets sum to column target sum.
     */
    private void scaleRowTargets() {

        rowTargets.scale((float) (columnTargets.getSum() / rowTargets.getSum()));
    }


    /**
     * Scale column targets sum to row target sum.
     */
    private void scaleColumnTargets() {

        columnTargets.scale((float) (rowTargets.getSum() / columnTargets
                .getSum()));
    }


    /**
     * Scale targets to the average sum.
     */
    private void scaleTargetsToAvg() {
        float avg = (float) ((rowTargets.getSum() + columnTargets.getSum()) / 2.0);
        columnTargets.scale((float) (avg / columnTargets.getSum()));
        rowTargets.scale((float) (avg / rowTargets.getSum()));
    }
}
