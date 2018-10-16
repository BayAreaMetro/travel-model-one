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

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.models.reference.IndustryOccupationSplitIndustryReference;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Random;

// the 1990 PUMS industry field name is INDUSTRY
// the 2000 PUMS industry field name is INDNAICS

public abstract class SwIndustry {

    protected static Logger logger = Logger.getLogger(SwIndustry.class);

    //set from the IndustryOccSplitIndustry reference object
    IndustryOccupationSplitIndustryReference ref;
    protected int maxIndustryIndex;
    protected int nIndustries;
    protected String[] swIndustryLabels;
    HashMap<String, Integer> industryLabelToIndustryIndex;

    String correspFileName;
    String year;
    HashMap<String, Integer> pumsIndustryStringToIndustryIndex = new HashMap<String, Integer>();
    private final boolean usingAcs;
    

    public SwIndustry ( String correspFileName, String year, IndustryOccupationSplitIndustryReference ref ) {
        this(correspFileName,year,ref,false);
    }

    public SwIndustry (String correspFileName, String year, IndustryOccupationSplitIndustryReference ref, boolean usingAcs) {
        this.usingAcs = usingAcs;
        this.correspFileName = correspFileName;
        this.year = year;
        this.maxIndustryIndex = ref.getMaxIndustryIndex();
        this.industryLabelToIndustryIndex = ref.getIndustryLabelToIndexMapping();
        this.swIndustryLabels = ref.getIndustryLabelsByIndex();
        this.nIndustries = ref.getNumOfIndustries();

        this.ref = ref;
        // read the correspondence file between PUMS Naics industry values and Sw model industry categories.
        //if correspondence file is null, then the PUMS correspondence is not needed/used, and this init step will be skipped
        if (correspFileName != null)
		    pumsIndustryToIndustry( correspFileName );
    }

    //constructor for case when PUMS correspondence not needed/invalid
    public SwIndustry (String year, IndustryOccupationSplitIndustryReference ref,boolean usingAcs) {
        this(null,year,ref,usingAcs);
    }

    
    // return the number of SW industry categories.
    public int getNumberIndustries() {
        return nIndustries;
    }

    
    
    // return the maximum SW industry category number.
    public int getMaxIndustryIndex() {
        return maxIndustryIndex;
    }
    
    // use this method to get the statewide industry category from a 1990 PUMS INDUSTRY code
    public int getIndustryIndexFromPumsCode ( int pumsCode ) {

        int returnValue = -1;

        if (usingAcs) {
            returnValue = getIndustryIndexFromAcsCode(pumsCode);
        } if ( year.equals("1990") ) {
            returnValue = getIndustryIndexFrom1990PumsCode(pumsCode);
        }
        else  {
            logger.error ("For PUMS2000 data, the industry code must be a String value.");
            System.exit(-1);
        }
        
        return returnValue;
        
    }
    
    
    // use this method to get the statewide industry category from a 2000 PUMS INDNAICS code
    public int getIndustryIndexFromPumsCode ( String pumsCode ) {

        int returnValue;
        
        if (usingAcs) {
            returnValue = getIndustryIndexFromAcsCode(Integer.parseInt(pumsCode));
        } else if ( year.equals("2000") ) {
            returnValue = getIndustryIndexFrom2000PumsCode(pumsCode);
        }
        else  {
            String msg = "For PUMS1990 data, the industry code must be an int value.";
            logger.error(msg);
            throw new RuntimeException(msg);
        }
        
        return returnValue;
        
    }
    
    
    // return the SW industry category index given the 2000 PUMS NAICS industry code
    // from the pums person record industry field.
    private int getIndustryIndexFrom2000PumsCode(String pumsNaics) {
        return pumsIndustryStringToIndustryIndex.get( pumsNaics );
    }



    // return the SW industry category index given the 1990 PUMS INDUSTRY code
    // from the pums person record industry field.
    private int getIndustryIndexFrom1990PumsCode(int pumsIndustry) {
        return pumsIndustryStringToIndustryIndex.get( Integer.toString(pumsIndustry) );
    }

    private int getIndustryIndexFromAcsCode(int pumsIndustry) {
        String ind = Integer.toString(pumsIndustry);
        if (!pumsIndustryStringToIndustryIndex.containsKey(ind)) {
            logger.info("not found: " + ind);
            logger.info("in: " + pumsIndustryStringToIndustryIndex);
        }
        return pumsIndustryStringToIndustryIndex.get(Integer.toString(pumsIndustry));
    }

    
    // return the SW Industry category index given the label.
    public int getIndustryIndexFromLabel(String industryLabel) {
        return industryLabelToIndustryIndex.get( industryLabel.trim() );
    }

    
    // return the array of SW industry labels
    public String[] getIndustryLabels() {
        return swIndustryLabels;
    }


    // return the array of SW industry labels
    public String getIndustryLabel(int i) {
        return swIndustryLabels[i];
    }

    //Should be implement by a project specific Industry class.
    //In OSMP, the columnIndicator is the current year
    //In TLUMIP, the columnIndicator is always "2"
   public abstract float[] getIndustryEmployment(String fileName, String columnIndicator);

    /**
     * This method will return a TableDataSet of dollars of employment
     * from an input file that has the first column as the employment sector
     * and one or more other columns with employment dollars by sector.
     * @param tableFileName
     * @return TableDataSet
     */
	protected TableDataSet getIndustryEmploymentTableData( String tableFileName ) {

		// read the SW regional employment by industry output file into a TableDataSet
		CSVFileReader reader = new CSVFileReader();

		TableDataSet table = null;
		try {
			table = reader.readFile(new File( tableFileName ));
		} catch (IOException e) {
			e.printStackTrace();
		}

		return table;
        
	}


    /**
     * This method will return a float array of dollars of employment
     * from a TableDataSet that has the first column as the employment sector
     * labels and one or more other columns with the employment dollars for one
     * or more years.  The column of interset is passed as an argument.
     * @param table of employment
     * @param column in file
     * @return float[]
     */
    protected float[] getIndustryEmploymentForColumn( TableDataSet table, int column ) {

        // get the SW regional employment by industry for the specified column from the TableDataSet

        // this table has one row of employment totals for each industry
        String[] tempIndustryLabels = table.getColumnAsString(1);
        float[] tempIndustryEmployment = table.getColumnAsFloat(column);
        float[] industryEmployment = new float[maxIndustryIndex+1];

        for (int i=0; i < tempIndustryLabels.length; i++) {
            int industryIndex = getIndustryIndexFromLabel( tempIndustryLabels[i] );
            industryEmployment[industryIndex] = tempIndustryEmployment[i];
        }

        return industryEmployment;
    }

    /**
     * This method will return a float array of dollars of employment
     * from a TableDataSet that has the first column as the employment sector
     * labels and one or more other columns with the employment dollars for one
     * or more years.  The column of interset is passed as an argument.
     * @param table of employment
     * @param column in file
     * @return float[]
     */
    protected float[] getIndustryEmploymentForColumn( TableDataSet table, String columnName ) {

        // get the SW regional employment by industry for the specified column from the TableDataSet

        // this table has one row of employment totals for each industry
        String[] tempIndustryLabels = table.getColumnAsString(1);
        float[] tempIndustryEmployment = table.getColumnAsFloat(columnName);
        float[] industryEmployment = new float[maxIndustryIndex+1];

        for (int i=0; i < tempIndustryLabels.length; i++) {
            int industryIndex = getIndustryIndexFromLabel( tempIndustryLabels[i] );
            industryEmployment[industryIndex] = tempIndustryEmployment[i];
        }

        return industryEmployment;
    }
    
    
	// read the pums/industry index correspondence table
    private void pumsIndustryToIndustry ( String fileName ) {

		// read the naics by industry correspondence file into a TableDataSet
		CSVFileReader reader = new CSVFileReader();
		TableDataSet table;
		String[] columnFormats = { "STRING", "STRING"};
		try {
			table = reader.readFileWithFormats( new File( fileName ), columnFormats );
		} catch (IOException e) {
			String msg = "Could not read file " + fileName + ".";
            logger.fatal(msg);
            throw new RuntimeException(msg, e);
		}

		// this table has a column of PUMS industry codes and the associated SW Industry category label
        String[] pumsIndustryStrings = table.getColumnAsString(1);
        String[] industryLabels = table.getColumnAsString(2);

        for (int i=0; i < industryLabels.length; i++) {
            boolean validLabel = ref.isIndustryLabelValid(industryLabels[i]);
		    String pumsIndustryString;
            if(validLabel){
                int id = ref.getIndustryIndexFromLabel(industryLabels[i]);
                pumsIndustryString = pumsIndustryStrings[i].trim();
                if (usingAcs) {
                    pumsIndustryStringToIndustryIndex.put("" + Integer.parseInt(pumsIndustryString),id);
                } else if (year.equals("1990")) {
                    if ( Integer.parseInt(pumsIndustryString) >= 0 && Integer.parseInt(pumsIndustryString) <= 999 ){
                        pumsIndustryStringToIndustryIndex.put( pumsIndustryString, id);
                    } else logger.warn(pumsIndustryString + " is not in the range of 0-999 - value will not be stored");
                } else {
                    pumsIndustryStringToIndustryIndex.put( pumsIndustryString, id);
                }
            } else{
                logger.warn(industryLabels[i] + " does not match the labels defined in the" +
                        " IndustryOccupationSplitIndustryCorrespondenceFile which is the definitive list");
            }

       }
    }

    
    public int getSplitIndustryIndex ( int unsplitIndustryIndex, int occupIndex ) {

        //return ref.getSplitIndustryIndexFromIndustryAndOccupation(unsplitIndustryIndex, occupIndex);
        return ref.getSplitIndustryIndex(unsplitIndustryIndex, occupIndex);
        
    }

    
}

