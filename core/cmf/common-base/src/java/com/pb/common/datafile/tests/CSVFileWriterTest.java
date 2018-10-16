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
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;


/**
 * Tests the CSVFileWriter class.
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class CSVFileWriterTest {

    
    public static void main(String[] args) {

        CSVFileWriterTest.testWrite();
    }
    
    
    public static void testWrite() {
    
        //Read a CSV file first
        TableDataSet table = null;
        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File("src/sql/zonedata.csv"));
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        //Write the table out to a new file name
        CSVFileWriter writer = new CSVFileWriter();
        try {
            writer.writeFile(table, new File("src/sql/zonedata_new.csv"));
        } catch (IOException e) {
            e.printStackTrace();
        }

    }
    
    
}
