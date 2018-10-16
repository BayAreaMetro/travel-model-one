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
package com.pb.common.sql.tests;

import java.sql.ResultSet;
import java.sql.SQLException;

import com.pb.common.sql.JDBCConnection;
import com.pb.common.sql.SQLExecute;
import com.pb.common.sql.SQLHelper;

/**
 * Tests the JDBCConnection class. Work with a local JDBCProperties database.
 * 
 * 1. Create a connection to a local database as root user.
 * 2. Creates a table named "sample".
 * 3. Inserts values in table.
 * 4. Queries all rows in the table and prints results.
 * 
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class JDBCConnectionTest {

    public static String HOST     = "localhost";
    public static String DATABASE = "test";
    public static String USER     = "";
    public static String PASSWD   = "";
    public static String TABLE    = "sample";
    public static String DRIVER   = "com.mysql.jdbc.Driver";
    
    
    //Database url string - specific to vendor
    public static String URL = "jdbc:mysql://" + HOST + "/" + DATABASE + "?user=" + USER + "&password=" + PASSWD;

    
    public static void main (String[] args) {
        
        JDBCConnectionTest.testCreateTable();
        JDBCConnectionTest.testReadTable();
    }
    
    
    /** Create a new table for testing in the database.
     * 
     */ 
    public static void testCreateTable() {
        JDBCConnection connection = new JDBCConnection(URL, DRIVER, USER, PASSWD);
        
        SQLExecute sql = new SQLExecute(connection);

        try {
            sql.execute("DROP TABLE sample");
        } catch (Exception e) {
            System.out.println("table \"sample\" might not exist");
        }
        
        sql.execute("CREATE TABLE sample (city VARCHAR(20), areatype INT, cbdind FLOAT)");

        sql.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('San Francisco',5,100.1)");
        sql.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Portland',4,200.2)");
        sql.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Albuquerque',3,300.3)");
        sql.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Seattle', 2,400.4)");
        sql.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Calgary', 1,500.5)");

        connection.close();
    }


    /** Read all rows from a table in the database.
     * 
     */ 
    public static void testReadTable() {
        JDBCConnection connection = new JDBCConnection(URL, DRIVER, USER, PASSWD);
        
        //Print the tables names from the database
        String[] tables  = connection.getTableNames();
        for (int i=0; i<tables.length; i++) {
            System.out.println("table["+i+"]"+" = " + tables[i]);
        }
        
        //Create an execution wrapper and execute a SQL statement
        SQLExecute sql = new SQLExecute(connection);
        ResultSet rs = sql.executeQuery("SELECT * from " + TABLE);

        System.out.println();
        SQLHelper.printResultSet(rs);
        
        //Frees memory immediately
        try {
            rs.close();
        } catch (SQLException e) {
            e.printStackTrace();
        }
        
        connection.close();
    }
}
