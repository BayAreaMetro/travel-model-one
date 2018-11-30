package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;
import java.util.HashSet;
import java.util.StringTokenizer;

import org.apache.log4j.Logger;

public class Util
        implements Serializable
{

    private static Logger logger = Logger.getLogger(Util.class);

    public static boolean getBooleanValueFromPropertyMap(HashMap<String, String> rbMap, String key)
    {
        boolean returnValue;
        String value = rbMap.get(key);
        if (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("false"))
        {
            returnValue = Boolean.parseBoolean(value);
        } else
        {
            logger.error("property file key: " + key + " = " + value
                    + " should be either 'true' or 'false'.");
            throw new RuntimeException();
        }

        return returnValue;
    }

    public static String getStringValueFromPropertyMap(HashMap<String, String> rbMap, String key)
    {
        String returnValue = rbMap.get(key);
        if (returnValue == null) returnValue = "";

        return returnValue;
    }

    public static int getIntegerValueFromPropertyMap(HashMap<String, String> rbMap, String key)
    {
        String value = rbMap.get(key);
        if (value != null)
        {
            return Integer.parseInt(value);
        } else
        {
            logger.error("property file key: " + key
                    + " missing.  No integer value can be determined.");
            throw new RuntimeException();
        }
    }

    public static float getFloatValueFromPropertyMap(HashMap<String, String> rbMap, String key)
    {
        String value = rbMap.get(key);
        if (value != null)
        {
            return Float.parseFloat(value);
        } else
        {
            logger.error("property file key: " + key
                    + " missing.  No float value can be determined.");
            throw new RuntimeException();
        }
    }
 
    public static int[] getIntegerArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
    {

        int[] returnArray;
        String valueList = rbMap.get(key);
        if (valueList != null)
        {

            HashSet<Integer> valueSet = new HashSet<Integer>();

            if (valueSet != null)
            {
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
                    int intValue = Integer.parseInt(listValue.trim());
                    valueSet.add(intValue);
                }
            }

            returnArray = new int[valueSet.size()];
            int i = 0;
            for (int v : valueSet)
                returnArray[i++] = v;

        } else
        {
            logger.error("property file key: " + key
                    + " missing.  No integer value can be determined.");
            throw new RuntimeException();
        }

        return returnArray;

    }
    
    public static float[] getFloatArrayFromPropertyMap(HashMap<String, String> rbMap, String key) {
        String[] values = getStringValueFromPropertyMap(rbMap,key).split(",");
        float[] array = new float[values.length];
        for (int i = 0; i < array.length; i++)
        	array[i] = Float.parseFloat(values[i]);
        return array;
    }


}
