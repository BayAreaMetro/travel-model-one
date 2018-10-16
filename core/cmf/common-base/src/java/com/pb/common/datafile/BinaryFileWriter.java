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
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectOutput;
import java.io.ObjectOutputStream;
import java.util.ArrayList;
import org.apache.log4j.Logger;


/**
 * Writes a TableDataSet class to a binary file.
 *
 * @author   Tim Heier
 * @version  1.0, 5/08/2004
 *
 */
public class BinaryFileWriter extends TableDataFileWriter implements DataTypes {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    

    public BinaryFileWriter () {
    }

    
    /**
     * Writes a binary file containing serialized objects that make up a TableDataSet
     * object.
     * 
     * @param tableData  the tabledataset to be written out to file
     * @param file  the file where the data should be written
     * 
     * @throws IOException is thrown when the file cannot be written to
     */
    public void writeFile(TableDataSet tableData, File file) throws IOException {

        //Pull data out of tableData object for convenience
        int nCols = tableData.getColumnCount();
        String[] columnLabels = tableData.getColumnLabels();
        ArrayList columnData = tableData.getColumnData();

        try {
            logger.debug("Opening file: "+file);

            //Create file
            ObjectOutput outStream = new ObjectOutputStream(new FileOutputStream(file));
        
            //Write magic number
            outStream.writeInt(1);
            
            //Write number of columns
            outStream.writeInt( nCols );

            //Write titles
            for (int c=0; c < nCols; c++) {
                outStream.writeUTF( columnLabels[c] );
            }
            
            //Write column data
            for (int c=0; c < nCols; c++) {
                outStream.writeObject( columnData.get(c) );
            }

            outStream.close();
        } 
        catch (IOException e) {
            throw e;
        }
        
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#writeTable(com.pb.common.datafile.TableDataSet, java.lang.String)
     */
    public void writeTable(TableDataSet tableData, String tableName) throws IOException {
        File file = new File (getMyDirectory().getPath() + File.separator + tableName + ".binTable");
        writeFile(tableData, file);
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataWriter#close()
     */
    public void close() {
    }

}
