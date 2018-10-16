/*
 * Copyright  2011 PB Consult Inc.
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
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.StringTokenizer;
import java.util.zip.Inflater;
import org.apache.log4j.Logger;

/**
 * Read a VISUM compressed binary ($BI) matrix file
 * Internal matrix name is the file name
 * Max buffer sizes are for 10000 zone matrices
 *
 * @author    Ben Stabler
 * @version   1.0, 07/22/2011
 * 
 * 
 */
public class VisumMatrixReader extends MatrixReader {
	
	private RandomAccessFile randFile;

    //header values
    private int idlength;
    private String idvalue;
    private int headerlength;
    private String headervalue;
    private int transportvalue;
    private float starttime;
    private float endtime;
    private float factor;
    private int rows;
    private int datatype;
    private byte roundproc;
    private int[] zonenums;
    private int allnull;
    private double diagsum;
     
    private int buffer_offset;
    
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");

    /**
     * Prevent outside classes from instantiating the default constructor.
     */
    private VisumMatrixReader() {}

    /**
     * @param file represents the physical matrix file
     */
    public VisumMatrixReader(File file) throws MatrixException {
        this.file = file;
    }

    public Matrix readMatrix() throws MatrixException {
        return readMatrix("");
    }

    public Matrix readMatrix(String index) throws MatrixException {
        openBinaryFile();
        readHeader();
        return readData();
    }
    
    private void openBinaryFile() {
        try {
            randFile = new RandomAccessFile(file, "r");
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + ", "+ file);
        }
    }

	public Matrix[] readMatrices() throws MatrixException {
		Matrix[] m = new Matrix[1];
		m[0] = readMatrix();
		return m;
	}

    /**
    * Read matrix header information from file.
    *
    */
    private void readHeader() {

    	try {

    		//read a bunch of bytes into memory
    		//header is easily less than this but we don't know the exact length so we'll get enough to be safe 
    		byte[] header = new byte[50000];
    		randFile.read(header);
    		
    		//wrap with byte buffer and read as little end
    		ByteBuffer bb = ByteBuffer.wrap(header);
    		bb.order(ByteOrder.LITTLE_ENDIAN);
    		
    		//read header values
    		idlength = bb.getShort();
    		  		
    		byte[] idvalue_buff = new byte[idlength];
    		for(int i=0; i<idvalue_buff.length; i++) {
    			idvalue_buff[i] = bb.get();
    		}
            idvalue = new String(idvalue_buff);
            if(! idvalue.equals("$BI")) {
            	throw new MatrixException(new Exception(), MatrixException.ERROR_READING_FILE); 
            }
            
            headerlength = bb.getShort();
            
            byte[] header_buff = new byte[headerlength];
    		for(int i=0; i<header_buff.length; i++) {
    			header_buff[i] = bb.get();
    		}
            headervalue = new String(header_buff);

            transportvalue = bb.getInt();           
            starttime = bb.getFloat();           
            endtime = bb.getFloat();
            factor = bb.getFloat();
            rows = bb.getInt();
            datatype = bb.getShort();
            roundproc = bb.get();
        
            zonenums = new int[rows+1]; //PB Matrix class starts indexing at 1 so item 0 is set to 0
            zonenums[0] = 0; 
            for (int i=1; i < rows+1; i++) {
            	zonenums[i] = bb.getInt();
            }
            
            allnull = bb.get();
            diagsum = bb.getDouble();
            
            buffer_offset = bb.position();
            
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }


    /**
    * Returns a matrix.
    *
    */
    private Matrix readData() {
    	
    	//matrix data
    	float[][] values = new float[rows][rows];
    	
    	//row and column sums
    	double[] rowsums = new double[rows];
    	double[] colsums = new double[rows];
    	
    	//define a few buffers
    	byte[] compress_length_buff = new byte[4];
    	byte[] rowsum_buff = new byte[8];
    	byte[] result_buff = new byte[8 * 10000]; //max uncompressed row buffer size in doubles

    	//seek to buffer offset from header
    	try {
			randFile.seek(buffer_offset);
		} catch (IOException e) {
			e.printStackTrace();
		}
    	
        try {

        	//loop through rows and read data
            for (int row=0; row <rows; row++) {

            	//compressed row length
                randFile.read(compress_length_buff);
                ByteBuffer bb = ByteBuffer.wrap(compress_length_buff);
                bb.order(ByteOrder.LITTLE_ENDIAN);
                int compresslength = bb.getInt();
            	
                //compressed row data
                byte[] compress_buff = new byte[compresslength];
            	randFile.read(compress_buff);
            	
            	// decompress the bytes and store the resulting data
            	Inflater decompresser = new Inflater();
           	    decompresser.setInput(compress_buff);
           	 	decompresser.inflate(result_buff);
           	    bb = ByteBuffer.wrap(result_buff);
        	 	bb.order(ByteOrder.LITTLE_ENDIAN);
           	    for (int i=0; i < rows; i++) {
           	    	values[row][i] = (float)bb.getDouble();
           	    }
                
            	//row sum
                randFile.read(rowsum_buff);
                bb = ByteBuffer.wrap(rowsum_buff);
                bb.order(ByteOrder.LITTLE_ENDIAN);
                rowsums[row] = bb.getDouble();
                
                //column sum (same size as rowsum)
                randFile.read(rowsum_buff);
                bb = ByteBuffer.wrap(rowsum_buff);
                bb.order(ByteOrder.LITTLE_ENDIAN);
                colsums[row] = bb.getDouble();
           	    
            }
           	 
            //close file
            randFile.close();
            
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.ERROR_READING_FILE);
        }

        //create matrix
        Matrix m = new Matrix(file.getName(), file.getName(), values);
        m.setExternalNumbers(zonenums, zonenums);

        return m;
    }
    
    
    public static void main(String args[]) throws java.lang.Throwable {   
    	
    	File f = new File("C:\\projects\\development\\cmf\\common-base\\bin\\visum_bi.mtx");
        VisumMatrixReader vmr = new VisumMatrixReader(f);
        Matrix m = vmr.readMatrix();
        System.out.println(m.name);
        System.out.println("i=3,j=100,value=" + m.getValueAt(3,100));
    }
    
    
}
