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
package com.pb.common.calculator2.tests;

import com.pb.common.calculator2.VariableTable;
import java.io.Serializable;

public class DMU implements VariableTable, Serializable {

    public double schooldriv = 5;

    public double[] arrayData = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };

    
    //--------- getter methods used in control file as @xxx

    public int getSchoolDrive() {
        return (int)schooldriv; 
    }

    public double getArrayData(int alternativeNumber) {
        return arrayData[alternativeNumber];
    }

    public int getIndexValue(String variableName) {
        if (variableName.equalsIgnoreCase("schooldriv"))
            return 10;
        else
        if (variableName.equalsIgnoreCase("arrayData"))
            return 20;
        else
            return -999;
    }

    public int getAssignmentIndexValue(String variableName) {
        throw new RuntimeException("Method Not Implemented");
    }

    public double getValueForIndex(int variableIndex) {
        if (variableIndex == 10) {
            return schooldriv;
        }
        else
            return -999;
    }

    public double getValueForIndex(int variableIndex, int arrayIndex) {
        if (variableIndex == 20) {
            return arrayData[arrayIndex];
        }
        else
            return -999;
    }

    public void setValue(String variableName, double variableValue) {
        throw new RuntimeException("Method Not Implemented");
    }

    public void setValue(int variableIndex, double variableValue) {
        throw new RuntimeException("Method Not Implemented");
    }
}

