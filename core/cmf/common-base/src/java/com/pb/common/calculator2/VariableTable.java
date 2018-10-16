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
package com.pb.common.calculator2;

/**
 * Defines a call back interface for the expression class. Any class can
 * implement this interface and provide a variable table to the expression
 * class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */

public interface VariableTable {

    /**
     * Called to get an index value for a variable
     */
    public int getIndexValue(String variableName);

    /**
     * Called to get an index value for an assignment variable
     * for example a=b+c  where a is the assignment variable
     */
    public int getAssignmentIndexValue(String variableName);

    /**
     * Called to get a value for an indexed variable
     */
    public double getValueForIndex(int variableIndex);

    /**
     * Called to get a value for an indexed variable
     */
    public double getValueForIndex(int variableIndex, int arrayIndex);

    /**
     * Called to set a value for a given variable name
     */
    public void setValue(String variableName, double variableValue);

    /**
     * Called to set a value for a given variable index
     */
    public void setValue(int variableIndex, double variableValue);

}
