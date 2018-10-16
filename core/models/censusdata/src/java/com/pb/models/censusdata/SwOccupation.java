package com.pb.models.censusdata;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.model.ModelException;
import com.pb.models.reference.IndustryOccupationSplitIndustryReference;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;

//the 1990 PUMS industry field name is OCCUP
//the 2000 PUMS industry field name is OCCSOC5

public class SwOccupation {

    protected static Logger logger = Logger.getLogger(SwOccupation.class);

    protected IndustryOccupationSplitIndustryReference ref;
    protected static String[] swOccupationLabels;
    HashMap<String, Integer> occupationLabelToOccupationIndex = new HashMap<String, Integer>();
    int maxOccupationIndex;
    int nOccupations;


    HashMap<String, Integer> pumsOccupationStringToOccupationIndex = new HashMap<String, Integer>();
	String correspFileName;
    String year;
    private final boolean usingAcs;
	

    public SwOccupation ( String correspFileName, String year, IndustryOccupationSplitIndustryReference ref ) {
        this(correspFileName,year,ref,false);
    }
    
    public SwOccupation ( String correspFileName, String year, IndustryOccupationSplitIndustryReference ref , boolean usingAcs) {
        this.usingAcs = usingAcs;
        this.correspFileName = correspFileName;
        this.year = year;

        this.nOccupations = ref.getNumOfOccupations();
        this.maxOccupationIndex = ref.getMaxOccupationIndex();
        swOccupationLabels = ref.getOccupationLabelsByIndex();
        this.occupationLabelToOccupationIndex = ref.getOccupationLabelToIndexMapping();

        this.ref = ref;
        // establish the correspondence table between pums occupation codes and SW occupation categories
		pumsOccsoc5ToOccupation( correspFileName );

    }


    // return the number of occupation categories.    
	public int getNumberOccupations() {
		return swOccupationLabels.length;
	}



    // if an int argument is supplied, the year must be 1990
    public int getOccupationIndexFromPumsCode ( int pumsCode ) {

        int returnValue = -1;

        if (usingAcs) {
            returnValue = getOccupationIndexFromAcs(pumsCode);
        } else if ( year.equals("1990") ) {
            returnValue = getOccupationIndexFromPums1990Code(pumsCode);
        }
        else  {
            String msg = "For PUMS2000 data, the occupation code must be a " +
                    "String value.";
            logger.error(msg);
            throw new ModelException(msg);
        }
        
        return returnValue;
        
    }
    
    
    // if a String argument is supplied, the year must be 2000
    public int getOccupationIndexFromPumsCode ( String pumsCode ) {

        int returnValue = -1;
        
        if (usingAcs) {
            returnValue = getOccupationIndexFromAcs(Integer.parseInt(pumsCode));
        } else if ( year.equals("2000") ) {
            returnValue = getOccupationIndexFromPums2000Code(pumsCode);
        }
        else  {
            logger.error ("For PUMS1990 data, the occupation code must be an int value.");
            System.exit(-1);
        }
        
        return returnValue;
        
    }
    

    // return the SW occupation category index given the 2000 PUMS OCCSOC5 occupation code
    // from the pums person record occupation field.
    private int getOccupationIndexFromPums2000Code(String pumsOccsoc5) {

        try {
            return pumsOccupationStringToOccupationIndex.get(pumsOccsoc5);
        } catch (Exception e) {
            String msg = "Could not find " + pumsOccsoc5 + " in the PUMS code "
                    + "correspondence file.";
            logger.fatal(msg);
            throw new ModelException(msg);
        }
    }

    // return the SW occupation category index given the 1990 PUMS OCCUP occupation code
    // from the pums person record occupation field.
    private int getOccupationIndexFromPums1990Code(int pumsOccup) {
        return pumsOccupationStringToOccupationIndex.get( Integer.toString(pumsOccup) );
    }

    private int getOccupationIndexFromAcs(int pumsOccup) {
        return pumsOccupationStringToOccupationIndex.get(Integer.toString(pumsOccup));
    }

    // return the SW Occupation category index given the SW Occupation category label.
    public int getOccupationIndexFromLabel(String occupationLabel) {
        return occupationLabelToOccupationIndex.get( occupationLabel );
    }
    

    // return the occupation category label given the index.    
	public String getOccupationLabel(int pumsOccupationIndex) {
		return swOccupationLabels[pumsOccupationIndex];
	}



    // return all the occupation category labels.    
    public String[] getOccupationLabels() {
        return swOccupationLabels;
    }


	// define the pums/swOccupation index correspondence table
	private void pumsOccsoc5ToOccupation ( String fileName ) {
        
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
	    
        
        // this table has a column of PUMS occupation codes and the associated SW Occupation index and category label
        String[] pumsOccupationStrings = table.getColumnAsString(1);
        String[] occupationLabels = table.getColumnAsString(2);

        for (int i=0; i < occupationLabels.length; i++) {
            boolean validLabel = ref.isOccupationLabelValid(occupationLabels[i]);
            String pumsOccupationString;
            if(validLabel){
                pumsOccupationString = pumsOccupationStrings[i].trim();
                int id = ref.getOccupationIndexFromLabel(occupationLabels[i]);
                if (usingAcs) {
                    pumsOccupationStringToOccupationIndex.put("" + Integer.parseInt(pumsOccupationString),id);
                } else if (year.equals("1990")) {
                    if ( Integer.parseInt(pumsOccupationString) >= 0 && Integer.parseInt(pumsOccupationString) <= 999 ){
                        pumsOccupationStringToOccupationIndex.put( pumsOccupationString, id);
                    } else logger.warn("pumsOccupationString was not in the range 0-999 - value was not stored");
                } else {
                    pumsOccupationStringToOccupationIndex.put( pumsOccupationString, id);    
                }
            } else{
                logger.warn(occupationLabels[i] + " does not match the labels defined in the" +
                        " IndustryOccupationSplitIndustryCorrespondenceFile which is the definitive list");
            }
        }

     }

    
}

