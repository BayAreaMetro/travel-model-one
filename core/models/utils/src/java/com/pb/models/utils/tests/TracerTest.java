/*
 * Copyright 2006 PB Consult Inc.
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
 * Created on Jun 13, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
package com.pb.models.utils.tests;

import com.pb.common.util.ResourceUtil;
import com.pb.models.utils.Tracer;
import junit.framework.TestCase;
import org.apache.log4j.Logger;

import java.util.MissingResourceException;
import java.util.ResourceBundle;

/**
 * Test cases for the Trace class.
 * 
 * @author Andrew Stryker <stryker@pbworld.com>
 * @version 0.1 Jun 22, 2006
 */
public class TracerTest extends TestCase {
    private transient static Logger logger = Logger.getLogger(TracerTest.class);

    public TracerTest(String arg0) {
        super(arg0);
        Tracer tracer = Tracer.getTracer();

        tracer.clearTraceHouseholds();
        tracer.clearTracePersons();
        tracer.clearTraceZonePairs();
    }

    public static void main(String[] args) {
        junit.textui.TestRunner.run(TracerTest.class);
    }

    /*
     * Test method for 'com.pb.models.pt.Trace.isTraceOn()'
     */
    public void testIsTrace() {
        Tracer tracer = Tracer.getTracer();

        assertEquals(false, tracer.isTraceOn());

        tracer.setTrace(true);
        assertEquals(true, tracer.isTraceOn());

        tracer.setTrace(false);
        assertEquals(false, tracer.isTraceOn());
    }

    /*
     * Test method for 'com.pb.models.pt.Trace.isTracePerson(int, int)'
     */
    public void testIsTracePersonWithNulls() {
        logger.info("Testing isTracePerson() before adding househoulds "
                + "and persons.");
        Tracer tracer = Tracer.getTracer();

        assertEquals(false, tracer.isTracePerson("5_5"));
    }

    public void testTraceHousehold() {
        Tracer tracer = Tracer.getTracer();

        int[] households = { 1, 3, 5, 7 };

        logger.info("Testing the effects of adding households.");
        tracer.setTrace(true);

        for (int household : households) {
            tracer.traceHousehold(household);
        }

        for (int household : households) {
            assertEquals(true, tracer.isTraceHousehold(household));
        }

        assertEquals(false, tracer.isTraceHousehold(2));
    }

    public void testTracePerson() {
        Tracer tracer = Tracer.getTracer();
        String[] persons = { "1_1", "2_1", "3_4", "3000000_9" };

        logger.info("Testing the effects of adding persons.");
        tracer.setTrace(true);

        for (int i = 0; i < persons.length; ++i) {
            tracer.tracePerson(persons[i]);
        }

        for (String person : persons) {
            assertEquals(true, tracer.isTracePerson(person));
        }

        assertEquals(false, tracer.isTracePerson("5_5"));

    }

    public void testIsTraceZonePair() {
        Tracer tracer = Tracer.getTracer();
        int[] itazs = { 1, 3, 5, 7 };
        int[] jtazs = { 2, 4, 6, 8 };

        logger.info("Testing zone pair tracing.");

        assertFalse("Tracer should be empty.", tracer.isTraceZonePair(0, 0));

        for (int i = 0; i < itazs.length; ++i) {
            tracer.traceZonePair(itazs[i], jtazs[i]);
        }

        for (int i = 0; i < itazs.length; ++i) {
            assertTrue("Missing " + itazs[i] + "," + jtazs[i], tracer
                    .isTraceZonePair(itazs[i], jtazs[i]));
            assertFalse("Unexpected pair " + itazs[i] + "," + jtazs[i], tracer
                    .isTraceZonePair(jtazs[i], itazs[i]));
        }
    }

    public void testReadFromPropertiesFile() {
        ResourceBundle rb;
        Tracer tracer = Tracer.getTracer();

        logger.info("Testing reading from a properties file.");

        try {
            rb = ResourceUtil.getResourceBundle("TracerExample1");
        } catch (MissingResourceException e) {
            logger.warn("Could not read properties file.");
            return;
        }

        tracer.readTraceSettings(rb, "trace.rows", "trace.columns");

        assertTrue("Person 1_1", tracer.isTracePerson("1_1"));
        assertTrue("Person 5_1", tracer.isTracePerson("5_1"));
        assertTrue("Person 1_13", tracer.isTracePerson("1_13"));
        assertFalse("Person 2_8", tracer.isTracePerson("2_8"));

        assertFalse("Household 3", tracer.isTraceHousehold(3));

        assertTrue("Zone Pair (1, 3)", tracer.isTraceZonePair(1, 3));
        assertFalse("Zone Pair (1, 4)", tracer.isTraceZonePair(1, 4));
    }

    public void testKeySets() {
        ResourceBundle bundle;
        Tracer tracer = Tracer.getTracer();
        logger.info("Testing reading key-sets from a properties file.");

        try {
            bundle = ResourceUtil.getResourceBundle("TracerExample1");
        } catch (MissingResourceException e) {
            logger.warn("Could not read properties file.");
            return;
        }

        tracer.readKeySet(bundle, "commodity", "trace.commodities");

        assertTrue("Missing trace commodity STCC39", tracer.isTraceKeyValue(
                "commodity", "STCC39"));

        assertFalse("Unexpected trace commodity STCC93", tracer
                .isTraceKeyValue("commodity", "STCC93"));

        tracer.setTrace(tracer.isTraceKeyValue("commodity", "STCC13"));

        assertFalse("Trace not on", tracer.isTraceOn());

    }
}
