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

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Implementes a MatrixWriter to write matrices to a compressed matrix file.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class ZipMatrixWriter extends MatrixWriter {

    public static final int VERSION   = 2;
    public static final int WORDSIZE  = 4;

    private ZipOutputStream zos = null;

    /**
     * Prevent outside classes from instantiating the default constructor.
     */
    private ZipMatrixWriter() {}


    /**
     * @param file represents the physical matrix file
     */
    public ZipMatrixWriter(File file) {
        this.file = file;
    }

    public void writeMatrix(Matrix m) throws MatrixException {
        writeMatrix("", m);
    }

    public void writeMatrix(String index, Matrix m) throws MatrixException {
        createZipFile();
        writeData( m );
    }

    /**
    * Creates the zip file overwriting the file if it exists.
    */
    private boolean createZipFile() {
        boolean fileExists = false;
        try {
            //Find out if we are overwriting an existing file
            if (file.exists())
                fileExists = true;

            //Create output stream
            zos = new ZipOutputStream(new FileOutputStream( file ));
        }
        catch (Exception e) {
            e.printStackTrace();
        }
        return fileExists;
    }

    /**
    * Writes a matrix to the underlying file.
    *
    *@param  m  the matrix to write
    *
    */
    private void writeData(Matrix m) {
        //Write header information
        addEntry("_version", VERSION);
        addEntry("_rows", m.nRows);
        addEntry("_columns", m.nCols);
        addEntry("_name", m.name);
        addEntry("_description", m.description);
        addEntry("_external row numbers", m.externalRowNumbers);
        addEntry("_external column numbers", m.externalColumnNumbers);

        long startTime = System.currentTimeMillis();

        //Write data
        try {
            for (int row=0; row < m.nRows; row++) {
                String rowName = "row_" + (row+1);

                ZipEntry entry = new ZipEntry(rowName);
                zos.putNextEntry(entry);

                //Create a byte array output stream to buffer bytes for one row.
                ByteArrayOutputStream baos = new ByteArrayOutputStream( m.nCols * WORDSIZE );
                DataOutputStream dout = new DataOutputStream(baos);

                //Write contents of a row to the byte array.
                for(int col=0; col < m.nCols; col++) {
                    dout.writeFloat(m.values[row][col]);
                }
                dout.close();

                //Create a byte array.
                byte byteArray[] = baos.toByteArray();

                baos.close();
                zos.write(byteArray, 0, byteArray.length);
                zos.closeEntry();
            }
            //Close zip stream
            zos.close();
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_WRITING_FILE);
        }

        long finishTime = System.currentTimeMillis();

        //System.out.println("writeData() time = " + (finishTime-startTime));

    }

    private void addEntry(String name, int data) {
        ZipEntry entry = null;
        byte[] buf = null;

        try {
            entry = new ZipEntry(name);
            zos.putNextEntry(entry);
            buf = Integer.toString(data).getBytes();
            zos.write(buf, 0, buf.length);
            zos.closeEntry();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void addEntry(String name, String data) {
        ZipEntry entry = null;
        byte[] buf = null;

        try {
            entry = new ZipEntry(name);
            zos.putNextEntry(entry);
            buf = data.getBytes();
            zos.write(buf, 0, buf.length);
            zos.closeEntry();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void addEntry(String name, int[] data) {
        try {
            StringBuffer buffer = new StringBuffer(1024);
            for (int i=1; i < data.length; i++) {
                if (i > 1)
                    buffer.append(",");
                buffer.append( Integer.toString(data[i]) );
            }

            ZipEntry entry = new ZipEntry(name);
            zos.putNextEntry(entry);
            byte[] byteBuff = buffer.toString().getBytes();
            zos.write(byteBuff, 0, byteBuff.length);
            zos.closeEntry();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

	/** Writes all tables of an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public void writeMatrices(String[] maxTables, Matrix[] m) throws MatrixException {
        throw new MatrixException("method not supported yet");
	}


/* Not currently used
    private void addEntry(String name, float[] data) {

        ZipEntry entry = null;
        byte[] buf = null;

        try {
            entry = new ZipEntry(name);
            zos.putNextEntry(entry);
            ByteArrayOutputStream baos = new ByteArrayOutputStream( (data.length+1)*WORDSIZE );
            DataOutputStream dout = new DataOutputStream(baos);

            for (int i=1; i <= data.length; i++) {
                dout.writeFloat(data[i]);
            }
            buf = baos.toByteArray();
            zos.write(buf, 0, buf.length );
            zos.closeEntry();
            dout.close();
            baos.close();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }
*/

}
