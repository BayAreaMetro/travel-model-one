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
package com.pb.common.matrix;

/**
 * Compute the machine epsilon for the float and double types,
 * the largest positive floating-point value that, when added to 1,
 * results in a value equal to 1 due to roundoff.
 */
public final class Epsilon
{
    private static final float  floatEpsilon;
    private static final double doubleEpsilon;

    static {

        // Loop to compute the float epsilon value.
        float fTemp = 0.5f;
        while (1 + fTemp > 1) fTemp /= 2;
        floatEpsilon = fTemp;

        // Loop to compute the double epsilon value.
        double dTemp = 0.5;
        while (1 + dTemp > 1) dTemp /= 2;
        doubleEpsilon = dTemp;
    };

    /**
     * Return the float epsilon value.
     * @return the value
     */
    public static float floatValue() { return floatEpsilon; }

    /**
     * Return the double epsilon value.
     * @return the value
     */
    public static double doubleValue() { return doubleEpsilon; }
}