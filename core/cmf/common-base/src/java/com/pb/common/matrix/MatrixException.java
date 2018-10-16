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

/**
 * Defines an exception used in the matrix package with messages.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class MatrixException extends RuntimeException {

    private static final long serialVersionUID = 1L;
    
    public static final String INVALID_INDEX = "Invalid index";
    public static final String INVALID_DIMENSIONS = "Invalid matrix dimensions";
    public static final String ZERO_ROW = "Matrix has a zero row";
    public static final String SINGULAR = "Matrix is singular";
    public static final String NO_CONVERGENCE = "Solution did not converge";
    public static final String INVALID_TYPE = "Invalid matrix type";
    public static final String FILE_NOT_FOUND = "Matrix file not found";
    public static final String BUFFER_OVERFLOW = "Supplied buffer is too small";
    public static final String ERROR_READING_FILE= "Error while reading file";
    public static final String ERROR_WRITING_FILE= "Error while writing to file";
    public static final String MATRIX_DOES_NOT_EXIST = "Matrix does not exist";
    public static final String INVALID_FORMAT = "Invalid format";
    public static final String INVALID_TABLE_NAME = "Matrix does not exist with name"; 

    public MatrixException() {
        super();
    }

    public MatrixException(String message) {
        super(message);
    }

    public MatrixException(Throwable t) {
        super(t);
    }

    public MatrixException(Throwable t, String message) {
        super(message, t);
    }

}
