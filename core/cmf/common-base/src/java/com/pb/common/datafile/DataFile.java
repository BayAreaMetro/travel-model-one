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

import java.io.IOException;

import java.util.Enumeration;
import java.util.Hashtable;

public class DataFile extends BaseDataFile {

    /**
     * Hashtable which holds the in-memory index. For efficiency, the entire index
     * is cached in memory. The hashtable maps a key of type String to a DataHeader.
     */
    protected Hashtable memIndex;
    protected  int maxElementSize = -1;


    /**
     * Creates a new database file.  The initialSize parameter determines the
     * amount of space which is allocated for the index.  The index can grow
     * dynamically, but the parameter is provide to increase
     * efficiency.
     */
    public DataFile(String dbPath, int initialSize) throws IOException {
        this(dbPath, initialSize, -1);
    }


    /**
     * Creates a new database file.  The initialSize parameter determines the
     * amount of space which is allocated for the index.  The index can grow
     * dynamically, but the parameter is provide to increase
     * efficiency.
     */
    public DataFile(String dbPath, int initialSize, int maxElementSize) throws IOException {
        super(dbPath, initialSize);
        this.maxElementSize = maxElementSize;
        this.memIndex = new Hashtable(initialSize);
    }


    /**
     * Opens an existing database and initializes the in-memory index.
     */
    public DataFile(String dbPath, String accessFlags) throws IOException {
        super(dbPath, accessFlags);

        int numRecords = readNumRecordsHeader();

        memIndex = new Hashtable(numRecords);

        for (int i = 0; i < numRecords; i++) {
            String key = readKeyFromIndex(i);
            DataHeader header = readDataHeaderFromIndex(i);

            header.setIndexPosition(i);
            memIndex.put(key, header);
        }

        //Read the maximum element size as one of the records
        if (recordExists("maxElementSize")) {
            DataReader dr = readRecord("maxElementSize");
            Integer i = null;
            try {
                i = (Integer) dr.readObject();
            }
            catch (Exception e) {
                e.printStackTrace();
            }
            this.maxElementSize = i.intValue();
        }

    }

    /**
     * Returns an enumeration of all the keys in the database.
     */
    public synchronized Enumeration enumerateKeys() {
        return memIndex.keys();
    }


    /**
     * Returns the current number of records in the database.
     */
    public synchronized int getNumRecords() {
        return memIndex.size();
    }


    /**
     * Checks if there is a record belonging to the given key.
     */
    public synchronized boolean recordExists(String key) {
        return memIndex.containsKey(key);
    }


    /**
     * Maps a key to a record header by looking it up in the in-memory index.
     */
    protected DataHeader keyToDataHeader(String key) throws IllegalArgumentException {
        DataHeader h = (DataHeader) memIndex.get(key);

        if (h == null) {
            throw new IllegalArgumentException("Key not found: " + key);
        }

        return h;
    }


    /**
     * This method searches the file for free space and then returns a DataHeader
     * which uses the space. (O(n) memory accesses)
     */
    protected DataHeader allocateRecord(String key, int dataLength) throws IOException {
        // search for empty space
        DataHeader newRecord = null;
        Enumeration e = memIndex.elements();

        //Search through existing data entries listed in the in-memory index and look for
        //an existing entry that has enough free space to accomodate this entry. Length of
        //new entry is stored in dataLength. If one is found then "split" the data record
        if (maxElementSize < 0) {
            while (e.hasMoreElements()) {
                DataHeader next = (DataHeader) e.nextElement();
                int free = next.getFreeSpace();

                if (dataLength <= free) {
                    newRecord = next.split();
                    writeDataHeaderToIndex(next);

                    break;
                }
            }
        }

        //An existing record was not split, must create a new data record to hold the entry
        //Append record to end of file - grows file to allocate space
        if (newRecord == null) {

            long fp = getFileLength();

            //If maxElementSize was specified then check that the data record being added fits
            if (maxElementSize > 0) {
                if (dataLength > maxElementSize) {
                        throw new IllegalArgumentException(
                                "Size of entry="+dataLength+" bytes is larger than maxElementSize=" + maxElementSize);
                }
                setFileLength(fp + maxElementSize); //all elements are maxElementSize in length
                newRecord = new DataHeader(fp, maxElementSize);
            }
            else {
                setFileLength(fp + dataLength);
                newRecord = new DataHeader(fp, dataLength);
            }
        }

        return newRecord;
    }


    /**
     * Returns the record to which the target file pointer belongs - meaning the specified location
     * in the file is part of the record data of the DataHeader which is returned.  Returns null if
     * the location is not part of a record. (O(n) mem accesses)
     */
    protected DataHeader getRecordAt(long targetFp) {
        Enumeration e = memIndex.elements();

        while (e.hasMoreElements()) {
            DataHeader next = (DataHeader) e.nextElement();

            if ((targetFp >= next.dataPointer) && (targetFp < (next.dataPointer + (long) next.dataCapacity))) {
                return next;
            }
        }

        return null;
    }


    /**
     * Closes the database.
     */
    public synchronized void close() throws IOException {
        try {
            super.close();
        } finally {
            memIndex.clear();
            memIndex = null;
        }
    }


    /**
     * Adds the new record to the in-memory index and calls the super class add
     * the index entry to the file.
     */
    protected void addEntryToIndex(String key, DataHeader newRecord, int currentNumRecords) throws IOException {
        super.addEntryToIndex(key, newRecord, currentNumRecords);
        memIndex.put(key, newRecord);
    }


    /**
     * Removes the record from the index. Replaces the target with the entry at the
     * end of the index.
     */
    protected void deleteEntryFromIndex(String key, DataHeader header, int currentNumRecords) throws IOException {
        super.deleteEntryFromIndex(key, header, currentNumRecords);

        DataHeader deleted = (DataHeader) memIndex.remove(key);
    }
}
