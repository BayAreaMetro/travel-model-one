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
package com.pb.common.matrix;

import org.apache.log4j.Logger;

/**
 * Interfaces with native DLL functions to read and write TP+ matrices. 
 * 
 * This class must be able to find tppdlibx.cll and tppioNative.dll 
 * in the systems PATH variable.  The first is provided by Citilabs, 
 * and usually found in C:\Program Files\Citilabs\Tpplus\.  The second
 * was written by PB to interface the native C code with java.  
 * 
 * WARNING:  Because this code references 32-bit DLL files, it cannot
 * be run from a 64-bit JVM.  It can, however, be run from a 32-bit JVM
 * on a 64-bit machine.
 * 
 * WARNING:  Because this code references native methods, it needs enough
 * memory both inside the JVM to store java matrices, and outside the JVM
 * to store native matrices.  This seems to be subject to a total limit of
 * about 1.3 GB.  If you an "Out of swap space?" error, try -reducing- the 
 * size of the JVM.  If you get an "Out of heap space" error, try increasing 
 * the size of the JVM.  
 * 
 * see common-base/src/c/matrix/tpplus_native_dll
 *
 * @author    Tim Heier/Greg Erhardt
 * @version   2.0, 7/16/2007
 */
public class TpplusNativeIO {

    protected static Logger logger = Logger.getLogger( TpplusNativeIO.class );

    // Load shared library containing native methods
    // and initialize the Citilabs dll and native function pointers
	static {
        try {
            System.loadLibrary ("tppioNative");
        }
        catch ( UnsatisfiedLinkError e ) {
            logger.error("could not load tppioNative.dll.", e);
            throw e;
        }
		
        tppInitDllNative();
	}

    

    private TpplusNativeIO() {
    }

    /**
     * Java interface to initialize TP+ I/O procedures.   
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @call tppInitDllNative ();
     * 
     * Need to ensure that tppdlibx.dll (included with Cube) is available
     * in the system's path.  
     */
	private static native void tppInitDllNative ();
	
    /**
     * Get the number of rows from a TP+ matrix on disk.  
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @param jfileName - Path to the file to read.
     */
    public static native int tppGetNumberOfRowsNative (String jfileName);
    
    /**
     * Get the number of tables from a TP+ matrix on disk.  
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @param jfileName - Path to the file to read.
     */
    public static native int tppGetNumberOfTablesNative (String jfileName);
    
    /**
     * Get the number of tables from a TP+ matrix on disk.     
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @param jfileName - Path to the file to read.
     * @param jtable    - The index of the table to read (1-based).  
     */
    public static native String tppGetTableNameNative (String jfileName, int jtable); 
    
    /**
     * Read a TP+ matrix from disk, only for a single table.  
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @param jfileName - Path to the file to read.
     * @param jdata     - A single array of data in which to store the results,
     *                    rows, then cols: double[nRows*nCols].
     * @param jtable    - The index of the table to read (1-based).  
     */
    public static native void tppReadTableNative (String jfileName, double[] jdata, int jtable);
    
    /**
     * Java interface to write a TP+ matrix file to disk, all tables.  
     * see common-base/src/c/matrix/tpplus_native_dll
     * 
     * @call tppWriteNative (String jfileName, float[] jdata, String jtableNames, int jnrows, int jntables, int jprecision);
     * 
     * @param jfileName  - Path to the file to write.
     * @param jdata      - A single array of data to write, rows, then tables, 
     *                     then columns: float[nRows*nTables*nCols].
     * @param jtableNames - A single string of table names, delimited by spaces.
     * @param jnrows     - Number of zones (supports square matrices only). 
     * @param jntables   - Number of tables. 
     * @param jprecision - Decimals of precision used to store output
     *                        (full precision 'D' and 'S' not supported. 
     * 
     */
    public static native void tppWriteNative (String jfileName, float[] jdata, String jtableNames, int jnrows, int jntables, int jprecision);
   
}
