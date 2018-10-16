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

import com.pb.common.math.MathUtil;

import java.util.HashMap;
import java.util.Iterator;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import java.io.Serializable;

/**
 * Represents an expression that can be parsed and evaluated.
 *
 * @author    Tim Heier
 * @version   1.0, 2/13/2003
 */
public class Expression implements Constants, Serializable {

    protected transient Logger logger = Logger.getLogger("com.pb.common.calculator");
    protected transient Logger debugLogger = Logger.getLogger("debug");
    protected transient Logger traceLogger = Logger.getLogger("trace");

    private boolean logDebug = false;
    private boolean logTrace = false;

    private String prog;
    private String token;
    private int tok_type;
    private int count = 0;
    private double answer;
    private String result_token = "";
    private int result_index = -1;
    private VariableTable vtable;
    
    private int[] sign;     //token type
    private double[] exp;   //execution stack
    private char[] temp;    //temp stack for unwinding parenthesis
    private int signindex, tempindex, expindex, tindex;

    //Keeps a map of variable index to name (where index is the lookup)
    private HashMap variableMap = new HashMap(100);

    //variables for internal stack
    private int sp = 1;
    private double[] valueStack = new double[20];  //arbitrary size of 20

    private boolean error = false;
    private static final int SYNTAX_ERROR = 0;
    private static final int PARANTHESIS = 1;

    String[] errors = {"Syntax error",
                       "Unbalanced Parenthesis",
                       "No Expression Present"};

    public Expression(String prog, VariableTable va) {
        setExpression(prog, va);
        //This is a debugging optimization
        if (debugLogger.isDebugEnabled()) {
            logDebug = true;
        }
    }
    
    public void setDebugForExpression(boolean value) {
        if ( value ) {
            logDebug = true;
            debugLogger.setLevel( org.apache.log4j.Level.DEBUG );
            logger.setLevel( org.apache.log4j.Level.DEBUG );
        }
        else {
            logDebug = false;
            debugLogger.setLevel( org.apache.log4j.Level.OFF );
            logger.setLevel( org.apache.log4j.Level.INFO );
        }
    }

    public void setTraceLogging( boolean value ) {
        logTrace = value;
    }

    public void setExpression(String prog, VariableTable va) {
        this.vtable = va;
        setExpression(prog);
    }

    public void setExpression(String prog) {
        this.prog = prog;
        sign = new int[1000];
        temp = new char[1000];
        exp = new double[1000];
        valueStack = new double[20];
        sp = 1;
    }

    public String getExpression() {
        return prog;
    }

    public HashMap getVariableMap() {
        return variableMap;
    }

    /**
     * Parse expression and create compiled representation
     */
    public final void parse() {

        String ttemp_token;

        signindex = 0;
        expindex = 0;
        tempindex = 0;

        boolean assignment = false;

        if (logger.isDebugEnabled()) {
            logger.debug("parsing expression: "+ prog);
        }

        if (prog.equals("")) {
            serror(2);
            error = true;
            return;
        }

        //Step through expression and count parenthesis
        int i = 0;
		int temp_count = 0;
        while (temp_count < prog.length()) {
            if (prog.charAt(temp_count) == '(')
                i++;
            else
            if (prog.charAt(temp_count) == ')')
                i--;

			temp_count++;
		}

		//Parenthesis are not balanced
		if (i != 0) {
			logger.warn("expression="+prog);
			serror(PARANTHESIS);
			error = true;
			return;
		}


        //Is there an assignment operation in the this expression?
        //Exclude ==, !=, <=, >=
		temp_count = 0;
		while (temp_count < prog.length()) {
            if (prog.charAt(temp_count) == '=') {
                if ( (prog.charAt(temp_count-1) == '=') || (prog.charAt(temp_count+1) == '=') ||
                     (prog.charAt(temp_count-1) == '!') ||
                     (prog.charAt(temp_count-1) == '<') || (prog.charAt(temp_count-1) == '>') ) {
                    assignment = false;
                }
                else {
					assignment = true;
					break;
                }
            }

            temp_count++;
        }

        if (logger.isDebugEnabled()) {
            logger.debug("assignment: "+ assignment);
        }

        get_token();

        //Handles case where expression is being assigned to a variable
        //eg. x=1+3
        if (assignment) {
            if (tok_type == VARIABLE) {
                //save old token
                ttemp_token = token.substring(0, token.length());

                get_token();

                //not assignment - restore old token
                if (!token.equals("=")) {
                    exp[expindex++] = vtable.getIndexValue(ttemp_token);
                    sign[signindex++] = VARIABLE;
                }
                //store result token and find index
                else {
                    result_token = ttemp_token;
                    result_index = vtable.getAssignmentIndexValue(result_token);

                    if(result_index < 0)
                        error = true;
                    //get next token
                    get_token();
                }
            }
        }

        while (!token.equals("_end_")) {

            switch (tok_type) {
                case NUMBER:
                    exp[expindex++] = Double.valueOf(token).doubleValue();
                    sign[signindex++] = NUMBER;
                    break;
                case VARIABLE:
                    char c = isReservedFunction(token);  //check for function like LN, EXP, ABS, etc.
                    if (c > 0) {
                        temp[tempindex++] = c;
                    }
                    else {
                        exp[expindex++] = find_varIndex(token);  //must be user supplied variable
                        sign[signindex++] = VARIABLE;
                    }
                    break;
                case DELIMITER:
                    if (token.charAt(0) == '(') {
                        temp[tempindex++] = token.charAt(0);
                    }
                    else
                    if (token.charAt(0) == ',') {

                        while ( (temp[--tempindex] != '(') && (temp[tempindex] != ',') ) {
                            exp[expindex++] = find_op(temp[tempindex]);
                            sign[signindex++] = DELIMITER;
                        }
                        //Still need to read more arguements for this function - store separator
                        temp[tempindex++] = token.charAt(0);
                    }
                    else
                    if (token.charAt(0) == ')') {

                        while ( (temp[--tempindex] != '(') && (temp[tempindex] != ',') ) {
                            exp[expindex++] = find_op(temp[tempindex]);
                            sign[signindex++] = DELIMITER;
                        }

                        if ( ((tempindex-1) >= 0) && isReservedFunction(temp[tempindex-1])) {
                            --tempindex;
                            exp[expindex++] = find_op(temp[tempindex]);
                            sign[signindex++] = DELIMITER;

                        }
                    }
                    else
                    if (tempindex == 0 || temp[tempindex - 1] == '(' ||
                            find_pre(temp[tempindex - 1]) < find_pre(token.charAt(0)))
                        temp[tempindex++] = operatorMapping(token);
                    else
                    if (find_pre(temp[tempindex - 1]) >= find_pre(token.charAt(0))) {
                        exp[expindex++] = find_op(temp[tempindex - 1]);
                        sign[signindex++] = DELIMITER;
                        temp[tempindex - 1] = operatorMapping(token);
                    }
            }
            get_token();
        }

        while ((--tempindex) >= 0) {
            exp[expindex++] = find_op(temp[tempindex]);
            sign[signindex++] = DELIMITER;
        }
        expindex--;
        count = 0;

        logVariableTable();
        logStackContents();
    }

    //Maps two character operators to one character
    protected char operatorMapping(String token) {

        if (token.startsWith(">="))
            return '}';
        else
        if (token.startsWith("<="))
            return '{';
        else
            return token.charAt(0);
    }

    protected char isReservedFunction(String functionString) {
        char c = 0;

        if (functionString.toUpperCase().equals("LN"))
            c = 'l';
        else
        if (functionString.toUpperCase().equals("EXP"))
            c = 'e';
        else
        if (functionString.toUpperCase().equals("ABS"))
            c = 'a';
        else
        if (functionString.toUpperCase().equals("SIGN"))
            c = 's';
        else
        if (functionString.toUpperCase().equals("INT"))
            c = 't';
        else
        if (functionString.toUpperCase().equals("MAX"))
            c = 'm';
        else
        if (functionString.toUpperCase().equals("MIN"))
            c = 'n';
        else
        if (functionString.toUpperCase().equals("IF"))
            c = 'i';
        else
        if (functionString.toUpperCase().equals("PUT"))
            c = 'p';
        else
        if (functionString.toUpperCase().equals("GET"))
            c = 'g';
        else
        if (functionString.toUpperCase().equals("SQRT"))
            c = 'q';

        return c;
    }

    protected boolean isReservedFunction(char functionChar) {
        boolean isFunction = false;

        if (functionChar == 'l')
            isFunction = true;
        else if (functionChar == 'e')
            isFunction = true;
        else if (functionChar == 'a')
            isFunction = true;
        else if (functionChar == 's')
            isFunction = true;
        else if (functionChar == 'i')
            isFunction = true;
        else if (functionChar == 'm')
            isFunction = true;
        else if (functionChar == 'n')
            isFunction = true;
        else if (functionChar == 't')
            isFunction = true;
        else if (functionChar == 'p')
            isFunction = true;
        else if (functionChar == 'g')
            isFunction = true;
        else if (functionChar == 'q')
            isFunction = true;

        return isFunction;
    }

    protected int find_op(char c) {

        switch (c) {
            case '+':
                return ADDITION;
            case '-':
                return SUBTRACTION;
            case '*':
                return MULTIPLICATION;
            case '/':
                return DIVISION;
            case '%':
                return MODULUS;
            case '^':
                return POWER;
            case '>':
                return GREATER;
            case '<':
                return LESS;
            case '}':
                return GREATER_EQUAL;
            case '{':
                return LESS_EQUAL;
            case 'm':
                return MAX;
            case '=':
                return EQUAL;
            case '!':
                return NOT_EQUAL;
            case 'n':
                return MIN;
            case 'l':
                return LN;
            case 'e':
                return EXP;
            case 'a':
                return ABS;
            case 's':
                return SIGN;
            case 't':
                return INT;
            case 'i':
                return IF;
            case 'p':
                return PUT;
            case 'g':
                return GET;
            case 'q':
                return SQRT;

        }

        return -999;
    }

    public double solve() {

        if ( logDebug ) {
            debugLogger.debug("solving: "+ prog);
        }

        if ( logTrace ) {
            traceLogger.debug("solving: "+ prog);
        }

        if (!error) {
            tindex = expindex;
            answer = solve1();
            if (result_index >= 0) {
                vtable.setValue(result_index, answer);
            }
        }
        else {
            throw new RuntimeException("cannot solve expression, " + prog);
        }

        if ( logDebug ) {
            debugLogger.debug( String.format("answer = %.4f", answer) );
        }

        if ( logTrace ) {
            traceLogger.debug( String.format("answer = %.4f", answer) );
        }

        return answer;
    }

    protected double solve1() {

        double d3;
        double d2;
        double d1;

        if (tindex == 0) {
            if (sign[tindex] == NUMBER) return exp[tindex];
            if (sign[tindex] == VARIABLE) return find_varValue(exp[tindex]);
        }

        int op = (int) exp[tindex];

        if (op > THREE_ARGS) {
            d3 = get_oprand();
            d2 = get_oprand();
            d1 = get_oprand();
            return calculate3(op, d1, d2, d3);
        }
        else
        if (op > TWO_ARGS) {
            d2 = get_oprand();
            d1 = get_oprand();
            return calculate2(op, d1, d2);
        }
        else {
            d1 = get_oprand();
            return calculate1(op, d1);
        }
    }

    protected double get_oprand() {

        if (sign[--tindex] == VARIABLE) {
            return find_varValue((int) exp[tindex]);
        }
        else
        if (sign[tindex] == NUMBER) {
            return exp[tindex];
        }
        else {
            return solve1();
        }
    }

    protected double calculate1(int i, double d1) {

        double result = Double.NaN;
        String operation= "";

        switch (i) {
            case LN:
                result = MathUtil.log(d1);       //natural log
                if ( logTrace )
                    operation = String.format("ln(%.4f) = %.4f", d1, result);
                break;
            case EXP:
                result = Math.pow(Math.E, d1);   //e^x
                if ( logTrace )
                    operation = String.format("exp(%.4f) = %.4f", d1, result);
                break;
            case ABS:
                result = Math.abs(d1);           //abs() function
                if ( logTrace )
                    operation = String.format("abs(%.4f) = %.4f", d1, result);
                break;
            case SIGN:                         //sign() function
                if (d1 < 0)
                    result = -1;
                else if (d1 == 0)
                    result = 0;
                else
                    result = 1;
                if ( logTrace )
                    operation = String.format("sign(%.4f) = %.4f", d1, result);
                break;
            case INT:                         //int() function
                result = Math.floor(d1);
                if ( logTrace )
                    operation = String.format("int(%.4f) = %.4f", d1, result);
                break;
            case PUT:                         //put() function
                valueStack[sp] = d1;
                sp++;
                result = d1;
                if ( logTrace )
                    operation = String.format("put(%.4f) = %.4f", d1, result);
                break;
            case GET:                         //get() function
                result = valueStack[(int)d1];
                if ( logTrace )
                    operation = String.format("get(%.4f) = %.4f", d1, result);
                break;
            case SQRT:                        //sqrt() function
                result = Math.sqrt(d1);
                if ( logTrace )
                    operation = String.format("sqrt(%.4f) = %.4f", d1, result);
                break;
            default:
                throw new RuntimeException("calculate1, function = " + i + " not found ");
        }


        if ( logTrace ) {
            traceLogger.debug( operation );
        }

        return result;
    }

    protected double calculate2(int i, double d1, double d2) {

        double result = Double.NaN;
        String operation = "";

        switch (i) {
            case ADDITION:
                result = d1 + d2;
                if ( logTrace )
                    operation = String.format("%.4f + %.4f = %.4f", d1, d2, result);
                break;
            case SUBTRACTION:
                result =  d1 - d2;
                if ( logTrace )
                    operation = String.format("%.4f - %.4f = %.4f", d1, d2, result);
                break;
            case MULTIPLICATION:
                result =  d1 * d2;
                if ( logTrace )
                    operation = String.format("%.4f * %.4f = %.4f", d1, d2, result);
                break;
            case DIVISION:
                result =  d1 / d2;
                if ( logTrace )
                    operation = String.format("%.4f / %.4f = %.4f", d1, d2, result);
                break;
            case MODULUS:
                result =  d1 % d2;
                if ( logTrace )
                    operation = String.format("%.4f % %.4f = %.4f", d1, d2, result);
                break;
            case GREATER:                   // >
                if (d1 > d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f > %.4f) = %.4f", d1, d2, result);
                break;
            case LESS:                      // <
                if (d1 < d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f < %.4f) = %.4f", d1, d2, result);
                break;
            case EQUAL:                     // ==
                if (d1 == d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f == %.4f) = %.4f", d1, d2, result);
                break;
            case NOT_EQUAL:                  // !=
                if (d1 != d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f != %.4f) = %.4f", d1, d2, result);
                break;
            case POWER:                     //general power function
                result =  Math.pow(d1, d2);
                if ( logTrace )
                    operation = String.format("pow(%.4f, %.4f) = %.4f", d1, d2, result);
                break;
            case MAX:
                result =  Math.max(d1, d2);
                if ( logTrace )
                    operation = String.format("max(%.4f, %.4f) = %.4f", d1, d2, result);
                break;
            case MIN:
                result =  Math.min(d1, d2);
                if ( logTrace )
                    operation = String.format("min(%.4f, %.4f) = %.4f", d1, d2, result);
                break;
            case GREATER_EQUAL:
                if (d1 >= d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f >= %.4f) = %.4f", d1, d2, result);
                break;
            case LESS_EQUAL:
                if (d1 <= d2)
                    result =  1;
                else
                    result =  0;
                if ( logTrace )
                    operation = String.format("if(%.4f <= %.4f) = %.4f", d1, d2, result);
                break;
            default:
                throw new RuntimeException("calculate2, function = " + i + " not found ");
        }


        if ( logTrace ) {
            traceLogger.debug( operation );
        }

        return result;
    }

    protected double calculate3(int i, double d1, double d2, double d3) {

        double result = Double.NaN;
        String operation = "";

        switch (i) {
            case IF:                           //if(x,y,z) function
                if (d1 > 0)
                    result = d2;
                else
                    result = d3;
                if ( logTrace )
                    operation = String.format("if(%.4f, %.4f, %.4f) = %.4f", d1, d2, d3, result);
                break;
            default:
                throw new RuntimeException("calculate3, function = " + i + " not found ");
        }


        if ( logTrace ) {
            traceLogger.debug( operation );
        }

        return result;
    }

    /** Return the value of a variable.
     */
    protected final double find_varValue(double i) {

        double value = vtable.getValueForIndex((int)i);

        if (logDebug) {
            String name = (String) variableMap.get(new Integer((int)i));
            debugLogger.debug(name + " = "+ String.format("%.3f", value) );
        }

        return value;
    }

    /** Return the value of a variable.
     */
    protected final double find_varIndex(String token) {
        int indexValue = (int) vtable.getIndexValue(token);
        variableMap.put( indexValue, token);
        return indexValue;
    }

    /** Returns the precedence of an operator
     */
    protected int find_pre(char c) {
        if (c == '=' || c == '!')
            return 1;
        if (c == '<' || c == '>' || c == '{' || c == '}')
            return 2;
        if (c == '+' || c == '-')
            return 3;
        if (c == '*' || c == '/' || c == '%')
            return 4;
        if (c == '^')
            return 5;

        return 0;
    }

    /** Return the next token.
     */
    protected final void get_token() {
        String cur_token = "";
        tok_type = 0;
        boolean processed = false;

        if (prog.equals("")) return;
        if (count >= prog.length()) {
            token = "_end_";
            return;
        }

        while (Character.isWhitespace(prog.charAt(count)) ) {
            count++;
        }

        char c = prog.charAt(count);

        //Variable
        if ( (Character.isLetter(c)) || (c == '$') || (c == '@') ) {
            int count1 = count;
            while (!isdelim(prog.charAt(count)) && count < prog.length() - 1)
                count++;
            if (!isdelim(prog.charAt(count)))
                cur_token = prog.substring(count1, ++count);
            else
                cur_token = prog.substring(count1, count);

            tok_type = VARIABLE;
        }

        //Number
        if ( (Character.isDigit(c)) || (c == '.') ) {
            int count2 = count;
            while (!isdelim(prog.charAt(count)) && count < prog.length() - 1)
                count++;
            if (!isdelim(prog.charAt(count)))
                cur_token = prog.substring(count2, ++count);
            else
                cur_token = prog.substring(count2, count);

            tok_type = NUMBER;
        }

        //Special handling for minus sign. Might be a negative number
        //such as (-0.25+10)
        if ( (c == '-') ) {

            //1. Look ahead one character for a digit
            char c1 = prog.charAt(count+1);
            if ( (Character.isDigit(c1)) || (c1 == '.') ) {

                //2. Check that a delimiter is to the left
                if ( (count == 0) ||
                     ((count > 0) && (isdelim(prog.charAt(count-1)))) ) {

                    int count2 = count;
                    count++;
                    while (!isdelim(prog.charAt(count)) && count < prog.length() - 1)
                        count++;
                    if (!isdelim(prog.charAt(count)))
                        cur_token = prog.substring(count2, ++count);
                    else
                        cur_token = prog.substring(count2, count);

                    tok_type = NUMBER;
                    cur_token = prog.substring(count2, count);
                    processed = true;
                }
            }
        }

        //Delimiter
        if ( isdelim(c) && ! (processed) ) {

            tok_type = DELIMITER;

            //Look ahead to handle ==, !=, <=, >=
            if ( (count+1 < prog.length()) && (prog.charAt(count+1) == '=' ) ) {
                cur_token = prog.substring(count, count+2);
                count += 2;
            }
            else {
                cur_token = prog.substring(count, ++count);
            }
        }

        token = cur_token;

        if (logDebug) {
            debugLogger.debug("get_token, token: " + token);
        }
    }

    /** Return true if character is a delimiter.
     *
     * ascii 0   ->  null
     * ascii 9   ->  horizontal tab
     * ascii 32  ->  space
     */
    protected final boolean isdelim(char c) {
        if (("+-/*%^=()>,<! ".indexOf(String.valueOf(c)) != -1) || c == 9 || c == 0)
            return true;
        else
            return false;
    }

    /** Display a syntax error.
     */
    protected final void serror(int i) {
        logger.warn(errors[i]);
    }


    protected void logVariableTable() {

        if (logger.isDebugEnabled()) {

            int length = 0;
            Iterator it;

            //Find maximum length of variables in map
            it = variableMap.keySet().iterator();
            while (it.hasNext()) {
                Integer index = (Integer)it.next();
                String varName = (String) variableMap.get(index);
                length = Math.max(length, varName.length());
            }

            String format = "%-"+length+"s";

            it = variableMap.keySet().iterator();
            while (it.hasNext()) {
                Integer index = (Integer)it.next();
                String varName = (String) variableMap.get(index);
                StringBuffer sb = new StringBuffer(128);
                sb.append( String.format( format, varName) );
                sb.append( String.format(" = %5d", index.intValue()) );
                logger.debug( sb.toString() );
            }
        }
    }

    protected void logStackContents() {

        if (logger.isDebugEnabled()) {

            StringBuffer sb = new StringBuffer(128);
            sb.append("sign[]=");

            for (int j=0; j <= expindex; j++) {
                sb.append( String.format("%7s,", getSign(sign[j])) );
            }
            logger.debug( sb.toString() );

            sb = new StringBuffer(128);
            sb.append("exp[]= ");
            for (int j=0; j <= expindex; j++) {
                sb.append( String.format("%7s,", getExp(sign[j], exp[j]) ) );
            }
            logger.debug( sb.toString() );
        }
        /*
        System.out.print( "temp[]=");
        for (int j=0; j < 10; j++) {
            System.out.print( Format.print("%7c,", temp[j]) );
        }
        System.out.println();
        */
    }

    protected int findMaximumLength(HashMap map) {

        int length = 0;

        Iterator it = map.keySet().iterator();
        while (it.hasNext()) {
            Integer index = (Integer)it.next();
            String varName = (String) map.get(index);
            length = Math.max(length, varName.length());
        }

        return length;
    }

    /** Used in debugging output
     */
    protected String getSign(int sign) {

        switch (sign) {
            case DELIMITER: return "DELIM";
            case NUMBER: return "NUM";
            case VARIABLE: return "VAR";
        }

        return "NF";
    }

    /** Used in debugging output
     */
    protected String getExp(int sign, double exp) {

        if (sign == DELIMITER) {

            switch ((int)exp) {
                case LN: return "LN";
                case EXP: return "EXP";
                case ABS: return "ABS";
                case SIGN: return "SIGN";
                case INT: return "INT";
                case GET: return "GET";
                case PUT: return "PUT";
                case SQRT: return "SQRT";

                case ADDITION: return "ADD";
                case SUBTRACTION: return "SUB";
                case MULTIPLICATION: return "MULT";
                case DIVISION: return "DIV";
                case MODULUS: return "MOD";
                case POWER: return "POW";
                case MAX: return "MAX";
                case MIN : return "MIN";
                case EQUAL: return "==";
                case NOT_EQUAL: return "!=";
                case GREATER: return ">";
                case LESS: return "<";
                case GREATER_EQUAL: return ">=";
                case LESS_EQUAL: return "<=";

                case IF: return "IF";
            }
        }
        else
        if (sign == NUMBER) {
            return String.format("%7.2f", exp);
        }
        else {
            return String.format("%7d", (int)exp);
        }

        return "NF";
    }

}
