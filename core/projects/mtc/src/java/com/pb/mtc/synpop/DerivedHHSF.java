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

import com.pb.models.synpopV3.ControlVarIndex;
import com.pb.models.synpopV3.DataDictionary;
import com.pb.models.synpopV3.DerivedHH; 
import com.pb.models.synpopV3.DerivedPerson;
import com.pb.models.synpopV3.HHCat;
import com.pb.models.synpopV3.HHCatTable;
import com.pb.models.synpopV3.PUMSPerson;
import com.pb.models.synpopV3.PropertyParser;

import java.util.Set;
import java.util.Iterator;
import java.util.Vector;
import org.apache.log4j.Logger;



/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Modified on Nov. 17, 2004
 * 
 * This class is not generic, derived attribute names are hardcoded.
 * PUMS attributes are in upper case, derived attributes are in lower case
 */

public class DerivedHHSF extends DerivedHH{
      
  //derived attributes in a HH
  protected int hmultiunit; 
  protected int hminority;
  protected int h0004;
  protected int h0511;
  protected int hworkersFt;
  protected int hworkersPt;

  
  public DerivedHHSF(String record_raw, Vector pRecords_raw, DataDictionary dd) {
  	super(record_raw, pRecords_raw, dd);
    logger = PropertyParser.getLogger();
    
    // set the derived attributes specific to SF
    setDerivedSfAttrs();
  }
  
  /**
   * Given a person sequence number, return a PUMSPerson object
   * @param PNum represents person sequence number, 1-based
   * @return
   */
  public DerivedPersonSF getPerson(int PNum){
    String PNum_s=""+PNum;
    DerivedPersonSF person=(DerivedPersonSF)pRecordsMap.get(PNum_s);
    return person;
  }
  
  /**
   * Creates a new person object, of the appropriate sub-class
   * 
   * @param pRecord person record from PUMS
   * @param dd data dictionary
   * @return DerivedPerson
   */
  protected DerivedPersonSF createNewPerson(String pRecord, DataDictionary dd) {
      DerivedPersonSF p = new DerivedPersonSF(pRecord, dd); 
      return p; 
  }
  
  /**
  * get derived HH attributes
  * to get other person attributes, use getHHAttr() of super class PUMSHH
  * other attributes are defined in arc.properties
  */
  public int getHHDerivedAttr(String varName){
    int result=-1;
    if(varName.equals("hmultiunit"))
      result=hmultiunit;
    else if(varName.equals("hminority"))
      result=hminority; 
    else if(varName.equals("h0004"))
        result=h0004;
    else if(varName.equals("h0511"))
        result=h0511;
    else if(varName.equals("hworkersFt"))
        result=hworkersFt;
    else if(varName.equals("hworkersPt"))
        result=hworkersPt;
    else 
        result=super.getHHDerivedAttr(varName); 
    
    return result;
  }
  
  
  public void print(){
    super.print(); 
    logger.info("hmultiunit="+hmultiunit);
    logger.info("hminority="+hminority);
    logger.info("h0004="+h0004);
    logger.info("h0511="+h0511);   
    logger.info("hworkerFt="+hworkersFt);
    logger.info("hworkersPt="+hworkersPt);
    
  }

  private void setDerivedSfAttrs(){
    setHmultiunit();
    setHminority();
    setFullPartTime();
    setAlternativeAgeCat();
  }
  

  private void setAlternativeAgeCat(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    PUMSPerson person;
    int age;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(PUMSPerson)pRecordsMap.get(key);
        age=person.getPAttr("AGE");        
        // altnernate definition
        if(age<=4) {
            h0004++;
        }else if (age<=11) {
            h0511++;
        }
    }
  }

    
  private void setFullPartTime(){
      Set keySet =pRecordsMap.keySet();
      Iterator itr = keySet.iterator();
      String key=new String();
      DerivedPersonSF person;
      int pemploySf;

      while (itr.hasNext()) {
          key = (String) itr.next();
          person=(DerivedPersonSF)pRecordsMap.get(key);
          pemploySf=person.getPDerivedAttr("pemploySf");
          if(pemploySf==1 || pemploySf==3){
            hworkersFt++;
          }else if(pemploySf==2 || pemploySf==4){
            hworkersPt++;
          }
      }
  }
  
    // gde 10.6.2006 added
    // 0 - single family detached, single family attached
    // 1 - building wiht 2+ apartments, mobile home, boat, rv, van, etc.  
    private void setHmultiunit() {
        int bldgsz = ((Integer) hhAttrsMap.get("BLDGSZ")).intValue();
        if (bldgsz==2 || bldgsz==3) {
            hmultiunit = 0;
        } else {
            hmultiunit = 1;
        }
    }

    // gde 10.8.2006 added
    // 0 - White Alone, Not Hispanic
    // 1 - Minority
    private void setHminority() {
        Set keySet = pRecordsMap.keySet();
        Iterator itr = keySet.iterator();
        String key = new String();
        DerivedPersonSF person;

        while (itr.hasNext()) {
            key = (String) itr.next();
            person = (DerivedPersonSF) pRecordsMap.get(key);
            if (person.getPAttr("RELATE") == 1
                    || person.getPAttr("RELATE") == 22
                    || person.getPAttr("RELATE") == 23) {
                if (person.getPAttr("RACE1") == 1 && person.getPAttr("HISPAN") == 1)
                    hminority = 0;
                else
                    hminority = 1;
            }
        }
    }
}