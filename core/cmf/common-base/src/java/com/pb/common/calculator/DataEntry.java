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

import java.io.Serializable;

public class DataEntry implements Serializable {

    public String type;
    public String name;
    public String format;
    public String fileName;
    public String matrixName;
    public String groupName;
    public boolean indexFlag = false;

    public DataEntry(String type, String name, String format, String fileName,
                     String matrixName, String groupName, boolean indexFlag) {
        this.type = type.trim();
        this.name = name.trim();
        this.format = format.trim();
        this.fileName = fileName.trim();
        this.matrixName = matrixName.trim();
        this.groupName = groupName.trim();
        this.indexFlag = indexFlag;
    }

    public DataEntry(String type, String format, String fileName) {
        this(type, "", format, fileName, "", "", false);
    }

    public String toString() {
        return "type="+type+", name="+name+", format="+format+
                ", fileName="+fileName+", matrixName="+matrixName+
                ", groupName="+groupName+", indexFlag="+indexFlag;
    }
}
