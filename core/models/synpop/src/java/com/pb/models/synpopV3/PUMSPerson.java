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

import java.util.HashMap;
import java.util.Vector;
// import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, modified on Nov. 15, 2004
 *
 * Create a PUMSPerson object from raw string record of a person in PUMS data.
 */

public class PUMSPerson {

  //raw person record as a string
  protected String pRecord_raw;
  //PUMS person attributes
  protected Vector pattrs;
  //person attributes map, attribute name<--->value pairs
  protected HashMap pAttrsMap;
  //PUMS person record parser
  protected PUMSRecordParser recordParser;
  //data dictionary
  protected DataDictionary dd;

  /**
   * constructor
   * must be defined so that subclass DerivedPerson compiles
   */
  public PUMSPerson(){
  }
  /**
   * Constructor
   * @param pRecord_raw represents a raw string person record
   * @param dd represents a PUMS data dictionary
   */
  public PUMSPerson(String pRecord_raw, DataDictionary dd) {
    this.pRecord_raw=pRecord_raw;
    this.dd=dd;
    recordParser=new PUMSRecordParser(pRecord_raw, dd);
    pattrs=PUMSAttrs.getPersonAttrs();
    makeAttrsMap();
  }

  /**
   * Givan a person attribute name, return its value
   * @param attr represents a person attribute name
   * @return
   */
  public int getPAttr(String attr){
    int attrVal=((Integer)pAttrsMap.get(attr)).intValue();
    return attrVal;
  }
  
  /**
   * get all person attributes
   * @return
   */
  public HashMap getPAttrs(){
  	return pAttrsMap;
  }

  private void makeAttrsMap(){
  	
    String attr;
    int attrVal;
    pAttrsMap=new HashMap();
    
    for(int i=0; i<pattrs.size();i++){
      attr=(String)pattrs.get(i);
      attrVal=recordParser.getPUMSPersDataValue(attr);
      
      pAttrsMap.put(attr,new Integer(attrVal));
    }
  }
  
  //for testing purpose only
  public static void main(String [] args){
  	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
  	PUMSPerson person=new PUMSPerson("P00236170500001103011020030010110000010147050000100001092499901 00000 001301000000000000000000000000000000000000000000 0 0 0 0 0 000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000-00000000000000      0      0      0     0     0     0      0      0       0       329", dd);
  	System.out.println("ok, I am done.");
  }
}