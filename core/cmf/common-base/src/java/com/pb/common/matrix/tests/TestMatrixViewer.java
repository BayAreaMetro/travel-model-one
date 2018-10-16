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


import java.io.File;

import javax.swing.JFrame;

import com.pb.common.matrix.*;
import com.pb.common.matrix.ui.MatrixViewerPanel;

/**
 * Tests class and methods in the matrix package.
 *
 * @author    Tim Heier
 * @version   1.0, 1/11/2003
 */
public class TestMatrixViewer {
	
	Matrix m = null;

    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("java TestMatrixViewer <input-zipfile>");
            return;
        }

        String fileName = args[0];

        MatrixType type = MatrixReader.determineMatrixType(new File(fileName));

        String format = fileName.substring(fileName.indexOf(".")+1);
        System.out.println("matrix type is: " + type);
        
    	TestMatrixViewer tester = new TestMatrixViewer();
    	if(type.equals(MatrixType.ZIP)){
            tester.readZipTestMatrix( fileName );
        } else if(type.equals(MatrixType.BINARY)){
            tester.readBinaryTestMatrix( fileName );
        } else System.out.println("Matrix viewer only works with ZIP or BINARY matrices, " +
                "enter a differnt format");

        tester.createTestMatrixViewerData();
        tester.createBigMatrix();
    	tester.testMatrixViewer();
    }


    
    /**
     * Create a full matrix and set some sample values into it.
     */
    private void createTestMatrixViewerData() {

        m = new Matrix(10,10);

        m.setDescription("Matrix object for testing MatrixViewer");

        int[] externalNumbers = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };
        m.setExternalNumbers( externalNumbers );

        m.setValueAt(1, 1, (float)1.1);
        m.setValueAt(3, 3, (float)3.3);
        m.setValueAt(5, 5, (float)5.5);
        m.setValueAt(8, 8, (float)8.8);
        m.setValueAt(10, 10, (float)10.10);

        System.out.println("\n--------- Full matrix ---------");
        MatrixUtil.print(m, "%7.2f");

        m.logMatrixStats();
    }


    /**
     * Create a full matrix and set some sample values into it.
     */
    private void createBigMatrix() {

        Matrix m = new Matrix(1000,1000);

        m.setDescription("Big matrix object for testing MatrixViewer");

//        int[] externalNumbers = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };
//        m.setExternalNumbers( externalNumbers );

        m.setValueAt(1, 1, (float)1.1);
        m.setValueAt(3, 3, (float)3.3);
        m.setValueAt(5, 5, (float)5.5);
        m.setValueAt(8, 8, (float)8.8);
        m.setValueAt(10, 10, (float)10.10);
        m.setValueAt(100, 100, (float)100.10);
        m.setValueAt(500, 500, (float)500.50);
        m.setValueAt(1000, 1000, (float)1000.10);

        MatrixWriter writer = MatrixWriter.createWriter(MatrixType.BINARY, new File("1000x1000.bin"));
        writer.writeMatrix(m);
    }


    /**
     *  Read the matrix from an existing zip file
     */
    private void readZipTestMatrix(String fileName) {
        MatrixReader mw = MatrixReader.createReader(MatrixType.ZIP, new File(fileName));
        m = mw.readMatrix();
    }

    /**
     *  Read the matrix from an existing binary file
     */
    private void readBinaryTestMatrix(String fileName) {
        MatrixReader mw = MatrixReader.createReader(MatrixType.BINARY, new File(fileName));
        m = mw.readMatrix();
    }


    public void testMatrixViewer() {
    	
	    //JFrame.setDefaultLookAndFeelDecorated(true);
    	
	    JFrame frame = new JFrame("MatrixViewer - " + m.getDescription());
	    frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
	
	    //Create and set up the content pane
	    MatrixViewerPanel matrixContentPane = new MatrixViewerPanel(m);
	    matrixContentPane.setOpaque(true); //content panes must be opaque
	    frame.setContentPane(matrixContentPane);
	
	    frame.pack();
	    frame.setVisible(true);

    }
}
