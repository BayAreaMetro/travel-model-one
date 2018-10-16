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

import com.pb.common.util.ResourceUtil;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.ResourceBundle;


/**
 * TableDataSetLoader: A helper class that has a method that
 * returns a TableDataSet from a csv file
 *
 * @author Freedman
 * @version Aug 11, 2004
 * 
 */
public class TableDataSetLoader {

    protected static Logger logger = Logger.getLogger(TableDataSetLoader.class);

    private TableDataSetLoader(){}
    /**
      * A helper method that returns a TableDataSet
      * @param rb Contains the key pathName that points to the table to load
      * @param pathName  The path/filename to load into memory
      * @return the table read by the method or null if no table found
      */
     public static TableDataSet loadTableDataSet(ResourceBundle rb,String pathName) {
         String path = ResourceUtil.getProperty(rb, pathName);
         TableDataSet table =null;
         try {
             CSVFileReader reader = new CSVFileReader();
             table = reader.readFile(new File(path));

         } catch (IOException e) {
            throw new RuntimeException("Can't find input table "+path, e);
         }
         return table;
     }

}
