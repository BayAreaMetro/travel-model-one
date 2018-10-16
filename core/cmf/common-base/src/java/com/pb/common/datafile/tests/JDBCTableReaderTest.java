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

import java.io.IOException;

import com.pb.common.datafile.JDBCTableReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.sql.JDBCConnection;

/**
 * Tests the JDBCTableReader class.
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class JDBCTableReaderTest {

    public static String HOST     = "localhost";
    public static String DATABASE = "test";
    public static String USER     = "";
    public static String PASSWD   = "";
    public static String TABLE    = "zonedata";
    public static String DRIVER   = "com.mysql.jdbc.Driver";
    
    
    //Database url string - specific to vendor
    public static String URL = "jdbc:mysql://" + HOST + "/" + DATABASE + "?user=" + USER + "&password=" + PASSWD;

    
    public static void main(String[] args) {

        JDBCTableReaderTest.testLoad();
    }
    
    
    public static void testLoad() {
        JDBCConnection jdbcConn = new JDBCConnection(URL, "com.mysql.jdbc.Driver", USER, PASSWD);

        JDBCTableReader reader = new JDBCTableReader(jdbcConn);
        
        TableDataSet table = null;
        try {
            table = reader.readTable(TABLE);
        } catch (IOException e) {
            e.printStackTrace();
        }
        jdbcConn.close();
        
        //Display some statistics about the file
        System.out.println("Number of columns: " + table.getColumnCount());
        System.out.println("Number of rows: " + table.getRowCount());

        //Display column titles
        String[] labels = table.getColumnLabels();
        for (int i = 0; i < labels.length; i++) {
            System.out.print( String.format("%10s", labels[i]) );
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
