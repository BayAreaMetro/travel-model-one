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

import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.matrix.CSVMatrixReader;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixUtil;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Random;

/**
 * The matrices output from tests 1, 2 and 3 should all look the same.
 * 
 * @author Christi Willison 
 * @version 1.0, May 24, 2006
 */
public class TestCSVMatrixReader {
    public static final String csvTestFileName = "csv_matrix_3cols_header.csv";
    public static final String csvTest2FileName = "csv_matrix_4cols_header.csv";
    public static final String csvTest3FileName = "csv_matrix_4cols_noheader.csv";
    public static final String csvTest4FileName = "csv_matrix_4cols_nullvaluesin3.csv";
    public static final String csvTest5FileName = "csv_matrix_4cols_nullvaluesin4.csv";
    
    static CSVMatrixReader reader = null;
    
    public static void main (String[] args){
        
        //Create test file with header. Used in tests 1, 2 and 3
        int[] originColumn = {1,2,3,4,5,1,2,3,4,5,1,2,3,4,5,1,2,3,4,5,1,2,3,4,5};
        int[] destColumn = {1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,5,5,5,5,5};
        float[] values = new float[originColumn.length];
        Random random = new Random();
        for(int i=0; i< values.length; i++){
            values[i] = 10.0f * random.nextFloat(); 
        }
        TableDataSet testFileWithHeader = new TableDataSet();
        testFileWithHeader.appendColumn(originColumn, "i");
        testFileWithHeader.appendColumn(destColumn, "j");
        testFileWithHeader.appendColumn(values,"time");
        
        //Write the 3-column, header row file
        CSVFileWriter csvWriter = new CSVFileWriter();
        try {
            csvWriter.writeFile(testFileWithHeader, new File(csvTestFileName));
            System.out.println("Writing Test File 1 to " + new File(csvTestFileName).getAbsolutePath());
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        //Set up new table.  This will be identical
        //to table 1, but now a "dist" column has been appended.
        float[] distCol = new float[originColumn.length];
        for(int i=0; i< distCol.length; i++){
            distCol[i] = (10.0f * random.nextFloat()) + 50.0f; 
        }
        
        TableDataSet testFile2WithHeader = new TableDataSet();
        testFile2WithHeader.appendColumn(originColumn, "i");
        testFile2WithHeader.appendColumn(destColumn, "j");
        testFile2WithHeader.appendColumn(values,"time");
        testFile2WithHeader.appendColumn(distCol,"dist");
        //Write the 4-column, header row file
        csvWriter = new CSVFileWriter();
        try {
            csvWriter.writeFile(testFile2WithHeader, new File(csvTest2FileName));
            System.out.println("Writing Test File 2 to " + new File(csvTest2FileName).getAbsolutePath());
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        //Creating a new file without a header row to do final tests.  Has 4 columns
        PrintWriter outStream = null;

        try {
            System.out.println("Writing Test File 3 to " + new File(csvTest3FileName).getAbsolutePath());
            outStream = new PrintWriter(new BufferedWriter(new FileWriter(new File(csvTest3FileName))));
            for(int i=0; i< originColumn.length; i++){
                outStream.println(originColumn[i] + "," + destColumn[i]+ "," + values[i] + "," + distCol[i] );
            }
            outStream.close();
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        System.out.println();

        //Set up new table that has null values in row 3 within the matrix
        try {
            System.out.println("Writing Test File 4 to " + new File(csvTest4FileName).getAbsolutePath());
            outStream = new PrintWriter(new BufferedWriter(new FileWriter(new File(csvTest4FileName))));
            for(int i=0; i< originColumn.length; i++){
                if(i % 2 == 0)
                    outStream.println(originColumn[i] + "," + destColumn[i]+ ","  + "," + distCol[i] );
                else
                    outStream.println(originColumn[i] + "," + destColumn[i]+ "," + values[i] + "," + distCol[i] );
            }
            outStream.close();
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        System.out.println();

        //Set up new table that has null values in row 4 within the matrix
        try {
            System.out.println("Writing Test File 5 to " + new File(csvTest5FileName).getAbsolutePath());
            outStream = new PrintWriter(new BufferedWriter(new FileWriter(new File(csvTest5FileName))));
            for(int i=0; i< originColumn.length; i++){
                if(i % 2 == 0)
                    outStream.println(originColumn[i] + "," + destColumn[i]+ "," + values[i] + "," + distCol[i] );
                else
                    outStream.println(originColumn[i] + "," + destColumn[i]+ "," + values[i] + ","  );
            }
            outStream.close();
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        System.out.println();

        
//****  TESTS BELOW USE THE FILE THAT HAS 3 COLUMNS WITH A HEADER ROW ****///
        
        //Test 1: test the default 'readMatrix' method.
        testReadMatrix(csvTestFileName);
        
        //Test 2: test the readMatrix(columnPosition) method
        testReadMatrixColumnPosition(csvTestFileName, 3);
        
        //Test 3: test the readMatrix(columnName) method
        testReadMatrixColumnName(csvTestFileName, "time");
        
        //Test 4: test the readMatrices() method
        testReadMatrices(csvTestFileName);
        
//****  TESTS BELOW USE THE FILE THAT HAS 4 COLUMNS WITH A HEADER ROW ****///
        
        //Test 5:  test the readMatrix() method.  In this case the 
        // time column should be read even though there is a time and dist
        //column.  The name of the matrix should be "time"
        testReadMatrix(csvTest2FileName);
        
        //Test 6: test the readMatrix(columnPosition) method (skip the time and
        // only read the distance column)
        // The matrix should be called "dist"
        testReadMatrixColumnPosition(csvTest2FileName, 4);
        
        
        //Test 7: test the readMatrix(columnName) method (skip the time and
        // only read the distance column)
        // The matrix should be called "dist"
        testReadMatrixColumnName(csvTest2FileName, "dist");
        
        
        //Test 8:  test the readMatrices() method.  This time the reader should
        //return 2 matrices, one called time and the other called dist.
        testReadMatrices(csvTest2FileName);
        
        
//****  TESTS BELOW USE THE FILE THAT HAS 4 COLUMNS WITHOUT A HEADER ROW ****///
        
        //Test 9: Should print out the time values  
        testReadMatrix(csvTest3FileName);
        
        //Test 10: test the readMatrix(columnPosition) method (skip the time and
        // only read the distance column)
        // The matrix should be called "dist"
        testReadMatrixColumnPosition(csvTest3FileName, 4);
        
        
        //Test 11: test the readMatrix(columnName) method (skip the time and
        // only read the distance column)
        // This should throw an exception because the file doesn't have a header.
        try{
            testReadMatrixColumnName(csvTest3FileName, "dist");
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }
        
        //Test 12:  test the readMatrices() method.  This time the reader should
        //return 2 matrices, one called time and the other called dist.
        testReadMatrices(csvTest3FileName);
        
        //Test 13:
        try{
            testReadMatrixColumnPosition(csvTest3FileName, 5);
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }
        
        //Test 14:
        try{
            testReadMatrixColumnPosition(csvTest3FileName, 2);
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }
        
        //Test 15:
        try{
            testReadMatrixColumnName(csvTest2FileName, "i");
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }
        
        //Test 16:
        try{
            testReadMatrixWithNulls(csvTest4FileName,3);
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }

        //Test 16:
        try{
            testReadMatrixWithNulls(csvTest5FileName,4);
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }

        //Test 16:
        try{
            testReadMatrixReplaceNulls(csvTest4FileName);
        }catch (RuntimeException e){
            System.out.println(e.getMessage());
            System.out.println();
            System.out.println();
        }
        
        
    }
    
    private static void testReadMatrix(String fileName){
        System.out.println("Test Description: ");
        System.out.println("\tMatrix read in using default 'readMatrix' method.");
        System.out.println("\tRegardless of the number of colums, it should print");
        System.out.println("\tout the 'time' values (numbers between 1 and 10)");
        
        reader = new CSVMatrixReader(new File(fileName));
        Matrix m = reader.readMatrix();
        
        System.out.println("Matrix name is '" + m.getName() + "'.  User read in file " + fileName);
        MatrixUtil.print(m,"%8.3f");
        System.out.println();
        System.out.println();
    }
    
    private static void testReadMatrixColumnPosition(String fileName, int columnPosition){
        System.out.println("Test Description: ");
        System.out.println("\tMatrix read in using 'readMatrix(columnPosition)' method.");
        System.out.println("\tIf user specifies columns 1, 2 or greater than 4, a runtime exception is thrown.");
        System.out.println("\tIf user specifies column 3, the 'time' values (numbers between 1 and 10) should print");
        System.out.println("\tIf user specifies column 4, the 'dist' values (numbers between 50 and 60) should print");
        System.out.println("User specified column " + columnPosition + ".  User read in file " + fileName);
        
        reader = new CSVMatrixReader(new File(fileName));
        Matrix m = reader.readMatrix(columnPosition);
        MatrixUtil.print(m,"%8.3f");
        System.out.println();
        System.out.println();
    }
    
    private static void testReadMatrixColumnName(String fileName, String columnName){
        System.out.println("Test Description: ");
        System.out.println("\tMatrix read in using 'readMatrix(columnName)' method.");
        System.out.println("\tIf user specifies columns i or j, a runtime error should occur.");
        System.out.println("\tIf user specifies column 'time', the 'time' values (numbers between 1 and 10) should print");
        System.out.println("\tIf user specifies column 'dist', the 'dist' values (numbers between 50 and 60) should print");
        System.out.println("User specified column " + columnName + ".  User read in file " + fileName);
        reader = new CSVMatrixReader(new File(fileName));
        Matrix m = reader.readMatrix(columnName);
        
        MatrixUtil.print(m,"%8.3f");
        System.out.println();
        System.out.println();
    }
    
    private static void testReadMatrices(String fileName){
        System.out.println("Test Description: ");
        System.out.println("\tMatrices read in using 'readMatrices()' method.");
        System.out.println("\tIf user specifies file 'csv_matrix_3cols_header.csv', the time matrix will print");
        System.out.println("\tIf user specifies file 'csv_matrix_4cols_header.csv' or , 'csv_matrix_4cols_noheader.csv'");
        System.out.println("\tthe time and dist matrices will print");
        System.out.println("User specified file " + fileName);
        reader = new CSVMatrixReader(new File(fileName));
        Matrix[] matrices = reader.readMatrices();
        for(int m=0; m< matrices.length; m++){
            MatrixUtil.print(matrices[m],"%8.3f");
            System.out.println();
            System.out.println();
        }
    }

    private static void testReadMatrixWithNulls(String fileName, int columnPosition){
        System.out.println("Test Description: ");
        System.out.println("\tCSV file has empty values for certain entries");
        System.out.println("\tMatrices read in using 'readMatrix(column)' method.");
        System.out.println("\tIf user specifies column 3, the 'time' values (numbers between 1 and 10) should print");
        System.out.println("\tIf user specifies column 4, the 'dist' values (numbers between 50 and 60) should print");
        System.out.println("\tThe missing values should be replaced by the default value -999");
        System.out.println("User specified column " + columnPosition + ".  User read in file " + fileName);
        reader = new CSVMatrixReader(new File(fileName));
        Matrix matrix = reader.readMatrix(columnPosition);
        MatrixUtil.print(matrix,"%10.3f");
        System.out.println();
        System.out.println();
    }

    private static void testReadMatrixReplaceNulls(String fileName){
            System.out.println("Test Description: ");
            System.out.println("\tReader constructed using the null replacement argument '-1'");
            System.out.println("\tMatrices read in using 'readMatrix(3)' method.");
            System.out.println("\tIf user specifies file 'csv_matrix_4cols_nullvaluesin3.csv' ");
            System.out.println("\tthe time matrices will print and should have '-1' for some of the elements");
            System.out.println("User specified file " + fileName);
            reader = new CSVMatrixReader(new File(fileName), -1.0f);
            Matrix matrix = reader.readMatrix(3);
            MatrixUtil.print(matrix,"%10.3f");
            System.out.println();
            System.out.println();
        }


    
    
}
