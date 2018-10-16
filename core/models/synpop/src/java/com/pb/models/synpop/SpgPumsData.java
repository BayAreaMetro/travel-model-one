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
package com.pb.models.synpop;

import com.pb.common.datafile.DataTypes;
import com.pb.common.datafile.TableDataSet;
import com.pb.models.censusdata.DataDictionary;
import com.pb.models.censusdata.PUMSDataReader;
import com.pb.models.censusdata.PumsGeography;
import com.pb.models.censusdata.SwIndustry;
import com.pb.models.censusdata.SwOccupation;
import com.pb.models.censusdata.Workers;
import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;

/**
 * The PUMSData class is used to manage input of PUMS data.
 *
 */

public class SpgPumsData {

    protected static Logger logger = Logger.getLogger(SpgPumsData.class);

    public static final int PUMS_HHID_INDEX = 2;
    public static final int HHID_INDEX = 3;
    public static final int STATE_INDEX = 4;
    public static final int PUMA_INDEX = 5;
    public static final int HHSIZE_INDEX = 6;
    public static final int HHINC_INDEX = 7;
    public static final int HHWT_INDEX = 8;
    public static final int HHWRKRS_INDEX = 9;
    
    public static final int PERSON_ARRAY_INDEX = HHWRKRS_INDEX + 1;
    
    DataDictionary dd;
    String year;
    SwIndustry ind = null;
    SwOccupation occ = null;
    Workers hhWorkers = null;

    
    
    public SpgPumsData (String PUMSDataDictionary, String year, SwIndustry ind, SwOccupation occ, Workers hhWorkers ) {
        this.dd = new DataDictionary( PUMSDataDictionary, year );
        this.year = year;
        this.ind = ind;
        this.occ = occ;
        this.hhWorkers = hhWorkers;
    }

    public ArrayList setSpg1Attributes (int stateIndex, String fileName, PumsGeography halo, HashMap fieldMap ) {
        return setSpg1Attributes(stateIndex,fileName,halo,fieldMap,null);
    }
    
    public ArrayList setSpg1Attributes(int stateIndex, String fileName, PumsGeography halo, HashMap fieldMap, PumsToSplitIndustry pumsToSplitIndustry) {


        // set the PUMS field names for fields needed by this method
        String[] hhFieldNames = { (String)fieldMap.get( "hhIdField" ),
                (String)fieldMap.get( "personsName" ),
                (String)fieldMap.get( "stateName" ),
                (String)fieldMap.get( "pumaName" ),
                (String)fieldMap.get( "hhIncName" ),
                (String)fieldMap.get( "hhWeightName" ) };

        String[] personFieldNames = { (String)fieldMap.get( "empStatName" ),
                (String)fieldMap.get( "industryName" ),
                (String)fieldMap.get( "occupationName" ),
                (String)fieldMap.get( "personAgeName" ),
                (String)fieldMap.get( "personWeightName" ),
                (String)fieldMap.get( "hhIdField" ) };

        // get the pumaIndex array for the state being read
        int[] pumaSet = halo.getStatePumaIndexArray(stateIndex);

        
        // now read the PUMS data.
        // read only the hh records residing in pumas which intersect our study area.
        // read only the PUMS hh and person fields specified.
        PUMSDataReader dr = new PUMSDataReader();
        dr.readPumsAttributes(fileName, dd, hhFieldNames, personFieldNames, pumaSet);

        return setSpg1AttributesFromData(dr.getHhTableDataSet(),dr.getPersonTableDataSet(),fieldMap,year,ind,occ,hhWorkers,pumsToSplitIndustry);
    }

    //convenience method to let me leverage this stuff from outside this class
    protected static ArrayList setSpg1AttributesFromData(TableDataSet hhTable, TableDataSet personTable, HashMap fieldMap, String year, SwIndustry ind, SwOccupation occ, Workers hhWorkers, PumsToSplitIndustry pumsToSplitIndustries) {
        ArrayList hhList = new ArrayList();
        int[] hhAttribs = null;
        final boolean serialStringType = hhTable.getColumnType()[hhTable.getColumnPosition((String) fieldMap.get("hhIdField"))-1] == DataTypes.STRING;
        for (int h=1; h < hhTable.getRowCount()+1; h++) {

            // get the hh attribute values for this hh
            int hhid = (int)hhTable.getValueAt( h, "HHID" );
            //asume using strings because id too long, so have to truncate down to 9 digits
            int pumsHhId = serialStringType ? Integer.parseInt(hhTable.getStringValueAt(h,(String) fieldMap.get("hhIdField")).substring(0,9)):
                                              (int) hhTable.getValueAt(h,(String) fieldMap.get("hhIdField"));
            int numPersons = (int)hhTable.getValueAt( h, (String)fieldMap.get( "personsName" ) );
            int stateFips = (int)hhTable.getValueAt( h, (String)fieldMap.get( "stateName" ) );
            int puma = (int)hhTable.getValueAt( h, (String)fieldMap.get( "pumaName" ) );
            int hhIncome = (int)hhTable.getValueAt( h, (String)fieldMap.get( "hhIncName" ) );
            int hhWeight = (int)hhTable.getValueAt( h, (String)fieldMap.get( "hhWeightName" ) );

            int personOffset = (int)hhTable.getValueAt( h, "FIRSTPERSONID" ) + 1;

            hhAttribs = new int[PERSON_ARRAY_INDEX + SPG.NUM_PERSON_ATTRIBUTES*numPersons + SPG.NUM_PERSON_ATTRIBUTES];

            hhAttribs[PUMS_HHID_INDEX] = pumsHhId;
            hhAttribs[HHID_INDEX] = hhid;
            hhAttribs[STATE_INDEX] = stateFips;
            hhAttribs[PUMA_INDEX] = puma;
            hhAttribs[HHSIZE_INDEX] = numPersons;
            hhAttribs[HHINC_INDEX] = hhIncome;
            hhAttribs[HHWT_INDEX] = hhWeight;


            // get the person attribute values for all persons in the household.
            int workers = 0;
            int employed = 0;
            for (int i=0; i < numPersons; i++) {

                int rlabor = (int)personTable.getValueAt( personOffset + i, (String)fieldMap.get( "empStatName" ) );
                int personWeight = (int)personTable.getValueAt( personOffset + i, (String)fieldMap.get( "personWeightName" ) );
                int age = (int)personTable.getValueAt( personOffset + i, (String)fieldMap.get( "personAgeName" ) );

                int industry = 0;
                int occup = 0;

                if (pumsToSplitIndustries != null) {
                    int pumsInd = (int) personTable.getValueAt(personOffset + i,(String) fieldMap.get("industryName"));
                    int pumsOcc = (int) personTable.getValueAt(personOffset + i,(String) fieldMap.get("occupationName"));
                    industry = pumsToSplitIndustries.selectSplitIndustry(pumsInd,pumsOcc);
                    occup = occ.getOccupationIndexFromPumsCode(pumsOcc);
                } else if ( year.equals("1990") ) {

                    int pumsInd = (int)personTable.getValueAt( personOffset + i, (String)fieldMap.get( "industryName" ) );
                    industry = ind.getIndustryIndexFromPumsCode(pumsInd);

                    int pumsOcc = (int)personTable.getValueAt( personOffset + i, (String)fieldMap.get( "occupationName" ) );
                    occup = occ.getOccupationIndexFromPumsCode(pumsOcc);

                }
                else if ( year.equals("2000") ) {

                    String pumsInd = null;
                    String pumsOcc = null;

                    try {
                        pumsInd = personTable.getStringValueAt( personOffset + i, (String)fieldMap.get( "industryName" ) );
                        industry = ind.getIndustryIndexFromPumsCode(pumsInd);
                    }
                    catch (Exception e) {
                        logger.error("could not find correspondence value for PUMS 2000 industry code = " + pumsInd + ", h = " + h + ", i = " + i );
                        System.exit(1);
                    }

                    try {
                        pumsOcc = personTable.getStringValueAt( personOffset + i, (String)fieldMap.get( "occupationName" ) );
                        occup = occ.getOccupationIndexFromPumsCode(pumsOcc);
                    }
                    catch (Exception e) {
                        logger.error("could not find correspondence value for PUMS 2000 occupation code = " + pumsOcc + ", h = " + h + ", i = " + i );
                        System.exit(1);
                    }

                }


                switch (rlabor) {
                    case 0:
                    case 3:
                    case 6:
                        employed = 0;
                        industry = 0;
                        occup = 0;
                        break;
                    case 1:
                    case 2:
                    case 4:
                    case 5:
                        employed = 1;
                        workers++;
                        break;
                }


                // save industry for each person followed by occup for each person in hhAttrib array.
                hhAttribs[PERSON_ARRAY_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES + 0] = industry;
                hhAttribs[PERSON_ARRAY_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES + 1] = occup;
                hhAttribs[PERSON_ARRAY_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES + 2] = employed;
                hhAttribs[PERSON_ARRAY_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES + 3] = personWeight;
                hhAttribs[PERSON_ARRAY_INDEX + i*SPG.NUM_PERSON_ATTRIBUTES + 4] = age;

            }

            if ( workers > hhWorkers.getNumberWorkerCategories()-1 )
                hhAttribs[HHWRKRS_INDEX] = hhWorkers.getNumberWorkerCategories()-1;
            else
                hhAttribs[HHWRKRS_INDEX] = workers;

            hhList.add (hhid, hhAttribs);

        }

        return (hhList);

    }
    
    
	public ArrayList readSpg2OutputAttributes (  String fileName, String[] hhFieldNames, String[] personFieldNames, PumsGeography halo, HashMap fieldMap ) {

        String pumaFieldName = (String)fieldMap.get( "pumaName" );
        String stateFieldName = (String)fieldMap.get( "stateName" );
        String personsFieldName = (String)fieldMap.get( "personsName" );

        int recCount=0;
		
		int hhid = 0;
		int numPersons = 0;
		int puma = 0;
		int state = 0;

		ArrayList hhList = new ArrayList();
		
	
		try {
			BufferedReader in = new BufferedReader(new FileReader(fileName));
			String s = new String();
            
			while ((s = in.readLine()) != null) {
			    
				recCount++;
                numPersons = getPUMSHHDataValue (s, personsFieldName );

				// skip HH records where persons field is zero
				if ( numPersons > 0 ) {

					String[][] outputFieldValues = new String[numPersons+1][];
					outputFieldValues[0] = new String[hhFieldNames.length];
					for (int i=0; i < numPersons; i++)
						outputFieldValues[i+1] = new String[personFieldNames.length];
				
				
					// read the household attributes from the household data record
					if (getPUMSRecType(s).equals("H")) {

                        state = getPUMSHHDataValue (s, stateFieldName );
                        puma = getPUMSHHDataValue (s, pumaFieldName);

						// don't save info if hh is not in halo.  read person records then skip to next hh record.
						if ( !halo.isFipsPumaInHalo ( state, puma ) ) {

							for (int i=0; i < numPersons; i++)
								s = in.readLine();

							continue;
							
						}
            

						for (int j=0; j < hhFieldNames.length; j++)
							outputFieldValues[0][j] = getPUMSHHStringValue ( s, hhFieldNames[j] );
					    

						// read the person records for the number of persons in the household.
						for (int i=0; i < numPersons; i++) {
							s = in.readLine();

							if (! getPUMSRecType(s).equals("P")) {
								logger.fatal("Expected P record type on record: " + recCount + " but got: " + getPUMSRecType(s) + ".");
								logger.fatal("exiting readData(" + fileName + ") in PUMSData.");
								logger.fatal("exit (21)");
								System.exit (21);
							}

							for (int j=0; j < personFieldNames.length; j++)
								outputFieldValues[i+1][j] = getPUMSPersStringValue ( s, personFieldNames[j] );
						}
						
					}
					else {
						logger.fatal("Expected H record type on record: " + recCount + " but got: " + getPUMSRecType(s) + ".");
						logger.fatal("exiting readData(" + fileName + ") in PUMSData.");
						logger.fatal("exit (20)");
						System.exit (20);
					}
				
	
					hhList.add (hhid, outputFieldValues);
					hhid++;

				}
				
			}

		} catch (Exception e) {

			logger.fatal ("IO Exception caught reading pums data file: " + fileName, e);
			System.exit(1);
			
		}

		
		return (hhList);
	}
    
    
    private String getPUMSRecType (String s) {
        return s.substring(dd.getStartCol(dd.HHAttribs, "RECTYPE"), dd.getLastCol(dd.HHAttribs, "RECTYPE"));
    }


    private int getPUMSHHDataValue (String s, String PUMSVariable) {
        return Integer.parseInt ( s.substring(dd.getStartCol(dd.HHAttribs, PUMSVariable.trim()), dd.getLastCol(dd.HHAttribs, PUMSVariable.trim())) );
    }


    private String getPUMSHHStringValue (String s, String PUMSVariable) {
        return s.substring(dd.getStartCol(dd.HHAttribs, PUMSVariable.trim()), dd.getLastCol(dd.HHAttribs, PUMSVariable.trim()) );
    }

    
    private String getPUMSPersStringValue (String s, String PUMSVariable) {
        return s.substring(dd.getStartCol(dd.PersAttribs, PUMSVariable.trim()), dd.getLastCol(dd.PersAttribs, PUMSVariable.trim()) );
    }


    public void printPUMSDictionary () {
     
        logger.info ("PUMS Houshold Attributes");
		logger.info ("------------------------");
        dd.printDictionary(dd.HHAttribs);

		logger.info (" ");
		logger.info (" ");
           
		logger.info ("PUMS Person Attributes");
		logger.info ("----------------------");
        dd.printDictionary(dd.PersAttribs);
    }

}

