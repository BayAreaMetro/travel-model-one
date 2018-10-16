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
package com.pb.common.datafile;

import java.io.IOException;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import org.apache.log4j.Logger;

import com.pb.common.sql.JDBCConnection;
import com.pb.common.sql.SQLExecute;

/**
 * Creates a TableData class from a table in a JDBC data source.
 *
 * @author   Tim Heier
 * @version  1.0, 2/07/2004
 *
 */
public class JDBCTableReader extends TableDataReader {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    private JDBCConnection jdbcConn = null;

    private boolean mangleTableNamesForExcel = false;

    
    public JDBCTableReader (JDBCConnection jdbcConn) {
        if (jdbcConn == null) {
            throw new RuntimeException("Database connection is null");
        }

        this.jdbcConn = jdbcConn;
    }


    /**
    * Load all columns and rows of table.
    */
    public TableDataSet readTable(String tableName) throws IOException {
        String mangledTableName = tableName;
        if (mangleTableNamesForExcel) {
            logger.debug("Mangling table name "+tableName+" to ["+tableName+"$]");
            mangledTableName = "["+tableName+"$]";
        }
        TableDataSet theTable = null;
        try {
           theTable =  loadTable(tableName, "SELECT * FROM " + mangledTableName);
           theTable.setName(tableName);
        } catch (RuntimeException e) {
            logger.warn("Table "+tableName+" can not be read by JDBCTableReader, "+e.toString());
            // want to return null object if table doesn't exist, to be consistent with other table readers.
            theTable = null;
        }
        return theTable;
    }


    /**
    * Load table using specified query string.
    */
    private TableDataSet loadTable(String tableName, String sqlString) throws IOException {
        List columnData = new ArrayList();
        String[] columnLabels;
        int columnCount;
        
        logger.debug("JDBCTableReader, table name: " + tableName);
        logger.debug("JDBCTableReader, SQL String: " + sqlString);
        
        if (mangleTableNamesForExcel) {
            logger.debug("Mangling table name "+tableName+" to ["+tableName+"$]");
            tableName = "["+tableName+"$]";
        }
        
        Statement stmt = null;    
        ResultSet rs = null;
        ResultSetMetaData metaData = null;
        
        SQLExecute sqlExecute = new SQLExecute(jdbcConn);
        try {
            int rowCount = sqlExecute.getRowCount(tableName);
            
            //Run main query
            rs = sqlExecute.executeQuery(sqlString);
            metaData = rs.getMetaData();
            
            columnCount = sqlExecute.getColumnCount();
            columnLabels = sqlExecute.getColumnLabels();
            int[] columnType  = new int[columnCount];

            //Set up a vector of arrays to hold the result set. Store the
            //column type at the same time.  Each vector holds a column of data.
            for (int c = 0; c < columnCount; c++) {
                int type = metaData.getColumnType(c+1);
                
                switch(type) {
                //Map these types to STRING
                case Types.CHAR:
                case Types.VARCHAR:
                case Types.LONGVARCHAR:
                case Types.DATE:
                case Types.TIME:
                case Types.TIMESTAMP:
                case Types.BIT:
                    columnData.add(new String[rowCount]);
                    columnType[c] = DataTypes.STRING; 
                    break;
                //Map these types to NUMBER
                case Types.TINYINT:
                case Types.SMALLINT:
                case Types.INTEGER:
                case Types.BIGINT:
                case Types.FLOAT:
                case Types.REAL:
                case Types.DOUBLE:
                case Types.NUMERIC:
                    columnData.add(new float[rowCount]);
                    columnType[c] = DataTypes.NUMBER; 
                    break;
                default:
                    System.err.println("**error** unknown column data type, column=" + c +
                            ", type=" + type);
                    break;
                }
            }

            //Read result set and store the data into column-wise arrays.
            //Column data in a ResultSet starts in 1,2...
            int row = 0;
            while (rs.next()) {
                for (int c=0; c < columnCount; c++) {
                    int type = columnType[c];
                    
                    switch(type) {
                    case DataTypes.STRING:
                        String[] s = (String[]) columnData.get(c);
                        s[row] = rs.getString(c+1);  
                        break;
                    case DataTypes.NUMBER:
                        float[] f = (float[]) columnData.get(c);
                        f[row] = rs.getFloat(c+1);  
                        break;
                    default:
                        System.err.println("**error** unknown column data type - should not be here");
                        break;
                    }
                }
                row++;
            }
        }
        catch (SQLException e) {
            throw new IOException(e.getMessage());
        }
//        finally {
//            try {
//                rs.close();
//                stmt.close();
//            }
//            catch (SQLException e) {
//                e.printStackTrace();
//            }
//        }
        
        TableDataSet tds =  makeTableDataSet(columnData, columnLabels, columnCount);
        tds.setName(tableName);
        return tds;
    }


    private TableDataSet makeTableDataSet(List columnData, String[] columnLabels, int columnCount) {

        TableDataSet table = new TableDataSet();

        for (int i=0; i < columnCount; i++) {
            table.appendColumn(columnData.get(i), columnLabels[i]);
        }

        return table;
    }
    
    
    /**
     * @return Returns the mangleTableNamesForExcel.
     */
    public boolean isMangleTableNamesForExcel() {
        return mangleTableNamesForExcel;
    }

    /**
     * @param mangleTableNamesForExcel The mangleTableNamesForExcel to set.
     */
    public void setMangleTableNamesForExcel(boolean mangleTableNamesForExcel) {
        this.mangleTableNamesForExcel = mangleTableNamesForExcel;
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#close()
     */
    public void close() {
        jdbcConn.close();
    }

}
