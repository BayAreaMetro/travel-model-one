/*
 * Copyright  2005 PB Consult Inc.
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
 *
 */
package com.pb.models.synpopV3;

import java.util.Vector;

import com.pb.common.matrix.NDimensionalMatrixDouble;
import org.apache.log4j.Logger;


/**
 * @author Dave Ory
 * <oryd@pbworld.com>
 *
 * This class creates a future year seed distribution using the balanced base year distribution
 * (from the base year model run) as well as the base year distribution at the PUMA and TRACT 
 * level of aggregation (using weights). 
 * 
 */
public class FutureSeedDistribution {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    protected NDimensionalMatrixDouble hhCatsByTazShares;
    protected double [][] hhCatsByTractShares;
    protected double [][] hhCatsByPumaShares;
    protected Vector<Double> tazSize;
    protected Vector<Double> tractSize;
    protected LookUpTable tazToPumaCrosswalk;
    protected LookUpTable tazToTractCrosswalk;
    protected int numberOfHhCats;
    protected int numberOfInternalZones;
    protected double weights[] = {0.0,0.0,0.0};
    protected float lowSizeThreshold;
    protected float highSizeThreshold;
  
    /**
     * Constructor
     * Reads the base year seed matrix and computes the shares for each category at
     * three levels of aggregation: zone, tract, and puma.
     */
    public FutureSeedDistribution() {
    	
    	numberOfHhCats = new Integer (PropertyParser.getPropertyByName("NoHHCats")).intValue();
        lowSizeThreshold = new Float (PropertyParser.getPropertyByName("Forecast.LowSizeThreshold")).floatValue();
        highSizeThreshold = new Float (PropertyParser.getPropertyByName("Forecast.HighSizeThreshold")).floatValue();
    	
    	// read in the base year seed distribution
    	String seedFile = new String(PropertyParser.getPropertyByName("Forecast.directory")+PropertyParser.getPropertyByName("Forecast.BaseSeedDistributionFile"));
    	hhCatsByTazShares = new NDimensionalMatrixDouble(seedFile);
        
        // use the lookUpTable object as an easy way to crosswalk taz to puma and tract
    	tazToPumaCrosswalk = new LookUpTable("file","PUMA");
    	tazToTractCrosswalk =new LookUpTable("file","TRACT");
    	int numberOfPumas  = tazToPumaCrosswalk.numberOfIndices();
    	int numberOfTracts = tazToTractCrosswalk.numberOfIndices();
    	
    	// variables for later use
    	numberOfInternalZones = hhCatsByTazShares.getShape(1); 
    	int index=0;
    	int [] tazLocation = {0,0};
    	
    	// create the puma array
    	hhCatsByPumaShares = new double[numberOfHhCats][numberOfPumas];
    	
    	// fill the puma array
    	for(int i=0;i<numberOfHhCats;++i){
    		
    		// set the aggregation location arrays
    		tazLocation[0] = i;
    		
    		for(int j=0;j<numberOfInternalZones;++j){
    			
    			// get the corresponding puma for the index
                int extTaz = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
    			index = tazToPumaCrosswalk.tazToAggregateIndex(extTaz);
    			
    			// build the aggregation
    			tazLocation[1] = j;

    			hhCatsByPumaShares[i][index] += hhCatsByTazShares.getValue(tazLocation);
    			
    		}
    		
    	} // i loop
    	
    	// compute the shares for each hhCat in each puma
    	double rowTotal;
    	for(int i=0;i<numberOfPumas;++i){
    		
    		// get the rowTotal from the matrix
    		rowTotal = 0.0;
    		for(int j=0;j<numberOfHhCats;++j) rowTotal+=hhCatsByPumaShares[j][i];
    		
    		// set the share
    		for(int j=0;j<numberOfHhCats;++j){
    			
    			if(rowTotal>0.0) hhCatsByPumaShares[j][i] = hhCatsByPumaShares[j][i]/rowTotal;
        		else hhCatsByPumaShares[j][i] = 0.0;
    			
    		}
    	}
    	
    	// create the tract array
    	hhCatsByTractShares = new double [numberOfHhCats][numberOfTracts];
    	
        // fill the tract array
    	for(int i=0;i<numberOfHhCats;++i){
    		for(int j=0;j<numberOfInternalZones;++j){
    			
    			// get the corresponding tract for the index
                int extTaz = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
    			index = tazToTractCrosswalk.tazToAggregateIndex(extTaz);
    			
    			// build the aggregation
    			tazLocation[0] = i;
    			tazLocation[1] = j;
    			
    			hhCatsByTractShares[i][index] += hhCatsByTazShares.getValue(tazLocation);
    			
    		}
    	}
    	
    	// compute the shares for each hhCat in each tract
    	this.tractSize = new Vector<Double>(numberOfTracts);
    	for(int i=0;i<numberOfTracts;++i){
    		
    		// get the rowTotal from the matrix
    		rowTotal = 0.0;
       		for(int j=0;j<numberOfHhCats;++j) rowTotal+=hhCatsByTractShares[j][i];
    		
    		tractSize.add(i,rowTotal);
    		
    		// set the share
    		for(int j=0;j<numberOfHhCats;++j){

    			if(rowTotal>0.0) hhCatsByTractShares[j][i] = hhCatsByTractShares[j][i]/rowTotal;
        		else hhCatsByTractShares[j][i] = 0.0;
    			
    		}
    	}
    	
    	// compute shares for each hhCat in each Taz
    	this.tazSize = new Vector<Double>(numberOfInternalZones);
    	for(int i=0;i<numberOfInternalZones;++i){
    		
    		// get the rowTotal from the matrix
    		tazLocation[0]=-1; tazLocation[1]=i;
    		rowTotal = hhCatsByTazShares.getVectorSum(tazLocation);
    		
    		tazSize.add(i,rowTotal);
    		
    		// set the share
    		for(int j=0;j<numberOfHhCats;++j){
    			
    			tazLocation[0] = j;
    			if(rowTotal>0.0) hhCatsByTazShares.setValue(hhCatsByTazShares.getValue(tazLocation)/rowTotal,tazLocation);
        		else hhCatsByTazShares.setValue(0.0,tazLocation);
    			
    		}
    	}
    	
    }   	
    
    /**
     * Generates future seed from base year seed at different aggregation levels, using weights
     * and forecast year household size
     * @param ForecastTazData set
     * 
     */
    public void generateSeed(TazData forecastData){
    	
    	int pumaIndex;
    	int tractIndex;
    	double tazSz, tractSz, share;
    	int location[] = {0,0};
    	
    	// use j for tazs to keep the i, j in the location the same as the matrices
    	for(int j=0;j<numberOfInternalZones;++j){
    		
            // get the puma and tractIndex
            int extTaz = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
			pumaIndex  = tazToPumaCrosswalk.tazToAggregateIndex(extTaz);
			tractIndex = tazToTractCrosswalk.tazToAggregateIndex(extTaz);
			
			tazSz   = ((Double) tazSize.get(j)).doubleValue();
			tractSz = ((Double) tractSize.get(tractIndex)).doubleValue();
			
			// case one -- weights(taz, tract, puma)
			if(tazSz<lowSizeThreshold && tractSz<lowSizeThreshold){
				weights[0] = 0.0; 
				weights[1] = 0.0; 
				weights[2] = 1.0;
			}
			
            // case two
			else if(tazSz<lowSizeThreshold && tractSz>=lowSizeThreshold && tractSz<highSizeThreshold){
				weights[0] = 0.0; 
				weights[1] = (tractSz-lowSizeThreshold) /(highSizeThreshold - lowSizeThreshold); 
				weights[2] = (highSizeThreshold-tractSz)/(highSizeThreshold - lowSizeThreshold);
			}
			
            // case three
			else if(tazSz<lowSizeThreshold && tractSz>=highSizeThreshold){
				weights[0] = 0.0; 
				weights[1] = 1.0; 
				weights[2] = 0.0;
			}
			
            // case four
			else if(tazSz>=lowSizeThreshold && tazSz<highSizeThreshold && tractSz>=lowSizeThreshold && tractSz<highSizeThreshold){
				weights[0] = (tazSz-lowSizeThreshold)/(highSizeThreshold - lowSizeThreshold); 
				weights[1] = (tractSz-tazSz)/(highSizeThreshold - lowSizeThreshold); 
				weights[2] = (highSizeThreshold-tractSz)/(highSizeThreshold - lowSizeThreshold);
			}
			
			// case five
			else if(tazSz>=lowSizeThreshold && tazSz<highSizeThreshold && tractSz>=highSizeThreshold){
				weights[0] = (tazSz-lowSizeThreshold) /(highSizeThreshold - lowSizeThreshold); 
				weights[1] = (highSizeThreshold-tazSz)/(highSizeThreshold - lowSizeThreshold); 
				weights[2] = 0.0;
			}
			
			// case six
			else{
				weights[0] = 1.0; 
				weights[1] = 0.0; 
				weights[2] = 0.0;
			}
			
			location[1] = j;
			
			// now loop through the hh categories and apply the weights
			for(int i=0;i<numberOfHhCats;++i){
				
				location[0] = i;
				
                // taz
    			location[1] = j;
    			share = weights[0] * hhCatsByTazShares.getValue(location);
    			
    			// tract
    			share += weights[1] * hhCatsByTractShares[i][tractIndex];
    			
    			// puma
    			share += weights[2] * hhCatsByPumaShares[i][pumaIndex];
    			
    			// and use the hhCatsByTazShare matrix to store them
    			location[1] = j;
    			hhCatsByTazShares.setValue(share,location);
			
			} // hh category i loop	
			
    	} // j taz loop
    	
    	// again, reverse the i and j to keep consistent with how matrices are put together
        for(int j=0;j<numberOfInternalZones;++j){
    		
        	
        	
        	
        	// get the number of hhs in taz
        	int extTaz = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
        	tazSz = 1.0 * forecastData.getNumberOfHouseholds(extTaz);
        	
        	location[1] = j;
        	
    		for(int i=0;i<numberOfHhCats;++i){
    			
    			location[0] = i;
    			hhCatsByTazShares.setValue(hhCatsByTazShares.getValue(location) * tazSz,location);

    		}
    		
        }
    	
    	// write the seed distribution if desired
    	if(PropertyParser.getPropertyByName("Forecast.WriteForecastSeedDistribution").equalsIgnoreCase("true")){
        	String fileName=PropertyParser.getPropertyByName("interimResult.directory")+PropertyParser.getPropertyByName("Forecast.OutputSeedDistributionFile");
        	hhCatsByTazShares.printMatrixDelimited(",",fileName);
        }
 	
    }
    
    public NDimensionalMatrixDouble getSeed(){

    	return hhCatsByTazShares;
    }
    
    //  for testing purposes only
    // tested successfully 12/05 (dto)
    public static void main(String [] args){
		
    	//FutureSeedDistribution futureSeed = new FutureSeedDistribution();
    	
    	/*
    	TableDataManager tableDataManager=new TableDataManager();
    	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+
    			                             PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
	  	PUMSData pumsData=new PUMSData(dd,tableDataManager.getTAZtoPUMAIndex());
	  	
    	ForecastTazData data = new ForecastTazData();
		data.computeControlTotals(10,pumsData.generateForecastControlData(),16);
		*/
		

    	
	}
		
  
}

    
