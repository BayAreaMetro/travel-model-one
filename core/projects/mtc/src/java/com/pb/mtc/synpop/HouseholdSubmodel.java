/*
 * Copyright  2006 PB Consult Inc.
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
package com.pb.mtc.synpop;

import java.io.File;
import java.io.IOException;
import java.util.Hashtable;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataFileReader;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.model.ProportionalAllocationModel;
import com.pb.common.util.ResourceUtil;
import com.pb.common.datafile.DBFFileReader;

/**
 * This class applies household submodels to the San Francisco TAZ data.
 * It is needed to prepare the TAZ data for use by the population synthesizer.
 * 
 * @author Erhardt
 * @version 1.0 Oct 11, 2006
 *
 */
public class HouseholdSubmodel {


    protected static Logger logger = Logger.getLogger(HouseholdSubmodel.class);
    ResourceBundle rb;
        
    /**
     * Default constructor.   
     */
    public HouseholdSubmodel() {
        logger.info("Running household submodels.");
        rb = ResourceUtil.getResourceBundle("hhSubmodels");
    }

    /** 
     * Reads the zonal data file.  
     * 
     * @return The table data set read into memory.  
     */
    public TableDataSet readTableData(String rbProperty) {
        String fileName = new String(ResourceUtil.getProperty(rb, rbProperty));
        logger.info("Reading file " + fileName);
        
        TableDataSet data  = new TableDataSet();        
        try {
            TableDataFileReader reader;
            if (fileName.endsWith(".dbf") || fileName.endsWith(".DBF")) {
                reader = new DBFFileReader();
            } else {
                reader = new CSVFileReader();
            }
            data = reader.readFile(new File(fileName));
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        return data; 
    }
    
    /** 
     * Writes the zonal data file.  
     *
     * @param The table data set to write.  
     */
    public void writeTazData(TableDataSet tazData) {
        String fileName = new String(ResourceUtil.getProperty(rb, "tazdata.out.file"));
        logger.info("Writing file " + fileName);
        
        try {
            CSVFileWriter writer = new CSVFileWriter();
            writer.writeFile(tazData, new File(fileName));
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    /**
     * Appends the internal TAZ number for use with the population synthesizer.
     * 
     * @param tazData The taz data to work with.  Must contain SFTAZ.  
     * @return The same data with TAZ appended as the internal TAZ.  
     */
    public TableDataSet addInternalTaz(TableDataSet tazData) {
        logger.info("Adding internal TAZ number.");
        
        // create the lookup table
        TableDataSet tazIndexTable = readTableData("TAZIndexTable");
        int[] extTazIndex = tazIndexTable.getColumnAsInt("extTAZ");
        int[] intTazIndex = tazIndexTable.getColumnAsInt("intTAZ");
        Hashtable<Integer, Integer> tazIndex = new Hashtable<Integer, Integer>();
        for (int i=0; i<extTazIndex.length; i++) {
            tazIndex.put(new Integer(extTazIndex[i]), new Integer(intTazIndex[i]));
        }
        
        // determine the values of each internal taz to write
        int[] extTaz = tazData.getColumnAsInt("SFTAZ");
        int[] intTaz = new int[extTaz.length];
        for (int i=0; i<extTaz.length; i++) {
            intTaz[i] = tazIndex.get(new Integer(extTaz[i])).intValue();
        }
        
        // modify the table
        tazData.appendColumn(intTaz, "TAZ");
        
        return tazData; 
    }
    
    /**
     * Appends the external TAZ number for use with the population synthesizer.
     * 
     * @param tazData The taz data to work with.  Must contain SFTAZ.  
     * @return The same data with TAZ appended as the external TAZ.  
     */
    public TableDataSet addExternalTaz(TableDataSet tazData) {
        logger.info("Adding external TAZ number.");
        
        // determine the values of each internal taz to write
        int[] extTaz = tazData.getColumnAsInt("SFTAZ");
        
        // modify the table
        tazData.appendColumn(extTaz, "TAZ");
        
        return tazData; 
    }
    
    
    /** 
     * Converts from average household size to households by size.
     *
     * @param tazData The taz data to work with.  Must contain HHPOP and HHLDS.
     * @return The same taz data with fields appended.  
     */
    public TableDataSet runHHSizeModel(TableDataSet tazData) {
        logger.info("Running household size submodel.");
        
        // calculate the average HH size
        float[] avgHHSize = getAverageHHSize(tazData);
        tazData.appendColumn(avgHHSize, "AVGHHSIZE");
        float[] hhlds = tazData.getColumnAsFloat("HHLDS");
        
        // run the base model
        String curves = new String(ResourceUtil.getProperty(rb, "hhsizeLookup.file"));
        ProportionalAllocationModel model = new ProportionalAllocationModel(curves);
        model.setDataFile(tazData, "HHLDS", "AVGHHSIZE");
        tazData = model.runModel();
        
        // the model for SF zones
        TableDataSet sfTazData = new TableDataSet();
        sfTazData.appendColumn(hhlds, "HHLDS");
        sfTazData.appendColumn(avgHHSize, "AVGHHSIZE");
        
        String sfCurves = new String(ResourceUtil.getProperty(rb, "hhsizeLookup.sf.file"));
        ProportionalAllocationModel sfModel = new ProportionalAllocationModel(sfCurves);
        sfModel.setDataFile(sfTazData, "HHLDS", "AVGHHSIZE");
        sfTazData = sfModel.runModel();       
                
        // combine the results for the groups
        String[] resultColumns = model.getOutputLabels(); 
        tazData = combineResults(tazData, sfTazData, resultColumns);
        
        return tazData;
    }
    
    
    /**
     * Splits the total workers into GQ workers and HH workers.  
     * 
     * @param tazData TAz data with GQPOP and EMPRES
     * @return Modified table with number of GQ workers and non workers and HH workers
     */
    public TableDataSet runGQWorkerModel(TableDataSet tazData) {
        logger.info("Determining number of Group Quarters Workers");        

        TableDataSet baseGQ = readTableData("baseDistributions.file");

        float defaultGqWorkerShare = (float) ResourceUtil.getDoubleProperty(rb, "defaultGqWorkerShare");
        
        float[] baseGQWorkers    = baseGQ.getColumnAsFloat("GQWKRS");
        float[] baseGQNonWorkers = baseGQ.getColumnAsFloat("GQNONWKRS");         
        float[] gqPop      = tazData.getColumnAsFloat("GQPOP");
        
        float[] totWorkers   = tazData.getColumnAsFloat("EMPRES");
        float[] gqWorkers    = new float[totWorkers.length];
        float[] gqNonWorkers = new float[totWorkers.length]; 
        float[] hhWorkers    = new float[totWorkers.length];
        
        for (int i=0; i<gqPop.length; i++) {
            float gqWkrShare = defaultGqWorkerShare;
            if (baseGQWorkers[i] + baseGQNonWorkers[i] > 0) {
                gqWkrShare = baseGQWorkers[i] / (baseGQWorkers[i] + baseGQNonWorkers[i]);                
            }
            gqWorkers[i] = gqWkrShare * gqPop[i];
            if (gqWorkers[i] > totWorkers[i]) {
                gqWorkers[i] = totWorkers[i];
            }
            gqNonWorkers[i] = gqPop[i] - gqWorkers[i];
            hhWorkers[i] = totWorkers[i] - gqWorkers[i];            
        }
        
        tazData.appendColumn(gqNonWorkers, "GQNONWKRS");
        tazData.appendColumn(gqWorkers, "GQWKRS");
        tazData.appendColumn(hhWorkers, "HHWKRS");
                
        return tazData; 
    }
    
    /** 
     * Converts from average workers per HH to households by workers.
     *
     * @param tazData The taz data to work with.  Must contain EMPRES and HHLDS.
     * @return The same taz data with fields appended.  
     */
    public TableDataSet runWorkerModel(TableDataSet tazData) {
        logger.info("Running household size submodel.");
        
        // calculate the average HH size
        float[] avgWorkers = getAverageWorkers(tazData);
        tazData.appendColumn(avgWorkers, "AVGWORKERS");
        float[] hhlds = tazData.getColumnAsFloat("HHLDS");
        
        // run the base model
        String curvesFileName = new String(ResourceUtil.getProperty(rb, "hhworkersLookup.file"));
        ProportionalAllocationModel model = new ProportionalAllocationModel(curvesFileName);
        model.setDataFile(tazData,"HHLDS", "AVGWORKERS");
        tazData = model.runModel();
        
        // the model for SF zones
        TableDataSet sfTazData = new TableDataSet();
        sfTazData.appendColumn(hhlds, "HHLDS");
        sfTazData.appendColumn(avgWorkers, "AVGWORKERS");
        
        String sfCurves = new String(ResourceUtil.getProperty(rb, "hhworkersLookup.sf.file"));
        ProportionalAllocationModel sfModel = new ProportionalAllocationModel(sfCurves);
        sfModel.setDataFile(sfTazData, "HHLDS", "AVGWORKERS");
        sfTazData = sfModel.runModel();       
                
        // combine the results for the groups
        String[] resultColumns = model.getOutputLabels(); 
        tazData = combineResults(tazData, sfTazData, resultColumns);
        
        return tazData;
    }
        
    /**
     * Adjusts the households in each income category to match Census 2000 breakpoints.  
     * 
     * @param tazData The taz data to work with.  Must have fields specified in OldGroup.
     * @return The modified taz data, with fields added for NewGroup.  
     */
    public TableDataSet runIncomeInflationAdjustment(TableDataSet tazData) {
        logger.info("Running income inflation adjustments.");
        
        TableDataSet incomeConversion = readTableData("incomeInflation.file");
        
        for (int i=1; i <= incomeConversion.getRowCount(); i++) {
            // read the info for this conversion
            String oldGroup = incomeConversion.getStringValueAt(i, "OldGroup");
            String newGroup = incomeConversion.getStringValueAt(i, "NewGroup");
            float fractionOfOld = incomeConversion.getValueAt(i, "FractionOfOld");
            
            // if the new column does not exist, then add it
            if (tazData.getColumnPosition(newGroup) == -1) {
                float[] zeros = new float[tazData.getRowCount()];
                tazData.appendColumn(zeros, newGroup);
            } 
            
            // get the values for each taz
            float[] oldGroupValues = tazData.getColumnAsFloat(oldGroup);
            float[] newGroupValues = tazData.getColumnAsFloat(newGroup);
            
            // calculate the new households in each
            for (int j=0; j<oldGroupValues.length; j++) {
                newGroupValues[j] = newGroupValues[j] + fractionOfOld * oldGroupValues[j];
            }
            
            // fill in the table data set
            int position = tazData.checkColumnPosition(newGroup);
            tazData.setColumnAsFloat(position, newGroupValues);
        }
        
        return tazData; 
    }
    
    /**
     * Adjust the households with children, and with householders 65+ based on changes
     * in age cohorts.  
     * 
     * @param tazData Zonal data, must have new age cohorts and HHLDS
     * @return modified zonal data with added fields. 
     */
    public TableDataSet runHouseholdAgeSubmodel(TableDataSet tazData) {
        logger.info("Running household age submodels.");
        
        TableDataSet baseDistributions = readTableData("baseDistributions.file");
                
        float[] hage1kids0  = new float[tazData.getRowCount()];
        float[] hage1kids1  = new float[tazData.getRowCount()];
        float[] hage65kids0 = new float[tazData.getRowCount()];
        float[] hage65kids1 = new float[tazData.getRowCount()];
                
        for (int i=0; i<tazData.getRowCount(); i++) {
            
            // get the base distribution
            float baseTotal        = getTotalFromBase(baseDistributions, i+1);
            float hage1kids0share  = baseDistributions.getValueAt(i+1, "hage1kids0") / baseTotal;
            float hage1kids1share  = baseDistributions.getValueAt(i+1, "hage1kids1") / baseTotal;
            float hage65kids0share = baseDistributions.getValueAt(i+1, "hage65kids0") / baseTotal;
            float hage65kids1share = baseDistributions.getValueAt(i+1, "hage65kids1") / baseTotal;
            
            // get the targets
            float targetHage65pShare = getTargetHage65pShare(baseDistributions, tazData, i+1);
            float targetKidsShare    = getTargetKidsShare(baseDistributions, tazData, i+1);
            
            // IPF to get the individual shares
            float hageDiff = Math.abs(targetHage65pShare - (hage65kids0share + hage65kids1share));
            float kidsDiff = Math.abs(targetKidsShare - (hage1kids1share + hage65kids1share));
            float iter = 0; 
            while (hageDiff > 0.01 && kidsDiff > 0.01 && iter < 25) {
                // adjust for age
                float actualHage65pShare = hage65kids0share + hage65kids1share;
                hage1kids0share  = hage1kids0share * (1-targetHage65pShare) / (1-actualHage65pShare);
                hage1kids1share  = hage1kids1share * (1-targetHage65pShare) / (1-actualHage65pShare);
                hage65kids0share = hage65kids0share * targetHage65pShare / actualHage65pShare;
                hage65kids1share = hage65kids1share * targetHage65pShare / actualHage65pShare;                
                
                // adjust for kids
                float actualKidsShare = hage1kids1share + hage65kids1share;
                hage1kids0share  = hage1kids0share * (1-targetKidsShare) / (1-actualKidsShare); 
                hage1kids1share  = hage1kids1share * targetKidsShare / actualKidsShare; 
                hage65kids0share = hage65kids0share * (1-targetKidsShare) / (1-actualKidsShare); 
                hage65kids1share = hage65kids1share * targetKidsShare / actualKidsShare;   
                
                // look at differences
                hageDiff = Math.abs(targetHage65pShare - (hage65kids0share + hage65kids1share));
                kidsDiff = Math.abs(targetKidsShare - (hage1kids1share + hage65kids1share));                
            }
                
                
            // calculate the totals
            hage1kids0[i]  = hage1kids0share  * tazData.getValueAt(i+1, "HHLDS");
            hage1kids1[i]  = hage1kids1share  * tazData.getValueAt(i+1, "HHLDS");
            hage65kids0[i] = hage65kids0share * tazData.getValueAt(i+1, "HHLDS");
            hage65kids1[i] = hage65kids1share * tazData.getValueAt(i+1, "HHLDS");              
        }
        
        // add the columns
        tazData.appendColumn(hage1kids0, "HAGE1KIDS0");
        tazData.appendColumn(hage1kids1, "HAGE1KIDS1");
        tazData.appendColumn(hage65kids0, "HAGE65KIDS0");
        tazData.appendColumn(hage65kids1, "HAGE65KIDS1");
        
        return tazData;
    }
    
    public TableDataSet runGQAgeSubmodel(TableDataSet tazData) {
        logger.info("Running group quarters age submodels.");
        
        TableDataSet baseDistributions = readTableData("baseDistributions.file");
                
        float[] gqPop    = tazData.getColumnAsFloat("GQPOP");
        float[] gqAge064 = new float[tazData.getRowCount()];
        float[] gqAge65p = new float[tazData.getRowCount()];
                
        float defaultGqAge65pShare = (float) ResourceUtil.getDoubleProperty(rb, "defaultGqAge65pShare");
        
        for (int i=0; i<tazData.getRowCount(); i++) {
            
            // get the base distribution for GQ
            float baseGqAge064 = baseDistributions.getValueAt(i+1, "GQAGE064");
            float baseGqAge65p = baseDistributions.getValueAt(i+1, "GQAGE65P");
            float baseGqAge65pShare = defaultGqAge65pShare;
            if (baseGqAge064 + baseGqAge65p > 0) {
                baseGqAge65pShare = baseGqAge65p / (baseGqAge064 + baseGqAge65p);                
            }
            
            // get the age 65+ share for the entire population
            float baseAge65pShare   = getAge65pShare(baseDistributions, i+1);
            float targetAge65pShare = getAge65pShare(tazData, i+1);
            
            // calculate the target shares
            float gqAge65pShare = baseGqAge65pShare;
            if (baseAge65pShare > 0) {
                gqAge65pShare = baseGqAge65pShare * (targetAge65pShare / baseAge65pShare);                
            }          
            float gqAge064Share = 1 - baseGqAge65pShare; 
            
            // and the trips
            gqAge064[i] = gqAge064Share * gqPop[i]; 
            gqAge65p[i] = gqAge65pShare * gqPop[i];                
        }
        
        // add the columns
        tazData.appendColumn(gqAge064, "GQAGE064");
        tazData.appendColumn(gqAge65p, "GQAGE65P");
    
        return tazData;
    }
    
    
    private TableDataSet combineResults(TableDataSet tazData,
            TableDataSet sfTazData, String[] columns) {

        int sfCountyID = ResourceUtil.getIntegerProperty(rb, "sfCountyID");
        for (int row=1; row<=tazData.getRowCount(); row++) {
            int county = (int) tazData.getValueAt(row, "COUNTY");
            if (county == sfCountyID) {
                for (int col=0; col<columns.length; col++) {
                    float sfValue = sfTazData.getValueAt(row, columns[col]);
                    tazData.setValueAt(row, columns[col], sfValue);
                }
            }
        }
        
        return tazData; 
    }

    /**
     * Calculates the average HH size for each TAZ.  
     * 
     * @param tazData The TAZ data set.  
     * @return An array with the average HH size for each TAZ.
     */
    private float[] getAverageHHSize(TableDataSet tazData) {
        float[] hhpop = tazData.getColumnAsFloat("HHPOP");
        float[] hh    = tazData.getColumnAsFloat("HHLDS");
        float[] avgHHSize = new float[hhpop.length];
        for (int i=0; i<hhpop.length; i++) {
            if (hh[i] > 0) {
                avgHHSize[i] = hhpop[i] / hh[i];                
            }
            else {
                avgHHSize[i] = 0; 
            }
        }
        return avgHHSize; 
    }
    
    /**
     * Calculates the average workers per household for each TAZ.  
     * 
     * @param tazData The TAZ data set.  
     * @return An array with the average workers per household for each TAZ.
     */
    private float[] getAverageWorkers(TableDataSet tazData) {

        float[] workers = tazData.getColumnAsFloat("HHWKRS");
        float[] hh    = tazData.getColumnAsFloat("HHLDS");
        float[] avgWorkers = new float[workers.length];
        for (int i=0; i<workers.length; i++) {
            if (hh[i] > 0) {
                avgWorkers[i] = workers[i] / hh[i];                
            }
            else {
                avgWorkers[i] = 0; 
            }
        }
        
        return avgWorkers; 
    }
    
    /**
     * 
     * @param table Table data set containing age cohort fields
     * @param row   The row of interest
     * @return      The share of the population age 65+
     */
    private float getAge65pShare(TableDataSet table, int row) {

        float age0004 = table.getValueAt(row, "AGE0004");
        float age0519 = table.getValueAt(row, "AGE0519");
        float age2044 = table.getValueAt(row, "AGE2044");
        float age4564 = table.getValueAt(row, "AGE4564");
        float age65p  = table.getValueAt(row, "AGE65P");
        
        float total = age0004+age0519+age2044+age4564+age65p;        
        float share = 0;
        if (total > 0) share = age65p / total;
        
        return share;
    }
    
    /**
     * 
     * @param table Table data set containing age cohort fields
     * @param row   The row of interest
     * @return      The share of the population age 0-19
     */
    private float getAge0019Share(TableDataSet table, int row) {

        float age0004 = table.getValueAt(row, "AGE0004");
        float age0519 = table.getValueAt(row, "AGE0519");
        float age2044 = table.getValueAt(row, "AGE2044");
        float age4564 = table.getValueAt(row, "AGE4564");
        float age65p  = table.getValueAt(row, "AGE65P");
        
        float total = age0004+age0519+age2044+age4564+age65p;        
        float share = 0; 
        if (total > 0) share = (age0004+age0519) / total;
        
        return share;
    }
    
    /**
     * 
     * @param table Table data set containing household type
     * @param row   The row of interest
     * @return      The share of households with kids
     */
    private float getKidsShare(TableDataSet table, int row) {
        
        float hage1kids0 = table.getValueAt(row, "hage1kids0");
        float hage1kids1 = table.getValueAt(row, "hage1kids1");
        float hage65kids0 = table.getValueAt(row, "hage65kids0");
        float hage65kids1 = table.getValueAt(row, "hage65kids1");
        
        float total = hage1kids0+hage1kids1+hage65kids0+hage65kids1;        
        float share = 0; 
        if (total > 0) share = (hage1kids1+hage65kids1) / total;
        
        return share;
    }
    
    /**
     * 
     * @param table Table data set containing household type
     * @param row   The row of interest
     * @return      The share of households with householder age 65+
     */
    private float getHage65pShare(TableDataSet table, int row) {
        
        float hage1kids0 = table.getValueAt(row, "hage1kids0");
        float hage1kids1 = table.getValueAt(row, "hage1kids1");
        float hage65kids0 = table.getValueAt(row, "hage65kids0");
        float hage65kids1 = table.getValueAt(row, "hage65kids1");
        
        float total = hage1kids0+hage1kids1+hage65kids0+hage65kids1;        
        float share = 0; 
        if (total > 0) share = (hage65kids0+hage65kids1) / total;
        
        return share;
    }
    
    /**
     * 
     * @param table Table data set containing household type
     * @param row   The row of interest
     * @return      The total households for all categories. 
     */
    private float getTotalFromBase(TableDataSet table, int row) {
        
        float hage1kids0 = table.getValueAt(row, "hage1kids0");
        float hage1kids1 = table.getValueAt(row, "hage1kids1");
        float hage65kids0 = table.getValueAt(row, "hage65kids0");
        float hage65kids1 = table.getValueAt(row, "hage65kids1");
        
        float total = hage1kids0+hage1kids1+hage65kids0+hage65kids1;   
        
        return total;
    }
    
    /**
     * 
     * @param base   Table data set with base distributions.  
     * @param target Table data set wtih future distributions.  
     * @param row    Row of interest.  
     * @return       The targeted share of households with age 65+ householder.  
     */
    private float getTargetHage65pShare(TableDataSet base, TableDataSet target, int row) {
        
        float baseAge65pShare    = getAge65pShare(base, row);
        float targetAge65pShare  = getAge65pShare(target, row); 
        float baseHage65pShare   = getHage65pShare(base, row);
        
        // if we're starting from zero, double the share
        if (baseAge65pShare == 0) {
            baseAge65pShare = targetAge65pShare / 2; 
        }
        
        float targetHage65pShare = 0;
        if (targetAge65pShare > 0) {
            targetHage65pShare = (targetAge65pShare / baseAge65pShare) * baseHage65pShare;            
        }
        
        return targetHage65pShare;
    }
    
    /**
     * 
     * @param base   Table data set with base distributions.  
     * @param target Table data set wtih future distributions.  
     * @param row    Row of interest.  
     * @return       The targeted share of households with kids.  
     */
    private float getTargetKidsShare(TableDataSet base, TableDataSet target, int row) {
        
        float baseAge0019Share    = getAge0019Share(base, row);
        float targetAge0019Share = getAge0019Share(target, row); 
        float baseKidsShare       = getKidsShare(base, row);
        
        // if we're starting from zero, double the share
        if (baseAge0019Share == 0) {
            baseAge0019Share = targetAge0019Share / 2; 
        }
        
        float targetKidsShare = 0;
        if (targetAge0019Share > 0) {
            targetKidsShare = (targetAge0019Share / baseAge0019Share) * baseKidsShare;            
        }
        
        return targetKidsShare;
    }
    
    
    /**
     * Runs the SF Household submodels, including:
     *  1.  Convert average HH size to households by size.
     *  2.  Convert average HH workers to households by workers.
     *  3.  Adjust income groups to match 2000 Census categories.
     */
    public static void main(String[] args) {
        HouseholdSubmodel submodel = new HouseholdSubmodel();
        TableDataSet tazData = submodel.readTableData("tazdata.file");
        tazData = submodel.runHHSizeModel(tazData);
        tazData = submodel.runGQWorkerModel(tazData);
        tazData = submodel.runWorkerModel(tazData);
        tazData = submodel.runIncomeInflationAdjustment(tazData);
        tazData = submodel.runHouseholdAgeSubmodel(tazData);
        tazData = submodel.runGQAgeSubmodel(tazData);
        tazData = submodel.addExternalTaz(tazData);
        
        submodel.writeTazData(tazData);
        logger.info("Finished with HH submodels!\n");
    }

}
