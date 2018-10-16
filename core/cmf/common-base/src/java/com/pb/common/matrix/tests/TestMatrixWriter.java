/*
 * Copyright 2006 PB Consult Inc.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 * 
 * Created on Oct 17, 2006 by Andrew Stryker <stryker@pbworld.com>
 */

package com.pb.common.matrix.tests;

import static org.junit.Assert.*;

import java.io.File;

import org.apache.log4j.Logger;
import org.junit.Test;

import com.pb.common.matrix.CSVMatrixWriter;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixWriter;
import com.pb.common.matrix.ZipMatrixWriter;

/**
 * @author Andrew Stryker
 * @version 0.1
 */
public class TestMatrixWriter {
    private Logger logger = Logger.getLogger(TestMatrixWriter.class);

    /**
     * Test method where the file name has a valid type.
     * 
     * {@link com.pb.common.matrix.MatrixWriter#createWriter(java.lang.String)}.
     */
    @Test
    public void testCreateWriterStringCorrect() {
        float[][] values = { { 1, 2 }, { 3, 4 } };
        Matrix matrix = new Matrix(values);
        Matrix matrix1;
        String fileName = "createWriterStringCorrect.zmx";
        MatrixWriter writer = MatrixWriter.createWriter(fileName);

        logger.info("Writing " + fileName);
        writer.writeMatrix(matrix);

        matrix1 = MatrixReader.readMatrix(new File(fileName), fileName);

        for (int i = 1; i <= 2; ++i) {
            for (int j = 1; j <= 2; ++j) {
                assertEquals(matrix.getValueAt(i, j), matrix1.getValueAt(i, j));

            }
        }

        File file = new File(fileName);
        file.delete();
    }

    /**
     * Test method where the file name does correspond to a valid type.
     * 
     * {@link com.pb.common.matrix.MatrixWriter#createWriter(java.lang.String)}.
     */
    @Test
    public void testCreateWriterStringFail() {
        String fileName = "createWriterStringFail.junk";
        boolean runtimeCaught = false;

        try {
            @SuppressWarnings("unused")
            MatrixWriter writer = MatrixWriter.createWriter(fileName);
        } catch (RuntimeException e) {
            logger.info("Caught expected RuntimeException");
            runtimeCaught = true;
        } catch (Exception e) {
            logger.error("Caught an unexpected exception.");
        }
        
        if (!runtimeCaught) {
            fail("Did not catch a RuntimeException.");
        }
    }
    

    /**
     * Test to see if we get the right kind of MatrixWriter
     * 
     * {@link com.pb.common.matrix.MatrixWriter#createWriter(java.lang.String)}.
     */
    @Test
    public void testCreateWriterString() {
        String fileName = "fooBar";
        MatrixWriter zipWriter = MatrixWriter.createWriter(fileName + ".zmx");
        MatrixWriter csvWriter = MatrixWriter.createWriter(fileName + ".csv");
        
        if (!(zipWriter instanceof ZipMatrixWriter)) {
            fail("Writer should have been an instance of the ZipMatrixWriter.");            
        }
        
        if (!(csvWriter instanceof CSVMatrixWriter)) {
            fail("Writer should have been an instance of the CSVMatrixWriter.");            
        }
    }
}
