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
import java.util.Vector;
import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * <sunw@pbworld.com>
 * @version 1.0, Jan. 5, 2003
 *
 * A control table example:
 * ---------------------------------------------------
 * Control ID     D1CCat     D2Cat(TAZ)     Target     
 * ---------------------------------------------------
 * 1              1          	1			---
 * 2              1          	2			---
 * 3              1          	3
 * ...
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
 * ------------------------------------------------------
 * 
 * 4 Control Tables: 
 * 1) base year source data
 * 2) base year meta data 
 * 3) future year source data
 * 4) future year meta data
 * 
 * To create a control table, this class needs "d1Incidence.file" and "controlInput.file".
 * 
 * "d1Incidence.file": 
 * 		incidence matirix defined in control incidence Excel sheets for
 * 		base, base MetaTarget, future, and future MetaTarget scenarios
 * "controlInput.file": 
 * 		last row vector of "d1Incidence.file"
 * 
 * These 2 files need to be defined in property file for each of the 4 control tables.
 */

public class ControlTable {

  protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
  
  //d1Incidence (read in from txt file)
  protected TableDataSet d1Incidence;
  //controlInput (read in from txt file)
  protected TableDataSet controlInput;
  //number of dimension 1 segment category (for ARC base year 316, for ARC base year meta 116)
  protected int ND1SCat;
  //number of dimension 1 control categories (control categories, 116)
  protected int ND1CCat;
  //number of dimension 2 categories (TAZs, 1683)
  protected int ND2Cat;
  //number of controls in control table
  protected int NControl;
  
  //control ID array, 1st col in control table
  protected Vector ID;
  //control D1CCat array, 2nd col in control table
  protected Vector D1CCat;
  //control D2Cat array, 3rd col in control table
  protected Vector D2Cat;
  //targets, 4th col in control table
  protected Vector targets;
  
  //raw 2D target array [ND1CCat][ND2Cat], for ARC [116][1683]
  protected double [][] rawTargets;
  
  //protected CSVFileWriter writer;
  
  protected TableDataReader designTableReader;
  
  /**
   * constructor
   * @param type represents control table type, "base", "baseMeta","future", or "futureMeta"
   * @param rawTargets represent control targets by dimenstion 1 control category (116) and
   * dimension 2 category (TAZ, 1683)
   * 
   * Note: rawTargets is from target generators (BaseTargetGenerator, MetaTargetGenerator, etc.)
   */

  public ControlTable(String type, double [][] rawTargets, TableDataReader designTableReader) {
  	
  	this.rawTargets=rawTargets;
  	this.designTableReader=designTableReader;
  	
  	String incidenceFile=type+"Incidence.csv";
  	String incidenceLastRow=type+"IncidenceLastRow.csv";
  	
  	//open dimension 1 incidence file
  	d1Incidence=designTableReader.getTable(incidenceFile);
    //open control input file (last incidence row)
  	controlInput=designTableReader.getTable(incidenceLastRow);
  		
    ND1SCat=d1Incidence.getRowCount();
  	ND1CCat = d1Incidence.getColumnCount();
    ND2Cat = PopulationSynthesizer.numberOfInternalZones;
    
    //make control table
    makeControlTable();
    
  }

    /**
     * Constructor that accepts and converts float[][].
     * 
     * @param type
     *            represents control table type, "base", "baseMeta","future", or
     *            "futureMeta"
     * @param rawTargets
     *            represent control targets by dimenstion 1 control category
     *            (116) and dimension 2 category (TAZ, 1683)
     * 
     * Note: rawTargets is from target generators (BaseTargetGenerator,
     * MetaTargetGenerator, etc.)
     */
    public ControlTable(String type, float[][] rawTargets,
            TableDataReader designTableReader) {

    	double[][] dArray = new double[rawTargets.length][];
		
		// change error in counter (dto); added second dimension
		for (int i = 0; i < rawTargets.length; ++i) {
			dArray[i] = new double [rawTargets[i].length];
			for (int j = 0; j < rawTargets[i].length; ++j) {
				dArray[i][j] = rawTargets[i][j];
			}
		}


		this.rawTargets = dArray;
		this.designTableReader = designTableReader;

		String incidenceFile = type + "Incidence.csv";
		String incidenceLastRow = type + "IncidenceLastRow.csv";

		// open dimension 1 incidence file
		d1Incidence = designTableReader.getTable(incidenceFile);
		// open control input file (last incidence row)
		controlInput = designTableReader.getTable(incidenceLastRow);

		ND1SCat = d1Incidence.getRowCount();
		ND1CCat = d1Incidence.getColumnCount();
		ND2Cat = PopulationSynthesizer.numberOfInternalZones;

		// make control table
		makeControlTable();
	}
  
  /**
	 * get targets as a vector
	 * 
	 * @return
	 */
  public Vector getTargets(){
  	return targets;
  }
  
  /**
   * get targets as an array
   * @return
   */
  public float [] getTargetsArray(){
  	float [] result=new float[targets.size()];
  	for(int i=0; i<targets.size(); i++){
  		result[i]=((Float)targets.get(i)).floatValue();
  	}
  	return result;
  }
  
  /**
   * get dimension 1 control categories
   * @return
   */
  public Vector getD1CCat(){
  	return D1CCat;
  }
  
  /**
   * get dimension 2 categories (TAZs)
   * @return
   */
  public Vector getD2Cat(){
  	return D2Cat;
  }
  
  /**
   * get dimension 1 control category by control ID
   */
  public int getD1CCatByID(int ID){
    int result=((Integer)D1CCat.get(ID)).intValue();
    return result;
  }

  /**
   * get dimension 2 category (TAZ) by control ID
   * @param ID
   * @return
   */
  public int getD2CatByID(int ID){
    int result=((Integer)D2Cat.get(ID)).intValue();
    return result;
  }

  /**
   * get control ID by dimension 1 control category and dimension 2 category (TAZ)
   */
  public int getControlIDByD1CCatD2Cat(int D1CCat, int D2Cat){
    int result=-1;
    for(int i=0; i<ID.size(); i++){
      if(getD1CCatByID(i)==D1CCat&&getD2CatByID(i)==D2Cat){
        result = i;
        break;
      }
    }
    return result;
  }
  
  /**
   * get number of controls
   * @return
   */
  public int getNoControls(){
  	return NControl;
  }
  
  /**
   * get number of dimension 1 control categories
   * @return
   */
  public int getND1CCat(){
  	return ND1CCat;
  }
  
  /**
   * get number of dimension 2 categories
   * @return
   */
  public int getND2Cat(){
  	return ND2Cat;
  }
  
  /**
   * get number of dimension 1 segment category
   * @return
   */
  public int getND1SCat(){
  	return ND1SCat;
  }
  
  /**
   * get dimension 1 incidence table
   * @return
   */
  public TableDataSet getD1Incidence(){
  	return d1Incidence;
  }
  
  /**
   * get last row vector of dimension 1 incidence file
   * @return
   */
  public TableDataSet getControlInput(){
  	return controlInput;
  }
  
  private void makeControlTable() {
  	
    //initialize first 4 columns in control table
    ID=new Vector();
    D1CCat=new Vector();
    D2Cat=new Vector();
    targets=new Vector();
  	
    int newD1CCat = 0;
    int newD2Cat = 0;

    float aggregateIndex;
    float currentAggregateTarget;
    float[] controlInputVector = controlInput.getRowValues(1);
    
    //control counter
    int count=0;
    
    //make control table, important: i and j both start from 1 here
    for (int i = 1; i < ND1CCat+1; i++) {// for ARC, ND1CCat=116
        newD1CCat = i;
        //target aggregation index on D2 control categories (TAZs)
        aggregateIndex=controlInputVector[i-1];
        currentAggregateTarget=0;
        
        //index==0, then aggregate target, and increase count for each ND1CCat, but not for ND2Cat
        //index!=0, then don't aggregate target, and increase count for both ND1CCat and ND2Cat
        if(aggregateIndex==0){
        	//D2Cat is set to 0, because this is an aggregated control
        	newD2Cat=0;
        	//aggregate over D2 category (TAZ)
	        for (int j = 1; j < ND2Cat+1; j++) {
	        	currentAggregateTarget+=rawTargets[i-1][j-1];
	        }
	        //set first 4 colums of a control table, control ID starts from 0
            ID.add(new Integer(count));
            D1CCat.add(new Integer(newD1CCat));
            D2Cat.add(new Integer(newD2Cat));
            
            // add check for small targets (dto)
            if(currentAggregateTarget<0.001) targets.add(0.0f);
            else targets.add(new Float(currentAggregateTarget));  
            
            count++;
        }else{
	        for (int j = 1; j < ND2Cat+1; j++) {
	        	newD2Cat=j;
	            //control ID starts from 0
	            ID.add(new Integer(count));
	            D1CCat.add(new Integer(newD1CCat));
	            D2Cat.add(new Integer(newD2Cat));
	            
	            // add check for small targers (dto)
	            if(rawTargets[i-1][j-1]<0.001) targets.add(0.0f);
	            else targets.add(new Float(rawTargets[i-1][j-1]));  
	            
	            count++;
	        }       	
        }
    }

    //get number of controls
    NControl=ID.size();
  }

  //for testing purpose only
  //successfully tested Meta Targets on April 8, 2005
  public static void main(String [] args){
  	
  	/*
  	float [][] targets=new float[2][3];
  	targets[0][0]=1000;
  	targets[0][1]=2000;
  	targets[0][2]=3000;
  	targets[1][0]=1200;
  	targets[1][1]=1700;
  	targets[1][2]=3200;
  	*/
  	
  	TableDataManager tableDataManager=new TableDataManager();
  	BaseTargetGenerator btg=new BaseTargetGenerator(tableDataManager);
  	ControlTable table=new ControlTable("baseMeta", btg.getTargets(), tableDataManager.getTableReader("design"));
    Vector D1CCat=table.getD1CCat();
    Vector D2Cat=table.getD2Cat();
    logger.info("NControl="+table.getNoControls());
  }
}