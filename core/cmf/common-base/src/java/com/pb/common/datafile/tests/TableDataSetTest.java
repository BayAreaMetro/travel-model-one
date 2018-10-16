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
package com.pb.common.datafile.tests;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;

import java.io.File;
import java.io.IOException;
import org.apache.log4j.Logger;

/**
 * Tests the TableDataSet class.
 *
 * @author   Tim Heier
 * @version  1.0, 2/8/2003
 */
public class TableDataSetTest {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile.test");
    
    public static void main(String[] args) {
        TableDataSet table = TableDataSetTest.readCSVFile();
        TableDataSetTest.testGetRowValues( table );
        TableDataSetTest.testGetValueAt( table );
        TableDataSetTest.testColmnNameRetrieval( table );
        TableDataSetTest.testSetValueAt( table );
        TableDataSetTest.testSaveFile( table );
        TableDataSetTest.testBuildIndex( table );
        TableDataSetTest.readCSVFileNoLabels();
        TableDataSetTest.readCSVFileFilteringColumns();
        //TableDataSetTest.testPerformance();
    }


/* TCH - Test method for my machine.

    public static void testPerformance() {
        TableDataSetTest.printMemory();
        
        TableDataSet[] tables = new TableDataSet[3];
        long startTime, stopTime = 0;
        try {
            for (int i=0; i < 3; i++) {
                startTime = System.currentTimeMillis();
                tables[i] = new TableDataSet(new File("c:/temp/morpc/M5678.csv"));
                stopTime = System.currentTimeMillis();
                logger.info("Finished reading " + i + ", " + (stopTime-startTime));
                TableDataSetTest.printMemory();
            }
            startTime = System.currentTimeMillis();
            tables[2].saveFile(new File("c:/temp/morpc/M5678_new.csv"), 0, new DecimalFormat("#.000000"));
            stopTime = System.currentTimeMillis();
            logger.info("Finished writing " + (stopTime-startTime));
            TableDataSetTest.printMemory();
        }
        catch (IOException e) {
            e.printStackTrace();
            return;
        }
    }
    
    public static void printMemory() {
        logger.info("Total memory : " + Runtime.getRuntime().totalMemory());
        logger.info("Max memory   : " + Runtime.getRuntime().maxMemory());
        logger.info("Free memory  : " + Runtime.getRuntime().freeMemory());
    }
*/  
    
    /**
     * Read a table data set.
     *
     * @return a fully populated TableDataSet
     */
    public static TableDataSet readCSVFile() {
        System.out.println("executing readCSVFile()");
        TableDataSet table = null;

        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File("src/sql/bufcrl1.txt"));
        }
        catch (IOException e) {
            e.printStackTrace();
        }

        return table;
    }


    /**
     * Tests the getRowValues() method.
     *
     */
    public static void testGetRowValues(TableDataSet table) {
        System.out.println("executing testGetRowValues()");

        //Display some statistics about the file
        System.out.println("Number of columns: " + table.getColumnCount());
        System.out.println("Number of rows: " + table.getRowCount());

        //Display column titles
        String[] titles = table.getColumnLabels();
        for (int i = 0; i < titles.length; i++) {
            System.out.print( String.format("%10s", titles[i]) );
        }
        System.out.println();

        try {
            //Print the first 10 rows
            for (int i=1; i <= 10; i++) {

                //Get a row from table
                float row[] = (float[]) table.getRowValues(i);

                for (int j=0; j < row.length; j++) {
                    System.out.print( String.format(" %9.2f", row[j]) );
                }
                System.out.println();
            }
        }
        catch (Throwable e) {
            System.out.println("Exception in testGetRowValues()");
            e.printStackTrace();
        }
    }

    
    /**
     * Tests the getValueAt() and getValues() methods.
     *
     */
    public static void testGetValueAt(TableDataSet table) {
        System.out.println("executing testGetValueAt()");

        //Get the name of a column
        float value1 = table.getValueAt( 1, 10 );
        float value2 = table.getValueAt( 2, 10 );
        String strValue = table.getStringValueAt( 2, 19 );
        
        System.out.println( String.format("value at (1,10) =%7.2f",  value1) );
        System.out.println( String.format("value at (2,10) =%7.2f",  value2) );

        System.out.println( String.format("value at (2,19) =%s",  strValue) );
        System.exit(1);

        //Ask for data as a float[][]. This can be used to create a Matrix
        float[][] values = null;
        try {
            values = table.getValues();

            for (int i = 0; i < 10; i++) {
    
                for (int j = 0; j < table.getColumnCount(); j++) {
                    System.out.print( String.format(" %9.2f", values[i][j]) );
                }
                System.out.println();
            }
        } 
        catch (Exception e) {
            System.out.println("Exception in testGetRowValues()");
            e.printStackTrace();
        }
    }

    
    /**
     * Test the column look-up features of the table dataset.
     *
     */
    public static void testColmnNameRetrieval(TableDataSet table) {
        System.out.println("executing testColmnNameRetrieval()");

        //Get the name of a column
        String name1 = table.getColumnLabel( 1 );
        String name2 = table.getColumnLabel( 2 );

        System.out.println( "column 1 = " + name1 );
        System.out.println( "column 2 = " + name2 );

        //Get the position of a column given it's name - case is ignored
        int position1 = table.getColumnPosition("zone");
        int position2 = table.getColumnPosition("totpop");

        System.out.println( "position of zone = " + position1 );
        System.out.println( "position of totpop = " + position2 );
        
        String hhInc = table.getStringValueAt(1, "totpop");
        System.out.println("totpop on row 1 = " + hhInc);
    }

    
    /**
     * Test the column look-up features of the table dataset.
     *
     */
    public static void testSetValueAt(TableDataSet table) {
        System.out.println("executing testSetValueAt()");
        
        float value1 = table.getValueAt( 1, 10 );
        System.out.println( String.format("value before update (1,10) =%7.2f",  value1) );

        table.setValueAt(1, 10, (float)300.1);

        System.out.println( String.format("value after update (1,10) =%7.2f",  table.getValueAt( 1, 10 )) );

    }

    
    /**
     * Test the indexing feature of the table dataset.
     *
     */
    public static void testSaveFile(TableDataSet table) {
        System.out.println("executing testSaveFile()");
        
        try {
            CSVFileWriter writer = new CSVFileWriter();
            writer.writeFile(table, new File("testtable_new.csv"));
        }
        catch (IOException e) {
            e.printStackTrace();
        }
    }

    
    /**
     * Test the indexing feature of the table dataset.
     *
     */
    public static void testBuildIndex(TableDataSet table) {
        System.out.println("executing testBuildIndex()");

        //Build an index on column 1
        table.buildIndex(1);
        float value1 = table.getIndexedValueAt( 25, 1 );

        System.out.println( String.format("looking up indexed value=25 in column=1: %7.2f", value1) );
    }

    
    /**
     * Read a table data set.
     */
    public static void readCSVFileNoLabels() {
        System.out.println("executing readCSVFileNoLabels()");
        
        TableDataSet table = null;

        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File("src/sql/zonedata_nolabels.csv"), false);
        }
        catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }

        //Display column titles
        String[] titles = table.getColumnLabels();
        for (int i = 0; i < titles.length; i++) {
            System.out.print( String.format("%10s", titles[i]) );
        }
        System.out.println();
        
    }
    

    /**
     * Read a table data set.
     */
    public static void readCSVFileFilteringColumns() {
        System.out.println("executing readCSVFileFilteringColumns()");
        TableDataSet table = null;

        String[] columnsToRead = { "tothh", "hhinc1" };
        
        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File("src/sql/zonedata.csv"), columnsToRead);
        
            //Display column titles
            String[] titles = table.getColumnLabels();
            for (int i = 0; i < titles.length; i++) {
                System.out.print( String.format("%10s", titles[i]) );
            }
            System.out.println();
        
            //Print a couple of values
            float value1 = table.getValueAt( 1, 1 );
            float value2 = table.getValueAt( 1, 2 );
            float value3 = table.getValueAt( 2, 1 );
            float value4 = table.getValueAt( 2, 2 );
            
            System.out.println( String.format("value at (1,1) =%7.2f",  value1) );
            System.out.println( String.format("value at (1,2) =%7.2f",  value2) );
            System.out.println( String.format("value at (2,1) =%7.2f",  value3) );
            System.out.println( String.format("value at (2,2) =%7.2f",  value4) );
        }
        catch (Exception e) {
            e.printStackTrace();
        }

    }


}
