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
package com.pb.models.synpopV3;

import org.apache.log4j.Logger;

import com.pb.common.datafile.TableDataSet;
// import com.pb.morpc.synpop.pums2000.DataDictionary;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixWriter;
import com.pb.common.matrix.MatrixType;
import java.io.File;
import java.util.Vector;
import java.util.Random;

import com.pb.common.matrix.NDimensionalMatrixDouble;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Sept. 27, 2004
 * 
 * 
 * Given PUMSData, first calculate portion of each HHCat in a PUMA,
 * then use it to represent portion of each HHCat in a TAZ contained in this PUMA,
 * finally multiply by Households in each TAZ to get seed distributions:
 * a [ND1SCat][ND2Cat] matrix  ([316][1683] for ARC)
 * 
 */

public class BaseSeedDistributionGenerator {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	
	protected TableDataManager tableManager;
	protected TAZtoPUMAIndex tpIndex;
	
	//number of TAZs
	protected int numberOfInternalZones;
	//number of HH categories
	protected int NoHHCats;
	//number of PUMAs in study region
	protected int NoPUMAs;
	//puma array
	protected int [] puma;
	//buckets
	protected PUMSBucketGroup buckets;
	//number of HHs by TAZ
	protected int [] HHsByTAZ;
	//number of HHs by PUMA and HHCat
	protected int [][] PUMSHHsByPUMAHHCat;
	//number of PUMS HHs by PUMA
	protected int [] PUMSHHsByPUMA;
	//main result array of this class [ND1SCat][ND2Cat], [316][1683]
	protected double [][] BaseSeedDistribution;
	//base seed distribution matrix
	protected Matrix BaseSeedDistributionMatrix;
	//matrix writer
	protected MatrixWriter writer;

  public BaseSeedDistributionGenerator(TableDataManager tableManager,PUMSBucketGroup buckets) {

  	this.tableManager=tableManager;
  	this.tpIndex=tableManager.getTAZtoPUMAIndex();
  	this.buckets=buckets;
  	  	
  	//get PUMA array contains unique PUMAs
  	puma=tpIndex.getPUMAs();
  	
  	numberOfInternalZones=PopulationSynthesizer.numberOfInternalZones;
    NoHHCats=HHCatTable.NHHCat;
    NoPUMAs=tpIndex.getNoPUMAs();
    
    HHsByTAZ=new int[numberOfInternalZones];
    PUMSHHsByPUMAHHCat=new int[NoPUMAs][NoHHCats];
    PUMSHHsByPUMA=new int[NoPUMAs];
    
    makeHHsByTAZ();
    makePUMSHHsByPUMAHHCat();
    makePUMSHHsByPUMA();
    makeBaseSeedDistribution();
        
    //create base seed distribution as a matrix
    float[][] bsd = new float[NoHHCats][numberOfInternalZones];
    for (int h = 0; h < NoHHCats; ++h) {
			for (int t = 0; t < numberOfInternalZones; ++t) {
				bsd[h][t] = (float) BaseSeedDistribution[h][t];
			}
	}

	BaseSeedDistributionMatrix = new Matrix("BaseSeedDistribution",
				"base year seed distribution", bsd);   
    
    //write base seed distribution matrix to disk
    /*
    if(PropertyParser.getPropertyByName("WriteBaseSeedDistribution").equalsIgnoreCase("true")){
    	writeBaseSeedDistributionMatrixToDisk();
    }
    */
   	
  }
  
  /**
   * get base year seed distribution as an array
   * @return
   */
  public double [][] getBaseSeedDistribution(){
  	return BaseSeedDistribution;
  }
  
  /**
   * get base year seed distribution as an NDimensionalMatrix Object
   * @return
   */
  public NDimensionalMatrixDouble getBaseSeedDistributionNMatrix(){
  	return new NDimensionalMatrixDouble("matrix", BaseSeedDistribution);
  }
  
  /**
   * get base year seed distribution as a Matrix
   * @return
   */
  public Matrix getBaseSeedDistributionMatrix(){
  	return BaseSeedDistributionMatrix;
  }
  
  /**
   * calculate households in each TAZ, source table is sf1p26.csv
   *
   */
  private void makeHHsByTAZ(){
  	TableDataReader tableReader=tableManager.getTableReader("converted");
  	
  	// get the table name 
  	String sf1p26Name  = PropertyParser.getPropertyByName("converted.basedistribution");
  	String sf1p26FieldName = "P026001";
	logger.info("Households by TAZ assumed to be in " + sf1p26Name + ", column " + sf1p26FieldName);
  	
  	TableDataSet sf1p26=tableReader.getTable(sf1p26Name);
  	HHsByTAZ=sf1p26.getColumnAsInt(sf1p26FieldName);
  }
    
  private void makePUMSHHsByPUMAHHCat(){
    	//1D PUMA, 2D HHCat
    	PUMSBucket [][] pbs=buckets.getPUMSBuckets();
    	for(int i=0; i<NoPUMAs; i++){
    		for(int j=0; j<NoHHCats; j++){
    			PUMSHHsByPUMAHHCat[i][j]=pbs[i][j].NHHs;
    		}
    	}
    }
  
  /**
   * make array PUMSHHsByPUMA
   *
   */
  private void makePUMSHHsByPUMA(){
  	
  	for(int i=0; i<NoPUMAs; i++){
  		for(int j=0; j<NoHHCats; j++){
  			PUMSHHsByPUMA[i]+=PUMSHHsByPUMAHHCat[i][j];
  		}
  	}
  }
  
  /**
   * make base year seed distribution
   *
   */
  private void makeBaseSeedDistribution(){
  	
  	//calculate proportion of PUMS hhs in each HHCat by PUMA
  	double [][] proportion=new double[NoPUMAs][NoHHCats];
  	for(int i=0; i<NoPUMAs; i++){
  		for(int j=0; j<NoHHCats; j++){
  			if(PUMSHHsByPUMA[i]!=0){
  				proportion[i][j]=(double)PUMSHHsByPUMAHHCat[i][j]/(double)PUMSHHsByPUMA[i];
  			}
  			else{
  				proportion[i][j]=0;
  				logger.fatal("No PUMS HHs in PUMA:"+puma[i]);
  				System.exit(-1);
  			}
  		}
  	}
  	
  	BaseSeedDistribution=new double[NoHHCats][numberOfInternalZones];
  	int currentPUMA=-1;
  	for(int i=0; i<NoHHCats; i++){
  		for(int j=0; j<numberOfInternalZones; j++){
            int extTAZ = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1); 
  			currentPUMA=tpIndex.getPUMA(extTAZ);
  			BaseSeedDistribution[i][j]=((float)HHsByTAZ[j])*((float)proportion[findPUMAIndex(currentPUMA)][i]);
  		}
  	} 
  	
  }
  
  /**
   * find PUMA index in PUMA array
   * @param pumaID
   * @return
   */
  private int findPUMAIndex(int pumaID){
  	int result=-1;
  	for(int i=0; i<NoPUMAs; i++){
  		if(puma[i]==pumaID){
  			result=i;
  		}
  	}
    if (result==-1) {
        logger.error("Could not find pumaID: " + pumaID); 
    }    
  	return result;
  }
  
  private void writeBaseSeedDistributionMatrixToDisk(){
  		String dir=PropertyParser.getPropertyByName("interimResult.directory");
  		String fileName=PropertyParser.getPropertyByName("BaseSeedDistributionMatrix.file");
    	File matrixFile=new File(dir+fileName);
        writer=MatrixWriter.createWriter(MatrixType.BINARY, matrixFile);
        writer.writeMatrix(BaseSeedDistributionMatrix);	
  }

  //For testing purpose only
  //Successfully tested on March 25, 2005.  Finished in 104 minutes.
  public static void main(String [] args){
  	
    long startTime = System.currentTimeMillis();
    Random randomGenerator = new Random(0);
    
	//census table converted to TAZ-based tables here
	TableDataManager tableDataManager=new TableDataManager();	
  	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);

    DerivedHHFactory factory = new DerivedHHFactory();         
  	PUMSData pumsdata=new PUMSData(dd,tableDataManager.getTAZtoPUMAIndex(), factory);
  	
  	PUMSBucketGroup buckets=new PUMSBucketGroup(pumsdata, tableDataManager.getTAZtoPUMAIndex(),randomGenerator);
  	BaseSeedDistributionGenerator generator=new BaseSeedDistributionGenerator(tableDataManager, buckets);

  	logger.info("full BaseSeedDistribution in: " +((System.currentTimeMillis() - startTime) / 60000.0) + " minutes");
  }
}