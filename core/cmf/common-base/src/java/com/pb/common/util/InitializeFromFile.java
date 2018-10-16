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
package com.pb.common.util;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.IOException;
import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.util.StringTokenizer;
import org.apache.log4j.Logger;

/**
 * This static class initializes the members of an object from a file; it is similar to the FORTRAN NAMELIST
 * command, but only requires a class containing fields whose names are exactly listed
 * in a text file along with corresponding values.
 * The text file can be delimited by spaces, commas, or tabs.  The fields can be String, boolean,
 * byte, short, int, long, float or double.  Arrays of primitives are handled, but not Arrays of
 * Strings.  Arrays should be listed by (example in space-delimited format):
 * <p/>
 * arrayName[]   value1  value2  value3...valuen
 * 
 * @author Joel Freedman
 * @version 11/02
 */
public final class InitializeFromFile {

    protected static Logger logger = Logger.getLogger("com.pb.common.util");

    public static Object getValues(String fileName, Object target) {

        Field[] targetFields = target.getClass().getFields();

        /**
         * Try using reflection to initialize the class fields
         * from a text file.
         **/
        String s;
        String d = new String();
        int index = 0;
        try {
            BufferedReader br = new BufferedReader(new FileReader(fileName));
            while ((s = br.readLine()) != null) {
                StringTokenizer st = new StringTokenizer(s, " ");
                if (s.startsWith(";")) continue;      // a comment card
                s = s.trim();
                ++index;
                if (index == 1) {
                    logger.debug("Scanning text parameter file " + fileName);
                    //find out what the delimiter is
                    if (s.indexOf(",") != -1) {
                        logger.debug(" in comma-delimited format");
                        d = ",";
                    } else if (s.indexOf(" ") != -1) {
                        logger.debug(" in space-delimited format");
                        d = " ";
                    } else {
                        logger.debug(" in tab-delimited format");
                        d = "\t";
                    }
                    st = new StringTokenizer(s, d);

                }
                if (st.countTokens() < 2) {
                    logger.error("Error: Only " + st.countTokens() + " fields in file " + fileName);
                    System.exit(1);
                }
                //first field is variable name
                String name = st.nextToken();

                if (name.endsWith("]"))
                    name = name.substring(0, name.indexOf("["));
                  
                //search for name in class fields
                for (int i = 0; i < targetFields.length; ++i) {
                    //strip the package from the field name
                    String searchName = targetFields[i].toString().substring((targetFields[i].toString().lastIndexOf(".") + 1));
                    if (searchName.equals(name)) {
                        //found variable name in class fields
                        try {
                            //set the value depending on the type
                            String type = targetFields[i].getType().getName();
                            //if type is array, set the elements of the array
                            if (type.indexOf("[") > -1) {
                                type = type.substring(type.length() - 1);
                                if (type.equals("B")) {
                                    byte j = 0;
                                    byte value[] = new byte[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Byte(st.nextToken()).byteValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("Z")) {
                                    int j = 0;
                                    boolean value[] = new boolean[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Boolean(st.nextToken()).booleanValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("S")) {
                                    int j = 0;
                                    short value[] = new short[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Short(st.nextToken()).shortValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("I")) {
                                    int j = 0;
                                    int value[] = new int[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Integer(st.nextToken()).intValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("J")) {
                                    int j = 0;
                                    long value[] = new long[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Long(st.nextToken()).longValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("F")) {
                                    int j = 0;
                                    float value[] = new float[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Float(st.nextToken()).floatValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                if (type.equals("D")) {
                                    int j = 0;
                                    double value[] = new double[st.countTokens()];
                                    while (st.hasMoreTokens()) {
                                        value[j] = new Double(st.nextToken()).doubleValue();
                                        ++j;
                                    }
                                    targetFields[i].set(target, value);
                                }
                                break;
                            }   
                            //otherwise set the value                                                    
                            if (type.equals("java.lang.String")) {
                                String value = st.nextToken();
                                targetFields[i].set(target, value);
                                break;
                            }
                            if (type.equals("byte")) {
                                byte value = new Byte(st.nextToken()).byteValue();
                                targetFields[i].setByte(target, value);
                                break;
                            }
                            if (type.equals("boolean")) {
                                boolean value = new Boolean(st.nextToken()).booleanValue();
                                targetFields[i].setBoolean(target, value);
                                break;
                            }
                            if (type.equals("short")) {
                                short value = new Short(st.nextToken()).shortValue();
                                targetFields[i].setShort(target, value);
                                break;
                            }
                            if (type.equals("int")) {
                                int value = new Integer(st.nextToken()).intValue();
                                targetFields[i].setInt(target, value);
                                break;
                            }
                            if (type.equals("long")) {
                                long value = new Long(st.nextToken()).longValue();
                                targetFields[i].setLong(target, value);
                                break;
                            }
                            if (type.equals("float")) {
                                float value = new Float(st.nextToken()).floatValue();
                                targetFields[i].setFloat(target, value);
                                break;
                            }
                            if (type.equals("double")) {
                                double value = new Double(st.nextToken()).doubleValue();
                                targetFields[i].setDouble(target, value);
                                break;
                            }
                            logger.error("Error: couldn't find type of " + name);
                        } catch (Exception e) {
                            logger.error("Tried to set value of " + name + " and failed");
                        }
                    }
                }

            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return target;
    }

    public static void writeValues(BufferedWriter bw, Object tmp) {

        if (bw == null) {
            logger.error("Error: writeValues not possible as BufferedWriter is null");
            throw new RuntimeException();
        }
        try {
            Field[] fields = tmp.getClass().getFields();
            for (int i = 0; i < fields.length; ++i) {
                String name = fields[i].toString().substring((fields[i].toString().lastIndexOf(".") + 1));
                bw.write(name);
                for (int j = name.length(); j < 30; ++j)
                    bw.write(' ');

                if (!fields[i].get(tmp).getClass().isArray()) {
                    bw.write(fields[i].get(tmp).toString());
                } else {
                    for (int j = 0; j < Array.getLength(fields[i].get(tmp)); ++j) {
                        bw.write(Array.get(fields[i].get(tmp), j).toString());
                        for (int k = Array.get(fields[i].get(tmp), j).toString().length(); k < 6; ++k)
                            bw.write(' ');
                        bw.write("          ");
                    }
                }
                bw.newLine();
            }
            bw.flush();
        } catch (Exception e) {
            logger.error("Tried to write to bufferedWriter in InitializeFromFile.writeValues()");
            throw new RuntimeException();
        }

    }

    public static void logValues(Object tmp) {

        String name = new String();
        Field[] fields = tmp.getClass().getFields();
        try {
            for (int i = 0; i < fields.length; ++i) {
                name = String.format("%-20s   ", fields[i].toString().substring((fields[i].toString().lastIndexOf(".") + 1)));
                String values = new String();
                if (!fields[i].get(tmp).getClass().isArray()) {
                    values = new String(values + String.format("%20s   ", fields[i].get(tmp).toString()));
                } else {
                    for (int j = 0; j < Array.getLength(fields[i].get(tmp)); ++j) {
                        values = new String(values + String.format("%20s   ", Array.get(fields[i].get(tmp), j).toString() + "     "));
                    }
                }
                logger.info(name + values);
            }
        } catch (Exception e) {
            logger.error("Tried to access a field in InitializeFromFile.logValues()");
            logger.error("Fields length " + fields.length);
            logger.error("Field name " + name);
            throw new RuntimeException();
        }

    }
    /**
     * Returns the value of a field in the object as a string
     * @param fieldName
     * @return the value of the field
     */
    public static String getValue(String fieldName, Object tmp){
        String name = new String();
        Field[] fields = tmp.getClass().getFields();
        String values= new String();
        try {
            for (int i = 0; i < fields.length; ++i) {
                name =  fields[i].toString().substring((fields[i].toString().lastIndexOf(".") + 1));
                
                if(name.compareTo(fieldName)==0){
               
                    if (!fields[i].get(tmp).getClass().isArray()) {
                        values = new String(values + String.format("%20s   ", fields[i].get(tmp).toString()));
                    } else {
                     for (int j = 0; j < Array.getLength(fields[i].get(tmp)); ++j) {
                        values = new String(values + String.format("%20s   ", Array.get(fields[i].get(tmp), j).toString() + "     "));
                    }
                }
            }
            }
        } catch (Exception e) {
            logger.error("Tried to access a field in InitializeFromFile.logValues()");
            logger.error("Fields length " + fields.length);
            logger.error("Field name " + name);
            throw new RuntimeException();
        }
        return values;
    
    }

}