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
package com.pb.common.math;

import java.util.ArrayList;

public class LogExpCalculator {

    static final double ln2 = Math.log(2);
    
    static public double exp(double argument, double precision) {
        if (argument >600) return Double.POSITIVE_INFINITY;
        if (argument <-600) return Double.NEGATIVE_INFINITY;
        if (argument >-5) {
            if (precision >0.5) precision =0.5;
            double result = 1;
            double term = 1;
            int count = 1;
            while (Math.abs(term)>= precision){
                term*=argument/count;
                result +=term;
                count++;
            };
            return result;
        } else {
            return 1/exp(-argument,1/precision);
        }
    }
    
    static public double ln(double argument, double precision) {
        if (argument <0) throw new ArithmeticException("ln of negative number "+argument);
        if (argument == 0) return Double.NEGATIVE_INFINITY;
        double base=1;
        int baseLookup =0;
        double between0and2 = argument;
        if (argument >1) {
            while (between0and2 >1.414) {
                between0and2/=2;
                baseLookup ++;
                base *=2;
            }
        } else {
            while (between0and2 <0.7) {
                between0and2*=2;
                baseLookup--;
                base *=2;
            }
        }
        double result = between0and2-1;
        double term = result;
        int count = 2;
        while (Math.abs(term/count)>precision) {
            term*=-(between0and2-1);
            result += term/count;
        }
        return baseLookup * ln2 +result; 
    }

}
