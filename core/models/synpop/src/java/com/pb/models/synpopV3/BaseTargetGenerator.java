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
import java.util.HashMap;
import java.util.Vector;
import org.apache.log4j.Logger;
import com.pb.common.matrix.NDimensionalMatrixDouble;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Oct. 1, 2004
 * 
 * 1) Get base year target design information from a design table reader.
 * 2) Get converted census data from a converted table reader.
 * 3) Calculate 2-dimensional raw targets, [ND1CCat][NTAZs]--[116][1683]
 */

public class BaseTargetGenerator {
	
	protected HashMap propertyMap=PropertyParser.getPropertyMap();
	protected static Logger logger=Logger.getLogger("com.pb.models.synpopV3");
	
	protected TableDataReader convertedTableReader;
	protected TableDataReader designTableReader;
	
	protected TableDataSet BaseYearSourceData;
	
	//control ID
	protected int [] controlID;
	//target source type (sf or ctpp)
	protected String [] srcTypes;
	//target source table name
	protected String [] tableNames;
	//fileds included in calculating target
	protected String [] dataItems;

	protected int NoTargets;
	protected int numberOfInternalZones;
	
	//raw targets by ControlID and TAZ, Number of ControlID=116, Number of TAZ=1683
	//Note:
	//		raw targets will be passed to ControlTable constructor
	//		and then will be converted to 1D array as in ControlTable
	protected double [][] rawTargets;
	
	/**
	 * constructor
	 * @param convertedTableReader represents a TableDataReader for converted tables
	 * @param designTableReader represents a TableDataReader for design tables
	 */
	public BaseTargetGenerator(TableDataManager tableDataManager){
		this(tableDataManager, "BaseYear");
	}
    
    
    /**
     * constructor
     * @param convertedTableReader represents a TableDataReader for converted tables
     * @param designTableReader represents a TableDataReader for design tables
     */
    public BaseTargetGenerator(TableDataManager tableDataManager, String type){
        
        //converted census table reader
        convertedTableReader=tableDataManager.getTableReader("converted");
        designTableReader=tableDataManager.getTableReader("design");
        
        numberOfInternalZones = PopulationSynthesizer.numberOfInternalZones;
        
        //open base year source data file, a table in design folder     
        BaseYearSourceData=designTableReader.getTable(type + "SourceData.csv");
            
        //get columns from base year source table, columns are "CtrlID","DataItem","srcType", and "Table"
        controlID=BaseYearSourceData.getColumnAsInt(BaseYearSourceData.getColumnPosition("CtrlID"));
        dataItems=BaseYearSourceData.getColumnAsString(BaseYearSourceData.getColumnPosition("DataItem"));      
        srcTypes=BaseYearSourceData.getColumnAsString(BaseYearSourceData.getColumnPosition("srcType")); 
        tableNames=BaseYearSourceData.getColumnAsString(BaseYearSourceData.getColumnPosition("Table")); 
 
        //number of targets==number dimension 1 control categories, 116
        NoTargets=BaseYearSourceData.getRowCount();
        rawTargets=new double[NoTargets][numberOfInternalZones];
        
        set2DTargets();
    }
    
	
	/**
	 * get targets for all control IDs
	 * @return
	 */
	public double [][] getTargets(){
		return rawTargets;
	}
	
	public double [][] getTargetsDouble(){
		int NoRows=rawTargets.length;
		int NoCols=rawTargets[0].length;
		double [][] result=new double[NoRows][NoCols];
		for(int i=0; i<NoRows; i++){
			for(int j=0; j<NoCols; j++){
				result[i][j]=(double)rawTargets[i][j];
			}
		}
		return result;
	}
    
    public float [][] getTargetsFloat() {
        int NoRows=rawTargets.length;
        int NoCols=rawTargets[0].length;
        float [][] result=new float[NoRows][NoCols];
        for(int i=0; i<NoRows; i++){
            for(int j=0; j<NoCols; j++){
                result[i][j]=(float)rawTargets[i][j];
            }
        }
        return result;
    }
	
	public NDimensionalMatrixDouble getTargetsNDimimensionalMatrix(){
		return new NDimensionalMatrixDouble("matrix",rawTargets);
	}
	
	/**
	 * Given a control ID, get target
	 * @param ControlID
	 * @return
	 */
	public float [] getTarget(int ControlID){
		float [] result=new float[numberOfInternalZones];
		//controlID is 1-based sequential integer
		for(int i=0; i<numberOfInternalZones; i++){
			result[i]= (float) rawTargets[ControlID-1][i];
		}
		return result;
	}
	
	/**
	 * populate targets [NoTargets][NoTAZs]
	 *
	 */
	private void set2DTargets(){
		
		TableDataSet table=null;
		String [] items=null;

		for(int i=0; i<NoTargets; i++){
				
			//table source for current control
			String tableSource=srcTypes[i]+tableNames[i]+".csv";
			
			//open table source for current control
			table=convertedTableReader.getTable(tableSource);
			
			//data fileds included for current control
			items=parseDataItems(dataItems[i]);
	
			//caculate targets
			for(int t=0; t<numberOfInternalZones; t++){
				for(int j=0; j<items.length; j++){
					int intTAZ = t+1;
					rawTargets[i][t]+=findTableCell(table, intTAZ, items[j]);	
				}
			}
		}
	}
	
	/**
	 * given taz index, and column name, find a cell in a table.
	 * taz index is from 0-NoTAZs, represents internal taz ID, 
	 * all tables with a "taz" column must use the same internal taz index
	 */
	private float findTableCell(TableDataSet table, int intTAZ, String columnName){
		
		float result=0;
		int [] taz=table.getColumnAsInt("TAZ");
		int rowPos=-1;
		int colPos=table.getColumnPosition(columnName);
        
        // check for errors
        if (colPos < 0) {
            logger.error("Cannot find column " + columnName + " in table " + table.getName());
        }
        
        // get the external TAZ
        int extTAZ = ExtTAZtoIntTAZIndex.getExternalTAZ(intTAZ);
        
        // find the row position of the current TAZ
        for(int i=0;i<taz.length;i++){
        	if(taz[i]==extTAZ){
        		rowPos=i+1;
        		break;
        	}
        }
		
		//if current TAZ found in table, get cell value from table
		//else set return 0
		if(rowPos!=-1)
			result=table.getValueAt(rowPos,colPos);
		else
			result=0f;

		return result;
	}
	
	/**
	 * parse data items separated by "+"
	 * @param dataItems
	 * @return
	 */
	private String [] parseDataItems(String dataItems){
		
		Vector result_v=PropertyParser.parseValues(dataItems,"+");
		String [] result=new String[result_v.size()];
		for(int i=0; i<result_v.size();i++){
			result[i]=(String)result_v.get(i);
		}
		return result;
	}
	
	/*
	 * For testing purpose only.
	 * Successfully tested on March 25, 2005
	 */
	public static void main(String [] args){
		
        double markTime=System.currentTimeMillis();
								
		//create base year targets
		BaseTargetGenerator btg=new BaseTargetGenerator(new TableDataManager());
		
		System.out.println("after base target generator.");
		
		//get target ID=16
		float [] target=btg.getTarget(16);
		//print out targets
		for(int i=0; i<target.length; i++){
			logger.info("target["+i+"]="+target[i]);
		}
		
        double runningTime = System.currentTimeMillis() - markTime;
        logger.info ("total running minutes = " + (float)((runningTime/1000.0)/60.0));   
	}
}