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
import org.apache.log4j.Logger;

/**
 * Implements a MatrixWriter to write a matrix to a .311 text file.
 *
 * @author    Joel Freedman
 * @version   1.0, 6/2003
 */
public class Emme2311MatrixWriter extends MatrixWriter {

    protected Logger logger = Logger.getLogger("com.pb.common.matrix");



    /**
     * @param file represents the physical matrix file
     */
    public Emme2311MatrixWriter(File file) {
        this.file = file;

    }


    /**
     * TODO: matrix reader
     */
     public void writeMatrix(Matrix M) throws MatrixException {
        throw new UnsupportedOperationException("Not yet implemented");
    }

    public void writeMatrix(String index, Matrix m) throws MatrixException{
        throw new UnsupportedOperationException("Not yet implemented");
    }

	/** Writes all tables of an entire matrix
	 *  (not implemented for this matrix type.)
	 *
	 */
	public void writeMatrices(String[] maxTables, Matrix[] m) throws MatrixException {

	}




}
