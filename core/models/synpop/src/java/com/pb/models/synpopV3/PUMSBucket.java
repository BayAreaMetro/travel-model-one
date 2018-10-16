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
import java.util.Random;
import org.apache.log4j.Logger;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 * March 28, 2005
 */

public class PUMSBucket {
	
  protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
  //PUMA of this bucket
  protected int PUMA;
  //HHCat of this bucket
  protected HHCat hhcat;
  //HHCat ID of this bucket
  protected int hhcatID;
  //number of bins
  protected int NBucketBins;
  //????????????????????
  protected int NHHs;
  //PUMS bucket bins in this bucket
  protected PUMSBucketBin [] bins;
  
  /**
   * Constructor.
   * @param pumsdata represents PUMS data
   * @param PUMA represents a PUMA
   * @param hhcatID represents a HH category ID in HHCatTable, 1-based
   */
  public PUMSBucket(PUMSData pumsdata, int PUMA, int hhcatID, Random randomGenerator) {

    this.PUMA=PUMA;
    this.hhcatID=hhcatID;
    //get number of bins from arc.properties
    NBucketBins=(new Integer(PropertyParser.getPropertyByName("NBucketBins"))).intValue();

    bins=new PUMSBucketBin[NBucketBins];

    //given hhcat ID, get HHCat
    hhcat=HHCatTable.getHHCat(hhcatID);

    setBins(pumsdata, hhcat, randomGenerator);
  }
  
  /**
   * Constructor.
   * @param pumsdata represents PUMS data
   * @param PUMA represents a PUMA
   * @param hhcat represents a HHCat object
   */
  public PUMSBucket(PUMSData pumsdata, int PUMA, HHCat hhcat, Random randomGenerator) {

    this.PUMA=PUMA;
    //get number of bins from arc.properties
    NBucketBins=(new Integer(PropertyParser.getPropertyByName("NBucketBins"))).intValue();
    
    bins=new PUMSBucketBin[NBucketBins];
    
    setBins(pumsdata, hhcat, randomGenerator);
  }
  
  public void reset(){
  	for(int i=0; i<bins.length; i++){
  		bins[i].reset();
  	}
  }
    
  public boolean isDone(){
  	if(getNBinsDone()==NBucketBins || isEmpty()) return true;
  	
  	return false;
  }
  
  public boolean isEmpty(){
  	if(NHHs==0) return true;
  	return false;
  }
  
  public int getPUMA(){
    return PUMA;
  }

  public int getHHCatID(){
    return hhcatID;
  }

  /**
   * Get number of bins that are done.
   * @return
   */
  public int getNBinsDone(){
    int result=0;
    PUMSBucketBin tempBin;
    for(int i=0; i<bins.length; i++){
      tempBin=bins[i];
      if(tempBin.isDone()){
        result++;
      }
    }
    return result;
  }

  public PUMSBucketBin [] getBins(){
    return bins;
  }
  
  /**
   * given a bin index, find the PUMSBucketBin
   * @param binIndex represents the bin index, which is 0-based
   * @return
   */
  public PUMSBucketBin getBin(int binIndex){
  	return bins[binIndex];
  }

  /**
   * Assign HHs to bins in this bucket.
   * @param pumsdata represents PUMS data.
   */
  private void setBins(PUMSData pumsdata, HHCat hhcat, Random randomGenerator){
  	
    // modify function to make assignment to bins random (dto)
	boolean [] usedIndex;
	  
	//get HHs in given PUMA and HHCat
    Vector HHsInBucket=pumsdata.getPUMSHHsByPUMAByHHCat(PUMA,hhcat);
    
    //get number of HHs
    NHHs=HHsInBucket.size();

    // create an array of used bucket tracker
    usedIndex = new boolean[NBucketBins];
    
    // initialize empty bins and used index
    for(int i=0; i<NBucketBins; i++){
      bins[i]=new PUMSBucketBin();
      usedIndex[i] = false;
    }
  	
    int binIndex=-1;
    int temp;
    DerivedHH tempHH;
    
    for(int i=0; i<NHHs; i++){
    	
      // get a random number
      temp = randomGenerator.nextInt();
      if(temp<0) temp = -temp;
      binIndex = temp%NBucketBins;
      
      // check if this bin has been used
      if(usedIndex[binIndex])
      {
    	  // find the next bin that has not been used
    	  int counter = 0;
    	  while(counter<NBucketBins)
    	  {
    		  binIndex++;
    		  if(binIndex>=NBucketBins) binIndex-=NBucketBins;
    		  
    		  if(!usedIndex[binIndex]) break;
    		  
    		  counter++; 
    	  }
    	  
    	  // see if we're bigger than the counter
    	  if(counter==NBucketBins){
    		  
              // if we made it here, all the indexes are full, reset the usedIndex
    		  for(int j=0;j<NBucketBins;++j) usedIndex[j] = false;
    	  }
      }
      
      usedIndex[binIndex] = true;
      
      //get current HH
      tempHH=(DerivedHH)HHsInBucket.get(i);
      
      //set drawn status of current HH to false
      tempHH.setDrawnSta(false);
      
      //add current HH to corresponding bin
      bins[binIndex].addHH(tempHH);
      
    }
  }
  
  //for testing purpose only
  //successfully tested on April 6, 2005
  public static void  main(String [] args){
  	Random randomGenerator = new Random(0);
	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
	TableDataReader conversionTableReader=new TableDataReader("conversion");
	TAZtoPUMAIndex index=new TAZtoPUMAIndex(conversionTableReader,false);
    DerivedHHFactory factory = new DerivedHHFactory(); 
  	PUMSData pums = new PUMSData(dd, index, factory);
    long startTime = System.currentTimeMillis();
    PUMSBucket bucket=new PUMSBucket(pums, 700, 100, randomGenerator);
  	logger.info("process each PUMSBucket in: " +((System.currentTimeMillis() - startTime) / 60000.0) + " minutes");
    logger.info("ok, I am done.");
  }
}
