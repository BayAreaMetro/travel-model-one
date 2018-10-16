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
package com.pb.models.censusdata;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.TextFile;

import java.io.File;
import java.io.IOException;

import org.apache.log4j.Logger;


public class Workers {

    private static Logger logger = Logger.getLogger(Workers.class);

    String[] workersLabels = {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9+"
    };



    String[] fixedCategories = {
            "0",
            "1",
            "2",
            "3",
            "4",
            "5+"
    };



    public Workers () {
    }



    // return the number of HH workers categories.
    public int getNumberWorkerCategories() {
        return workersLabels.length;
    }



    // return the workers category index given the pums number of workers code
    // from the pums person record RLABOR field.
    public int getWorkers(int workers) {

        int returnValue=0;

        if ( workers > getNumberWorkerCategories()-1 )
            returnValue = getNumberWorkerCategories()-1;
        else
            returnValue = workers;


        return returnValue;
    }



    // return the workers category label given the index.
    public String getWorkersLabel(int workersIndex) {
        return workersLabels[workersIndex];
    }



    // return all the workers category labels.
    public String[] getWorkersLabels() {
        return workersLabels;
    }



    // return the array of households by number of workers from the named file
    public int[] getWorkersPerHousehold( String fileName, String currentYear ) {


        //read file as text so that first line can be parsed to determine how many columns
        //  this would be bad if this was a big file, but it is not, so we're ok
        int columns = (new TextFile(fileName)).getLine(0).trim().split(",").length;

        String[] columnFormats = new String[columns];
        columnFormats[0] = "STRING";
        for (int i = 1; i < columns; i++) {
            columnFormats[i] = "NUMBER";
        }

        // read the base households by number of workers file into a TableDataSet
        CSVFileReader reader = new CSVFileReader();

        TableDataSet table = null;
        try {
            logger.info("Starting to read the workers per household file...");
            table = reader.readFileWithFormats(new File(fileName),columnFormats);
            logger.info("...finished");
        } catch (IOException e) {
                e.printStackTrace();
                logger.fatal(e);
        }

//        try {
//            logger.info("Starting to read the workers per household file...");
//            table = reader.readFileWithFormats(new File(fileName),
//                    new String[] { "STRING", "NUMBER"} );
//
//            logger.info("...finished");
//        } catch (ArrayIndexOutOfBoundsException e) {
//            try {
//                table = reader.readFileWithFormats( new File( fileName ),
//                    new String[] { "STRING", "NUMBER", "NUMBER", "NUMBER"} );
//            } catch (IOException ee) {
//                ee.printStackTrace();
//                logger.fatal(ee);
//            }
//        } catch (IOException e) {
//                e.printStackTrace();
//                logger.fatal(e);
//        }


        // this table has one row of number of households for each workers per household category
        assert table != null;
        workersLabels = table.getColumnAsString(1);

        // need to make sure table has right column labels
        String columnName = currentYear + "households";
        logger.info("Worker Marginal HHs Column: " + columnName);

        int[] workers;

        try {
            workers = table.getColumnAsInt(columnName);
        } catch (Exception e) {
            logger.warn("Could not find selected worker marginal hhs column; we are using the second column as the default.");
            workers = table.getColumnAsInt(2);
        }

        return workers;
    }


    // return the proportions of worker categories relative to total employed households
    public float[] getWorkersPerHouseholdProportions( int[] workersPerHousehold ) {

        float[] proportions = new float[fixedCategories.length];
        float[] tempWorkers = new float[fixedCategories.length];
        float totalEmployedHouseholds = 0;

        // workers in employed households start at workers category 1
        for (int i=1; i < workersPerHousehold.length; i++) {
            totalEmployedHouseholds += workersPerHousehold[i];
            if (i < fixedCategories.length - 1)
                tempWorkers[i] = workersPerHousehold[i];
            else
                tempWorkers[fixedCategories.length - 1] += workersPerHousehold[i];
        }


        // calculate proportions of workers in employed households
        for (int i=1; i < fixedCategories.length; i++)
            proportions[i] = tempWorkers[i]/totalEmployedHouseholds;

        return proportions;
    }



    // return the array of households by number of workers from the named file
    public double[] getJobsPerWorkerFactors( String fileName, SwIndustry ind ) {

        String[] formats = { "STRING", "NUMBER" };

        // read the base households by number of workers file into a TableDataSet
        CSVFileReader reader = new CSVFileReader();

        TableDataSet table = null;
        try {
            table = reader.readFileWithFormats( new File( fileName ), formats );
        } catch (IOException e) {
            e.printStackTrace();
        }

        // this table has one row of number of households for each workers per household category
        String[] tempIndustryLabels = table.getColumnAsString(1);
        double[] tempFactors = table.getColumnAsDouble(2);
        double[] industryFactors = new double[ind.getMaxIndustryIndex()+1];

        for (int i=0; i < tempIndustryLabels.length; i++) {
            int industryIndex = ind.getIndustryIndexFromLabel( tempIndustryLabels[i] );
            industryFactors[industryIndex] = tempFactors[i];
        }

        return industryFactors;

    }


}

