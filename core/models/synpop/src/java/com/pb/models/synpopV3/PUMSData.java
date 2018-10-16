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

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.Iterator;
import java.util.Set;
import java.util.Vector;
import org.apache.log4j.Logger;
// import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 * @version 1.1, Nov. 14, 2004
 * 
 * Main class for processing PUMS data.  Related assistant classes are:
 * PUMSRecordParser, PUMSHH, and DerivedHH
 */

public class PUMSData {
	
	protected boolean logDebug=true;
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    protected String pumsDirectory;
    protected String pumsFile;
    //Derived HH vector, 1st dimension is PUMA, 2nd dimension is HHCat, for ARC [32][316]
    //protected Vector pumsHHs;
    protected Vector [][] pumsHHs;
    protected int hhCount=0;
    protected int recCount=0;
    protected DataDictionary dd;
    protected TAZtoPUMAIndex pumaIndex;
    protected PUMSRecordParser recordParser;
    protected DerivedHHFactory hhFactory; 
    
    protected int NoPUMAs;
    protected int NoHHCats;
    
    protected boolean useGQrecords; 
        
    public PUMSData(DataDictionary dd, TAZtoPUMAIndex pumaIndex, DerivedHHFactory hhFactory) {
    	this.dd=dd;
    	this.pumaIndex=pumaIndex;
        this.hhFactory = hhFactory; 
    	NoPUMAs=pumaIndex.getNoPUMAs();
    	NoHHCats=HHCatTable.getHHCatCount();
    	//pums directory from property file
    	pumsDirectory=PropertyParser.getPropertyByName("pums.directory");
    	//pums data file from property file
    	pumsFile=PropertyParser.getPropertyByName("pums.data");
        //determine whether or not to used GQ records
        useGQrecords = false;
        if(PropertyParser.getPropertyByName("pums.useGQRecords").equalsIgnoreCase("true")) useGQrecords = true;
        
    	//read PUMS data
    	readData(pumsDirectory+pumsFile);
    }

    /**
     * get PUMS hhs by All
     * @return
     */
    public Vector [][] getPUMSHHs(){
      return pumsHHs;
    }
    
    /**
     * get PUMS hhs by PUMA index
     * @param pumaIndex is 0-based
     * @return
     */
    public Vector [] getPUMSHHsByPUMAIndex(int pumaIndex){
    	return pumsHHs[pumaIndex];
    }
 
    /**
     * get PUMS hhs by PUMA
     * @param PUMA represent a PUMA
     * @return an array of vector of Derived HHs (size of vector array=number of HHCats, for ARC=316)
     */
    public Vector [] getPUMSHHsByPUMA(int PUMA){
    	return pumsHHs[pumaIndex.getPUMAArrayIndex(PUMA)];
    }
     
    /**
     * get a vector of PUMSHHs by PUMA index and by HHCat ID
     * @param pumaIndex represents a PUMA index, 0-based
     * @param hhcatID represents a HHCat ID, 1-based
     * @return
     */
    public Vector getPUMSHHsByPUMAIndexHHCatID(int pumaIndex, int hhcatID){
    	return pumsHHs[pumaIndex][hhcatID-1];
    }
        
    /**
     * get PUMS hhs by PUMA and by HHCat
     * @param PUMA represents a PUMA
     * @param hhcat represents a HHCat object
     * @return a vector of HHs
     */
    public Vector getPUMSHHsByPUMAByHHCat(int PUMA, HHCat hhcat){	
    	//importatn HHCat ID in HHCatTable is 1-based
    	return pumsHHs[pumaIndex.getPUMAArrayIndex(PUMA)][HHCatTable.getHHCatID(hhcat)-1];
    }
    
    /**
     * get PUMS data record count
     * @return
     */
    public int getPUMSRecCount() {
        return recCount;
    }
    
    /**
     * get PUMS hh count by ALL
     * @return
     */
    public int getPUMSHHCount() {
        return hhCount;
    }
    
    /**
     * get PUMS hh count by PUMA Index
     * @param pumaIndex represents PUMA index, 0-based
     * @return
     */
    public int getPUMSHHCountByPUMAIndex(int pumaIndex){
    	Vector [] v=pumsHHs[pumaIndex];
    	int result=0;
    	for(int i=0; i<v.length; i++){
    		result+=v[i].size();
    	}
    	return result;
    }
    
    /**
     * get PUMS hh count by PUMA
     * @param PUMA
     * @return
     */
    public int getPUMSHHCountByPUMA(int PUMA){
    	return getPUMSHHCountByPUMAIndex(pumaIndex.getPUMAArrayIndex(PUMA));
    }
    
    /**
     * get PUMS hh count by PUMA index and by HHCat ID
     * @param pumaIndex represents PUMA index, 0-based
     * @param hhcatID represents HHCat ID, 1-based
     * @return
     */
    public int getPUMSHHCountByPUMAIndexByHHCatID(int pumaIndex, int hhcatID){
    	return pumsHHs[pumaIndex][hhcatID-1].size();
    }

    /**
     * get PUMS hh count by PUMA and by HHCat
     * @param PUMA represents PUMA
     * @param hhcat represents a HHCat object
     * @return
     */
    public int getPUMSHHCountByPUMAByHHCat(int PUMA, HHCat hhcat){
    	int hhcatID=HHCatTable.getHHCatID(hhcat);
    	return getPUMSHHCountByPUMAIndexByHHCatID(PUMA, hhcatID);
    }
    
    /** 
     * builds pums data needed for the forecast controls
     * @return an array of longs used by ForecastTazData.java
     */
    public long [] generateForecastControlData(){
    	
    	long [] forecastControlData;
    	
        String key;
        long householdersSixtyFiveUp = 0;
    	long populationSixtyFiveUp = 0;
    	long householdersLessSixtyFiveWithKidsUnder17 = 0;
    	long childrenUnder14 = 0;
    	long totalPersons = 0;
    	long totalHouseholds = 0;
    	
    	// loop through the households
    	for(int i=0;i<this.NoPUMAs;++i){
    		for(int j=0;j<this.NoHHCats;++j){
    			for(int k=0;k<this.pumsHHs[i][j].size();++k){
    				
    				// create a Derived household
        			DerivedHH tempHousehold = (DerivedHH) this.pumsHHs[i][j].get(k);
        			int householderAge = tempHousehold.getHHAttr("hhagecat");
        			int family = tempHousehold.getHHAttr("hfamily");
        			int kidsLess17 = tempHousehold.getHHAttr("h0005") + tempHousehold.getHHAttr("h0005") +
        			                 tempHousehold.getHHAttr("h0611") + tempHousehold.getHHAttr("h1215") + 
        			                 tempHousehold.getHHAttr("h1617");
        				
        			if(householderAge==2) householdersSixtyFiveUp++;
        			if(householderAge==1 && family==2 && kidsLess17>0) householdersLessSixtyFiveWithKidsUnder17++;
        			
                    // move through the people in the household
        			totalHouseholds++;
        			Set keySet = tempHousehold.pRecordsMap.keySet();
        			Iterator iterator = keySet.iterator();
        			PUMSPerson person;
        			
        			while (iterator.hasNext()){
        				key = (String) iterator.next();
        				person = (PUMSPerson) tempHousehold.pRecordsMap.get(key);
        				int personAge = person.getPAttr("AGE");
        				
        				// person logic
        				totalPersons++;
        				if(personAge<14) childrenUnder14++;
        				if(personAge>=65) populationSixtyFiveUp++;
        			}
    				
    			} // k
    			
    		} // j
    			
    	} // i
    	
    	// put each of the variables in the array
    	forecastControlData = new long[6];
    	forecastControlData[0] = householdersSixtyFiveUp;
    	forecastControlData[1] = populationSixtyFiveUp;
    	forecastControlData[2] = householdersLessSixtyFiveWithKidsUnder17;
    	forecastControlData[3] = childrenUnder14;
    	forecastControlData[4] = totalPersons;
    	forecastControlData[5] = totalHouseholds;
    	
    	return forecastControlData;
    	
    }

    /**
     * Read PUMS data file, populate pumsHHs
     * @param fileName represents the location of PUMS data file
     */
    private void readData(String fileName) {
    
      pumsHHs=new Vector[NoPUMAs][NoHHCats];
      //initialize pumsHHs array
      for(int i=0; i<NoPUMAs; i++){
      	for(int j=0; j<NoHHCats; j++){
      		pumsHHs[i][j]=new Vector();
      	}
      }
      
      String currentHHRecord = new String();
      String s=new String();
      Vector personRecords=new Vector();
      PUMSHH hh;
      int persons = 0;
      int personsProcessed=0;
      
      int puma=-1;
      int pIndex=-1;
      int hhcat_id=-1;
      int counter=0;

      try {
        BufferedReader in = new BufferedReader(new FileReader(fileName));
        while ( (s = in.readLine()) != null) {
          recCount++;
          recordParser=new PUMSRecordParser(s,dd);
          //if a H record
          if (recordParser.isHHRecord()) {
            //add 1 to hhCount
            hhCount++;
            //get number of persons in HH
            persons = recordParser.getPUMSHHDataValue("PERSONS");
            //set current line as current HH record
            currentHHRecord = s;
            //set number of processed persons to 0
            personsProcessed=0;
            //create a new person record vector to store person records of this HH
            personRecords=new Vector();
            
          }
          //if a P record
          else {
            //add current line to person record vector
            personRecords.add(s);
            //add 1 to number of processed persons
            personsProcessed++;
            //if number of processed persons=number of persons in this HH
            if(persons==personsProcessed){
              //create a new DrivedHH
              DerivedHH dhh=hhFactory.createDerivedHH(currentHHRecord, personRecords, dd);
       
              //add DerivedHH to HH vector if hh is non-GQ, othewise discard it
              //**************allow the option of using GQ records based on control file property**************
              if(dhh.getHHDerivedAttr("hunittype")==0 || useGQrecords){
              	puma=dhh.getHHAttr("PUMA5");
              	hhcat_id=dhh.getHHCatID(); 	
              	pIndex=pumaIndex.getPUMAArrayIndex(puma);
              	//importatn hhcat ID is 1-based, must minus 1 here
              	//if PUMA not found in PUMA array, then discard current PUMS record
              	if(pIndex!=-1){
              		pumsHHs[pIndex][hhcat_id-1].add(dhh);
              		counter++;
              	}
              }
            }
          }
        }
      }
      catch (Exception e) {
        logger.info("IO Exception caught reading PUMS data file: " +fileName);
        e.printStackTrace();
        System.exit(1); 
      }
      
      if(logDebug){
	      logger.info(getPUMSHHCount() + " PUMS households read from " +getPUMSRecCount() + " PUMS records.");
	      logger.info("PUMS households in study area:"+counter);
      }
    }

    // for testing purpose only
    // successfully tested on May 5, 2005
    public static void main(String[] args) {
      	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
        TAZtoPUMAIndex pumaIndex=new TAZtoPUMAIndex(new TableDataReader("conversion"),false);
      	DerivedHHFactory factory = new DerivedHHFactory();         
        PUMSData pums = new PUMSData(dd, pumaIndex, factory);
        DerivedHH hh;
        Vector [][] hhs=pums.getPUMSHHs();
        logger.info("ok, I am done.");
    }
}
