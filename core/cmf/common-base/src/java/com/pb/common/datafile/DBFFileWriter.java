/*
 * Copyright  2006 PB Consult Inc.
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

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

import org.apache.log4j.Logger;

import com.linuxense.javadbf.DBFException;
import com.linuxense.javadbf.DBFField; 
import com.linuxense.javadbf.DBFWriter;

import com.pb.common.datafile.DataTypes;
import com.pb.common.datafile.TableDataFileWriter;
import com.pb.common.datafile.TableDataSet;

/**
 * @author Erhardt
 * @version 1.0 Jul 27, 2006
 *
 */
public class DBFFileWriter extends TableDataFileWriter {
    
    protected static Logger logger = Logger.getLogger(DBFFileWriter.class);

    int characterFieldLength; 
    int numericFieldLength; 
    int decimalFormat; 
    
    /**
     * Default constructor
     */
    public DBFFileWriter() {
        super();
        characterFieldLength = 30;
        numericFieldLength = 12;
        decimalFormat = 3; 
    }

    /**
     * Writes the tableData to the file in DBF format.
     * Convenience method to apply the same format to each 
     * field in the table (3 decimals).
     * 
     * @param table the TableDataSet to write
     * @param file  the destination file to write to
     * 
     * @throws IOException
     */
    public void writeFile(TableDataSet table, File file) throws IOException {
        
        // set all the decimals to the default number
        int[] decimals = new int[table.getColumnCount()]; 
        for (int i=0; i<decimals.length; i++) {
            decimals[i] = decimalFormat; 
        }
        
        writeFile(table, decimals, file);
    }

    /**
     * Writes the tableData to the file in DBF format.
     * Convenience method to apply the same format to each 
     * field in the table (3 decimals).
     * 
     * @param table the TableDataSet to write
     * @param decimals An array indicating the number of decimals for each field.
     * @param file  the destination file to write to
     * 
     * @throws IOException
     */
    public void writeFile(TableDataSet table, int[] decimals, File file)
            throws IOException {
        
        // Create a writer, with the proper field formats
        DBFField[] fields = defineDBFFields(table, decimals);
        DBFWriter writer = new DBFWriter();
        writer.setFields(fields);
        
        // populate the data
        writer = populateData(writer, table);
        
        // write the output
        FileOutputStream outStream = new FileOutputStream(file);
        writer.write(outStream);
        outStream.close();
    }
    
    /** 
     * Creates a set of empty DBF fields of the correct format. 
     * 
     * @param table Table to take field names and formats from.
     * @return an array of DBF fields of the proper format.
     */
    private DBFField[] defineDBFFields(TableDataSet table, int[] decimals) {
        
        //Pull data out of tableData object for convenience
        int nCols = table.getColumnCount();
        int[] columnType = table.getColumnType();
        String[] columnLabels = table.getColumnLabels();
        
        // define the DBF fields
        DBFField[] field = new DBFField[nCols];        
        for (int c=0; c<nCols ; c++) {
            field[c] = new DBFField();
            field[c].setName(columnLabels[c]);
            if (columnType[c] == DataTypes.STRING) {
                field[c].setDataType(DBFField.FIELD_TYPE_C);
                field[c].setFieldLength(characterFieldLength);
            }
            else if (columnType[c] == DataTypes.NUMBER) {
                field[c].setDataType(DBFField.FIELD_TYPE_F);  
                field[c].setFieldLength(numericFieldLength);
                field[c].setDecimalCount(decimals[c]);
            }
            else {
                throw new RuntimeException("unknown column data type: " + columnType[c]);
            }                       
        }
        
        return field;
    }
    
    /**
     * Adds the data in the table to the DBF writer, and returns it.
     * 
     * @param writer An empty DBF writer to add data to.
     * @param table  The data to add.
     * @return The same DBF writer, but populated.
     */
    private DBFWriter populateData(DBFWriter writer, TableDataSet table) {
       
        //Pull data out of tableData object for convenience
        int nRows = table.getRowCount();
        int nCols = table.getColumnCount();
        int[] columnType = table.getColumnType();
        
        // set each row
        for (int r=0; r < nRows; r++) {
            Object[] rowData = new Object[nCols];
            
            // get the data individually for each column, to set the type
            for (int c=0; c < nCols; c++) {
                if (columnType[c] == DataTypes.STRING) {
                    rowData[c] = table.getStringValueAt(r+1, c+1);
                }
                else if (columnType[c] == DataTypes.NUMBER) {
                    rowData[c] = new Double(table.getValueAt(r+1, c+1));
                }
                else {
                    throw new RuntimeException("unknown column data type: " + columnType[c]);
                }  
            }
            
            // add the row
            try {
                writer.addRecord(rowData);
            } 
            catch (DBFException e) {
                logger.error("Error writing DBF at row " + r);
                e.printStackTrace();
                System.exit(1);
            }
        }
        
        return writer; 
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#writeTable(com.pb.common.datafile.TableDataSet, java.lang.String)
     */
    public void writeTable(TableDataSet table, String tableName)
            throws IOException {
        File file = new File (getMyDirectory().getPath() + File.separator + tableName + ".dbf");
        writeFile(table, file);
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#close()
     */
    public void close() {
    }

}
