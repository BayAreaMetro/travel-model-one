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

import java.util.Vector;
import java.util.HashMap;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, modified Nov. 15, 2004
 *
 * Control variable index.  
 * 
 * 6 control variables:
 * 1) hhagecat: household header age 
 * 2) hsizecat: household size 
 * 3) hfamily: 	family status 
 * 4) hNOCcat: 	children status 
 * 5) hwrkrcat: number of workers 
 * 6) hinccat1: household income category
 * 
 * Important: these names must match the column labels in HHCatFile.csv
 */

public class ControlVarIndex {

  //raw control variables from property file
  protected static String ctrlVarRaw;
  //control variable names
  protected static Vector ctrlVars;
  //index map between indices and control variable
  protected static HashMap indexMap=new HashMap();
  //reverse of indexMap
  protected static HashMap reverseIndexMap=new HashMap();

  static{
  	
    ctrlVarRaw=PropertyParser.getPropertyByName("control.variables");
    ctrlVars=PropertyParser.parseValues(ctrlVarRaw,",");
    
    Integer index=null;
    String catName=null;
    //make index/reverse index map  
    //important: index starts from 0
    for(int i=0; i<ctrlVars.size(); i++){
      index=new Integer(i);
      catName=(String)ctrlVars.get(i);
      indexMap.put(index,catName);
      reverseIndexMap.put(catName,index);
    }
    
  }

  /**
   * Given a control variable, get its index.
   * @param varName represents a control varialbe.
   * @return
   */
  public static int getIndex(String varName){
    int index=((Integer)(reverseIndexMap.get(varName))).intValue();
    return index;
  }

  /**
   * Given an index, get control variable.
   * @param index represents the index of a control variable.
   * @return
   */
  public static String getCtrlVarName(int index){
    String ctrlVarName=(String)indexMap.get(new Integer(index));
    return ctrlVarName;
  }

  /**
   * Get control variables
   * @return
   */  
  public static String [] getCtrlVarNames(){
  	String [] result=new String[ctrlVars.size()];
  	for(int i=0; i<ctrlVars.size(); i++){
  		result[i]=(String)ctrlVars.get(i);
  	}
  	return result;
  }
  
  /**
   * get number of control variables
   * @return
   */
  public static int getCtrlVarCount(){
  	return ctrlVars.size();
  }

  //for test purpose only
  public static void main(String [] args){
  	System.out.println(ControlVarIndex.getCtrlVarCount());
  	System.out.println(ControlVarIndex.getCtrlVarName(0));
  	System.out.println(ControlVarIndex.getCtrlVarName(5));
  }
}