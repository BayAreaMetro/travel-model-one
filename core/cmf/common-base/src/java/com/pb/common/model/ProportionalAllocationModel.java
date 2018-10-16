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
package com.pb.common.model;
 /**
 * @author fujioka, freedman
 * 
 * This class provides a generic implementation of a proportional model which uses the average value 
 * of some unit (a TAZ, for example) to index into a table of proportions (by any stratification),
 * to determine the distribution of households or some other aggregate category by each stratification.
 * An example of use would be a household income submodel.  The distribution of households by n income
 * groups and y categories of income index is given in the proportionFile, and a tazdata file is given 
 * which lists the income index for every zone.  The model uses the index for each zone to lookup 
 * the proportion of households for each income group, and those proportions are cross-multiplied by the
 * households in each zone to determine the number of households by income group.
 * 
 * Inputs: 
 * 
 * 1) A csv data file with one record for each geographic unit, with the lookup value for each unit,
 * and the aggregate value to be distributed (eg households, persons, or any other typical value). Note that
 * the index value should be in real (floating point) precision 
 * 
 * 2) a csv proportion file with one record per index value, and one field for each proportion category.
 *
 * Output:  same input data file with the # of Households by each proportional group added.
 * 
 * 
 * Created April 20, 2005
 */
import java.io.File;
import java.io.IOException;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;

public class ProportionalAllocationModel {

	protected static Logger logger = Logger
			.getLogger("com.pb.pag.tripgeneration");

    protected HashMap proportionsMap;
    protected String[] proportionTableLabels;
    protected String[] outputFieldNames; 
    protected TableDataSet dataTable = null;
    protected int precision=0;
    protected float maxIndex = 0;
    protected float minIndex = 0;
    protected int numberOfGroups=0;
    protected int aggregateQuantityPosition=0;
    protected String aggregateQuantityField = null;
    protected int dataTableIndexPosition=0;
    protected String dataTableIndexField = null;
 
	/**
	 * Public constructor
	 */
	public ProportionalAllocationModel() {
	}

    /**
     * Public constructor with proportion file name:
     *   Format: comma-separated value with row headings:
     *   Field 1:    Index value, in integer format (tenths)
     *   Field 2-n:  The proportion in each of n categories.  They must add up to 1.0
     *
     * @param proportionFileName
     */
    public ProportionalAllocationModel(String proportionFileName) {
        
        readProportionFile(proportionFileName);
        
    }
	/**
	 * Read a TableDataSet of the geographic (zonal) data file.
	 * 
     * @param fileName                 The name/path of the geographic data file.
     * @param aggregateQuantityField   The name of the field in the data file containing aggregate data to allocate.
     * @param indexField               The name of the field in the data file to use as an index into the proportions file.
     * @return zonal or other geographic data file.
     * 
     */
	public TableDataSet readDataFile(String fileName, String aggregateQuantityField, String indexField) {

		logger.info("Reading data file " + fileName);
		dataTable = null;

		try {
			CSVFileReader reader = new CSVFileReader();
			dataTable = reader.readFile(new File(fileName));
		} catch (IOException e) {
			e.printStackTrace();
			System.exit(1);
		}

        aggregateQuantityPosition = dataTable.checkColumnPosition(aggregateQuantityField);
        this.aggregateQuantityField = aggregateQuantityField;
        dataTableIndexPosition = dataTable.checkColumnPosition(indexField);
        this.dataTableIndexField = indexField;
        
	/*	logger.debug("Building index");
		dataFile.buildIndex(1);
    */
		return dataTable;
	}

    /**
     * Sets a TableDataSet of the geographic (zonal) data file.
     * Use this instead of readDataFile() if you already have it stored in memory. 
     * 
     * @param data                     The the geographic data table.  
     * @param aggregateQuantityField   The name of the field in the data file containing aggregate data to allocate.
     * @param indexField               The name of the field in the data file to use as an index into the proportions file.
     * 
     */
    public void setDataFile(TableDataSet data, String aggregateQuantityField, String indexField) {

        dataTable = data;

        aggregateQuantityPosition = dataTable.checkColumnPosition(aggregateQuantityField);
        this.aggregateQuantityField = aggregateQuantityField;
        dataTableIndexPosition = dataTable.checkColumnPosition(indexField);
        this.dataTableIndexField = indexField;
    }
    
	/**
	 * Read a TableDataSet of the proportions data file.
	 * 
	 * Format: comma-separated value with row headings:
     *   Field 1:    Index value--use enough precision to avoid truncation error
     *   Field 2-n:  The proportion in each of n categories.  They must add up to 1.0
	 * 
     * @param  Path and name of model curves data file in csv format
	 * @return HashTable of arrays of model data mapped by Float index values
	 */
	public HashMap readProportionFile(String fileName) {

		logger.info("Reading proportions file " + fileName);
		TableDataSet proportionsDataTable = null;

		try {
			CSVFileReader reader = new CSVFileReader();
			proportionsDataTable = reader.readFile(new File(fileName));
		} catch (IOException e) {
			e.printStackTrace();
			System.exit(1);
		}
        
        //read and store the column labels
        proportionTableLabels = proportionsDataTable.getColumnLabels();

        //store number of model groups
        numberOfGroups = proportionsDataTable.getColumnCount()-1;
        proportionsMap = new HashMap();
        maxIndex = -99999;
        minIndex = 99999;
        
        Float index = null;
        //set up the HashMap with the values in the TableDataSet
        for(int row=1;row<=proportionsDataTable.getRowCount();++row){
            
            index = new Float(proportionsDataTable.getValueAt(row,1));
            
            float[] proportions = new float[numberOfGroups];
            
            for(int c=2;c<=proportionsDataTable.getColumnCount();++c)
                proportions[c-2]=proportionsDataTable.getValueAt(row,c);
            
            proportionsMap.put(index,proportions);

            maxIndex = Math.max(maxIndex,index.floatValue());
            minIndex = Math.min(minIndex,index.floatValue());
         
            //determine decimal precision by casting to string and searching for decimal
            // gde 8.16.2006 calculate max precision across all rows, rather than just from last row.
            String indexString = index.toString();
            int currentPrecision = (int) Math.pow(10,(indexString.length()-indexString.indexOf(".")-1));
            if (currentPrecision > precision) precision = currentPrecision;            
        }
        
        logger.debug("Precision: "+precision);
        
		return proportionsMap;
	}

	/**
     *  This method applies the proportions model to data and updates
     * the data to include the resulting aggregate quantities distributed by group.
     * 
     * @return The original data TableDataSet with n (one for each category) columns appended.  The new columns
     * will be named according to the following convention: proportionFieldName_indexFieldName
     * 
	 */
	public TableDataSet runModel() {
        
        // make sure data file has been read
	    if(dataTable==null){
         logger.fatal("Please use readDataFile method to read in data file before running proportions model!");
         throw new RuntimeException();
        }
        
        // make sure proportions file has been read
        if(proportionsMap==null){
         logger.fatal("Please use readProportionFile method to read in data file before running proportions model!");
         throw new RuntimeException();
        }
        
		int rowCount = dataTable.getRowCount();
		float index = 0;
		float aggregateQuantity = 0;
		float allocatedQuantity = 0;

		//append columns to the dataTable for storage of aggregate quantities by proportional category
		//store index of those columns in allocatedColumnIndex[]
		int allocatedColumnIndex[] = new int[numberOfGroups];
        outputFieldNames = new String[numberOfGroups];
 		for (int proportionGroup = 0; proportionGroup < numberOfGroups; ++proportionGroup) {
			outputFieldNames[proportionGroup] = (proportionTableLabels[proportionGroup+1]+ "_" + aggregateQuantityField);
            dataTable.appendColumn(new float[rowCount], outputFieldNames[proportionGroup]);
			allocatedColumnIndex[proportionGroup] = dataTable.checkColumnPosition(outputFieldNames[proportionGroup]);
            logger.debug("Appending field "+ outputFieldNames[proportionGroup] + " to data table");
		}
        
        Float indexAsObject;
 		//iterate through rows in taz data, get income index, compute proportions by income
		//cross-multiply by households and save results in taz data
		for (int r = 1; r <= rowCount; r++) {
			index = dataTable.getValueAt(r, dataTableIndexField);
            
            //make sure indexes read from data file are within min and max of proportion file
            if (index < minIndex)
				index = (float) minIndex;
			if (index > maxIndex)
				index = maxIndex;
            
            //make sure index is in correct precision
            index = ((float) Math.round(index*precision)) / precision; 
            
            indexAsObject = new Float(index);
			//get aggregate quantity from data file
			aggregateQuantity = dataTable.getValueAt(r, aggregateQuantityPosition);

            //get proportions from model
            float[] proportions = (float[]) proportionsMap.get(indexAsObject);
            //allocate the aggregate quantity to each proportional group
			for (int s = 0; s < numberOfGroups; s++) {

                allocatedQuantity = proportions[s] * aggregateQuantity;
				//multiply proprtn by households and store in tazdata here
				dataTable.setValueAt(r, allocatedColumnIndex[s], allocatedQuantity);
				//some debug statements
				logger.debug("proportion["+s+"] :" + proportions[s]);

			}
		}
        return dataTable;
	}
    
    /**
     * 
     * @return The names of the fields created by the model.  
     */
    public String[] getOutputLabels() {
        return outputFieldNames; 
    }

    /**
     * 1) Creates a proportional model
     * 2) Reads proportions from file
     * 3) Reads taz data
     * 4) Runs model
     * 
     * @param args
     */
	public static void main(String[] args) {
        
        ProportionalAllocationModel incomeModel = new ProportionalAllocationModel();
        
        incomeModel.readProportionFile("c:\\projects\\pag\\application\\pb_model\\inputs\\idcurves.csv");
        
        incomeModel.readDataFile("c:\\projects\\pag\\application\\pb_model\\inputs\\tazdatarev.csv","HU","Inc_Index");
	
        incomeModel.runModel();
    }
}