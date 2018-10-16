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
 * Created on Nov 22, 2004
 * This class prepares for BaseMetaTargetGenerator.  
 * It extracts meta target source grouping information from a MetaTargetGroupingFile.
 * Note:
 * MetaTargetGroupingFile is created from "Base yr MetaTarget source data" from control work book.
 */
package com.pb.models.synpopV3;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import org.apache.log4j.Logger;
import java.util.HashSet;

/**
 * @author SunW
 * <sunw@pbworld.com>
 */
public class MetaTargetSourceGroup {
	
	protected Logger logger;
	protected String dir;
	protected String groupFile;
	protected CSVFileReader reader;
	protected TableDataSet metaGroupTable;
	protected int NoMetaTargets;
	protected HashSet sourceGroups;
	protected String [] A;
	protected String [] B;
	protected String [] C;
	
	protected TableDataReader designTableReader;
	
	public MetaTargetSourceGroup(TableDataReader designTableReader){

		logger=Logger.getLogger("com.pb.models.synpopV3");
		this.designTableReader=designTableReader;
		metaGroupTable=designTableReader.getTable("metaTargetGrouping.csv");
 
        NoMetaTargets=metaGroupTable.getRowCount();
        A=new String[NoMetaTargets];
        B=new String[NoMetaTargets];
        C=new String[NoMetaTargets];
        doWork();	
	}
	
	/**
	 * get meta target source group
	 * @return
	 */
	public HashSet getMetaSourceGroups(){
		return sourceGroups;
	}
	
	/**
	 * get column A source
	 * @return
	 */
	public String [] getColASource(){
		return A;
	}
	/**
	 * get column B source
	 * @return
	 */
	public String [] getColBSource(){
		return B;
	}
	
	/**
	 * get column C source
	 * @return
	 */
	public String [] getColCSource(){
		return C;
	}
	
	/**
	 * get number of meta targets
	 * @return
	 */
	public int getNoMetaTargets(){
		return NoMetaTargets;
	}
	
	/**
	 * set meta target source group, column A, B, and C.
	 *
	 */
	private void doWork(){
		int NoCols=metaGroupTable.getColumnCount();
		sourceGroups=new HashSet();
		String currentVal=null;
		for(int i=0; i<NoCols; i++){
			for(int j=0; j<NoMetaTargets; j++){
				currentVal=metaGroupTable.getStringValueAt(j+1,i+1);
				sourceGroups.add(currentVal);
				if(i+1==1){
					A[j]=currentVal;
				}
				if(i+1==2){
					B[j]=currentVal;
				}	
				if(i+1==3){
					C[j]=currentVal;
				}
			}
		}	
	}
	
	public static void main(String [] args){
		TableDataReader designTableReader=new TableDataReader("design");
		MetaTargetSourceGroup group=new MetaTargetSourceGroup(designTableReader);
		HashSet set=group.getMetaSourceGroups();
		String [] A=group.getColASource();
		String [] B=group.getColBSource();
		String [] C=group.getColCSource();
		int targets=group.getNoMetaTargets();
		System.out.println("ok, I am done.");
	}
}
