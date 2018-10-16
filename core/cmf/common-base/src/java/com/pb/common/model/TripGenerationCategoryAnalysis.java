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
/*
 * Created on Aug 9, 2004
 * 
 * Use this class for trip generation cross-classification or category analysis
 * A trip production/attraction rate table is assumed to have following format:
 * 	Label		|Cat1_Label1	Cat1_label2 ... Cat1_Labeln
 * -------------------------------------------------------------
 * Cat2_Label1  |
 * Cat2-Label2  |
 * ...			|
 * Cat2_Labeln	|
 * -------------------------------------------------------------
 */
package com.pb.common.model;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */

public class TripGenerationCategoryAnalysis {
		
	protected Logger logger =null;
	protected int tripSourceVolume;
	protected TableDataSet rateTable;
	protected TableDataSet trips;

	/**
	 * Constructor
	 * @param tripRateFile represents a trip production/attraction rate file
	 */
	public TripGenerationCategoryAnalysis(Logger logger, String tripRateFile, int sourceVolume){
		
        this.logger=logger;
		this.tripSourceVolume=sourceVolume;
		rateTable=readRateTable(tripRateFile);
		trips=calTrips(tripSourceVolume, rateTable);
		
	}
	
	public TripGenerationCategoryAnalysis(Logger logger, String tripRateFile){
		this(logger, tripRateFile,0);		
	}
	
	/**
	 * get trips table.
	 * @return  trips table
	 */
	public TableDataSet getTripsTable(){
		return trips;
	}
	
	public void setTripSourceVolume(int vol){
		tripSourceVolume=vol;
	}
	
	public float getTripsByRowCategory(String rowName){
		
		float result=0f;
		int rowNo=-1;
		String [] rowNames=trips.getColumnAsString(1);
		for(int i=0; i<rowNames.length; i++){
			if(rowName.equalsIgnoreCase(rowNames[i])){
				rowNo=i+1;
				break;
			}
		}
		
		float [] temp= trips.getRowValues(rowNo);
		for(int i=0; i<temp.length; i++){
			result=+temp[i];
		}
		return result;
		
	}
	
	public float getTripsByColCategory(String colName){
		
		float result=0f;
		int colNo=-1;
		String [] colLabels=trips.getColumnLabels();
		for(int i=1; i<colLabels.length; i++){
			if(colName.equalsIgnoreCase(colLabels[i])){
				colNo=i+1;
				break;
			}
		}
		
		float [] temp=trips.getColumnAsFloat(colNo);
		for(int i=0; i<temp.length; i++){
			result=+temp[i];
		}
		return result;
		
	}
	
	/**
	 * get trips by row and column names, row and column are trip generation categories.
	 * if returns -1, then no valid trips found.
	 * assumption: 
	 * 2 categories, labels of 1st one appears in 1st column of a TableDataSet object
	 * @param rowName
	 * @param colName
	 * @return float
	 */
	public float getTripsByCategory(String rowName, String colName){
		float result=-1f;
		
		int rowNo=0;
		String [] rowNames=trips.getColumnAsString(1);
		for(int i=0; i<rowNames.length; i++){
			if(rowName.equalsIgnoreCase(rowNames[i])){
				rowNo=i+1;
				break;
			}
		}
		
		if(rowNo==0){
			logger.error("invalid row number for row: "+rowName);
		}else{
			result=trips.getValueAt(rowNo, colName);
		}
		
		return result;
	}
	
	/**
	 * read trip production/attraction rate table
	 * @param rateTableFile represent the file name of a trip production/attraction table
	 * @return a TableDataSet object, or null if failed.
	 */
	private TableDataSet readRateTable(String rateTableFile){
		
		TableDataSet result=null;
		CSVFileReader reader=new CSVFileReader();
		
		//read trip production/attraction rate table
		try{
			result=reader.readFile(new File(rateTableFile),true);
		}catch(IOException e){
			logger.error("can not open file:"+rateTableFile);
		}
		
		return result;	
	}
		
	private TableDataSet calTrips(int tripSourceVolume, TableDataSet rateTable){
		
		int NoRows=rateTable.getRowCount();
		int NoCols=rateTable.getColumnCount();
		float temp=-1f;
		
		for(int i=2; i<NoRows+1; i++){
			for(int j=1; j<NoCols+1; j++){
				temp=rateTable.getValueAt(i,j)*tripSourceVolume;
				rateTable.setValueAt(i,j,temp);
			}
		}
		return rateTable;
		
	}
}
