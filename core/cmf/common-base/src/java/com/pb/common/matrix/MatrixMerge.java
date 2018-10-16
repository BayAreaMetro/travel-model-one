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

import java.text.DecimalFormat;
import org.apache.log4j.Logger;
import java.io.File;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;
import java.io.IOException;

/**
 * @author Freedman
 *
 * A general utility for merging matrix data with TableDataSet data, as in
 * estimation file construction.  Currently only works by appending Emme2
 * matrix data to data file. 
 */
public class MatrixMerge {

    public static Logger logger = Logger.getLogger("com.pb.common.matrix");

    public MatrixMerge(){
    }

    /**
     * Get a matrix from the file
     * 
     * @param fileName The name of the file containing the matrix
     * @param matrixLocation THe location of the matrix in the file: 
     *    For emme2, matrix id.  
     *    For TP+, table number.
     * @return A matrix from the file at the specified location.
     */
    public Matrix getMatrix(String fileName, String matrixLocation, String matrixType){
       
        Matrix m;
        MatrixReader mr = null;
        
        if(matrixType.equals(new String("EMME2")))
            mr = MatrixReader.createReader(MatrixType.EMME2, new File(fileName));
        else if(matrixType.equals(new String("TP+")))
            mr = MatrixReader.createReader(MatrixType.TPPLUS, new File(fileName));
        else if(matrixType.equals(new String("BINARY")))
            mr = MatrixReader.createReader(MatrixType.BINARY, new File(fileName));
        else if(matrixType.equals(new String("ZIP")))
            mr = MatrixReader.createReader(MatrixType.ZIP, new File(fileName));
        else if(matrixType.equals(new String("CSV")))
            mr = MatrixReader.createReader(MatrixType.CSV, new File(fileName));
        else if(matrixType.equals(new String("D311")))
            mr = MatrixReader.createReader(MatrixType.D311, new File(fileName));
        else if(matrixType.equals(new String("TRANSCAD")))
            mr = MatrixReader.createReader(MatrixType.TRANSCAD, new File(fileName));

        logger.debug("Reading matrix "+matrixLocation+" in file "+fileName);
        
        m = mr.readMatrix(matrixLocation);
       
        return m;
       
        
    }
    /**
     * Run by:
     * java MatrixMerge <matrixType> <fileName> <location> <infile> <outfile> <ptaz column> <ataz column>
     */ 
    public static void main(String[] args) {
    
        if(args.length<7){
            logger.error("Error: java class usage:");
            logger.error("java MatrixMerge <matrixType> <fileName> <location> <inFile> <outFile> <ptaz column> <ataz column>");
            logger.error("where");
            logger.error("  matrixType = EMME2, TP+, BINARY, ZIP, CSV, D311, or TRANSCAD");
            logger.error("  fileName   = Name of file containing matrix");
            logger.error("  location   = Location of matrix in file (ex: mf01(emme2), 1 (table of TP+ matrix)");
            logger.error("  inFile     = Name of file with data to append skim to");
            logger.error("  outFile    = Name of file to write appended data to");
            logger.error("  ptaz col   = Column with PTAZ");
            logger.error("  ataz col   = Column with ATAZ");
            System.exit(1);
        }
        MatrixMerge mm = new MatrixMerge();
        String matrixType = args[0];
        String fileName = args[1];
        String matrixLocation = args[2];
        String inFileName = args[3];
        String outFileName = args[4];
        int ptazColumn = new Integer(args[5]).intValue();
        int atazColumn = new Integer(args[6]).intValue();
        
        Matrix m = mm.getMatrix(fileName,matrixLocation,matrixType);
        
        //Open data file
        TableDataSet table = null;
        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File(inFileName));
        }
        catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }

        //Display some statistics about the file
        logger.debug("Number of columns in input data : " + table.getColumnCount());
        logger.debug("Number of rows in input data    : " + table.getRowCount());
        logger.debug("Input ptaz column: "+ptazColumn);
        logger.debug("Input ataz column: "+atazColumn);

        int maxTaz=0;
        int[] tazArray = m.getInternalNumbers();
        for(int i=1;i<tazArray.length;++i)
            maxTaz = Math.max(maxTaz,tazArray[i]);
        
        logger.debug("Max Taz in matrix : "+maxTaz);
        //generate an extra row for the matrix
        float[] data = new float[table.getRowCount()];

        int maxPTaz=0;
        int maxATaz=0;
                
        //loop through table and set the data value to skim value
        for(int i=1;i<=table.getRowCount();++i){
            
            int ptaz = (int) table.getValueAt(i,ptazColumn);
            int ataz = (int) table.getValueAt(i,atazColumn);    

            if(ptaz<=0||ataz<=0||ptaz>maxTaz||ataz>maxTaz)
                continue;
                        
            if(i<=5||i%100==0||i==table.getRowCount())
                logger.info("Row "+i+" ptaz "+ptaz+" ataz "+ataz);
        
            maxPTaz = Math.max(ptaz,maxPTaz);
            maxATaz = Math.max(ataz,maxATaz);
            data[i-1]=m.getValueAt(ptaz,ataz);
        
        }
        
        logger.debug("Maximum ptaz read: "+maxPTaz);
        logger.debug("Maximum ataz read: "+maxATaz);
            
        //append the column
        table.appendColumn(data,"");
        
        String[] titles = new String[table.getColumnCount()];
        table.setColumnLabels(titles);
        
       
        //save the file    
        try {
            CSVFileWriter writer = new CSVFileWriter();
            writer.writeFile(table, new File(outFileName), 9, new DecimalFormat("#.00"));
        }
        catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
    
        logger.debug("Finished writing "+outFileName);
    }
}
