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

import com.pb.common.datafile.TableDataSet;

import org.apache.log4j.Logger;

/**
 * Contains operations that involve grid files.
 *
 * @version  1.0, 10/25/03
 * @author   Tim Heier
 *
 */
public class GridOperations {

    private static Logger logger = Logger.getLogger("com.pb.common.grid");


    private GridOperations() {

    }


    /**
     * Calculates the distance from a grid cell to the nearest grid cell containing
     * the search value.
     *
     * @param searchFile  grid file to use
     * @param row  row number for cell to search from
     * @param col  column number for cell to search from
     * @param searchValue  value to look for
     *
     * @return  straight line distance from center of beginning grid cell to
     *          the grid cell found with the search value
     */
    public static double calculateDistanceToCell(GridFile searchFile,
                                                 int row,
                                                 int col,
                                                 int searchValue) {

        //Calculate nearest distance here...

        return 0;
    }


    /**
     * Calculate...
     *
     * @param devTypeFile
     * @param sqFeetFile
     * @param alphaZoneFile
     * @param targetAlphaZone
     * @param alphaZoneToGridExtents
     *
     * @return  number of square feet
     */
    public static double calculateSpace(GridFile devTypeFile,
                                        GridFile sqFeetFile,
                                        GridFile alphaZoneFile,
                                        int targetAlphaZone,
                                        TableDataSet alphaZoneToGridExtents
                                        ) {

        //Calculate space here...

        return 0;
    }


    /**
     * Creates a grid file with grid cells listed in the containing grid cells that are
     *
     * @param originalFile
     * @param alphaZoneToGridExtents
     *
     * @return  reference to a grid file with extracted grid cells
     */
    public static GridFile extractGrid(GridFile originalFile,
                                       TableDataSet alphaZoneToGridExtents,
                                       int[] listOfAlphaZones) {

        //Create a new grid file...

        return null;
    }

}
