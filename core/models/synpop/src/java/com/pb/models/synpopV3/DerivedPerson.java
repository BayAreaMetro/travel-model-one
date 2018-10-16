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
// import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, modified on Nov. 15, 2004
 */

public class DerivedPerson extends PUMSPerson{

  protected Logger logger;
  protected int pagecat;
  protected int pemploy;
  protected int pstudent;
  protected int phispan;
  protected int padkid;
  protected int ptype;
  

  public DerivedPerson(String pRecord_raw, DataDictionary dd) {
  	super(pRecord_raw, dd);
    logger = Logger.getLogger("com.pb.models.synpopV3");
    setVariables();
  }

  public void setPadkid(int padkid){
    this.padkid=padkid;
  }
  
  /**
   * get derived person attributes, "pagecat", "pemploy", "pstudent", "phispan", "ptype", or "padkid"
   * to get other person attributes, use getPAttr() of super class PUMSPerson
   * other attributes are defined in arc.properties
   * @param attr
   * @return
   */
  public int getPDerivedAttr(String attr){
  	int result=-1;
  	if(attr.equalsIgnoreCase("pagecat"))
  		result=pagecat;
    else if(attr.equalsIgnoreCase("pemploy"))
  		result=pemploy; 
    else if(attr.equalsIgnoreCase("pstudent"))
  		result=pstudent;
    else if(attr.equalsIgnoreCase("phispan"))
  		result=phispan;
    else if(attr.equalsIgnoreCase("ptype"))
  		result=ptype;
    else if(attr.equalsIgnoreCase("padkid"))
  		result=padkid;    
    
  	return result;
  }
  
  /**
   * get person attribute (derived or original)
   */
  public int getPAttr(String attr){
  	int result=getPDerivedAttr(attr);
  	if(result==-1){
  		result=super.getPAttr(attr);
  	}
  	return result;
  }
  
  public void print(){
  	logger.info("PUMS variables");
  	logger.info("-----------------");
  	logger.info("AGE="+getPAttr("AGE"));
  	logger.info("RELATE="+getPAttr("RELATE"));
  	logger.info("ESR="+getPAttr("ESR"));
  	logger.info("GRADE="+getPAttr("GRADE"));
  	logger.info("SERIALNO="+getPAttr("SERIALNO"));
  	logger.info("PNUM="+getPAttr("PNUM"));
  	logger.info("PAUG="+getPAttr("PAUG"));
  	logger.info("DDP="+getPAttr("DDP"));
  	logger.info("SEX="+getPAttr("SEX"));
  	logger.info("WEEKS="+getPAttr("WEEKS"));
  	logger.info("HOURS="+getPAttr("HOURS"));
  	logger.info("RACE1="+getPAttr("RACE1"));
  	logger.info("HISPAN="+getPAttr("HISPAN"));
  	logger.info("MSP="+getPAttr("MSP"));
//  JB added following line for INCTOT
  	logger.info("INCTOT="+getPAttr("INCTOT"));
  	logger.info("POVERTY="+getPAttr("POVERTY"));
  	logger.info("EARNS="+getPAttr("EARNS"));
    logger.info("ECUC="+getPAttr("EDUC"));
    logger.info("OCCCEN5="+getPAttr("OCCCEN5"));
    logger.info("INDNAICS="+getPAttr("INDNAICS"));  	
  	logger.info("-----------------");
  	logger.info("derived variables");
	logger.info("pagecat="+pagecat);
    logger.info("pemploy="+pemploy);
    logger.info("pstudent="+pstudent);
    logger.info("phispan="+phispan);
    logger.info("htype="+ptype);
    logger.info("padkid="+padkid);
  }
  
  private void setVariables(){
    setPagecat();
    setPemploy();
    setPstudent();
    setPhispan();
    setPtype();
  }
  
  private void setPagecat(){
    int age=((Integer)pAttrsMap.get("AGE")).intValue();
    if(age>=0&&age <=5){
      pagecat = 0;
    }else if(age<=11){
      pagecat = 1;
    }else if(age<=15){
      pagecat=2;
    }else if(age<=17){
      pagecat=3;
    }else if(age<=24){
      pagecat=4;
    }else if(age<=34){
      pagecat=5;
    }else if(age<=49){
      pagecat=6;
    }else if(age<=64){
      pagecat=7;
    }else if(age<=79){
      pagecat=8;
    }else{
      pagecat=9;
    }
  }

  private void setPemploy(){
  	
    int esr=((Integer)pAttrsMap.get("ESR")).intValue();
    int pweeks=((Integer)pAttrsMap.get("WEEKS")).intValue();
    int phours=((Integer)pAttrsMap.get("HOURS")).intValue();
    
    // zeros are missing values, assumed to be full time worker
    if((esr==1||esr==2||esr==4||esr==5)){
      if ((pweeks > 30 || pweeks==0) && (phours >= 35 || phours==0)) {
        pemploy = 1;
      }
      else {
        pemploy = 2;
      }
    }else if(esr==0){
      pemploy = 4;
    }else{
      pemploy=3;
    }
  }

  private void setPstudent(){
    int grade=((Integer)pAttrsMap.get("GRADE")).intValue();
    if(grade==0 || grade==1){
      pstudent=3;
    }else if(grade==6||grade==7){
      pstudent=2;
    }else{
      pstudent=1;
    }
  }

  private void setPhispan(){
    int hispan=((Integer)pAttrsMap.get("HISPAN")).intValue();
    if(hispan>2)
      phispan=2;
    else
      phispan=hispan;
  }

  private void setPtype(){
    int page=((Integer)pAttrsMap.get("AGE")).intValue();
    if(page<6 && pstudent==3){
      ptype=8;                       // pre-school
    }else if(page<=15){
      ptype=7;                       // non-driving under 16
    }else if(pemploy==1){
      ptype=1;                       // full-time worker
    }else if(pstudent==2||(page>=20&&pstudent==1)){     
      ptype=3;                       // college student (documentation says this should be ptype 5)
    }else if(pstudent==1){
      ptype=6;                       // driving age student  
    }else if(pemploy==2){
      ptype=2;                       // part-time worker
    }else if(page<65){
      ptype=4;                       // non-working adult (documentation says this should be ptype 3)
    }else{
      ptype=5;                       // non-working senior (documentation says this should be ptype4)
    }
  }
        
}