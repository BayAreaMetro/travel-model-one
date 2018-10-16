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
package com.pb.common.math;

import com.pb.common.util.ResourceUtil;

/** This class contains math utilties.
 *
 * @author    Tim Heier
 * @version   1.0, 9/29/2002
 */

public class MathUtil {

    private static boolean useNative = false;
    
    //Look for property which determines which math library to use 
    static {
        String value = ResourceUtil.checkSystemProperties("math.useNative", "false");
        if (value.equalsIgnoreCase("true")) {
            useNative = true;
        }
        
        //This line forces the MathNative library to be loaded - serves as a check
        //that the libary can be found.
        if (useNative)
            new MathNative();
    }
    
    /**
     * Computes the value of x raised to the n power.
     *
     * @param  x  any double number
     * @param  n  the int power to raise x to

     * @return x raised to the n power
     * @exception java.lang.IllegalArgumentException
     *   Indicates that x is zero and n is not positive.
     **/
    public static double pow(double x, int n) {
        double product; // The product of x with itself n times
        int count;

        if (x == 0 && n <= 0)
            throw new IllegalArgumentException("x is zero and n=" + n);

        if (n >= 0) {
            product = 1;
            for (count = 1; count <= n; count++)
                product = product * x;
            return product;
        } else
            return 1 / pow(x, -n);
    }


    /**
     * Alternate implementation of the power method.
     **/
    public static double pow2(double x, int n) {
        if (x == 0 && n <= 0)
            throw new IllegalArgumentException("x is zero and n=" + n);
        else if (n == 0)
            return 1;
        else if (n > 0)
            return x * pow2(x, n - 1);
        else // x is nonzero, and n is negative.
            return 1 / pow2(x, -n);
    }

    
    public static double log(double a) {
        if (useNative == true)
            return MathNative.log(a);
        else
            return Math.log(a);
    }
    
    
    public static double exp(double a) {
        if (useNative == true)
            return MathNative.exp(a);
        else
            return Math.exp(a);
    }
    
    public static void expArray(double[] arg, double[] result) {
        if (useNative == true) {
            MathNative.expArray( arg, result );
        }
        else {
            for ( int i=0; i < arg.length; i++ )
                result[i] = Math.exp(arg[i]);
        }
    }
    
}
