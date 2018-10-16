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

/**
 * Represents a list of constants used in the Expression class.
 *
 * @author    Tim Heier
 * @version   1.0, 3/8/2003
 */
public interface Constants {

    //One argument
    public final int ONE_ARGS = 0;
    public final int LN = 1;
    public final int EXP = 2;
    public final int ABS = 3;
    public final int SIGN = 4;
    public final int INT = 5;
    public final int PUT = 6;
    public final int GET = 7;
    public final int SQRT = 8;

    // Two arguments
    public final int TWO_ARGS = 10;
    public final int ADDITION = 11;
    public final int SUBTRACTION = 12;
    public final int MULTIPLICATION = 13;
    public final int DIVISION = 14;
    public final int MODULUS = 15;
    public final int POWER = 16;
    public final int MAX = 17;
    public final int MIN = 18;
    public final int GREATER = 19;
    public final int LESS = 20;
    public final int EQUAL = 21;
    public final int NOT_EQUAL = 22;
    public final int GREATER_EQUAL = 23;
    public final int LESS_EQUAL = 24;

    //Three arguments
    public final int THREE_ARGS = 30;
    public final int IF = 31;

    // Array special case
    public final int ARRAY_LOOKUP = 64;

    public final int DELIMITER = 1;
    public final int NUMBER = 2;
    public final int VARIABLE = 3;
}
