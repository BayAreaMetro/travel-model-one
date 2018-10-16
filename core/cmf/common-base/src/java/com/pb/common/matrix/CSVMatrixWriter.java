/*
 * Copyright 2005 PB Consult Inc.
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
 * Created on Nov 23, 2005 by Andrew Stryker <stryker@pbworld.com>
 */

package com.pb.common.matrix;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

/**
 * Write matrices to CSV files.
 *
 * @version 1.1 5/30/2007 - added functionality to write non-square matrices
 */
public class CSVMatrixWriter extends MatrixWriter {
    private File file;

    private Matrix[] matrices;

    /**
     * Constructor.
     * 
     * @param file
     *            The CSV output file.
     */
    public CSVMatrixWriter(File file) {
        this.file = file;
    }

    /**
     * Write the matrices.
     * 
     * The CSV files are have a header like so:
     * 
     * i,j,name1,name2...
     */
    private void writeData() {
        int[] externalRowNumbers = matrices[0].getExternalRowNumbers();
        int[] externalColNumbers = matrices[0].getExternalColumnNumbers();
        PrintWriter outStream = null;

        try {
            outStream = new PrintWriter(
                    new BufferedWriter(new FileWriter(file)));
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }

        // header
        outStream.print("i,j");

        for (int m = 0; m < matrices.length; ++m) {
            String name = matrices[m].getName();

            if (name.equals("")) {
                name = "matrix" + m;
            }

            outStream.print("," + name);
        }

        outStream.println();

        ExternalNumberIterator rowIter = new ExternalNumberIterator(
                 externalRowNumbers);
        while (rowIter.hasNext()) {
            int row = (Integer) rowIter.next();

            ExternalNumberIterator colIter = new ExternalNumberIterator(
                     externalColNumbers);
            while (colIter.hasNext()) {
                int col = (Integer) colIter.next();

                outStream.print(row + "," + col);

                for (Matrix m : matrices) {
                    outStream.print("," + m.getValueAt(row,col));
                }

                outStream.println();

            }
        }

        outStream.close();
    }


    /**
     * Write a matrix.
     * 
     * @param m
     *            Matrix to write.
     */
    public void writeMatrix(Matrix m) throws MatrixException {
        matrices = new Matrix[1];
        matrices[0] = m;
        writeData();
    }

    /**
     * Write a matrix.
     * 
     * @param index
     *            Ignored.
     * @param m
     *            The matrix to write.
     */
    public void writeMatrix(String index, Matrix m) throws MatrixException {
        writeMatrix(m);
    }

    /**
     * Write several matrices.
     * 
     * @param names
     *            Ignored.
     * @param m
     *            Matrices to write.
     */
    public void writeMatrices(String[] names, Matrix[] m) throws MatrixException {
        matrices = m;
        writeData();
    }

    /**
     * Usage: java com.pb.common.matrix.CSVMatrixWriter [taz matrix file] <out
     * csv file>
     */
    public static void main(String[] args) {
        Matrix m = null;
        String outFile = null;

        if (args.length == 2) {
            File inFile = new File(args[0]);
            outFile = args[1];
            MatrixReader reader = new BinaryMatrixReader(inFile);
            m = reader.readMatrix();
        } else {
            // create a small matrix as a test case
            m = new Matrix(2, 2);
            m.setName("test");
            int[] extNumbers = { 0, 1, 5 };
            m.setExternalNumbers(extNumbers);

            outFile = args[0];
        }

        m.setValueAt(1, 1, (float) 3.77);
        m.setValueAt(1, 5, (float) 2.5);
        m.setValueAt(5, 1, 8);

        // write the new matrix
        File file = new File(outFile);
        MatrixWriter writer = MatrixWriter.createWriter(MatrixType.CSV, file);
        writer.writeMatrix(m);

    }

}
