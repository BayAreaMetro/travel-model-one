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
package com.pb.common.util;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

/**
 * Copied from the OLD_CSVFileReader class to
 * be used by anyone.
 * 
 * @author Christi Willison 
 * @version 1.0, May 23, 2006
 */
public class FileUtil {
    
    /**
     * Helper method to find the number of lines in a text file.
     * 
     * @return total number of lines in file
     * 
     */
    public static int findNumberOfLinesInFile(File file) {
        int numberOfRows = 0;
        
        try {
            BufferedReader stream = new BufferedReader( new FileReader(file) );
            while (stream.readLine() != null) {
                numberOfRows++;
            }
            stream.close();
        }
        catch (IOException e) {
            throw new RuntimeException("Can't read from file " + file, e);
        }
        
        return numberOfRows;
    }

}
