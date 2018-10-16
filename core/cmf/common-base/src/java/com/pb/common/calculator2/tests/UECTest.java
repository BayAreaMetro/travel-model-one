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
package com.pb.common.calculator2.tests;

import com.pb.common.calculator2.UtilityExpressionCalculator;
import com.pb.common.calculator2.IndexValues;
import com.pb.common.util.ObjectUtil;

import java.io.File;
import java.io.Serializable;
import org.apache.log4j.Logger;
import java.util.HashMap;

/**
 * Provides tests for the UtilityExpressionCalculator (UEC) class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/22/2003
 */

public class UECTest implements Serializable {

    protected transient Logger logger = Logger.getLogger("com.pb.common.calculator");


    public static void main(String[] args) {

        //Read the control file name from the command-line
        UECTest test = new UECTest();
        String fileName = args[0];

        test.testBasic(new File(fileName));
    }

    public void testBasic(File file) {

        HashMap env = new HashMap();
        env.put("DATA_DIR", "C:/Users/Tim/Develop/TestData/calculator2");
        env.put("YEAR", "2000");

        DMU dmuObj = new DMU();

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(file, 4, 0, env, dmuObj);
        uec.setDebugOutput(true);

        IndexValues indexValues = new IndexValues();
        indexValues.o = 1;
        indexValues.d = 2;
        indexValues.s = 5;
        indexValues.z = 25;
        indexValues.h = 1000638;
        indexValues.i = 1;
        indexValues.j = 3;

        double[] results = uec.solve(indexValues, dmuObj, null);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }

        //Print size of UEC
        logger.info("SizeOf(UEC) = " + ObjectUtil.sizeOf( uec ) + " bytes");

    }


    public void testAvailableFlag(File file) {

        HashMap env = new HashMap();
        env.put("DATA_DIR", "C:/Users/Tim/Develop/TestData/calculator2");
        env.put("YEAR", "2000");

        DMU dmuObj = new DMU();

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(file , 0, 4, env, dmuObj);

        IndexValues indexValues = new IndexValues();
        indexValues.o = 1;
        indexValues.d = 2;
        indexValues.s = 5;
        indexValues.z = 25;
        indexValues.h = 1000638;

        int[] avail_flag = { 0, 1, 1 };

        double[] results = uec.solve(indexValues, dmuObj, avail_flag);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }
    }

}
