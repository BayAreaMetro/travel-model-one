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
 * Created on Nov 4, 2004
 * 
 * Manage census, conversion, design, and pums table data.  
 * Convert census tables to taz-based tables.  
 * Write converted census tables to disk.
 */
package com.pb.models.synpopV3;

import com.pb.common.datafile.TableDataSet;
import java.util.HashMap;
import java.util.Vector;
import org.apache.log4j.Logger;

/**
 * @author SunW
 * <sunw@pbworld.com>
 *
 */

public class TableDataManager {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected TableDataReader censusTableReader;
	protected TableDataReader conversionTableReader;
	protected TableDataReader designTableReader;
	protected TableDataReader convertedTableReader;
	protected HashMap convertedCensusTables;
	protected TAZtoPUMAIndex tpIndex;
	
	/**
	 * constructor
	 * @param isInit represents if this is the initial instantiation of TableDataManager object
	 */
	public TableDataManager(){
		
		designTableReader=new TableDataReader("design");
		conversionTableReader=new TableDataReader("conversion");
		
		// check if conversion is to be run
		boolean runConversion = PropertyParser.getPropertyByName("RunConversion").equalsIgnoreCase("true");
		if(runConversion){
			
			// if yes, read census data and convert them
			censusTableReader = new TableDataReader("census");
			convertedCensusTables=convertCensusTables(new ConversionManager(conversionTableReader));
		}
		
		// read in converted tables
		convertedTableReader=new TableDataReader("converted");
		
		//make TAZ to PUMA index table, and write it to conversion folder
        boolean convertTAZtoPUMA = PropertyParser.getPropertyByName("ConvertTAZtoPUMA").equalsIgnoreCase("true");
		tpIndex=new TAZtoPUMAIndex(conversionTableReader, convertTAZtoPUMA);

	}
	
	public HashMap getConvertedCensusTables(){
		return convertedCensusTables;
	}
	
	/**
	 * get table data reader
	 * @param type represent table type, either "census", "conversion", "design", "pums", or "converted"
	 * @return
	 */
	public TableDataReader getTableReader(String type){
		TableDataReader result=null;
		if(type.equalsIgnoreCase("census"))
			result=censusTableReader;
		else if(type.equalsIgnoreCase("conversion"))
			result=conversionTableReader;
		else if(type.equalsIgnoreCase("design"))
			result=designTableReader;
		else if(type.equalsIgnoreCase("converted"))
			result=convertedTableReader;
		else
			logger.error("wrong table type");
		
		return result;
	}
	
	/**
	 * get TAZ to PUMA index
	 * @return
	 */
	public TAZtoPUMAIndex getTAZtoPUMAIndex(){
		return tpIndex;
	}
	
	/**
	 * convert census tables to taz-based tables, and write converted tables to disk
	 * @return census table map (table name--table)
	 */
	private HashMap convertCensusTables(ConversionManager conversionManager){
		
		HashMap result=new HashMap();
		//get census table map
		HashMap censusTables=censusTableReader.getTables();
		String [] censusTableNames=censusTableReader.getTableNames();
		//get census table base unit map
		HashMap censusTableBaseUnitMap=conversionManager.getTableBaseUnitMap();
		int NoTables=censusTables.size();
		
		//checking
		if(NoTables!=censusTableBaseUnitMap.size()){
			logger.error("number of census tables and number of base units don't match.");
		}
		
		String tableName=null;
		String tableBaseUnit=null;
		TableDataSet table=null;
		String [] fields=null;
		String [] numFields=null;
		
		for(int i=0; i<NoTables; i++){
			
			//get current table name, base unit, table content, and table field names.
			tableName=censusTableNames[i];
			tableBaseUnit=(String)censusTableBaseUnitMap.get(tableName);
			table=(TableDataSet)censusTables.get(tableName);
			
			//all column labels
			fields=table.getColumnLabels();
			
			//get column labels for numerical fields
			Vector temp=new Vector();
			for(int j=0; j<fields.length; j++){
				if(!fields[j].equalsIgnoreCase(tableBaseUnit))
					  temp.add(fields[j]);
			}

			numFields=new String[temp.size()];
			for(int j=0; j<temp.size(); j++){
				numFields[j]=(String)temp.get(j);
			}
			
			//convert current table to taz-based table
			//fixed the order to allow removal of hardcoded names (dto)
			Vector conversionTableNames = PropertyParser.getPropertyElementsByName("conversion.tables",",");
			Object blkgrpName = conversionTableNames.elementAt(0);
			Object tazName    = conversionTableNames.elementAt(1);
			Object blockName  = conversionTableNames.elementAt(2);
			if(tableBaseUnit.equalsIgnoreCase("blkgrp"))
				table=conversionManager.BlkgrpToTAZ(blkgrpName.toString(), tableName, table, numFields);
			else if(tableBaseUnit.equalsIgnoreCase("block"))
				table=conversionManager.BlockToTAZ(blockName.toString(),tableName, table);
			else if(tableBaseUnit.equalsIgnoreCase("taz"))
				table=conversionManager.CtppToTAZ(tazName.toString(),tableName, table);
			else
				logger.error("wrong base unit type in: "+tableName);
			
			//write converted table to disk
			conversionManager.writeConvertedTable(table,tableName);
			result.put(tableName,table);
		}
		return result;
	}
	
	//for testing purpose only
	//successfully tested on March 23, 2005
	public static void main(String [] args){
        double markTime=System.currentTimeMillis();
		TableDataManager manager=new TableDataManager();
        double runningTime = System.currentTimeMillis() - markTime;
        logger.info ("total running minutes = " + (float)((runningTime/1000.0)/60.0));   
	}
}
