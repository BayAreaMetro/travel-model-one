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
import java.util.StringTokenizer;
import java.util.Date;
import org.apache.log4j.Logger;

/**
 * Assumes that the first 6 rows of the ASCII file contain the parameters needed to define
 * the Grid File.  We also assume that the order of those parameters is ncols, nrows, xllcorner,
 * yllcorner,cellsize and nodata_value.
 *
 * @author Chrsiti Willison
 * @version Oct 15, 2003
 * Created by IntelliJ.
 *  */

public class ConvertASCIItoGridFile {

    protected static Logger logger = Logger.getLogger("com.pb.common.grid");
    protected static final int REPORTING_INTERVAL = 1000;

    private static double getDoubleParameter (String key, String s) {
        double value = Double.NaN;
        StringTokenizer st = new StringTokenizer(s," ");
        String nt = st.nextToken();
        if (nt.equalsIgnoreCase(key))
            value = Double.parseDouble(st.nextToken());
        else {
            logger.error("Error: Expecting double keyword \""+key+"\""+ " but found \""+ nt+"\"");
            System.exit(12);
        }
        return value;
    }
    private static int getIntParameter (String key, String s) {
        int value=-9999;
        StringTokenizer st = new StringTokenizer(s," ");
        String nt = st.nextToken();
        if (nt.equalsIgnoreCase(key))
            value = Integer.parseInt(st.nextToken());
        else {
            logger.error("Error: Expecting int keyword \""+key+"\""+ " but found \""+ nt+"\"");
            System.exit(12);
        }
        return value;
  }

//    The method for creating GridFileParameters requires that wordSizeInBytes
//    is an integer and must be either 1,2 or 4.
//    (short = 16 bits = 2 bytes; int = 32 bits = 4 bytes).
    private static GridParameters readHeaderRows(BufferedReader reader){
        int nrows=-9999, ncols=-9999, nodata_value=-9999, wordsize=2;
        double xllcorner=221891.972108, yllcorner=-943468.337502, cellsize=Double.NaN;
        try {
            ncols = getIntParameter("ncols", reader.readLine());
            nrows = getIntParameter("nrows", reader.readLine()); //subtract out number of header rows
//            xllcorner = getDoubleParameter("xllcorner", reader.readLine());  there is a floating point representation error
//            yllcorner = getDoubleParameter("yllcorner", reader.readLine());  for these numbers and so we need to hard code for now 2/18/04
            cellsize = getDoubleParameter("cellsize", reader.readLine());
            nodata_value = getIntParameter("NODATA_value", reader.readLine());
        } catch (IOException e) {
            e.printStackTrace();
        }
        return (new GridParameters(nrows,ncols,xllcorner,yllcorner,cellsize,wordsize,nodata_value,""));
    }

    private static void transferData(BufferedReader reader,GridFile gridFile){

         for (int r=0; r<gridFile.getParameters().getNumberOfRows(); r++) {
            int[] rowData = new int[gridFile.getParameters().getNumberOfColumns()];
            String s = null;
            try {
                s = reader.readLine();
            } catch (IOException e1) {
                e1.printStackTrace();
            }
            if(s==null){
                System.err.println("No new line to read. "+(r+1)+" rows converted");
                System.exit(12);
            }
            StringTokenizer st = new StringTokenizer(s, " ");
            int column = 0;
            while(st.hasMoreTokens()){
                int i = Integer.parseInt(st.nextToken());
            // Handle cases where the value is too small or large to be stored
            // as short
                if (i<(int)Short.MIN_VALUE) rowData[column]= gridFile.getParameters().getNoDataValue();
                else if (i>(int)Short.MAX_VALUE) rowData[column]= gridFile.getParameters().getNoDataValue();
                else rowData[column]=i;
                column++;
             }
//  Check to make sure that each row has data values in every column
             if(column != gridFile.getParameters().getNumberOfColumns())
                        logger.warn("In Row Number: "+ (r+1) +" there are only " +column+" values, "
                                + "expecting " +gridFile.getParameters().getNumberOfColumns());

        // Tell us where we're at every once in a while
            if (r>0 & r%REPORTING_INTERVAL == 0) logger.info("At row number "+ (r+1) +"\n"+ s.substring(0,20));
             //put the row of values into the gridfile.
            try {
                    gridFile.putRow(r+1,rowData);
                } catch (IOException e1) {
                    e1.printStackTrace();
                }
        }
    }

//  Takes 2 arguments.  args[0] = name of the ASCII file to be converted
//                      args[1] = name of the Grid file that will be created.  Should have .grid extension
    public static void main(String[] args) {
        logger.info(new Date().toString());
        BufferedReader br = null;
        try {
            br = new BufferedReader(new FileReader(args[0]));
        } catch (FileNotFoundException e1) {
            e1.printStackTrace();
        }
        String gridFileName = args[1];
//  Read the parameters from the ASCII file that are needed to create a GridFile
        GridParameters params = readHeaderRows(br);
        logger.info("Header from file "+ args[0] + ": \n" +
                "rows " + params.getNumberOfRows() + "\n" +
                "cols " + params.getNumberOfColumns() + "\n" +
                "xllcorner " + params.getXllCorner() + "\n" +
                "yllcorner " + params.getYllCorner() + "\n" +
                "cellsize " + params.getCellSize() + "\n" +
                "nodata_value " + params.getNoDataValue());
// A grid file will now be created with these parameters and filled with the nodata_value.
        GridFile gridFile = null;
        try {
            gridFile = GridFile.create(new File(gridFileName),params);
        } catch (IOException e) {
            e.printStackTrace();
        }
//  Now fill it with the data from the ASCII file
        transferData(br,gridFile);

//  Close Grid File
        try {
            gridFile.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
        logger.info(new Date().toString());
    }

}
