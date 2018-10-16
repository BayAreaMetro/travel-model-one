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
package com.pb.common.math.tests;

import com.pb.common.math.MathUtil;


/** This class tests the use of the pow and pow2 methods that use recursion
 *  to calculate the value of a number raised to an integer power.
 *
 * @author    Tim Heier
 * @version   1.0, 9/29/2002
 */

public class MathUtilTest {

    public static int LOOP_SIZE = 10000000;


    public MathUtilTest() {
    }


    public static void main(String[] args) {

        System.out.println("\nstarting tests.");

        MathUtilTest test = new MathUtilTest();

        test.testMathPerformance();
        test.testMathUtil();

        System.out.println("\nfinished tests.");
    }


    public void testMathPerformance() {

        long start_time, stop_time;
        double result = 0;

        start_time = System.currentTimeMillis();
        for (int i = 0; i < LOOP_SIZE; i++) {
            result = Math.pow(2, 10);
        }
        stop_time = System.currentTimeMillis();
        System.out.println("Math.pow() time=" + (stop_time - start_time));
        System.out.println("result=" + result);

        start_time = System.currentTimeMillis();
        for (int i = 0; i < LOOP_SIZE; i++) {
            result = 2 * 2 * 2 * 2 * 2 * 2 * 2 * 2 * 2 * 2;
        }
        stop_time = System.currentTimeMillis();
        System.out.println();
        System.out.println("Simple loop  time=" + (stop_time - start_time));
        System.out.println("result=" + result);
    }


    public void testMathUtil() {

        long start_time, stop_time;
        double result = 0;

        start_time = System.currentTimeMillis();
        for (int i = 0; i < LOOP_SIZE; i++) {
            result = MathUtil.pow(2, 10);
        }
        stop_time = System.currentTimeMillis();
        System.out.println();
        System.out.println("MathUtil.pow() time=" + (stop_time - start_time));
        System.out.println("result=" + result);

        start_time = System.currentTimeMillis();
        for (int i = 0; i < LOOP_SIZE; i++) {
            result = MathUtil.pow2(2, 10);
        }
        stop_time = System.currentTimeMillis();
        System.out.println();
        System.out.println("MathUtil.pow2() time=" + (stop_time - start_time));
        System.out.println("result=" + result);

    }

}