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
package com.pb.common.grid.tests;

import com.pb.common.grid.GridFile;
import com.pb.common.grid.GridParameters;

import java.io.File;
import java.io.IOException;

/**
 * Tests the GridFile class.
 *
 * @author    Tim Heier
 * @version   1.0, 7/03/03
 */
public class GridFileTest {

    public static File TEST_FILE = new File("test.grid");

    public static int NUMBER_ROWS = 30141;
    public static int NUMBER_COLUMNS = 26848;
    public static int CELL_SIZE = 100;
    

    public static void main(String[] args) {

        GridFileTest.testCreateGridFile();
        GridFileTest.testAddDataToGridFile();

        //Surround with try/catch to avoid catching exceptions within the method
        try {
            GridFileTest.testReadGridFile();
        } catch (IOException e) {
            e.printStackTrace();
        }

        try {
            GridFileTest.testReadWriteCells();
        } catch (IOException e) {
            e.printStackTrace();
        }

        //Measures the amount of time it takes to read an entire grid file
        GridFileTest.testReadingGridFileRowWise();
        //GridFileTest.testReadingGridFileCellWise();
    }


    /**
     * Create a grid file for testing.
     */
    public static void testCreateGridFile() {

        System.out.println("\n--------- Creating Grid File ---------");

        //Create a params for the grid file
        GridParameters params =
                new GridParameters(NUMBER_ROWS, NUMBER_COLUMNS, 1.0, 1.0, CELL_SIZE, 
                                    "Created by com.pb.common.grid.GridFileTest");

        try {
            GridFile gridFile = GridFile.create(TEST_FILE, params);  //Create the grid file
            gridFile.close();
        } catch (IOException e) {
            e.printStackTrace();
        }

    }


    /**
     * Create a grid file for testing.
     */
    public static void testAddDataToGridFile() {

        System.out.println("\n--------- Adding Data to Grid File ---------");

        GridFile gridFile = null;

        try {
            gridFile = GridFile.open(TEST_FILE);
        } catch (IOException e) {
            e.printStackTrace();
        }

        GridParameters params = gridFile.getParameters();

        //Create a row and put some data in it
        int[] rowValues = new int[params.getNumberOfColumns()];
        for (int i = 0; i < rowValues.length; i++) {
            rowValues[i] = i;
        }

        try {
            gridFile.putRow(2, rowValues);  //store values in row 10
        } catch (IOException e) {
            e.printStackTrace();
        }

    }


    /**
     * Open a grid file for reading.
     */
    public static void testReadGridFile() throws IOException {

        System.out.println("\n--------- Reading Grid File ---------");

        GridFile gridFile = GridFile.open(TEST_FILE);

        GridParameters params = gridFile.getParameters();

        System.out.println("Number of Rows: " + params.getNumberOfRows());
        System.out.println("Number of Columns: " + params.getNumberOfColumns());
        System.out.println("Lower Left X Corner: " + params.getXllCorner());
        System.out.println("Lower Left Y Corner: " + params.getYllCorner());
        System.out.println("No Data Value: " + params.getNoDataValue());
        System.out.println("Word Size: " + params.getWordSizeInBytes() + " bytes");
        System.out.println("Description: " + params.getDescription());

        //Create an array to hold row data
        int[] rowValues = new int[params.getNumberOfColumns()];

        //Read values in row 1 and print the first 10
        gridFile.getRow(1, rowValues);

        for (int i = 0; i < 10; i++) {
            System.out.println("row[" + i + "] = " + rowValues[i]);
        }

        //Read values in row 2 and print the first 10
        gridFile.getRow(2, rowValues);

        for (int i = 0; i < 10; i++) {
            System.out.println("row[" + i + "] = " + rowValues[i]);
        }

        gridFile.close();
    }

    /**
     * Open a grid file for reading.
     */
    public static void testReadWriteCells() throws IOException {

        System.out.println("\n--------- Reading/Writing Grid Cells ---------");

        GridFile gridFile = GridFile.open(TEST_FILE);

        int cellValue;

        //Write/Read a couple of cell values
        cellValue = 100;

        gridFile.putValue(1, NUMBER_COLUMNS, cellValue);

        cellValue = gridFile.getValue(1, NUMBER_COLUMNS);

        System.out.println("row[1," + NUMBER_COLUMNS + "] = " + cellValue);

        // -----------------------------------------------------------------------
        cellValue = 200;

        gridFile.putValue(NUMBER_ROWS, NUMBER_COLUMNS, cellValue);

        cellValue = gridFile.getValue(NUMBER_ROWS, NUMBER_COLUMNS);

        System.out.println("row[" + NUMBER_ROWS + "," + NUMBER_COLUMNS + "] = " + cellValue);

        gridFile.close();
    }


    public static void testReadingGridFileRowWise() {

        System.out.println("\n--------- Reading Grid File Row Wise ---------");

        try {
            GridFile gridFile = GridFile.open(TEST_FILE);

            GridParameters params = gridFile.getParameters();

            //Create an array to hold row data
            int[] rowValues = new int[params.getNumberOfColumns()];

            long startTime = System.currentTimeMillis();

            //Looping by row is the fastest way to read through a grid file
            for (int i = 1; i <= params.getNumberOfRows(); i++) {
                gridFile.getRow(i, rowValues);
            }

            long endTime = System.currentTimeMillis();

            System.out.println("elapsed time = " + (endTime - startTime) + " ms");

            gridFile.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void testReadingGridFileCellWise() {

        System.out.println("\n--------- Reading Grid File Cell Wise ---------");

        try {
            GridFile gridFile = GridFile.open(TEST_FILE);

            GridParameters params = gridFile.getParameters();

            int cellValue;

            long startTime = System.currentTimeMillis();

            //This is about the slowest way to read a grid file
            for (int i = 1; i <= params.getNumberOfRows(); i++) {
                for (int j = 1; j <= params.getNumberOfColumns(); j++) {
                    cellValue = gridFile.getValue(i, j);
                }
            }

            long endTime = System.currentTimeMillis();

            System.out.println("elapsed time = " + (endTime - startTime) + " ms");

            gridFile.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

}

/****** WORD SIZE = 2

 --------- Creating Grid File ---------
 FINE, test.grid exists, deleting
 FINE, Creating grid file: test.grid
 FINE, Size of grid file = 1618452160 bytes
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 2
 FINE, rowSizeInBytes: 53696
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 FINE, Filling grid with value=-1
 FINE, Time to fill grid=68063
 FINE, Opening grid file: test.grid

 --------- Adding Data to Grid File ---------
 FINE, wordSizeInBytes: 2
 FINE, rowSizeInBytes: 53696
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer

 --------- Reading Grid File ---------
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 2
 FINE, rowSizeInBytes: 53696
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 Number of Rows: 30141
 Number of Columns: 26848
 Lower Left X Corner: 1.0
 Lower Left Y Corner: 1.0
 No Data Value: -1
 Word Size: 2 bytes
 Description: Created by com.pb.common.grid.GridFileTest
 row[0] = -1
 row[1] = -1
 row[2] = -1
 row[3] = -1
 row[4] = -1
 row[5] = -1
 row[6] = -1
 row[7] = -1
 row[8] = -1
 row[9] = -1
 row[0] = 0
 row[1] = 1
 row[2] = 2
 row[3] = 3
 row[4] = 4
 row[5] = 5
 row[6] = 6
 row[7] = 7
 row[8] = 8
 row[9] = 9

 --------- Reading/Writing Grid Cells ---------
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 2
 FINE, rowSizeInBytes: 53696
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 row[1,26848] = 100
 row[30141,26848] = 200

 --------- Reading Grid File Row Wise ---------
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 2
 FINE, rowSizeInBytes: 53696
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 elapsed time = 92640 ms
 Process terminated with exit code 0
 */


/****** WORD SIZE = 4

 --------- Creating Grid File ---------
 FINE, test.grid exists, deleting
 FINE, Creating grid file: test.grid
 FINE, Size of grid file = 3236903296 bytes
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 4
 FINE, rowSizeInBytes: 107392
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 FINE, Filling grid with value=-1
 FINE, Time to fill grid=183656
 FINE, Opening grid file: test.grid

 --------- Adding Data to Grid File ---------
 FINE, wordSizeInBytes: 4
 FINE, rowSizeInBytes: 107392
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer

 --------- Reading Grid File ---------
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 4
 FINE, rowSizeInBytes: 107392
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 Number of Rows: 30141
 Number of Columns: 26848
 Lower Left X Corner: 1.0
 Lower Left Y Corner: 1.0
 No Data Value: -1
 Word Size: 4 bytes
 Description: Created by com.pb.common.grid.GridFileTest
 row[0] = -1
 row[1] = -1
 row[2] = -1
 row[3] = -1
 row[4] = -1
 row[5] = -1
 row[6] = -1
 row[7] = -1
 row[8] = -1
 row[9] = -1
 row[0] = 0
 row[1] = 1
 row[2] = 2
 row[3] = 3
 row[4] = 4
 row[5] = 5
 row[6] = 6
 row[7] = 7
 row[8] = 8
 row[9] = 9

 --------- Reading/Writing Grid Cells ---------
 FINE, Opening grid file: test.grid
 FINE, wordSizeInBytes: 4
 FINE, rowSizeInBytes: 107392
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 row[1,26848] = 100
 row[30141,26848] = 200

 FINE, Opening grid file: test.grid
 --------- Reading Grid File Row Wise ---------
 FINE, wordSizeInBytes: 4
 FINE, rowSizeInBytes: 107392
 FINE, numberOfRowsToBuffer: 10
 FINE, Initializing row buffer
 elapsed time = 162422 ms
 */