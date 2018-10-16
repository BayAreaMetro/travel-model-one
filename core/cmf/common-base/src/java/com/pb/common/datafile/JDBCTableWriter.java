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
import org.apache.log4j.Logger;

import com.pb.common.sql.JDBCConnection;
import com.pb.common.sql.SQLExecute;

/**
 * @author jabraham
 *
 * This class writes TableDataSets to an SQL Database
 */
public class JDBCTableWriter extends TableDataWriter {
    
    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    private JDBCConnection jdbcConn = null;

    private boolean mangleTableNamesForExcel = false;

    

    public void writeTable(TableDataSet tableData, String tableName)
        throws IOException {
        String insertMangledTableName = tableName;
        if (mangleTableNamesForExcel) {
            logger.debug("Mangling table name "+tableName+" to ["+tableName+"$]");
            insertMangledTableName = "["+tableName+"$]";
        }
        String createMangledTableName = tableName;
        if (mangleTableNamesForExcel) {
            logger.debug("Mangling table name "+tableName+" to ["+tableName+"]");
            createMangledTableName = "["+tableName+"]";
        }
        saveTable(createMangledTableName, insertMangledTableName, tableData);
    }

    
    /**
     * @param mangledTableName
     * @param tableData
     */
    private void saveTable(String createMangledTableName, String insertMangledTableName, TableDataSet tableData) {
        
        //TODO: First we need to check to see if the table already exists and then delete it.
        
        // first create the table
        StringBuffer createStatement = new StringBuffer("CREATE TABLE "+createMangledTableName+ " (");
        int[] columnTypes = tableData.getColumnType();
        for (int c =0; c<columnTypes.length; c++) {
            if (c!=0) createStatement.append(",");
            createStatement.append(tableData.getColumnLabel(c+1));
            if (columnTypes[c] == TableDataSet.STRING) {
                createStatement.append(" VARCHAR(255)");
            } else {
                createStatement.append(" FLOAT");
            }
        }
        createStatement.append(");");
        SQLExecute sqlExecute = new SQLExecute(jdbcConn);
        sqlExecute.execute(createStatement.toString());
        
        // now set up the insert string prefix
        StringBuffer insertStringPrefix = new StringBuffer("INSERT INTO "+insertMangledTableName+" (");
        for (int c=0; c<columnTypes.length;c++){
            if (c!=0) insertStringPrefix.append(",");
            insertStringPrefix.append(tableData.getColumnLabel(c+1));
        }
        insertStringPrefix.append(") VALUES (");
        String insertStringPrefixString = insertStringPrefix.toString();
        
        // now insert the data
        for(int row=1;row<=tableData.getRowCount();row++) {
            StringBuffer insertString = new StringBuffer(insertStringPrefixString);
            for (int c=0;c<columnTypes.length;c++) {
                if (c!=0) insertString.append(",");
                if (columnTypes[c] == TableDataSet.STRING) {
                    insertString.append("\""+tableData.getStringValueAt(row,c+1)+"\"");
                } else {
                    insertString.append(tableData.getValueAt(row,c+1));
                }
            }
            insertString.append(");");
            sqlExecute.execute(insertString.toString());
        }
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

    
    /**
     * @param jdbcConn
     */
    public JDBCTableWriter(JDBCConnection jdbcConn) {
        super();
        this.jdbcConn = jdbcConn;
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#close()
     */
    public void close() {
        jdbcConn.close();
    }
}
