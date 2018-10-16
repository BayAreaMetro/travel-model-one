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
package com.pb.models.synpopV3;

import java.io.File;
import java.io.IOException;
import java.util.Hashtable;

import org.apache.log4j.Logger;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;

/**
 * @author Erhardt
 * @version 1.0 Oct 13, 2006
 *
 */
public class BasicTazData implements TazData {

    protected static Logger logger = Logger.getLogger("com.pb.models.synpopV3");

    TableDataSet tazTable;    
    Hashtable<Integer, Integer> indexedHouseholds; 
    
    /**
     * 
     * @param tazFileProperty   The name of the property to read containing the file name.
     * @param hhColumnProperty The name of the property storing the name of the households column.  
     */
    public BasicTazData(String tazFileProperty, String hhColumnProperty) {
        
        // read the properties
        String tazFile = PropertyParser.getPropertyByName(tazFileProperty);
        String hhColumn       = PropertyParser.getPropertyByName(hhColumnProperty);
        
        // read the table
        tazTable = new TableDataSet();        
        try{
            CSVFileReader CSVReader = new CSVFileReader();
            tazTable = CSVReader.readFile(new File(tazFile));
        } catch (IOException e){
            logger.error("Unable to read taz file:" + tazFile);
        }
        
        // create a hashtable with the taz id and number of households
        indexedHouseholds = new Hashtable<Integer, Integer>();
        int[] tazIds = tazTable.getColumnAsInt("TAZ");
        int[] hh     = tazTable.getColumnAsInt(hhColumn);
        for (int i=0; i<tazIds.length; i++) {
            indexedHouseholds.put(new Integer(tazIds[i]), new Integer(hh[i]));
        }
        
    }
    
    /** 
     * @see com.pb.models.synpopV3.TazData#getNumberOfHouseholds(int)
     */
    public int getNumberOfHouseholds(int tazNumber) {
        if (!(indexedHouseholds.containsKey(new Integer(tazNumber)))) {
            throw new RuntimeException("ERROR: Problem with TAZ " + tazNumber); 
        }        
        Integer households = indexedHouseholds.get(new Integer(tazNumber));        
        return households.intValue();
    }

}
