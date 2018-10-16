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

import java.io.File;
import java.io.IOException;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.TextFile;


public class HhSize {

    private static Logger logger = Logger.getLogger(HhSize.class);
    
    String[] hhSizeLabels;        
    int[] hhSizeValues;        
        
        
    public HhSize () {
    }

    

	// return the number of hhSize categories.    
	public int getNumberHhSizeCategories() {
		return hhSizeLabels.length;
	}



	// return the hhSize category index given the pums number of persons code
	// from the pums person record PERSONS field.    
    public int getHhSize(int persons) {

        int returnValue=0;

        if ( persons >= hhSizeValues.length )
            returnValue = hhSizeValues.length - 1;
        else
            returnValue = persons - 1;
        
        return returnValue;
    }



	// return the workers category label given the index.    
	public String getHhSizeLabel(int hhSizeIndex) {
		return hhSizeLabels[hhSizeIndex];
	}



	// return all the workers category labels.    
	public String[] getHhSizeLabels() {
		return hhSizeLabels;
	}


	// return the array of households by number of persons from the named file
	public int[] getHhsByHhSize( String fileName ) {
	 
		String[] formats = { "STRING", "NUMBER" };
		
		// read the base households by number of workers file into a TableDataSet
		CSVFileReader reader = new CSVFileReader();
        
		TableDataSet table = null;
		try {
			table = reader.readFileWithFormats( new File( fileName ), formats );
		} catch (IOException e) {
			e.printStackTrace();
		}
	    
		// this table has one row of number of households for each workers per household category
		String[] tempLabels = table.getColumnAsString(1);
		int[] persons = table.getColumnAsInt(2);
		
        hhSizeLabels = new String[tempLabels.length];
        hhSizeValues = new int[tempLabels.length];

		for (int i=0; i < tempLabels.length; i++) {
            hhSizeLabels[i] = tempLabels[i];
            hhSizeValues[i] = persons[i];
        }
	    
		return hhSizeValues;
	}

	// return the array of households by number of persons from the named file
	public int[] getHhsByHhSize( String fileName, String currentYear ) {

        //read file as text so that first line can be parsed to determine how many columns
        //  this would be bad if this was a big file, but it is not, so we're ok
        int columns = (new TextFile(fileName)).getLine(0).trim().split(",").length;

        String[] columnFormats = new String[columns];
        columnFormats[0] = "STRING";
        for (int i = 1; i < columns; i++) {
            columnFormats[i] = "NUMBER";
        }
		
		// read the base households by number of workers file into a TableDataSet
		CSVFileReader reader = new CSVFileReader();
        
		TableDataSet table = null;
		try {
			table = reader.readFileWithFormats( new File( fileName ), columnFormats );
		} catch (IOException e) {
			e.printStackTrace();
		}

        // need to make sure table has right column labels
        String columnName = currentYear + "households";
        logger.info("HH Size Marginal HHs Column: " + columnName);
	    
		// this table has one row of number of households for each workers per household category
		String[] tempLabels = table.getColumnAsString(1);
		int[] persons = table.getColumnAsInt(columnName); 
		
        hhSizeLabels = new String[tempLabels.length];
        hhSizeValues = new int[tempLabels.length];

		for (int i=0; i < tempLabels.length; i++) {
            hhSizeLabels[i] = tempLabels[i];
            hhSizeValues[i] = persons[i];
        }
	    
		return hhSizeValues;
	}
	
	
	// return the proportions of worker categories relative to total employed households
	public float[] getHhsByHhSizeProportions( int[] personsPerHousehold ) {
		
		float[] proportions = new float[hhSizeLabels.length];
		float[] tempPersons = new float[hhSizeLabels.length];
		float totalHouseholds = 0;
		
		// workers in employed households start at workers category 1
		for (int i=0; i < personsPerHousehold.length; i++) {
			totalHouseholds += personsPerHousehold[i];
			if (i < hhSizeLabels.length - 1)
				tempPersons[i] = personsPerHousehold[i];
			else
				tempPersons[hhSizeLabels.length - 1] += personsPerHousehold[i];
		}
		
		
		// calculate proportions of workers in employed households
		for (int i=0; i < hhSizeLabels.length; i++)
			proportions[i] = tempPersons[i]/totalHouseholds;
		
		return proportions;
	}
	
}

