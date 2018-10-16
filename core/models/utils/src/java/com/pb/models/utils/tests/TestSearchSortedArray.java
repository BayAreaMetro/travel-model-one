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
 * Created on Apr 12, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
package com.pb.models.utils.tests;

import org.apache.log4j.Logger;


import junit.framework.AssertionFailedError;
import junit.framework.TestCase;
import com.pb.models.utils.SearchSortedArray;

public class TestSearchSortedArray extends TestCase {
    protected static Logger logger = Logger
            .getLogger(TestSearchSortedArray.class);

    /**
     * Set-up a cumulative probability array for testing.
     * 
     */
    public TestSearchSortedArray() {
        double[] utilities = { 1, 2, 3, 2, 1 };
        double cumulative = 0;
        double sum = 0;

        double[] cumProbs = new double[utilities.length];

        for (double u : utilities) {
            sum += u;
        }

        for (int i = 0; i < utilities.length; ++i) {
            cumulative += utilities[i] / sum;
            cumProbs[i] = cumulative;
        }

    }

    /**
     * Test the binarySearch method.
     */
    public void testBinarySearch() {
        float[] array = { 0.1f, 0.3f, 0.5f, 0.7f, 0.99f };
        float[] targets = { 0f, 0.1f, 0.05f, 0.8f, 1f, 0.5f };
        int[] expectation = { 0, 1, 0, 4, 4, 3 };

        for (int i = 0; i < targets.length; ++i) {
            int index = SearchSortedArray.searchForInsertionPoint(array, targets[i]);

            try {
                assertEquals(expectation[i], index);
            } catch (AssertionFailedError e) {
                String msg = "On sub-test " + i + ", expected "
                        + expectation[i] + " and got " + index + ".";
                logger.fatal(msg);
                throw new AssertionFailedError(msg);
            }
        }

    }
}
