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
package com.pb.common.datafile;

import java.io.DataInput;
import java.io.DataOutput;
import java.io.IOException;

public class DataHeader {
    
    /**
     * File pointer to the first byte of record data (8 bytes).
     */
    protected long dataPointer;

    /**
     * Actual number of bytes of data held in this record (4 bytes).
     */
    protected int dataCount;

    /**
     * Number of bytes of data that this record can hold (4 bytes).
     */
    protected int dataCapacity;

    /**
     * Indicates this header's position in the file index.
     */
    protected int indexPosition;

    protected DataHeader() {
    }


    protected DataHeader(long dataPointer, int dataCapacity) {
        if (dataCapacity < 1) {
            throw new IllegalArgumentException("Bad record size: " + dataCapacity);
        }

        this.dataPointer = dataPointer;
        this.dataCapacity = dataCapacity;
        this.dataCount = 0;
    }

    protected int getIndexPosition() {
        return indexPosition;
    }


    protected void setIndexPosition(int indexPosition) {
        this.indexPosition = indexPosition;
    }


    protected int getDataCapacity() {
        return dataCapacity;
    }


    protected int getFreeSpace() {
        return dataCapacity - dataCount;
    }


    protected void read(DataInput in) throws IOException {
        dataPointer = in.readLong();
        dataCapacity = in.readInt();
        dataCount = in.readInt();
    }


    protected void write(DataOutput out) throws IOException {
        out.writeLong(dataPointer);
        out.writeInt(dataCapacity);
        out.writeInt(dataCount);
    }


    protected static DataHeader readHeader(DataInput in) throws IOException {
        DataHeader r = new DataHeader();

        r.read(in);

        return r;
    }


    /**
     * Returns a new record header which occupies the free space of this record.
     * Shrinks this record size by the size of its free space.
     */
    protected DataHeader split() {
        long newFp = dataPointer + (long) dataCount;
        DataHeader newData = new DataHeader(newFp, getFreeSpace());

        dataCapacity = dataCount;

        return newData;
    }
}
