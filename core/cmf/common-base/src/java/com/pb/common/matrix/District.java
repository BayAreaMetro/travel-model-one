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

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;

/**
 * @author Freedman
 *
 * Allows the summary of matrices using a district equivalency.
 * The class uses a TableDataSet to store the equivalency.
 *
 */
public class District {


    protected TableDataSet dTable = null;
    protected int[] externalNumbers;
    protected int numberOfDistricts;
    private int cols, rows;
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");

    
    /**
     * Use this constructor if reading a district equivalency 
     * from a text file.
     * @param file a district equivalency file in format: i, district
     * 
     */
    public District(File file){

        try {
            CSVFileReader reader = new CSVFileReader();
            dTable = reader.readFile(file);
        }
        catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        }
        initialize();
    }
    
    private void initialize(){
        
        //Build an index on column 1
        dTable.buildIndex(1);

        setExternalNumbers();        

        //set number of districts = max district number
        for(int i=1;i<=dTable.getRowCount();++i)
            numberOfDistricts = Math.max(numberOfDistricts, 
                (int)dTable.getValueAt(i,2));  
    }

    private void setExternalNumbers(){
        
        externalNumbers = new int[dTable.getRowCount()+1];
           
        for(int i=1;i<=dTable.getRowCount();++i)
            externalNumbers[i] = (int) dTable.getValueAt(i,1);
        
    }    
    /* Sum the argument matrix and return the
     * summed matrix by districts.
     * @param matrix The matrix to sum
     * @return matrix summed by districts
     */
    public Matrix getSum(Matrix matrix){
        
        //create return matrix
        Matrix dMatrix = generateDistrictMatrix(matrix);
        
        int[] externals = matrix.getExternalNumbers();
        
        //calculate sum
        for(int i=1;i<=matrix.getRowCount();++i){
            int extI = externals[i];    
            int districtI = (int) dTable.getIndexedValueAt(extI, 2);
            
            for(int j=1;j<=matrix.getColumnCount();++j){
                int extJ = externals[j];
                int districtJ = (int) dTable.getIndexedValueAt(extJ, 2);
                
                float value = dMatrix.getValueAt(districtI, districtJ)
                    + matrix.getValueAt(extI,extJ);
                
                dMatrix.setValueAt(districtI, districtJ, value);
                
                
            }
        }
       
        return dMatrix;        
    }     

    /**
     * Generate a return district matrix based on the type
     * of input matrix
     */
    private Matrix generateDistrictMatrix(Matrix matrix){

        //set rows and cols based on input matrix
        if(matrix.getRowCount()==1)
            rows=1;
        else
            rows=numberOfDistricts;
            
        if(matrix.getColumnCount()==1)
            cols=1;
        else
            cols=numberOfDistricts;
            
        String name = new String(matrix.getName()+" district equiv");
        String description =  new String(matrix.getDescription()+" district equiv");
        Matrix dMatrix = new Matrix(name, description,rows, cols);
        return dMatrix;        
        
    }
    
    /** get the number of districts
     *@return the number of districts
     */
    public int getNumberOfDistricts(){
        return numberOfDistricts;
    }

    /** Multiply the matrix by the values in the district matrix
     * @param operandMatrix the matrix to multiply
     * @param districtMatrix the matrix with values by district to multiply
     * @param row If true, rows will be used for district lookup, else columns
     * @return the result matrix
     */
    public Matrix multiply(Matrix operandMatrix, Matrix districtMatrix,
        boolean row){

        int rows = operandMatrix.getRowCount();
        int cols = operandMatrix.getColumnCount();       
        String name = new String(operandMatrix.getName()+" dMultiply "+districtMatrix.getName());
        String desc = operandMatrix.getDescription();
        
        Matrix result = new Matrix(name,desc,rows,cols);
        result.setExternalNumbers(externalNumbers);       
        int district = 0;
        //loop through operandMatrix, multiply by districtMatrix
        for(int i=0;i<rows;++i)
            for(int j=0;j<cols;++j){
                
                int extI = operandMatrix.getExternalNumber(i);
                int extJ = operandMatrix.getExternalNumber(j);
                
                float operand = 0;
                if(row){
                    district = (int) dTable.getIndexedValueAt(extI, 2);
                    operand = districtMatrix.getValueAt(district, 1);
                }else{
                    district = (int) dTable.getIndexedValueAt(extJ, 2);
                    operand = districtMatrix.getValueAt(1, district);
                }     
                float value = operandMatrix.getValueAt(extI,extJ) * operand;

                result.setValueAt(extI,extJ,value);                
            }               
        return result;
    }


    /**
     * Expand the district matrix to a full matrix.
     * 
     * @param districtMatrix
     */
    public Matrix expand(Matrix districtMatrix){
      
        int rows, cols;
        if(districtMatrix.getRowCount()>this.numberOfDistricts)
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);

        if(districtMatrix.getColumnCount()>this.numberOfDistricts)
            throw new MatrixException(MatrixException.INVALID_DIMENSIONS);
      
      
        if(districtMatrix.getRowCount()==1)
            rows = 1;
        else
            rows = dTable.getRowCount();
            
        if(districtMatrix.getColumnCount()==1)
            cols = 1;
        else
            cols = dTable.getRowCount();
                
        Matrix result = new Matrix("","",rows,cols);
        result.setExternalNumbers(externalNumbers);
        
        for(int i=0;i<rows;++i)
            for(int j=0;j<cols;++j){
             
                int extI = result.getExternalNumber(i);
                int extJ = result.getExternalNumber(j);
                int districtI = (int) dTable.getIndexedValueAt(extI,2);
                int districtJ = (int) dTable.getIndexedValueAt(extJ,2);
                float value = districtMatrix.getValueAt(districtI, districtJ);
                result.setValueAt(extI,extJ,value);
                     
            }   
        return result;   
    }    
     
    /**
     * Simple test
     */   
    public static void main(String[] args) {
        
      
        int rows=2634;
        int cols=2634;
        
        District d = new District(new File("/hgac_data/tazdata/district20.csv"));
               
        Matrix m = new Matrix("test","test matrix", rows, cols);
        
        for(int i=1;i<=rows;++i)
            for(int j=1;j<=cols;++j)
                m.setValueAt(i,j, 1);
        
        Matrix dSum = d.getSum(m);

       logger.info("i  j  value");
       logger.info("-----------");        
        for(int i=1;i<=dSum.getRowCount();++i)
            for(int j=1;j<=dSum.getColumnCount();++j)
                logger.info(""+i+" "+j+" "+dSum.getValueAt(i,j));
    
    }       
}
