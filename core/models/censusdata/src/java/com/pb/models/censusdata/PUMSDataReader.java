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
package com.pb.models.censusdata;

import com.pb.common.datafile.TableDataSet;
import com.pb.models.censusdata.DataDictionary;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;

import org.apache.log4j.Logger;

/**
 * The PUMSDataReader class is used to read PUMS data files.
 *
 */

public class PUMSDataReader {

    protected static Logger logger = Logger.getLogger(PUMSDataReader.class);

    TableDataSet hhTableData = null;
    TableDataSet personTableData = null;
    
    
    public PUMSDataReader () {
    }


    public TableDataSet getHhTableDataSet() {
        return hhTableData;
    }


    public TableDataSet getPersonTableDataSet() {
        return personTableData;
    }


	public void readPumsAttributes (String fileName, DataDictionary dd, String[] hhFieldNames, String[] personFieldNames ) {
	    readPumsAttributes ( fileName, dd, hhFieldNames, personFieldNames, null );
	}


	public void readPumsAttributes (String fileName, DataDictionary dd, String[] hhFieldNames, String[] personFieldNames, int[] pumaSet ) {

        int recCount = 0;
        int hhId = 0;
        int personId = 0;


        ArrayList[] hhAttribs = null;
        String[] hhAttribNames = null;
        if ( hhFieldNames != null ) {
            
            // we need to add two additional fields to the hh table, one for hhd, and the other for the
            // person table record number for the first person in this household. 
            hhAttribs = new ArrayList[hhFieldNames.length+2];
            for (int i=0; i < hhFieldNames.length+2; i++)
                hhAttribs[i] = new ArrayList();

            hhAttribNames = new String[hhFieldNames.length+2];
            for (int i=0; i < hhFieldNames.length; i++)
                hhAttribNames[i] = hhFieldNames[i];
            hhAttribNames[hhFieldNames.length] = "HHID";
            hhAttribNames[hhFieldNames.length+1] = "FIRSTPERSONID";
            
        }
        

        ArrayList[] personAttribs = null;
        String[] personAttribNames = null;
        if ( personFieldNames != null ) {
            
            // add one field to the person table for the hhid, i.e. the household table record number
            personAttribs = new ArrayList[personFieldNames.length+1];
            for (int i=0; i < personFieldNames.length+1; i++)
                personAttribs[i] = new ArrayList();

            personAttribNames = new String[personFieldNames.length+1];
            for (int i=0; i < personFieldNames.length; i++)
                personAttribNames[i] = personFieldNames[i];
            personAttribNames[personFieldNames.length] = "HHID";
            
        }   

        
		
		String personsFieldName = dd.getPersonsFieldName();
		String pumaFieldName = dd.getPumaFieldName();
		
		try {
			BufferedReader in = new BufferedReader(new FileReader(fileName));
			String s = new String();
            
			while ((s = in.readLine()) != null) {
				recCount++;
        
				// read the household attributes from the household data record
				if (getPUMSRecType(s, dd).equals("H")) {

		    		// skip HH records where persons field is zero
    				String numPersons = getPumsHhValue (s, personsFieldName, dd );
			    	if ( Integer.parseInt(numPersons) == 0 )
			    	    continue;
			    	    
			    	    
					// don't save info if hh's puma is not in pumaSet.  read person records then skip to next hh record.
					if ( pumaSet != null ) {
    	    			String puma = getPumsHhValue (s, pumaFieldName, dd );
    					if ( pumaSet[Integer.parseInt(puma)] == -1 ) {
    						for (int i=0; i < Integer.parseInt(numPersons); i++) {
    							s = in.readLine();
    							recCount++;
                            }
    						continue;
    					}
    				}
            

                    for (int i=0; i < hhFieldNames.length; i++) {
                        String stringValue = getPumsHhValue (s, hhFieldNames[i], dd );
                        hhAttribs[i].add( hhId, stringValue );
                    }
                    hhAttribs[hhFieldNames.length].add( hhId, Integer.toString(hhId) );
                    hhAttribs[hhFieldNames.length+1].add( hhId, Integer.toString(personId) );                    


					// read the person records for the number of persons in the household.
					for (int j=0; j < Integer.parseInt(numPersons); j++) {
						s = in.readLine();
        				recCount++;
					
						if (! getPUMSRecType(s, dd).equals("P")) {
							logger.fatal("Expected P record type on record: " + recCount + " but got: " + getPUMSRecType(s, dd) + ".");
							logger.fatal("exiting readData(" + fileName + ") in PUMSData.");
							System.exit (-1);
						}
							
                        if ( personAttribs != null ) {
                            
                            for (int i=0; i < personFieldNames.length; i++) {
                                String stringValue = getPumsPersValue (s, personFieldNames[i], dd );
                                personAttribs[i].add( personId, stringValue );
                            }
                            personAttribs[personFieldNames.length].add( personId, Integer.toString(hhId) );

                        }
                        
                        personId++;
                            	
					}
					
                    hhId++;

				}
				else {
					logger.fatal("Expected H record type on record: " + recCount + " but got: " + getPUMSRecType(s, dd) + ".");
					logger.fatal("exiting readData(" + fileName + ") in PUMSData.");
					System.exit (-1);
				}
				
			}

		} catch (Exception e) {

			logger.fatal ("IO Exception caught reading pums data file: " + fileName, e);
			System.exit(-1);
			
		}

		
        if ( hhAttribs != null )
            hhTableData = getTableDataSet ( hhAttribs, hhAttribNames );

        if ( personAttribs != null )
            personTableData = getTableDataSet ( personAttribs, personAttribNames );
		
	}
    
    

    private TableDataSet getTableDataSet ( ArrayList[] attribs, String[] fieldNames ) {
        
        int numFields = fieldNames.length;
        int numRecords = attribs[0].size();
        
        // save int values in numeric fields and String values in String fields
        float[][] numericFields = new float[numRecords][numFields];
        String[][] stringFields = new String[numRecords][numFields];

        // this index array has a 1 if field is an int field, 0 otherwise;        
        int[] numericFieldIndex = new int[numFields];


        for (int j=0; j < numFields; j++) {

            numericFieldIndex[j] = 1;
            
            for (int i=0; i < numRecords; i++) {
                
                // try to convert value to an int to save in an int field
                try {
                    numericFields[i][j] = Integer.parseInt( (String)attribs[j].get(i) );
                }
                // if runtime exception occurs, save all values in this field as String values
                catch (Exception e) {
                    for (int k=0; k < numRecords; k++) {
                        stringFields[k][j] = ((String)attribs[j].get(k)).trim();
                    }
                    numericFieldIndex[j] = 0;
                    break;
                }
                
            }
            
        }
        
        
        // create an array of int fields only.  Save as float[][] so TableDataSet.create() can be used.
        int k = 0;
        for (int i=0; i < numFields; i++) {
            if ( numericFieldIndex[i] == 1 )
                k++;
        }
        
        float[][] numericArray = new float[numRecords][k];
        String[] numericArrayHeadings = new String[k];
        
        k = 0;
        for (int j=0; j < numFields; j++) {
            if ( numericFieldIndex[j] == 1 ) {
                numericArrayHeadings[k] = fieldNames[j];
                for (int i=0; i < numRecords; i++) {
                    numericArray[i][k] = numericFields[i][j];
                }
                k++;
            }
        }  
        
        // create a TableDataSet from the int fields
        TableDataSet intTableData = TableDataSet.create(numericArray, numericArrayHeadings);
        
        
        
        // create an array of String fields only
        k = 0;
        for (int i=0; i < numFields; i++) {
            if ( numericFieldIndex[i] == 0 )
                k++;
        }
        
        String[][] stringArray = new String[numRecords][k];
        String[] stringArrayHeadings = new String[k];
        
        k = 0;
        for (int j=0; j < numFields; j++) {
            if ( numericFieldIndex[j] == 0 ) {
                stringArrayHeadings[k] = fieldNames[j];
                for (int i=0; i < numRecords; i++) {
                    stringArray[i][k] = stringFields[i][j];
                }
                k++;
            }
        }  
        
        // create a TableDataSet from the int fields
        TableDataSet stringTableData = TableDataSet.create(stringArray, stringArrayHeadings);
        

        
        // merge the stringTableData onto the inTableData
        intTableData.merge (stringTableData);
        
        
        return intTableData;
        
    }
    
    
    private String getPUMSRecType (String s, DataDictionary dd) {
        return s.substring(dd.getStartCol(dd.HHAttribs, "RECTYPE"), dd.getLastCol(dd.HHAttribs, "RECTYPE"));        
    }


    private String getPumsHhValue (String s, String PUMSVariable, DataDictionary dd) {
        return s.substring(dd.getStartCol(dd.HHAttribs, PUMSVariable), dd.getLastCol(dd.HHAttribs, PUMSVariable) );        
    }

    private String getPumsPersValue (String s, String PUMSVariable, DataDictionary dd) {
        return s.substring(dd.getStartCol(dd.PersAttribs, PUMSVariable), dd.getLastCol(dd.PersAttribs, PUMSVariable) );        
    }

}

