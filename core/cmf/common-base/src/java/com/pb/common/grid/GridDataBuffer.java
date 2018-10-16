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

import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import org.apache.log4j.Logger;
import java.io.IOException;

/**
 * Represents a buffer which maps to a physical grid file.
 *
 * @version  1.0, 7/03/03
 * @author   Tim Heier
 *
 */

public class GridDataBuffer {

    private static Logger logger = Logger.getLogger("com.pb.common.grid");

    public static int DEFAULT_BUFFERED_ROWS = 10;

    private FileChannel channel;
    private ByteBuffer inputBuffer;

    private int wordSizeInBytes;
    private int rowSizeInBytes;
    private int numberOfRowsToBuffer;
    private int minRowInBuffer = 1;
    private int maxRowInBuffer = 0;


    GridDataBuffer(FileChannel channel, int wordSizeInBytes, int rowSizeInBytes) throws IOException {
        this(channel, wordSizeInBytes, rowSizeInBytes, DEFAULT_BUFFERED_ROWS);
    }


    GridDataBuffer(FileChannel channel, int wordSizeInBytes, int rowSizeInBytes, int numberOfRowsToBuffer)
        throws IOException {

        this.channel = channel;
        this.wordSizeInBytes = wordSizeInBytes;
        this.rowSizeInBytes = rowSizeInBytes;
        this.numberOfRowsToBuffer = numberOfRowsToBuffer;

        logger.debug( "wordSizeInBytes: " + wordSizeInBytes);
        logger.debug( "rowSizeInBytes: " + rowSizeInBytes);
        logger.debug( "numberOfRowsToBuffer: " + numberOfRowsToBuffer);

        this.inputBuffer = ByteBuffer.allocateDirect( rowSizeInBytes * numberOfRowsToBuffer );

        logger.debug( "Initializing row buffer");
        fillBuffer( 1 );
    }


    public void getBytesForRow(int rowNumber, ByteBuffer inBuffer) throws IOException {
        if ( (rowNumber < minRowInBuffer) || (rowNumber > maxRowInBuffer) ) {
            fillBuffer( rowNumber );
        }
        inputBuffer.position( (rowNumber - minRowInBuffer) * rowSizeInBytes );

        for (int i=0; i < inBuffer.limit(); i++) {
            inBuffer.put( inputBuffer.get() );
        }
    }


    public void putBytesForRow(int rowNumber, ByteBuffer outBuffer) throws IOException {

        channel.position( calculateRowOffset(rowNumber) );
        channel.write( outBuffer );
    }


    public void putBytesForCell(int rowNumber, int columnNumber, ByteBuffer cellBuffer) throws IOException {

        channel.position( calculateCellOffset(rowNumber, columnNumber) );
        channel.write( cellBuffer );
    }


    public void getBytesForCell(int rowNumber, int columnNumber, ByteBuffer cellBuffer) throws IOException {

        channel.position( calculateCellOffset(rowNumber, columnNumber) );
        channel.read( cellBuffer );
    }


    private void fillBuffer(int startRow) throws IOException {

        int numRead;
/*
        if (logger.isDebugEnabled()) {
            logger.debug( "row=" + startRow + " not in buffer (minRowInBuffer=" +
                        minRowInBuffer + " maxRowInBuffer=" + maxRowInBuffer + ")");
        }
*/
        minRowInBuffer = startRow;
        maxRowInBuffer = startRow + (numberOfRowsToBuffer-1);
        channel.position( calculateRowOffset(startRow) );
/*
        if (logger.isDebugEnabled()) {
            logger.debug( "buffering " + numberOfRowsToBuffer  + " rows (minRowInBuffer=" +
                        minRowInBuffer + " maxRowInBuffer=" + maxRowInBuffer + ")");
        }
*/
        inputBuffer.clear();
        do {
            numRead = channel.read( inputBuffer );
        } while (numRead > 0);

        inputBuffer.flip();
    }

    /** Calculate row offset in grid file.
     *
     * @param rowNumber
     * @return
     */
    private long calculateRowOffset(int rowNumber) {
        return  (long)GridParameters.HEADER_SIZE +
                ((long)(rowNumber-1) * (long)rowSizeInBytes);
    }


    /** Calculate cell offset in grid file.
     *
     * @param rowNumber
     * @param columnNumber
     * @return
     */
    private long calculateCellOffset(int rowNumber, int columnNumber) {
        return  (long)GridParameters.HEADER_SIZE +
                ((long)(rowNumber-1) * (long)rowSizeInBytes) +
                ((long)(columnNumber-1) * (long)wordSizeInBytes);
    }


    public void close() throws IOException {

        try {
            channel.close();
        }
        catch (IOException e) {
            throw e;
        }
    }

}
