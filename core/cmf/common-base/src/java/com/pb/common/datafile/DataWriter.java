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

import java.io.DataOutput;
import java.io.IOException;
import java.io.ObjectOutputStream;
import org.apache.log4j.Logger;

public class DataWriter {

	protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    private String key;
    private DbByteArrayOutputStream out;
    private ObjectOutputStream objOut;

    
    public DataWriter(String key) {
        this.key = key;
        out = new DbByteArrayOutputStream();
        try {
            objOut = new ObjectOutputStream(out);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    
    public String getKey() {
        return key;
    }


    public void writeObject(Object o) throws IOException {
        
        //Reset the size of the underlying ByteArrayOutputStream so it can be reused
        //out.reset();
        objOut.reset();
        objOut.writeObject(o);
        objOut.flush();
    }


    /**
     * Returns the number of bytes in the data.
     */
    public int getDataLength() {
        return out.size();
    }


    /**
     *  Writes the data out to the stream without re-allocating the buffer.
     */
    public void writeTo(DataOutput str) throws IOException {
        out.writeTo(str);
    }
    
    
	/**
	 * Writes the serialized contents of the object to filename on disk using the specified key.
	 */ 
	public static void writeDiskObject ( Object obj, String filename, String key ) {
	    
		DataFile dataFile=null;
	    
		try {
			dataFile = new DataFile( filename, 1 );
			DataWriter dw = new DataWriter( key );
			dw.writeObject( obj );
			dataFile.insertRecord(dw);
		}
		catch (IOException e) {
			logger.error( "IO Exception thrown when writing DiskObject file: " + filename );
			e.printStackTrace();
		}

		try {
			dataFile.close();
		}
		catch (IOException e) {
			logger.error( "IO Exception thrown when closing DiskObject file: " + filename );
			e.printStackTrace();
		}
	}
	
    
}


