/*
 * Copyright 2005 PB Consult Inc.
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
 * Created on Mar 31, 2005
 * 
 * This class use seed distribution and PUMSData (with PUMS HHs assigned to buckets and bins) to
 * draw HHs and produce SynPop
 */
package com.pb.models.synpopV3;

import com.pb.common.matrix.NDimensionalMatrixDouble;

import java.util.Vector;
import java.util.Random;

import org.apache.log4j.Logger;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class HHDrawer {
	
	protected boolean logDebug=false;
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected PUMSData pumsdata;
	protected NDimensionalMatrixDouble distribution;
	protected TAZtoPUMAIndex pumaIndex;
	protected int numberOfInternalZones;
	protected int NoHHCats;
	protected int NoBucketBins;
	protected TAZBinAssigner binAssigner;
	protected PUMSBucketGroup bucketGroup;
	protected TableDataManager tableDataManager;
	protected PUMASimilarityTable pumaSimilarityTable;
	protected int [] PUMAs;
	//1st dimension HHCat, 2nd dimension TAZ, for ARC [316][1683]
	protected Vector [][] PopSyn;
	protected int NoDrawnHHs;
	protected int NoSkippedHHs;
	protected int NoDrawnPersons;
	
	public HHDrawer(PUMSData pumsdata, PUMSBucketGroup bucketGroup, NDimensionalMatrixDouble distribution,TableDataManager tableDataManager){
		this.pumsdata=pumsdata;
		this.bucketGroup=bucketGroup;
		this.distribution=distribution;
		this.tableDataManager=tableDataManager;
		pumaIndex=tableDataManager.getTAZtoPUMAIndex();
		numberOfInternalZones=PopulationSynthesizer.numberOfInternalZones;
		NoBucketBins=new Integer(PropertyParser.getPropertyByName("NBucketBins")).intValue();
		NoHHCats=HHCatTable.NHHCat;
		binAssigner=new TAZBinAssigner(pumsdata, pumaIndex);
		PUMAs=pumaIndex.getPUMAs();
		pumaSimilarityTable=new PUMASimilarityTable(tableDataManager.getTableReader("design"));
		initPopSyn();
		drawHH();
	}
	
	/**
	 * get population sythesizer
	 * @return
	 */
	public Vector [][] getPopSyn(){
		return PopSyn;
	}
	
	/**
	 * get number of drawn hhs in PopSyn
	 * @return
	 */
	public int getNoDrawnHHs(){
		return NoDrawnHHs;
	}
	
	public int getNoSkippedHHs(){
		return NoSkippedHHs;
	}
	

	public int getNoHHsInDistribution(){
		return (int)distribution.getSum();
	}
	
	/**
	 * get number of persons in PopSyn
	 * @return
	 */
	public int getNoDrawnPersons(){
		return NoDrawnPersons;
	}
	
	private void initPopSyn(){
		PopSyn=new Vector[NoHHCats][numberOfInternalZones];
		for(int i=0; i<NoHHCats; i++){
			for(int j=0; j<numberOfInternalZones; j++){
				PopSyn[i][j]=new Vector();
			}
		}
	}
	
    /**
     * Use seed distribution and PUMS data (with PUMS HHs assigned into buckets and bins) 
     * to draw HHs, and produce PopSyn
     */
    private void drawHH() {
    	
    	NoDrawnHHs=0;
    	NoSkippedHHs=0;
    	NoDrawnPersons=0;

        int puma=-1;
        int tazBin=-1;
        
        for(int i=0; i<NoHHCats; i++){
        	for(int j=0; j<numberOfInternalZones; j++){
        		
        		//get PUMA for current TAZ
        		puma=pumaIndex.getPUMA(ExtTAZtoIntTAZIndex.getExternalTAZ(j+1));
        		
        		//number of HHs in each seed distribution cell
        		int NoHHsInCell=-1;
        		
                //HHCat is 1st and TAZ is 2nd dimension in seed distribution
        		int [] shape={i,j};
        		
        		//get number of HHs in cell (i, j)
        		NoHHsInCell= (int)distribution.getValue(shape);

        		//bucketGroup=new PUMSBucketGroup(pumsdata, tableDataManager.getTAZtoPUMAIndex());
        		bucketGroup.reset(i);
        		
        		//bucketGroup.setPUMSBuckets(bucketsCopy);
        		
        		// move this out of the loop (dto)
        		tazBin = binAssigner.getBinNum(j+1);

		        for(int k=0; k<NoHHsInCell; k++){
		        	       	
		        	//initialize rank with 1, it represents current PUMA itself.
		            int rank = 1;
		            int similarPUMA=-1;
		        			
		            if(logDebug)
		            	logger.info("i="+i+" j="+j+" k="+k);
		            
		            //if buckets of HHCatIndex i are done, send a warning and reset the bucket
		            if(bucketGroup.isDoneByFixedHHCatIndex(i)){
		            	
		            	logger.warn("Could only draw "+k+" of " +NoHHsInCell+" needed hhs of HHCat "+(i+1)+
	    	        		    " in zone "+(j+1));
	    	            logger.warn("PUMA bucket will be reset and drawing continued");
	    	            
	    	            bucketGroup.reset(i);
	    	            
		            }
		            	
		            //find PUMS bucket for current puma, and hhcat.
		            PUMSBucket bucket = bucketGroup.getPUMSBucket(pumaIndex.getPUMAArrayIndex(puma),i);
		            PUMSBucketBin bin=null;
		                    
			        //While current bucket is not eligible, find the next similar bucket (in terms of PUMA)
			        while (bucket.isDone()) {
			            rank++;
			
			            //find the next similar PUMA
			            //to make sure a similar PUMA will always be found, cycle back to current PUMA as its similar PUMA when all other PUMAs are exhausted.
			            similarPUMA = pumaSimilarityTable.getSimilarPUMA(puma, rank);
			
			            //if the next similar PUMA is not current PUMA itself, find the bucket for the similar PUMA.
			            bucket = bucketGroup.getPUMSBucket(pumaIndex.getPUMAArrayIndex(similarPUMA), i);
			            tazBin=binAssigner.getBinNum(j+1);
			        }
			            
			        if(rank>pumaIndex.getNoPUMAs()){
			            logger.warn("rank > number of PUMAs!");
			        }
			                    
			        //get a bin from the newly found eligible bucket.
			        bin=bucket.getBin(tazBin);
			                    
			        //while current bin not eligible, move to the next bin until find one eligible bin
			        while (bin.isDone()) {
			            	
			            //move to next bin
			            tazBin++;
			
			            //cycle back to bin 1 if tazBin>=maximum number of bins in a bucket
			            if (tazBin >= NoBucketBins) {
			                tazBin = tazBin - NoBucketBins;
			            }
			
			            //get a new BucketBin for current binNo
			            bin=bucket.getBin(tazBin);
			        }
			                    			                    
			        //randomly select a HH from this bucket bin, and add it to synpop
			        DerivedHH selectedHH=selectHH(bin.getHHs(),i,j);
			                    
			        int PUMAIndex=-1;
			        if(similarPUMA!=-1)
			            PUMAIndex=pumaIndex.getPUMAArrayIndex(similarPUMA);
			        else
			            PUMAIndex=pumaIndex.getPUMAArrayIndex(puma);
			            
			        int HHCatIndex=i;
		            int binIndex=tazBin;
			        int hhIndex=findHHIndex(selectedHH, bin.getHHs());
			                    
			        bucketGroup.update(PUMAIndex, HHCatIndex, binIndex, hhIndex, selectedHH);
		             
			        //create a DrawnHH from the selected DerivedHH
			        DrawnHH drawnHH=new DrawnHH(selectedHH);
			            
			        //HHCat starts from 1, must add 1 to i
			        drawnHH.setD1SCat(i+1);
			        drawnHH.setBucketBin(tazBin);
			        drawnHH.setOriginalPUMA(selectedHH.getHHAttr("PUMA5"));
			        drawnHH.setSelectedPUMA(puma);
			            
			        //TAZ is 1-based
			        drawnHH.setTAZ(j+1);
			        PopSyn[i][j].add(drawnHH);
			             
			        NoDrawnHHs++;
			                    			                    
			        NoDrawnPersons+=selectedHH.getNoOfPersons();
			                    
			        if(logDebug){
				        if(selectedHH.getHHAttr("PUMA5")!=puma){
				            logger.info("original puma="+selectedHH.getHHAttr("PUMA5"));
				            logger.info("selected puma="+puma);
				        }
			        }
			            
                    // increment tazBin after each draw rather than just when bin is empty (dto)
			        tazBin++;
			        if(tazBin >= NoBucketBins ){
			            tazBin = tazBin - NoBucketBins;
			        }
			            
		    	}
	        }
        }
        
        logger.info("drawn hhs="+NoDrawnHHs);
	    logger.info("skipped hhs="+NoSkippedHHs);
	    logger.info("hhs in distribution="+distribution.getSum());
    }
    
    /**
     * Randomly select a HH from a Vector of HHs (select only from HHs with drawnSta==false).
     * @param HHs represents a vector of DerivedHH objects
     * @param tazIndex represents internal TAZ index, 0-based
     * @param hhcatIndex represents internal HHCat index, 0-based
     * @return
     */
    private DerivedHH selectHH(Vector HHs, int hhcatIndex, int tazIndex) {
        //vector contains only those HHs of drawnSta==fasle
        Vector undrawnHHs = new Vector();

        //current HH
        DerivedHH currentHH=null;
        //drawn status of current HH
        boolean drawnSta=false;

        //filter HHs, keep only those with drawnsta==false, and put them in undrawnHHs
        for (int i = 0; i < HHs.size(); i++) {
            currentHH = (DerivedHH) HHs.get(i);
            drawnSta = currentHH.getDrawnSta();

            if (!drawnSta) {
                undrawnHHs.add(currentHH);
            }
        }
        
        //instantiate a Random number generator
        Random generator = new Random();
       
        //set fixed random seed to random seed generator
        generator.setSeed(RandomSeedMatrix.getSeed(hhcatIndex, tazIndex));

        int i=-1;
        if(undrawnHHs.size()==0){
        	logger.fatal("there is no undrawn HHs in this bin, this is an invalid bin, check your logic.");
        }else{
        //create a random number between 0 and number of undrawn HHs
        	i = generator.nextInt(undrawnHHs.size());
        }
        
        DerivedHH result=(DerivedHH)undrawnHHs.get(i);
        
        return result;
    }
    
    /**
     * given a DerivedHH object, find its position in a Vector of HHs
     * @param hh
     * @param hhs
     * @return
     */
    private int findHHIndex(DerivedHH hh, Vector hhs){
    	int result=-1;
    	for(int i=0; i<hhs.size(); i++){
    		if((DerivedHH)hhs.get(i)==hh){
    			result=i;
    			break;
    		}
    	}
    	return result;
    }
    
}
