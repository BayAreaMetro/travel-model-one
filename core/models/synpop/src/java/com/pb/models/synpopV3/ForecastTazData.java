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

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Hashtable;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.ColumnVector;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.math.MathUtil;
import org.apache.log4j.Logger;


/**
 * @author Dave Ory
 * <oryd@pbworld.com>
 *
 * This class stores the forecast year taz data and builds the forecast control totals
 * 
 * This class was updated to be specific to ARC's forecast files
 * which use the same income bins as the v88 control configuration 
 * and also the household size data in the forecast files
 * Ben Stabler, stabler@pbworld.com, 9/3/10
 * 
 * HH workers calculated from worker percent lookup table and hh age of head from PUMS
 * HH age of head to persons age cross tab
 * Ben Stabler, stabler@pbworld.com, 11/5/12
 * 
 */
public class ForecastTazData implements TazData {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	
	// taz level data
	protected int [] tazNumber;
	protected int [] households;
	protected int [] persons;
	protected float [] incomeQ1;
	protected float [] incomeQ2;
	protected float [] incomeQ3;
	protected float [] incomeQ4;
	protected float [] hhSize1;
	protected float [] hhSize2;
	protected float [] hhSize3;
	protected float [] hhSize4;
	protected float [] hhSize5;
	protected float [] hhSize6p;
	protected float [] workers0;
	protected float [] workers1;
	protected float [] workers2;
	protected float [] workers3p;
	
	// regional level data
	protected long regionalPersons[];
	
	// control total data
	protected float [][] controlTazHhSize4;          // [taz][1,2,3,4+]
	protected float [][] controlTazIncQuartile;      // [taz][1,2,3,4]
	protected float [][] controlTazNumberWorkers;    // [taz][0,1,2,3+]
	protected float [] controlRegionHhAge;           // householder age [15to24,25to34,35to44,45to54,55to64,65to74,75to84,85+]
	protected float [][] controlTotals;  // [number of controls][taz]

	Hashtable<Integer, Integer> extTazToRowIndex;
	TableDataSet forecastTazTable;
	HashMap<String,float[]> workersPercent;
	Matrix ageOfHead2Age;
	float[] hhsByAge;
	float totalInputHhs;
	
    /**
     * Constructor
     * reads in and stores the data
     */
    public ForecastTazData() {
    	    	
    	//setup readers and destination data structures
    	CSVFileReader csvReader;
    	csvReader = new CSVFileReader();
    	csvReader.setPattern("\\b\\s+"); //match at word boundary, space delimited
    	TableDataSet forecastHHTable = new TableDataSet();
    	forecastTazTable = new TableDataSet();
    	
    	//read in household table
    	//hshld{year}g.dat
    	//inc0-20, inc20-50, inc50-100, inc100+
    	//hh size  1,2,3,4,5,6+
    	//fields: taz, inc1hhs1,inc1hhs2,...    	 
    	String forecastHHFile=(PropertyParser.getPropertyByName("converted.directory") + 
    			PropertyParser.getPropertyByName("Forecast.HHFile"));
    	try{
    		forecastHHTable = csvReader.readFile(new File(forecastHHFile), false);
    	} catch (IOException e){
    		logger.error("Unable to read Forecast.HHFile:" + forecastHHFile);
    		System.exit(1);
    	}

    	//read in land use table
    	//nwtaz{year}g.prn
    	//Zone, Constr emp, Manu emp, TCU emp, Wholesale emp, retail emp, Fire emp, 
    	//serv emp, total private emp, govt emp, govt2 emp, total emp, Population, 
    	//Households, univ enroll, Area (acres)
    	//get filenames to read in
    	String forecastLandUseFile=(PropertyParser.getPropertyByName("converted.directory") + 
    			PropertyParser.getPropertyByName("Forecast.LandUseFile"));
    	try{
    		forecastTazTable = csvReader.readFile(new File(forecastLandUseFile), false);
    	} catch (IOException e){
    		logger.error("Unable to read Forecast.LandUseFile:" + forecastLandUseFile);
    		System.exit(1);
    	}
    	

    	// read in Workers per HH lookup table
    	String fileName=(PropertyParser.getPropertyByName("converted.directory")+
    			                PropertyParser.getPropertyByName("Forecast.WorkersPercentFile"));

    	CSVFileReader CSVReader = new CSVFileReader();
    	TableDataSet workerPercentTable = new TableDataSet();
    	
    	try{
    		workerPercentTable = CSVReader.readFile(new File(fileName));
    	} catch (IOException e){
    		logger.error("Unable to read Forecast.WorkersPercentFile:" + workerPercentTable);
    		System.exit(1);
    	}
    	
    	// setup lookup table for worker percents
    	workersPercent = new HashMap<String,float[]>();
    	for(int i=0; i<workerPercentTable.getRowCount(); i++){
    		int size = workerPercentTable.getColumnAsInt(workerPercentTable.getColumnPosition("Size"))[i];
    		int income_group = workerPercentTable.getColumnAsInt(workerPercentTable.getColumnPosition("IncomeGroup"))[i];
    		
    		float[] pcts = new float[4];
    		pcts[0] = workerPercentTable.getColumnAsFloat(workerPercentTable.getColumnPosition("Workers0Percent"))[i];
    		pcts[1] = workerPercentTable.getColumnAsFloat(workerPercentTable.getColumnPosition("Workers1Percent"))[i];
    		pcts[2] = workerPercentTable.getColumnAsFloat(workerPercentTable.getColumnPosition("Workers2Percent"))[i];
    		pcts[3] = workerPercentTable.getColumnAsFloat(workerPercentTable.getColumnPosition("Workers3Percent"))[i] + 
    					workerPercentTable.getColumnAsFloat(workerPercentTable.getColumnPosition("Workers4Percent"))[i];

    		workersPercent.put(size + " " + income_group, pcts);
    	}
    	
    	// store regional data
    	regionalPersons = new long[9];
    	regionalPersons[0] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons0to14")).longValue();
    	regionalPersons[1] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons15to24")).longValue();
    	regionalPersons[2] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons25to34")).longValue();
    	regionalPersons[3] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons35to44")).longValue();
    	regionalPersons[4] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons45to54")).longValue();
    	regionalPersons[5] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons55to64")).longValue();
    	regionalPersons[6] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons65to74")).longValue();
    	regionalPersons[7] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons75to84")).longValue();
    	regionalPersons[8] = new Long(PropertyParser.getPropertyByName("Forecast.RegionalPersons85plus")).longValue();
    	    	
    	// read in persons by age by age of head table
    	fileName=(PropertyParser.getPropertyByName("converted.directory")+
    			                PropertyParser.getPropertyByName("Forecast.PersonsByHHAgeOfHeadFile"));

    	CSVReader = new CSVFileReader();
    	TableDataSet ageOfHead2AgeTable = new TableDataSet();
    	
    	try{
    		ageOfHead2AgeTable = CSVReader.readFile(new File(fileName));
    	} catch (IOException e){
    		logger.error("Unable to read Forecast.PersonsByHHAgeOfHeadFile:" + ageOfHead2AgeTable);
    		System.exit(1);
    	}
    	
    	// get regional age of head data
    	ageOfHead2Age = new Matrix(regionalPersons.length,regionalPersons.length);
    	for(int i=0; i<regionalPersons.length; i++){
    		for(int j=0; j<regionalPersons.length; j++) {
    			ageOfHead2Age.setValueAt(i+1, j+1, ageOfHead2AgeTable.getColumnAsFloat(j+2)[i]); //1-based indexing
    		}
    	}
    	
    	//get hhs by age of head to calculate persons per hh by age of head bin
    	hhsByAge = ageOfHead2AgeTable.getColumnAsFloat(ageOfHead2AgeTable.getColumnPosition("HHs"));
    	
    	// get all the column data in the land use file
    	tazNumber  = forecastTazTable.getColumnAsInt(1);
    	persons    = forecastTazTable.getColumnAsInt(13);
    	households = forecastTazTable.getColumnAsInt(14);
    	totalInputHhs = forecastTazTable.getColumnTotal(14);
    	
    	//get the income distribution from the hh file
    	incomeQ1 = new float[tazNumber.length];
    	incomeQ2 = new float[tazNumber.length];
    	incomeQ3 = new float[tazNumber.length];
    	incomeQ4 = new float[tazNumber.length];
    	
    	//get the hh size distribution from the hh file
    	hhSize1 = new float[tazNumber.length];
    	hhSize2 = new float[tazNumber.length];
    	hhSize3 = new float[tazNumber.length];
    	hhSize4 = new float[tazNumber.length];
    	hhSize5 = new float[tazNumber.length];
    	hhSize6p = new float[tazNumber.length];
    	
    	//worker distribution for hh file and lookup table
    	workers0 = new float[tazNumber.length];
    	workers1 = new float[tazNumber.length];
    	workers2 = new float[tazNumber.length];
    	workers3p = new float[tazNumber.length];
    	
    	for(int i=0;i<tazNumber.length;++i){
    		incomeQ1[i] =   forecastHHTable.getColumnAsFloat(2)[i] + 
			 				forecastHHTable.getColumnAsFloat(3)[i] + 
	 						forecastHHTable.getColumnAsFloat(4)[i] +
 							forecastHHTable.getColumnAsFloat(5)[i] +
							forecastHHTable.getColumnAsFloat(6)[i] +
							forecastHHTable.getColumnAsFloat(7)[i];
    		
    		incomeQ2[i] =   forecastHHTable.getColumnAsFloat(8)[i] + 
							forecastHHTable.getColumnAsFloat(9)[i] + 
							forecastHHTable.getColumnAsFloat(10)[i] +
							forecastHHTable.getColumnAsFloat(11)[i] +
							forecastHHTable.getColumnAsFloat(12)[i] +
							forecastHHTable.getColumnAsFloat(13)[i];
    		
    		incomeQ3[i] =   forecastHHTable.getColumnAsFloat(14)[i] + 
							forecastHHTable.getColumnAsFloat(15)[i] + 
							forecastHHTable.getColumnAsFloat(16)[i] +
							forecastHHTable.getColumnAsFloat(17)[i] +
							forecastHHTable.getColumnAsFloat(17)[i] +
							forecastHHTable.getColumnAsFloat(18)[i];
    		
    		incomeQ4[i] =   forecastHHTable.getColumnAsFloat(19)[i] + 
							forecastHHTable.getColumnAsFloat(20)[i] + 
							forecastHHTable.getColumnAsFloat(21)[i] +
							forecastHHTable.getColumnAsFloat(22)[i] +
							forecastHHTable.getColumnAsFloat(23)[i] +
							forecastHHTable.getColumnAsFloat(24)[i];
    		
    		hhSize1[i] =    forecastHHTable.getColumnAsFloat(2)[i] + 
    						forecastHHTable.getColumnAsFloat(8)[i] + 
    						forecastHHTable.getColumnAsFloat(14)[i] +
    						forecastHHTable.getColumnAsFloat(20)[i];

    		hhSize2[i] =    forecastHHTable.getColumnAsFloat(3)[i] + 
							forecastHHTable.getColumnAsFloat(9)[i] + 
							forecastHHTable.getColumnAsFloat(15)[i] +
							forecastHHTable.getColumnAsFloat(21)[i];
    		
    		hhSize3[i] =    forecastHHTable.getColumnAsFloat(4)[i] + 
							forecastHHTable.getColumnAsFloat(10)[i] + 
							forecastHHTable.getColumnAsFloat(16)[i] +
							forecastHHTable.getColumnAsFloat(22)[i];
    		
    		hhSize4[i] =    forecastHHTable.getColumnAsFloat(5)[i] + 
							forecastHHTable.getColumnAsFloat(11)[i] + 
							forecastHHTable.getColumnAsFloat(17)[i] +
							forecastHHTable.getColumnAsFloat(23)[i];
    		
    		hhSize5[i] =    forecastHHTable.getColumnAsFloat(6)[i] + 
							forecastHHTable.getColumnAsFloat(12)[i] + 
							forecastHHTable.getColumnAsFloat(18)[i] +
							forecastHHTable.getColumnAsFloat(24)[i];
    		
    		hhSize6p[i] =    forecastHHTable.getColumnAsFloat(7)[i] + 
							forecastHHTable.getColumnAsFloat(13)[i] + 
							forecastHHTable.getColumnAsFloat(19)[i] +
							forecastHHTable.getColumnAsFloat(25)[i];
    		
    		//hhs by workers 
    		int[] sizes = {1,2,3,4,5,6};
    		int[] incomes = {1,2,3,4};
    		int startColumn = 2;
    		float[] hhsByNumWorkers = new float[4];
    		for(int size : sizes) {
    			for(int income : incomes) {
    				hhsByNumWorkers = getWorkersForSizeIncomeGroup(forecastHHTable.getColumnAsFloat(startColumn)[i], size + " " + income);
    				workers0[i] = workers0[i] + hhsByNumWorkers[0];
    				workers1[i] = workers1[i] + hhsByNumWorkers[1];
    				workers2[i] = workers2[i] + hhsByNumWorkers[2];
    				workers3p[i]= workers3p[i] + hhsByNumWorkers[3];
    				startColumn = startColumn + 1;
    			}
    		}
    		
    	}
    	
    	// build the hashMap has a cross walk between the tazNumber and column index
    	extTazToRowIndex = new Hashtable<Integer,Integer>(tazNumber.length);
    	for(int i=0;i<tazNumber.length;++i){
    		int row = i;
    		extTazToRowIndex.put(tazNumber[i],row);
    	}
    	
    }
    
    /**
     * computeControlTotals
     * computes marginal control totals to be used by the Balancer
     * @param number of tazs, the controls from the pums data, TableDataReader of tables
     */
    public void computeControlTotals(int numberOfInternalZones, long [] forecastControlData, 
    		                         TableDataReader designTables){
    	
        // get all the "global" controls first, and then set the controls array

    	// 1. household size
    	controlTazHhSize4 = new float[numberOfInternalZones][4]; // 1, 2, 3, 4+
    	for(int i=0;i<numberOfInternalZones;++i)
    	{
    		int extTAZ    = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1);
    		controlTazHhSize4[i][0] = (float) this.getNumberOfHHSize1(extTAZ);
    		controlTazHhSize4[i][1] = (float) this.getNumberOfHHSize2(extTAZ);
    		controlTazHhSize4[i][2] = (float) this.getNumberOfHHSize3(extTAZ);
    		controlTazHhSize4[i][3] = (float) this.getNumberOfHHSize4(extTAZ) + 
    			this.getNumberOfHHSize5(extTAZ) + this.getNumberOfHHSize6p(extTAZ);
    	}
    	
    	// 2. household income quartiles (no modifications needed, just store in array)
    	controlTazIncQuartile = new float[numberOfInternalZones][4];
    	for(int i=0;i<numberOfInternalZones;++i)
    	{
    		int extTAZ    = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1);
    		controlTazIncQuartile[i][0] = (float) this.getNumberOfIncomeQ1(extTAZ);
    		controlTazIncQuartile[i][1] = (float) this.getNumberOfIncomeQ2(extTAZ);
    		controlTazIncQuartile[i][2] = (float) this.getNumberOfIncomeQ3(extTAZ);
    		controlTazIncQuartile[i][3] = (float) this.getNumberOfIncomeQ4(extTAZ);
    	}
    	
    	// 3. number of workers per hh calculated from workers percent lookup by size and income
    	controlTazNumberWorkers = new float[numberOfInternalZones][4];
    	for(int i=0;i<numberOfInternalZones;++i)
    	{
    		int extTAZ    = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1);
    		controlTazNumberWorkers[i][0] = (float) this.getNumberOfWorkers0(extTAZ);
    		controlTazNumberWorkers[i][1] = (float) this.getNumberOfWorkers1(extTAZ);
    		controlTazNumberWorkers[i][2] = (float) this.getNumberOfWorkers2(extTAZ);
    		controlTazNumberWorkers[i][3] = (float) this.getNumberOfWorkers3p(extTAZ);
    	}
        
    	
        // 4. number of householders in age categories
    	
    	//calculate forecasts persons by age to PUMS persons by age adjustment factor
    	//apply to households by age crosstabs to get new hhs by age totals and divide by avg persons per hh by age cat
    	float[] persPerHHAgeCat = new float[regionalPersons.length];
    	for(int i=0; i<regionalPersons.length; i++) {
    		persPerHHAgeCat[i] = ageOfHead2Age.getRowSum(i+1) / hhsByAge[i];
    	}
    	
    	controlRegionHhAge = new float[regionalPersons.length-1]; //there is no control for householder age 0to14
    	for(int i=0; i<regionalPersons.length; i++) {
    		float adjFactor = regionalPersons[i] / ageOfHead2Age.getColumnSum(i+1);
    		ageOfHead2Age.setColumn(ageOfHead2Age.getColumn(i+1).multiply(adjFactor).getColumn(1), i+1);
    	}
    	for(int i=0; i<regionalPersons.length; i++) {
    		if(i>0) { 
    			controlRegionHhAge[i-1] = ageOfHead2Age.getRowSum(i+1) / persPerHHAgeCat[i];
    			logger.info(String.format("hhagecat8: %d, persons: %.0f, base pers per hh: %.2f, hhs: %.0f", i, ageOfHead2Age.getRowSum(i+1), persPerHHAgeCat[i], controlRegionHhAge[i-1]));
    		}
    	}
    	//scale hhs by age controls to match input total households    	
    	float totalHHsFromAgeControl = 0;
    	for(int i=0; i<controlRegionHhAge.length; i++) {    		
    		totalHHsFromAgeControl = totalHHsFromAgeControl + controlRegionHhAge[i];  
    	}
    	for(int i=0; i<controlRegionHhAge.length; i++) {    		
    		controlRegionHhAge[i] = controlRegionHhAge[i] * (totalInputHhs / totalHHsFromAgeControl);
    	}
    	
        // build an array of control totals
        
        // get the controls design table
    	TableDataSet controlDesign = designTables.getTable("ForecastControlManager.csv");
    	int numberOfControls = new Float 
    	                      (controlDesign.getColumnTotal(controlDesign.getColumnPosition("switch"))).intValue();
    	
    	int [] levers = controlDesign.getColumnAsInt(controlDesign.getColumnPosition("switch"));
    	
    	// loop through the levers array and make an indexer array
    	int [] controlIndex = new int[levers.length];
    	int counter = 0;
    	
    	for(int i=0;i<levers.length;++i){
    		if(levers[i]==1){
    			controlIndex[i] = counter;
    			counter++;
    		}
    	}
    	
    	controlTotals = new float[numberOfControls][numberOfInternalZones];
        
        for(int i=0;i<numberOfInternalZones;++i){
        
        	// hh size 4+
        	if(levers[0]==1) controlTotals[controlIndex[0]][i] = controlTazHhSize4[i][0];
        	if(levers[1]==1) controlTotals[controlIndex[1]][i] = controlTazHhSize4[i][1];
        	if(levers[2]==1) controlTotals[controlIndex[2]][i] = controlTazHhSize4[i][2];
        	if(levers[3]==1) controlTotals[controlIndex[3]][i] = controlTazHhSize4[i][3];
        	
        	// hh income controls 
        	if(levers[4]==1) controlTotals[controlIndex[4]][i] = controlTazIncQuartile[i][0];
        	if(levers[5]==1) controlTotals[controlIndex[5]][i] = controlTazIncQuartile[i][1];
        	if(levers[6]==1) controlTotals[controlIndex[6]][i] = controlTazIncQuartile[i][2];
        	if(levers[7]==1) controlTotals[controlIndex[7]][i] = controlTazIncQuartile[i][3];
        	
        	// number of worker controls
            if(levers[8]==1) controlTotals[controlIndex[8]][i] = controlTazNumberWorkers[i][0];
            if(levers[9]==1) controlTotals[controlIndex[9]][i] = controlTazNumberWorkers[i][1];
            if(levers[10]==1) controlTotals[controlIndex[10]][i] = controlTazNumberWorkers[i][2];
            if(levers[11]==1) controlTotals[controlIndex[11]][i] = controlTazNumberWorkers[i][3];
        } 
        
        // regional controls (put in zero location)
        
        // number of householder age controls
        if(levers[12]==1) controlTotals[controlIndex[12]][0] = controlRegionHhAge[0];
        if(levers[13]==1) controlTotals[controlIndex[13]][0] = controlRegionHhAge[1];
        if(levers[14]==1) controlTotals[controlIndex[14]][0] = controlRegionHhAge[2];
        if(levers[15]==1) controlTotals[controlIndex[15]][0] = controlRegionHhAge[3];
    	if(levers[16]==1) controlTotals[controlIndex[16]][0] = controlRegionHhAge[4];
        if(levers[17]==1) controlTotals[controlIndex[17]][0] = controlRegionHhAge[5];
    	if(levers[18]==1) controlTotals[controlIndex[18]][0] = controlRegionHhAge[6];
    	if(levers[19]==1) controlTotals[controlIndex[19]][0] = controlRegionHhAge[7];
        
    }
    
    public float[] getWorkersForSizeIncomeGroup(float households, String sizeIncomeGroupKey) {
    	
    	float[] householdsByWorkerPercents = workersPercent.get(sizeIncomeGroupKey);
    	float[] householdsByWorkers = new float[householdsByWorkerPercents.length];
    	for(int i=0; i<householdsByWorkers.length; i++) {
    		householdsByWorkers[i] = households * householdsByWorkerPercents[i];
    	}
    	return(householdsByWorkers);
    }
        
    private int getNumberOfPersons(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return persons[arrayRow];
    }
    
    private float getNumberOfIncomeQ1(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return incomeQ1[arrayRow];
    }
    
    private float getNumberOfIncomeQ2(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return incomeQ2[arrayRow];
    }
    
    private float getNumberOfIncomeQ3(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return incomeQ3[arrayRow];
    }
    
    private float getNumberOfIncomeQ4(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return incomeQ4[arrayRow];
    }
    
    private float getNumberOfHHSize1(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return hhSize1[arrayRow];
    }
 
    private float getNumberOfHHSize2(int extTAZ){
 	
 	int arrayRow = extTazToRowIndex.get(extTAZ);
 	return hhSize2[arrayRow];
    }
 
    private float getNumberOfHHSize3(int extTAZ){
 	
 	int arrayRow = extTazToRowIndex.get(extTAZ);
 	return hhSize3[arrayRow];
    }
 
    private float getNumberOfHHSize4(int extTAZ){
 	
 	int arrayRow = extTazToRowIndex.get(extTAZ);
 	return hhSize4[arrayRow];
    }
 
    private float getNumberOfHHSize5(int extTAZ){
 	
 	int arrayRow = extTazToRowIndex.get(extTAZ);
 	return hhSize5[arrayRow];
    }
 
    private float getNumberOfHHSize6p(int extTAZ){
 	
 	int arrayRow = extTazToRowIndex.get(extTAZ);
 	return hhSize6p[arrayRow];
    }
    
    private float getNumberOfWorkers0(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return workers0[arrayRow];
    }
    
    private float getNumberOfWorkers1(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return workers1[arrayRow];
    }
    
    private float getNumberOfWorkers2(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return workers2[arrayRow];
    }    
    
    private float getNumberOfWorkers3p(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return workers3p[arrayRow];
    }
            
    public float[][] getControlTotals(){
    	
    	return controlTotals;
    }
    
    public int getNumberOfHouseholds(int extTAZ){
    	
    	int arrayRow = extTazToRowIndex.get(extTAZ);
    	return households[arrayRow];
    }
  
}

    
