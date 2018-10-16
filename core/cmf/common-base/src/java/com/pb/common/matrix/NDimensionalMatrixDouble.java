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

/** 
 * NDimensional Matrix 
 *
 * @author    Joel Freedman
 * @version   1.0, 10/22/2002
 *
 */

import org.apache.log4j.Logger;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Serializable;
import java.util.Arrays;
import java.util.StringTokenizer;

public class NDimensionalMatrixDouble implements Cloneable, Serializable{

    public String matrixName;
    protected int dimensions;  // number of dimensions from 1->n
    protected int[] shape; // rectangular; array contains number of elements in each dimension
    protected double[] value;
    protected String[] vectorNames;
    private int[] offset;
    protected boolean trace;
    protected static Logger logger = Logger.getLogger(NDimensionalMatrixDouble.class);

    /**
     * Create an NDimensional for a Matrix.
     * 
     * @param matrix
     */
    public static NDimensionalMatrixDouble createNDMatrixFromMatrix(
            Matrix matrix) {
        double[][] dmatrix = new double[matrix.getRowCount()][matrix
                .getColumnCount()];

        int[] extRowNumbers = matrix.getExternalRowNumbers();
        int[] extColNumbers = matrix.getExternalColumnNumbers();

        for (int r = 0; r < matrix.getRowCount(); ++r) {
            int row = extRowNumbers[r + 1];

            for (int c = 0; c < matrix.getColumnCount(); ++c) {
                int col = extColNumbers[c + 1];

                dmatrix[r][c] = matrix.getValueAt(row, col);
            }
        }

        return new NDimensionalMatrixDouble(matrix.getName(), dmatrix);
    }

    /**
    Creates a rectangular matrix of any dimensions.
     
    @param name                The name of the matrix, used for reports.
    @param matrixDimensions    The number of dimensions of the matrix.
                               Ex: matrixDimensions = 3:  A 3-d matrix will be created.
    @param matrixShape         An array containing the number of elements on each dimension.
    
    **/  
    public NDimensionalMatrixDouble(String name, int matrixDimensions, int matrixShape[]) {
        
        //set name
        matrixName=name;
        
        //set number of dimensions
        dimensions=matrixDimensions;
        
        //initialize vector names
        vectorNames = new String[dimensions];
        
        //check to make sure shape array length is equal to matrixDimensions
        checkLookupArray(matrixShape);
        
        //set number of shapes per dimension
        shape = matrixShape;
        
        calculateOffsets();
        
        initializeValueArray();
       
    }
    /**
    Constructor with no arguments; use to generate undefined NDimensionalMatrixDouble class.
    **/
    public NDimensionalMatrixDouble(){};   
    
    /**
    Constructor to use if reading matrix from file.
    **/
    public NDimensionalMatrixDouble(String fileName){
    
        readMatrixFromTextFile(fileName);    
        
    }

    /**
     * Constructor that takes a Matrix.
     */
    public NDimensionalMatrixDouble(Matrix matrix) {
        int[] shape = {matrix.getRowCount(), matrix.getColumnCount()};
        this.shape = shape;
        matrixName = matrix.getName();
        int[] extRowNumbers = matrix.getExternalRowNumbers();
        int[] extColNumbers = matrix.getExternalColumnNumbers();

        dimensions = 2;
        calculateOffsets();
        initializeValueArray();

        for (int r = 0; r < matrix.getRowCount(); ++r) {
            int row = extRowNumbers[r + 1];
            
            for (int c = 0; c < matrix.getColumnCount(); ++c) {
                int col = extColNumbers[c + 1];
                int[] location = { r, c };
                double value = (double) matrix.getValueAt(row, col);
                
                setValue(value, location);
            }
        }
    }

    /**
     * Constructor to use for constructing from 2-d double array
     * @param name The name of the NDimensionalMatrixDouble
     * @param array  The array to construct from.
     */
    public NDimensionalMatrixDouble(String name, double[][] array){
        
        this.dimensions=2;
        int[] loc = new int[2];
        int[] shape = { array.length,array[0].length };
        this.shape = shape;
        this.matrixName = name;
 
        calculateOffsets();
        
        initializeValueArray();
           
        // Set matrix values
        for (int r=0; r < array.length; r++) {
            for (int c=0; c < array[0].length; c++) {
                loc[0] = r;
                loc[1] = c;
                this.setValue ( (double)array[r][c], loc );
            }
        }        
    }
    

    
    /**
    Return a matrix of integerized values (represented still as doubles)
    from the current matrix of fractional values
    **/
    public NDimensionalMatrixDouble discretize() {
    	
    	double[][] marginals = new double[dimensions][];
        double marginalProduct;
    	int[] loc = new int[dimensions];
        int[] location = null;
        NDimensionalMatrixDouble fracPart = (NDimensionalMatrixDouble) this.clone();

//        logger.info("entering NDimensionalMatrixDouble discretize method");

        // initialize cell potential to 1 - available
        int[] potential = new int[value.length];
        Arrays.fill(potential, 1);


        // initialize an indices array and a values array for sorting
        // fractional values in descending order
        int[] indexLabel = new int[value.length];
        int[] sortValues = new int[value.length];
        int[] index;
        
        // remove the integer parts from the matrix values and discretize the fractional parts
        int totalIntegerPart = 0;
        for(int i=0; i < value.length; i++) {
 
            // set matrix of fractional parts
            fracPart.value[i] -= (int)value[i];
            totalIntegerPart += (int)value[i];
           
            // initialize any zero or negative cells to potential = 0 - unusable
            if (fracPart.value[i] <= (double)0.0){
                potential[i] = 0;
            }
           
        }

        // define a set of marginals for the fractional values in each dimension
        for (int i=0; i < shape.length; i++)
            marginals[i] = fracPart.collapseToVectorAsDouble (i);


        // determine a set of values on which to sort the matrix values
        // the random index is used in order to avoid order bias in discretizing equal cell values
        int intPart3=0;
        for(int i=0; i < value.length; i++) {

            loc = getLocation(i);
            marginalProduct = 1.0f;
            for (int j=0; j < loc.length; j++)
                marginalProduct *= marginals[j][loc[j]];
                
            sortValues[i] = (int)( fracPart.value[i]*marginalProduct*(-1000000) );
        }
        
        
        // sort the matrix elements so they can be processed in order from largest to smallest
        index = indexSort (sortValues);


        // sum total fractions in NDimensionalMatrixDouble
        int totalFractions = (int)(fracPart.getSum() + 0.5f);
            
        // sum total fractions in NDimensionalMatrixDouble
        double matrixTotal = fracPart.getSum();
            
//        logger.info("totalFractions= "+totalFractions);
    
        int k = 0;
        for (int capN=0; capN < totalFractions; capN++) {	    
	    
//            if(capN % 1000 == 0)
//                logger.info("capN= "+capN);
            
			// get the table cell location for the largest table value with potential
            int[] maxLocation = null;
            while ( potential[index[k]] != 1 ) {
                k++;
                // if no cells with potential are left, go through the subset of cells which were not originally
                // 0, and are not currently 1, sum the marginals over all dimensions for each cell, and find
                // the cell with the largest marginal total -- this cell will be the one to set to 1.  Process
                // this cell just like any other normal cell and adjust marginals.  Reset k so that if another
                // hh is to be processed, we'll still be at the end of the list for k.
                if (k >= value.length) {
                    double maxMarginSum = -999999999.9f;
                    maxLocation = new int[dimensions];
                    for (k=0; k < value.length; k++) {
                        if (potential[k] == 3) {
                            location = getLocation(k);
                            double marginSum = 0.0f;
                            for (int i=0; i < location.length; i++)
                                marginSum += marginals[i][location[i]];
                            if (marginSum > maxMarginSum) {
                                maxMarginSum = marginSum;
                                maxLocation = getLocation(k);
                            }
                        }
                    }
                    location = maxLocation;
                    k = totalFractions - 2;
                    break;
                }
            }
            if (maxLocation == null)
                location = getLocation(index[k]);
            
			// set the fractional value of this table cell to 1.0 and
            fracPart.setValue ( 1.0f, location );
            
            // set the potential of this table cell to 2 - selected.
		    potential[index[k]] = 2;


			int start;
			int finish;
			int incr;
			int repeat;

			// set potential to false for all cells along any dimension where marginal is negative
			for (int i=0; i < location.length; i++) {
				marginals[i][location[i]] -= 1.0;

				if ( marginals[i][location[i]] <= 0.000001 ) {
					
					// these indices loop through array values for other dimensions that the one being frozen;
					repeat = shape[i];
					for (int s=i+1; s < location.length; s++)
						repeat *= shape[s];
					
					incr = 1;
					if (i < (shape.length - 1)) {
						incr = shape[shape.length - 1];
						for (int s=shape.length - 2; s > i; s--)
							incr *= shape[s];
					}
					
					for (int m=0; m < value.length; m += repeat) {
						start = m + location[i]*incr;
						finish = start + incr;
						
                        // set potential of this cell to 3 - unavailable
	                    for (int n=start; n < finish; n++)
                            if (potential[n] == 1)
                                potential[n] = 3;   

					}
				}
			}

            k++;	
		}

		
		for (int n=0; n < fracPart.value.length; n++)
			fracPart.value[n] = (int)value[n] + (int)fracPart.value[n];
                        

        totalFractions = (int)fracPart.getSum();

//		logger.info("Leaving the NDimensional Matrix discretize method");
		return fracPart;
    }      



    /**
    Used to calculate offsets based on matrix shape 
    **/
    private void calculateOffsets(){
        
        //calculate offsets for indexing
        offset=new int[shape.length];
        offset[offset.length-1]=1;
          
        //calculate offsets for all other dimensions
        for(int d=offset.length-2;d>=0;--d)
            offset[d]=offset[d+1]*shape[d+1];
    }      
    private void initializeValueArray(){
        //initialize value array
        int totalShape=1;
        for(int i=0;i<shape.length;++i)
            totalShape *= shape[i];           
        
        value=new double[totalShape];
    }      
    /** 
    Get shape of matrix for a given dimension.
    @param dimension  The dimension to get shape for.
    **/
    public int getShape(int dimension){
        if(dimension>shape.length){
            logger.error("Error: Tried to get shape for dimension ("+dimension+") that is greater than number of "
            +"dimensions of NDimensionalMatrixDouble "+matrixName+" ("+shape.length+")");
            System.exit(1);
        }
          
        return this.shape[dimension] ;      
    }
    /** 
    Get array of shapes for all dimensions.
    **/
    public int[] getShape(){
          
        return this.shape;      
    }
     /** 
    Get the number of elements in this matrix.
    **/
    public int getNumberOfElements(){
          
        return value.length;      
    }
   /** 
    Get number of dimensions for this matrix.
    **/
    public int getDimensions(){
        return dimensions;
    }
    /**
    Set trace for this NDimensionalMatrixDouble to write debug to System.out
    **/
    public void setTrace(boolean tf){
        trace=tf;
    }
    /** 
    Return a copy of this NDimensionalMatrixDouble.
    **/
    public Object clone(){
        NDimensionalMatrixDouble o = null;
        try{
            o= (NDimensionalMatrixDouble)super.clone();
            
            
        }catch(CloneNotSupportedException e){
            logger.error("Error: NDimensionalMatrixDouble can't clone");
            System.exit(1);
        }
        //clone references
        o.shape = new int[this.shape.length];
        o.value = new double[this.value.length];
        
        if(this.vectorNames!=null){
            o.vectorNames = new String[this.vectorNames.length];
            System.arraycopy(this.vectorNames,0,o.vectorNames,0,this.vectorNames.length); 
        }
        o.offset = new int[this.offset.length];
        
         
        System.arraycopy(this.shape,0,o.shape,0,this.shape.length);
        System.arraycopy(this.value,0,o.value,0,this.value.length);
        System.arraycopy(this.offset,0,o.offset,0,this.offset.length);     
        return o;
    }
    /**
    Sets a value in the matrix.
    
    @param inValue    The value of the cell referred to in the location array.
    @param location   An array specifying the coordinates of the cell. 
                      Ex: location = {5,3,9} 
                      changes the value at cell i=5, j=3, k=9
    **/
    public void setValue(double inValue, int[] location){
        //check location array
        checkLookupArray(location);
        
        value[getIndex(location)]=inValue;
        
    }
        
    /**
    Returns a value from the matrix.
    
    @param location   An array specifying the coordinates of the cell. 
                      Ex: location = {5,3,9} 
                      changes the value at cell i=5, j=3, k=9
    **/
    public double getValue(int[] location){
        //check location array
        checkLookupArray(location);
         
        return value[getIndex(location)];
    }
    /**
    Sets all the values in the matrix to a value.
    
    @param val   The number to set the matrix to.
    **/
    public void setMatrix(double val){
        
        for(int i=0;i<value.length;++i)
            value[i]=val;
    }
    /**
    Returns a reference to the NDimensional matrix.  To get a copy of the matrix use clone().
    
    **/
    public NDimensionalMatrixDouble getMatrix(){
        
        return this;
    }

    /**
     * Get values as a Matrix.
     * 
     * Note that the zone numbering system is not set.
     */
    public Matrix getValuesAsMatrix() {
        Matrix matrix;

        if (dimensions != 2) {
            String eMsg = "Matrix class only support matrices with tow dimensions.";
            logger.fatal(eMsg);
            throw new MatrixException(eMsg);
        }

        int nRows = shape[0];
        int nCols = shape[1];

        matrix = new Matrix(nRows, nCols);

        for (int r = 0; r < nRows; ++r) {
            int row = r + 1;
            for (int c = 0; c < nCols; ++c) {
                int col = c + 1;
                int[] location = { r, c };
                float value = (float) getValue(location);

                matrix.setValueAt(row, col, value);
            }
        }

        return matrix;
    }

    /**
     * Get the values of a 2D NDimensionalMatrix using external numbers.
     * 
     * @param extRowNumbers
     * @param extColumnNumbers
     * @return
     */
    public Matrix getValuesAsMatrix(int[] extRowNumbers, int[] extColumnNumbers) {
        Matrix matrix = getValuesAsMatrix();

        matrix.setExternalNumbers(extRowNumbers, extColumnNumbers);
        return matrix;
    }

    /**
     * Get the values of a square 2D NDimensionalMatrixDouble with set external
     * numbers.
     * 
     * @param extNumbers
     * @return
     */
    public Matrix getValuesAsMatrix(int[] extNumbers) {
        return getValuesAsMatrix(extNumbers, extNumbers);
    }
    
    /**
     * 
     * Returns a vector from the matrix.
     * 
     * @param vectorLocation An array specifying the location of the vector. Ex.
     *            vectorLocation= {1,2,-1} returns the vector for i=1, j=2, all
     *            k's. (-1 signifies the dimension to return)
     */
    public RowVector getVector(int[] vectorLocation){
        
        double[] dArray = getVectorAsDouble(vectorLocation);
        float[] fArray = new float[dArray.length];
        for(int i=0;i<dArray.length;++i)
            fArray[i]=(float)dArray[i];
            
        return new RowVector(fArray);
    }
    
    /** 
    
    Returns a vector from the matrix as a double array.
    
    @param vectorLocation   An array specifying the location of the vector.
                            Ex. vectorLocation= {1,2,-1}
                            returns the vector for i=1, j=2, all k's.
                            (-1 signifies the dimension to return)
    **/
    public double[] getVectorAsDouble(int[] vectorLocation){
        
        checkLookupArray(vectorLocation);
        int dimension0=-1;
        
        if(trace){
            logger.info("Getting vector for vectorLocation {");
            for(int i=0;i<vectorLocation.length;++i){
                logger.info(" "+vectorLocation[i]);
                if((i+1)<vectorLocation.length)
                    logger.info(",");
            }
            logger.info("}");
       }
                
        
        //find the 0 dimension
        for(int i=0;i<vectorLocation.length;++i){
            if(vectorLocation[i]==-1){
                dimension0=i;
                break;
            }
        }
        
        if(dimension0==-1){
            logger.error("Error: tried to getVector in matrix "+matrixName+
                " with incorrectly specified location");
            System.exit(1);
        }               

        //Initialize the size of the double array to the vector size
        double[] outVector = new double[shape[dimension0]];
        int[] lookupVector = new int[vectorLocation.length];
        System.arraycopy(vectorLocation,0,lookupVector,0,vectorLocation.length);
        lookupVector[dimension0]=0;        
        
        if(trace)
            logger.info("Getting vector for dimension "+dimension0+" that has "+outVector.length+" elements");
        //get the values for this dimension   
        for(int i=0;i<outVector.length;++i){
        
            if(trace){
                logger.info("Getting value for location ");
                for(int j=0;j<lookupVector.length;++j)
                    logger.info(" "+j+"="+lookupVector[j]+" ");
                logger.info(" ");
            } 
            
            //get the value
            outVector[i]=getValue(lookupVector);
            
            
            //next value in vector   
            ++lookupVector[dimension0];
        }
        return outVector;
        
    }
    /** 
    Sets a vector in the matrix.
    
    @param vectorLocation   An array specifying the location of the vector.
                            Ex. vectorLocation= {1,2,-1}
                            sets the vector for i=1, j=2, all k's.
                            (-1 signifies the dimension of the vector to set)
    @param inVector         An array of values to set the vector to.
    **/
    public void setVector(double[] inVector, int[] vectorLocation){
        
        checkLookupArray(vectorLocation);
        int dimension0=-1;
        
        //find the 0 dimension
        for(int i=0;i<vectorLocation.length;++i)
            if(vectorLocation[i]==-1){
                dimension0=i;
                break;
            }
        
        if(dimension0==-1){
            logger.info("Error: tried to getVector in matrix "+matrixName+
                " with incorrectly specified location");
            System.exit(1);
        }               

        int[] lookupVector = new int[vectorLocation.length];
        System.arraycopy(vectorLocation,0,lookupVector,0,vectorLocation.length);
        lookupVector[dimension0]=0;
        //set the values for this dimension   
        for(int i=0;i<inVector.length;++i){
        
            //set the value
            setValue(inVector[i],lookupVector);
            
            //next value in vector   
            ++lookupVector[dimension0];
        }
        
    }
    /**
    Returns the sum of the matrix
    **/
    public double getSum(){
        
        double sum=0;
        for(int i=0;i<value.length;i++)
            sum+=value[i];
        return sum;
    }  
    /** 
    Returns the sum of a vector
    @param vectorLocation   An array specifying the location of the vector.
                            Ex. vectorLocation= {1,2,-1}
                            returns the sum for vector at i=1, j=2, all k's.
                            (-1 signifies the dimension to sum across)
    **/  
    public double getVectorSum(int[] vectorLocation){
        
        double[] vector = getVectorAsDouble(vectorLocation);
        double vectorSum=0;
        for(int i=0; i< vector.length;++i)
            vectorSum += vector[i];
        return vectorSum;    
        
    }    
    /**
    Sums the matrix across all dimensions except for vectorLocation
    and returns vector of sums for the vectorLocation
    @param dimension        The dimension of the vector to be returned.
    **/  
    public RowVector collapseToVector(int dimension){

        RowVector vectorSum = new RowVector(shape[dimension]);
        int[] location = new int[dimensions];
    
        for(int e=0;e<value.length;++e){
                        
            location = getLocation(e);
            vectorSum.setValueAt(location[dimension],
                (float)(getValue(location)+vectorSum.getValueAt(location[dimension])));                  
            
        }
         return vectorSum;
               
    }
   /**
    Sums the matrix across all dimensions except for vectorLocation
    and returns an array of sums for the vectorLocation
    @param dimension        The dimension of the vector to be returned.
    **/  
    public double[] collapseToVectorAsDouble(int dimension){
        
        double vectorSum[]=new double[shape[dimension]];
        int[] location = new int[dimensions];
    
        for(int e=0;e<value.length;++e){
            location = getLocation(e);
            vectorSum[location[dimension]] += value[e];
        }
         return vectorSum;
    }
    /** 
    Multipy only one vector in the matrix by a vector and return the result.
   
    @param operandVector      An array of values to multiply.
    @param vectorLocation     An array specifying the location of the vector.
                              Ex. vectorLocation= {1,2,-1}
                              returns the matrix that is the product of the
                              operandVector multplied by across i=1, j=2, all k's.
                              (-1 signifies the dimension to multiply across)
    **/ 
    public NDimensionalMatrixDouble vectorMultiply(RowVector operandVector, int[] vectorLocation) {
    
        double[] vector = getVectorAsDouble(vectorLocation);
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.size()){
            logger.info("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            logger.info("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.size(), vector.length);
        }
        for(int i=0;i<minLength;++i)
            vector[i] *= operandVector.getValueAt(i);
            
        result.setVector(vector, vectorLocation);
    
        return result;
    }
                
    /** 
    Multipy only one vector in the matrix by an vector and return the result.
   
    @param operandVector      An array of values to multiply.
    @param vectorLocation     An array specifying the location of the vector.
                              Ex. vectorLocation= {1,2,-1}
                              returns the matrix that is the product of the
                              operandVector multplied by across i=1, j=2, all k's.
                              (-1 signifies the dimension to multiply across)
    **/ 
    public NDimensionalMatrixDouble vectorMultiply(double[] operandVector, int[] vectorLocation) {
    
        double[] vector = getVectorAsDouble(vectorLocation);
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.length){
            logger.info("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            logger.info("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.length, vector.length);
        }
        for(int i=0;i<minLength;++i)
            vector[i] *= operandVector[i];
            
        result.setVector(vector, vectorLocation);
    
        return result;
    }
   /** 
    Operate on only one vector in the matrix by a vector and return the result.
   
    @param operandVector      An array of values to multiply.
    @param vectorLocation     An array specifying the location of the vector.
                              Ex. vectorLocation= {1,2,-1}
                              returns the matrix that is the product of the
                              operandVector multplied by across i=1, j=2, all k's.
                              (-1 signifies the dimension to multiply across)
    @param operand            one of:"*","/","+","-"
    **/ 
    public NDimensionalMatrixDouble vectorOperate(double[] operandVector, int[] vectorLocation, String operand) {
    
        double[] vector = getVectorAsDouble(vectorLocation);
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.length){
            logger.info("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            logger.info("Common matrix elements will be operated on");
            minLength=Math.min(operandVector.length, vector.length);
        }
        if(operand.compareTo("*")==0){
            for(int i=0;i<minLength;++i)
                vector[i] *= operandVector[i];
        }else if(operand.compareTo("/")==0){
            for(int i=0;i<minLength;++i)
                vector[i] /= operandVector[i];
        }else if(operand.compareTo("+")==0){
            for(int i=0;i<minLength;++i)
                vector[i] += operandVector[i];
        }else if(operand.compareTo("-")==0){
                for(int i=0;i<minLength;++i)
                    vector[i] -= operandVector[i];
        }else{
            logger.error("Error:  Operand "+operand+" not recognized as valid operation");
            System.exit(1);
        }
        result.setVector(vector, vectorLocation);
    
        return result;
    }

    /**
    Collapse a dimension by adding it's values to the other dimensions and return
    the resulting NDimensionalMatrix with 1 less dimension than the original matrix.
    @param dimensionToCollapse  The number of the dimension to collapse (0-init)
    **/
    public NDimensionalMatrixDouble collapseDimension(int dimensionToCollapse){    

        if(dimensions==1||dimensionToCollapse>dimensions){
            logger.error("Error: Attempting to collapse dimension "+dimensionToCollapse+
                " of "+dimensions+"-dimensional matrix");
            System.exit(1);
        }
        //create the new matrix
        int resultDimensions = this.dimensions-1;
        int[] resultShape= new int[resultDimensions];
        int j=0;
        for(int i=0;i<shape.length;++i){
            if(i==dimensionToCollapse)
                continue;
            resultShape[j]=this.shape[i];
            ++j;
        }
        NDimensionalMatrixDouble result = new NDimensionalMatrixDouble(this.matrixName, resultDimensions,resultShape);
        //create an array with the number of elements = matrix dimensions
        int[] location= new int[dimensions];
        location[dimensionToCollapse]=-1;
        
        //create lower and upper bound arrays (lower and upper bounds for dimension of vector = -1)
        int[] lower = new int[dimensions];
        lower[dimensionToCollapse]=-1;
        
        int[] upper = new int[dimensions];
        for(int u=0;u<upper.length;++u){
            if(u==dimensionToCollapse) 
                upper[u] = -1;
            else
                upper[u] = shape[u]-1;
        }
        
        result=recursivelyVectorCollapse(0, location, lower, upper,result);
        
        return result;
    }
        
    
    /**
    Multiply the entire matrix by a value and return the result.
    
    @param oValue   The value to multiply the matrix by.
        
    **/
    public NDimensionalMatrixDouble matrixMultiply(double oValue){
        
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        
        for(int i=0;i<result.value.length;++i)
            result.value[i] *= oValue;
            
        return result;
    }

    /**
    Perform an operation on the entire matrix by a value and return the result.
    
    @param oValue   The value to multiply the matrix by.
    @param operand  one of:"*","/","+","-"

    **/
    public NDimensionalMatrixDouble matrixOperate(double oValue, String operand){
        
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        
        if(operand.compareTo("*")==0){
            for(int i=0;i<result.value.length;++i)
                result.value[i] *= oValue;
        }else if(operand.compareTo("/")==0){
            for(int i=0;i<result.value.length;++i)
                result.value[i] /= oValue;
        }else if(operand.compareTo("+")==0){
            for(int i=0;i<result.value.length;++i)
                result.value[i] += oValue;
        }else if(operand.compareTo("-")==0){
                for(int i=0;i<result.value.length;++i)
                result.value[i] -= oValue;
        }else{
            logger.error("Error:  Operand "+operand+" not recognized as valid operation");
            System.exit(1);
        }
        
        return result;
    }
    
    /**
    Perfom an operation on the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
    @param operand  one of:"*","/","+","-"
        
    **/
    public NDimensionalMatrixDouble matrixOperate(RowVector operandVector, int vectorDimension, String operand){

        float[] oFloatVector = operandVector.copyValues1D();
        double[] oDoubleVector= new double[oFloatVector.length];
        for(int i=0;i<oDoubleVector.length;++i)
            oDoubleVector[i]=(float)oFloatVector[i];
        
        return matrixOperate(oDoubleVector,vectorDimension,operand);
    
    }
    /**
    Multiply the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
        
    **/
    public NDimensionalMatrixDouble matrixMultiply(RowVector operandVector, int vectorDimension){

        float[] oFloatVector = operandVector.copyValues1D();
        double[] oDoubleVector= new double[oFloatVector.length];
        for(int i=0;i<oDoubleVector.length;++i)
            oDoubleVector[i]=(float)oFloatVector[i];
        
        return matrixMultiply(oDoubleVector,vectorDimension);
    
    }
    /**
    Multiply the entire matrix by an NDimensionalMatrixDouble and return the result.
    
    @param operandMatrix     The NDimensionalMatrixDouble to multiply the matrix by.
        
    **/
    public NDimensionalMatrixDouble matrixMultiply(NDimensionalMatrixDouble operandMatrix){

        if(operandMatrix.shape != this.shape){
            logger.error("Error: The operand matrix is not of equal size as this matrix");
            System.exit(1);
        }
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();
        for(int i=0;i<value.length;++i)
            result.value[i]=operandMatrix.value[i]*this.value[i];
        
        return result;
    
    }
    /**
    Multiply the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
        
    **/
    public NDimensionalMatrixDouble matrixMultiply(double[] operandVector, int vectorDimension){
        
        if(trace)
            logger.info("Attempting to multiply vector of length "+operandVector.length
            +" against dimension "+vectorDimension);
            
        if((dimensions-1)<vectorDimension){
            logger.error("Error: Attempting to matrixMultiply a vector across a dimension ("+
                vectorDimension+") that is greater than the number of dimensions ("+dimensions+") in"
                +" the matrix "+matrixName);
            System.exit(1);
        }
        
        int minLength=operandVector.length;
        if(operandVector.length!=shape[vectorDimension]){
            logger.info("Operand vector length not equal to matrix vector length in matrix "+
                matrixName);
            logger.info("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.length, shape[vectorDimension]);
        }
       
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();

        //create an array with the number of elements = matrix dimensions
        int[] location= new int[dimensions];
        location[vectorDimension]=-1;
        
        //create lower and upper bound arrays (lower and upper bounds for dimension of vector = -1)
        int[] lower = new int[dimensions];
        lower[vectorDimension]=-1;
        
        int[] upper = new int[dimensions];
        for(int u=0;u<upper.length;++u){
            if(u==vectorDimension) 
                upper[u] = -1;
            else
                upper[u] = shape[u]-1;
        }
        
        result=recursivelyVectorMultiply(0, location, lower, upper, operandVector,result);
        
        return result;
    }
    /**
    Operate on the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
    @param operand  one of:"*","/","+","-"
        
    **/
    public NDimensionalMatrixDouble matrixOperate(double[] operandVector, int vectorDimension, String operand){
        
        if(trace)
            logger.info("Attempting to multiply vector of length "+operandVector.length
            +" against dimension "+vectorDimension);
            
        if((dimensions-1)<vectorDimension){
            logger.error("Error: Attempting to matrixMultiply a vector across a dimension ("+
                vectorDimension+") that is greater than the number of dimensions ("+dimensions+") in"
                +" the matrix "+matrixName);
            System.exit(1);
        }
        
        int minLength=operandVector.length;
        if(operandVector.length!=shape[vectorDimension]){
            logger.info("Operand vector length not equal to matrix vector length in matrix "+
                matrixName);
            logger.info("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.length, shape[vectorDimension]);
        }
       
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();

        //create an array with the number of elements = matrix dimensions
        int[] location= new int[dimensions];
        location[vectorDimension]=-1;
        
        //create lower and upper bound arrays (lower and upper bounds for dimension of vector = -1)
        int[] lower = new int[dimensions];
        lower[vectorDimension]=-1;
        
        int[] upper = new int[dimensions];
        for(int u=0;u<upper.length;++u){
            if(u==vectorDimension) 
                upper[u] = -1;
            else
                upper[u] = shape[u]-1;
        }
        
        result=recursivelyVectorOperate(0, location, lower, upper, operandVector,operand,result);
        
        return result;
    }
    protected NDimensionalMatrixDouble recursivelyVectorMultiply(int k, int[] loc, int[] lower, int[] upper,double[] ov,
        NDimensionalMatrixDouble result){
        
        if(k==dimensions){
            result=result.vectorMultiply(ov,loc);
            return result;
        }else{
            for(loc[k] = lower[k];loc[k] <= upper[k];++loc[k]){
                result=recursivelyVectorMultiply((k+1),loc, lower,upper, ov,result);
            }
        }
        return result;
    }
            
    /** 
    TO colllapse the NDimensionalMatrix, this recursive method is called.  It calls the
    getVectorSum() method for the dimension to collapse for all other dimensions, storing
    the result in the appropriate location in the resultMatrix, and returns the result
    when all values for all dimensions have been exhausted.
    **/
    protected NDimensionalMatrixDouble recursivelyVectorCollapse(int k, int[] loc, int[] lower, int[] upper,
        NDimensionalMatrixDouble resultMatrix){
        
        if(k==dimensions){
            //set location for result of vector collapse
            int[] resultLocation = new int[resultMatrix.dimensions];
            int j=0;
            for(int i=0;i<loc.length;++i){
                if(loc[i]==-1)
                    continue;
                resultLocation[j]=loc[i];
                ++j;
            } 
            resultMatrix.setValue(getVectorSum(loc),resultLocation);
            return resultMatrix;
        }else{
            for(loc[k] = lower[k];loc[k] <= upper[k];++loc[k]){
                resultMatrix=recursivelyVectorCollapse((k+1),loc, lower,upper, resultMatrix);
            }
        }
        return resultMatrix;
    }
    
    protected NDimensionalMatrixDouble recursivelyVectorOperate(int k, int[] loc, int[] lower, int[] upper,double[] ov,
        String operand,NDimensionalMatrixDouble result){
        
        if(k==dimensions){
            result=result.vectorOperate(ov,loc,operand);
            return result;
        }else{
            for(loc[k] = lower[k];loc[k] <= upper[k];++loc[k]){
                result=recursivelyVectorOperate((k+1),loc, lower,upper, ov,operand,result);
            }
        }
        return result;
    }
    /**
    Multiply the entire matrix by a set of vectors and return the result.
    
    @param operandMatrix     A 2-d matrix containing operands to multiply the matrix by.
    The length of the operandMatrix first dimension should be equal to the number of dimensions 
    of the NDimensionalMatrixDouble object, and the length of the second dimensions should be equal to 
    the shape of the NDimensionalMatrixDouble object for each dimension (ie can be non-rectangular). 
    Each element of the operand matrix is a factor to apply to the appropriate vector of the 
    NDimensionalMatrixDouble object.  This method can be used in matrix balancing, for example.
    **/
    
    public NDimensionalMatrixDouble matrixMultiply(double operandMatrix[][]){
        
        if(operandMatrix.length!=dimensions){
            logger.error("Error: Trying to matrix multiply operand matrix whose first "
            +"dimension (size "+operandMatrix.length+") is not equal to number of dimensions "
            +"of NDimensionalMatrixDouble "+matrixName+"("+dimensions+")");
            System.exit(1);
        }
        
        NDimensionalMatrixDouble result = (NDimensionalMatrixDouble) this.clone();

        for(int d=0;d<dimensions;++d){
        
            if(operandMatrix[d].length!=result.shape[d]){
                logger.error("Error: Trying to matrix multiply operand matrix whose shape "
                +"is not equal to shape of NDimensionalMatrixDouble "+matrixName);
                System.exit(1);
            }
            
            result = result.matrixMultiply(operandMatrix[d], d);
            
        }

        return result;
        
    }
    /** 
    Read an N-DimensionalMatrix from an ASCII text file 
    @param fileName  The path&name of the file.
    
    Note: the file can be either space, comma, or tab-separated.
    The name of the matrix defaults to the name of the file.
    **/  
    public void readMatrixFromTextFile(String fileName){
        String s;
        String d = new String(); 
        int index=0;       
        try {
            //first run through file, determine shape of matrix 
            BufferedReader br = new BufferedReader(new FileReader(fileName));
            while ((s = br.readLine()) != null) {
                if (s.startsWith(";")) continue;      // a comment card
                s=s.trim();
                ++index;
                if(index==1){
                    logger.debug("Scanning text matrix file "+fileName);
                    //find out what the delimiter is
                    if(s.indexOf(",")!=-1){
                        logger.debug(" in comma-delimited format");
                        d = ",";
                    }else if(s.indexOf(" ")!=-1){
                        logger.debug(" in space-delimited format");
                        d = " ";
                    }else{
                        logger.debug(" in tab-delimited format");
                        d="\t";
                    }
                    logger.debug("");
                   
                }
                StringTokenizer st = new StringTokenizer(s,d);
                if(index==1){
                    dimensions=st.countTokens()-1;
                    shape= new int[dimensions];
                    matrixName=fileName;
                }
            
                int token=0;
                while(st.hasMoreTokens() && token<dimensions){
                    shape[token]=Math.max(shape[token],Integer.parseInt(st.nextToken())+1);
                    ++token;
                }
            }
            //housekeeping
            calculateOffsets();
            initializeValueArray();
            
            //now run through file, setting matrix values
            int[] location = new int[dimensions]; 
            br = new BufferedReader(new FileReader(fileName));
            while ((s = br.readLine()) != null) {
                if (s.startsWith(";")) continue;      // a comment card
                s=s.trim();
                StringTokenizer st = new StringTokenizer(s,d);
                logger.debug(s);
                int token=0;
                while(st.hasMoreTokens() && token<dimensions){
                    location[token]= new Integer(st.nextToken()).intValue();
                    ++token;
                }
                double inValue=new Double(st.nextToken()).doubleValue();
                this.setValue(inValue,location); 
            }
            logger.debug("");
            
            
            
            
       } catch (IOException e) { e.printStackTrace(); }
    }

    /**
    Print the value with the delimiter to System.out.
    
    @param location   The location of the value
    @param delimiter  The delimiter to use to separate indices.
    
    Ex:  for a 2-d matrix, will print values such as:
    0  0  23.2
    0  1  98.3
    0  2  23.4
    0  3  14.3
    1  0  15.1
    when delimiter is a string "  "
    **/
    public void printValueDelimited(int[] location, String delimiter){
        
        String outLine = new String();
        for(int i=0;i<location.length;++i)
            outLine = new String(outLine+location[i]+delimiter);

        logger.info(outLine+getValue(location));
    }
        
    /**
    Print the value with the delimiter to file.
    
    @param location   The location of the value
    @param delimiter  The delimiter to use to separate indices.
    
    Ex:  for a 2-d matrix, will print values such as:
    0  0  23.2
    0  1  98.3
    0  2  23.4
    0  3  14.3
    1  0  15.1
    when delimiter is a string "  "
    **/
    public void printValueDelimited(int[] location, String delimiter, BufferedWriter bw){
        
        String outLine = new String();
        for(int i=0;i<location.length;++i)
            outLine = new String(outLine+location[i]+delimiter);
        
        try{
            bw.write(outLine+getValue(location)+"\n");
        }catch(IOException e){
            e.printStackTrace();
        } 
    }
    /** 
    Print the entire matrix with the delimiter to System.out.
    
    @param delimiter  The delimiter to use to separate indices.
    
    **/    
    public void printMatrixDelimited(String delimiter){
        
        int currentDimension=shape.length-1;
 
        for(int i=0;i<value.length;++i){
            int[] location = getLocation(i);
            printValueDelimited(location,delimiter);
        }           
     }

    /** 
    Print the entire matrix with the delimiter to print file.
    
    @param delimiter  The delimiter to use to separate indices.
    
    **/    
    public void printMatrixDelimited(String delimiter, String fileName){
        
        try {
            //first run through file, determine shape of matrix 
            BufferedWriter bw = new BufferedWriter(new FileWriter(fileName));

            for(int i=0;i<value.length;++i){
               int[] location = getLocation(i);
                printValueDelimited(location,delimiter,bw);
            }           
 
 
            bw.flush();
       } catch (IOException e) { e.printStackTrace(); }


     }



    private void checkLookupArray(int[] lookupArray){
        //check to make sure location array length is equal to matrixDimensions
        if(lookupArray.length!=dimensions){
            // check to make sure location array length is equal to matrixDimensions
            if (lookupArray.length != dimensions) {
                String eMsg = "Fatal error:  location length not equal to number "
                        + "of dimensions specified in matrix " + matrixName;

                logger.fatal(eMsg);
                logger.fatal("look-up array has length of " + lookupArray.length
                        + " and the expected dimensions is " + dimensions);
                throw new MatrixException(eMsg);
            }
        }    

    }    
    
    private int getIndex(int[] location){
     
        int index=0;
        
        if(dimensions==1){
            index=location[0];
            return index;
        }
        else if(dimensions>=2){
 
            //calculate index
            for(int d=0;d<location.length;++d)
                index +=location[d]*offset[d];
        }
        return index;
                  
    }
    private int[] getLocation(int index){
        
        int[] location = new int[shape.length];
        
        if(index>value.length-1){
            logger.error("Error: Index value ("+index+") in calculateLocation() "
            +" is greater than number of elements in matrix "+matrixName);
            System.exit(1);
        }         
            
        if(dimensions==1){
            location[0]=index;
            return location;
        }else if(dimensions==2){
            
            location[0]= index/shape[1]; 
            location[1]= (index % shape[1]);  
            
        }else if(dimensions>2){
            int search=index;
            int d=0;
            while(search>0){
                if(search>=offset[d]){
                    ++location[d];
                        search = search-offset[d];
                }else{
                    ++d;
                }
            }
        }
        return location;     
    }
     
        /*
     */

	/**
	 * take an array of integer values and return an array of indices to the sorted values
	 * 
	 **/
    public static int[] indexSort (int[] sortData) {
    	
    	int[] index = new int[sortData.length];
    	for (int i=0; i < sortData.length; i++)
    		index[i] = i;
    		
        quickIndexSort (0, sortData.length - 1, sortData, index);
        
        return index;
    }

    private static int[] quickIndexSort (int lo, int hi, int[] sortData, int[] index) {

        int i, j;
        int tmp;

        if (hi > lo) {
            tmp = sortData[index[hi]];
            i = lo - 1;
            j = hi;
            while (true) {
                while (lessThan(sortData[index[++i]], tmp))
                    ;
                while (j > 0) {
                    if (lessThanOrEqual(sortData[index[--j]], tmp))
                        break;
                }
                if (i >= j)
                    break;
                swapIndex (i, j, index);
            }
            swapIndex (i, hi, index);
            quickIndexSort (lo, i-1, sortData, index);
            quickIndexSort (i+1, hi, sortData, index);
        }
        
        return index;
    }

    private static void swapIndex (int a, int b, int[] index) {
        int tmp = index[a];
        index[a] = index[b];
        index[b] = tmp;
    }

    private static boolean lessThan (int a, int b) {
        return(a < b);
    }

    private static boolean lessThanOrEqual (int a, int b) {
        return(a <= b);
    }
    
    
    /**
    for testing
    **/

    public static void main(String[] args){
        
        System.out.println("Testing NDimensional Matrix Class");
        
        System.out.println("Create a 2-D Matrix: {3,8}");
        
        int[] dim={3,8};
        NDimensionalMatrixDouble matrix2d=new NDimensionalMatrixDouble("matrix2d",2,dim);
        System.out.println("matrix2d dimensions: "+matrix2d.getDimensions());
        System.out.print("matrix2d shape: ");
        for(int i=0;i<matrix2d.getDimensions();++i)
            System.out.print(matrix2d.getShape(i)+" ");
        System.out.println();
        System.out.println("matrix2d number of elements: "+matrix2d.getNumberOfElements());   
        
        System.out.println("Setting matrix values ((i+1)*(j+1)*(j+1))");
        for(int i=0;i<dim[0];++i)
            for(int j=0;j<dim[1];++j){
                    int loc[] = {i,j};
                    double val=((i+1)*(j+1)*(j+1));
                    System.out.println("i "+i+" j "+j+" : "+val);
                    matrix2d.setValue( val, loc);
                }       
        
        System.out.println("Printing matrix values  ((i+1)*(j+1)*(j+1))");
        matrix2d.printMatrixDelimited("  ");
         
        System.out.println("Getting a row from matrix2d for i=2");
        int[] lookupRow2d = {2,-1};
        double[] row2d=matrix2d.getVectorAsDouble(lookupRow2d);
        for(int i=0;i<row2d.length;++i)
            System.out.println(i+" "+row2d[i]);
            
        System.out.println("Sum of matrix2d is "+matrix2d.getSum());
        
        System.out.println("Getting location for values in matrix2d");
        for(int v=0;v<matrix2d.getNumberOfElements();++v){
            int[] loc = matrix2d.getLocation(v);
            System.out.println(loc[0]+" "+loc[1]);
        }       
 
        System.out.println("-----------------------------");       
                
        System.out.println("Create a 3-D Matrix: {3,5,2}");
        
        int[] dim3={3,5,2};
        NDimensionalMatrixDouble matrix3d=new NDimensionalMatrixDouble("matrix3d",3,dim3);
        System.out.println("matrix3d dimensions: "+matrix3d.getDimensions());
        System.out.print("matrix3d shape: ");
        for(int i=0;i<matrix3d.getDimensions();++i)
            System.out.print(matrix3d.getShape(i)+" ");
        System.out.println();
        System.out.println("matrix3d number of elements: "+matrix3d.getNumberOfElements());   
        
        System.out.println("Setting matrix values ((i+1)*(j+1)+(i+1))*(k+1)");
        for(int i=0;i<dim3[0];++i)
            for(int j=0;j<dim3[1];++j)
                for(int k=0;k<dim3[2];++k){
                    int loc[] = {i,j,k};
                    double val=((i+1)*(j+1)+(i+1))*(k+1);
                    System.out.println("i "+i+" j "+j+" k "+k+" : "+val);
                    matrix3d.setValue( val, loc);
                }       
        
        System.out.println("Printing matrix values ((i+1)*(j+1)+(i+1))*(k+1)");
 
        for(int i=0;i<dim3[0];++i)
            for(int j=0;j<dim3[1];++j)
                for(int k=0;k<dim3[2];++k){
                    int loc[] = {i,j,k};
                    System.out.println("i "+i+" j "+j+" k "+k+" : "+matrix3d.getValue(  loc));
                }       
        matrix3d.printMatrixDelimited("  ");
       
        System.out.println("Getting a vector from matrix3d for i=2 j=3 all k");
        int[] lookupVector3d = {2,3,-1};
        double[] vector3d=matrix3d.getVectorAsDouble(lookupVector3d);
        for(int i=0;i<vector3d.length;++i)
            System.out.println(i+" "+vector3d[i]);
            
        System.out.println("Sum of vector from matrix3d for i=2, j=3, all k is: "+matrix3d.getVectorSum(lookupVector3d));
        
        System.out.println("Multiplying matrix3d for i=2 j=3 by the vector");
        matrix3d.vectorMultiply(vector3d,lookupVector3d);
        for(int i=0;i<vector3d.length;++i)
            System.out.println(i+" "+vector3d[i]);
        
        matrix3d.setTrace(true);    
        System.out.println("Getting a collapsed vector for dimension 0 from matrix3d");
        double[] collapsedDimension0 = matrix3d.collapseToVectorAsDouble(0);
        System.out.println("Multiplying vector across entire matrix3d");
        NDimensionalMatrixDouble result = matrix3d.matrixMultiply(collapsedDimension0,0); 
        result.printMatrixDelimited(" ");
       
        matrix3d.setTrace(false);
        System.out.println("Collapsing 2nd Dimension from result");
        NDimensionalMatrixDouble collapsedResult = result.collapseDimension(1);
        collapsedResult.printMatrixDelimited(" ");
       
       /*
            
        System.out.println("-----------------------------");       

        System.out.println("Create a 4-D Matrix: {2,3,2,4}");
        
        int[] dim4={20,3,6,4};
        NDimensionalMatrixDouble matrix4d=new NDimensionalMatrixDouble("matrix4d",4,dim4);
        System.out.println("matrix4d dimensions: "+matrix4d.getDimensions());
        System.out.print("matrix4d shape: ");
        for(int i=0;i<matrix4d.getDimensions();++i)
            System.out.print(matrix4d.getShape(i)+" ");
        System.out.println();
        System.out.println("matrix4d number of elements: "+matrix4d.getNumberOfElements());   
        
        System.out.println("Setting matrix values ((i+1)*(j+1)+(i+1))*(k+1)*(l+1)");
        for(int i=0;i<dim4[0];++i)
            for(int j=0;j<dim4[1];++j)
                for(int k=0;k<dim4[2];++k)
                    for(int l=0;l<dim4[3];++l){
                    int loc[] = {i,j,k,l};
                    double val=((i+1)*(j+1)+(i+1))*(k+1)*(l+1);
                    System.out.println("i "+i+" j "+j+" k "+k+" l "+l+" : "+val);
                    matrix4d.setValue( val, loc);
                }       
        
        System.out.println("Printing matrix values ((i+1)*(j+1)+(i+1))*(k+1)*(l+1)");
        matrix4d.printMatrixDelimited(" ");
        

//        System.out.println("Testing readMatrixFromTextFile();");
//        NDimensionalMatrixDouble fileMatrix = new NDimensionalMatrixDouble("c:/projects/phoenix/95mesa/autoown.dat");
//        fileMatrix.printMatrixDelimited(" ");

        System.out.println("Collapsing 4d matrix to vector for dimension 0");
        double[] collapsedVector0 = matrix4d.collapseToVectorAsdouble(0);
        for(int i=0;i<collapsedVector0.length;++i)
            System.out.println(i+" "+collapsedVector0[i]);        
                
        System.out.println("Collapsing 4d matrix to vector for dimension 2");
        double[] collapsedVector2 = matrix4d.collapseToVectorAsdouble(2);
        for(int i=0;i<collapsedVector2.length;++i)
            System.out.println(i+" "+collapsedVector2[i]);        
  */
        
    }
}
