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
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

import org.apache.log4j.Logger;

import com.linuxense.javadbf.DBFException;
import com.linuxense.javadbf.DBFField;
import com.linuxense.javadbf.DBFReader;
import com.pb.common.datafile.TableDataFileReader;
import com.pb.common.datafile.TableDataSet;

import static com.pb.common.datafile.DataTypes.*;

/**
 * This class reads DBF files and stores them as TableDataSets.  It uses the third party 
 * classes from com.linuxense.javadbf
 * 
 * @author Erhardt
 * @version 1.0 Nov 27, 2006
 *
 */
public class DBFFileReader extends TableDataFileReader {

    protected static transient Logger logger = Logger.getLogger(DBFFileReader.class);

    //These attributes are initialized on each call to readFile()
    private int columnCount;
    private int rowCount;
    private List columnData;
    private ArrayList columnLabels;
    private int[] columnType;
    private DBFField[] columnDBF; 
    
    /** 
     * Default constructor.  
     *
     */
    public DBFFileReader() {
        
    }
    
    /**
     * @see com.pb.common.datafile.TableDataFileReader#readFile(java.io.File)
     */
    @Override
    public TableDataSet readFile(File file) throws IOException {
        
        //Initialize class attributes
        columnCount = 0;
        rowCount = 0;
        columnData = new ArrayList();
        columnLabels = new ArrayList();
        columnType = null;

        // open file
        logger.debug("Opening file: "+file);
        InputStream inStream = new FileInputStream(file);
        DBFReader reader = new DBFReader(inStream);
               
        // read data
        readHeader(reader);
        readData(reader);
        inStream.close();
        
        // make table
        TableDataSet tds = makeTableDataSet();
        tds.setName(file.toString());
        return tds;
    }

    /**
     * Reads the header information and sets up the table structure.  
     * 
     * @param reader
     * @throws DBFException
     */
    private void readHeader(DBFReader reader) throws DBFException {
        
        // Determine the number of columns in the file
        columnCount = reader.getFieldCount(); 
        logger.debug("number of columns in file: " + columnCount);
        
        //Determine the number of lines in the file
        rowCount = reader.getRecordCount(); 
        logger.debug("number of lines in file: " + rowCount);

        //Get the field descriptions
        columnType = new int[columnCount];
        columnDBF = new DBFField[columnCount];
        for (int col=0; col<columnCount; col++) {
            columnDBF[col] = reader.getField(col);
            columnLabels.add(columnDBF[col].getName());      
            
            switch(columnDBF[col].getDataType()) {
            case DBFField.FIELD_TYPE_C:
                columnType[col] = STRING;  
                columnData.add(new String[rowCount]);
                break;
            case DBFField.FIELD_TYPE_F:
                columnType[col] = NUMBER;  
                columnData.add(new float[rowCount]);
                break;
            case DBFField.FIELD_TYPE_N:
                columnType[col] = NUMBER;  
                columnData.add(new float[rowCount]);
                break;
            default:
                throw new RuntimeException("Error, invalid field type" + columnDBF[col].getDataType());                    
            }
        }
    }
    
    

    /**
     * Read and parse data portion of file where the caller has passed in a
     */
    private void readData(DBFReader reader)
        throws IOException {

        int rowNumber = 0;
        Object[] rowObjects; 
        
        while ((rowObjects = reader.nextRecord()) != null) {

            if(rowNumber % 25000 ==0)
                logger.debug("Reading line "+rowNumber);
            
            //Process each field on the current line
            for (int col=0; col < columnCount; col++) {
                                
                switch(columnDBF[col].getDataType()) {
                case DBFField.FIELD_TYPE_C:
                    String token = (String) rowObjects[col];
                    //Remove " character from string if present
                    if (token.startsWith("\"")) {
                        token = token.substring(1);
                    }
                    if (token.endsWith("\"")) {
                        token = token.substring(0, token.length());
                    }
                    String[] s = (String[]) columnData.get(col);
                    s[rowNumber] = token;
                    break;
                case DBFField.FIELD_TYPE_F:
                    float[] f = (float[]) columnData.get(col);            
                    f[rowNumber] = ((Float) rowObjects[col]).floatValue();
                    break;
                case DBFField.FIELD_TYPE_N:
                    float[] n = (float[]) columnData.get(col);            
                    n[rowNumber] = ((Double) rowObjects[col]).floatValue();
                    break;
                default:
                    throw new RuntimeException("Error, invalid field type" + columnDBF[col].getDataType());                    
                }
            }
            rowNumber++;
        }
    }

    
    /**
     * Creates the table data set from the information read into memory
     * 
     * @return
     */
    private TableDataSet makeTableDataSet() {

        TableDataSet table = new TableDataSet();

        //Column labels were not present in the file
        if (columnLabels.size() == 0) {
            for (int i=0; i < columnCount; i++) {
                columnLabels.add("column_"+(i+1));
            }
        }

        for (int i=0; i < columnCount; i++) {
            table.appendColumn(columnData.get(i), (String) columnLabels.get(i));
        }

        return table;
    }
    
    /**
     * @see com.pb.common.datafile.TableDataReader#close()
     */
    @Override
    public void close() {
    }

    /**
     * @see com.pb.common.datafile.TableDataReader#readTable(java.lang.String)
     */
    @Override
    public TableDataSet readTable(String tableName) throws IOException {
        File fileName = new File (getMyDirectory().getPath() + File.separator + tableName + ".dbf");
        TableDataSet me= readFile(fileName);
        me.setName(tableName);
        return me;
    }

}
