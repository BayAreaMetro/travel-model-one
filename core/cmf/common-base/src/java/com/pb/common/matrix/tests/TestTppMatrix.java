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
package com.pb.common.matrix.tests;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixWriter;
import com.pb.common.matrix.MatrixType;
import com.pb.common.util.ResourceUtil;

import java.io.File;
import java.util.ResourceBundle;
import org.apache.log4j.Logger;

/**
 * Tests the TppMatrixReader/Writer classes.
 *
 * @author    Jim Hicks
 * @version   1.0, 4/7/2003
 */
public class TestTppMatrix {




    public static void main(String[] args) {

		int nColumns;
		int nRows;
		MatrixReader tppReader;

        Logger logger = Logger.getLogger("com.pb.common.matrix");
        ResourceBundle rb = ResourceUtil.getResourceBundle( "morpc" );

        String input1Matrix =  ResourceUtil.getProperty(rb,"tppTest.input1Matrix");
        String outputMatrix = ResourceUtil.getProperty(rb,"tppTest.outputMatrix");
        String input2Matrix =  ResourceUtil.getProperty(rb,"tppTest.input2Matrix");



        System.out.println("\n\n");
        logger.info("Creating 1st matrix reader");
        tppReader = MatrixReader.createReader( MatrixType.TPPLUS, new File(input1Matrix) );

        System.out.println("\n");
        logger.info("Reading matrix " + input1Matrix);
        Matrix m = tppReader.readMatrix ("2");

        nColumns = m.getColumnCount();
        nRows = m.getRowCount();
        logger.info(input1Matrix + " has " + nColumns + " columns and " + nRows + " rows.");


//        m.logMatrixStats();


        System.out.println("\n\n");
        logger.info("Creating matrix writer");
        MatrixWriter tppWriter = MatrixWriter.createWriter( MatrixType.TPPLUS, new File(outputMatrix) );

        System.out.println("\n");
        logger.info("Writing matrix " + outputMatrix);
        tppWriter.writeMatrix ("1", m);




        System.out.println("\n\n");
        logger.info("Creating 2nd matrix reader");
        tppReader = MatrixReader.createReader( MatrixType.TPPLUS, new File(input2Matrix) );

        System.out.println("\n");
//		logger.info("Reading matrix " + outputMatrix);
		logger.info("Reading matrix " + input1Matrix);
        m = tppReader.readMatrix ( "1" );

        nColumns = m.getColumnCount();
        nRows = m.getRowCount();
        logger.info(input1Matrix + " has " + nColumns + " columns and " + nRows + " rows.");

		m.logMatrixStats();

        System.out.println("\n");
        logger.info("End of TestTppMatrix.");
    }
}
