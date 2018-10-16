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
 * A very simple binary grid manager for the Despair framework that undoubtedly
 * will be overhauled by Tim as soon as he gets ahold of it. The header contains
 * both ints and doubles, but the cell values are short ints.
 *
 * @version  0.9, 04/07/03
 * @author   rdonnelly@pbtfsc.com
 *
 * @deprecated  This class is deprecated in favor of the GridFile class.
 */

public class GridManager {
    private final static int HEADER_SIZE = 36;  // size in bytes
    private final static int DATA_RECORD_SIZE = 2;   // size in bytes (short)
    private int nrows, ncols, nodata_value;
    private double xllcorner, yllcorner, cellsize;
    private RandomAccessFile rf;

    // GridManager (String filename) { GridManagerX0(filename, "r"); }
    public GridManager(String filename, String filemode) {
        try {
            // Open the file in the requested mode
            rf = new RandomAccessFile(filename, filemode);
            // Extract the header, assuming for now that all values are valid
            nrows = rf.readInt();
            ncols = rf.readInt();
            xllcorner = rf.readDouble();
            yllcorner = rf.readDouble();
            cellsize = rf.readDouble();
            nodata_value = rf.readInt();
            // At this point the file is ready for processing
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void close() {
        try {
            rf.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public int getCellValue(int targetRow, int targetColumn) {
        int cellValue = -1;  // returning this would be bad
        // Calc offset in bytes (include header) from beginning of file
        int offset = ((targetRow * ncols) * DATA_RECORD_SIZE) + (targetColumn *
                DATA_RECORD_SIZE) + HEADER_SIZE;
//        System.out.println("getCell(" + targetRow + "," + targetColumn +
//                ") calculated offset=" + offset);
        try {
            rf.seek((long) offset);
            cellValue = rf.readShort();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return cellValue;
    }

    public void putCellValue(int targetRow, int targetColumn, int cellValue) {
        // Calc offset in bytes (include header) from beginning of file
        int offset = ((targetRow * ncols) * DATA_RECORD_SIZE) + (targetColumn *
                DATA_RECORD_SIZE) + HEADER_SIZE;
//        System.out.println("getCell(" + targetRow + "," + targetColumn +
//                ") calculated offset=" + offset);
        try {
            rf.seek((long) offset);
            rf.writeShort(cellValue);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public String getHeader() {
        return "r=" + nrows + " c=" + ncols + " x=" + xllcorner + " y=" + yllcorner + " s=" +
                cellsize + " NA=" + nodata_value;
    }

    public int getNcols() {
        return ncols;
    }

    public int getNrows() {
        return nrows;
    }

    public int[] getRow(int irow) {
        int[] r = new int[ncols];
        // Calc offset in bytes (include header) from beginning of file
        int offset = ((irow * ncols) * DATA_RECORD_SIZE) + HEADER_SIZE;
        //System.out.println("getRow("+irow+") calculated offset="+offset);
        try {
            rf.seek((long) offset);
            for (int p = 0; p < ncols; p++)
                r[p] = rf.readShort();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return r;
    }

    public void putHeader() {
        try {
            rf.seek((long) 0);
            rf.writeInt(nrows);
            rf.writeInt(ncols);
            rf.writeDouble(xllcorner);
            rf.writeDouble(yllcorner);
            rf.writeDouble(cellsize);
            rf.writeInt(nodata_value);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void putRow(int[] i) {
        try {
            int size = i.length;
            for (int p = 0; p < ncols; p++)
                rf.writeShort(i[p]);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void putRow(int[] i, int targetRow) {
        try {
            int size = i.length;
            // Calc the offset needed to start in column 0 of the desired row
            int offset = ((targetRow * ncols) * DATA_RECORD_SIZE) + HEADER_SIZE;
            rf.seek((long) offset);
            for (int p = 0; p < ncols; p++)
                rf.writeShort(i[p]);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public static void main(String[] args) {
        String filename = "test.raf";
        GridManager g = new GridManager(filename, "rw");
        System.out.println(filename + ": " + g.getHeader());

        // Try reading the sixth row of data (remember that Java starts array
        // subscript numbering at zero)
        int[] i = new int[g.getNcols()];
        int targetRow = 5;
        i = g.getRow(targetRow);
        System.out.println("Data from row 6:");
        for (int p = 0; p < g.getNcols(); p++)
            System.out.println("  i[" + p + "]=" + i[p]);

        // Try reading the first column of the seventh row
        System.out.println();
        System.out.println("First column, seventh row=" + g.getCellValue(6, 0));

        // What happens if we try to write to it?
        g.putHeader();
        g.close();

    }

}
