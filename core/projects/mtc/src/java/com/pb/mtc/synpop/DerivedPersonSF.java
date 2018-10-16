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
package com.pb.mtc.synpop;

import com.pb.models.synpopV3.DataDictionary;
import com.pb.models.synpopV3.DerivedPerson; 

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Greg Erhardt
 * @version 2.0, modified on Oct. 2, 2007
 */

public class DerivedPersonSF extends DerivedPerson{
  
  protected int praceSf; 
  protected int pemploySf; 
  

  public DerivedPersonSF(String pRecord_raw, DataDictionary dd) {
  	super(pRecord_raw, dd);
    setVariables();
  }

  
  /**
   * get derived person attributes
   * to get other person attributes, use getPAttr() of super class PUMSPerson
   * other attributes are defined in arc.properties
   * @param attr
   * @return
   */
  public int getPDerivedAttr(String attr){
  	int result=-1;
    if(attr.equalsIgnoreCase("praceSf"))
        result=praceSf;
    else if(attr.equalsIgnoreCase("pemploySf"))
        result=pemploySf;
    else 
        result=super.getPDerivedAttr(attr); 
    
  	return result;
  }
    
  public void print(){
    super.print(); 
    logger.info("praceSf="+praceSf);
    logger.info("pemploySf="+pemploySf);
  }
  
  private void setVariables(){
    setPraceSf();
    setPemploySf();
  }
  

  /**
    * 1 . White alone
    * 2 . Black or African American alone
    * 3 . American Indian alone
    * 4 . Alaska Native alone
    * 5 . American Indian and Alaska Native tribes specified, and American Indian or Alaska Native,  not specified, and no other races
    * 6 . Asian alone
    * 7 . Native Hawaiian and Other Pacific Islander alone
    * 8 . Some other race alone
    * 9 . Two or more major race groups
    * 10  Hispanic, all races
  */
  private void setPraceSf() {

      int race1=((Integer)pAttrsMap.get("RACE1")).intValue();
      int hispan=((Integer)pAttrsMap.get("HISPAN")).intValue();
 
      if (hispan==1) {
          praceSf = race1;
      } else {
          praceSf = 10; 
      }
      
  }
  
  /**
  * 1 'full time'
  * 2 'part time'
  * 3 'full time self-employed'
  * 4 'part time self-employed'
  * 5 'not employed'/
  */
  private void setPemploySf() {

      int esr=((Integer)pAttrsMap.get("ESR")).intValue();
      int clwkr=((Integer)pAttrsMap.get("CLWKR")).intValue();
      int phours=((Integer)pAttrsMap.get("HOURS")).intValue();
      
      
      if((esr==1||esr==2||esr==4||esr==5)){   // employed 
        if (phours >= 35) {                   // full time
          if (clwkr==6 || clwkr==7) {         // self employed
              pemploySf = 3;          
          } else {                            // not self-employed
              pemploySf = 1;
          }        
        } else {                              // part time
          if (clwkr==6 || clwkr==7) {         // self employed
              pemploySf = 4;          
          } else {                            // not self-employed
              pemploySf = 2;
          }       
        }      
      } else{                                  // not employed
        pemploySf=5;
      }
  }
  
}