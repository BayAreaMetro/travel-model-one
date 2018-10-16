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

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.text.DecimalFormat;
import java.util.ArrayList;
import org.apache.log4j.Logger;

import com.pb.common.util.PaddedDecimalFormat;


/**
 * Creates a TableData class from a CSV file.
 *
 * @author   Tim Heier
 * @version  1.0, 2/07/2004
 *
 */
public class CSVFileWriter extends TableDataFileWriter implements DataTypes {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    private String delimChar = ",";
    
    boolean quoteStrings = false;
    
    private DecimalFormat myDecimalFormat = new GeneralDecimalFormat("0.#####E0",100000000,.01);

    public void setMyDecimalFormat(DecimalFormat myDecimalFormat) {
        this.myDecimalFormat = myDecimalFormat;
    }

    public DecimalFormat getMyDecimalFormat() {
        return myDecimalFormat;
    }

    public CSVFileWriter () {
    }


    /**
     * Sets the delimiter used to separate each column.
     * 
     * @param delimChar
     */
    public void setDelimChar(String delimChar) {
        this.delimChar = delimChar;
    }
    
    
    /**
     * 
     * @return the delimiter character in use
     */
    public String getDelimChar() {
        return delimChar;
    }
    
    
    
    /**
     * Convenience method to apply the same format to each field in the table.
     * 
     * @param tableData the TableDataSet to write
     * @param file  the destination file to write to
     * 
     * @throws IOException
     */
    public void writeFile(TableDataSet tableData, File file) throws IOException {
        if(logger.isDebugEnabled()){
            logger.debug("Writing file "+tableData.getName()+" to file "+file);
        }
        writeFile(tableData, file, 0, myDecimalFormat);
    }

    
    /**
     * Convenience method to apply the same format to each field in the table.
     * Each field with have a field width large enough to print the field but
     * will not be padded.
     * 
     * @param tableData the TableDataSet to write
     * @param file  the destination file to write to
     * @param format an instance of DecimalFormat describing the field mask
     * 
     * @throws IOException
     */
    public void writeFile(TableDataSet tableData, File file, DecimalFormat format) throws IOException {
        writeFile(tableData, file, 0, format);
    }

    
    /**
     * Convenience method to apply the same format to each field in the table.
     * 
     * @param tableData the TableDataSet to write
     * @param file  the destination file to write to
     * @param fieldWidth  the desired width of each field
     * @param format an instance of DecimalFormat describing the field mask
     * 
     * @throws IOException
     */
    public void writeFile(TableDataSet tableData, File file, int fieldWidth, DecimalFormat format) throws IOException {

        int nCols = tableData.getColumnCount();
        
        PaddedDecimalFormat[] paddedFormat = new PaddedDecimalFormat[nCols];

        //Use the supplied format for each column
        for (int i=0; i < nCols; i++) {
            paddedFormat[i] = new PaddedDecimalFormat(fieldWidth, format);
        }
        writeFile(tableData, file, paddedFormat);
    }
    
    /**
     * This method will save to a new file name, overwriting if it exists.
     *
     * The DecimalFormat class is used to format each field. The fieldWidth
     * parameter is used to create a right-justified field padded with spaces.
     * 
     * Examples showing the C-like syntax mapped to the DecimalFormat syntax
     * include:
     * 
     * %8.2f --> #.00  and fieldWidth = 8
     * %6.0f --> #.#   and fieldWidth = 6
     * %.3f  --> #.000 and fieldWidth = 3
     *
     * @param tableData the TableDataSet to write
     * @param file  the destination file to write to
     * @param fieldFormat an array of PaddedDecimalFormat objects, one for each column
     * 
     */
    public void writeFile(TableDataSet tableData, File file, PaddedDecimalFormat[] fieldFormat) throws IOException {
        String formatString;
        PrintWriter outStream = null;

        //Pull data out of tableData object for convenience
        int nCols = tableData.getColumnCount();
        int nRows = tableData.getRowCount();
        int[] columnType = tableData.getColumnType();
        String[] columnLabels = tableData.getColumnLabels();
        ArrayList columnData = tableData.getColumnData();
        
        if (fieldFormat.length != nCols) {
            throw new RuntimeException("Length of format array is " + fieldFormat.length + 
                    " should be " + nCols);
        }
        
        try {
            outStream = new PrintWriter (new BufferedWriter( new FileWriter(file) ) );

            //Print titles
            for (int i = 0; i < columnLabels.length; i++) {
                if (i != 0)
                    outStream.print(",");
                outStream.print( columnLabels[i] );
            }
            outStream.println();

            //Print data
            for (int r=0; r < nRows; r++) {
                //float[] rowValues = getRowValues(r, 0);
                
                for (int c=0; c < nCols; c++) {
                    if (c != 0)
                        outStream.print(",");

                    switch(columnType[c]) {
                    case STRING:
                        String[] s = (String[]) columnData.get(c);
                        if (quoteStrings) {
                            outStream.print("\""+ s[r]+"\"" );
                        } else {
                            outStream.print(s[r]);
                        }
                        break;
                    case NUMBER:
                        float[] f = (float[]) columnData.get(c);
                        outStream.print( fieldFormat[c].format(f[r]) );
                        break;
                    default:
                        throw new RuntimeException("unknown column data type: " + columnType[c]);
                    }
                }
                outStream.println();
            }
            outStream.close();
        }
        catch (IOException e) {
            throw e;
        }

        //Update dirty flag
        tableData.setDirty(false);
    }
    
    

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#writeTable(com.pb.common.datafile.TableDataSet, java.lang.String)
     */
    public void writeTable(TableDataSet tableData, String tableName) throws IOException {
        File file = new File (getMyDirectory().getPath() + File.separator + tableName + ".csv");
        writeFile(tableData, file);
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#close()
     */
    public void close() {
    }

    public boolean isQuoteStrings() {
        return quoteStrings;
    }

    public void setQuoteStrings(boolean quoteStrings) {
        this.quoteStrings = quoteStrings;
    }

    
    
}
