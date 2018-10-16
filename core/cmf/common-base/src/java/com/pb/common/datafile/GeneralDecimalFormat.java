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
package com.pb.common.datafile;

import java.text.*;

/**
 * This class provides a way to use scientific notation when necessary.
 */
public class GeneralDecimalFormat extends DecimalFormat {
    final DecimalFormat nonScientific;
    double useScientificAbove;
    double useScientificBelow;

    public GeneralDecimalFormat(String scientificString, double useScientificAbove, double useScientificBelow) {
        super(scientificString);
        this.useScientificAbove = useScientificAbove;
        this.useScientificBelow = useScientificBelow;
        String nonScientificString = scientificString.replaceAll("E0+","");
        nonScientific = new DecimalFormat(nonScientificString);
    }
    
    public StringBuffer format(double val, StringBuffer buffer, FieldPosition f) {
        if (val ==0.0 || (Math.abs(val) <= useScientificAbove && Math.abs(val) > useScientificBelow)) {
            return nonScientific.format(val, buffer, f);
        } else {
            return super.format(val,buffer,f);
        }
    }
    
    public StringBuffer format(long val, StringBuffer buffer, FieldPosition f) {
        if (val ==0.0 || (Math.abs(val) <= useScientificAbove && Math.abs(val) > useScientificBelow)) {
            return nonScientific.format(val, buffer, f);
        } else {
            return super.format(val,buffer,f);
        }
    }
        
}