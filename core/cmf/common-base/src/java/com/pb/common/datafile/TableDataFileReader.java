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
 * Defines a general class used to read table data from files. To read from a JDBC 
 * source, the JDBCTableReader class should be used directly.
 *
 * @author    Tim Heier
 * @version   1.0, 5/08/2004
 */
public abstract class TableDataFileReader extends TableDataReader {


    private File myDirectory;
    
    
    /** Factory method to create a concrete TableDataReader class based on a file type.
     *
     * @param type a type-safe enumeration of file types.
     * @return a concrete TableDataReader.
     * @throws Exception when a file reader cannot be determined
     */
    public static TableDataFileReader createReader(FileType type) {

        TableDataFileReader reader = null;

        if (type.equals(FileType.BINARY)) {
            reader = new BinaryFileReader();
        }
        else
		if  (type.equals(FileType.CSV)) {
            reader = new CSVFileReader();
        }
        else {
            throw new RuntimeException("Invalid file type: "+ type);
        }
        return reader;
    }


    /** Factory method to create a concrete TableDataReader class based on a file.
     *
     * @param file the physical file containing the table data.
     * @return a concrete TableDataReader.
     * @throws Exception when a file reader cannot be determined
     */
    public static TableDataFileReader createReader(File file) {

        TableDataFileReader reader = null;

        String fileName = file.getName();
        
        if ( fileName.endsWith(".bin") || fileName.endsWith(".binary") ) {
            reader = new BinaryFileReader();
        }
        else
        if ( fileName.endsWith(".csv") ) {
            reader = new CSVFileReader();
        }
        else {
            throw new RuntimeException("Could not determine file type for: "+ fileName);
        }
        return reader;
    }

    
    /**
     * All concrete TableDataReader classes must implement this method.
     *
     * @param file physical location of matrix in file.
     * @return the TableDataSet read.
     * @throws IOException
     */
    abstract public TableDataSet readFile(File file) throws IOException;
    
    
    public void setMyDirectory(File myDirectory) {
        this.myDirectory = myDirectory;
    }


    public  File getMyDirectory() {
        return myDirectory;
    }
    
    
    
}
