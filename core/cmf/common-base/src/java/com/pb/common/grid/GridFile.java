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

import org.apache.log4j.Logger;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.io.IOException;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.RandomAccessFile;

/**
 * Represents a grid file.
 *
 * Note: All row indexing is zero based. i.e. Row numbers and row data should be accessed
 * starting from zero.
 *
 * @version  1.0, 7/03/03
 * @author   Tim Heier
 *
 */

public class GridFile {

    private static Logger logger = Logger.getLogger("com.pb.common.grid");

    private GridDataBuffer fileBuffer;
    private GridParameters params;

    private ByteBuffer inRowBuffer;
    private ByteBuffer outRowBuffer;
    private ByteBuffer cellBuffer;

    private int wordSizeInBytes;


    private GridFile() {

    }


    GridFile(GridDataBuffer fileBuffer, GridParameters params) {
        this.fileBuffer = fileBuffer;
        this.params = params;

        wordSizeInBytes = params.getWordSizeInBytes();

        inRowBuffer = ByteBuffer.allocateDirect(params.getRowSizeInbytes());
        outRowBuffer = ByteBuffer.allocateDirect(params.getRowSizeInbytes());
        cellBuffer = ByteBuffer.allocateDirect(params.getWordSizeInBytes());
    }


    /** Reads a row of values from a grid file. Overwrites any values that
     * are already in the rowData array. The row values should start in
     * rowData[0].
     *
     * @param rowNumber  row number to store data values. Valid values are
     *                   1..numberOfRows
     * @param rowData values for row. Values should start in rowData[0]
     *
     * @throws IOException
     */
    public void getRow(int rowNumber, int[] rowData) throws IOException {

        if ((rowNumber < 1) || (rowNumber > params.getNumberOfRows())) {
            throw new IndexOutOfBoundsException("rowNumber=" + rowNumber);
        }

        inRowBuffer.clear();
        fileBuffer.getBytesForRow(rowNumber, inRowBuffer);
        inRowBuffer.flip();

        for (int i = 0; i < rowData.length; i++) {
            rowData[i] = getValueFromInRowBuffer();
        }

    }


    /** Stores a row of grid values in a grid file. Overwrites any values
     * already in the grid file with the contents of rowData. The row values
     * should start in rowData[0]
     *
     * @param rowNumber  row number to store data values. Valid values are
     *                   1..numberOfRows
     * @param rowData values for row. Values should start in rowData[0]
     *
     * @throws IOException
     */
    public void putRow(int rowNumber, int[] rowData) throws IOException {

        if ((rowNumber < 1) || (rowNumber > params.getNumberOfRows())) {
            throw new IndexOutOfBoundsException("rowNumber=" + rowNumber);
        }

        outRowBuffer.clear();

        for (int i = 0; i < rowData.length; i++) {
            putValueInOutRowBuffer(rowData[i]);
        }
        outRowBuffer.flip();

        fileBuffer.putBytesForRow(rowNumber, outRowBuffer);

    }


    /** Stores a single value in a grid file. Overwrites the value currently
     * occupied by the specified row/column number.
     *
     * @param rowNumber  row number at which to store the value. Valid values
     *                   are 1..numberOfRows
     * @param columnNumber  column number at which to store the value. Valid
     *                      values are 1..numberOfRows
     * @param cellValue  cell value to store in grid file
     *
     * @throws IOException
     */
    public void putValue(int rowNumber, int columnNumber, int cellValue) throws IOException {

        cellBuffer.clear();
        putValueInCellBuffer(cellValue);
        cellBuffer.flip();

        fileBuffer.putBytesForCell(rowNumber, columnNumber, cellBuffer);
    }


    /** Reads a single value from a grid file. Overwrites the value currently
     * occupied by the specified row/column number.
     *
     * @param rowNumber  row number from which to read the value. Valid values
     *                   are 1..numberOfRows
     * @param columnNumber  column number from which to read the value. Valid
     *                      values are 1..numberOfRows
     * @return requested cell value
     *
     * @throws IOException
     */
    public int getValue(int rowNumber, int columnNumber) throws IOException {

        cellBuffer.clear();
        fileBuffer.getBytesForCell(rowNumber, columnNumber, cellBuffer);
        cellBuffer.flip();

        return getValueFromCellBuffer();
    }


    public int getValueFromInRowBuffer() {

        switch (wordSizeInBytes) {
            case 1:
                return inRowBuffer.get();
            case 2:
                return inRowBuffer.getShort();
            case 4:
                return inRowBuffer.getInt();
            default:
                throw new RuntimeException("Invalid word size: " + params.getWordSizeInBytes());
        }
    }


    public void putValueInOutRowBuffer(int value) {

        switch (wordSizeInBytes) {
            case 1:
                outRowBuffer.put((byte) value);
                break;
            case 2:
                outRowBuffer.putShort((short) value);
                break;
            case 4:
                outRowBuffer.putInt(value);
                break;
            default:
                throw new RuntimeException("Invalid word size: " + params.getWordSizeInBytes());
        }
    }


    public int getValueFromCellBuffer() {

        switch (wordSizeInBytes) {
            case 1:
                return cellBuffer.get();
            case 2:
                return cellBuffer.getShort();
            case 4:
                return cellBuffer.getInt();
            default:
                throw new RuntimeException("Invalid word size: " + params.getWordSizeInBytes());
        }
    }


    public void putValueInCellBuffer(int value) {

        switch (wordSizeInBytes) {
            case 1:
                cellBuffer.put((byte) value);
                break;
            case 2:
                cellBuffer.putShort((short) value);
                break;
            case 4:
                cellBuffer.putInt(value);
                break;
            default:
                throw new RuntimeException("Invalid word size: " + params.getWordSizeInBytes());
        }
    }


    private void fillWithValue(int value) throws IOException {

        long startTime = System.currentTimeMillis();
        logger.debug( "Filling grid with value=" + value);

        //Create an array to hold row data
        int[] rowValues = new int[params.getNumberOfColumns()];

        //Fill row values with value
        for (int i = 0; i < params.getNumberOfColumns(); i++) {
            rowValues[i] = value;
        }

        //Write row values in each row of grid
        for (int i = 1; i <= params.getNumberOfRows(); i++) {
            putRow(i, rowValues);
        }

        long endTime = System.currentTimeMillis();
        logger.debug( "Time to fill grid=" + (endTime - startTime));
    }


    public void close() throws IOException {

        try {
            fileBuffer.close();
        } catch (IOException e) {
            throw e;
        }
    }

    //================================= static factory methods =================================

    public static GridFile open(File file) throws FileNotFoundException {

        logger.debug( "Opening grid file: " + file);

        if (!file.exists()) {
            FileNotFoundException e = new FileNotFoundException(file.getAbsolutePath());
            logger.error("error opening grid file", e);
            throw e;
        }
        GridFile gridFile = openFile(file);
        return gridFile;
    }


    private static GridFile openFile(File file) {

        GridFile gridFile = null;

        try {
            FileChannel channel = new RandomAccessFile(file, "rw").getChannel();
            GridParameters params = readParams(channel);

            GridDataBuffer dataBuffer =
                    new GridDataBuffer(channel, params.getWordSizeInBytes(), params.getRowSizeInbytes());

            gridFile = new GridFile(dataBuffer, params);
        } catch (Exception e) {
            e.printStackTrace();
        }

        return gridFile;
    }


    private static GridParameters readParams(FileChannel channel) throws IOException {

        ByteBuffer buf = ByteBuffer.allocate(GridParameters.HEADER_SIZE);
        channel.read(buf);
        buf.flip();

        //Read each element of the parameter block
        int version = buf.getInt();
        int wordSize = buf.getInt();
        int numberOfRows = buf.getInt();
        int numberOfColumns = buf.getInt();
        double xllCorner = buf.getDouble();
        double yllCorner = buf.getDouble();
        double cellSize = buf.getDouble();
        int noDataValue = buf.getInt();

        int length = buf.getInt();  //length of description

        //Read the description, one character at a time
        StringBuffer sb = new StringBuffer(length);
        for (int i = 0; i < length; i++) {
            sb.append(buf.getChar());
        }
        String description = sb.toString();

        //Create a parameters object
        GridParameters params =
                new GridParameters(numberOfRows, numberOfColumns, xllCorner, yllCorner, cellSize,
                        wordSize, noDataValue, description);

        return params;
    }


    public static GridFile create(File file, GridParameters params) throws IOException {

        //File is not open, delete it
        if (file.exists()) {
            logger.debug( file + " exists, deleting");
            file.delete();
        }

        logger.debug( "Creating grid file: " + file);
        logger.debug( "Size of grid file = " + params.getGridSizeInBytes() + " bytes");

        GridFile gridFile = null;

        try {
            //Create a read-write file and size it
            RandomAccessFile randFile = new RandomAccessFile(file, "rw");
            randFile.setLength(params.getGridSizeInBytes());

            FileChannel channel = randFile.getChannel();

            writeParams(channel, params);
            channel.close();

            gridFile = GridFile.open(file);
            gridFile.fillWithValue(params.getNoDataValue());
        } catch (IOException e) {
            throw e;
        }

        return gridFile;
    }


    private static void writeParams(FileChannel channel, GridParameters params) throws IOException {

        ByteBuffer buf = ByteBuffer.allocate(GridParameters.HEADER_SIZE);

        try {
            channel.position(0);

            //Write each element of the params
            buf.putInt(params.getVersion());
            buf.putInt(params.getWordSizeInBytes());
            buf.putInt(params.getNumberOfRows());
            buf.putInt(params.getNumberOfColumns());
            buf.putDouble(params.getXllCorner());
            buf.putDouble(params.getYllCorner());
            buf.putDouble(params.getCellSize());
            buf.putInt(params.getNoDataValue());

            //Write length of description
            String description = params.getDescription();
            int length = description.length();
            buf.putInt(length);

            //Write the description, one character at a time
            for (int i = 0; i < length; i++) {
                buf.putChar(description.charAt(i));
            }

            buf.flip();
            channel.write(buf);
        } catch (IOException e) {
            throw e;
        }

    }


    public GridParameters getParameters() {
        return params;
    }

}
