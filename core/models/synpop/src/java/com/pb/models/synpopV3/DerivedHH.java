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

import java.util.Set;
import java.util.Iterator;
import java.util.Vector;
import org.apache.log4j.Logger;
// import com.pb.morpc.synpop.pums2000.DataDictionary;


/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Modified on Nov. 17, 2004
 * 
 * This class is not generic, derived attribute names are hardcoded.
 * PUMS attributes are in upper case, derived attributes are in lower case
 * 
 * bts - 11/5/12 added hhagecat8
 */

public class DerivedHH extends PUMSHH{

  protected Logger logger;
      
  //derived attributes in a HH
//JB added hinc2
  protected int hinc2;
  protected int hinccat1;
  protected int hinccat2;
  protected int hhagecat;
  protected int hhagecat8;
  protected int hsizecat;
  protected int hfamily;
  protected int hunittype;
  protected int hNOCcat;
  protected int hwrkrcat;
  protected int h0005;
  protected int h0611;
  protected int h1215;
  protected int h1617;
  protected int h1824;
  protected int h2534;
  protected int h3549;
  protected int h5064;
  protected int h6579;
  protected int h80up;
  protected int hworkers;
  protected int hwork_f;
  protected int hwork_p;
  protected int huniv;
  protected int hnwork;
  protected int hretire;
  protected int hpresch;
  protected int hschpred;
  protected int hschdriv;
  protected int htypdwel;
  protected int hownrent;
  protected int hadnwst;
  protected int hadwpst;
  protected int hadkids;

  //Following data items are Drawer related
  //HH drawn status (used in HHDrawer, drawnSta is initialized as false,
  //when a HH is drawn from a PUMS bucket, set drawnSta to true
  protected boolean drawnSta;
  //dimension 1 segment category, HHCat (316 in ARC)
  /*
  protected int D1SCat;
  protected int bucketBin;
  protected int originalPUMA;
  protected int selectedPUMA;
  */

  public DerivedHH(String record_raw, Vector pRecords_raw, DataDictionary dd) {
  	super(record_raw, pRecords_raw, dd);
    logger = Logger.getLogger("com.pb.models.synpopV3");
    setDerivedAttrs();
    //must at the end of DrivedHH constructor
    setPadkidToPerson();
  }
  

  /**
   * Creates a new person object, of the appropriate sub-class
   * 
   * @param pRecord person record from PUMS
   * @param dd data dictionary
   * @return DerivedPerson
   */
  protected DerivedPerson createNewPerson(String pRecord, DataDictionary dd) {
      DerivedPerson p = new DerivedPerson(pRecord, dd); 
      return p; 
  }
  
  /**
   * Given a person sequence number, return a PUMSPerson object
   * @param PNum represents person sequence number, 1-based
   * @return
   */
  public DerivedPerson getPerson(int PNum){
    String PNum_s=""+PNum;
    DerivedPerson person=(DerivedPerson)pRecordsMap.get(PNum_s);
    return person;
  }
  
  public void reset(){
  	drawnSta=false;
  }

  public int [] getControlAttrs(){
    int [] result=new int [ControlVarIndex.getCtrlVarCount()];
    
    // remove the hard coding of the control variable names (dto)
    for(int i=0;i<result.length;++i) {
        String controlVar = ControlVarIndex.getCtrlVarName(i); 
        result[i] = this.getHHAttr(controlVar);
    }
    return result;
  }

  public HHCat getHHCat(){
    return HHCatTable.getHHCat(getControlAttrs());
  }
  
  public int getHHCatID(){
  	return HHCatTable.getHHCatID(HHCatTable.getHHCat(getControlAttrs()));
  }
  
  /**
  * get derived HH attributes
  * to get other person attributes, use getHHAttr() of super class PUMSHH
  * other attributes are defined in arc.properties
  */
  public int getHHDerivedAttr(String varName){
    int result=-1;
//JB added hinc2
    if(varName.equals("hinc2"))
      result=hinc2;
    else if(varName.equals("hinccat1"))
      result=hinccat1;
    else if(varName.equals("hinccat2"))
      result=hinccat2;
    else if(varName.equals("hhagecat"))
      result=hhagecat;
    else if(varName.equals("hhagecat8"))
        result=hhagecat8;
    else if(varName.equals("hsizecat"))
      result=hsizecat;
    else if(varName.equals("hfamily"))
      result=hfamily;
    else if(varName.equals("hunittype"))
      result=hunittype;
    else if(varName.equals("hNOCcat"))
      result=hNOCcat;
    else if(varName.equals("hwrkrcat"))
      result=hwrkrcat;
    else if(varName.equals("h0005"))
      result=h0005;
    else if(varName.equals("h0611"))
      result=h0611;
    else if(varName.equals("h1215"))
      result=h1215;
    else if(varName.equals("h1617"))
      result=h1617;
    else if(varName.equals("h1824"))
      result=h1824;
    else if(varName.equals("h2534"))
      result=h2534;
    else if(varName.equals("h3549"))
      result=h3549;
    else if(varName.equals("h5064"))
      result=h5064;
    else if(varName.equals("h6579"))
      result=h6579;
    else if(varName.equals("h80up"))
      result=h80up;
    else if(varName.equals("hworkers"))
      result=hworkers;
    else if(varName.equals("hwork_f"))
      result=hwork_f;
    else if(varName.equals("hwork_p"))
      result=hwork_p;
    else if(varName.equals("huniv"))
      result=huniv;
    else if(varName.equals("hnwork"))
      result=hnwork;
    else if(varName.equals("hretire"))
      result=hretire;
    else if(varName.equals("hpresch"))
      result=hpresch;
    else if(varName.equals("hschpred"))
      result=hschpred;
    else if(varName.equals("hschdriv"))
      result=hschdriv;
    else if(varName.equals("htypdwel"))
      result=htypdwel;
    else if(varName.equals("hownrent"))
      result=hownrent;
    else if(varName.equals("hadnwst"))
      result=hadnwst;
    else if(varName.equals("hadwpst"))
      result=hadwpst;
    else if(varName.equals("hadkids"))
      result=hadkids;
 
    return result;
  }
  
  /**
   * get HH attributes (derived and original)
   */
  public int getHHAttr(String attr){
  	int result=getHHDerivedAttr(attr);
  	if(result==-1){
  		result=super.getHHAttr(attr);
  	}
    if (result==-1) {
        logger.error("Could not find household attribute: " + attr); 
    }
  	return result;
  }

  /**
   * Set drawnSta (used in PUMSBucket to initialize it, updated in HHDrawer)
   * @param sta represents darwn status
   */
  public void setDrawnSta(boolean sta){
    drawnSta=sta;
  }

  /**
   * Get drawn status of this HH.
   * @return
   */
  public boolean getDrawnSta(){
    return drawnSta;
  }
  
  public void print(){
  	logger.info("PUMS variables");
  	logger.info("-----------------");
  	logger.info("PUMA5="+getHHAttr("PUMA5"));
  	logger.info("SERIALNO="+getHHAttr("SERIALNO"));
  	logger.info("HINC="+getHHAttr("HINC"));
  	logger.info("PERSONS="+getHHAttr("PERSONS"));
  	logger.info("HHT="+getHHAttr("HHT"));
  	logger.info("UNITTYPE="+getHHAttr("UNITTYPE"));
  	logger.info("NOC="+getHHAttr("NOC"));
  	logger.info("BLDGSZ="+getHHAttr("BLDGSZ"));
  	logger.info("TENURE="+getHHAttr("TENURE"));
  	logger.info("-----------------");
  	logger.info("derived variables");
//JB added hinc2
	logger.info("hinc2="+hinc2);
	logger.info("hinccat1="+hinccat1);
    logger.info("hinccat2="+hinccat2);
    logger.info("hhagecat="+hhagecat);
    logger.info("hhagecat8="+hhagecat8);
    logger.info("hsizecat="+hsizecat);
    logger.info("hfamily="+hfamily);
    logger.info("hunittype="+hunittype);
    logger.info("hNOCat="+hNOCcat);
    logger.info("hwrkrcat="+hwrkrcat);
    logger.info("h0005="+h0005);
    logger.info("h0611="+h0611);
    logger.info("h1215="+h1215);
    logger.info("h1617="+h1617);
    logger.info("h1824="+h1824);
    logger.info("h2534="+h2534);
    logger.info("h3549="+h3549);
    logger.info("h5064="+h5064);
    logger.info("h6579="+h6579);
    logger.info("h80up="+h80up);
    logger.info("hworkers="+hworkers);
    logger.info("hwork_f="+hwork_f);
    logger.info("howrk_p="+hwork_p);
    logger.info("huniv="+huniv);
    logger.info("hnwork="+hnwork);
    logger.info("hretire="+hretire);
    logger.info("hpresch="+hpresch);
    logger.info("hschpred="+hschpred);
    logger.info("hschdriv="+hschdriv);
    logger.info("htypdwel="+htypdwel);
    logger.info("hownrent="+hownrent);
    logger.info("hadnwst="+hadnwst);
    logger.info("hadwpst="+hadwpst);
    logger.info("hadkids="+hadkids);
    
  }

  private void setDerivedAttrs(){
//JB added Hinc2
    setHinc2();
    setHinccat1();
    setHinccat2();
    setHhagecat();
    setHhagecat8();
    setHsizecat();
    setHfamily();
    setHunittype();
    setHNOCcat();
    setHwrkrcat();
    setNoInAgeCat();
    setNoInPersonTypeCat();
    setHtypdwel();
    setHownrent();
    setHadnwst();
    setHadwpst();
    
    // add hadkids routine (dto)
    setHadkids();
  
  }
  

// add function to compute the number of adult kids (hadkids) (dto)
  private void setHadkids(){
	    
	    hadkids = 0;
	    
	    // check for a family, adults age 35 to 49 + adults age 50 to 64, then set
	    // hadkids to adults age 18 to 24
	    if (hfamily==2 && (h3549+h5064)>0) hadkids = h1824;
    	    	
  }
  
  
//JB added Hinc2
  private void setHinc2(){
    int hinc=((Integer)hhAttrsMap.get("HINC")).intValue();
    int hunittype=((Integer)hhAttrsMap.get("UNITTYPE")).intValue();
    
    if(hunittype==1||hunittype==2){
    	hinc2=0;
        Set keySet = pRecordsMap.keySet();
        Iterator itr = keySet.iterator();
        String key=new String();
        PUMSPerson person;
      
        while (itr.hasNext()) {
          key = (String) itr.next();
          person=(PUMSPerson)pRecordsMap.get(key);
          hinc2=hinc2+person.getPAttr("INCTOT");
        }
    }else {
      hinc2=hinc;
    }
    
    // zero out negative incomes-gde 10.30.2006
    if (hinc2 < 0) {
        hinc2 = 0; 
    }    
  }

//JB changed to use hinc2 instead of hinc
  private void setHinccat1(){
    if(hinc2<20000){
      hinccat1=1;
    }else if(hinc2<50000){
      hinccat1=2;
    }else if(hinc2<100000){
      hinccat1=3;
    }else{
      hinccat1=4;
    }
  }

//JB changed to use hinc2 instead of hinc
  private void setHinccat2(){
    if(hinc2<10000){
      hinccat2=1;
    }else if(hinc2<20000){
      hinccat2=2;
    }else if(hinc2<30000){
      hinccat2=3;
    }else if(hinc2<40000){
      hinccat2=4;
    }else if(hinc2<50000){
      hinccat2=5;
    }else if(hinc2<60000){
      hinccat2=6;
    }else if(hinc2<75000){
      hinccat2=7;
    }else if(hinc2<100000){
      hinccat2=8;
    }else{
      hinccat2=9;
    }
  }

  private void setHhagecat(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    DerivedPerson person;
    //int wrkrcount=0;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(DerivedPerson)pRecordsMap.get(key);
//JB replaced next line, so that GQ person is treated as householder
//      if(person.getPAttr("RELATE")==1){
        if(person.getPAttr("RELATE")==1||person.getPAttr("RELATE")==22||person.getPAttr("RELATE")==23){
            if(person.getPAttr("AGE")<65)
        		hhagecat=1;
        	else
        		hhagecat=2;
        }      	
    }
  }
  
  private void setHhagecat8(){

	    Set keySet = pRecordsMap.keySet();
	    Iterator itr = keySet.iterator();
	    String key=new String();
	    DerivedPerson person;
	    //int wrkrcount=0;

	    while (itr.hasNext()) {
	        key = (String) itr.next();
	        person=(DerivedPerson)pRecordsMap.get(key);
	        if(person.getPAttr("RELATE")==1||person.getPAttr("RELATE")==22||person.getPAttr("RELATE")==23){
	            if(person.getPAttr("AGE")<25) {
	            	hhagecat8=1;
	            } else if(person.getPAttr("AGE")<35) {
	            	hhagecat8=2;
	            } else if(person.getPAttr("AGE")<45) {
	            	hhagecat8=3;
	            } else if(person.getPAttr("AGE")<55) {
	            	hhagecat8=4;
	            } else if(person.getPAttr("AGE")<65) {
	            	hhagecat8=5;
	            } else if(person.getPAttr("AGE")<75) {
	            	hhagecat8=6;
	            } else if(person.getPAttr("AGE")<85) {
	            	hhagecat8=7;
	            } else {
	            	hhagecat8=8;
	            }
	        }
	    }
	  }

  private void setHsizecat(){
    int hsize=((Integer)hhAttrsMap.get("PERSONS")).intValue();
    if(hsize==0){
      hsizecat = 1;
    }else if(hsize<5){
      hsizecat = hsize;
    }else{
      hsizecat = 5;
    }
  }

  private void setHfamily(){

    int hht=((Integer)hhAttrsMap.get("HHT")).intValue();
//JB  if(hht<=3)
      if((hht>=1)&&(hht<=3))
      hfamily=2;
    else
      hfamily=1;
  }

  private void setHunittype(){
    int hsize=((Integer)hhAttrsMap.get("PERSONS")).intValue();
    int unittype=((Integer)hhAttrsMap.get("UNITTYPE")).intValue();
    if(hsize==0)
      hunittype=3;
    else
      hunittype=unittype;
  }

  private void setHNOCcat(){
    int noc=((Integer)hhAttrsMap.get("NOC")).intValue();
    if(noc>=1)
      hNOCcat=1;
    else
      hNOCcat=0;
  }

  private void setHwrkrcat(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    PUMSPerson person;
    int wrkrcount=0;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(PUMSPerson)pRecordsMap.get(key);
        if(person.getPAttr("ESR")==1||person.getPAttr("ESR")==2||person.getPAttr("ESR")==4||person.getPAttr("ESR")==5)
          wrkrcount++;
    }

    hworkers=wrkrcount;

    if(wrkrcount>=3)
      hwrkrcat = 3;
    else
      hwrkrcat=wrkrcount;
  }
  
  private void setNoInAgeCat(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    PUMSPerson person;
    int age;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(PUMSPerson)pRecordsMap.get(key);
        age=person.getPAttr("AGE");
        if(age<=5){
          h0005++;
        }else if(age<=11){
          h0611++;
        }else if(age<=15){
          h1215++;
        }else if(age<=17){
          h1617++;
        }else if(age<=24){
          h1824++;
        }else if(age<=34){
          h2534++;
        }else if(age<=49){
          h3549++;
        }else if(age<=64){
          h5064++;
        }else if(age<=79){
          h6579++;
        }else{
          h80up++;
        }
    }
  }

  private void setNoInPersonTypeCat(){

    Set keySet =pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    DerivedPerson person;
    int ptype;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(DerivedPerson)pRecordsMap.get(key);
        ptype=person.getPDerivedAttr("ptype");
        if(ptype==1){
          hwork_f++;
        }else if(ptype==2){
          hwork_p++;
        }else if(ptype==3){
          huniv++;
        }else if(ptype<=4){
          hnwork++;
        }else if(ptype==5){
          hretire++;
        }else if(ptype==6){
          hschdriv++;
        }else if(ptype==7){
          hschpred++;
        }else if(ptype==8){
          hpresch++;
        }
    }
  }

  private void setHtypdwel(){
    int bldgsz=((Integer)hhAttrsMap.get("BLDGSZ")).intValue();
    if(bldgsz==2){
      htypdwel = 1;
//JB}else if(bldgsz==1){
    }else if((bldgsz==1)||(bldgsz==10)){
      htypdwel=3;
    }else{
      htypdwel = 2;
    }
  }

  private void setHownrent(){
    int tenure=((Integer)hhAttrsMap.get("TENURE")).intValue();
    if(tenure==1||tenure==2){
      hownrent = 1;
    }else{
      hownrent = 2;
    }
  }

  private void setHadnwst(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    PUMSPerson person;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(PUMSPerson)pRecordsMap.get(key);
        if((person.getPAttr("ESR")==3||person.getPAttr("ESR")==6)&&person.getPAttr("GRADE")>0)
          hadnwst++;
    }
  }

  private void setHadwpst(){

    Set keySet = pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    PUMSPerson person;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(PUMSPerson)pRecordsMap.get(key);
        if((person.getPAttr("ESR")==1||person.getPAttr("ESR")==2||person.getPAttr("ESR")==4||person.getPAttr("ESR")==5)&&person.getPAttr("GRADE")>0)
          hadwpst++;
    }
  }

  private void setPadkidToPerson(){

    Set keySet =pRecordsMap.keySet();
    Iterator itr = keySet.iterator();
    String key=new String();
    DerivedPerson person;
    int h3564=h3549+h5064;

    while (itr.hasNext()) {
        key = (String) itr.next();
        person=(DerivedPerson)pRecordsMap.get(key);
        if((person.getPDerivedAttr("pagecat")==4)&&hfamily==2&&h3564>0&&h1824>0)
          person.setPadkid(1);
        else
          person.setPadkid(2);
    }
  }
  

}