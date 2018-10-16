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
package com.pb.common.calculator;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.util.ArrayList;

/**
 * Manages instances of TableDataSet. Ensures that there is only one copy of a given
 * TableDataSet in memory.
 *
 */
public class TableDataSetManager implements Serializable {

    protected transient Logger logger = Logger.getLogger("com.pb.common.calculator");

    private static TableDataSetManager instance = new TableDataSetManager();

    //Holds list of table data sets read into memory
    private ArrayList tableEntryList = new ArrayList();

    //Array of column names
    //Initialize to zero incase there are no entries in control file
    private String[] zoneColumnName = new String[0];
    private String[] hhColumnName = new String[0];

    private TableDataSet zoneTableData = new TableDataSet();  //Zone data
    private TableDataSet hhTableData = null;                  //Household data


    private TableDataSetManager() {

    }

    /** Returns an instance to the singleton.
     */
    public static TableDataSetManager getInstance() {
        return instance;
    }


    /** Unloads the data that is being stored in memory so heap can be
     * reclaimed by the garbage collector.
     */
	synchronized public void clearData() {
        tableEntryList.clear();

        zoneColumnName = new String[0];
        hhColumnName = new String[0];

        zoneTableData = new TableDataSet();
        hhTableData = null;
    }


	synchronized public void addTableEntries(DataEntry[] tableEntries) {

        readZoneData(tableEntries);
        readHouseholdData(tableEntries);
    }


    /*
     * Read zone data.
     */
    private void readZoneData(DataEntry[] tableEntries) {

        long startTime, endTime;
        String fileName = null;

        startTime = System.currentTimeMillis();

        for (int i = 0; i < tableEntries.length; i++) {

            if (tableEntries[i].type.toUpperCase().startsWith("Z")) {

                //Skip table if already loaded
                if (isTableLoaded(tableEntries[i])) {
                    logger.debug("table name=" + tableEntries[i].fileName + " (" + tableEntries[i].type + ") " + " is already loaded - skipping");
                    continue;
                }

                try {
                    fileName = tableEntries[i].fileName;
                    
                    CSVFileReader reader = new CSVFileReader();
                    TableDataSet tempTable = reader.readFile(new File(fileName));

                    //add columns to zoneTableData
                    for (int c=1; c <= tempTable.getColumnCount(); c++) {

                        float[] columnData = tempTable.getColumnAsFloat(c);
                        String columnLabel = tempTable.getColumnLabel(c);

                        //check if column label has already been added to zoneTableData
                        int columnPosition = zoneTableData.getColumnPosition(columnLabel);

                        //column label does not exist
                        if (columnPosition < 0) {
                            zoneTableData.appendColumn(columnData, columnLabel);
                        } else {
                            logger.debug("table name=" + tableEntries[i].fileName + ", column name=" +
                                            columnLabel + " is already loaded - skipping column");
                        }
                    }

                    //Add table entry to list of tables read
                    tableEntryList.add(tableEntries[i]);

                    //Print column names
                    if (logger.isDebugEnabled()) {
                        logger.debug("table name=" + tableEntries[i].fileName + " (" + tableEntries[i].type + ")" );

                        StringBuffer sb = new StringBuffer(256);
                        sb.append("Column names= ");
                        String[] columnLabels = tempTable.getColumnLabels();

                        for (int j = 0; j < columnLabels.length; j++) {
                            sb.append(columnLabels[j] + ", ");
                        }
                        logger.debug(sb.toString());
                    }

                } catch (IOException e) {
                    e.printStackTrace();
                    System.exit(1);
                }
                endTime = System.currentTimeMillis();
                logger.info("Read " + fileName + " : " + (endTime - startTime) + " ms");

                //Zone tables are ready and combined - now index them and get a list of column names
                zoneTableData.buildIndex(1);
                zoneColumnName = zoneTableData.getColumnLabels();

            }

        }

    }

    /*
     * Read household data.
     */
    private void readHouseholdData(DataEntry[] tableEntries) {

        long startTime, endTime;
        String fileName = null;

        startTime = System.currentTimeMillis();
        
        for (int i = 0; i < tableEntries.length; i++) {

            if (tableEntries[i].type.toUpperCase().startsWith("H")) {

                //If table is already loaded re-read the column headers (in case any columns have been appended since
                // the last read and then skip the read
                if (isTableLoaded(tableEntries[i])) {
                    hhColumnName = hhTableData.getColumnLabels();
                    if(logger.isDebugEnabled()){
                        logger.debug("adding table name=" + tableEntries[i].type + ", " +
                            tableEntries[i].fileName + " is already loaded");
                        StringBuffer sb = new StringBuffer(256);
                        sb.append("Household data columns: ");
                        for (int j = 0; j < hhColumnName.length; j++) {
                            sb.append(hhColumnName[j] + ", ");
                        }
                    }
                    continue;
                }

                try {
                    fileName = tableEntries[i].fileName;
                    
                    CSVFileReader reader = new CSVFileReader();
                    hhTableData = reader.readFile(new File(fileName));
                    
                    hhTableData.buildIndex(1);
                    hhColumnName = hhTableData.getColumnLabels();

                    //Add table entry to list of tables read
                    tableEntryList.add(tableEntries[i]);

                    //Print column names
                    if (logger.isDebugEnabled()) {
                        StringBuffer sb = new StringBuffer(256);
                        sb.append("Household data columns: ");
                        for (int j = 0; j < hhColumnName.length; j++) {
                            sb.append(hhColumnName[j] + ", ");
                        }
                        logger.debug(sb.toString());
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                    System.exit(1);
                }
                endTime = System.currentTimeMillis();
                logger.info("Read " + fileName + " : " + (endTime - startTime) + " ms");

                break;  //read the first file only
            }
        }

    }


    /**
     * Checks to see if a table data set has been loaded already.
     * Combine table name + file name and test for uniqueness.
     */
    private boolean isTableLoaded(DataEntry entry) {

        for (int i = 0; i < tableEntryList.size(); i++) {
            DataEntry tableEntry = (DataEntry) tableEntryList.get(i);

            String loadedName = tableEntry.type + tableEntry.fileName;
            String newName = entry.type + entry.fileName;

            if (loadedName.equalsIgnoreCase(newName)) {
                return true;
            }
        }

        return false;
    }


    synchronized public int findZoneIndex(String variableName) {

        int index = -1;

        for (int i = 0; i < zoneColumnName.length; i++) {
            if (zoneColumnName[i].equalsIgnoreCase(variableName)) {
                index = i + 1;   //TableDataSet set is 1 based
                break;
            }
        }

        return index;
    }


	synchronized public int findHouseholdIndex(String variableName) {

        int index = -1;

        for (int i = 0; i < hhColumnName.length; i++) {
            if (hhColumnName[i].equalsIgnoreCase(variableName)) {
                index = i + 1;   //TableDataSet set is 1 based
                break;
            }
        }

        return index;
    }


    public double getZoneValueForIndex(int zoneIndex, int valueIndex) {
        return zoneTableData.getIndexedValueAt(zoneIndex, valueIndex);
    }


    public double getHouseholdValueForIndex(int hhIndex, int valueIndex) {
        return hhTableData.getIndexedValueAt(hhIndex, valueIndex);
    }


    public int getNumberOfZones() {
        int numZones = 0;

        if (zoneTableData != null)
            numZones = zoneTableData.getRowCount();

        return numZones;
    }


	synchronized public TableDataSet getZoneData() {
        return zoneTableData;
    }

	synchronized public TableDataSet getHouseholdData() {
        return hhTableData;
    }

    /**
     * Log the zone data values for a given taz
     * 
     * @param taz
     */
    public void logZoneTableValues(int taz){
    	logZoneTableValues(logger, taz); 
    }
    

    /**
     * Log the zone data values for a given taz
     * 
     * @param localLogger - the logger to send the results to
     * @param taz
     */
    public void logZoneTableValues(Logger localLogger, int taz){
        if(zoneTableData == null || zoneTableData.getRowCount() == 0)
            return;
        
        localLogger.info("");
        localLogger.info("Zone data values for taz "+taz);
        localLogger.info("");
        for(int i=1;i<=zoneTableData.getColumnCount();++i){
            String columnName = zoneTableData.getColumnLabel(i);
            float value = (float)getZoneValueForIndex(taz, i);
            localLogger.info(columnName+" : "+value);
        }
        localLogger.info(""); 
    }
}
