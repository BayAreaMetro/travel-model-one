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
 * Sample class implementation for MethodInvoker so UtilityExpressionCalculator
 * will compile. A real version of this class will be generated at run time and
 * put in the classpath.
 *
 * @author    Tim Heier
 * @version   1.0, 9/03/2003
 */

public interface MethodInvoker {

    public double invoke(Object obj, int methodNumber, int alternativeNumber);
}
