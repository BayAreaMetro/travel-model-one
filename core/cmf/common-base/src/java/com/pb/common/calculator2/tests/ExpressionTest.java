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

import com.pb.common.calculator.Expression;
import com.pb.common.calculator.VariableTable;

/**
 * Provides test cases for the Expression class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */

public class ExpressionTest implements VariableTable {

    //Defalt variable values
    private double utility, distance, time;
    private double answer;


    public static void main(String[] args) {
        ExpressionTest test = new ExpressionTest();
//        test.doTest1();
//        test.doTest2();
        test.doTest3();
//        test.doTest4();
//        test.doTest5();
    }

    public void doTest1() {
        Expression e = new Expression("distance=10+(-10+30)+10", this); //answer = 40
        e.parse();
        answer = e.solve();
        System.out.println("Answer=" + answer + ", distance=" + distance);
    }

    public void doTest2() {
        Expression e = new Expression("time=2*log(exp(2.5))+1", this); //answer = 6
        e.parse();
        answer = e.solve();
        System.out.println("Answer=" + answer + ", time=" + time);

        //Try setting another expression using a previous expression object
        e.setExpression("utility=-0.25*distance + -0.50*time");
        e.parse();
        answer = e.solve();
        System.out.println("Answer=" + answer + ", utility=" + utility); //answer = -13
    }


    public void doTest3() {
        //Expression e = new Expression("min( max(1,2), 3)", this);
        //Expression e = new Expression("time=if( 5 == 6, 1, 2)", this);
        //Expression e = new Expression("if( min(0,1), 1, 2)", this);
        //Expression e = new Expression("int(-8.9) * 2", this);
        //Expression e = new Expression("1<2 * 4+1^2+3", this);        //answer = 1
        //Expression e = new Expression("4+1^2+3", this);              //answer = 8
        //Expression e = new Expression("abs(1-2)", this);
        //Expression e = new Expression("2 == 2", this);
        //Expression e = new Expression("ln(2)*.2", this);
        //Expression e = new Expression("6<2 * 5", this);              //answer = 1
        //Expression e = new Expression("(6<2) * 5", this);            //answer = 0
        //Expression e = new Expression("0.25+.25", this);              //answer = 0
        Expression e = new Expression("5<=5 * 5", this);              //answer = 5
        e.setDebugForExpression(true);
        e.parse();
        answer = e.solve();
        System.out.println("Answer3=" + answer);
        //System.out.println("time=" + time);
    }

    
    public void doTest4() {
        Expression e = new Expression(" 1 + 1 \n + 1 + 1", this); //answer = 4
        e.parse();
        answer = e.solve();
        System.out.println("Answer=" + answer);
    }

    
    public void doTest5() {
        Expression e = new Expression("put(1+1) + get(1)", this); //answer = 5
        e.parse();
        answer = e.solve();
        System.out.println("Answer=" + answer);
    }

    
    //------------------------ Variable Table Methods ------------------------

    /**
     *  Called to get a value for an indexed variable
     */
    public final double getValueForIndex(int i) {
        switch (i) {
            case 0:
                return utility;
            case 1:
                return distance;
            case 2:
                return time;

        }
        return 0.0;
    }

    /**
     *  Called to get an index value for a variable
     */
    public final int getIndexValue(String s) {
        int value = -1;

        if (s.equals("utility"))
            value = 0;
        else
        if (s.equals("distance"))
            value = 1;
        else
        if (s.equals("time"))
            value = 2;

        return value;
    }

    /**
     * Called to get an index value for an assignment variable
     */
    public final int getAssignmentIndexValue(String s) {
        int value = -1;

        if (s.equals("utility"))
            value = 0;
        else
        if (s.equals("distance"))
            value = 1;
        else
        if (s.equals("time"))
            value = 2;

        return value;
    }

    /**
     *  Called to set a value for a given variable name
     */
    public final void setValue(String name, double value) {

        System.out.println("------------ Should not see this message ------------");

        if (name.equals("utility"))
            utility = value;
        else
        if (name.equals("distance"))
            distance = value;
        else
        if (name.equals("time"))
            time = value;
    }


    /**
     *  Called to set a value for a given variable index
     */
    public final void setValue(int variableIndex, double variableValue) {
        if (variableIndex == 0)
            utility = variableValue;
        else
        if (variableIndex == 1)
            distance = variableValue;
        else
        if (variableIndex == 2)
            time = variableValue;
    }
    /**
     * Called to get an index value for a given variable index
     */
    public final double getValueForIndex(int variableIndex, int arrayIndex) {
        throw new UnsupportedOperationException();
    }
    
}

