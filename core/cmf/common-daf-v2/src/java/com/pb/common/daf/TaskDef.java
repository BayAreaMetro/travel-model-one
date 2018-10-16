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


/** This class holds the properties for a single task.
 *
 * @author    Tim Heier
 * @version   1.0, 9/16/2002
 */

public class TaskDef implements java.io.Serializable {

    String name;
    String className;
    String nodeName;
    String queueName;


    private TaskDef() {
    }


    public TaskDef(String name, String className, String nodeName, String queueName) {
        this.name = name;
        this.className = className;
        this.nodeName = nodeName;
        this.queueName = queueName;
    }


    public String toString() {
        return "Task=[" +
        "name=" + name + ", " +
        "class=" + className + ", " +
        "node=" + nodeName + ", " +
        "queue=" + queueName + "]";
    }
}