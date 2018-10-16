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

import java.io.*;
import java.util.StringTokenizer;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import org.apache.log4j.Logger;

/**
 * Implementes a MatrixReader to read matrices from a compressed matrix file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class ZipMatrixReader extends MatrixReader {

    private ZipFile zfile = null;

    //Store header values - used by readData()
    private int version;
    private int nRows;
    private int nCols;
    private String name = "";
    private String description = "";
    private int[] externalRowNumbers;
    private int[] externalColumnNumbers;
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");

    /**
     * Prevent outside classes from instantiating the default constructor.
     */
    private ZipMatrixReader() {}

    /**
     * @param file represents the physical matrix file
     */
    public ZipMatrixReader(File file) throws MatrixException {
        this.file = file;
        openZipFile();
    }

    public Matrix readMatrix() throws MatrixException {
        return readMatrix("");
    }

    public Matrix readMatrix(String index) throws MatrixException {
        readHeader();
        return readData();
    }

    private void openZipFile() throws MatrixException {

        try {
            zfile = new ZipFile( file );
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + ", "+ file);
        }
    }

	/** Reads and returns an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public Matrix[] readMatrices() throws MatrixException {

		Matrix[] m = null;

		return m;
	}

    /**
    * Read matrix information from zip file.
    *
    */
    private void readHeader() {

        ZipEntry entry = null;
        InputStream input = null;
        byte[] buf = new byte[256];
        int len;

        try {
            entry = zfile.getEntry("_version");
            input = zfile.getInputStream(entry);
            String versionString = "";
            while((len = input.read(buf)) > -1) {
                versionString += new String(buf,0,len);
            }
            version = Integer.parseInt(versionString);

            entry = zfile.getEntry("_rows");
            input = zfile.getInputStream(entry);
            String rowString = "";
            while((len = input.read(buf)) > -1) {
                rowString += new String(buf, 0, len);
            }
            nRows += Integer.parseInt(rowString);

            entry = zfile.getEntry("_columns");
            input = zfile.getInputStream(entry);
            String colString = "";
            while((len = input.read(buf)) > -1) {
                colString += new String(buf, 0, len);
            }
            nCols += Integer.parseInt(colString);

            entry = zfile.getEntry("_name");
            input = zfile.getInputStream(entry);
            while((len = input.read(buf)) > -1) {
                name += new String(buf, 0, len);
            }

            entry = zfile.getEntry("_description");
            input = zfile.getInputStream(entry);
            while((len = input.read(buf)) > -1) {
                description += new String(buf, 0, len);
            }

            //--Read externalNumbers from file
            if (version == 2) {
                externalRowNumbers = readArrayEntry("_external row numbers");
                externalColumnNumbers = readArrayEntry("_external column numbers");
            } else {
                externalRowNumbers = readArrayEntry("_external numbers");
                externalColumnNumbers = externalRowNumbers.clone();
            }

        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    private int[] readArrayEntry(String entryName) throws IOException {
        ZipEntry entry = zfile.getEntry(entryName);
        InputStream input = zfile.getInputStream(entry);
        byte[] buf = new byte[8192];
        int[] intArray;
        int len;

        //Read string in chunks
        String str = "";
        while((len = input.read(buf)) > -1) {
            str += new String(buf, 0, len);
        }

        //Split array using comma
        String[] values = str.split(",");
        intArray = new int[values.length + 1];

        //Convert string values to int
        for (int i=0; i < values.length; i++) {
            intArray[i+1] = Integer.parseInt( values[i] );
        }

        return intArray;
    }

    /**
    * Returns a matrix.
    *
    */
    private Matrix readData() {

        int len;
        float[][] values = new float[nRows][nCols];

        byte[] byteArray = new byte[(nCols+1)*ZipMatrixWriter.WORDSIZE];

        try {
            for (int row=0; row < nRows; row++) {

                String rowName = "row_" + (row+1);
                ZipEntry entry = zfile.getEntry(rowName);
                if (entry == null){
                    throw new RuntimeException("could not read row = " + rowName);
                }
                InputStream input = zfile.getInputStream(entry);

                //Read the contents of the zip file
                for (int s=0 ; ;) {
                    len = input.read(byteArray, s, byteArray.length-s);
                    if (len <= 0)
                        break;
                    s += len;
                }
                input.close();
                
                //Create a data input stream to read from byte array.
                DataInputStream din = new DataInputStream(new ByteArrayInputStream(byteArray));

                //Read float values from byte array
                for(int col=0; col < nCols; col++) {
                    values[row][col] = din.readFloat();
                }
            }
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }

        Matrix m = new Matrix(name, description, values);
        m.setExternalNumbers(externalRowNumbers, externalColumnNumbers);

        return m;
    }
}
