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
package com.pb.common.util;

import java.text.DecimalFormat;

/** Helper class that pads the result of a value formatted with the
 * DecimalFormatt class.
 * 
 * @author Tim Heier
 * @version 1.0, 1/10/2004
 * 
 */
public class PaddedDecimalFormat {

    private int defaultWidth = 0;
    private DecimalFormat decimalFormat = new DecimalFormat("0.0");
    private StringBuffer buffer = new StringBuffer(64);
    
    

    private PaddedDecimalFormat() { } ;


    
    /** 
     * A DecimalFormat class is used to format values.
     * 
     * @param width default width for format
     * @param format DecimalFormat class to be used for formatting
     */
    public PaddedDecimalFormat(int width, DecimalFormat format) {
        this.defaultWidth = width;
        this.decimalFormat = format;
    }
    
    
    /**
     * Right justify the value by padding from the left with blanks.
     *  
     * @param width  the desired total with of the value 
     * @param value  the value to be formatted
     * @return formatted and padded value
     */
    public String format(int width, double value) {

        String formattedString = decimalFormat.format(value);
        if (width == 0)
            return formattedString; 
        
        buffer.setLength(0);
        
        int fieldLength = formattedString.length();
        int i=1;

        while(i <= (width - fieldLength) ) {
            buffer.append(" ");
            ++i;
        }
        return (buffer + formattedString);
    }

    
    /**
     * A pass through method which calls the underlying DecimalFormat class
     * directly. Primarily provided for convenience. 
     *  
     *
     * @param value  the value to be formatted
     * @return formatted and padded value
     */
    public String format(double value) {

        return format(defaultWidth, value);
    }
}
