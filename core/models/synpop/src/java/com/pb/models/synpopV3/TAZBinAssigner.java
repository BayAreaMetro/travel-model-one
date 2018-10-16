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

// import com.pb.morpc.synpop.pums2000.DataDictionary;
import java.util.Vector;
import org.apache.log4j.Logger;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 * This class assigns a bin number ( example: 1 to 10 ) to each TAZ.
 * For each HHs in a TAZ, we need to know not only which PUMS bucket it belongs to,
 * but also which bin in the PUMS bucket it belongs to.  Each TAZ is pre-assigned
 * a bin number in this class.
 * 
 * The bin assignment of TAZs must persist so that the base year and multiple
 * forecast year PopSyn are based on the same TAZ bin assignments.
 *
 */
public class TAZBinAssigner {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    protected int NTAZ;
    protected int NBins;
    protected int NPUMA;
    protected int[] binNums;
    protected PUMSData pumsdata;    
    protected TAZtoPUMAIndex pumaIndex;
    protected Vector[] TAZsInPUMA;
  
    /**
     * Constructor
     * @param pumsdata represents PUMS data
     * @param pumaIndex represents a TAZ to PUMA index
     */
    public TAZBinAssigner(PUMSData pumsdata, TAZtoPUMAIndex pumaIndex) {
    	
        this.pumsdata = pumsdata;
    	this.pumaIndex=pumaIndex;
    	
        //number of PUMAs
    	NPUMA = pumaIndex.getNoPUMAs();
    	//vector of TAZs which belong to each PUMA
        TAZsInPUMA = new Vector[NPUMA];
        //number of TAZs
        NTAZ = PopulationSynthesizer.numberOfInternalZones;
        //number of bins in each bucket
        NBins = (new Integer(PropertyParser.getPropertyByName("NBucketBins"))).intValue();
        //bins assigned to each TAZ
        binNums = new int[NTAZ+1];

        assignBinNum();
    }

    /**
     * Get bin numbers assigned to TAZs.
     * @return
     */
    public int [] getBinNums(){
      return binNums;
    }

    /**
     * Given a TAZ, find it's bin number.
     * @param taz represents a TAZ number.  Important: TAZ must be 1-based sequential integer.
     * @return a bin number.
     */
    public int getBinNum(int taz){
      return binNums[taz];
    }

    /**
     * Assign bin number to each TAZ
     */
    private void assignBinNum() {
    	
    	//initialize TAZsInPUMA
    	for(int i=0; i<NPUMA; i++){
    		TAZsInPUMA[i]=new Vector();
    	}
    	
    	int [] PUMAs=pumaIndex.getPUMAs();

        //assign TAZs to each PUMA, assume TAZ is 1-based.
        for (int i = 0; i < NTAZ; i++) {
        	//get corresponding PUMA for a given TAZ
            int extTAZ = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1); 
        	int puma=pumaIndex.getPUMA(extTAZ);
        	int index=-1;
        	//find array index of this PUMA
        	for(int j=0; j<NPUMA; j++){
        		if(puma==PUMAs[j]){
        			index=j;
        			break;
        		}
        	}
        	//add TAZ to TAZ vector of a PUMA
        	TAZsInPUMA[index].add(new Integer(i+1));
        }

        //number of HHs in each PUMA
        //int NHHsInPUMA=-1;
        //number of TAZs in each PUMA
        int NTAZsInPUMA=-1;
        
        //assign bin number to each TAZ
        for (int i = 0; i < NPUMA; i++) {
            //get number of HHs in current PUMA
            // int NHHsInPUMA = pumsdata.getPUMSHHCountByPUMA(PUMAs[i]);
            //get number of TAZs in current PUMA
            NTAZsInPUMA = TAZsInPUMA[i].size();

            for (int j = 0; j < NTAZsInPUMA; j++) {
                //current taz
                int taz = ((Integer) TAZsInPUMA[i].get(j)).intValue();
                //taz is equally assigned to NBins
                binNums[taz]=j%NBins;
            }
        }
    }
    
    //for testing purpose only
    //successfully tested on April 8, 2005
    public static void main(String [] args){
	  	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
		TableDataReader conversionTableReader=new TableDataReader("conversion");
		TAZtoPUMAIndex index=new TAZtoPUMAIndex(conversionTableReader,false);
        DerivedHHFactory factory = new DerivedHHFactory(); 
	  	PUMSData pums = new PUMSData(dd, index, factory);
		TAZBinAssigner assigner=new TAZBinAssigner(pums, index);
	    logger.info("ok, I am done.");
    }
}
