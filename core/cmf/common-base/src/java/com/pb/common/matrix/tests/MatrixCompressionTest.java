/*
 * Copyright 2006 PB Consult Inc.
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
package com.pb.common.matrix.tests;

import com.pb.common.matrix.AlphaToBeta;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixCompression;
import junit.framework.TestCase;
import junit.framework.TestSuite;
import junit.textui.TestRunner;
import org.junit.Before;

/**
 * This class is used for ...
 * Author: Christi Willison
 * Date: Aug 2, 2007
 * Email: willison@pbworld.com
 * Created by IntelliJ IDEA.
 */
public class MatrixCompressionTest extends TestCase {

    MatrixCompression squeezer;
    Matrix connected;
    Matrix unconnectedWithZeroes;
    Matrix unconnectedWithInfinities;
    Matrix partiallyUnconnectedZeroes;
    Matrix partiallyUnconnectedInfinities;

    @Before
    public void setUp(){

        int[] aZones = {1,2,3,4,5,6,10,11,12};
        int[] bZones = {1,1,1,4,4,4,10,10,11};
        AlphaToBeta a2b = new AlphaToBeta(aZones, bZones);
        squeezer = new MatrixCompression(a2b);

        int[] externalNumbers = {0,1,2,3,4,5,6,10,11,12};

        //SEE METHODS BELOW FOR EXAMPLE OF THE MATRIX.
        connected = createConnectedMatrix(externalNumbers);
//        System.out.println("All Zones are connected");
//        printMatrix(connected);
//        System.out.println();

        unconnectedWithZeroes = createUnconnectedZeroesMatrix(externalNumbers, 0.0f);
//        System.out.println("No alphas within the beta will be connected to other alphas (row, col = 0)");
//        printMatrix(unconnectedWithZeroes);
//        System.out.println();

        unconnectedWithInfinities = createUnconnectedZeroesMatrix(externalNumbers, Float.NEGATIVE_INFINITY);
//        System.out.println("No alphas within the beta will be connected to other alphas (row, col = neg infinity)");
//        printMatrix(unconnectedWithInfinities);
//        System.out.println();

        partiallyUnconnectedZeroes = createPartiallyConnectedMatrix(externalNumbers, 0.0f);
//        System.out.println("One alpha in the beta zone is unconnected but others are - 0");
//        printMatrix(partiallyUnconnectedZeroes);
//        System.out.println();

        partiallyUnconnectedInfinities = createPartiallyConnectedMatrix(externalNumbers, Float.NEGATIVE_INFINITY);
//        System.out.println("One alpha in the beta zone is unconnected but others are - neg infinity");
//        printMatrix(partiallyUnconnectedInfinities);
//        System.out.println();


    }

    //all zones have a valid value
    public void testSqueezeMeanConnected(){
        Matrix mean = squeezer.getCompressedMatrix(connected, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals(7.5f, mean.getValueAt(10,4));
        printMatrix(mean);
        System.out.println();

    }

    // This matrix has a zone that is completely disconnected from all
    // alphas and all betas and the missing value is 0 but the person calling the method
    // has not explicitly set the missing value to 0 (default is neg inf) and therefore
    // the 0 is treated as a regular number.
    public void testSqueezeMeanUnconnectedZeroes(){
        Matrix mean = squeezer.getCompressedMatrix(unconnectedWithZeroes, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals(0.0f, mean.getValueAt(11,10));
        printMatrix(mean);
        System.out.println();
    }

    public void testSqueezeMeanUnconnectedInfinities(){
        Matrix mean = squeezer.getCompressedMatrix(unconnectedWithInfinities, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals(Float.NEGATIVE_INFINITY, mean.getValueAt(11,10));
        printMatrix(mean);
        System.out.println();
    }

    //This matrix has a zone that is completely disconnected from all
    // alphas and all betas.  Here the user IS explicitly set the missing value to 0 (default is neg inf)
    // prior to calling the method and therefore the 0 is treated as a missing value.
    public void testSqueezeMeanSetZeroAsDisconnectedFull(){
            squeezer.setMissingValue(0.0f);
            Matrix mean = squeezer.getCompressedMatrix(unconnectedWithZeroes, MatrixCompression.MatrixCompressionType.MEAN);
            assertEquals(0.0f, mean.getValueAt(11,10));
            printMatrix(mean);
            System.out.println();
        }




    //The following 3 tests use a matrix where one of the alpha zones is disconnected from all
    //other alphas but there are other alphas within the beta that have valid values and therefore
    //the beta matrix will not have missing values.
    //In this first test however, the person forgot to explicitly set the missing value to 0 and so it is
    //going to treat the 0 as a valid number.
    public void testSqueezeMeanPartiallyUnconnectedZeroes(){
        Matrix mean = squeezer.getCompressedMatrix(partiallyUnconnectedZeroes, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals((30.0f/9.0f), mean.getValueAt(4,1));
        printMatrix(mean);
        System.out.println();
    }



    //Here the default missing value is used.
    public void testSqueezeMeanPartiallyUnconnectedInfinities(){
        Matrix mean = squeezer.getCompressedMatrix(partiallyUnconnectedInfinities, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals((30.0f/6.0f), mean.getValueAt(4,1));
        printMatrix(mean);
        System.out.println();
    }

    //Here the user explicitly sets the missing value to 0 and therefore it is not included in the average
    public void testSqueezeMeanSetZeroAsDisconnectedPartial(){
        squeezer.setMissingValue(0.0f);
        Matrix mean = squeezer.getCompressedMatrix(partiallyUnconnectedZeroes, MatrixCompression.MatrixCompressionType.MEAN);
        assertEquals((30.0f/6.0f), mean.getValueAt(4,1));
        printMatrix(mean);
        System.out.println();
    }


        //The matrix looks like this:
//         		   1		   4		   10	   11  /beta zones
//	               1   2   3   4   5   6   10  11  12  /alpha zones
//
//     1   1       1   1   1   1   1   1   1   1   1
//   	   2	   2   2   2   2   2   2   2   2   2
//  	   3	   3   3   3   3   3   3   3   3   3
//     4   4	   4   4   4   4   4   4   4   4   4
//  	   5	   5   5   5   5   5   5   5   5   5     values = all zones connected.
//  	   6	   6   6   6   6   6   6   6   6   6
//    10  10	   7   7   7   7   7   7   7   7   7
//  	  11	   8   8   8   8   8   8   8   8   8
//    11  12	   9   9   9   9   9   9   9   9   9
    private Matrix createConnectedMatrix(int[] externals){
        float[][] test = new float[9][9];
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                test[i][j] = i+1;
            }
        }

        Matrix testMatrix = new Matrix(test);
        testMatrix.setExternalNumbers(externals);
        return testMatrix;
    }

    //The matrix looks like this:
//         		   1		       4		     10		   11  /beta zones
//	               1     2    3    4    5    6   10   11   12  /alpha zones
//
//     1   1       1     1    1    1    1    1    1    1   DV
//   	   2	   2     2    2    2    2    2    2    2   DV
//  	   3	   3     3    3    3    3    3    3    3   DV
//     4   4	   4     4    4    4    4    4    4    4   DV
//  	   5	   5     5    5    5    5    5    5    5   DV     DV = disconnected value (0 or -neg inf).
//  	   6	   6     6    6    6    6    6    6    6   DV
//    10  10	   7     7    7    7    7    7    7    7   DV
//  	  11	   8     8    8    8    8    8    8    8   DV
//    11  12	   DV    DV   DV   DV   DV   DV   DV   DV  DV
    private Matrix createUnconnectedZeroesMatrix(int[] externals, float disconnectedValue){
        float[][] test = new float[9][9];
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                if(i==8 || j==8) test[i][j] = disconnectedValue;
                else test[i][j] = i+1;
            }
        }

        Matrix testMatrix = new Matrix(test);
        testMatrix.setExternalNumbers(externals);
        return testMatrix;
    }


    //The matrix looks like this:
//         		   1		       4		     10		   11  /beta zones
//	               1     2    3    4    5    6   10   11   12  /alpha zones
//
//     1   1       1     1   DV    1    1    1    1    1    1
//   	   2	   2     2   DV    2    2    2    2    2    2
//  	   3	   DV   DV   DV   DV   DV   DV   DV   DV   DV
//     4   4	   4     4   DV    4    4    4    4    4    4
//  	   5	   5     5   DV    5    5    5    5    5    5     DV = disconnected value (0 or -neg inf).
//  	   6	   6     6   DV    6    6    6    6    6    6
//    10  10	   7     7   DV    7    7    7    7    7    7
//  	  11	   8     8   DV    8    8    8    8    8    8
//    11  12	   9     9   DV    9    9    9    9    9    9

    public Matrix createPartiallyConnectedMatrix(int[] externals, float discValue){
        float[][] test = new float[9][9];
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                if(i==2 || j==2) test[i][j] = discValue;
                else test[i][j] = i+1;
            }
        }

        Matrix testMatrix = new Matrix(test);
        testMatrix.setExternalNumbers(externals);
        return testMatrix;
    }

    private void printMatrix(Matrix mtx){
        float[][] values = mtx.getValues();
        for (float[] value : values) {
            mtx.printArray(value);
        }
    }

    public static void main(String[] args) {
        new TestRunner().doRun(new TestSuite(MatrixCompressionTest.class));
    }
}
