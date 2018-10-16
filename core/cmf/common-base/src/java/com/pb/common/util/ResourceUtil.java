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

import org.apache.log4j.Logger;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Iterator;
import java.util.MissingResourceException;
import java.util.Properties;
import java.util.PropertyResourceBundle;
import java.util.ResourceBundle;
import java.util.StringTokenizer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A helper class for working with ResourceBundles.
 *
 * @author Tim Heier
 * @version 1.0, 4/18/2002
 */
public class ResourceUtil {

    protected static Logger logger = Logger.getLogger(ResourceUtil.class);

    /**
     * Helper method for working with ResourceBundles. The classpath is
     * searched for the bundle name.
     *
     * @return reference to a resource bundle or NULL if bundle cannot be found.
     */
    public static ResourceBundle getResourceBundle(String bundleName) {

        ResourceBundle rb = null;

        try {
            rb = ResourceBundle.getBundle(bundleName);
        } catch (MissingResourceException e) {
            throw e;
        }

        return rb;
    }


    /**
     * Helper method for working with ResourceBundles. The propFile
     * location is used to load the property file. A property file bundle
     * is created and returned.
     *
     * @return reference to a resource bundle or NULL if bundle cannot be found.
     */
    public static ResourceBundle getPropertyBundle(File propFile) {

        FileInputStream inputStream = null;
        try {
            inputStream = new FileInputStream(propFile);
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        }

        PropertyResourceBundle rb = null;
        try {
            rb = new PropertyResourceBundle(inputStream);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return rb;
    }

    /**
     * Helper method for when working with ResourceBundles.
     *
     * @return value for keyName or defaultValue if keyName cannot be found.
     */
    public static ArrayList getListWithUserDefinedSeparator(ResourceBundle rb, String keyName, String separator) {

        String keyValue = keyName;
        ArrayList list = new ArrayList();

        try {
            keyValue = rb.getString(keyName);
        } catch (NullPointerException e) {
            //key was not found
        }

        //System properties can override values in resource bundle.
        String systemValue = checkSystemProperties(keyName);
        if (systemValue != null) {
            keyValue = systemValue;
        }

        //Parse list of values.
        StringTokenizer st = new StringTokenizer(keyValue, separator);
        while (st.hasMoreTokens()) {
            list.add(st.nextElement());
        }

        return list;
    }


    /**
     * Helper method for when working with ResourceBundles.
     *
     * @return value for keyName or defaultValue if keyName cannot be found.
     */
    public static ArrayList getList(ResourceBundle rb, String keyName) {

        String keyValue = keyName;
        ArrayList list = new ArrayList();

        try {
            keyValue = rb.getString(keyName);
        } catch (NullPointerException e) {
            //key was not found
        }

        //System properties can override values in resource bundle.
        String systemValue = checkSystemProperties(keyName);
        if (systemValue != null) {
            keyValue = systemValue;
        }

        //Parse list of values.
        StringTokenizer st = new StringTokenizer(keyValue, ", |");
        while (st.hasMoreTokens()) {
            list.add(st.nextElement());
        }

        return list;
    }

    public static String[] getArray (ResourceBundle rb, String keyName){
        ArrayList list = getList(rb,keyName);
        String[] array = new String[list.size()];
        for (int i = 0; i < list.size(); i++) {
             array[i] =  (String) list.get(i);
        }
        return array;
    }
    
    public static int[] getIntegerArray(ResourceBundle rb, String keyName) {
    	String property = getProperty(rb, keyName); 
    	int[] values = getIntValuesFromString(property); 
    	return values; 
    }

    public static double[] getDoubleArray(ResourceBundle rb, String keyName) {
    	String property = getProperty(rb, keyName); 
    	double[] values = getDoubleValuesFromString(property); 
    	return values; 
    }

    /**
     * Helper method for when working with ResourceBundles.
     *
     * @return HashMap with contents of the resource bundle or null if the filename is not found.
     */
    public static HashMap getResourceBundleAsHashMap(String bundleName) {

        ResourceBundle rb = getResourceBundle(bundleName);

        HashMap rbMap = new HashMap();
        Enumeration rbEnum = rb.getKeys();
        String keyName = null;
        String keyValue = null;

        // go through the Enumeration, get keywords, and put them in a HashMap
        while (rbEnum.hasMoreElements()) {

            keyName = (String) rbEnum.nextElement();

            try {
                keyValue = rb.getString(keyName);
            } catch (NullPointerException e) {
                //key was not found
            }

            //System properties can override values in resource bundle.
            String systemValue = checkSystemProperties(keyName);
            if (systemValue != null) {
                keyValue = systemValue;
            }

            //Check if value can be updated with system property values
            keyValue = replaceWithSystemPropertyValues(keyValue);

            rbMap.put(keyName, keyValue);
        }

        return rbMap;
    }

    /**
     * Helper method for when working with ResourceBundles.
     *
     * @return HashMap with contents of the resource bundle or null if the filename is not found.
     */
    public static HashMap changeResourceBundleIntoHashMap(ResourceBundle rb) {

        HashMap rbMap = new HashMap();
        Enumeration rbEnum = rb.getKeys();
        String keyName = null;
        String keyValue = null;

        // go through the Enumeration, get keywords, and put them in a HashMap
        while (rbEnum.hasMoreElements()) {

            keyName = (String) rbEnum.nextElement();

            try {
                keyValue = rb.getString(keyName);
            } catch (NullPointerException e) {
                //key was not found
            }

            //System properties can override values in resource bundle.
            String systemValue = checkSystemProperties(keyName);
            if (systemValue != null) {
                keyValue = systemValue;
            }

            //Check if value can be updated with system property values
            keyValue = replaceWithSystemPropertyValues(keyValue);

            //trailing spaces can cause parsing of boolean expressions to go awry
            keyValue = keyValue.trim();
            
            rbMap.put(keyName, keyValue);
        }

        return rbMap;
    }


    /**
     * Helper method for when working with ResourceBundles.
     *
     * @return value for keyName or defaultValue if keyName cannot be found.
     */
    public static String getProperty(ResourceBundle rb, String keyName, String defaultValue) {

        String keyValue = defaultValue;

        try {
            keyValue = rb.getString(keyName);
        } catch (RuntimeException e) {
            //key was not found or resourc bundle is null
            if(rb == null) throw new RuntimeException("ResourceBundle is null", e);
        }

        //System properties can override values in resource bundle.
        String systemValue = checkSystemProperties(keyName);
        if (systemValue != null) {
            keyValue = systemValue;
        }

        //Check if value can be updated with system property values
        keyValue = replaceWithSystemPropertyValues(keyValue);

        if(keyValue == null) return keyValue;  //you can't trim a null.

        return keyValue.trim();
    }


    /**
     * Convienence method, calls main method with null as default value.
     *
     * @return value for keyName or defaultValue if keyName cannot be found.
     */
    public static String getProperty(ResourceBundle rb, String keyName) {
        return getProperty(rb, keyName, null);
    }

    /**
     * Convenience method, logs and throws meaningful error message if property does not exist
     * @param rb the resource bundle to look for the property
     * @param keyName the name of the key
     * @return retVal
     */
    public static String checkAndGetProperty(ResourceBundle rb, String keyName) {
        String retVal = getProperty(rb, keyName);
        if (retVal == null) {
            logger.error("Can't find property "+keyName+" in Resource Bundle");
            throw new RuntimeException("Can't find property "+keyName+" in Resource Bundle");
        }
        return retVal;
    }

    public static String checkSystemProperties(String keyName) {
        return checkSystemProperties(keyName, null);
    }


    public static String checkSystemProperties(String keyName, String defaultValue) {

        String systemValue = null;

        try {
            systemValue = System.getProperty(keyName);
        } catch (RuntimeException e) {
            ;
        }

        if (systemValue == null) {
            systemValue = defaultValue;
        }
        return systemValue;
    }


    /*
     * Search and replace patterns in a string based on values in the environment.
     */
    public static String replaceWithSystemPropertyValues(String inputStr) {

        if (inputStr == null)
            return null;

        String tempStr = new String(inputStr);

        Properties props = System.getProperties();
        Iterator keys = props.keySet().iterator();

        while (keys.hasNext()) {
            String name = (String) keys.next();
            String value = props.getProperty(name);

            //Build a pattern and compile it
            String patternStr = "%" + name + "%";
            Pattern pattern = Pattern.compile(patternStr);

            // Replace all occurrences of pattern in input string
            Matcher matcher = pattern.matcher(tempStr);
            tempStr = matcher.replaceAll(value);
        }

        return tempStr;
    }

    /*
     *  use this to get an array of integer values from a delimited string of values in a properties file
     */
    public static int[] getIntValuesFromString ( String delimitedString ) {
        
        //Parse list of values from the input string.
        ArrayList list = new ArrayList();
        StringTokenizer st = new StringTokenizer(delimitedString, ", \\");
        while (st.hasMoreTokens()) {
            list.add(st.nextElement());
        }
        
        int[] values = new int[list.size()];
        for (int i=0; i < list.size(); i++)
            values[i] = Integer.parseInt((String)list.get(i));
        
        return values;
    }

    /*
     *  use this to get an array of double values from a delimited string of values in a properties file
     */
    public static double[] getDoubleValuesFromString ( String delimitedString ) {
        
        //Parse list of values from the input string.
        ArrayList list = new ArrayList();
        StringTokenizer st = new StringTokenizer(delimitedString, ", \\");
        while (st.hasMoreTokens()) {
            list.add(st.nextElement());
        }
        
        double[] values = new double[list.size()];
        for (int i=0; i < list.size(); i++)
            values[i] = Double.parseDouble((String)list.get(i));
        
        return values;
    }


    public static boolean getBooleanProperty(ResourceBundle rb, String flagName, boolean defaultValue) {
        String stringVal = getProperty(rb, flagName);
        if (stringVal == null) {
            logger.warn("Using default value of "+defaultValue+" for property "+flagName);
            return defaultValue;
        }
        if (stringVal.equalsIgnoreCase("false")) {
            return false;
        }
        if (stringVal.equalsIgnoreCase("true")) {
            return true;
        }
        logger.error("Boolean flag "+flagName+" is not set to 'true' or 'false' in property file, it is set to "+stringVal);
        throw new RuntimeException("Boolean flag "+flagName+" is not set to 'true' or 'false' in property file, it is set to "+stringVal);
    }

    public static boolean getBooleanProperty(ResourceBundle rb, String flagName) {
        String stringVal = getProperty(rb, flagName);
        boolean retVal = false;
        if (stringVal == null) {
            logger.error("Boolean flag "+flagName+" not set in property file");
            throw new RuntimeException("Boolean flag "+flagName+" not set in property file");
        }
        if (stringVal.equalsIgnoreCase("false")) {
            return false;
        }
        if (stringVal.equalsIgnoreCase("true")) {
            return true;
        }
        logger.error("Boolean flag "+flagName+" is not set to 'true' or 'false' in property file, it is set to "+stringVal);
        throw new RuntimeException("Boolean flag "+flagName+" is not set to 'true' or 'false' in property file, it is set to "+stringVal);
    }


    public static int getIntegerProperty(ResourceBundle rb, String name, int defaultValue) {
        String stringVal = ResourceUtil.getProperty(rb, name);
        if (stringVal == null) {
        	logger.warn("Using default value of "+defaultValue+" for property "+name);
        	return defaultValue;
        }
        int retVal = defaultValue;
        try {
        	Integer value = Integer.valueOf(stringVal);
        	retVal = value.intValue();
        } catch (Exception e) {
        	logger.error("Property "+name+" is not set properly as an integer in properties file, it is set to "+stringVal);
        	throw new RuntimeException("Property "+name+" is not set properly as an integer in properties file, it is set to "+stringVal);
        }
        return retVal;
    }


    public static double getDoubleProperty(ResourceBundle rb, String name, double defaultValue) {
        String stringVal = ResourceUtil.getProperty(rb, name);
        if (stringVal == null) {
        	logger.warn("Using default value of "+defaultValue+" for property "+name);
        	return defaultValue;
        }
        double retVal = defaultValue;
        try {
        	Double value = Double.valueOf(stringVal);
        	retVal = value.doubleValue();
        } catch (Exception e) {
        	logger.error("Property "+name+" is not set properly as a double in properties file, it is set to "+stringVal);
        	throw new RuntimeException("Property "+name+" is not set properly as a double in properties file, it is set to "+stringVal);
        }
        return retVal;
    }

    public static int getIntegerProperty(ResourceBundle rb, String name) {
        String stringVal = ResourceUtil.getProperty(rb, name);
        if (stringVal == null) {
            logger.error("Property "+name+" is not set in properties file");
            throw new RuntimeException("Property "+name+" is not set in properties file");
        }
        try {
            Integer value = Integer.valueOf(stringVal);
            return value.intValue();
        } catch (Exception e) {
            logger.error("Property "+name+" is not set properly as an integer in properties file, it is set to "+stringVal);
            throw new RuntimeException("Property "+name+" is not set properly as an integer in properties file, it is set to "+stringVal);
        }
    }


    public static double getDoubleProperty(ResourceBundle rb, String name) {
        String stringVal = ResourceUtil.getProperty(rb, name);
        if (stringVal == null) {
            logger.error("Property "+name+" is not set in properties file");
            throw new RuntimeException("Property "+name+" is not set in properties file");
        }
        try {
            Double value = Double.valueOf(stringVal);
            return value.doubleValue();
        } catch (Exception e) {
            logger.error("Property "+name+" is not set properly as a double in properties file, it is set to "+stringVal);
            throw new RuntimeException("Property "+name+" is not set properly as a double in properties file, it is set to "+stringVal);
        }
    }

    
}