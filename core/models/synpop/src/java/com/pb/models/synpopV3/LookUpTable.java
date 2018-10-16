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
 * Created on May 4, 2005
 *
 */
package com.pb.models.synpopV3;

import org.apache.log4j.Logger;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */
public class LookUpTable {
	
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected TableDataSet table;
	protected String tableName;
	
	// redo method to use a HashMap to go from Taz to aggregation level to aggregation index (dto)
	protected HashMap TazToAggregation;
	protected HashMap AggregationToIndex;
    protected HashMap IndexToAggregation;
		
	/**
	 * constructor
	 * @param tableName represent a .csv table name, don't include .csv as part of the name
	 * @param levelName represents the aggregation level (e.g. PUMA)
	 */
	public LookUpTable(String tableName, String levelName){
		this.tableName=tableName;
		table=readTable();
		buildLookUpTables(levelName);
	}
			
	// modify to read in strings instead of floats; assume table is of the format number, string (x3)
	// taz, tract, puma, county, supercounty (last four in any order) (dto)
	private TableDataSet readTable(){
		
		TableDataSet result=null;
		CSVFileReader reader=new CSVFileReader();
		String dir=PropertyParser.getPropertyByName("LookUpTable.directory");
		String name=PropertyParser.getPropertyByName("LookUpTable."+tableName);
		String [] format = {"NUMBER","STRING","STRING","STRING","STRING"};

		//assume table has column titles
		try{
			result=reader.readFileWithFormats(new File(dir+name),format);
		}catch(IOException e){
			logger.fatal("can not open file:"+dir+name);
		}
		return result;
	}
	

	// add method to build the HashMaps from the table data (dto)
	public void buildLookUpTables(String name){
		
		// redo routine to use hashMaps (dto)
		int nRows = table.getRowCount();
		int [] tazs = table.getColumnAsInt(table.getColumnPosition("TAZ"));
        
        // check column type and get as that (gde)
        int columnPosition = table.checkColumnPosition(name);
        int[] columnType = table.getColumnType();
        String[] aggregation; 
        if (columnType[columnPosition-1] == 2) {
            aggregation = table.getColumnAsString(name);
        } else {
            int[] aggregationInt = table.getColumnAsInt(name);
            aggregation = new String[aggregationInt.length];
            for (int i=0; i<aggregationInt.length; i++) {                
                aggregation[i] = (new Integer(aggregationInt[i])).toString();
            }
        }
        
		
		// make hashMaps
		TazToAggregation = new HashMap(nRows);
		AggregationToIndex = new HashMap();
        IndexToAggregation = new HashMap();
		
		int counter=0;
		for(int i=0;i<nRows;i++){
		
			// set the TazToAggregation map
			if (TazToAggregation.isEmpty()){
				TazToAggregation.put(tazs[i],aggregation[i]);
			}
			else if (!TazToAggregation.containsKey(tazs[i])){
				TazToAggregation.put(tazs[i],aggregation[i]);
			
			}

			// set the aggregation to index map
			if(AggregationToIndex.isEmpty()){
				AggregationToIndex.put(aggregation[i],counter);
                IndexToAggregation.put(counter, aggregation[i]);
				counter++;
			}
			else if(!AggregationToIndex.containsKey(aggregation[i])){
				AggregationToIndex.put(aggregation[i],counter);
                IndexToAggregation.put(counter, aggregation[i]);
				counter++;
			}
		
		} // for i
		
	}
	
	// returns index of aggregate element (e.g. if we have 15 PUMAs, returns number 1 to 15 for the TAZ) (dto)
	public int tazToAggregateIndex(int Taz){
		
		return (Integer) (AggregationToIndex.get(TazToAggregation.get(Taz)));
		
	}   
    
    /**
     * 
     * @param index The index.  
     * @return The label of the aggregation geography.
     */
    public String getAggregationFromIndex(int index) {
        String aggregation = (String) IndexToAggregation.get(index);
        return aggregation;
    }
    
	// the number of indices in the aggregate elements (e.g. 15 PUMAs, returns 15) (dto)
	public int numberOfIndices(){
		return AggregationToIndex.size();
	}
	
	
	
	//for testing purpose only
	//re-tested nov 1, 2006 (dto)
	public static void main(String [] args){
		LookUpTable table=new LookUpTable("file","TRACT");
		logger.info("for TAZ=10 Index="+table.tazToAggregateIndex(10));
	}
}
