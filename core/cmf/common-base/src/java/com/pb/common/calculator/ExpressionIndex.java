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
package com.pb.common.calculator;

import org.apache.log4j.Logger;
import java.io.Serializable;

/**
 * Holds index attributes that apply to an Expression.
 *
 * @author    Tim Heier
 * @version   1.0, 4/25/2003
 */
public class ExpressionIndex implements Serializable {

    protected static Logger logger = Logger.getLogger("com.pb.common.calculator");

    public static String patternStr = ",";

    public String indexString;
    public String[] indexEntries;

    public ExpressionIndex(String indexString) {
        this.indexString = indexString;

        //Parse index values
        this.indexEntries = indexString.split(patternStr);
        logger.debug("");
        logger.debug("indexEntries="+toString());
    }

    public String getIndexEntry(int i) {

        if ( (i < 0) || (i >= indexEntries.length) ) {
            throw new ArrayIndexOutOfBoundsException("ExpressionIndex.getIndexEntry, i="+i+", indexEntries.length="+indexEntries.length);
        }

        return indexEntries[i];
    }

    public String toString() {
        StringBuffer sb = new StringBuffer(64);
        sb.append("[");
        for (int i=0; i < indexEntries.length; i++) {
            sb.append(indexEntries[i]);
            sb.append(" ");
        }
        sb.append("]");
        return sb.toString();
    }

}
