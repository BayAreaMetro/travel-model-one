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

import java.util.Iterator;

/**
 * An iterator for the external numbers in a matrix class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/16/2004
 * 
 */
public class ExternalNumberIterator implements Iterator {

    private int[] externalNumbers;
    private int cursor = 1; //external numbers are assumed to start in array element 1
    private int length;
    
    
    private ExternalNumberIterator() {
    }
    
    
    public ExternalNumberIterator(int[] externalNumbers) {
        this.externalNumbers = externalNumbers;
        this.length = externalNumbers.length;
    }

    
    public boolean hasNext() {
        if (cursor == length) {
            return false;
        }
        return true;
    }

    
    public Object next() {
        int number = externalNumbers[cursor];
        cursor++;
        return (new Integer(number));
    }

    public void remove() {
        throw new UnsupportedOperationException("This iterator does not support the remove method");
    }
}
