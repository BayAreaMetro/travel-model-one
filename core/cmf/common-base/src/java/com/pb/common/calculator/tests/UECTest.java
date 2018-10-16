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

import com.pb.common.calculator.UtilityExpressionCalculator;
//import com.pb.models.ctramp.jppf.UtilityExpressionCalculator;
import com.pb.common.calculator.IndexValues;
import com.pb.common.util.ResourceUtil;
import com.pb.common.util.ObjectUtil;

import java.io.File;
import java.io.Serializable;
import org.apache.log4j.Logger;
import java.util.HashMap;
import java.util.ResourceBundle;

/**
 * Provides tests for the UtilityExpressionCalculator (UEC) class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/22/2003
 */

public class UECTest implements Serializable {

    protected transient Logger logger = Logger.getLogger("com.pb.common.calculator");
    
    protected String fileName;


    public static void main(String[] args) {

        //Read the control file name from the command-line
        UECTest test = new UECTest(args[0]);
        //test.testDMU();
        test.testEnvironmentVariables();
        //test.testDMUAsVariableTable();
        //test.testAvailableFlag();
        //test.testResourceBundle();
        //test.testUsingTwoUEC();
    }


    public UECTest(String fileName) {
        this.fileName = fileName;
    }


    public void testDMU() {
        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName));

        DMU dmuObj = new DMU();

        int iZone=1;            //origin zone
        int jZone=2;            //destination zone
        int zoneNumber=25;
        int householdId=1000638;

        double[] results = uec.solve(iZone, jZone, zoneNumber, householdId, dmuObj);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }
    }

    //06-Jan-2007 15:14:30:714, INFO, Read /myfiles/testdata/morpc\se_lu2000.csv : 843 ms
    //06-Jan-2007 15:14:30:746, INFO, Read /myfiles/testdata/morpc\se_lu2000-stops.csv : 875 ms
    //06-Jan-2007 15:14:31:636, INFO, Read C:\myfiles\testdata\morpc\morpc_hh_input.csv : 890 ms
    //06-Jan-2007 15:14:32:699, INFO,
    //06-Jan-2007 15:14:32:699, INFO, ---------- solve() results ----------
    //06-Jan-2007 15:14:32:699, INFO, alternative 1, utility =   190.53
    //06-Jan-2007 15:14:32:714, INFO, alternative 2, utility =     3.20
    //06-Jan-2007 15:14:32:714, INFO, alternative 3, utility =    55.00  <-- zone=25 stop=5
    //06-Jan-2007 15:14:33:058, INFO, SizeOf(UEC) = 14207149 bytes

    public void testEnvironmentVariables() {

        HashMap env = new HashMap();
        env.put("MORPC_DATA_DIR", "/Users/Tim/Dev/testdata/morpc");
        env.put("YEAR", "2000");
        env.put("TEST_DATA_DIR", "/Users/Tim/Dev/testdata/morpc");

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 0, 1, env, DMU.class);

        IndexValues index = new IndexValues();
        index.setOriginZone(1);
        index.setDestZone(2);
        index.setStopZone(5);
        index.setZoneIndex(25);
        index.setHHIndex(1000638);

        DMU dmuObj = new DMU();

        uec.setDebugOutput(true);
        
        double[] results = uec.solve(index, dmuObj, null);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }

        //Print size of UEC
        logger.info("SizeOf(UEC) = " + ObjectUtil.sizeOf( uec ) + " bytes");

    }


//    public void testDMUAsVariableTable() {
//
//        HashMap env = new HashMap();
//        env.put("MORPC_DATA_DIR", "/Users/Tim/Dev/testdata/morpc");
//        env.put("YEAR", "2000");
//        env.put("TEST_DATA_DIR", "/Users/Tim/Dev/testdata/morpc");
//
//        DMU dmuObj = new DMU();
//
//        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 0, 1, env, dmuObj);
//
//        IndexValues index = new IndexValues();
//        index.setOriginZone(1);
//        index.setDestZone(2);
//        index.setStopZone(5);
//        index.setZoneIndex(25);
//        index.setHHIndex(1000638);
//
//        uec.setDebugOutput(true);
//
//        double[] results = uec.solve(index, dmuObj, null);
//
//        logger.info("");
//        logger.info("---------- solve() results ----------");
//        for (int i=0; i < results.length; i++) {
//            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
//        }
//
//        //Print size of UEC
//        logger.info("SizeOf(UEC) = " + ObjectUtil.sizeOf( uec ) + " bytes");
//
//    }


    public void testResourceBundle() {

        ResourceBundle rb = ResourceUtil.getResourceBundle("testuec");

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 0, 1, rb, DMU.class);

        DMU dmuObj = new DMU();

        int iZone=1;            //origin zone
        int jZone=2;            //destination zone
        int zoneNumber=25;
        int householdId=1000638;

        double[] results = uec.solve(iZone, jZone, zoneNumber, householdId, dmuObj);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }

    }


    public void testAvailableFlag() {

        HashMap env = new HashMap();
        env.put("MORPC_DATA_DIR", "/myfiles/test/morpc");
        env.put("YEAR", "2000");

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 0, 1, env, DMU.class);

        DMU dmuObj = new DMU();

        int iZone=1;            //origin zone
        int jZone=2;            //destination zone
        int zoneNumber=25;
        int householdId=1000638;

        int[] avail_flag = { 0, 1, 1 };

        double[] results = uec.solve(iZone, jZone, zoneNumber, householdId, dmuObj, avail_flag);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }
    }


    public void testUsingTwoUEC() {

        UtilityExpressionCalculator uec1 = createUEC1();
        logger.info("sizeOf uec1 = " + ObjectUtil.sizeOf(uec1));

        UtilityExpressionCalculator.clearData();

        UtilityExpressionCalculator uec2 = createUEC2();
        logger.info("sizeOf uec2 = " + ObjectUtil.sizeOf(uec2));

        /* Should see these answers:
        *
        * INFO, ---------- solve() results ----------
        * INFO, alternative 1, utility =    190.53
        * INFO, alternative 2, utility =      3.20
        *
		* INFO, sizeOf uec1 = 14156416  (from first output)
		* INFO, sizeOf uec2 = 14157241  (from second output)
        *        
        */
    }


    private UtilityExpressionCalculator createUEC1() {

        HashMap env = new HashMap();
        env.put("MORPC_DATA_DIR", "/myfiles/test/morpc");
        env.put("YEAR", "2000");
        env.put("TEST_DATA_DIR", "/myfiles/test/morpc");

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 0, 1, env, DMU.class);

        IndexValues index = new IndexValues();
        index.setOriginZone(1);
        index.setDestZone(2);
        index.setStopZone(5);
        index.setZoneIndex(25);
        index.setHHIndex(1000638);

        DMU dmuObj = new DMU();

        double[] results = uec.solve(index, dmuObj, null);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }

        return uec;

    }


    private UtilityExpressionCalculator createUEC2() {

        HashMap env = new HashMap();
        env.put("MORPC_DATA_DIR", "/myfiles/test/morpc");
        env.put("YEAR", "2000");
        env.put("TEST_DATA_DIR", "/myfiles/test/morpc");

        UtilityExpressionCalculator uec = new UtilityExpressionCalculator(new File(this.fileName), 2, 3, env, DMU.class);

        IndexValues index = new IndexValues();
        index.setOriginZone(1);
        index.setDestZone(2);
        index.setStopZone(5);
        index.setZoneIndex(25);
        index.setHHIndex(1000638);

        DMU dmuObj = new DMU();

        double[] results = uec.solve(index, dmuObj, null);

        logger.info("");
        logger.info("---------- solve() results ----------");
        for (int i=0; i < results.length; i++) {
            logger.info( "alternative "+ (i+1) + ", utility = " + String.format("%8.2f", results[i]) );
        }

        return uec;

    }
}
