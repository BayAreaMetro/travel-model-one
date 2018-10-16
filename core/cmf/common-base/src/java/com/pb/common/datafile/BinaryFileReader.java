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

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.ObjectInput;
import java.io.ObjectInputStream;
import java.util.ArrayList;
import org.apache.log4j.Logger;

/**
 * Reads a binary file containing a seriazlied TableDataSet class and creates
 * an instance of a TableDataSet class.
 *
 * @author   Tim Heier
 * @version  1.0, 5/08/2004
 *
 */
public class BinaryFileReader extends TableDataFileReader implements DataTypes {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    //These attributes are initialized on each call to readFile()
    private int columnCount;
    private int rowCount;
    private ArrayList columnData = new ArrayList();
    private ArrayList columnLabels = new ArrayList();
    private int[] columnType;

    
    public BinaryFileReader () {
    }


    /**
     * Reads a binary file containing serialized objects that make up a TableDataSet
     * object.
     * 
     * @param file  name of file which contains the binary data 
     * @return a TableDataSet object 
     * 
     * @throws IOException when the file is not found
     */
    public TableDataSet readFile(File file) throws IOException {

        TableDataSet table = null;

        try {
            logger.debug("Opening file: "+file);

            //Open the file
            ObjectInput inStream = new ObjectInputStream(new FileInputStream(file));
        
            //Read magic number
            int magicNumber = inStream.readInt();
            
            //Read number of columns
            int nCols = inStream.readInt();
            columnType = new int[nCols];

            //Read titles
            for (int c=0; c < nCols; c++) {
                columnLabels.add( inStream.readUTF() );
            }
            
            //Read column data
            for (int c=0; c < nCols; c++) {
                Object colObj = inStream.readObject();
                columnData.add( colObj );
            }
            inStream.close();

            table = new TableDataSet();
            table.setName(file.toString());
            for (int i=0; i < nCols; i++) {
                table.appendColumn(columnData.get(i), (String) columnLabels.get(i));
            }
        } 
        catch (ClassNotFoundException e) {
            logger.error("", e);
        }

        return table;
    }


    public TableDataSet readTable(String tableName) throws IOException {
        File fileName = new File (getMyDirectory().getPath() + File.separator + tableName + ".binTable");
        TableDataSet myTable = readFile(fileName);
        myTable.setName(tableName);
        return myTable;
    }


    public void close() {
    }
    
}
