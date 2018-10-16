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

import java.io.File;
import java.util.Hashtable;


/**
 * Defines a general class used to read matrices from files.
 *
 * @author    Tim Heier & Joel Freedman (Transcad capabilities)
 * @version   2.0, 1/11/2003
 *
 */
public abstract class MatrixReader {

    public static Hashtable<MatrixType, MatrixReader> typeToClassTable = new Hashtable<MatrixType, MatrixReader>();
    
    public MatrixType type;
    public File file;

    /** Factory method to create a concrete MatrixReader class.
     *
     * @param type a type-safe enumeration of matrix types.
     * @param file the physical file containing the matrix.
     * @return a concrete MatrixReader.
     * @throws MatrixException
     */
    public static MatrixReader createReader(MatrixType type, File file)
        throws MatrixException {

        //Instantiate the user defined reader class for the given type. If one
        //is not found then drop through and use the default reader for each type.
        MatrixReader reader = typeToClassTable.get(type);
        if (reader != null) {
            try {
                reader.type = type;
                reader.file = file;
                return reader;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        if (type.equals(MatrixType.BINARY)) {
            reader = new BinaryMatrixReader( file );
        }
        else if  (type.equals(MatrixType.ZIP)) {
            reader = new ZipMatrixReader( file );
        }
        else if  (type.equals(MatrixType.CSV)) {
                reader = new CSVMatrixReader( file );
        }
        else if  (type.equals(MatrixType.EMME2)) {
            reader = new Emme2MatrixReader( file );
        }
        else if  (type.equals(MatrixType.TPPLUS)) {
            reader = new TpplusMatrixReader64( file ); // replacing TpplusMatrixReader, which uses the 32bit reader
        }
        else if  (type.equals(MatrixType.TRANSCAD)) {
            // reader = new TranscadMatrixReader( file );
            throw new RuntimeException("TRANSCAD not supported");
        }
        else if (type.equals(MatrixType.D311)) {
            reader = new Emme2311MatrixReader(file);
        }
        else if  (type.equals(MatrixType.TPPLUS32)) { // TODO: remove once 32bit reader DLL is no longer supported
            reader = new TpplusMatrixReader( file );  
        }
        else {
            throw new MatrixException(MatrixException.INVALID_TYPE+", "+ type);
        }

        reader.type = type;
        return reader;
    }

    public static MatrixReader createReader(String matrixTypeName, File file)
    throws MatrixException {

        MatrixType type = MatrixType.lookUpMatrixType(matrixTypeName);
        return createReader(type,file);
    }
    
    public static MatrixReader createReader(String fileName)
    throws MatrixException {
        File file = new File(fileName);
        MatrixType type = determineMatrixType(file);
        return createReader(type,file);
    }
    

    public static Matrix readMatrix(File file, String matrixName) {
        Matrix matrix;
        MatrixType type = determineMatrixType(file);

        //Create the correct matrix reader
        if (type.equals(MatrixType.EMME2)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.EMME2, file);
            matrix = mr.readMatrix(matrixName);
        } else if (type.equals(MatrixType.BINARY)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.BINARY, file);
            matrix = mr.readMatrix();
        } else if (type.equals(MatrixType.ZIP)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.ZIP, file);
            matrix = mr.readMatrix();
        } else if (type.equals(MatrixType.CSV)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.CSV, file);
            matrix = mr.readMatrix();
        } else if (type.equals(MatrixType.TPPLUS)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS, file);
            matrix = mr.readMatrix(matrixName);
        } else if (type.equals(MatrixType.TPPLUS32)) { // TODO: remove once 32bit reader DLL is no longer supported
            MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS32, file);
            matrix = mr.readMatrix(matrixName);
        } else if (type.equals(MatrixType.TRANSCAD)) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.TRANSCAD, file);
            matrix = mr.readMatrix(matrixName);
         } else {
            throw new RuntimeException("Unsupported matrix type: " + type);
        }

        return matrix;
    }

    /**
     * Attempts to determine the type of a matrix file base on the file extension.
     *
     * @param file name of matrix file
     * @return the matrix type based on file extension.
     * @throws RuntimeException when type cannot be determined
     */
    public static MatrixType determineMatrixType(File file) {
        MatrixType type;
        String fileName = file.getName();

        if (fileName.indexOf(".bin") > 0 || fileName.indexOf(".BIN") > 0 ||
           fileName.indexOf(".binary") > 0 || fileName.indexOf(".BINARY") > 0)
        {
            type = MatrixType.BINARY;
        }
        else if (fileName.indexOf(".zip") > 0 || fileName.indexOf(".ZIP") > 0
                || fileName.indexOf(".zmx") > 0
                || fileName.indexOf(".compressed") > 0
                || fileName.indexOf(".COMPRESSED") > 0) {
            type = MatrixType.ZIP;
        }
        else if (fileName.indexOf(".csv") > 0 || fileName.indexOf(".CSV") > 0) {
            type = MatrixType.CSV;
        }
        else if (fileName.indexOf(".emme2") > 0 || fileName.indexOf(".EMME2") > 0 ||
                fileName.indexOf(".e2ban") > 0 || fileName.indexOf(".E2BAN") > 0 ||
                fileName.indexOf(".em2") > 0 || fileName.indexOf(".EM2") > 0 ||
                fileName.indexOf("emme2ban") >= 0 || fileName.indexOf("EMME2BAN") >= 0 ||
                fileName.equalsIgnoreCase("emme2ban") || fileName.equalsIgnoreCase("emmebank"))
        {
            type = MatrixType.EMME2;
        }
        else if (fileName.indexOf(".tpp") > 0 || fileName.indexOf(".TPP") > 0 ||
                fileName.indexOf(".tpplus") > 0 || fileName.indexOf(".TPPLUS") > 0)
        {
            type = MatrixType.TPPLUS;
        }
        else if (fileName.indexOf(".mtx") > 0 || fileName.indexOf(".MTX") > 0 ||
                fileName.indexOf(".transcad") > 0 || fileName.indexOf(".TRANSCAD") > 0)
        {
            type = MatrixType.TRANSCAD;
        }
        else {
            throw new RuntimeException("Could not determine type of matrix file, " + file.getAbsolutePath());
        }

        return type;
    }

    public static void setReaderClassForType(MatrixType type, MatrixReader reader) {
        typeToClassTable.put(type, reader);
    }

    public static void clearReaderClassForType(MatrixType type) {
        typeToClassTable.remove(type);
    }
    
    
    public void testRemote(String name) throws MatrixException {
        System.out.println ("RMI call to testRemote() for MatrixType " + type.toString());
        System.out.println ("file type: " + this.type.toString());
        System.out.println ("file name: " + this.file.getName());
        System.out.println ("table name: " + name);
    }
    
    
    
    /*
     * All concrete MatrixReader classes must implement these methods.
     */
    /**
     * Reads a single matrix.  
     * 
     * @param name name of the matrix table to read, or the index of the table.  
     * @return the matrix read.
     * @throws MatrixException
     */
    abstract public Matrix readMatrix(String name) throws MatrixException;

    
    /**
     * Reads a single matrix.  
     * 
     * @return the matrix read.
     * @throws MatrixException
     */
    abstract public Matrix readMatrix() throws MatrixException;

	/** Reads an entire set of matrices from a tpplus or transcad matrix file
	 *
	 * @return a complete matrix
	 * @throws MatrixException
	 */
    abstract public Matrix[] readMatrices() throws MatrixException;


}
