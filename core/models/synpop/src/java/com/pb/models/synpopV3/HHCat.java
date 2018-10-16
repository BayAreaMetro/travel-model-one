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

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.0, Jan. 8, 2004
 *
 * This class represents one HH catetory.
 */

public class HHCat {
	
  protected Logger logger;
  //control variable values
  protected String [] ctrlVals;
  //number of control variables
  protected int NoCtrlVars;

  /**
   * Constructor.
   * @param ctrlVal represents control variable values.
   */
  public HHCat(String [] ctrlVals) {
  	
    logger=Logger.getLogger("com.pb.models.synpopV3");
    this.ctrlVals=ctrlVals;
    NoCtrlVars=ctrlVals.length;
    
  }
  
  /**
   * get control variable values
   * @return
   */
  public String [] getCtrlVarVals(){
  	return ctrlVals;
  }
  
  public void print(){
  	for(int i=0; i<NoCtrlVars; i++){
  		logger.info("name="+ControlVarIndex.getCtrlVarName(i)+" value="+ctrlVals[i]);
  	}
  }
  
  /**
   * compare this object with a given HHCat object
   * @param hhcat
   * @return
   */
  public boolean equals(HHCat hhcat){
  	
  	boolean result=true;
  	String [] hhcatVal=hhcat.getCtrlVarVals();
  	String tempVal=null;
  	for(int i=0; i<NoCtrlVars; i++){
  		tempVal=ctrlVals[i];
  		if(!tempVal.equalsIgnoreCase(hhcatVal[i])){
  			result=false;
  			break;
  		}
  	}
  	return result;
  	
  }
}