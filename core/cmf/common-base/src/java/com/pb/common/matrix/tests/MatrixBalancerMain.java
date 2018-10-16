package com.pb.common.matrix.tests;

import com.pb.common.matrix.ColumnVector;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixBalancerRM;
import com.pb.common.matrix.RowVector;

import java.util.Random;

/** To Balance a matrix create a new "MatrixBalancerRM" and call ".balance();"
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
 *  There are three constructors to balance a matrix:
 *  Case 1: Set relative Error
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, adjust);
 *  Case 2: Set maximum number of iterations
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxIterations, adjust);
 *  Case 3: Set relative Error and maximum of iterations
 *    MatrixBalancerRM matrix_object = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
 *
 *  To balance the matrix call:
 *    Matrix new_matrix_name = matrix_object.balance();
 *  Date: Apr 30, 2007
 *  User: Moeckel
 */

public class MatrixBalancerMain {

    /**
     * Tests MatrixBalancer in different ways
     * The seed is set by random values between 0 and 1
     * @param args Arguments
     */
    public static void main(String[] args){

        MatrixBalancerMain main = new MatrixBalancerMain();
        System.out.println("Test 1");
        main.test1();
        System.out.println("Test 2");
        main.test2();
        System.out.println("Test 3");
        main.test3();
        System.out.println("Test 4");
        main.test4();
        System.out.println("Test 5");
        main.test5();
        System.out.println("Test 6");
        main.test6();
    }


    /**
     * Tests a matrix with 3 columns and 4 rows
     * - no traget adjustments
     * - maxIterations is set
     * - maxRelativeError is set
     */
    public void test1(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed matrix", 4, 3);
        ColumnVector rowTargets = new ColumnVector(new float []{2f,1f,9f,4490f});
        RowVector colTargets = new RowVector(new float []{4490f,8f,4f});
        for (int i=1; i<=seedmat.getRowCount(); i++){
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
            }
        }
        int maxIterations = 1000;
        double maxRelativeError = 0.000001;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.NONE;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Tests a matrix with 3 columns and 4 rows
     * - adjust row targets
     * - maxIterations is set
     * - maxRelativeError is set
     */
    public void test2(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed matrix", 4, 3);
        ColumnVector rowTargets = new ColumnVector(new float []{2f,1f,9f,3490f});
        RowVector colTargets = new RowVector(new float []{4490f,8f,4f});
        for (int i=1; i<=seedmat.getRowCount(); i++){
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
            }
        }
        int maxIterations = 1000;
        double maxRelativeError = 0.000001;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.ROW_TARGETS;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Tests a matrix with 3 columns and 4 rows
     * - adjust column targets
     * - maxIterations is set
     * - maxRelativeError is set
     */
    public void test3(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed matrix", 4, 3);
        ColumnVector rowTargets = new ColumnVector(new float []{2f,1f,9f,3490f});
        RowVector colTargets = new RowVector(new float []{4490f,8f,4f});
        for (int i=1; i<=seedmat.getRowCount(); i++){
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
            }
        }
        int maxIterations = 1000;
        double maxRelativeError = 0.000001;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.COLUMN_TARGETS;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Tests a matrix with 3 columns and 4 rows
     * - adjust column and row targets using their average
     * - maxIterations is set
     * - maxRelativeError is set
     */
    public void test4(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed matrix", 4, 3);
        ColumnVector rowTargets = new ColumnVector(new float []{2f,1f,9f,3490f});
        RowVector colTargets = new RowVector(new float []{4490f,8f,4f});
        for (int i=1; i<=seedmat.getRowCount(); i++){
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
            }
        }
        int maxIterations = 1000;
        double maxRelativeError = 0.000001;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.BOTH_USING_AVERAGE;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Tests a matrix with 3 columns and 4 rows
     * - adjust column and row targets using their average
     * - maxIterations is set
     * - maxRelativeError is not set
     */
    public void test5(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed matrix", 4, 3);
        ColumnVector rowTargets = new ColumnVector(new float []{2f,1f,9f,3490f});
        RowVector colTargets = new RowVector(new float []{4490f,8f,4f});
        for (int i=1; i<=seedmat.getRowCount(); i++){
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
            }
        }
        int maxIterations = 1000;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.BOTH_USING_AVERAGE;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Tests a matrix with 5000 columns and 6000 rows
     * - adjust column and row targets using their average
     * - maxIterations is set
     * - maxRelativeError is set
     */
    public void test6(){

        Random randomGenerator = new Random(System.currentTimeMillis());
        Matrix seedmat = new Matrix("seed", "seed  matrix", 4150, 4050);
        ColumnVector rowTargets = new ColumnVector(seedmat.getRowCount());
        RowVector colTargets = new RowVector(seedmat.getColumnCount());
        for (int i=1; i<=seedmat.getRowCount(); i++){
            rowTargets.setValueAt(i, 10000000*randomGenerator.nextFloat());
            for (int j=1; j<=seedmat.getColumnCount(); j++){
                colTargets.setValueAt(j, 10000000*randomGenerator.nextFloat());
                seedmat.setValueAt(i, j, randomGenerator.nextFloat());
                if (randomGenerator.nextFloat() <= 0.5) seedmat.setValueAt(i, j, 0);
            }
        }
        double maxRelativeError = 0.00000000001;
        int maxIterations = 1;
        MatrixBalancerRM.ADJUST adjust = MatrixBalancerRM.ADJUST.BOTH_USING_AVERAGE;
        MatrixBalancerRM matBalancer = new MatrixBalancerRM(seedmat, rowTargets, colTargets, maxRelativeError, maxIterations, adjust);
        Matrix balancedMatrix = matBalancer.balance();
        printMatrix(balancedMatrix, rowTargets, colTargets);
    }


    /**
     * Print the balanced matrix with target values and actual sums
     * @param resultMatrix Balanced matrix
     * @param rowTargets Row targets
     * @param colTargets Column Targets
     */
    public void printMatrix(Matrix resultMatrix, ColumnVector rowTargets, RowVector colTargets) {

        float value;
        for(int r=1; r<=resultMatrix.getRowCount(); r++){
            float sum = 0;
            if (r <= 5) System.out.print("     ");
            for (int c=1; c<=resultMatrix.getColumnCount(); c++){
                value = resultMatrix.getValueAt(r, c);
                sum+=value;
                if (c <= 5 && r <= 5) System.out.format("%8.2f, ", value);
                else if (c == 6 && r <= 5) System.out.print("... "); 
            }
            if (r <= 5){
                System.out.format("Sum:%10.2f  ", sum);
                System.out.format("Target:%10.2f", rowTargets.getValueAt(r));
                System.out.println();
            }
            else if (r == 6) System.out.println("     ...");

        }

        System.out.print("Sum: ");
        for (int c=1; c<=resultMatrix.getColumnCount(); c++){
            float sum = 0;
            for (int r=1; r<=resultMatrix.getRowCount(); r++){
                sum = sum + resultMatrix.getValueAt(r, c);
            }
            if (c <= 5) System.out.format("%8.2f, ", sum);
            if (c == 6) System.out.print("... ");
        }
        System.out.println();
        System.out.print("Trg: ");
        for (int c=1; c<=resultMatrix.getColumnCount(); c++){
            if (c <= 5) System.out.format("%8.2f, ", colTargets.getValueAt(c));
            if (c == 6) System.out.print("...");
        }
        System.out.println();
        System.out.println();
    }
}



