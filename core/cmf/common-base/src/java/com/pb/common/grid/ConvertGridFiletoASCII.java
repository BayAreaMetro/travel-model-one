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

import java.io.*;

/**
 * Converts a GridFile (.grid) to an ASCII file (.txt) so that is can be viewed
 * by ArcView.
 * 
 * @author  Christi Willison
 * @version Dec 21, 2003
 */
public class ConvertGridFiletoASCII {

    public static void main(String[] args) {
        String gridFileName=args[0];
        String asciiFileName=args[1];

        GridFile fileToConvert=null;
        GridParameters params=null;
        try {
            fileToConvert=GridFile.open(new File(gridFileName));
            params=fileToConvert.getParameters();

            String[] headerText = {"NCOLS","NROWS","XLLCORNER","YLLCORNER","CELLSIZE","NODATA_VALUE"};
            int ncols=params.getNumberOfColumns();
            int nrows=params.getNumberOfRows();
            double xll=params.getXllCorner();
//            double xll=221891.972108;  //normally we would read from the file but in this case the numbers
            double yll=params.getYllCorner();
//            double yll=-943468.337502; //weren't translated correctly so we have to put the value in manually
            double cellsize=params.getCellSize();
            int noData=params.getNoDataValue();
            PrintWriter outStream = null;

            outStream = new PrintWriter (new BufferedWriter( new FileWriter(asciiFileName) ) );

            //Print header
            outStream.println(headerText[0]+" "+ncols);
            outStream.println(headerText[1]+" "+nrows);
            outStream.println(headerText[2]+" "+xll);
            outStream.println(headerText[3]+" "+yll);
            outStream.println(headerText[4]+" "+cellsize);
            outStream.println(headerText[5]+" "+noData);

            //Print data
            for (int r=1;r<=nrows;r++) {
                int[] dataRow = new int[ncols];
                fileToConvert.getRow(r,dataRow);
                for(int c=0;c<dataRow.length-1;c++)
                    outStream.print(dataRow[c]+" ");//print a space after each entry
                outStream.println(dataRow[dataRow.length-1]);//don't want to end the row with space
            }
            outStream.close();
        }catch (IOException e) {
            e.printStackTrace();
        }
    }
}
