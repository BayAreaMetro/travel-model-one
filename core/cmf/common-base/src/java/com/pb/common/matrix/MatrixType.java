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

import java.io.Serializable;

import org.apache.log4j.Logger;

/**
 * Defines a type-safe enumeration of matrix types supported in the matrix package.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public final class MatrixType implements Serializable {
    
    static final Logger logger = Logger.getLogger(MatrixType.class);

    public static final MatrixType BINARY = new MatrixType("Binary", 1);
    public static final MatrixType ZIP = new MatrixType("ZIP", 2);
    public static final MatrixType CSV = new MatrixType("CSV", 3);
    public static final MatrixType EMME2 = new MatrixType("Emme2", 4);
    public static final MatrixType D311 = new MatrixType("D311", 5);
    public static final MatrixType TPPLUS = new MatrixType("TPPlus", 6);
    public static final MatrixType TRANSCAD = new MatrixType("Transcad", 7);
    public static final MatrixType TPPLUS32 = new MatrixType("TPPlus32", 8); // TODO: remove once 32bit reader DLL is no longer supported 
    

    private String id;
    private int hashValue;

    /** Keep this class from being created with "new".
     *
     */
    private MatrixType(String id, int hashCode) {
        this.id = id;
        this.hashValue = hashCode;
    }

    public String toString() {
        return this.id;
    }

    public int hashCode() {
        //System.out.println ( "hashValue = " + hashValue ); 
        return hashValue;
    }
    
    public boolean equals( Object obj ) {
        MatrixType type = (MatrixType)obj;
        boolean stringResult = type.toString().equals( id );
        boolean intResult = type.hashCode() == hashValue;
        //System.out.println ( "stringResult = " + stringResult + ", toString() = " + type.toString() + ", id = " + id ); 
        //System.out.println ( "intResult = " + intResult + ", type.hashCode() = " + type.hashCode() + ", hashValue = " + hashValue );
        //System.out.println ( "stringResult && intResult = " + (stringResult && intResult) );
        return stringResult && intResult;
    }

    /*
    public boolean equals(MatrixType type) {
        boolean result = false;

        int index = type.toString().indexOf(this.id);
        if (index == 0)
            result = true;

        return result;
    }
    */
        
    public static MatrixType lookUpMatrixType(String matrixTypeName) {
        if (BINARY.toString().equalsIgnoreCase(matrixTypeName)) return BINARY;
        if (ZIP.toString().equalsIgnoreCase(matrixTypeName)) return ZIP;
        if (CSV.toString().equalsIgnoreCase(matrixTypeName)) return CSV;
        if (EMME2.toString().equalsIgnoreCase(matrixTypeName)) return EMME2;
        if (D311.toString().equalsIgnoreCase(matrixTypeName)) return D311;
        if (TPPLUS.toString().equalsIgnoreCase(matrixTypeName)) return TPPLUS;
        if (TRANSCAD.toString().equalsIgnoreCase(matrixTypeName)) return TRANSCAD;
        if (TPPLUS32.toString().equalsIgnoreCase(matrixTypeName)) return TPPLUS32; // TODO: remove once 32bit reader DLL is no longer supported 

        logger.error("Matrix type "+matrixTypeName+" is not defined");
        return null;
    }

    public static MatrixType[] values() {
        return new MatrixType[]{BINARY,ZIP,CSV,EMME2,D311,TPPLUS,TRANSCAD,TPPLUS32}; // TODO: remove once 32bit reader DLL is no longer supported 

    }
}
