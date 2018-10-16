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
import java.io.IOException;

/**
 * Defines a general class used to write table data to files. To write to a JDBC 
 * source, the JDBCTableWriter class should be used directly.
 *
 * @author    Tim Heier
 * @version   1.0, 5/08/2004
 */
public abstract class TableDataFileWriter extends TableDataWriter {


    /** Factory method to create a concrete TableDataWriter class based on a file type.
     *
     * @param type a type-safe enumeration of file types.
     * @return a concrete TableDataWriter.
     */
    public static TableDataFileWriter createWriter(FileType type) {

        TableDataFileWriter writer = null;

        if (type.equals(FileType.BINARY)) {
            writer = new BinaryFileWriter();
        }
        else
		if  (type.equals(FileType.CSV)) {
            writer = new CSVFileWriter();
        }
        else {
            throw new RuntimeException("Invalid file type: "+ type);
        }
        return writer;
    }


    /** Factory method to create a concrete TableDataReader class based on a file.
     *
     * @param file the physical file containing the table data.
     * @return a concrete TableDataReader.
     */
    public static TableDataFileWriter createReader(File file) {

        TableDataFileWriter writer = null;

        String fileName = file.getName();
        
        if ( fileName.endsWith(".bin") || fileName.endsWith(".binary") ) {
            writer = new BinaryFileWriter();
        }
        else
        if ( fileName.endsWith(".csv") ) {
            writer = new CSVFileWriter();
        }
        else {
            throw new RuntimeException("Could not determine file type for: "+ fileName);
        }
        return writer;
    }

    
    /**
     * All concrete TableDataWriter classes must implement this method.
     *
     * @param tableData instance of TableDataSet to write.
     * @param file physical location of matrix in file.
     * @throws IOException
     */
    abstract public void writeFile(TableDataSet tableData, File file) throws IOException;

    private File myDirectory;
    
    public void setMyDirectory(File myDirectory) {
        this.myDirectory = myDirectory;
    }


    protected File getMyDirectory() {
        return myDirectory;
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#readTable(java.lang.String)
     */
    
}
