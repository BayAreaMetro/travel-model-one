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
 * Interfaces with native DLL functions to read and write TP+/Cube matrices. 
 * 
 * This interface allows the use 64-bit DLL files and can thus be run on a
 * 64-bit JVM.
 * 
 * This class relies on JNA libraries jna-3.5.2.jar and platform-3.5.2.jar
 * and the VoyagerFileAccess.dll file. The file must be in the environment.
 * 
 * WARNING:  Untested!
 * 
 * 
 *
 * @author    Yegor Malinovskiy
 * @version   0.1, 5/2/2013
 */
import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Pointer;

/**
* @author    Yegor Malinovskiy
* @version   0.1, 8/13/2013
**/

public interface TpplusNativeIO64 extends Library
{		
	TpplusNativeIO64 INSTANCE=(TpplusNativeIO64) Native.loadLibrary("VoyagerFileAccess",TpplusNativeIO64.class);
	
	Pointer MatReaderOpen(String filename, String errMsg, int errBuffLen);
	Pointer MatWriterOpen(String filename, String field, int ntype, int nZones, int nMatrices, byte[] precisions, String[] matrixNames, String errMsg, int errBuffLen);
	
	void MatReaderClose(Pointer state);	
	void MatWriterClose(Pointer state);	
	
	int MatReaderGetNumMats(Pointer state);	
	int MatReaderGetNumZones(Pointer state);	
	int MatReaderGetMatrixNames(Pointer state, String[] names);
	
	int MatReaderGetRow(Pointer state, int matNumber, int rowNumber, double[] buffer);	
	int MatWriterWriteRow(Pointer state, int matNumber, int rowNumber, double[] buffer);	
}

