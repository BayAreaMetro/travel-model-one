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
 * Created on Apr 13, 2005
 * Write HHs and Persons in each SynPop cell as CSV files
 */
package com.pb.models.synpopV3;

import java.util.Vector;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;

/**
 * @author Wu Sun
 * <sunw@pbworld.com>
 *
 */
public class SynPopPrinter {
	
	protected boolean logDebug=true;
    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    
	protected String [] hhAttrs;
	protected String [] personAttrs;
	protected Vector [][] PopSyn;
	

    public SynPopPrinter(Vector [][] PopSyn, int NoHHs, int NoPersons){
		this.PopSyn=PopSyn;
		setHHAttrs();
		setPersonAttrs();
		if(logDebug)
			logger.info("NoHHs="+NoHHs+"  NoPersons="+NoPersons);
	}
	
	private void setHHAttrs(){
		Vector attrs=PropertyParser.getPropertyElementsByName("print.HHAttrs",",");
		hhAttrs=new String[attrs.size()+2];
		for(int i=0; i<attrs.size(); i++){
			hhAttrs[0]="HHID";
			hhAttrs[1]="TAZ";
			hhAttrs[i+2]=(String)attrs.get(i);
		}
	}
	
	private void setPersonAttrs(){
		Vector attrs=PropertyParser.getPropertyElementsByName("print.PersonAttrs",",");
		personAttrs=new String[attrs.size()+2];
		for(int i=0; i<attrs.size(); i++){
			personAttrs[0]="HHID";
            personAttrs[1]="PERID";
			personAttrs[i+2]=(String)attrs.get(i);
		}
	}
	
	public void print() {
		
		String outputDir=PropertyParser.getPropertyByName("PopSynResult.directory");
		String HHFileName=PropertyParser.getPropertyByName("HHFile");
		String PersonFileName=PropertyParser.getPropertyByName("PersonFile");
				
        int[] HHTableRecord = new int[hhAttrs.length];
        int[] PersonTableRecord = new int[personAttrs.length];

		int PersonTableRowCounter=0;
		
        int NoHHCat=PopSyn.length;
        int NoTAZ=PopSyn[0].length;
        
		//current HH
		DrawnHH hh=null;
		//Derived HH
		DerivedHH dhh=null;
		//current Person
		DerivedPerson person=null;
		
        
        
        PrintWriter hhStream = null;
        PrintWriter personStream = null;

        try {
            
            // open output streams for writing HH and Person files
            hhStream = new PrintWriter( new BufferedWriter( new FileWriter(outputDir+HHFileName) ) );
            personStream = new PrintWriter( new BufferedWriter( new FileWriter(outputDir+PersonFileName) ) );

            
            
            // write file header records
            hhStream.print ( "HHID,TAZ" );
            for(int m=2; m < hhAttrs.length - 1; m++)
                hhStream.print( "," + hhAttrs[m] );
            hhStream.println( "," + hhAttrs[hhAttrs.length - 1] );

            personStream.print ( "HHID,PERID" );
            for(int m=2; m < personAttrs.length - 1; m++)
                personStream.print( "," + personAttrs[m] );
            personStream.println( "," + personAttrs[personAttrs.length - 1] );


                
            // construct the hh records and person records and write them to the repective files    
    		int HHID=1;
            int PERID=1;
    		for(int i=0; i<NoHHCat; i++){
    			for(int j=0; j<NoTAZ; j++){
    				
                    //number of HHs in current PopSyn cell
    				int NoHHs=PopSyn[i][j].size();
    				for(int k=0; k<NoHHs; k++){
    					
                        //get current HH
    					hh=(DrawnHH)PopSyn[i][j].get(k);
    					dhh=hh.getDerivedHH();
    					
                        //set values for first 2 cols of HH record
    					HHTableRecord[0] = HHID;
    					HHTableRecord[1] = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
                        
    					//set values for other cols of HH record
    					for(int m=2; m<hhAttrs.length; m++){
                            HHTableRecord[m] = hh.getHHAttr(hhAttrs[m]);
    					}

                        // write the household record to the file
                        hhStream.print( HHTableRecord[0] );
                        for(int m=1; m < hhAttrs.length - 1; m++)
                            hhStream.print( "," + HHTableRecord[m] );
                        hhStream.println( "," + HHTableRecord[hhAttrs.length - 1] );
                        
    					
    					//get number of persons in current HH
    					int NoPersons=dhh.getNoOfPersons();
    					for(int n=0; n<NoPersons; n++){
    						
                            //Get current person, person ID starts from 1?????
    						person=dhh.getPerson(n+1);
    						
                            //set value for 1st col of Person record
    						PersonTableRecord[0] = HHID;
                            PersonTableRecord[1] = PERID;
                            
    						//set other cols of Person table
    						for(int m=2; m<personAttrs.length; m++){
    							PersonTableRecord[m] = person.getPAttr(personAttrs[m]);
    						}
                            
                            // write the household record to the file
                            personStream.print( PersonTableRecord[0] + "," + PersonTableRecord[1]);
                            for(int m=2; m < personAttrs.length - 1; m++)
                                personStream.print( "," + PersonTableRecord[m] );
                            personStream.println( "," + PersonTableRecord[personAttrs.length - 1] );

                            //increase Person table row counter by 1
    						PersonTableRowCounter++;
                            PERID++;
    					}
    					HHID++;
    				}
                    
    			}
                
    		}
		
            hhStream.close();
            personStream.close();

            
            if(logDebug)
                logger.info("Number of households = " + HHID + ", number of persons = " + PersonTableRowCounter);
		
        }
        catch (IOException e) {
            logger.fatal ("I/O exception caught writing synthetic household and person output files.", e);
        }

    }
    
    
	/**
     * Prints a table with one record for each person, with household attributes
     * appended to those same records.  This format was added because it is expected
     * by the SF CHAMP model.   
     *
	 */
    public void printJointHHPersonAttributes() {
        
        String outputDir=PropertyParser.getPropertyByName("PopSynResult.directory");
        String jointFileName=PropertyParser.getPropertyByName("JointHHPersonFile");

        // determine whether or not to skip institutionalized GQ residents
        boolean skipInstGQ = false;
        if(PropertyParser.getPropertyByName("print.SkipInstGQinJointFile").equalsIgnoreCase("true")) skipInstGQ = true;
        
        // determine whether or not to write the header row
        boolean writeHeaderRow = false;
        if(PropertyParser.getPropertyByName("print.PrintJointHHPersonHeader").equalsIgnoreCase("true")) writeHeaderRow = true;      
        
        // this table specifies which columns to write
        TableDataSet fileSpec = readTableData("print.JointHHPersonPrintAttr");
        String[] printLabels = fileSpec.getColumnAsString("Label");
        String[] table       = fileSpec.getColumnAsString("Table");
        String[] sourceType  = fileSpec.getColumnAsString("SrcType");
        float[]  factor      = fileSpec.getColumnAsFloat("Factor");
        String[] dataItem    = fileSpec.getColumnAsString("DataItem");
        String[] formatSpec  = fileSpec.getColumnAsString("Format");
                
        float[] jointTableRecord = new float[printLabels.length + 3];
        String[] format = new String[formatSpec.length + 3];

        int PersonTableRowCounter=0;
        
        int NoHHCat=PopSyn.length;
        int NoTAZ=PopSyn[0].length;
        
        //current HH
        DrawnHH hh=null;
        //Derived HH
        DerivedHH dhh=null;
        //current Person
        DerivedPerson person=null;
        
        PrintWriter jointStream = null;

        try {
            
            // open output streams for writing HH and Person files
            jointStream = new PrintWriter( new BufferedWriter( new FileWriter(outputDir+jointFileName) ) );            
            
            // write file header records
            if (writeHeaderRow) {
                jointStream.print ("HHID PERID TAZ " );
                for(int m=0; m < printLabels.length; m++) {
                    jointStream.print(printLabels[m] + " " );
                }
                jointStream.print("\n");                
            }
                
            // construct the hh records and person records and write them to the repective files    
            int HHID=1;
            int PERID=1;
            int numSkipped=0;
            for(int i=0; i<NoHHCat; i++){
                for(int j=0; j<NoTAZ; j++){
                    
                    //number of HHs in current PopSyn cell
                    int NoHHs=PopSyn[i][j].size();
                    for(int k=0; k<NoHHs; k++){
                        
                        //get current HH
                        hh=(DrawnHH)PopSyn[i][j].get(k);
                        dhh=hh.getDerivedHH();
                        
                        //get number of persons in current HH
                        int NoPersons=dhh.getNoOfPersons();
                        for(int n=0; n<NoPersons; n++){

                            //Get current person
                            person=dhh.getPerson(n+1);
                            
                            if (dhh.getHHDerivedAttr("hunittype")==1 && skipInstGQ) {
                                numSkipped++;
                            } else {
                                // set the first values
                                jointTableRecord[0] = HHID;
                                jointTableRecord[1] = PERID;
                                jointTableRecord[2] = ExtTAZtoIntTAZIndex.getExternalTAZ(j+1);
                                
                                format[0] = "%.0f";
                                format[1] = "%.0f";
                                format[2] = "%.0f";
                                                                                                                    
                                //set other cols of joint table
                                for (int m=0; m<printLabels.length; m++) {
                                    float value = 0;
                                    String[] attribute = parseDataItems(dataItem[m]);
                                    if (table[m].equalsIgnoreCase("pums")) {
                                        if (sourceType[m].equalsIgnoreCase("hh")) {
                                            for (int a=0; a<attribute.length; a++) {
                                                value += (float) dhh.getHHAttr(attribute[a]);
                                            }
                                        } else {
                                            for (int a=0; a<attribute.length; a++) {
                                                value += (float) person.getPAttr(attribute[a]);
                                            }
                                        }                                    
                                    } else {
                                        if (sourceType[m].equalsIgnoreCase("hh")) {
                                            for (int a=0; a<attribute.length; a++) {
                                                value += (float) dhh.getHHDerivedAttr(attribute[a]);
                                            }
                                        } else {
                                            for (int a=0; a<attribute.length; a++) {
                                                value += (float) person.getPDerivedAttr(attribute[a]);
                                            }
                                        }    
                                    } 
                                    jointTableRecord[m+3] = value * factor[m];
                                    format[m+3] = formatSpec[m];
                                }                                                        
                                
                                // write the household record to the file
                                for(int m=0; m < (jointTableRecord.length); m++) {
                                    String entry = String.format(format[m], jointTableRecord[m]);
                                    jointStream.print(entry + " ");
                                }
                                jointStream.print("\n");

                                //increase Person table row counter by 1
                                PersonTableRowCounter++;
                            }
                            PERID++;
                        }
                        HHID++;
                    }                    
                }                
            }
        
            jointStream.close();
            
            logger.info("Number of households = " + HHID + ", number of persons = " + PersonTableRowCounter);
            logger.info("Skipped " + numSkipped + " persons living in institutional group quarters");
        }
        catch (IOException e) {
            logger.fatal ("I/O exception caught writing joint household-person output files.", e);
        }
    }
    
    /** 
     * Reads a CSV data file.  
     * 
     * @return The table data set read into memory.  
     */
    private TableDataSet readTableData(String rbProperty) {
        String fileName=PropertyParser.getPropertyByName(rbProperty);
        logger.info("Reading file " + fileName);
        
        TableDataSet data  = new TableDataSet();        
        try {
            CSVFileReader reader = new CSVFileReader();
            data = reader.readFile(new File(fileName));
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        return data; 
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
}
