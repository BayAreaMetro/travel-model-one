/*
 * Copyright 2006 PB Consult Inc.
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
import com.pb.common.matrix.MatrixHistogram;
import junit.framework.TestCase;
import junit.framework.TestSuite;
import junit.textui.TestRunner;
import org.junit.Before;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;

/**
 * This class is used for ...
 * Author: Christi Willison
 * Date: Oct 4, 2007
 * Email: willison@pbworld.com
 * Created by IntelliJ IDEA.
 */
public class MatrixHistogramTest extends TestCase {

    Matrix mtxQty;
    Matrix mtxDist;
    double[] boundaries = {2.0, 100.0};

    @Before
    public void setUp(){
        int[] externalNumbers = {0,1,2};
        float[][] quantities = {{100,1000},{500,5000}};
        float[][] distances = {{10,20}, {20,5}};

        mtxQty = new Matrix(quantities);
        mtxQty.setExternalNumbers(externalNumbers);

        mtxDist = new Matrix(distances);
        mtxDist.setExternalNumbers(externalNumbers);
    }

    public void testMatrixHistogram(){
        MatrixHistogram hist = new MatrixHistogram(boundaries);
        hist.generateHistogram(mtxDist, mtxQty);

        try {
            BufferedWriter histogramFile = new BufferedWriter(new FileWriter("HistogramsTest.csv"));
            histogramFile.write("Commodity,BuyingSelling,BandNumber,LowerBound,Quantity,AverageLength\n");

            hist.writeHistogram("testData", "buying", histogramFile );
            histogramFile.close();
        } catch (IOException e) {
            e.printStackTrace();
        }


    }

    public static void main(String[] args) {
        new TestRunner().doRun(new TestSuite(MatrixHistogramTest.class));
    }
}
