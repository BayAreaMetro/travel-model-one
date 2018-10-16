/*
 * Copyright 2006 PB Consult Inc.
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
 */
package com.pb.models.synpopV3;

import org.apache.log4j.Logger;
import com.pb.common.util.ResourceUtil;
import java.util.HashMap;
import java.util.Vector;
import java.util.Set;
import java.util.Iterator;
import java.util.StringTokenizer;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.0, Dec. 15, 2003
 */

public class PropertyParser {

  protected static HashMap propertyMap;
//  protected static Logger logger;
    protected static Logger logger=Logger.getLogger(PropertyParser.class);

//  static {
//  	propertyMap=ResourceUtil.getResourceBundleAsHashMap("arc");
//  	logger=Logger.getLogger("com.pb.models.synpopV3");
//  }

  public static void setPropertyMap( String propertyFile ){
        propertyMap=ResourceUtil.getResourceBundleAsHashMap( propertyFile );
    }
    
  public static HashMap getPropertyMap(){
        return propertyMap;
    }
    
  public static Logger getLogger(){
  	return logger;
  }
  
  /**
   * Parse key--value pairs in property file as a HashMap, indexed by keys
   * @param keyType represents what type of keys is parsed. e.g. ".source" ".columns"
   * @return
   */
  public static HashMap getPropertyByType(String keyType){

    HashMap result=new HashMap();
    Set keySet=propertyMap.keySet();
    Iterator itr=keySet.iterator();
    String key=new String();
    String keyName=new String();
    String keyValue=new String();

    while (itr.hasNext()) {
        key = (String) itr.next();
        //find keys in property file belong to given key type
        if (key.endsWith(keyType)) {
          //eliminate .keyType from key string
          keyName=key.replaceAll(keyType,"");
          //get key value of a given key
          keyValue =(String)propertyMap.get(key);
          //add key and key value pair to a HashMap object
          result.put(keyName,keyValue);
        }
    }
    return result;
  }

  /**
   * Return number of properties by type
   * @param keyType
   * @return
   */
  public static int getNoOfPropertiesByType(String keyType){
    return getPropertyByType(keyType).size();
  }

  /**
   * Given property name, return property
   * @param propertyName represents the given property name
   * @return
   */
  public static String getPropertyByName(String propertyName){
    return (String)propertyMap.get(propertyName);
  }
  
  /**
   * Given property name and separator, return a vector of property elements
   * @param propertyName represents the given property name
   * @param separator represents the separator between property elements
   * @return
   */
  public static Vector getPropertyElementsByName(String propertyName, String separator){
  	return parseValues(getPropertyByName(propertyName),separator);
  }
  
  /**
   * Parse a string using a given separator
   * @param string_raw represents string to be parsed
   * @param separator represents the separator
   * @return
   */
  public static Vector parseValues(String string_raw, String separator ) {
      Vector result = new Vector();
      StringTokenizer st = new StringTokenizer(string_raw, separator);

      while (st.hasMoreTokens()) {
          String token = st.nextToken();
          token=token.trim();
          result.add(token);
      }
      return result;
  }

  public static void main(String [] args){
    String CMD_LOCATION=PropertyParser.getPropertyByName("CMD_LOCAION");
    System.out.println("CMD_LOCATION="+CMD_LOCATION);
  }
}

