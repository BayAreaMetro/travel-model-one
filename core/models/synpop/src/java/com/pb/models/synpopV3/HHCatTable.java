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
import java.util.Vector;
import org.apache.log4j.Logger;

/**
 * <p>Company: PB Consult, Parsons Brinckerhoff</p>
 * @author Wu Sun
 * @version 1.1, Modified on Nov. 15, 2004
 *
 * Represents a HH categories table: HHCatFile.csv.
 * Each table entry is a HHCat object.
 * 
 **/

public class HHCatTable {
	
  protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
  protected static CSVFileReader reader;
  //HH categories file location
  protected static String hhcat_file;
  //HH categories table as a TableDataSet
  protected static TableDataSet hhcat_table;
  //Number of HH categories
  protected static int NHHCat;
  //HH category dimension, 6 for ARC
  protected static int HHCatDim;
  //HH categories, an array of HHCat objects
  protected static HHCat [] hhcats;

  static {
  	
    reader=new CSVFileReader();
    hhcat_file=PropertyParser.getPropertyByName("hhcat.file");
    HHCatDim=ControlVarIndex.getCtrlVarCount();

    try{
      hhcat_table = reader.readFile(new File(hhcat_file),true);
    }catch(IOException e){
      logger.error("failed open "+hhcat_file);
    }

    NHHCat=hhcat_table.getRowCount();

    //populate HHCat array
    int rowPos=-1;
    int colPos=-1;
    hhcats=new HHCat[NHHCat];
    String [] currentHHCatName=ControlVarIndex.getCtrlVarNames();

    for(int i=0; i<NHHCat; i++){
      String [] currentHHCatVal=new String[HHCatDim];
      rowPos=i+1;
      for(int j=0; j<HHCatDim; j++){
      	colPos=hhcat_table.getColumnPosition(currentHHCatName[j]);
        currentHHCatVal[j]=hhcat_table.getStringValueAt(rowPos, colPos);
      }
      //make a new HHCat object
      hhcats[i]=new HHCat(currentHHCatVal);
    }
  }

  /**
   * Get HHCat array.
   * @return
   */
  public static HHCat [] getHHCats(){
    return hhcats;
  }
  
  /**
   * get a HHCat by ID
   * @param ID important 1-based
   * @return
   */
  public static HHCat getHHCat(int ID){
  	return hhcats[ID-1];
  }
  
  /**
   * given HH control variables, find corresponding HHCat
   * @param ctrlVals
   * @return
   */
  public static HHCat getHHCat(int [] ctrlVals){
  
  	//current HH category in HHCatTable
  	HHCat currentHHCat=null;
  	//control variables in current HHCat
  	String [] currentCtrlStr=null;
  	//HHCat found flag
  	boolean flag;
  	
  	// TODO add a routine to capture hh's that never get matched (dto)
  	
  	for(int i=0; i<NHHCat; i++){
  		
  		//get current HHCat
  		currentHHCat=hhcats[i];
  		
  		//get control variables in current HHCat
  		currentCtrlStr=currentHHCat.getCtrlVarVals();
  		
  		//initialize flag to true
  		flag=true;
  		
  		for(int j=0; j<ctrlVals.length; j++){
  			
  			//if control variable value not in corresponding control string, 
  			//then HHCat not found, and break out of current loop
  			if(!isValueInString(ctrlVals[j],currentCtrlStr[j],"+")){
  				flag=false;
  				break;
  			}
  		}
  		
  		//if HHCat found, then break out of loop
  		if(flag){
  			break;
  		}
  	}
  	
  	return currentHHCat;
  }
  
  /**
   * chech if an integer value is in a string separated by "separator"
   * @param value represents an integer
   * @param str represents a String
   * @param separator represents the separator separtes string elements
   * @return
   */
  private static boolean isValueInString(int value, String str, String separator){
  	
  	boolean result=false;
  	
	Vector strElements=PropertyParser.parseValues(str,separator);
	
	String currentElement=null;
	int currentElementInt=-1;
	
	for(int i=0; i<strElements.size(); i++){
		currentElement=(String)strElements.get(i);
		currentElementInt=new Integer(currentElement).intValue();
		if(currentElementInt==value){
			result=true;
			break;
		}
	}
	return result;
  }
  
  /**
   * given a HHCat object, return its ID in household category table
   * Important: the returned ID is 1-based
   * @param hhcat
   * @return
   */
  public static int getHHCatID(HHCat hhcat){
  	int result=-1;
  	for(int i=0; i<NHHCat; i++){
  		if(hhcat.equals(hhcats[i])){
  			result=i+1;
  			break;
  		}
  	}
  	return result;
  }

  /**
   * Get number of HH categories in HH categories table.
   * @return
   */
  public static int getHHCatCount(){
    return NHHCat;
  }

  /**
   * Get dimension of HH control variables.
   * @return
   */
  public static int getHHCatDim(){
    return HHCatDim;
  }

//for testing purpose only
  //successfully tested on March 29, 2005
  public static void main(String [] args){
  	int [] test={1,3,1,0,0,1};
  	HHCat cat=HHCatTable.getHHCat(test);
    logger.info("ok, stop here");
  }
}