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

import com.pb.common.emme2.io.Emme2DataBank;

import org.apache.log4j.Logger;
/**
 * Contains helper methods for the Emme2Matrix I/O.
 *
 * @author    Tim Heier
 * @version   1.0, 2/7/2003
 */
public class Emme2MatrixHelper {

    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");

    public static void checkMatrixName(Emme2DataBank dataBank, String matrixName) {

        //Parse matrixName to get type and number
        int matrixType = dataBank.matrixType(matrixName);
        int matrixNumber = dataBank.matrixNumber( matrixName );

        //Check matrix type
        if (matrixType != Emme2DataBank.MS && matrixType != Emme2DataBank.MO
        && matrixType != Emme2DataBank.MD && matrixType != Emme2DataBank.MF) {
            logger.error("Unsupported matrix type: " + matrixName);
            throw new MatrixException("Unsupported matrix type: " + matrixName);
        }

        //Check matrix number
        if ( (matrixNumber < 1) || (matrixNumber > dataBank.getMaxMatrices()) ) {
            logger.error("Matrix number out of range: " + matrixNumber);
            throw new MatrixException("Matrix number out of range: " + matrixNumber);
        }

        //Check to see if matrix exists
        if (! dataBank.matrixExists( matrixName )) {
            logger.error("Matrix is not initialized in Emme2 databank: " + matrixName);
            throw new MatrixException(MatrixException.MATRIX_DOES_NOT_EXIST + ": " + matrixName);
        }

        //Check if matrix is column-wise - can't read right now
        if (dataBank.isColumnWiseMatrix( matrixName )) {
            logger.error("Columnwise flag detected for matrix: " + matrixName);
            throw new MatrixException(MatrixException.INVALID_FORMAT + ": " + matrixName);
        }

    }


    public static long calculateByteOffset(Emme2DataBank dataBank, String matrixName) {

        Emme2MatrixHelper.checkMatrixName( dataBank, matrixName );

        int matrixNumber = dataBank.matrixNumber( matrixName );
        int matrixType = dataBank.matrixType(matrixName);
 
        int arrayElement=0;
        if(matrixType == Emme2DataBank.MS)
            arrayElement=61;
        else if(matrixType==Emme2DataBank.MO)
            arrayElement=62;
        else if(matrixType == Emme2DataBank.MD)
            arrayElement=63;
        else
            arrayElement=64;    

        //Calulate offset to beginning of matrix
        long byteOffset = dataBank.getFileParameters(arrayElement).offset+                   //file
                         ((long) (matrixNumber-1) * dataBank.getFileParameters(arrayElement).reclen); //matrix

        return byteOffset;
    }

}
