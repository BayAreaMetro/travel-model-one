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
 * Created on Nov 11, 2004
 * 
 */
package com.pb.models.synpopV3;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileWriter;
import java.io.*;
import org.apache.log4j.Logger;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Vector;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 * 
 * 1) Create a TAZ to PUMA index from TAZ to TRACT and TRACT to PUMA tables.
 * 2) Write out TAZ to PUMA table if this class is instanciated for the 1st time.
 * 3) Make a PUMA array with unique PUMAs in it.
 * 
 */
public class TAZtoPUMAIndex {
	
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	protected CSVFileWriter CSVWriter;
	protected String conversionDir;
	protected TableDataSet TAZtoTRACTData;
	protected TableDataSet TRACTtoPUMAData;
	protected TableDataSet TAZtoPUMAData;
	protected HashMap<Integer,Integer> tazToPumaMap;
	protected int NoPUMAs;
	protected int [] PUMA;
	
	protected TableDataReader conversionTableReader;
	
	public TAZtoPUMAIndex(TableDataReader conversionTableReader, boolean isInit){
		
		CSVWriter=new CSVFileWriter();
		conversionDir=PropertyParser.getPropertyByName("conversion.directory");
		this.conversionTableReader=conversionTableReader;
		
		// fix the order of the table names to avoid hardcoding the filenames (dto)
		Vector conversionTableNames = PropertyParser.getPropertyElementsByName("conversion.tables",",");
		Object tractCountyName = conversionTableNames.elementAt(1);
		Object tractPumaName   = conversionTableNames.elementAt(3);
		Object tazPumaName  = conversionTableNames.elementAt(4);
		
		
		if(isInit){
			TAZtoTRACTData=conversionTableReader.getTable(tractCountyName.toString());
			TRACTtoPUMAData=conversionTableReader.getTable(tractPumaName.toString());			
	        TAZtoPUMAData=makeTAZtoPUMAData();
	        setPUMAs();
	        writeTAZtoPUMAData();
		}else{
			TAZtoPUMAData=conversionTableReader.getTable(tazPumaName.toString());
			setPUMAs();
		}
	}
		
	private void writeTAZtoPUMAData(){
		
		// fix the order of the table names to avoid hardcoding the filenames (dto)
		Vector conversionTableNames = PropertyParser.getPropertyElementsByName("conversion.tables",",");
		Object tazPumaName  = conversionTableNames.elementAt(4);
		
		try{
			CSVWriter.writeFile(TAZtoPUMAData,new File(conversionDir+tazPumaName.toString()));
		}catch(IOException e){
			logger.error("failed writing:"+conversionDir+tazPumaName.toString());
		}
	}
	
	/**
	 * given a TAZ ID, return corresponding PUMA
	 * @param tazID
	 * @return
	 */
	public int getPUMA(int tazID){
		
		// create the HashMap once
		if(tazToPumaMap==null){
			
			int [] tazList  = TAZtoPUMAData.getColumnAsInt("TAZ");
			int [] pumaList = TAZtoPUMAData.getColumnAsInt("PUMA");
			tazToPumaMap = new HashMap<Integer,Integer>(tazList.length);
			for(int i=0;i<tazList.length;++i){
				tazToPumaMap.put(tazList[i], pumaList[i]);
			}
			
		}
		
		if(tazToPumaMap.containsKey(tazID)){
			return tazToPumaMap.get(tazID);
		}
		else{
			logger.error("No matching PUMA found for TAZ "+tazID);
			System.exit(1);
		}
		
		return -1;
	}
//	public int getPUMA(int tazID){
//		
//		int result=-1;
//		int [] taz=TAZtoPUMAData.getColumnAsInt("TAZ");
//		int [] puma=TAZtoPUMAData.getColumnAsInt("PUMA");
//		int NoRows=TAZtoPUMAData.getRowCount();
//		
//		for(int i=0; i<NoRows; i++){
//			if(tazID==taz[i]){
//				result=puma[i];
//				break;
//			}
//		}
//        if (result==-1) {
//            logger.error("Could not find tazID: " + tazID); 
//            System.exit(1);
//        }   
//		return result;
//	}
	
	/**
	 * given a PUMA, find the array index of this PUMA
	 * @param puma
	 * @return
	 */
	public int getPUMAArrayIndex(int puma){
		int result=-1;
		for(int i=0; i<NoPUMAs; i++){
			if(PUMA[i]==puma){
				result=i;
				break;
			}
		}
		
		if(result==-1){
			logger.debug("PUMA:"+puma+" not found in PUMA array.");
		}

		return result;
	}
	
	/**
	 * get number of PUMAs in study region
	 * @return
	 */
	public int getNoPUMAs(){
		return NoPUMAs;
	}
	
	/**
	 * return PUMA array in study region
	 * @return
	 */
	public int [] getPUMAs(){
		return PUMA;
	}
	
	/**
	 * set PUMA array and NoPUMAs.  PUMAs in this array are unique.
	 *
	 */
	private void setPUMAs(){
		
		//put puma array in a HashSet (HashSet elements are unique)
		HashSet pumaSet=new HashSet();
		int [] puma=TAZtoPUMAData.getColumnAsInt("PUMA");
		
		for(int i=0; i<puma.length; i++){
			pumaSet.add(new Integer(puma[i]));
		}
		
		NoPUMAs=pumaSet.size();
		
		PUMA=new int[NoPUMAs];
		Iterator itr=pumaSet.iterator();
		int index=0;
		while(itr.hasNext()){
			PUMA[index]=((Integer)itr.next()).intValue();
			index++;
		}
	}
	
	private TableDataSet makeTAZtoPUMAData(){
		
		TableDataSet result=new TableDataSet();
		
		int [] taz=TAZtoTRACTData.getColumnAsInt("CENTROID");
		String [] tract1=TAZtoTRACTData.getColumnAsString("TRACT_S");
		String [] tract2=TRACTtoPUMAData.getColumnAsString("TRACT_S");
		int [] puma=TRACTtoPUMAData.getColumnAsInt("PUMA");
		
		int NoRows1=taz.length;
		int NoRows2=puma.length;
		int [] matchedPUMA=new int[NoRows1];
		
		for(int i=0; i<NoRows1; i++){
			for(int j=0; j<NoRows2; j++){
				if(tract1[i].equalsIgnoreCase(tract2[j])){
					matchedPUMA[i]=puma[j];
					break;
				}	
			}
		}
		
		result.appendColumn(taz,"TAZ");
		result.appendColumn(matchedPUMA,"PUMA");
		
		return result;
	}
	
	//for testing purpose only
	//successfully tested on March 23, 2005
	public static void main(String [] args){
		TableDataReader conversionTableReader=new TableDataReader("conversion");
		TAZtoPUMAIndex index=new TAZtoPUMAIndex(conversionTableReader,false);
		//int [] puma=index.getPUMAs();
		logger.info("if TAZ=6 "+"then PUMA="+index.getPUMA(6));
	}
}
