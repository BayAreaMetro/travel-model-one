/*
 * Created on 13-Oct-2005
 *
 * Copyright  2005 JE Abraham and others
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
package com.pb.common.datafile;

import java.io.File;
import java.util.Iterator;
import java.util.TreeSet;

public class TableDataSetCrosstabber {

    
    
    public TableDataSetCrosstabber() {
        super();
    }
    
    public static void main(String args[]) {
        if (args.length!=5) {
            System.out.println("usage: java com.pb.common.datafile.TableDataSetCrosstabber directory table rows columns, values");
            System.exit(1);
        }
        CSVFileReader myReader= new CSVFileReader();
        myReader.setMyDirectory(new File(args[0]));
        CSVFileWriter myWriter = new CSVFileWriter();
        myWriter.setMyDecimalFormat(new GeneralDecimalFormat("0.#########E0",10000000,.001));
        myWriter.setMyDirectory(new File(args[0]));
        TableDataSetCollection myCollection = new TableDataSetCollection(myReader,myWriter);
        TableDataSet results = crossTabDataset(myCollection,args[1],args[2],args[3],args[4]);
        results.setName(args[1]+"_"+args[2]+args[3]+"_"+args[4]+"_crossTab");
        myCollection.addTableDataSet(results);
        myCollection.flush();
    }

// this will be the new way to avoid code duplication
//    public static TableDataSet crossTabDataset(TableDataSetCollection aCollection, String inputTableName, String rowColumnName, String columnColumnName, String valuesColumnName) {
//        String[] rowNames = new String[1];
//        rowNames[0] = rowColumnName;
//        return crossTabDataset(aCollection, inputTableName, rowNames, columnColumnName, valuesColumnName);
//    }
    
// this is the method that should be able to handle multiple row headers
    // TODO test this
    public static TableDataSet crossTabDataset(TableDataSetCollection aCollection, String inputTableName, String[] rowColumnNames, String columnColumnName, String valuesColumnName) {
        // preliminaries
        TableDataSet inputTable = aCollection.getTableDataSet(inputTableName);
        int[] columnTypes = inputTable.getColumnType();
        TableDataSet out = new TableDataSet();
        
        // set up rows
        TreeSet[] rowHeaders = new TreeSet[rowColumnNames.length];
        int totalOutputRows = 1;
        for (int rowColumnId=0;rowColumnId < rowColumnNames.length;rowColumnId++) {
            int forRows = inputTable.checkColumnPosition(rowColumnNames[rowColumnId]);
            rowHeaders[rowColumnId] = new TreeSet();
            if (columnTypes[forRows-1]==TableDataSet.STRING) {
                String[] rowColumn = inputTable.getColumnAsString(forRows);
                for (int i=0;i<rowColumn.length;i++) {
                    rowHeaders[rowColumnId].add(rowColumn[i]);
                }
            } else {
                int[] rowColumn = inputTable.getColumnAsInt(forRows);
                for (int i=0;i<rowColumn.length;i++) {
                    rowHeaders[rowColumnId].add(new Integer(rowColumn[i]));
                }
            }
            totalOutputRows *= rowHeaders[rowColumnId].size();
        }
        for (int rowColumnId=0;rowColumnId < rowColumnNames.length;rowColumnId++) {
            int forRows = inputTable.checkColumnPosition(rowColumnNames[rowColumnId]);
            if (columnTypes[forRows-1]==TableDataSet.STRING) {
                out.appendColumn(new String[totalOutputRows],rowColumnNames[rowColumnId]);
            } else {
                out.appendColumn(new int[totalOutputRows],rowColumnNames[rowColumnId]);
            }
        }
        

        // set up columns
        int forColumns = inputTable.checkColumnPosition(columnColumnName);
        TreeSet columnHeaders = new TreeSet();
        if (columnTypes[forColumns-1]==TableDataSet.STRING) {
            String[] columnColumn = inputTable.getColumnAsString(forColumns);
            for (int i=0;i<columnColumn.length;i++) {
                columnHeaders.add(columnColumn[i]);
            }
        } else {
            int[] columnColumn = inputTable.getColumnAsInt(forColumns);
            for (int i=0;i<columnColumn.length;i++) {
                columnHeaders.add(new Integer(columnColumn[i]));
            }
        }

        // set up values
        int forValues = inputTable.checkColumnPosition(valuesColumnName);
        
        // now populate row headers
        Iterator[] rowIterators = new Iterator[rowColumnNames.length];
        Object[] currentNames = new Object[rowColumnNames.length];
        int rowNumber = 1;
        for (int rowColumnId=0;rowColumnId < rowColumnNames.length;rowColumnId++) {
            rowIterators[rowColumnId] = rowHeaders[rowColumnId].iterator();
        }
        boolean done = false;
        int rowNameColumnNumber = 0;
        while (!done) {
            if (rowIterators[rowNameColumnNumber].hasNext()) {
                currentNames[rowNameColumnNumber] = rowIterators[rowNameColumnNumber].next();
                if (currentNames[rowNameColumnNumber] instanceof String) {
                    out.setStringValueAt(rowNumber,rowNameColumnNumber+1,(String) currentNames[rowNameColumnNumber]);
                } else {
                    out.setValueAt(rowNumber,rowNameColumnNumber+1,((Integer) currentNames[rowNameColumnNumber]).intValue());
                }
                if (rowNameColumnNumber == rowColumnNames.length-1) {
                    // at last row
                    rowNumber++;
                } else {
                    rowNameColumnNumber++;
                }
            } else {
                if (rowNameColumnNumber ==0) done = true;
                else rowIterators[rowNameColumnNumber]= rowHeaders[rowNameColumnNumber].iterator();
                rowNameColumnNumber--;
            }
        }
        
        // now set up the indices output table
        int[] rowIndicesForTableDataSet= new int[rowColumnNames.length];
        int columnIndexForTableDataSet=0;
        String[] stringHeaders;
        int numStringHeaders = 0;
        String[] intHeaders;
        int numIntHeaders = 0;
        String[][] stringValues;
        int[][] intValues;
        
        // figure out sizes
        for (int rowColumnId=0;rowColumnId < rowColumnNames.length;rowColumnId++) {
            int forRows = inputTable.checkColumnPosition(rowColumnNames[rowColumnId]);
            if (columnTypes[forRows-1] == TableDataSet.STRING) {
                rowIndicesForTableDataSet[rowColumnId]= numStringHeaders;
                numStringHeaders++;
            }
            else {
                rowIndicesForTableDataSet[rowColumnId] = numIntHeaders;
                numIntHeaders++;
            }
        }
        if (columnTypes[forColumns-1] == TableDataSet.STRING) {
            columnIndexForTableDataSet = numStringHeaders;
            numStringHeaders++;
        }
        else {
            columnIndexForTableDataSet = numIntHeaders;
            numIntHeaders++;
        }
        
        stringHeaders = new String[numStringHeaders];
        stringValues = new String[1][numStringHeaders];
        intHeaders = new String[numIntHeaders];
        intValues = new int[1][numIntHeaders];
        
        // put in header values
        for (int rowColumnId=0;rowColumnId < rowColumnNames.length;rowColumnId++) {
            int forRows = inputTable.checkColumnPosition(rowColumnNames[rowColumnId]);
            if (columnTypes[forRows-1] == TableDataSet.STRING) {
                stringHeaders[rowIndicesForTableDataSet[rowColumnId]]=rowColumnNames[rowColumnId];
            }
            else {
                intHeaders[rowIndicesForTableDataSet[rowColumnId]] = rowColumnNames[rowColumnId];
            }
        }
        if (columnTypes[forColumns-1] == TableDataSet.STRING) {
            stringHeaders[columnIndexForTableDataSet] = columnColumnName;
        }
        else {
            intHeaders[columnIndexForTableDataSet] = columnColumnName;
        }
        
// TODO delete all this
//        if (columnTypes[forColumns-1]== TableDataSet.STRING && columnTypes[forRows-1]== TableDataSet.STRING) {
//            stringHeaders = new String[2];
//            stringHeaders[0] = rowColumnName;
//            stringHeaders[1] = columnColumnName;
//            columnIndexForTableDataSet = 1;
//            intHeaders = new String[0];
//            intValues = new int[1][0];
//            stringValues = new String[1][2];
//        } else if (columnTypes[forColumns-1]== TableDataSet.STRING) {
//            stringHeaders = new String[1];
//            stringHeaders[0] = columnColumnName;
//            intHeaders = new String[1];
//            intHeaders[0] = rowColumnName;
//            intValues = new int[1][1];
//            stringValues = new String[1][1];
//        } else if (columnTypes[forRows-1]== TableDataSet.STRING) {
//            stringHeaders = new String[1];
//            stringHeaders[0] = rowColumnName;
//            intHeaders = new String[1];
//            intHeaders[0] = columnColumnName;
//            intValues = new int[1][1];
//            stringValues = new String[1][1];
//        } else {
//            stringHeaders = new String[0];
//            intHeaders = new String[2];
//            intHeaders[0] = rowColumnName;
//            intHeaders[1] = columnColumnName;
//            columnIndexForTableDataSet = 1;
//            intValues = new int[1][2];
//            stringValues = new String[1][0];
//        }
//

        // now we go through and let TableDataSetIndexedValue do all the work of summing
        Iterator columnIterator = columnHeaders.iterator();
        int columnNumber = 2;
        Iterator[] rowIterator = new Iterator[rowColumnNames.length];
        while (columnIterator.hasNext()) {
            Object column = columnIterator.next();
            String columnHeader = null;
            if (column instanceof String) {
                columnHeader = (String) column;
                stringValues[0][columnIndexForTableDataSet]=columnHeader;
            }
            else {
                columnHeader = ((Integer) column).toString();
                intValues[0][columnIndexForTableDataSet]=((Integer) column).intValue();
            }
            
            float[] values = new float[totalOutputRows];
            TableDataSetIndexedValue tdsiv = new TableDataSetIndexedValue(inputTableName,stringHeaders,intHeaders,stringValues,intValues,valuesColumnName);
            tdsiv.setValueMode(TableDataSetIndexedValue.SUM_MODE);
            rowNumber = 0;
            while (!done) {
                if (rowIterators[rowNameColumnNumber].hasNext()) {
                    Object row = rowIterators[rowNameColumnNumber].next();
                    if (row instanceof String) {
                        stringValues[0][rowIndicesForTableDataSet[rowNameColumnNumber]] = (String) row;
                    } else {
                        intValues[0][rowIndicesForTableDataSet[rowNameColumnNumber]] = ((Integer) row).intValue();
                    }
                    if (rowNameColumnNumber == rowColumnNames.length-1) {
                        // at last row
                        tdsiv.setIntValues(intValues);
                        tdsiv.setStringValues(stringValues);
                        values[rowNumber] = tdsiv.retrieveValue(aCollection);
                        rowNumber++;
                    } else {
                        rowNameColumnNumber++;
                    }
                } else {
                    if (rowNameColumnNumber ==0) done = true;
                    else rowIterators[rowNameColumnNumber]= rowHeaders[rowNameColumnNumber].iterator();
                    rowNameColumnNumber--;
                }
            }
            out.appendColumn(values,columnHeader);
        }
        
        return out;
        
    }
    
// this is the old way that works
    public static TableDataSet crossTabDataset(TableDataSetCollection aCollection, String inputTableName, String rowColumnName, String columnColumnName, String valuesColumnName) {
        TableDataSet inputTable = aCollection.getTableDataSet(inputTableName);
        int[] columnTypes = inputTable.getColumnType();
        int forRows = inputTable.checkColumnPosition(rowColumnName);
        TreeSet rowHeaders = new TreeSet();
        int forColumns = inputTable.checkColumnPosition(columnColumnName);
        TreeSet columnHeaders = new TreeSet();
        int forValues = inputTable.checkColumnPosition(valuesColumnName);
        if (columnTypes[forRows-1]==TableDataSet.STRING) {
            String[] rowColumn = inputTable.getColumnAsString(forRows);
            for (int i=0;i<rowColumn.length;i++) {
                rowHeaders.add(rowColumn[i]);
            }
        } else {
            int[] rowColumn = inputTable.getColumnAsInt(forRows);
            for (int i=0;i<rowColumn.length;i++) {
                rowHeaders.add(new Integer(rowColumn[i]));
            }
        }
        if (columnTypes[forColumns-1]==TableDataSet.STRING) {
            String[] columnColumn = inputTable.getColumnAsString(forColumns);
            for (int i=0;i<columnColumn.length;i++) {
                columnHeaders.add(columnColumn[i]);
            }
        } else {
            int[] columnColumn = inputTable.getColumnAsInt(forColumns);
            for (int i=0;i<columnColumn.length;i++) {
                columnHeaders.add(new Integer(columnColumn[i]));
            }
        }
        
        TableDataSet out = new TableDataSet();
        if (columnTypes[forRows-1]==TableDataSet.STRING) {
            out.appendColumn(new String[rowHeaders.size()],rowColumnName);
        } else {
            out.appendColumn(new int[rowHeaders.size()],rowColumnName);
        }
        
        Iterator rowIterator = rowHeaders.iterator();
        int rowNumber = 1;
        while (rowIterator.hasNext()) {
            Object row = rowIterator.next();
            if (row instanceof String) {
                out.setStringValueAt(rowNumber,1,(String) row);
            } else {
                out.setValueAt(rowNumber,1,((Integer) row).intValue());
            }
            rowNumber++;
        }
        
        String[] stringHeaders;
        String[] intHeaders;
        String[][] stringValues;
        int[][] intValues;
        int rowIndexForTableDataSet=0;
        int columnIndexForTableDataSet=0;
        if (columnTypes[forColumns-1]== TableDataSet.STRING && columnTypes[forRows-1]== TableDataSet.STRING) {
            stringHeaders = new String[2];
            stringHeaders[0] = rowColumnName;
            stringHeaders[1] = columnColumnName;
            columnIndexForTableDataSet = 1;
            intHeaders = new String[0];
            intValues = new int[1][0];
            stringValues = new String[1][2];
        } else if (columnTypes[forColumns-1]== TableDataSet.STRING) {
            stringHeaders = new String[1];
            stringHeaders[0] = columnColumnName;
            intHeaders = new String[1];
            intHeaders[0] = rowColumnName;
            intValues = new int[1][1];
            stringValues = new String[1][1];
        } else if (columnTypes[forRows-1]== TableDataSet.STRING) {
            stringHeaders = new String[1];
            stringHeaders[0] = rowColumnName;
            intHeaders = new String[1];
            intHeaders[0] = columnColumnName;
            intValues = new int[1][1];
            stringValues = new String[1][1];
        } else {
            stringHeaders = new String[0];
            intHeaders = new String[2];
            intHeaders[0] = rowColumnName;
            intHeaders[1] = columnColumnName;
            columnIndexForTableDataSet = 1;
            intValues = new int[1][2];
            stringValues = new String[1][0];
        }

        Iterator columnIterator = columnHeaders.iterator();
        int columnNumber = 2;
        while (columnIterator.hasNext()) {
            Object column = columnIterator.next();
            String columnHeader = null;
            if (column instanceof String) {
                columnHeader = (String) column;
                stringValues[0][columnIndexForTableDataSet]=columnHeader;
            }
            else {
                columnHeader = ((Integer) column).toString();
                intValues[0][columnIndexForTableDataSet]=((Integer) column).intValue();
            }
            
            float[] values = new float[rowHeaders.size()];
            TableDataSetIndexedValue tdsiv = new TableDataSetIndexedValue(inputTableName,stringHeaders,intHeaders,stringValues,intValues,valuesColumnName);
            tdsiv.setValueMode(TableDataSetIndexedValue.SUM_MODE);
            rowIterator= rowHeaders.iterator();
            int currentRowNumber = 0;
            while (rowIterator.hasNext()) {
                Object row = rowIterator.next();
                if (row instanceof String) {
                    stringValues[0][rowIndexForTableDataSet] = (String) row;
                } else {
                    intValues[0][rowIndexForTableDataSet] = ((Integer) row).intValue();
                }
                tdsiv.setIntValues(intValues);
                tdsiv.setStringValues(stringValues);
                values[currentRowNumber] = tdsiv.retrieveValue(aCollection);
                currentRowNumber++;
            }
            out.appendColumn(values,columnHeader);
        }
        
        return out;
        
    }
    

}
