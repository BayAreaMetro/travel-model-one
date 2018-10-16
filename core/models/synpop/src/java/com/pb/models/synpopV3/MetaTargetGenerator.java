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
 * Use this class to calcualte meta targets.
 * 
 * Meta Target calculation:  
 * MetaTarget=sumA*(SumB/SumC)	
 * 
 * ------------------------------------------------	
 *	A				B				C
 *-------------------------------------------------
 *	8-14,115,116	8-14,115,116	8-14,115,116
 *	15,16			8-14,115,116	15-22
 *	17,18			8-14,115,116	15-22
 *-------------------------------------------------
 *
 * Note:
 * numbers in this table represent base target IDs in base target array.
 */
package com.pb.models.synpopV3;

import java.util.StringTokenizer;
import java.util.Vector;
import java.io.*;
import org.apache.log4j.Logger;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileWriter;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 */
public class MetaTargetGenerator {
	
	protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
	//base target generator
	protected BaseTargetGenerator baseTargetGenerator;
	//base targets (base targets=meta seed distribution)
	protected double [][] baseTargets;
	//meta target source groups
	protected MetaTargetSourceGroup sourceGroups;
	//meta target sources in column A, B, and C
	//these are arrays of Vectors, each element represents a vector of data items in base targets to be summed up
	protected Vector [] ASource;
	protected Vector [] BSource;
	protected Vector [] CSource;
	protected int NoMetaTargets;
	protected int numberOfInternalZones;
	//column A, B, and C values, array[NoMetaTargets][NoTAZs]
	protected double [][] AVals;
	protected double [][] BVals;
	protected double [][] CVals;
	//meta targets, main results, array[NoMetaTargets][NoTAZs]
	protected double [][] metaTargets;

	/**
	 * constructor
	 * @param baseTargetGenerator represents a BaseTargetGenerator object
	 */
	public MetaTargetGenerator(BaseTargetGenerator baseTargetGenerator, TableDataReader designTableReader){
		this.baseTargetGenerator=baseTargetGenerator;
		//get base targets
		baseTargets=baseTargetGenerator.getTargets();
		//meta target source group
		sourceGroups=new MetaTargetSourceGroup(designTableReader);
		//get array dimensions
		NoMetaTargets=sourceGroups.getNoMetaTargets();
		numberOfInternalZones=PopulationSynthesizer.numberOfInternalZones;
		
		//define A,B,C meta targets sources and values
		ASource=new Vector[NoMetaTargets];
		BSource=new Vector[NoMetaTargets];
		CSource=new Vector[NoMetaTargets];
		AVals=new double[NoMetaTargets][numberOfInternalZones];
		BVals=new double[NoMetaTargets][numberOfInternalZones];
		CVals=new double[NoMetaTargets][numberOfInternalZones];
		
		//initialize meta target array
		metaTargets=new double[NoMetaTargets][numberOfInternalZones];
		for(int i=0; i<NoMetaTargets; i++){
			for(int j=0; j<numberOfInternalZones; j++){
				metaTargets[i][j]=0f;
			}
		}
		
		//initialize ASource,BSource,and CSource
		for(int i=0; i<NoMetaTargets; i++){
			ASource[i]=new Vector();
			BSource[i]=new Vector();
			CSource[i]=new Vector();
		}
		
		parseABCSources();
		calculateABCVals();
		calculateMetaTargets();
	}
	
	/**
	 * get meta targets.
	 * @return
	 */
	public double [][] getMetaTargets(){
		return metaTargets;
	}
	
	/**
	 * get number of meta targets.
	 * @return
	 */
	public int getNoMetaTargets(){
		return NoMetaTargets;
	}
	
	/**
	 * calculate meta targets
	 *
	 */
	private void calculateMetaTargets(){
		for(int i=0; i<NoMetaTargets; i++){
			for(int j=0; j<numberOfInternalZones; j++){
				if(CVals[i][j]!=0)
					metaTargets[i][j]=AVals[i][j]*(BVals[i][j]/CVals[i][j]);
				else
					metaTargets[i][j]=0;
			}
		}
		
	}
	
	/**
	 * parse column A,B,and C sources 
	 * (convert a string of control ID combination to a vector containing control IDs)
	 *
	 */
	private void parseABCSources(){
		String [] a=sourceGroups.getColASource();
		String [] b=sourceGroups.getColBSource();
		String [] c=sourceGroups.getColCSource();
		String currentA=null;
		String currentB=null;
		String currentC=null;
		for(int i=0; i<NoMetaTargets; i++){
			currentA=a[i];
			currentB=b[i];
			currentC=c[i];
			ASource[i]=parseValues(currentA,"+");
			BSource[i]=parseValues(currentB,"+");	
			CSource[i]=parseValues(currentC,"+");
		}
	}
	
	/**
	 * calculate A,B,and C values
	 *
	 */
	private void calculateABCVals(){
		int [] currentASource=null;
		int [] currentBSource=null;
		int [] currentCSource=null;
		int currentAIndex;
		int currentBIndex;
		int currentCIndex;
		for(int i=0; i<NoMetaTargets; i++){
			currentASource=covertStringVectorToIntArray(ASource[i]);
			currentBSource=covertStringVectorToIntArray(BSource[i]);
			currentCSource=covertStringVectorToIntArray(CSource[i]);
			for(int j=0; j<numberOfInternalZones; j++){
				for(int k=0; k<currentASource.length;k++){
					AVals[i][j]+=baseTargets[currentASource[k]-1][j];
				}
				for(int k=0; k<currentBSource.length;k++){
					BVals[i][j]+=baseTargets[currentBSource[k]-1][j];
				}
				for(int k=0; k<currentCSource.length;k++){
					CVals[i][j]+=baseTargets[currentCSource[k]-1][j];
				}
			}
		}
	}
	
	/**
	 * convert a vector to an integer array
	 * @param stringVector
	 * @return
	 */
	private int [] covertStringVectorToIntArray(Vector stringVector){
		int NoElements=stringVector.size();
		int [] result=new int[NoElements];
		for(int i=0; i<NoElements; i++){
			result[i]=new Integer((String)stringVector.get(i)).intValue();
		}
		return result;
	}
	
	  /**
	   * Parse a string using a given separator
	   * @param string_raw represents string to be parsed
	   * @param separator represents the separator
	   * @return
	   */
	  public static Vector parseValues(String string_raw, String separator ) {
	      Vector result = new Vector();
	      StringTokenizer st = new StringTokenizer(string_raw, separator);

	      while (st.hasMoreTokens()) {
	          String token = st.nextToken();
	          token=token.trim();
	          if(!token.equalsIgnoreCase(""))
	          	result.add(token);
	      }
	      return result;
	  }
	
	//For testing purpose only
	//Successfully tested on March 25, 2005
	public static void main(String [] args){
		
        double markTime=System.currentTimeMillis();
        
        TableDataManager tableDataManager=new TableDataManager();
				
		//create base year targets
		BaseTargetGenerator btg=new BaseTargetGenerator(tableDataManager);
		
		MetaTargetGenerator mtg=new MetaTargetGenerator(btg, tableDataManager.getTableReader("design"));
		
		double [][] cvals=mtg.CVals;
		double [] sf1hh=cvals[0];
		double [] CTPPhh=cvals[60];
		double [] sf3hh=cvals[8];
		
		TableDataSet table=new TableDataSet();
		table.appendColumn(sf1hh,"sf1HH");
		table.appendColumn(CTPPhh,"CTPPHH");
		table.appendColumn(sf3hh,"sf3HH");

		CSVFileWriter writer=new CSVFileWriter();
		String tempFile=PropertyParser.getPropertyByName("interimResult.directory")+PropertyParser.getPropertyByName("temp.file");
		try{
			File file=new File(tempFile);
			writer.writeFile(table,file);
		}catch(IOException e){
			logger.fatal("failed writing out temp table");
		}
        double runningTime = System.currentTimeMillis() - markTime;
        logger.info ("total running minutes = " + (float)((runningTime/1000.0)/60.0));   
	}
}
