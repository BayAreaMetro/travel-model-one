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
import org.apache.log4j.Logger;

public class DataReader {

	protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    String key;
    byte[] data;
    ByteArrayInputStream in;
    ObjectInputStream objIn;

    public DataReader(String key, byte[] data) {
        this.key = key;
        this.data = data;
        in = new ByteArrayInputStream(data);
    }

    public String getKey() {
        return key;
    }


    public byte[] getData() {
        return data;
    }


    public InputStream getInputStream() throws IOException {
        return in;
    }


    public ObjectInputStream getObjectInputStream() throws IOException {
        if (objIn == null) {
            objIn = new ObjectInputStream(in);
        }

        return objIn;
    }


    /**
     * Reads the next object in the record using an ObjectInputStream.
     */
    public Object readObject() throws IOException, OptionalDataException, ClassNotFoundException {
        return getObjectInputStream().readObject();
    }
    

    
	/**
	 * Reads the serialized object from filename on disk using the specified key.
	 */ 
	public static Object readDiskObject ( String filename, String key ) {

		Object obj=null;
		DataFile dataFile=null;
	    
		try {
			dataFile = new DataFile( filename, "r" );
			DataReader dr = dataFile.readRecord( key );
			obj =  dr.readObject();
		}
		catch (Exception e) {
			logger.error("Exception thrown when reading DiskObject file: " + filename );
			e.printStackTrace();
		}

		return obj;
	}
	
	
	
    
}
