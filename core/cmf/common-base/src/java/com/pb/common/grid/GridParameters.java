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
package com.pb.common.grid;

/**
 * Represents the parameters of a grid. These are essentially the header elemments in
 * a grid file.
 *
 * @version  1.0, 7/03/03
 * @author   Tim Heier
 *
 */
public class GridParameters {

    public static final int  VERSION = 1;
    public static final int  DEFAULT_NODATA_VALUE = -1;
    public static final int  DEFAULT_WORD_SIZE = 2;  //in bytes
    public static final int  HEADER_SIZE = 1024;

    //Fixed header elements - 36 bytes
    private int version;
    private int wordSizeInBytes;
    private int numberOfRows;
    private int numberOfColumns;
    private double xllCorner;
    private double yllCorner;
    private double cellSize;
    private int noDataValue = -1;

    private String description = "";  //Not part of fixed 36 bytes

    private int rowSizeInBytes;    //calculated value


    private GridParameters() { }


    /** Convenience constructor. Allows for the minimal set of attributes to create a
     * grid file.
     *
     * @param numberOfRows
     * @param numberOfColumns
     * @param xllCorner
     * @param yllCorner
     * @param cellSize
     */
    public GridParameters(int numberOfRows, int numberOfColumns, double xllCorner, double yllCorner, 
                            double cellSize) {

        this(numberOfRows, numberOfColumns, xllCorner, yllCorner, cellSize, DEFAULT_WORD_SIZE, DEFAULT_NODATA_VALUE, "n/a");
    }

    /** Convenience constructor. Allows for the minimal set of attributes to create a
     * grid file plus a description (which is optional)
     *
     * @param numberOfRows
     * @param numberOfColumns
     * @param xllCorner
     * @param yllCorner
     * @param cellSize
     * @param description
     */

    public GridParameters(int numberOfRows, int numberOfColumns, double xllCorner, double yllCorner, 
                            double cellSize, String description) {

        this(numberOfRows, numberOfColumns, xllCorner, yllCorner, cellSize, DEFAULT_WORD_SIZE, DEFAULT_NODATA_VALUE, description);
    }

    /** Full constructor which exposes all values in this object.
     *
     * @param numberOfRows
     * @param numberOfColumns
     * @param xllCorner
     * @param yllCorner
     * @param cellSize
     * @param wordSizeInBytes
     * @param noDataValue
     * @param description
     */
    public GridParameters(int numberOfRows, int numberOfColumns, double xllCorner, double yllCorner,
                              double cellSize, int wordSizeInBytes, int noDataValue, String description) {

        this.numberOfRows = numberOfRows;
        this.numberOfColumns = numberOfColumns;
        this.xllCorner = xllCorner;
        this.yllCorner = yllCorner;
        this.cellSize = cellSize;
        this.wordSizeInBytes = wordSizeInBytes;
        this.noDataValue = noDataValue;

        if (description != null) {
            //limit length to 768 bytes
            if (description.length() > 768)
                description = description.substring(0, 768);

            this.description = description;
        }

        //set calculated values
        this.rowSizeInBytes = wordSizeInBytes * numberOfColumns;
    }


    public int getVersion() {
        return version;
    }

    public int getWordSizeInBytes() {
        return wordSizeInBytes;
    }

    public int getNumberOfRows() {
        return numberOfRows;
    }

    public int getNumberOfColumns() {
        return numberOfColumns;
    }

    public double getXllCorner() {
        return xllCorner;
    }

    public double getYllCorner() {
        return yllCorner;
    }

    public int getNoDataValue() {
        return noDataValue;
    }

    public String getDescription() {
        return description;
    }

    public int getRowSizeInbytes() {
        return rowSizeInBytes;
    }

    public long getGridSizeInBytes() {
        return (long)HEADER_SIZE + ((long)rowSizeInBytes * (long)numberOfRows);
    }

    public double getCellSize() {
        return cellSize;
    }

}
