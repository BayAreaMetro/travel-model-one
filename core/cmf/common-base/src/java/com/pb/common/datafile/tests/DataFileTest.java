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

import java.util.Date;

import com.pb.common.datafile.DataFile;
import com.pb.common.datafile.DataReader;
import com.pb.common.datafile.DataWriter;

/**
 * Tests the records package.
 * class.
 *
 * @author    Tim Heier
 * @version   1.0, 4/15/2000
 *
 */
public class DataFileTest {

    public static void main(String[] args) throws Exception {
        int numRecords = 100;
        String fileName = "sample.db";

        //Delete file if it exists as part of the test
        File file = new File(fileName);

        if (file.exists()) {
            file.delete();
        }

        System.out.println("creating data file: sample.db");

        DataFile dataFile = new DataFile("sample.db", 100);

        System.out.println("adding data: lastAccessTime");

        DataWriter dw = new DataWriter("lastAccessTime");

        dw.writeObject(new Date());
        dataFile.insertRecord(dw);

        DataReader dr = dataFile.readRecord("lastAccessTime");
        Date d = (Date) dr.readObject();

        System.out.println("lastAccessTime = " + d.toString());

        System.out.println("updating data: lastAccessTime");
        dw = new DataWriter("lastAccessTime");
        dw.writeObject(new Date());
        dataFile.updateRecord(dw);

        System.out.println("reading data: lastAccessTime");
        dr = dataFile.readRecord("lastAccessTime");
        d = (Date) dr.readObject();
        System.out.println("lastAccessTime = " + d.toString());

        System.out.println("deleting data: lastAccessTime");
        dataFile.deleteRecord("lastAccessTime");

        if (dataFile.recordExists("lastAccessTime")) {
            throw new Exception("data not deleted");
        } else {
            System.out.println("data successfully deleted.");
        }

        System.out.println("test completed.");
    }
}
