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
package com.pb.common.daf;


/** This class holds the properties for a single queue.
 *
 * @author    Tim Heier
 * @version   1.0, 1/23/2004
 */

public class QueueDef implements java.io.Serializable {

    String name;
    String nodeName;
    int size;


    private QueueDef() {
    }


    public QueueDef(String name, String nodeName, int size) {
        this.name = name;
        this.nodeName = nodeName;
        this.size = size;
    }


    public String toString() {
        return "Queue=[" + 
        name + ", " +
        "node=" + nodeName + ", " +
        "size=" + size + "]";
    }
}