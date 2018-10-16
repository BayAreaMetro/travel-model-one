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

// removed morpc dependency (dto)
//import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.2, modified on Nov. 17, 2004
 * 
 * Use this class to parse PUMS HH record.
 */

public class PUMSRecordParser {

  protected String pumsDir;
  protected String pumsDD;
  protected DataDictionary dd;
  protected String record;
  
  /**
   * constructor
   * @param record represents a raw record string
   * @param dd represents a data dictionary
   */
  public PUMSRecordParser(String record, DataDictionary dd){
  	this.record=record;
  	this.dd=dd;
  	pumsDir=PropertyParser.getPropertyByName("pums.directory");
  	pumsDD=PropertyParser.getPropertyByName("pums.dictionary");
  }

  /**
   * Given a string PUMSHH record and a PUMSHH variable name, return value of this variable
   * @param PUMSVariable represents PUMSHH variable name
   * @return
   */
  public int getPUMSHHDataValue(String PUMSVariable) {
      int startCol=dd.getStartCol(dd.HHAttribs, PUMSVariable);
      int endCol=dd.getLastCol(dd.HHAttribs, PUMSVariable);
      String temp = record.substring(startCol,endCol);

      String emptyStr=" ";
      for(int i=0; i<endCol-startCol-1; i++)
        emptyStr=emptyStr+" ";

      if (temp.equals(emptyStr)) return 0;
      return Integer.parseInt(temp);
  }
  
  /**
   * Given a string PUMS Person record and a PUMS Person variable name, return value of this variable
   * @param PUMSVariable represents PUMS Person variable name
   * @return
   */
  public int getPUMSPersDataValue(String PUMSVariable) {

    int startCol=dd.getStartCol(dd.PersAttribs, PUMSVariable);
    int endCol=dd.getLastCol(dd.PersAttribs, PUMSVariable);
    String temp = record.substring(startCol,endCol);

    String emptyStr=" ";
    for(int i=0; i<endCol-startCol-1; i++)
      emptyStr=emptyStr+" ";

      if (temp.equals(emptyStr)) return 0;
      return Integer.parseInt(temp);
  }
  
  /**
   * Given a PUMS record, return its RECTYPE
   * @param s represents a PUMS record
   * @return
   */
  public String getPUMSRecType() {
      return record.substring(dd.getStartCol(dd.HHAttribs, "RECTYPE"),
          dd.getLastCol(dd.HHAttribs, "RECTYPE"));
  }
  
  /**
   * if recrod is a HH record
   * @return
   */
  public boolean isHHRecord(){
  	boolean result=false;
  	String recordType=getPUMSRecType();
  	if(recordType.equalsIgnoreCase("H"))
  		result=true;
  	return result;
  }

  /**
   * get PUMS data dictionary.
   * @return
   */
  public DataDictionary getPUMSDataDictionary(){
    return dd;
  }
  
  /**
   * return raw record string.
   * @return
   */
  public String getPUMSRecord(){
  	return record;
  }
}