/*
 * Created on 15-Feb-2006
 *
 * Copyright  2005 JE Abraham and others
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

import com.pb.common.math.LogExpCalculator;

import junit.framework.TestCase;

public class LogExpCalculatorTest extends TestCase {

    /*
     * Test method for 'com.pb.common.math.LogExpCalculator.exp(double, double)'
     */
    public void testExp() {
        double x = -1e-57;
        while (x<600) {
            double precision = Math.pow(0.1,Math.random()*10);
            double result = LogExpCalculator.exp(x,precision);
            double realResult = Math.exp(x);
            if (realResult>1) {
                assert(Math.abs(realResult/result-1)<precision);
            } else {
                assert(Math.abs(realResult-result)<precision);
            }
            System.out.println("exp "+x+" ok");
            x *= -1.3;
        }
    }

    /*
     * Test method for 'com.pb.common.math.LogExpCalculator.ln(double, double)'
     */
    public void testLn() {
        double x = 1e25;
        while (x>1e-25) {
            double precision = Math.pow(0.1,Math.random()*10);
            double result = LogExpCalculator.ln(x,precision);
            double realResult = Math.log(x);
            if (realResult >1) {
                assert(Math.abs(realResult/result-1)<precision);
            } else {
                assert(Math.abs(realResult-result)<precision);
            }
            System.out.println("ln "+x+" ok");
            x /=3;
        }
    }
    

    public static void main(String[] args) {
        LogExpCalculatorTest me = new LogExpCalculatorTest();
        me.testExp();
        me.testLn();
        long numTests = 5000000;
        long time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = Math.exp(i*10/numTests);
        }
        System.out.println("Math.exp "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = LogExpCalculator.exp(i*10/numTests, 1e-3);
        }
        System.out.println("LogExpCalculator.exp "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = Math.log((i*1000+1)/numTests);
        }
        System.out.println("Math.log "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = LogExpCalculator.ln((i*1000+1)/numTests, 1e-3);
        }
        System.out.println("LogExpCalculator.ln "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        
        // same thing with less range
        System.out.println("now with constant arguments close to 1.0");
        for (long i=0;i<numTests;i++) {
            double x = Math.exp(1.2);
        }
        System.out.println("Math.exp "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = LogExpCalculator.exp(1.2, 1e-7);
        }
        System.out.println("LogExpCalculator.exp "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = Math.log(1.2);
        }
        System.out.println("Math.log "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
        time = System.currentTimeMillis();
        for (long i=0;i<numTests;i++) {
            double x = LogExpCalculator.ln(1.2, 1e-7);
        }
        System.out.println("LogExpCalculator.ln "+numTests+" times takes "+(System.currentTimeMillis()-time)+" milliseconds");
    }
    

}
