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

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.Serializable;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 8/13/2003
 *
 */

public class DiskObjectArray implements Serializable {

	private String fileName;
	private int arraySize;
    private int maxElementSize;

	private String[] indexArray;

	private transient DataFile dataFile;

	private DiskObjectArray() { 
	}


    /**
     * Constructor called when creating/overwriting an existing file.
     *
     * @param fileName  fully quallified file name of file used to
     * @param arraySize  number of elements in the array
     * @param maxElementSize  maximum size of an element that will be stored (in bytes)
     * @throws IOException
     */
    public DiskObjectArray(String fileName, int arraySize, int maxElementSize) throws IOException {
        this.fileName = fileName;
        this.arraySize = arraySize;
        this.maxElementSize = maxElementSize;

        dataFile = new DataFile(fileName, arraySize, maxElementSize);

        //Number of elements in array - used when the data file is opened later
        DataWriter dw = new DataWriter("arraySize");
        dw.writeObject( new Integer(arraySize) );
        dataFile.insertRecord(dw);

        //maximum size of an element that will be stored - used when the data file is opened later
        dw = new DataWriter("maxElementSize");
        dw.writeObject( new Integer(maxElementSize) );
        dataFile.insertRecord(dw);

        indexArray = new String[arraySize+1];
        for (int i=0; i <=arraySize; i++) {
            indexArray[i] = i + "";
        }

    }


	/**
	 * Constructor called when opening an existing file.
	 * 
	 * @param fileName  fully qualified file name of data-file
	 * @throws IOException
	 */
	public DiskObjectArray(String fileName) throws IOException, FileNotFoundException {
		this.fileName = fileName;
		
		File f = new  File(fileName);

		if (! f.exists()) {
		    throw new FileNotFoundException("Database file could not be found: " + fileName);
		}

		//Read size of array from data file and initialize indexArray
		try {
			dataFile = new DataFile(fileName, "rw");
			DataReader dr = dataFile.readRecord("arraySize");
			Integer i = (Integer) dr.readObject();
			this.arraySize = i.intValue();

            dr = dataFile.readRecord("maxElementSize");
            i = (Integer) dr.readObject();
            this.maxElementSize = i.intValue();

            //This is a small hack to set the max element size without calling a constructor
            //dataFile.maxElementSize = this.maxElementSize;

		}
		catch (IOException e) {
			throw e;
		}
		catch (ClassNotFoundException e) {
			e.printStackTrace();
		}
        
		indexArray = new String[arraySize+1];
		for (int i=0; i <=arraySize; i++) {
			indexArray[i] = i + "";
		}

	}


	public void add(int index, Object element) {
		//Skip size check for maximum performance
		//if (index > size || index < 0) {
		//	throw new IndexOutOfBoundsException("Index: "+index+", Size: "+size);
		//}

        DataWriter dw = new DataWriter( indexArray[index] );
        try {
            dw.writeObject( element );
        }
        catch (IOException e) {
            e.printStackTrace();
        }

        //Check size of element against the maximum allowed record size
        if (dw.getDataLength() > maxElementSize) {
            throw new IllegalArgumentException(
                    "Size of entry="+dw.getDataLength()+" bytes is larger than maxElementSize=" + maxElementSize);
        }

        try {
			//Update record if it exists already
			if (dataFile.recordExists(indexArray[index])) {
				dataFile.updateRecord( dw );
			}
			else {
				dataFile.insertRecord( dw );
			}
		}
        catch (Exception e) {
            e.printStackTrace();
        }
	}


	/**
	 * Returns an element from the array.
	 *  
	 * @param index  array index
	 */
	public Object get(int index) {
		//Skip size check for maximum performance
		//if (index > size || index < 0) {
		//	throw new IndexOutOfBoundsException("Index: "+index+", Size: "+size);
		//}

		DataReader dr = null;
		Object obj = null;
        try {
            dr = dataFile.readRecord(indexArray[index]);
			obj = dr.readObject();
        }
        catch (Exception e) {
            e.printStackTrace();
        }

		return obj;
	}


	/**
	 * Removes an element from the array. Can be an expensive operation so only 
	 * delete when necessary.
	 * 
	 * @param index  array index
	 */
	public void remove(int index) {
		try {
            dataFile.deleteRecord( indexArray[index] );
        }
        catch (IOException e) {
            e.printStackTrace();
        }
		
	}


    public String getFileName() {
        return fileName;
    }


    public int getArraySize() {
        return arraySize;
    }


    public int getMaxElementSize() {
        return maxElementSize;
    }

	/**
	 * Closes the underlying file.
	 *
	 */
	public void close() {
		try {
            dataFile.close();
        }
        catch (IOException e) {
            e.printStackTrace();
        }
	}
}

