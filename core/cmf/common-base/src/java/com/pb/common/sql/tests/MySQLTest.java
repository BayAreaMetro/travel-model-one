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

import com.pb.common.sql.SQLHelper;

import java.sql.*;

/**
 * Tests working with a JDBCProperties database using pure JDBC code.
 * 
 * Steps:  Create a connection to a local database as root user.
 *           Creates a table named "sample".
 *           Inserts values in table.
 *           Queries all rows in the table and prints results.
 * 
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class MySQLTest {

    public static String HOST     = "localhost";
    public static String DATABASE = "test";
    public static String USER     = "";
    public static String PASSWD   = "";
    public static String TABLE    = "sample";
    public static String DRIVER   = "com.mysql.jdbc.Driver";
    
    
    //Database url string - specific to vendor
    public static String URL = "jdbc:mysql://" + HOST + "/" + DATABASE + "?user=" + USER + "&password=" + PASSWD;

    
    public static void main (String[] args) {
        MySQLTest.testCreateTable();
        MySQLTest.testReadTable();
    }
    
    
    /** Create a new table for testing in the database.
     * 
     */ 
    public static void testCreateTable() {
        Statement stmt = null;
        try {
            //Load database driver
            Class.forName(DRIVER).newInstance();
            
            //Get a connection to the database
            System.out.println();
            System.out.println("----- Creating table");
            System.out.println("URL = " + URL);

            //Create a statement that can execute sql
            Connection conn = DriverManager.getConnection( URL );

            //Create a statement from th connection
            stmt = conn.createStatement();
            
            //Drop table - could generate an exception if table does not exist
            System.out.println("Dropping table \"sample\"");
            stmt.execute("DROP TABLE sample");
        } 
        catch (Exception e) {
            e.printStackTrace();
        }

        //Create table
        try {
            System.out.println("Creating table \"sample\"");
            stmt.execute("CREATE TABLE sample (city VARCHAR(20), areatype INT, cbdind FLOAT)");

            stmt.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('San Francisco',5,100.1)");
            stmt.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Portland',4,200.2)");
            stmt.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Albuquerque',3,300.3)");
            stmt.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Seattle', 2,400.4)");
            stmt.execute("INSERT INTO sample (city, areatype, cbdind) VALUES('Calgary', 1,500.5)");
            
        }
        catch (SQLException e) {
            System.out.println("SQLException: " + e.getMessage());
            System.out.println("SQLState:     " + e.getSQLState());
            System.out.println("VendorError:  " + e.getErrorCode());
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }


    /** Read all rows from a table in the database.
     * 
     */ 
    public static void testReadTable() {
        try {
            //Load database driver
            Class.forName(DRIVER).newInstance();

            System.out.println();
            System.out.println("----- Reading table");
            System.out.println("URL = " + URL);

            //Get a connection to the database
            Connection conn = DriverManager.getConnection( URL );

            //Create a statement from th connection
            Statement stmt = conn.createStatement();
            
            //Execute a sql statement
            ResultSet rs = stmt.executeQuery("SELECT * from " + TABLE);
            
            //Print the result set
            SQLHelper.printResultSet(rs);
            
            //Tidy up
            rs.close();
            stmt.close();
            conn.close();
        }
        catch (SQLException e) {
            System.out.println("SQLException: " + e.getMessage());
            System.out.println("SQLState:     " + e.getSQLState());
            System.out.println("VendorError:  " + e.getErrorCode());
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }
}
