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

import java.io.*;

import java.util.Enumeration;

public abstract class BaseDataFile {

    // Total length in bytes of the global database headers.
    protected static final int FILE_HEADERS_REGION_LENGTH = 16;

    // Number of bytes in the record header.
    protected static final int RECORD_HEADER_LENGTH = 16;

    // The length of a key in the index.
    protected static final int MAX_KEY_LENGTH = 64;

    // The total length of one index entry - the key length plus the record header length.
    protected static final int INDEX_ENTRY_LENGTH = MAX_KEY_LENGTH + RECORD_HEADER_LENGTH;

    // File pointer to the num records header.
    protected static final long NUM_RECORDS_HEADER_LOCATION = 0;

    // File pointer to the data start pointer header.
    protected static final long DATA_START_HEADER_LOCATION = 4;

    // The database file.
    private RandomAccessFile file;

    // Current file pointer to the start of the record data.
    protected long dataStartPtr;

    /**
     * Creates a new database file, initializing the appropriate headers. Enough 
     * space is allocated in the index for the specified initial size.
     */
    protected BaseDataFile(String dbPath, int initialSize) throws IOException {
        File f = new File(dbPath);

        //if (f.exists()) {
        //    throw new IOException("Database already exits: " + dbPath);
        //}
        file = new RandomAccessFile(f, "rw");

        // Record Data Region starts were the (i+1)th index entry would start.
        dataStartPtr = indexPositionToKeyFp(initialSize);
        setFileLength(dataStartPtr);
        writeNumRecordsHeader(0);
        writeDataStartPtrHeader(dataStartPtr);
    }


    /**
     * Opens an existing database file and initializes the dataStartPtr. The
     * accessFlags parameter can be "r" or "rw" -- as defined in RandomAccessFile.
     */
    protected BaseDataFile(String dbPath, String accessFlags) throws IOException {
        File f = new File(dbPath);

        if (!f.exists()) {
            throw new IOException("Database not found: " + dbPath);
        }

        file = new RandomAccessFile(f, accessFlags);
        dataStartPtr = readDataStartHeader();
    }

    /**
     * Returns an Enumeration of the keys of all records in the database.
     */
    public abstract Enumeration enumerateKeys();


    /**
     * Returns the number or records in the database.
     */
    public abstract int getNumRecords();


    /**
     * Checks there is a record with the given key.
     */
    public abstract boolean recordExists(String key);


    /**
     * Maps a key to a record header.
     */
    protected abstract DataHeader keyToDataHeader(String key);


    /**
     * Locates space for a new record of dataLength size and initializes a 
     * DataHeader.
     */
    protected abstract DataHeader allocateRecord(String key, int dataLength) throws IOException;


    /**
     * Returns the record to which the target file pointer belongs - meaning the
     * specified location in the file is part of the record data of the DataHeader 
     * which is returned.  Returns null if the location is not part of a record. 
     * (O(n) mem accesses)
     */
    protected abstract DataHeader getRecordAt(long targetFp);


    protected long getFileLength() throws IOException {
        return file.length();
    }


    protected void setFileLength(long l) throws IOException {
        file.setLength(l);
    }


    /**
     * Reads the number of records header from the file.
     */
    protected int readNumRecordsHeader() throws IOException {
        file.seek(NUM_RECORDS_HEADER_LOCATION);

        return file.readInt();
    }


    /**
     * Writes the number of records header to the file.
     */
    protected void writeNumRecordsHeader(int numRecords) throws IOException {
        file.seek(NUM_RECORDS_HEADER_LOCATION);
        file.writeInt(numRecords);
    }


    /**
     * Reads the data start pointer header from the file.
     */
    protected long readDataStartHeader() throws IOException {
        file.seek(DATA_START_HEADER_LOCATION);

        return file.readLong();
    }


    /**
     * Writes the data start pointer header to the file.
     */
    protected void writeDataStartPtrHeader(long dataStartPtr) throws IOException {
        file.seek(DATA_START_HEADER_LOCATION);
        file.writeLong(dataStartPtr);
    }


    /**
     * Returns a file pointer in the index pointing to the first byte
     * in the key located at the given index position.
     */
    protected long indexPositionToKeyFp(int pos) {
        return FILE_HEADERS_REGION_LENGTH + (INDEX_ENTRY_LENGTH * pos);
    }


    /**
     * Returns a file pointer in the index pointing to the first byte
     * in the record pointer located at the given index position.
     */
    long indexPositionToDataHeaderFp(int pos) {
        return indexPositionToKeyFp(pos) + MAX_KEY_LENGTH;
    }


    /**
     * Reads the ith key from the index.
     */
    String readKeyFromIndex(int position) throws IOException {
        file.seek(indexPositionToKeyFp(position));

        return file.readUTF();
    }


    /**
     * Reads the ith record header from the index.
     */
    DataHeader readDataHeaderFromIndex(int position) throws IOException {
        file.seek(indexPositionToDataHeaderFp(position));

        return DataHeader.readHeader(file);
    }


    /**
     * Writes the ith record header to the index.
     */
    protected void writeDataHeaderToIndex(DataHeader header) throws IOException {
        file.seek(indexPositionToDataHeaderFp(header.indexPosition));
        header.write(file);
    }


    /**
     * Appends an entry to end of index. Assumes that insureIndexSpace() has 
     * already been called.
     */
    protected void addEntryToIndex(String key, DataHeader newRecord, int currentNumRecords) throws IOException {
        DbByteArrayOutputStream temp = new DbByteArrayOutputStream(MAX_KEY_LENGTH);

        (new DataOutputStream(temp)).writeUTF(key);

        if (temp.size() > MAX_KEY_LENGTH) {
            throw new IllegalArgumentException("Key is larger than permitted size of " 
                                                + MAX_KEY_LENGTH + " bytes");
        }

        file.seek(indexPositionToKeyFp(currentNumRecords));
        temp.writeTo(file);
        file.seek(indexPositionToDataHeaderFp(currentNumRecords));
        newRecord.write(file);
        newRecord.setIndexPosition(currentNumRecords);
        writeNumRecordsHeader(currentNumRecords + 1);
    }


    /**
     * Removes the record from the index. Replaces the target with the entry at the
     * end of the index.
     */
    protected void deleteEntryFromIndex(String key, DataHeader header, int currentNumRecords)
        throws IOException {
        
        if (header.indexPosition != (currentNumRecords - 1)) {
            String lastKey = readKeyFromIndex(currentNumRecords - 1);
            DataHeader last = keyToDataHeader(lastKey);

            last.setIndexPosition(header.indexPosition);
            file.seek(indexPositionToKeyFp(last.indexPosition));
            file.writeUTF(lastKey);
            file.seek(indexPositionToDataHeaderFp(last.indexPosition));
            last.write(file);
        }

        writeNumRecordsHeader(currentNumRecords - 1);
    }


    /**
     * Adds the given record to the database.
     */
    public synchronized void insertRecord(DataWriter rw) throws IOException {
        String key = rw.getKey();

        if (recordExists(key)) {
            throw new IllegalArgumentException("Key exists: " + key);
        }

        insureIndexSpace(getNumRecords() + 1);

        DataHeader newRecord = allocateRecord(key, rw.getDataLength());

        writeRecordData(newRecord, rw);
        addEntryToIndex(key, newRecord, getNumRecords());
    }


    /**
     * Updates an existing record. If the new contents do not fit in the original record,
     * then the update is handled by deleting the old record and adding the new.
     */
    public synchronized void updateRecord(DataWriter rw) throws IOException {
        DataHeader header = keyToDataHeader(rw.getKey());

        if (rw.getDataLength() > header.dataCapacity) {
            deleteRecord(rw.getKey());
            insertRecord(rw);
        } else {
            writeRecordData(header, rw);
            writeDataHeaderToIndex(header);
        }
    }


    /**
     * Reads a record.
     */
    public synchronized DataReader readRecord(String key) throws IOException {
        byte[] data = readRecordData(key);

        return new DataReader(key, data);
    }


    /**
     * Reads the data for the record with the given key.
     */
    protected byte[] readRecordData(String key) throws IOException {
        return readRecordData(keyToDataHeader(key));
    }


    /**
     * Reads the record data for the given record header.
     */
    protected byte[] readRecordData(DataHeader header) throws IOException {
        byte[] buf = new byte[header.dataCount];

        file.seek(header.dataPointer);
        file.readFully(buf);

        return buf;
    }


    /**
     * Updates the contents of the given record. An IOException is thrown if the
     * new data does not fit in the space allocated to the record. The header's 
     * data count is updated, but not written to the file.
     */
    protected void writeRecordData(DataHeader header, DataWriter rw) throws IOException {
        if (rw.getDataLength() > header.dataCapacity) {
            throw new IOException("Record data does not fit, header.dataCapacity="+
                                    header.dataCapacity+
                                    ", dataLength="+rw.getDataLength());
        }

        header.dataCount = rw.getDataLength();
        file.seek(header.dataPointer);
        rw.writeTo((DataOutput) file);
    }


    /**
     * Updates the contents of the given record. A DataFileException is thrown if
     * the new data does not fit in the space allocated to the record. The header's 
     * data count is updated, but not written to the file.
     */
    protected void writeRecordData(DataHeader header, byte[] data) throws IOException {
        if (data.length > header.dataCapacity) {
			throw new IOException("Record data does not fit, header.dataCapacity="+
                                    header.dataCapacity+
                                    ", dataLength="+data.length);
        }

        header.dataCount = data.length;
        file.seek(header.dataPointer);
        file.write(data, 0, data.length);
    }


    /**
     * Deletes a record.
     */
    public synchronized void deleteRecord(String key) throws IOException {
        DataHeader delRec = keyToDataHeader(key);
        int currentNumRecords = getNumRecords();

        if (getFileLength() == (delRec.dataPointer + delRec.dataCapacity)) {
            // shrink file since this is the last record in the file
            setFileLength(delRec.dataPointer);
        } else {
            DataHeader previous = getRecordAt(delRec.dataPointer - 1);

            if (previous != null) {
                // append space of deleted record onto previous record
                previous.dataCapacity += delRec.dataCapacity;
                writeDataHeaderToIndex(previous);
            } else {
                // target record is first in the file and is deleted by adding its 
                // space to the second record.
                DataHeader secondRecord = getRecordAt(delRec.dataPointer + 
                                          (long) delRec.dataCapacity);
                byte[] data = readRecordData(secondRecord);

                secondRecord.dataPointer = delRec.dataPointer;
                secondRecord.dataCapacity += delRec.dataCapacity;
                writeRecordData(secondRecord, data);
                writeDataHeaderToIndex(secondRecord);
            }
        }

        deleteEntryFromIndex(key, delRec, currentNumRecords);
    }


    // Checks to see if there is space for and additional index entry. If 
    // not, space is created by moving records to the end of the file.
    protected void insureIndexSpace(int requiredNumRecords) throws IOException {
        int originalFirstDataCapacity;
        int currentNumRecords = getNumRecords();
        long endIndexPtr = indexPositionToKeyFp(requiredNumRecords);

        if (endIndexPtr > getFileLength() && currentNumRecords == 0) {
            setFileLength(endIndexPtr);
            dataStartPtr = endIndexPtr;
            writeDataStartPtrHeader(dataStartPtr);

            return;
        }

        // If first.dataCapacity is set to the actual data count BEFORE resetting 
        // dataStartPtr, and there is free space in 'first', then dataStartPtr will 
        // not be reset to the start of the second record. Capture the capacity 
        // first and use it to perform the reset.
        while (endIndexPtr > dataStartPtr) {
            DataHeader first = getRecordAt(dataStartPtr);
            byte[] data = readRecordData(first);
            first.dataPointer = getFileLength();
            originalFirstDataCapacity = first.dataCapacity;
            first.dataCapacity = data.length;
            setFileLength(first.dataPointer + data.length);
            writeRecordData(first, data);
            writeDataHeaderToIndex(first);
            dataStartPtr += originalFirstDataCapacity;
            writeDataStartPtrHeader(dataStartPtr);
        }
    }


    /**
     * Closes the file.
     */
    public synchronized void close() throws IOException {
        try {
            file.close();
        } finally {
            file = null;
        }
    }
}
