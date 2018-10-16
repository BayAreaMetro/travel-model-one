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
 * 
 * Created on Apr 29, 2005
 * 
 * Use this class to calculate validation statistics (universes+all validating statistics)
 */
package com.pb.models.synpopV3;

import java.util.HashMap;
import java.util.Vector;
import org.apache.log4j.Logger;
import com.pb.common.datafile.TableDataSet;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class CensusValidationStatistics {
	
	protected HashMap propertyMap=PropertyParser.getPropertyMap();
	protected static Logger logger=Logger.getLogger("com.pb.models.synpopV3");
	
	protected TableDataReader convertedTableReader;
	protected TableDataReader designTableReader;
	protected TableDataSet CensusVStatistics;	
	//1D validation statistic ID, 2D TAZ
	protected float [][] vStatistics;
	
	protected int numberOfInternalZones;
	protected int NoStatistics;
	
	public CensusValidationStatistics(TableDataManager tableManager, String type){
		
		numberOfInternalZones = PopulationSynthesizer.numberOfInternalZones;
		
		NoStatistics=new Integer(PropertyParser.getPropertyByName("NoValidationStatistics")).intValue();
		
		convertedTableReader=tableManager.getTableReader("converted");
		designTableReader=tableManager.getTableReader("design");
		
		String censusValidationFile=type+"YearCensusVStatistics.csv";
		CensusVStatistics=designTableReader.getTable(censusValidationFile);

		makeVStatistics();
	}
	
	public float [][] getVStatistics(){
		return vStatistics;
	}
	
	public float getVStatistics(int i, int j){
		return vStatistics[i][j];
	}
	
	public int getNoStatistics(){
		return NoStatistics;
	}
    
    public String[] getLabels() {
        String[] labels = null; 
        
        int colPosition = CensusVStatistics.getColumnPosition("Label");
        if (colPosition>=0) {
            labels = CensusVStatistics.getColumnAsString(colPosition);
        } else {
            colPosition = CensusVStatistics.getColumnPosition("CtrlID");
            
            float[] numbers = CensusVStatistics.getColumnAsFloat(colPosition); 
            labels = new String[numbers.length];
            for (int i=0; i<numbers.length; i++) {
                labels[i] = (new Float(numbers[i])).toString(); 
            }
        }                
        
        return labels;
    }
			
	private void makeVStatistics(){
		
		vStatistics=new float[NoStatistics][numberOfInternalZones];
		
        //get columns from base year census universe table, columns are "ID","DataItem","srcType", and "Table"
		//int [] universeID=BaseYearCensusUniverse.getColumnAsInt(BaseYearCensusUniverse.getColumnPosition("ID"));
        String [] dataItems=CensusVStatistics.getColumnAsString(CensusVStatistics.getColumnPosition("DataItem"));      
        String [] srcTypes=CensusVStatistics.getColumnAsString(CensusVStatistics.getColumnPosition("srcType")); 
        String [] tableNames=CensusVStatistics.getColumnAsString(CensusVStatistics.getColumnPosition("Table")); 
		
		TableDataSet table=null;
		String [] items=null;
		int NoRows=CensusVStatistics.getRowCount();
		
		if(NoStatistics!=NoRows){
			logger.info("NoStatistics="+NoStatistics+" NoRows="+NoRows);
			logger.fatal("Number of rows in validation design sheet doesn't match defined in property file!");
			System.exit(1);
		}

		for(int i=0; i<NoRows; i++){
				
			//table source for current control
			String tableSource=srcTypes[i]+tableNames[i]+".csv";
			
			//open table source for current control
			table=convertedTableReader.getTable(tableSource);
			
			//data fields included for current control
			items=parseDataItems(dataItems[i]);
						
			//calculate validation statistics
			for(int t=0; t<numberOfInternalZones; t++){
				for(int j=0; j<items.length; j++){	
					vStatistics[i][t]+=findTableCell(table, t, items[j]);	
				}
			}
		}	
	}
	
	/**
	 * given taz index, and column name, find a cell in a table.
	 * taz index is from 0-NoTAZs, represents internal taz ID, 
	 * all tables with a "taz" column must use the same internal taz index
	 */
	private float findTableCell(TableDataSet table, int tazIndex, String columnName){
		
		float result=0;
		int [] taz=table.getColumnAsInt("TAZ");
		int rowPos=-1;
		int colPos=table.getColumnPosition(columnName);
		
		//find row position of current TAZ
		for(int i=0; i<taz.length; i++){
			if(tazIndex+1==taz[i]){
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
	
	//for testing purpose only
	//successfully tested on May 12 2005
	public static void main(String [] args){
		
		TableDataManager tm=new TableDataManager();
		CensusValidationStatistics cvs=new CensusValidationStatistics(tm,"Base");
		float [][] s=cvs.getVStatistics();
		logger.info("ok, I am done.");
	}
}
