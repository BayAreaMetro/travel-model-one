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
package com.pb.common.sql;

import org.apache.log4j.Logger;

import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * A convenience class that encapsulates the creation and cleanup of 
 * Statement class. Error handling is also taken care of.
 *
 * @author   Tim Heier
 * @version  1.0, 2/7/2004
 */
public class SQLExecute {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.sql");
    private JDBCConnection jdbcConn;
    private String[] columnNames = null;
    private int columnCount = 0;
    
    private SQLExecute() {
        
    }
    
    
    /**
     * 
     * @param jdbcConn
     */
    public SQLExecute(JDBCConnection jdbcConn) {
        this.jdbcConn = jdbcConn;
    }
    
    
    /**
     * Returns the nubmer of rows in a table. Note, there is no way to do this without running
     * a SQL command.
     * 
     * @param tableName
     * @return the number of rows in the specified table
     */
    public int getRowCount(String tableName) {
        int rowCount = 0;
        try {
            Statement stmt = jdbcConn.createStatement();
            String countString = "SELECT count(*) AS \"row_count\" FROM " + tableName;
            logger.debug("SQLExecute.getRowCount, " + countString); 
            ResultSet rs = stmt.executeQuery(countString);
            rs.next();
            rowCount = rs.getInt("row_count");
            logger.debug("SQLExecute.getRowCount, " + rowCount); 
            rs.close();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
        
        return rowCount;
    }
    
    
    /**
     * Execute an update or alter statement. Samples of update statements include:
     * 
     * eg. UPDATE, DROP TABLE, CREATE TABLE, ALTER TABLE, GRANT ...
     * 
     * @param sqlString
     */
    public void execute (String sqlString) {
        logger.debug("SQLExecute.execute, " + sqlString); 
        try {
            Statement stmt = jdbcConn.createStatement();
            stmt.execute(sqlString);
            stmt.close();
        } 
        catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    
    /**
     * Execute a query statement. Samples of query statements include:
     * 
     * eg. SELECT, JOIN
     * 
     * @param sqlString
     */
    public ResultSet executeQuery (String sqlString) {
        ResultSet rs = null;
        ResultSetMetaData metaData = null;
        
        logger.debug("SQLExecute.execute, " + sqlString); 
        try {
            Statement stmt = jdbcConn.createStatement();
            rs = stmt.executeQuery(sqlString);
            
            //Get the column labels
            metaData = rs.getMetaData();
            columnCount =  metaData.getColumnCount();
            columnNames = new String[columnCount];

            //Metadata values start in 1,2... but are stored 0,1...
            for(int column = 0; column < columnCount; column++) {
                columnNames[column] = metaData.getColumnLabel(column+1);
            }
            
        } 
        catch (SQLException e) {
            throw new RuntimeException(e);
        }

        return rs;
    }
    
    
    /**
     * Returns the column names for the last sql statement executed.
     * 
     * @return String[]
     */
    public String[] getColumnLabels() {
        return columnNames;
    }

    
    /**
     * Returns the number of columns for the last sql statement executed.
     * 
     * @return  int
     */
    public int getColumnCount() {
        return columnCount;
    }
}
