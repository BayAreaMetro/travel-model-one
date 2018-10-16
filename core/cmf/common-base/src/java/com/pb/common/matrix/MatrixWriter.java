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
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public abstract class MatrixWriter {

    public static Hashtable<MatrixType, MatrixWriter> typeToClassTable = new Hashtable<MatrixType, MatrixWriter>();

    public MatrixType type;
    File file;

    public static MatrixWriter createWriter(String matrixTypeName, File file)
    throws MatrixException {

        MatrixType type = MatrixType.lookUpMatrixType(matrixTypeName);
        return createWriter(type,file);
    }

    /** Factory method to create a concrete MatrixWriter class.
     *
     * @param type a type-safe enumeration of matrix types.
     * @param file the physical file containing the matrix.
     * @return a concrete MatrixWriter.
     * @throws MatrixException
     */
    public static MatrixWriter createWriter(MatrixType type, File file)
        throws MatrixException {
            
         //Instantiate the user defined writer class for the given type. If one
         //is not found then drop through and use the default writer for each type.
         MatrixWriter writer = typeToClassTable.get(type);
         if (writer != null) {
             try {
                 writer.type = type;
                 writer.file = file;
                 return writer;
             } catch (Exception e) {
                 e.printStackTrace();
             }
         }

         
        if (type.equals(MatrixType.BINARY)) {
            writer = new BinaryMatrixWriter( file );
        }
        else
        if  (type.equals(MatrixType.ZIP)) {
            writer = new ZipMatrixWriter( file );
        }
        else
        if  (type.equals(MatrixType.EMME2)) {
            writer = new Emme2MatrixWriter( file );
        }
        else
        if  (type.equals(MatrixType.TPPLUS)) {
            writer = new TpplusMatrixWriter64( file );
        }
        else
        if  (type.equals(MatrixType.TPPLUS32)) {
            writer = new TpplusMatrixWriter( file );
        }
        else
            if  (type.equals(MatrixType.TRANSCAD)) {
                // writer = new TranscadMatrixWriter( file );
                throw new RuntimeException("TRANSCAD not supported");
            }
        else
        if (type.equals(MatrixType.CSV)) {
            writer = new CSVMatrixWriter( file );
        }
        else {
            throw new MatrixException(MatrixException.INVALID_TYPE + ", " + type);
        }

        writer.type = type;
        return writer;
    }

    /**
     * Factory method to crate a MatrixWriter.
     * 
     * @param fileName physical file name
     * @return a concrete MatrixWriter
     * @throws MatrixException
     */
    public static MatrixWriter createWriter(String fileName)
            throws MatrixException {
        File file = new File(fileName);
        MatrixType type = MatrixReader.determineMatrixType(file);

        return createWriter(type, file);
    }
    
    public static void writeMatrix(File file, Matrix m) {
        MatrixType type = MatrixReader.determineMatrixType(file);
        MatrixWriter writer = createWriter(type, file); 
        writer.writeMatrix(m); 
    }
    


    public static void setWriterClassForType(MatrixType type, MatrixWriter writer) {
        typeToClassTable.put(type, writer);
    }

    public static void clearWriterClassForType(MatrixType type) {
        typeToClassTable.remove(type);
    }
    

    /* All concrete MatrixWriter classes must implement these methods.
     */
    /**
     * Writes a single matrix to file. 
     * 
     * @param m the matrix to write.  
     * @throws MatrixException
     */
    abstract public void writeMatrix(Matrix m) throws MatrixException;

    /**
     * Writes a single matrix to file. 
     * 
     * @param name the name to use, or the index of the table.
     * @param m    the matrix to write.  
     * @throws MatrixException
     */
	abstract public void writeMatrix(String name, Matrix m) throws MatrixException;

    /**
     * Writes all matrices to a single file.  
     * 
     * @param names the array of names to use.
     * @param m    the matrices to write.  
     * @throws MatrixException
     */
	abstract public void writeMatrices(String[] names, Matrix[] m) throws MatrixException;
	
    public String testRemote()    
    {
        return " testRemote() method only implemented for RMI instance.";
    }
    public String testRemote( String arg )    
    {
        return " testRemote2(" + arg + ") method only implemented for RMI instance.";
    }
    public String testRemote3( String[] arg )    
    {
        return " testRemote3() method only implemented for RMI instance.";
    }
    public String testRemote4( Matrix[] arg )    
    {
        return " testRemote4() method only implemented for RMI instance.";
    }
}
