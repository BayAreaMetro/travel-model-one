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
 * Created on Oct 7, 2004
 *
 * internal-external TAZ index class.
 */
package com.pb.models.synpopV3;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;

import org.apache.log4j.Logger;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */

public class ExtTAZtoIntTAZIndex {
	
    protected static Logger logger=Logger.getLogger(ExtTAZtoIntTAZIndex.class);

	protected static CSVFileReader CSVReader;
	protected static TableDataSet indexTable;
	protected static String tableFile=PropertyParser.getPropertyByName("TAZIndexTable");
	private static int[] intTAZs = null;
	private static int[] extTAZs = null;
	protected static HashMap<Integer,Integer> internalToExternalMap;
	protected static HashMap<Integer,Integer> externalToInternalMap;
	protected static int numberOfInternalZones = -1;
	
	
	static{
		
		CSVReader=new CSVFileReader();
		
	    try{
	        indexTable =CSVReader.readFile(new File(tableFile));
	        extTAZs=indexTable.getColumnAsInt(indexTable.getColumnPosition("extTAZ"));
	        intTAZs=indexTable.getColumnAsInt(indexTable.getColumnPosition("intTAZ"));
	      
	    }catch (IOException e) {
	        logger.error("IO Error when reading "+tableFile);
	        System.exit(1);
	    }
	    
	    numberOfInternalZones = intTAZs.length;
	    internalToExternalMap = new HashMap<Integer,Integer>(intTAZs.length);
	    for(int i=0;i<intTAZs.length;++i){
	    	internalToExternalMap.put(intTAZs[i], extTAZs[i]);
	    }
	    
	    externalToInternalMap = new HashMap<Integer,Integer>(extTAZs.length);
	    for(int i=0;i<extTAZs.length;++i){
	    	externalToInternalMap.put(extTAZs[i], intTAZs[i]);
	    }
		
	}
	
	public static int getNumberOfInternalZones(){
		return numberOfInternalZones;
	}
	
	public static int [] getInternalTAZs(){
		return intTAZs;
	}
	
	public static int [] getExternalTAZs(){
		return extTAZs;
	}
	
	/**
	 * given an external TAZ, find internal TAZ
	 * @param extTAZ represents external TAZ, non-sequential is ok
	 * @return
	 */
	public static int getInternalTAZ(int extTAZ){
		if(externalToInternalMap.containsKey(extTAZ)){
			return externalToInternalMap.get(extTAZ);
		}
		else{
			logger.error("No internal zone for external zone "+extTAZ+" in TAZIndexTable.");
			System.exit(1);
		}
		return -1;
		
	}
	
	
	
//	public static int getInternalTAZ(int extTAZ){
//		int result=-1;
//		for(int i=0; i<NoTAZs; i++){
//			if(extTAZ==extTAZs[i]){
//				result=intTAZs[i];
//				break;
//			}
//		}
//		return result;
//	}
	
	/**
	 * given an internal TAZ, find external TAZ
	 * @param intTAZ represents internal TAZ, 1-based
	 * @return
	 */
    public static int getExternalTAZ(int intTAZ){
		if(internalToExternalMap.containsKey(intTAZ)){
			return internalToExternalMap.get(intTAZ);
		}
		else{
			logger.error("No external zone for internal zone "+intTAZ+" in TAZIndexTable.");
			System.exit(1);
		}
		return -1;
	}
//	public static int getExternalTAZ(int intTAZ){
//		int result=-1;
//		for(int i=0; i<NoTAZs; i++){
//			if(intTAZ==intTAZs[i]){
//				result=extTAZs[i];
//				break;
//			}
//		}
//		return result;
//	}	
}
