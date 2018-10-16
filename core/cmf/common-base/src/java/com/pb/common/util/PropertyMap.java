package com.pb.common.util;

import java.io.Serializable;
import java.util.HashMap;
import java.util.HashSet;
import java.util.StringTokenizer;

public class PropertyMap implements Serializable{

	   public static boolean getBooleanValueFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {
	        boolean returnValue;
	        String value = rbMap.get(key);
	        if (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("false"))
	        {
	            returnValue = Boolean.parseBoolean(value);
	        } else
	        {
	            System.out.println("property file key: " + key + " = " + value + " should be either 'true' or 'false'.");
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
	            System.out.println( "property file key: " + key + " missing.  No integer value can be determined.");
	            throw new RuntimeException();
	        }
	    }

	    /**
	     * This method returns an integer array from a comma-separated string in a HashMap, useful for arrays stored in a property file.
	     * The method guarantees to preserve order of values as represented in the original map.
	     * 
	     * @param rbMap  A HashMap
	     * @param key    The key to look up
	     * @return  An array of integer values in the order stored in the HashMap
	     */
	    public static int[] getIntegerArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {

	        int[] returnArray;
	        String valueList = rbMap.get(key);
	        if (valueList != null)
	        {

	        
	        	int elements = 0;
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    valueTokenizer.nextToken();
                    ++elements;
                }
                valueTokenizer = new StringTokenizer(valueList, ",");
                returnArray = new int[elements];
	            int element = 0; 
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
                    int intValue = Integer.parseInt(listValue.trim());
                    returnArray[element] = intValue;
                    ++element;
                }

	        } else
	        {
	            System.out.println( "property file key: " + key + " missing.  No integer array can be created.");
	            throw new RuntimeException();
	        }

	        return returnArray;

	    }

	    /**
	     * This method returns an byte array from a comma-separated string in a HashMap, useful for arrays stored in a property file.
	     * The method guarantees to preserve order of values as represented in the original map.
	     * 
	     * @param rbMap  A HashMap
	     * @param key    The key to look up
	     * @return  An array of byte values in the order stored in the HashMap
	     */
	    public static byte[] getByteArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {

	        byte[] returnArray;
	        String valueList = rbMap.get(key);
	        if (valueList != null)
	        {

	        
	        	int elements = 0;
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    valueTokenizer.nextToken();
                    ++elements;
                }
                valueTokenizer = new StringTokenizer(valueList, ",");
                returnArray = new byte[elements];
	            int element = 0; 
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
                    byte byteValue = Byte.parseByte(listValue.trim());
                    returnArray[element] = byteValue;
                    ++element;
                }

	        } else
	        {
	            System.out.println( "property file key: " + key + " missing.  No integer array can be created.");
	            throw new RuntimeException();
	        }

	        return returnArray;

	    }

	    /**
	     * This method returns an boolean array from a comma-separated string in a HashMap, useful for arrays stored in a property file.
	     * The method guarantees to preserve order of values as represented in the original map.
	     * 
	     * @param rbMap  A HashMap
	     * @param key    The key to look up
	     * @return  An array of booleans in the order stored in the HashMap
	     */
	    public static boolean[] getBooleanArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {

	        boolean[] returnArray = null;
	        String valueList = rbMap.get(key);
	        if (valueList != null)
	        {
	        	int elements = 0;
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    valueTokenizer.nextToken();
                    ++elements;
                }
                valueTokenizer = new StringTokenizer(valueList, ",");
                returnArray = new boolean[elements];
	            int element = 0; 
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
        	     	boolean returnValue = false;
                    if (listValue.equalsIgnoreCase("true") || listValue.equalsIgnoreCase("false"))
        	        	returnValue = Boolean.parseBoolean(listValue);
                    else if(listValue.equals("1") )
                    	returnValue = true;
                    else if(listValue.equals("0"))
                    	returnValue = false;
                    else{
        	            System.out.println("property file key: " + key + " = " + listValue + " should be either 'true' or 'false' or 0 or 1.");
        	            throw new RuntimeException();
        	        }
                    returnArray[element] = returnValue;
                    ++element;
                }

	        } else
	        {
	            System.out.println( "property file key: " + key + " missing.  No boolean array can be created.");
	            throw new RuntimeException();
	        }

	        return returnArray;

	    }

	    
	    
	    
	    
	    
	    /**
	     * This method returns a float array from a comma-separated string in a HashMap, useful for arrays stored in a property file.
	     * The method guarantees to preserve order of values as represented in the original map.
	     * 
	     * @param rbMap  A HashMap
	     * @param key    The key to look up
	     * @return  An array of float values in the order stored in the HashMap
	     */
	    public static float[] getFloatArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {

	        float[] returnArray;
	        String valueList = rbMap.get(key);
	        if (valueList != null)
	        {

	        
	        	int elements = 0;
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    valueTokenizer.nextToken();
                    ++elements;
                }
                valueTokenizer = new StringTokenizer(valueList, ",");
                returnArray = new float[elements];
	            int element = 0; 
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
                    float floatValue = Float.parseFloat(listValue.trim());
                    returnArray[element] = floatValue;
                    ++element;
                }

	        } else
	        {
	            System.out.println( "property file key: " + key + " missing.  No float value can be determined.");
	            throw new RuntimeException();
	        }

	        return returnArray;

	    }
	    
	    public static long getLongValueFromPropertyMap(HashMap<String, String> rbMap, String key){
		        String value = rbMap.get(key);
		        if (value != null)
		        {
		            return Long.parseLong(value);
		        } else
		        {
		            System.out.println( "property file key: " + key + " missing.  No long integer value can be determined.");
		            throw new RuntimeException();
		        }
		}

	    /**
	     * This method returns a string array from a comma-separated string in a HashMap, useful for arrays stored in a property file.
	     * The method guarantees to preserve order of values as represented in the original map.
	     * 
	     * @param rbMap  A HashMap
	     * @param key    The key to look up
	     * @return  An array of string values in the order stored in the HashMap
	     */
	    public static String[] getStringArrayFromPropertyMap(HashMap<String, String> rbMap, String key)
	    {

	        String[] returnArray;
	        String valueList = rbMap.get(key);
	        if (valueList != null)
	        {

	        
	        	int elements = 0;
                StringTokenizer valueTokenizer = new StringTokenizer(valueList, ",");
                while(valueTokenizer.hasMoreTokens())
                {
                    valueTokenizer.nextToken();
                    ++elements;
                }
                valueTokenizer = new StringTokenizer(valueList, ",");
                returnArray = new String[elements];
	            int element = 0; 
                while(valueTokenizer.hasMoreTokens())
                {
                    String listValue = valueTokenizer.nextToken();
                     returnArray[element] = listValue;
                    ++element;
                }

	        } else
	        {
	            System.out.println( "property file key: " + key + " missing.  No string array can be created.");
	            throw new RuntimeException();
	        }

	        return returnArray;

	    }

	    

	    /**
	     * Get a float value from the property map.
	     * 
	     * @param rbMap  Property map
	     * @param key    The key to lookup in the map
	     * @return  The float value
	     */
		public static float getFloatValueFromPropertyMap(HashMap<String, String> rbMap, String key){
		        String value = rbMap.get(key);
		        if (value != null)
		        {
		            return Float.parseFloat(value);
		        } else
		        {
		            System.out.println( "property file key: " + key + " missing.  No float value can be determined.");
		            throw new RuntimeException();
		        }
		}

}
