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
/*
 * Created on Mar 30, 2005
 * 
 * This class creates a group of PUMSBucket objects from PUMSData, 
 * TAZtoPUMAIndex, and HHCatTable.
 */
package com.pb.models.synpopV3;

import java.util.Random;
import org.apache.log4j.Logger;
// import com.pb.morpc.synpop.pums2000.DataDictionary;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 */

public class PUMSBucketGroup {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected PUMSData pumsdata;
	protected TAZtoPUMAIndex pumaIndex;
	protected int [] PUMAs;
	//buckets, 1D PUMA, 2D HHCat
	protected PUMSBucket [][] buckets;
	protected boolean logDebug=true;
	
	public PUMSBucketGroup(PUMSData pumsdata, TAZtoPUMAIndex pumaIndex, Random randomGenerator){
		this.pumsdata=pumsdata;
		this.pumaIndex=pumaIndex;
		PUMAs=pumaIndex.getPUMAs();
		populateBucketGroup(randomGenerator);
	}
	
	/**
	 * reset all bukcets in a HHCat
	 * @param hIndex
	 */
	public void reset(int hIndex){
		for(int i=0; i<buckets.length; i++){
			buckets[i][hIndex].reset();
		}
	}
	
	public void reset(){
		for(int i=0; i<buckets.length;i++){
			for(int j=0; j<buckets[0].length; j++)
				buckets[i][j].reset();
		}
	}
	
	public PUMSBucket [][] getPUMSBuckets(){
		return buckets;
	}
	
	public void setPUMSBuckets(PUMSBucket [][] buckets){
		this.buckets=buckets;
	}
	
	/**
	 * check if all buckets in bucket group are done.
	 * @return
	 */
	public boolean isDone(){
		boolean result=true;
		for(int i=0; i<buckets.length; i++){
			for(int j=0; j<buckets[0].length; j++){
				if(!buckets[i][j].isDone()){
					result=false;
					break;
				}
			}
			if(result==false){
				break;
			}
		}
		return result;
	}
	
	/**
	 * check if all buckets are done in a HHCat
	 * @param index 0-based
	 * @return
	 */
	public boolean isDoneByFixedHHCatIndex(int index){
		boolean result=true;
		for(int i=0; i<buckets.length; i++){
			if(!buckets[i][index].isDone()){
				result=false;
				break;
			}
		}
		
		return result;
	}
	
	/**
	 * check if all buckets are done in a PUMA
	 * @param index 0-based
	 * @return
	 */
	public boolean isDoneByFixedPUMAIndex(int index){
		boolean result=true;
		for(int i=0; i<buckets[0].length; i++){
			if(!buckets[index][i].isDone()){
				result=false;
				break;
			}
		}
		return result;
		
	}
	
	public boolean isDoneByFixedPUMAIndexHHCatIndex(int pIndex, int hIndex){
		boolean result=true;
		if(!buckets[pIndex][hIndex].isDone()){
			result=false;
		}
		return result;
	}
	
	/**
	 * given PUMA index and HHCat index, find corresponding PUMSBucket
	 * @param i represents PUMA index, it is 0-based
	 * @param j represents HHCat index, it is 0-based
	 * @return
	 */
	public PUMSBucket getPUMSBucket(int i, int j){
		if(i>=PUMAs.length){
			logger.fatal("invalid PUMA index:"+i);
		}
		if(j>=HHCatTable.getHHCatCount()){
			logger.fatal("invalid HHCat index:"+j);
		}
		return buckets[i][j];
	}
	
	/**
	 * given PUMAIndex, HHCatIndex, binIndex, and hhIndex, update bucketGroup
	 * @param PUMAIndex 0-based
	 * @param HHCatIndex 0-based
	 * @param binIndex 0-based
	 * @param hhIndex 0-based
	 * @param hh
	 */
	public void update(int PUMAIndex, int HHCatIndex, int binIndex, int hhIndex,DerivedHH hh){
		hh.setDrawnSta(true);
		buckets[PUMAIndex][HHCatIndex].bins[binIndex].setHH(hhIndex,hh);
		buckets[PUMAIndex][HHCatIndex].bins[binIndex].update();
	}
		
	private void populateBucketGroup(Random randomGenerator){
		int counter=0;
		buckets=new PUMSBucket [PUMAs.length][HHCatTable.getHHCatCount()];
		for(int i=0; i<PUMAs.length; i++){
			for(int j=0; j<HHCatTable.getHHCatCount(); j++){
				//logger.info("processing PUMA:"+PUMAs[i]+" and HHCat:"+(j+1));
				//Note: i is PUMA index, j is HHCat index, both 0-based;
				//j+1 represents HHCat ID in HHCatTable which is 1-based
				buckets[i][j]=new PUMSBucket(pumsdata, PUMAs[i],j+1,randomGenerator);
				counter+=buckets[i][j].NHHs;
				if(logDebug){
					if(buckets[i][j].NHHs==0){
						// TODO determine if this message is needed (dto)
						// logger.info("Warning: bucket with PUMA ID="+i+" HHCat ID="+j+" is empty!");
					}
				}
			}
		}
		if(logDebug)
			logger.info("total number of hhs in PUMSBucketGroup:"+counter);
	}
	
	//for testing purpose only.
	//successfully tested on April 6, 2005
	public static void main(String [] args){
        Random randomGenerator = new Random(0);
		DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
		TableDataReader conversionTableReader=new TableDataReader("conversion");
		TAZtoPUMAIndex index=new TAZtoPUMAIndex(conversionTableReader,false);
        DerivedHHFactory factory = new DerivedHHFactory(); 
	  	PUMSData pums = new PUMSData(dd, index, factory);
		PUMSBucketGroup group=new PUMSBucketGroup(pums, index, randomGenerator);
	    logger.info("ok, I am done.");
	}
}
