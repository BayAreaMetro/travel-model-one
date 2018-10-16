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
import org.apache.log4j.Logger;
// import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, modified on Nov. 15, 2004
 * 
 * Related assistant classes: PUMSAttrs, PUMSPerson, DerivedPerson
 * 
 */

public class PUMSHH {

  protected Logger logger = Logger.getLogger("com.pb.models.synpopV3");
  //raw string HH record
  protected String record_raw;
  //raw person records in this HH
  protected Vector pRecords_raw;
  //HH attributes, from property file
  protected Vector hhattrs;
  
  //HH attribute name<--->attribute value 
  protected HashMap hhAttrsMap;
  //persons map, PNum<--->DerivedPerson
  protected HashMap pRecordsMap;
  
  protected DataDictionary dd;
  protected PUMSRecordParser recordParser;
  
  /**
   * default constructor.
   * Must be defined so that subclass DerivedHH compiles
   */
  public PUMSHH(String record_raw, Vector pRecords_raw, DataDictionary dd) {

    this.record_raw=record_raw;
    this.pRecords_raw=pRecords_raw;
    this.dd=dd;
    
    //get HH attribute names
    hhattrs=PUMSAttrs.getHHAttrs();

    //instantiate HH record parser
    recordParser=new PUMSRecordParser(record_raw, dd);

    makeHHAttrsMap();
    makePRecordsMap();
  }

  /**
   * Given a HH attribute name, return its variable
   * @param attr represents HH attribute name
   * @return
   */
  public int getHHAttr(String attr){
    int attrVal=((Integer)hhAttrsMap.get(attr)).intValue();
    return attrVal;
  }
  
  /**
   * get all HH attributes.
   * @return
   */
  public HashMap getHHAttrs(){
  	return hhAttrsMap;
  }

  /**
   * Given a person sequence number, return a PUMSPerson object
   * @param PNum represents person sequence number, 1-based
   * @return
   */
  public PUMSPerson getPerson(int PNum){
    String PNum_s=""+PNum;
    PUMSPerson person=(PUMSPerson)pRecordsMap.get(PNum_s);
    return person;
  }
  
  /**
   * get all persons in a HH
   * @return
   */
  public HashMap getPersons(){
  	return pRecordsMap;
  }

  /**
   * Return number of persons in this HH record.
   * @return
   */
  public int getNoOfPersons(){
    return pRecordsMap.size();
  }

  /**
   * make hhAttrsMap
   * attr name----attr value (Integer)
   */
  private void makeHHAttrsMap(){
  	
    hhAttrsMap=new HashMap();
    String attr;

    int attrVal;
    for(int i=0; i<hhattrs.size(); i++){
      attr=(String)hhattrs.get(i);
      attrVal=recordParser.getPUMSHHDataValue(attr);
      hhAttrsMap.put(attr,new Integer(attrVal));
    }
  }

  /**
   * make pRecordsMap
   * PNum----DerivedPerson
   */
  private void makePRecordsMap(){
  	
    //number of persons in HH record
    int NoPersons=recordParser.getPUMSHHDataValue("PERSONS");
    //number of person records following this HH record
    int personRecords=pRecords_raw.size();
    
    String pRecord;
    int PNum;
    pRecordsMap=new HashMap();

    if(personRecords!=NoPersons){
      logger.error("PERSONS in HH doesn't match person records following this hh record");
    }else{
      for(int i=0; i<NoPersons; i++){
        //get a person record
        pRecord=(String)pRecords_raw.get(i);
        //create a DerivedPerson object
        PUMSPerson dperson=createNewPerson(pRecord, dd);
        //get a person record parser
        recordParser=new PUMSRecordParser(pRecord, dd);
        //get PNum, PNum 1-based
        PNum=recordParser.getPUMSPersDataValue("PNUM");
        //add this person record to pDRecordsMap
        pRecordsMap.put(PNum+"",dperson);
      }
    }
  }
  
  /**
   * Creates a new person object, of the appropriate sub-class
   * 
   * @param pRecord person record from PUMS
   * @param dd data dictionary
   * @return PUMSPerson
   */
  protected PUMSPerson createNewPerson(String pRecord, DataDictionary dd) {
      PUMSPerson p = new PUMSPerson(pRecord, dd); 
      return p; 
  }
  
  public static void main(String [] args){
  	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
  	Vector pvector=new Vector();
  	pvector.add("P00236170100002201000010440010110000010147010100100009092499901200000 00470100000010000000000000000000000000000000000020202020202022000004000000000000000100047001800470702170156099971560999701020040001000000010077023      620047-1011101052045004400000000000000000000000000000000000000000000000000004400000044000329");
  	pvector.add("P00236170200001702000320400010110000010147010100100006092499901200000 0047010000001000000000000000000000000000000000002020202020202200000400000000000000060000000000000000000000000000000000000000000000000223241076905617Z   423037-2012101016020000600000000000000000000000000000000000000000000000000000600000006000329");
  	pvector.add("P00236170300002203000010200010110000010147050600100011092499901200000 00470100000010000000000000000000000000000000000020202020202022000004000000000000000100047001800470702170156099971560999701020040001000000010077023      626047-2061101052035001700000000000000000000000000000000000000000000000000001700000017000329");
  	pvector.add("P00236170400001903011020150010110000010147050600205004092499901200000 00470100000010000000000000000000000000000000000020202020 0 022000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000-0000000000000000000000000000000000000000000000000000000000000000000000000000000000329");
  	pvector.add("P00236170500001103011020030010110000010147050000100001092499901 00000 001301000000000000000000000000000000000000000000 0 0 0 0 0 000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000-00000000000000      0      0      0     0     0     0      0      0       0       329");
  	PUMSHH hh=new PUMSHH("H002361751335001001301015601560999799972270    2030172029    2027399338    8305335709    8268343867420022050000030020613040301010103030202000360000001002000000100480020 0     0 0     0 0000 0    0    0  0 0     0100020502020330000000001079701421142020006700000067000", pvector, dd); 
  	System.out.println("ok, I am done.");
  }
}