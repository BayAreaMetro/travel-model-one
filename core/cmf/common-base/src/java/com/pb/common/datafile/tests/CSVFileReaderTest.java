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

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.util.PerformanceTimer;
import com.pb.common.util.PerformanceTimerType;

/**
 * Tests the CSVFileReader class.
 * 
 * @author Tim Heier
 * @version 1.0, 2/7/2004
 */
public class CSVFileReaderTest {

    public static void main(String[] args) {

        CSVFileReaderTest.testRead();
    }

    public static void testRead() {

        CSVFileReader reader = new CSVFileReader();
        // Can set the delimiter set if needed
        // reader.setDelimSet(" ,\t\n\r\f\"");

        PerformanceTimer timer = PerformanceTimer.createNewTimer("CsvFileTest",
                PerformanceTimerType.CSV_READ);
        timer.start();

        // Read sample file from common-base/src/sql directory
        TableDataSet table = null;
        try {
            table = reader.readFile(new File("test.csv"));
            timer.stop();
        } catch (IOException e) {
            e.printStackTrace();
        }

        // Display some statistics about the file
        System.out.println("Number of columns: " + table.getColumnCount());
        System.out.println("Number of rows: " + table.getRowCount());

        // Display column titles
        String[] labels = table.getColumnLabels();
        for (int i = 0; i < labels.length; i++) {
            System.out.print(String.format(" %10s", labels[i]));
        }
        System.out.println();

        // Print data
        for (int i = 1; i <= 10; i++) {
            // Get a row from table
            String row[] = table.getRowValuesAsString(i);

            for (int j = 0; j < row.length; j++) {
                System.out.print(String.format(" %10s", row[j]));
            }
            System.out.println();
        }

    }
}
