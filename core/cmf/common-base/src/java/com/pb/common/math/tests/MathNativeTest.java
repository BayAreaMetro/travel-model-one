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

import com.pb.common.math.MathNative;


/** This class tests the use of jni calls to MSVC++ intrinsic math functions.
 *
 * @author    Jim Hicks
 * @version   1.0, 1/14/2004
 */

public class MathNativeTest {

	public static int LOOP1_SIZE = 100000;
	public static int LOOP2_SIZE = 300;


    public MathNativeTest() {
    }


    public static void main(String[] args) {

        System.out.println("\nstarting tests.\n");

		MathNativeTest test = new MathNativeTest();

        test.testPerformance();

        System.out.println("\nfinished tests.");
    }


    public void testPerformance() {

        long start_time, stop_time;
        double result = 0;

		start_time = System.currentTimeMillis();
		result = 0;
		for (int i = 1; i <= LOOP1_SIZE; i++) {
			for (int j = 1; j <= LOOP2_SIZE; j++)
				result += Math.exp( j + (double)i/LOOP1_SIZE );
		}
		stop_time = System.currentTimeMillis();
		System.out.println("java.lang.Math.exp() time=" + (stop_time - start_time)/1000.0 + " seconds.");
		System.out.println("result=" + result);

		
		start_time = System.currentTimeMillis();
		result = 0;
		for (int i = 1; i <= LOOP1_SIZE; i++) {
			for (int j = 1; j <= LOOP2_SIZE; j++)
				result += MathNative.exp( j + (double)i/LOOP1_SIZE );
		}
		stop_time = System.currentTimeMillis();
		System.out.println("MathNative.expNative() time=" + (stop_time - start_time)/1000.0 + " seconds.");
		System.out.println("result=" + result);

		
		
		
		
		start_time = System.currentTimeMillis();
		result = 0;
		for (int i = 1; i <= LOOP1_SIZE; i++) {
			for (int j = 1; j <= LOOP2_SIZE; j++)
				result += Math.log( (double)i/j );
		}
		stop_time = System.currentTimeMillis();
		System.out.println("java.lang.Math.log() time=" + (stop_time - start_time)/1000.0 + " seconds.");
		System.out.println("result=" + result);
		
		
		start_time = System.currentTimeMillis();
		result = 0;
		for (int i = 1; i <= LOOP1_SIZE; i++) {
			for (int j = 1; j <= LOOP2_SIZE; j++)
				result += MathNative.log( (double)i/j );
		}
		stop_time = System.currentTimeMillis();
		System.out.println("MathNative.logNative() time=" + (stop_time - start_time)/1000.0 + " seconds.");
		System.out.println("result=" + result);

    }

/*
 * 
 * Results
 *

java.lang.Math.exp() time=8.172 seconds.
result=5.2800887736427924E135
MathNative.expNative() time=5.86 seconds.
result=5.2800887736427885E135
java.lang.Math.log() time=8.516 seconds.
result=1.7389918157519475E8
MathNative.logNative() time=4.922 seconds.
result=1.7389918157519475E8

expNative() is 28.3% faster
logNative() is 42.3% faster

 */
    
    
}