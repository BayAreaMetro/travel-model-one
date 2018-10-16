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
package com.pb.common.calculator.tests;

import com.pb.common.calculator.MatrixCalculator;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixUtil;

import java.util.HashMap;

/**
 * Provides test cases for the MatrixCalculator class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */

public class MatrixCalculatorTest {

    public static int SIZE = 10;

    Matrix mf1;
    Matrix mf2;

    public MatrixCalculatorTest() {
        createMatrixData();
    }

    /**
     * Create a full matrix and put some sample values into it.
     */
    public void createMatrixData() {

        mf1 = new Matrix(SIZE,SIZE);
        mf1.setValueAt(1, 1, (float)1);
        mf1.setValueAt(5, 5, (float)5);
        mf1.setValueAt(10, 10, (float)10);

        System.out.println("\n--------- Full matrix mf1 ---------");
        MatrixUtil.print(mf1, "%7f");
        System.out.println("Sum = " + mf1.getSum());

        mf2 = new Matrix(SIZE,SIZE);
        mf2.setValueAt(1, 1, (float)20);
        mf2.setValueAt(5, 5, (float)50);
        mf2.setValueAt(10, 10, (float)100);

        System.out.println("\n--------- Full matrix mf2 ---------");
        MatrixUtil.print(mf2, "%7f");
        System.out.println("Sum = " + mf2.getSum());
    }


    /**
     * Evaluate a simple matrix expression. Result is returned as a matrix.
     */
    public void doTest1() {

        HashMap matrixMap = new HashMap();
        matrixMap.put("mf1", mf1);
        matrixMap.put("mf2", mf2);

        MatrixCalculator mc = new MatrixCalculator("mf1 + mf1*(mf2/2)", matrixMap);

        Matrix resultMatrix = mc.solve();

        System.out.println("\n--------- Result matrix ---------");
        MatrixUtil.print(resultMatrix, "%7f");
        System.out.println("Sum = " + resultMatrix.getSum());

    }

    /**
     * Evaluate a simple matrix expression. Result is returned as a matrix
     * defined by the user in the expression.
     */
    public void doTest2() {

        HashMap matrixMap = new HashMap();
        matrixMap.put("mf1", mf1);
        matrixMap.put("mf2", mf2);

        Matrix mf3 = new Matrix(SIZE,SIZE);  //Holds the result
        matrixMap.put("mf3", mf3);

        MatrixCalculator mc = new MatrixCalculator("mf3 = mf1 + mf1*(mf2/2)", matrixMap);

        mc.solve();

        System.out.println("\n--------- Result matrix ---------");
        MatrixUtil.print(mf3, "%7f");
        System.out.println("Sum = " + mf3.getSum());

    }

    public static void main(String[] args) {
        MatrixCalculatorTest test = new MatrixCalculatorTest();
        test.doTest1();
        test.doTest2();
    }
}
