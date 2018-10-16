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
import com.pb.common.datafile.CSVFileReader;
import java.io.*;
import java.util.HashMap;
import java.util.Vector;
import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Sept. 27, 2004
 */

public class TableDataReader {
	
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected CSVFileReader CSVReader;
	protected HashMap propertyMap;
	protected String tableDir;
	protected Vector tableNames;
	protected Vector tables;
	protected HashMap tableMap;
	protected int NoTables;
	
	/**
	 * constructor
	 * @param type represents table type, "census", "conversion", "design", "pums", or "converted"
	 */
	public TableDataReader(String type) {
		
		CSVReader=new CSVFileReader();
		
		tableDir=null;
		tableNames=new Vector();
		
		if(type.equalsIgnoreCase("census")){
			tableDir=PropertyParser.getPropertyByName("census.directory");
			tableNames=PropertyParser.getPropertyElementsByName("census.tables",",");
		}
		else if(type.equalsIgnoreCase("conversion")){
			tableDir=PropertyParser.getPropertyByName("conversion.directory");
			tableNames=PropertyParser.getPropertyElementsByName("conversion.tables",",");
		}
		else if(type.equalsIgnoreCase("design")){
			tableDir=PropertyParser.getPropertyByName("design.directory");
			tableNames=PropertyParser.getPropertyElementsByName("design.tables",",");
		}
		else if(type.equalsIgnoreCase("converted")){
			tableDir=PropertyParser.getPropertyByName("converted.directory");
			tableNames=PropertyParser.getPropertyElementsByName("converted.tables",",");
		}
		else{
			logger.error("table type is invalid. "+this.toString());
		}
		
		NoTables=tableNames.size();	
		//read tables
		readTables();
		//make a table map
		makeTableMap();
	}
	
	/**
	 * get table names.
	 * @return
	 */
	public String [] getTableNames(){
		String [] result=new String[NoTables];
		for(int i=0; i<NoTables; i++){
			result[i]=(String)tableNames.get(i);
		}
		return result;
	}
	
	  /**
	   * Return table map: 
	   * 		talbe name----table
	   * Note: 	
	   * 		table names must be unique
	   */
	  public HashMap getTables(){
	    return tableMap;
	  }
	  
	  /**
	   * Given a table name, return a table object.
	   * @param tableName represents a table name.
	   * @return
	   */
	  public TableDataSet getTable(String tableName){
	    TableDataSet result=null;
	    for(int i=0; i<tables.size();i++){
	      result=(TableDataSet)tableMap.get(tableName);
	    }
	    if(result==null){
	    	logger.error("No census tables: "+tableName);
	    }
	    return result;
	  }
	
	/**
	 * read tables
	 */
	private void readTables(){
		tables=new Vector();
		
		String currentTableName;
		TableDataSet currentTable;
		
		for(int i=0; i<NoTables; i++){
			currentTableName=(String)tableNames.get(i);
	        try{
	        	//important assume all tables has column labels
	            currentTable =CSVReader.readFile(new File(tableDir+currentTableName),true);
	            tables.add(currentTable);
	        }catch (IOException e) {
	            logger.error("failed when try to open table "+tableDir+currentTableName);
	        }
		}
	}
	
	/**
	 * make table map:
	 * 		table name---table
	 *
	 */
	private void makeTableMap(){
		tableMap=new HashMap();
		for(int i=0; i<NoTables; i++){
			tableMap.put((String)tableNames.get(i),(TableDataSet)tables.get(i));
		}
	}
	
	//for testing purpose only
	//successfully tested on March 23, 2005
	public static void main(String [] args){
		//TableDataReader reader=new TableDataReader("conversion");
		logger.info("ok, I am done.");
	}
}