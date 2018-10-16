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
package com.pb.common.calculator2;

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

    private ArrayList tableEntryList = new ArrayList();      //List of DataEntry objects, one for each TableDataSet
    private ArrayList listOfTableDataSet = new ArrayList();  //List of TableDataSets objects, one for each file


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
        listOfTableDataSet.clear();
    }


    /*
     * Read zone data.
     */
    public synchronized void readTableData(DataEntry[] tableEntries) {

        long startTime, endTime;
        String fileName = null;

        startTime = System.currentTimeMillis();

        for (int i = 0; i < tableEntries.length; i++) {

            //Skip table if already loaded
            if (isTableLoaded(tableEntries[i])) {
                logger.debug("Table already loaded, skipping: " + tableEntries[i].fileName);
                continue;
            }

            try {
                fileName = tableEntries[i].fileName;

                CSVFileReader reader = new CSVFileReader();
                TableDataSet tempTable = reader.readFile(new File(fileName));

                //Build index on first column for zone datasets - can't do this for household datasets
                if (tableEntries[i].type.toUpperCase().startsWith("Z")) {
                    tempTable.buildIndex(1);
                }
                
                listOfTableDataSet.add(tempTable);   //Add to list of TableDataSets read so far

                tableEntryList.add(tableEntries[i]); //Add table entry to list of tables read

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


    synchronized public TableDataIndex getTableDataIndex(String variableName) {

        TableDataIndex index = null;

        for (int i=0; i < listOfTableDataSet.size(); i++) {
            TableDataSet tempDataSet = (TableDataSet) listOfTableDataSet.get(i);
            int columnPosition = tempDataSet.getColumnPosition(variableName);

            //Return index of 1) position of TableDataSet in list and 2) column position
            //in TableDataSet
            if (columnPosition >= 0) {
                index = new TableDataIndex(i, columnPosition);
                return index;
            }
        }

        return index;  //Should never reach this statement but compiler requires it!
    }


    public double getValueForIndex(int valueIndex, TableDataIndex index) {
        TableDataSet tempDataSet = (TableDataSet) listOfTableDataSet.get(index.positionInList);
        return tempDataSet.getValueAt(valueIndex, index.columnPosition);
    }


	synchronized public ArrayList getListOfTableDataSet() {
        return listOfTableDataSet;
    }

}
