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

import java.io.File;
import java.io.IOException;

import com.pb.common.datafile.BinaryFileReader;
import com.pb.common.datafile.BinaryFileWriter;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;


/**
 * Tests the BinaryFileReader and BinaryFile Writer classes.
 *
 * @author   Tim Heier
 * @version  1.0, 5/08/2004
 */
public class BinaryFileTest {

    
    public static void main(String[] args) {

        BinaryFileTest.testWrite();
        BinaryFileTest.testRead();
    }

    
    public static void testWrite() {
        TableDataSet table = null;

        //Read sample file from common-base/src/sql directory
        long startTime = System.currentTimeMillis();
        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File("src/sql/zonedata.csv"));
        } catch (IOException e) {
            e.printStackTrace();
        }
        long stopTime = System.currentTimeMillis();
        System.out.println("Time used to read CSV file: " + (stopTime-startTime));
        
        //Write the table out to a new file name
        BinaryFileWriter writer = new BinaryFileWriter();
        try {
            writer.writeFile(table, new File("src/sql/zonedata.bin"));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    
    public static void testRead() {
        TableDataSet table = null;

        //Read sample file from common-base/src/sql directory
        long startTime = System.currentTimeMillis();
        try {
            BinaryFileReader reader = new BinaryFileReader();
            table = reader.readFile(new File("src/sql/zonedata.bin"));
        } catch (IOException e) {
            e.printStackTrace();
        }
        long stopTime = System.currentTimeMillis();
        System.out.println("Time used to read Binary file: " + (stopTime-startTime));

        //Display some statistics about the file
        System.out.println("Number of columns: " + table.getColumnCount());
        System.out.println("Number of rows: " + table.getRowCount());

        //Display column titles
        String[] labels = table.getColumnLabels();
        for (int i = 0; i < labels.length; i++) {
            System.out.print( String.format(" %10s", labels[i]) );
        }
        System.out.println();

        //Print data
        for (int i=1; i <= 10; i++) {
            //Get a row from table
            String row[] = table.getRowValuesAsString(i);

            for (int j=0; j < row.length; j++) {
                System.out.print( String.format(" %10s", row[j]) );
            }
            System.out.println();
        }
    }

}
