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

import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Set;
import java.util.TreeSet;


/**
 * Implementes a MatrixReader to read matrices from a comma separated value file.
 * The CSV file is assumed to have the origin zone as the first column,
 * the destination zone as the second column and then multiple columns 
 * representing different values for the i,j pair.  The code will exit if the number
 * of origins is not equal to the number of destinations.
 * 
 * i.e. column 3 could be distance, column 4 could be time
 * 
 * The reader will return a single matrix with values specified
 * by the column name or number passed to 'readMatrix' or an array of matrices
 * if an array 'readMatrices' is called.
 * 
 * If there is no header row on the file, the matrix/matrices will be given
 * a generic name like matrix1, matrix2, etc., otherwise the column header
 * will be used as the name.
 *
 * History: 1.0, 5/23/2006
 *          1.1 5/30/2007 - added functionality to handle non-square matrices
 *
 * @author    Christi Willison
 * @version   1.1 5/30/2007
 */
public class CSVMatrixReader extends MatrixReader {

    private BufferedReader inStream = null;
    private boolean headerRow = false;
    String[] firstLineElements = null;
    private float missingEntryReplacementValue = -999;
    boolean missingEntriesFound = false;

    private int nRows;
    private int nCols;
    private String name = "";
    private String description = "";
    private int[] externalRowNumbers;
    private int[] externalColNumbers;
    protected static Logger logger = Logger.getLogger(CSVMatrixReader.class);

    /**
     * Prevent outside classes from instantiating the default constructor.
     */
    private CSVMatrixReader() {}

    /**
     * @param file represents the physical matrix file
     */
    public CSVMatrixReader(File file) throws MatrixException {
        this.file = file;
        openCsvFile();
     }

     /**
     *  This constructor will be called if the code previously detected null values.
      * @param file represents the physical matrix file
      * @param nullReplacementValue is a user-specified value used to replace the null values
     */
    public CSVMatrixReader(File file, float nullReplacementValue) throws MatrixException {
        this(file);
        this.missingEntryReplacementValue = nullReplacementValue;
    }

    /**
     * Convenience method (and required by the parent class) 
     * that assumes that the user wants to read the values in 
     * column 3 and store those in the matrix. Use if your file only
     * has 3 columns (origin, destination, value) or if you know
     * that you want the first value column.  If the file has a header,
     * then the header of column 3 will be used as the matrix name
     * otherwise the matrix will be called "matrix1". 
     */
    public Matrix readMatrix() throws MatrixException {
        return readMatrix(3);
    }

    /**
     * Use this method if your CSV file does not have a header 
     * row and there are 1 or more columns of values that could be
     * used to create a matrix.  The matrix name will be 
     * "matrix" + columnPosition-2.
     * @param columnPosition
     * @return Matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(int columnPosition) throws MatrixException {
        return readData(columnPosition);
    }

    /**
     * Use this method if your CSV file has a header row and
     * there are 1 or more columns of values that could be
     * used to create a matrix.  The column name will be used
     * as the matrix name.
     * @param columnName
     * @return Matrix
     * @throws MatrixException
     */
    public Matrix readMatrix(String columnName) throws MatrixException {
        return readData(columnName);
    }


    /**
     * Use this method if your CSV file has more than 1 column 
     * of values (4 or more columns total) and you want each value
     * column to be used to create a new matrix.  If the file has 
     * a header, the headers will be used as matrix names, otherwise
     * the matrices will be named "matrix1", "matrix2", etc.
     */
    public Matrix[] readMatrices() throws MatrixException {
        return readData();
    }



    private void openCsvFile() throws MatrixException {
        logger.debug("Opening file: "+ file);

        try {
            inStream = new BufferedReader( new FileReader(file) );
            firstLineElements = checkForHeader();
            setListOfOriginsAndDestinations();
            nRows = externalRowNumbers.length-1;
            nCols = externalColNumbers.length-1;
            description = "matrix from CSV file";
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + ", "+ file);
        }

    }





    /**
     * The first element in the first row is either an origin zone
     * number or a column header (something containing letters).
     * If the element can be parsed as an Integer then the 
     * file must not contain a header row.
     *
     */
     private String[] checkForHeader(){
         try {
             BufferedReader stream = new BufferedReader( new FileReader(file) );
             String firstLine = stream.readLine();
             stream.close();
             String[] firstLineElements = firstLine.split(",");
             try{
                 Integer.valueOf(firstLineElements[0]);
                 headerRow = false;
                 return firstLineElements;
             }catch (NumberFormatException e){
                 headerRow = true;
                 return firstLineElements;
             }
         } catch (IOException e) {
             throw new RuntimeException("Can't read from file " + file, e);
         }

     }

     /**
      * Make sure that you have established whether or not 
      * there is a header row before calling this method.
      * 
      */
     private void setListOfOriginsAndDestinations(){
        Set <Integer> uniqueOrigValues = new TreeSet <Integer> ();
        Set <Integer> uniqueDestValues = new TreeSet <Integer> ();
        try{
            BufferedReader stream = new BufferedReader( new FileReader(file) );
            String line;
            String[] lineElements;

            //skip the first row if there is a header.
            if(headerRow) stream.readLine();

            while ((line = stream.readLine()) != null) {
                lineElements = line.split(",");
                uniqueOrigValues.add(Integer.valueOf(lineElements[0]));
                uniqueDestValues.add(Integer.valueOf(lineElements[1]));
            }
            stream.close();

            if (uniqueOrigValues.size() != uniqueDestValues.size()) {
                logger.info("Non-square matrix being created.");
            } else {
                for (int i : uniqueOrigValues) {
                    if (!uniqueDestValues.contains(i)) {
                        logger.warn("Matrix is square but rows and columns use different external numbers.");
                        break;
                    }
                }
            }


            externalRowNumbers = new int[uniqueOrigValues.size() + 1];
            int index = 1;
            for (Integer i : uniqueOrigValues) {
                externalRowNumbers[index++] = i;
            }
            externalColNumbers = new int[uniqueDestValues.size() + 1];
            index = 1;
            for (Integer i : uniqueDestValues) {
                externalColNumbers[index++] = i;
            }
        }catch(Exception e){
            throw new RuntimeException(e);
        }
    }

    /**
     * Returns a matrix.
     *
     */
     private Matrix readData(int columnPosition) {
         if(columnPosition < 3 || columnPosition > firstLineElements.length){
             throw new RuntimeException("Column Position must be greater than 2 but no more than " + firstLineElements.length);
         }
         if(headerRow) {
             name = firstLineElements[columnPosition-1];
         }else{
             name = "matrix" + Integer.toString(columnPosition-2);
         }
         Matrix matrix = new Matrix(name, description, nRows, nCols );
         matrix.setName(name);
        matrix.setExternalNumbers(externalRowNumbers,externalColNumbers);

         //Now fill up the matrix with values from the file.
         matrix = readValues(matrix, columnPosition-1);

        return matrix;
     }

     /**
      * Users calling this method assume that there
      * is a header row.
      * 
      * Returns a matrix.
      *
      */
      private Matrix readData(String columnName) {
          //get name from header row.
          int positionInLine = -1;
          for(int i=0; i< firstLineElements.length; i++){
              if(firstLineElements[i].equals(columnName)){
                  positionInLine=i;
                  break;
              }
          }
          if(positionInLine == -1){
              throw new RuntimeException("Either you don't have a header row, or the names don't match");
          }else if(positionInLine < 2){
              throw new RuntimeException("Your column name cannot be the name of the first 2 columns");
          }
        return readData(positionInLine+1);
      }

     /**
    * Returns an array of matrices.
    *
    */
    private Matrix[] readData() {

        //remember, first 2 columns are origin zone, destination zone.
        Matrix[] matrices = new Matrix[firstLineElements.length-2];
        for(int m=0; m < firstLineElements.length-2; m++){
            name = "matrix" + (m+1);
            if(headerRow) name = firstLineElements[m+2];
            matrices[m] = new Matrix(name, description, nRows, nCols);
            matrices[m].setExternalNumbers(externalRowNumbers,externalColNumbers);
        }
        matrices = readValues(matrices);
        return matrices;
    }



    private Matrix readValues(Matrix m, int positionInLine){
//      Now fill up the matrix with values from the file.
        try{
           String line;
           String[] lineElements;
           int origin;
           int destination;
//         skip the first row if there is a header.
           if(headerRow) inStream.readLine();
           while ((line = inStream.readLine()) != null) {
               if(missingValuesInLine(line)){
                   missingEntriesFound = true;
                   line = replaceMissingValuesInLine(line);
               }
               lineElements = line.split(",");
               origin = Integer.valueOf(lineElements[0]);
               destination = Integer.valueOf(lineElements[1]);
               m.setValueAt(origin, destination, Float.valueOf(lineElements[positionInLine]));
           }
            if(missingEntriesFound) {
                logger.info("**MISSING VALUES WERE FOUND");
                logger.info("***MISSING VALUES WERE REPLACED WITH " + missingEntryReplacementValue);
            }
            inStream.close();
       }catch(Exception e){
           throw new RuntimeException(e);
       }
       return m;
    }

    private Matrix[] readValues(Matrix[] ms){
//      Now fill up the matrix with values from the file.
        try{
           String line;
           String[] lineElements;
           int origin;
           int destination;
           if(headerRow) inStream.readLine();
           while ((line = inStream.readLine()) != null) {
               if(missingValuesInLine(line)){
                   missingEntriesFound = true;
                   line = replaceMissingValuesInLine(line);
               }
               lineElements = line.split(",");
               origin = Integer.valueOf(lineElements[0]);
               destination = Integer.valueOf(lineElements[1]);
               for(int v=2; v < lineElements.length; v++){
                   ms[v-2].setValueAt(origin, destination, Float.valueOf(lineElements[v]));
               }
           }
            if(missingEntriesFound) {
                logger.info("**MISSING VALUES WERE FOUND");
                logger.info("***MISSING VALUES WERE REPLACED WITH " + missingEntryReplacementValue);
            }
            inStream.close();
       } catch(Exception e){
           throw new RuntimeException(e);
       }
       return ms;
    }

    private boolean missingValuesInLine(String line){
        return (line.endsWith(",") || line.contains(",,"));
    }

    private String replaceMissingValuesInLine(String line){
        line = line.replace(",," , ("," + missingEntryReplacementValue + ","));
        line = line.replace(",," , ("," + missingEntryReplacementValue + ","));
        if (line.substring(line.length() - 1).equals(","))
            line = line.substring(0,line.length() - 1) +( "," + missingEntryReplacementValue);
        return line;
     }

}
