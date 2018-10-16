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

import com.pb.common.datafile.TableDataSet;
import com.pb.common.matrix.NDimensionalMatrixDouble;
// import com.pb.morpc.synpop.pums2000.DataDictionary;
import java.util.Vector;
import java.util.Random;
import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.0, Nov. 20, 2003
 * 
 * A control table example:
 * --------------------------------------------------------------------------------------------
 * Control ID     D1CCat     D2Cat(TAZ)     Target     CurrentControl	PreviousControl	pDelta
 * --------------------------------------------------------------------------------------------
 * 1              1          	1			---
 * 2              1          	2			---
 * 3              1          	3
 * ...															EXTENDED AREA FROM ControlTable
 * 116	          1	        	116
 * 117			  2             1
 * 118			  2				2
 * 119			  2				3
 * ...			  ...			...			...
 * 232			  2				116			---
 * 233			  3             0*
 * ...
 * 
 * NControl=116X1683 if no aggregation on D2 category 
 * NControl<116X1683 if aggregation on D2 category
 * 
 * * If D2Cat=0, this control is an aggregated control
 * --------------------------------------------------------------------------------------------
 */
public class ControlTableBalancer {
	
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    //a control table with columns
    protected ControlTable controlTable;
    //"D1CCat" column in control table
    protected Vector D1CCat=new Vector();
    //"D2Cat" column in control table
    protected Vector D2Cat=new Vector();
    //"target" column in control table
    protected float[] targets;
    //"current" column in control table
    protected float[] currentControl;
    //hold previous control values for calculating pDelta
    protected float[] previousControl;
    //"pDelta" column in control table
    protected float[] pDelta;
    //current cells matrix
    protected NDimensionalMatrixDouble currentCells;
    //hold previous cell values for updating cells matrix
    protected NDimensionalMatrixDouble previousCells;
    //d1Incidence (read in from txt file)
    protected TableDataSet d1Incidence;
    //controlInput (read in from txt file)
    protected TableDataSet controlInput;
    //a connection matrix between control table and cell table
    protected NDimensionalMatrixDouble controlCellIncidence;
    //seed distribution
    protected NDimensionalMatrixDouble seedDistribution;    
    //number of dimension 1 control categories (control categories, 116 for base year)
    int ND1CCat;
    //number of dimension 2 categories (Number of TAZs, 1683)
    int ND2Cat;
    //number of dimension 1 segment categories (Household categories, 316)
    int ND1SCat;
    //number of controls in control table
    int NControl;
    //number of dimensions
    int dimensions;


    /**
     * constructor
     * @param seedDistribution represents a seed distribution [ND1SCat][ND2Cat] to be balanced (a [316][1683] array)
     * @param controlTable represents ControlTable object
     */
    public ControlTableBalancer(NDimensionalMatrixDouble seedDistribution, ControlTable controlTable) {
    	
    	this.controlTable=controlTable;
        this.seedDistribution = seedDistribution;
        
        //get target column from control table
        targets = controlTable.getTargetsArray();

        //number of dimension 1 control category, 116
        ND1CCat=controlTable.getND1CCat();
        //number of dimension 1 segment category, for ARC base year 316, for ARC base year meta 116
        ND1SCat=controlTable.getND1SCat();
        //number of dimension 2 category, 1683
        ND2Cat=controlTable.getND2Cat();      
        //number of control in control table
        NControl=controlTable.getNoControls();
        
        D1CCat=controlTable.getD1CCat();
        D2Cat=controlTable.getD2Cat();
        
        //incidence table, except last row
        d1Incidence=controlTable.getD1Incidence();
        //last row of incidence table
        controlInput=controlTable.getControlInput();

        //initialize controlCellIncidence matrix, [316][1683]
        int[] shape = { ND1SCat, ND2Cat };

        //dimensions
        dimensions = shape.length;
        controlCellIncidence = new NDimensionalMatrixDouble("controlCellIncidence matrix",
                dimensions, shape);

        currentControl=new float[NControl];
        previousControl=new float[NControl];
        pDelta=new float[NControl];

        //initialize current control and previous control
        for (int i = 0; i < NControl; i++) {
            currentControl[i] = 0.0f;
            previousControl[i] = 0.0f;
        }

        //initialize current cells and previous cells
        currentCells = seedDistribution;
        previousCells = seedDistribution;
    }
    
    /**
     * balance seed distribution and return balanced matrix
     * @return
     */
    public NDimensionalMatrixDouble getBalancedSeedDistribution(){
    	balanceControls();
    	return currentCells;
    }
    
    /**
     * return balanced seed as a 2D array
     * @return
     */
    public double [][] getBalancedSeedArray(){
    	int [] shape=currentCells.getShape();
    	double [][] result=new double[shape[0]][shape[1]];
    	balanceControls();
    	for(int i=0; i<shape[0]; i++){
    		for(int j=0; j<shape[1]; j++){
    			int [] position={i,j};
    			result[i][j]=currentCells.getValue(position);
    		}
    	}
    	return result;
    }
    
    /**
     * balance controls
     */
    public void balanceControls() {
        boolean converge = false;
        int count=0;
        float minDivision=(new Float(PropertyParser.getPropertyByName("minDivision"))).floatValue();
        float convergenceCriteria=(new Float(PropertyParser.getPropertyByName("convergenceCriteria"))).floatValue();

        double bigError;
        double holder;
        
        while (!converge) {
        	bigError = 0.0;
            boolean oneNotMet = false;
            count++;
            		                                 
            for (int i = 0; i < NControl; i++) {
                previousControl[i] = currentControl[i];

                // perhaps wu's greatest mystery here. not sure why he needs to set the
                // control incidence matrix for each control, but he previously only did
                // it for the first big iteration (count==1), so for now, i'll sacrifice
                // a bit of runtime and do it each time (dto)
                setControlCellIncidence(i);
                
                calCurrentControl(i);
                
                updateCells(i);
                                
                if(Math.abs(previousControl[i])<0.000001){
                    pDelta[i] = (currentControl[i] - previousControl[i]) / minDivision;
                }else{
                	pDelta[i] = (currentControl[i] - previousControl[i]) / previousControl[i];
                }
              
                // check criteria for each control
                holder = pDelta[i];
                if(pDelta[i]<0.0) holder=(-1.0)*pDelta[i];
                if(holder>bigError)bigError = holder;
                if (holder > convergenceCriteria) oneNotMet = true;               	
                    
            }

            logger.info("IPF iteration "+count+" complete; largest error: " + bigError);

            if (!oneNotMet) {
                converge = true;
            }
        }
    }
    
    /**
     * write balanced matrix to disk
     * @param fileLocation
     */
    public void writeBalancedMatrix(String fileLocation){
    	NDimensionalMatrixWriter writer=new NDimensionalMatrixWriter(currentCells);
    	writer.write(fileLocation);
    }


    /**
     * Set controlCellIncidence matrix for a given control
     * @param controlID represents control ID, it starts from 0
     */
    private void setControlCellIncidence(int controlID) {
        int D2CatValue = ((Integer) D2Cat.get(controlID)).intValue();
        int D1CCatValue = ((Integer) D1CCat.get(controlID)).intValue();
        
        if(D2CatValue!=0){
        	for(int i=1; i<ND1SCat+1; i++){
                int[] positionInControlCellIncidence = { i-1, D2CatValue-1 };
                //d1Incidence is a TableDataSet with row: HHCat, column: D1CCat (Control Cat), both are 1-based
                //controlCellIncidence is a NDimensionalMatrix object with row: HHCat, column: ND2Cat (TAZ), both are 0-based
        		controlCellIncidence.setValue(d1Incidence.getValueAt(i,D1CCatValue),positionInControlCellIncidence);
        	}
        }else{
	        //i and j both start from 1
	        for (int i = 1; i < ND1SCat+1; i++) {
	            for (int j = 1; j < ND2Cat+1; j++) {
	                //i and j both minus 1 because controlCellIncidence is a NDimensionalMatrix, and its index starts from 0
	                int[] positionInControlCellIncidence = { i-1, j-1 };
	                //in d1Incidence, i is the 1st dimension, D1CCatValue is the 2nd dimension; not as in John's psuedo code
	                controlCellIncidence.setValue(d1Incidence.getValueAt(i,D1CCatValue), positionInControlCellIncidence);
	            }
	        }
        }
    }

    /**
     * calculate current control vale for a given control
     * @param controlID represents a control ID
     */
    private void calCurrentControl(int controlID) {
        int D2CatValue = ((Integer) D2Cat.get(controlID)).intValue();
        int[] position = new int[dimensions];
        currentControl[controlID]=0.0f;

        if(D2CatValue!=0){
            for (int i = 1; i < ND1SCat+1; i++) {
	            //i and D2CatValue both minus 1 because currentCells and controlCellIncidence are both NDimensionalMatrix, index starts from 0
	            position[0] = i-1;
	            position[1]=D2CatValue-1;
                double currentCellValue=currentCells.getValue(position);
                double controlCellIncidenceValue=controlCellIncidence.getValue(position);
                currentControl[controlID] += currentCellValue * controlCellIncidenceValue;
            }
            
        }else{
	        for (int i = 1; i < ND1SCat+1; i++) {
	            for (int j = 1; j < ND2Cat+1; j++) {
	                //i and j both minus 1 because currentCells and controlCellIncidence are both NDimensionalMatrix, index starts from 0
	                position[0] = i-1;
	                position[1] = j-1;
	                double currentCellValue=currentCells.getValue(position);
	                double controlCellIncidenceValue=controlCellIncidence.getValue(position);
	                currentControl[controlID] += currentCellValue * controlCellIncidenceValue;
	            }
	        }
        }
    }

    /**
     * update cell matrix for a given control
     * @param controlID represents a control ID
     */
    private void updateCells(int controlID) {
    	
        int D2CatValue = ((Integer) D2Cat.get(controlID)).intValue();
        int[] position = new int[dimensions];
        double newCurrentCellValue = 0.0f;
        double controlCellIncidenceValue;
        
        float factor=-1;
        
        if(Math.abs(currentControl[controlID])<0.000001) factor = 1.0f;
        else factor=targets[controlID]/currentControl[controlID];
        
        if(D2CatValue!=0){
	        for (int i = 1; i < ND1SCat+1; i++) {
	        	position[0]=i-1;
	        	position[1]=D2CatValue-1;
                previousCells.setValue(currentCells.getValue(position), position);
                controlCellIncidenceValue=controlCellIncidence.getValue(position);
                if(controlCellIncidenceValue==1.0){
	                newCurrentCellValue =previousCells.getValue(position)*factor;
	                currentCells.setValue(newCurrentCellValue, position);
                }
	        }
        }else{
	        //i and j both start from 1
	        for (int i = 1; i < ND1SCat+1; i++) {
	            for (int j = 1; j < ND2Cat+1; j++) {
	                //i and j both minus 1, because previousCells and currentCells are both NDimensionalMatrix, index starts from 0
	                position[0] = i-1;
	                position[1] = j-1;
	                previousCells.setValue(currentCells.getValue(position), position);
	                controlCellIncidenceValue=controlCellIncidence.getValue(position);
	                if(controlCellIncidenceValue==1.0){
	                  newCurrentCellValue =previousCells.getValue(position)*factor;
	                  currentCells.setValue(newCurrentCellValue, position);
	               }
	            }
	        }
        }
    }
    
    /*
     * convert a 2D float array to a 2D double array
     * @param fArray
     * @return
     */
    /*
    private double [][] convertFloatArrayToDoubleArray(float [][] fArray){
    	double [][] result=new double[fArray.length][fArray[0].length];
    	for(int i=0; i<fArray.length; i++){
    		for(int j=0; j<fArray[0].length; j++){
    			result[i][j]=fArray[i][j];
    		}
    	}
    	return result;
    }
    */

    
    public static void main(String[] args) {
    	
        Random randomGenerator = new Random(0);
    	double runningTime0=System.currentTimeMillis();
        
		//census table converted to TAZ-based tables here
		TableDataManager tableDataManager=new TableDataManager();
        double runningTime1 = System.currentTimeMillis() - runningTime0;
        logger.info ("TableDataManager took = " + (float)((runningTime1/1000.0)/60.0));
								
	  	DataDictionary dd=new DataDictionary(PropertyParser.getPropertyByName("pums.directory")+PropertyParser.getPropertyByName("pums.dictionary"), 5, 120, 170);
        DerivedHHFactory factory = new DerivedHHFactory(); 
        PUMSData pumsdata=new PUMSData(dd, tableDataManager.getTAZtoPUMAIndex(), factory);
        double runningTime2 = System.currentTimeMillis() - runningTime1;
        logger.info ("PUMSData took = " + (float)((runningTime2/1000.0)/60.0));
        
      	PUMSBucketGroup buckets=new PUMSBucketGroup(pumsdata, tableDataManager.getTAZtoPUMAIndex(),randomGenerator);
	  	BaseSeedDistributionGenerator bsg=new BaseSeedDistributionGenerator(tableDataManager, buckets);
        double runningTime3 = System.currentTimeMillis() - runningTime2;
        logger.info ("BaseSeedDistributionGenerator took = " + (float)((runningTime3/1000.0)/60.0));
        
        BaseTargetGenerator btg=new BaseTargetGenerator(tableDataManager);
        double runningTime4 = System.currentTimeMillis() - runningTime3;
        logger.info ("BaseTargetGenerator took = " + (float)((runningTime4/1000.0)/60.0));
        
    	ControlTable controlTable=new ControlTable("base", btg.getTargets(), tableDataManager.getTableReader("converted"));
        ControlTableBalancer ctb = new ControlTableBalancer(bsg.getBaseSeedDistributionNMatrix(), controlTable);
        
        ctb.balanceControls();
        
        String dir=PropertyParser.getPropertyByName("interimResult.directory");
        String balancedBaseMetaSeedDistribution=PropertyParser.getPropertyByName("BalancedBaseMetaSeedDistribution");
        ctb.writeBalancedMatrix(dir+balancedBaseMetaSeedDistribution);   	
 
        double runningTime5 = System.currentTimeMillis() - runningTime4;
        logger.info ("balance table took = " + (float)((runningTime5/1000.0)/60.0));
        /*       
        float [] targets={1000.0f, 2000.0f, 3000.0f,1200.0f, 1700.f,3200.f};
        seedDistribution[0][0]=300.0;
        seedDistribution[0][1]=600.0;
        seedDistribution[0][2]=900.0;
        seedDistribution[1][0]=800.0;
        seedDistribution[1][1]=1600.0;
        seedDistribution[1][2]=2400.0;
        seedDistribution[2][0]=700.0;
        seedDistribution[2][1]=1400.0;
        seedDistribution[2][2]=2100.0;
        seedDistribution[3][0]=800.0;
        seedDistribution[3][1]=1600.0;
        seedDistribution[3][2]=2400.0;
        seedDistribution[4][0]=1500.0;
        seedDistribution[4][1]=3000.0;
        seedDistribution[4][2]=4500.0;
        */
    }
}
