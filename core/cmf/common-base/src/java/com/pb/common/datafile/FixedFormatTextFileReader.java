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

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataFileReader;
import com.pb.common.datafile.TableDataSet;

/**
 * Reads a fixed-format text file into a TableDataSet.  
 * Assumes that there is a dictionary file defining the column positions
 * and column labels of each field.  If no dictionary is provided, looks for
 * one with the same name, but the extension .dct.  
 *  
 * @author Erhardt
 * @version 1.0 Jul 27, 2006
 *
 */
public class FixedFormatTextFileReader extends TableDataFileReader {
    
    protected static Logger logger = Logger.getLogger(FixedFormatTextFileReader.class);
    
    /**
     * Default constructor.  
     */
    public FixedFormatTextFileReader() {
        super();
    }

    
    /**
     * Convenience method to load a fixed format file into a table data class.
     * 
     * The dictionary must be in CSV format, with the following columns:
     *   COLUMN - Name of the column in the data. 
     *   START  - Start position, 1-based, inclusive.
     *   END    - End position, 1-based, inclusive.
     *   TYPE   - STRING indicates it should be read as a string, 
     *            NUMBER, as a number. 
     *   LABELINFILE - 1 indicates that the first row of data
     *                 contains this field, 0 it does not.
     * 
     * @param file  name of file to read
     * 
     * @throws IOException
     * @return Data read from file in table.  
     */
    public TableDataSet readFile(File file) throws IOException {
        
        // get the path, and change the final extension
        String path = file.getPath(); 
        String dictionaryPath = path.replace(".dat", ".dct");
        File dictionaryFile = new File(dictionaryPath);
        
        return readFile(file, dictionaryFile);
    }

    
    /**
     * Convenience method to load a fixed format file into a table data class.
     * 
     * The dictionary must be in CSV format, with the following columns:
     *   COLUMN - Name of the column in the data. 
     *   START  - Start position, 1-based, inclusive.
     *   END    - End position, 1-based, inclusive.
     *   TYPE   - STRING indicates it should be read as a string, 
     *            NUMBER, as a number. 
     *   LABELINFILE - 1 indicates that the first row of data
     *                 contains this field, 0 it does not.
     * 
     * 
     * @param file  name of file to read
     * @param dictionaryFile name of the dictionary file containing column positions
     * 
     * @throws IOException
     * @return Data read from file in table.  
     */
    public TableDataSet readFile(File file, File dictionaryFile) throws IOException {
                        
        // read the dictionary, and open the data file
        TableDataSet dictionary = readDictionary(dictionaryFile);
        BufferedReader inStream = openFile(file);
        
        // Skip the first row if it just contains headers
        int labelFlagColumn = dictionary.getColumnPosition("LABELINFILE");
        float labelsInFile = dictionary.getColumnTotal(labelFlagColumn);
        if (labelsInFile > 0) {
            inStream.readLine(); 
        }
                
        // read the data
        ArrayList[] columnData = readData(inStream, dictionary);        
        inStream.close();
        
        // make the table        
        TableDataSet tds = makeTableDataSet(columnData, dictionary);
        tds.setName(file.toString());
        
        return tds;
    }    
    
    /**
     * Opens the file, and creates a buffered file reader to that file.  
     * 
     * @param file The file to open.  
     * @return Reader for the file
     * @throws IOException
     */
    private BufferedReader openFile(File file) throws IOException {
        logger.debug("Opening file: "+file);
        
        BufferedReader inStream = null;
        try {
            inStream = new BufferedReader( new FileReader(file) );
        }
        catch (IOException e) {
            throw e;
        }
        
        return inStream;
    }
    
    /**
     *  Read and parse data portion of file.
     *  
     *  @param inStream The stream of input data.
     *  @param dictionary The dictionary defining how the columns are set up.
     *  
     *  @return An ArrayList of data for each column read.  
     *  
     *  @throws IOException
     */
    private ArrayList[] readData(BufferedReader inStream, TableDataSet dictionary) throws IOException {
        
        // set up the start, end and type arrays
        int start[]   = new int[dictionary.getRowCount()];
        int end[]     = new int[dictionary.getRowCount()];
        String type[] = new String[dictionary.getRowCount()];
        for (int i=0; i<dictionary.getRowCount(); i++) {
            start[i] = (int) dictionary.getValueAt(i+1, "START");
            end[i]   = (int) dictionary.getValueAt(i+1, "END");
            type[i]  = dictionary.getStringValueAt(i+1, "TYPE");
        }        
        
        // set up the data container
        ArrayList[] columnData = new ArrayList[dictionary.getRowCount()];
        for (int i=0; i<columnData.length; i++) {
            if (type[i].equals("NUMBER")) {
                columnData[i] = new ArrayList<Float>();    
            }
            if (type[i].equals("STRING")) {
                columnData[i] = new ArrayList<String>();
            }            
        }        
        
        //Process each line in the file
        String line;
        int lineNum = 1; 
        while ((line = inStream.readLine()) != null) {
            String[] lineData = new String[dictionary.getRowCount()];
            for (int i=0; i<lineData.length; i++) {
                try {
                    lineData[i] = line.substring(start[i]-1, end[i]);
                    
                    // check for missing values
                    if (lineData[i].trim().equals(".")) {
                        logger.warn("Replacing missing value '.' with '0' at line: " + lineNum + " column: " + i);
                        lineData[i] = "0";
                    }
                    
                    if (type[i].equals("NUMBER")) {
                        columnData[i].add(new Float(lineData[i]));    
                    }
                    if (type[i].equals("STRING")) {
                        columnData[i].add(lineData[i]);
                    }  
                } catch (Exception e) {
                    logger.error("Cannot convert value: " + lineData[i] + " to type: " + type[i]);
                    logger.error("Row: " + lineNum + " Column: " + i);
                    throw new RuntimeException(e); 
                }
            }
            lineNum++;
        }
        
        return columnData;  
    }

    /**
     * Creates a TableDataSet from the data. 
     * 
     * @param columnData One ArrayList of data for each column.  
     * @param dictionary Dictionary with column names. 
     * @return TableDataSet with the data.  
     */
    private TableDataSet makeTableDataSet(ArrayList[] columnData, TableDataSet dictionary) {

        TableDataSet table = new TableDataSet();
        for (int i=0; i<columnData.length; i++) {
            String name = dictionary.getStringValueAt(i+1, "COLUMN");
            String type = dictionary.getStringValueAt(i+1, "TYPE");
            
            if (type.equals("STRING")) {                
                String[] data = new String[columnData[i].size()];
                for (int j=0; j<data.length; j++) {
                    data[j] = (String) columnData[i].get(j);
                }                
                table.appendColumn(data, name);
            }
            if (type.equals("NUMBER")) {
                float[] data = new float[columnData[i].size()];
                for (int j=0; j<data.length; j++) {
                    data[j] = (Float) columnData[i].get(j);
                }                
                table.appendColumn(data, name);
            }
        }
        
        return table;
    }
    
    /**
     * The dictionary must be in CSV format, with the following columns:
     *   COLUMN - Name of the column in the data. 
     *   START  - Start position, 1-based, inclusive.
     *   END    - End position, 1-based, inclusive.
     *   TYPE   - STRING indicates it should be read as a string, 
     *            NUMBER, as a number. 
     *   LABELINFILE - 1 indicates that the first row of data
     *                 contains this field, 0 it does not.
     * 
     * @param dictionaryFile File name of the dictionary file.  
     * @return The dictionary.  
     */
    public TableDataSet readDictionary(File dictionaryFile) {
        
        // read the data
        TableDataSet dictionary = new TableDataSet();
        try{ 
            logger.info("Reading file " + dictionaryFile);
            CSVFileReader reader = new CSVFileReader();
            dictionary = reader.readFile(dictionaryFile);
        } catch (IOException e) {
            logger.error("Error reading dictionary file " + dictionaryFile);
            System.exit(1);
        }        
        
        // check the format
        dictionary.checkColumnPosition("COLUMN");
        dictionary.checkColumnPosition("START");
        dictionary.checkColumnPosition("END");
        dictionary.checkColumnPosition("TYPE");
        dictionary.checkColumnPosition("LABELINFILE");
        
        // check the values
        for (int i=1; i<=dictionary.getRowCount(); i++) {
            int start = (int) dictionary.getValueAt(i, "START");
            int end = (int) dictionary.getValueAt(i, "START");
            if (start > end) {
                throw new RuntimeException("Start greater than end position: "+start+">"+end);
            }
            
            String type = dictionary.getStringValueAt(i, "TYPE");
            if (!type.equals("NUMBER") && !type.equalsIgnoreCase("STRING")) {
                throw new RuntimeException("Column type must be NUMBER or STRING.");
            }
            
            int labelInFile = (int) dictionary.getValueAt(i, "LABELINFILE");
            if (labelInFile!=0 && labelInFile!=1) {
                throw new RuntimeException("LABELINFILE must be 0 or 1.");
            }
        }
        
        return dictionary; 
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#readTable(java.lang.String)
     */
    public TableDataSet readTable(String tableName) throws IOException {
        File fileName = new File (getMyDirectory().getPath() + File.separator + tableName + ".dat");
        TableDataSet me= readFile(fileName);
        me.setName(tableName);
        return me;        
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#close()
     */
    public void close() {
    }

}
