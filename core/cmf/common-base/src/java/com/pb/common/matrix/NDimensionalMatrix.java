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
import java.util.Hashtable;
import java.util.StringTokenizer;

public class NDimensionalMatrix implements Cloneable, Serializable {
    
    static final long serialVersionUID=-333344445555L;
    
    public String matrixName;
    protected int dimensions;  // number of dimensions from 1->n
    protected int[] shape; // rectangular; array contains number of elements in each dimension
    protected float[] value;
    private int[] offset;
    protected boolean trace;
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");
   
    // column labels used for printing--one for each dimension
    protected String[] columnNames;
    protected Hashtable<Integer, String>[] label; 
    
    
    /**
     * Construct with a Matrix
     * 
     * @param matrix
     */
    public NDimensionalMatrix(Matrix matrix) {
        this(matrix.getName(), matrix.getValues());
    }
    
    
    /**
    Creates a rectangular matrix of any dimensions.
     
    @param name                The name of the matrix, used for reports.
    @param matrixDimensions    The number of dimensions of the matrix.
                               Ex: matrixDimensions = 3:  A 3-d matrix will be created.
    @param matrixShape         An array containing the number of elements on each dimension.
    
    **/  
    public NDimensionalMatrix(String name, int matrixDimensions, int matrixShape[]) {
        
        //set name
        matrixName=name;
        
        //set number of dimensions
        dimensions=matrixDimensions;        
                
        //check to make sure shape array length is equal to matrixDimensions
        checkLookupArray(matrixShape);
        
        //set number of shapes per dimension
        shape = matrixShape;

        //initialize vector names
        columnNames = new String[dimensions];
               
        // initialize an empty set of labels
        label = new Hashtable[dimensions]; 
        
        calculateOffsets();
        
        initializeValueArray();
       
    }
    /**
    Constructor with no arguments; use to generate undefined NDimensionalMatrix class.
    **/
    public NDimensionalMatrix(){};   
    
    /**
    Constructor to use if reading matrix from file.
    **/
    public NDimensionalMatrix(String fileName){
    
        readMatrixFromTextFile(fileName);    
        
    } 

    /**
     * Constructor to use for constructing from 2-d double array
     * @param name The name of the NDimensionalMatrix
     * @param array  The array to construct from.
     */
    public NDimensionalMatrix(String name, float[][] array){
                
        dimensions=2;
        int[] loc = new int[2];
        int[] shape = { array.length,array[0].length };
        this.shape = shape;
        this.matrixName = name;

        //initialize vector names
        columnNames = new String[dimensions];
               
        // initialize an empty set of labels
        label = new Hashtable[dimensions]; 
        
        calculateOffsets();
        
        initializeValueArray();
                   
        // Set matrix values
        for (int r=0; r < array.length; r++) {
            for (int c=0; c < array[0].length; c++) {
                loc[0] = r;
                loc[1] = c;
                setValue( array[r][c], loc );
            }
        }        
    }

    /**
     * Constructor to use for constructing from 2-d double array
     * @param name The name of the NDimensionalMatrix
     * @param array  The array to construct from.
     */
    public NDimensionalMatrix(String name, double[][] array){
        
        this.dimensions=2;
        int[] loc = new int[2];
        int[] shape = { array.length,array[0].length };
        this.shape = shape;
        this.matrixName = name; 

        //initialize vector names
        columnNames = new String[dimensions];
               
        // initialize an empty set of labels
        label = new Hashtable[dimensions]; 
        
        calculateOffsets();
        
        initializeValueArray();
           
        // Set matrix values
        for (int r=0; r < array.length; r++) {
            for (int c=0; c < array[0].length; c++) {
                loc[0] = r;
                loc[1] = c;
                this.setValue ( (float)array[r][c], loc );
            }
        }        
    }
    

    /**
     * @param dimensionNames the vectorNames to set
     */
    public void setDimensionNames(String[] dimensionNames) {
        if (dimensionNames.length==dimensions) {        
            this.columnNames = dimensionNames;
        } else {
            String errorMessage = "Error in NDimensionalMatrix, expecting "; 
            errorMessage += dimensions + " names, got " + dimensionNames.length;
            throw new RuntimeException(errorMessage); 
        }
    }
    
    /**
     * 
     * @param dimension The dimension for which we are setting the labels.
     * @param labels    An array of labels, same as the size of the dimension.  
     */
    public void setLabels(int dimension, String[] labels) {
        if (labels.length!=shape[dimension]) {
            throw new RuntimeException("Error in NDimensionalMatrix: expecting " 
                    + shape[dimension] + " labels, recieved " + labels.length); 
        } 
        
        label[dimension] = new Hashtable(shape[dimension]); 
        for (int i=0; i<shape[dimension]; i++) {
            label[dimension].put(i, labels[i]); 
        }
    }
    
    /**
    Return a matrix of integerized values (represented still as floats)
    from the current matrix of fractional values
    **/
    public NDimensionalMatrix discretize() {
    	
    	float[][] marginals = new float[dimensions][];
        float marginalProduct;
    	int[] loc = new int[dimensions];
        int[] location = null;
        NDimensionalMatrix fracPart = (NDimensionalMatrix) this.clone();

        logger.info("entering NDimensionalMatrix discretize method");

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
            if (fracPart.value[i] <= (float)0.0){
                potential[i] = 0;
            }
           
        }

        // define a set of marginals for the fractional values in each dimension
        for (int i=0; i < shape.length; i++)
            marginals[i] = fracPart.collapseToVectorAsFloat (i);


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


        // sum total fractions in NDimensionalMatrix
        int totalFractions = (int)(fracPart.getSum() + 0.5f);
            
        // sum total fractions in NDimensionalMatrix
        float matrixTotal = fracPart.getSum();
            
        logger.info("totalFractions= "+totalFractions);
    
        int k = 0;
        for (int capN=0; capN < totalFractions; capN++) {	    
	    
            if(capN % 1000 == 0)
                logger.info("capN= "+capN);
            
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
                    float maxMarginSum = -999999999.9f;
                    maxLocation = new int[dimensions];
                    for (k=0; k < value.length; k++) {
                        if (potential[k] == 3) {
                            location = getLocation(k);
                            float marginSum = 0.0f;
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

		logger.info("Leaving the NDimensional Matrix discretize method");
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
        
        value=new float[totalShape];
    }      
    /** 
    Get shape of matrix for a given dimension.
    @param dimension  The dimension to get shape for.
    **/
    public int getShape(int dimension){
        if(dimension>shape.length){
            System.out.println("Error: Tried to get shape for dimension ("+dimension+") that is greater than number of "
            +"dimensions of NDimensionalMatrix "+matrixName+" ("+shape.length+")");
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
    Set trace for this NDimensionalMatrix to write debug to System.out
    **/
    public void setTrace(boolean tf){
        trace=tf;
    }
    /** 
    Return a copy of this NDimensionalMatrix.
    **/
    public Object clone(){
        NDimensionalMatrix o = null;
        try{
            o= (NDimensionalMatrix)super.clone();
            
            
        }catch(CloneNotSupportedException e){
            logger.error("Error: NDimensionalMatrix can't clone");
            System.exit(1);
        }
        //clone references
        o.shape = new int[this.shape.length];
        o.value = new float[this.value.length];
        
        if(this.columnNames!=null){
            o.columnNames = new String[this.columnNames.length];
            System.arraycopy(this.columnNames,0,o.columnNames,0,this.columnNames.length); 
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
    public void setValue(float inValue, int[] location){
        //check location array
        checkLookupArray(location);
        
        value[getIndex(location)]=inValue;
        
    }
        
    /**
    Adds to the value in the matrix.
    
    @param additionalValue   The value of the cell referred to in the location array.
    @param location          An array specifying the coordinates of the cell. 
                             Ex: location = {5,3,9} 
                             changes the value at cell i=5, j=3, k=9
    **/
    public void incrementValue(float additionalValue, int[] location){
        //check location array
        checkLookupArray(location);
        
        value[getIndex(location)] += additionalValue;        
    }
    
    /**
    Returns a value from the matrix.
    
    @param location   An array specifying the coordinates of the cell. 
                      Ex: location = {5,3,9} 
                      changes the value at cell i=5, j=3, k=9
    **/
    public float getValue(int[] location){
        //check location array
        checkLookupArray(location);
         
        return value[getIndex(location)];
    }
    /**
    Sets all the values in the matrix to a value.
    
    @param val   The number to set the matrix to.
    **/
    public void setMatrix(float val){
        
        for(int i=0;i<value.length;++i)
            value[i]=val;
    }
    /**
    Returns a reference to the NDimensional matrix.  To get a copy of the matrix use clone().
    
    **/
    public NDimensionalMatrix getMatrix(){
        
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
        
        matrix = new Matrix();
        
        for (int r = 0; r < nRows; ++r) {
            int row = r + 1;
            for (int c = 0; c < nCols; ++c) {
                int col = c + 1;
                int[] location = {r, c};
                float value = getValue(location);
                
                matrix.setValueAt(row, col, value);
            }
        }
        
        return matrix;
    }
    /** 
    
    Returns a vector from the matrix.
    
    @param vectorLocation   An array specifying the location of the vector.
                            Ex. vectorLocation= {1,2,-1}
                            returns the vector for i=1, j=2, all k's.
                            (-1 signifies the dimension to return)
    **/
    public RowVector getVector(int[] vectorLocation){
        return new RowVector(getVectorAsFloat(vectorLocation));
    }
    
    /** 
    
    Returns a vector from the matrix as a float array.
    
    @param vectorLocation   An array specifying the location of the vector.
                            Ex. vectorLocation= {1,2,-1}
                            returns the vector for i=1, j=2, all k's.
                            (-1 signifies the dimension to return)
    **/
    public float[] getVectorAsFloat(int[] vectorLocation){
        
        checkLookupArray(vectorLocation);
        int dimension0=-1;
        
        if(trace){
            System.out.print("Getting vector for vectorLocation {");
            for(int i=0;i<vectorLocation.length;++i){
                System.out.print(vectorLocation[i]);
                if((i+1)<vectorLocation.length)
                    System.out.print(",");
            }
            System.out.println("}");
       }
                
        
        //find the 0 dimension
        for(int i=0;i<vectorLocation.length;++i){
            if(vectorLocation[i]==-1){
                dimension0=i;
                break;
            }
        }
        
        if(dimension0==-1){
            System.out.println("Error: tried to getVector in matrix "+matrixName+
                " with incorrectly specified location");
            System.exit(1);
        }               

        //Initialize the size of the float array to the vector size
        float[] outVector = new float[shape[dimension0]];
        int[] lookupVector = new int[vectorLocation.length];
        System.arraycopy(vectorLocation,0,lookupVector,0,vectorLocation.length);
        lookupVector[dimension0]=0;        
        
        if(trace)
            System.out.println("Getting vector for dimension "+dimension0+" that has "+outVector.length+" elements");
        //get the values for this dimension   
        for(int i=0;i<outVector.length;++i){
        
            if(trace){
                System.out.print("Getting value for location ");
                for(int j=0;j<lookupVector.length;++j)
                    System.out.print(j+"="+lookupVector[j]+" ");
                System.out.println();
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
    public void setVector(float[] inVector, int[] vectorLocation){
        
        checkLookupArray(vectorLocation);
        int dimension0=-1;
        
        //find the 0 dimension
        for(int i=0;i<vectorLocation.length;++i)
            if(vectorLocation[i]==-1){
                dimension0=i;
                break;
            }
        
        if(dimension0==-1){
            System.out.println("Error: tried to getVector in matrix "+matrixName+
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
    public float getSum(){
        
        float sum=0;
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
    public float getVectorSum(int[] vectorLocation){
        
        float[] vector = getVectorAsFloat(vectorLocation);
        float vectorSum=0;
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
                (getValue(location)+vectorSum.getValueAt(location[dimension])));                  
            
        }
         return vectorSum;
               
    }
    /**
    Sums the matrix across all dimensions except for vectorLocation
    and returns an array of sums for the vectorLocation
    @param dimension        The dimension of the vector to be returned.
    **/  
    public float[] collapseToVectorAsFloat(int dimension){
        
        float vectorSum[]=new float[shape[dimension]];
        int[] location = new int[dimensions];
    
        for(int e=0;e<value.length;++e){
            location = getLocation(e);
            vectorSum[location[dimension]] += value[e];
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
    public NDimensionalMatrix vectorMultiply(RowVector operandVector, int[] vectorLocation) {
    
        float[] vector = getVectorAsFloat(vectorLocation);
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.size()){
            System.out.println("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            System.out.println("Common matrix elements will be multiplied");
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
    public NDimensionalMatrix vectorMultiply(float[] operandVector, int[] vectorLocation) {
    
        float[] vector = getVectorAsFloat(vectorLocation);
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.length){
            System.out.println("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            System.out.println("Common matrix elements will be multiplied");
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
    public NDimensionalMatrix vectorOperate(float[] operandVector, int[] vectorLocation, String operand) {
    
        float[] vector = getVectorAsFloat(vectorLocation);
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();
        
        int minLength=vector.length;
        if(vector.length != operandVector.length){
            System.out.println("Operand matrix length not equal to matrix vector length in matrix "+
                matrixName);
            System.out.println("Common matrix elements will be operated on");
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
            System.out.println("Error:  Operand "+operand+" not recognized as valid operation");
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
    public NDimensionalMatrix collapseDimension(int dimensionToCollapse){    

        if(dimensions==1||dimensionToCollapse>dimensions){
            System.out.println("Error: Attempting to collapse dimension "+dimensionToCollapse+
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
        NDimensionalMatrix result = new NDimensionalMatrix(this.matrixName, resultDimensions,resultShape);
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
    public NDimensionalMatrix matrixMultiply(float oValue){
        
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();
        
        for(int i=0;i<result.value.length;++i)
            result.value[i] *= oValue;
            
        return result;
    }

    /**
    Perform an operation on the entire matrix by a value and return the result.
    
    @param oValue   The value to multiply the matrix by.
    @param operand  one of:"*","/","+","-"

    **/
    public NDimensionalMatrix matrixOperate(float oValue, String operand){
        
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();
        
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
            System.out.println("Error:  Operand "+operand+" not recognized as valid operation");
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
    public NDimensionalMatrix matrixOperate(RowVector operandVector, int vectorDimension, String operand){

        float[] oVector = operandVector.copyValues1D();
        
        return matrixOperate(oVector,vectorDimension,operand);
    
    }
    /**
    Multiply the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
        
    **/
    public NDimensionalMatrix matrixMultiply(RowVector operandVector, int vectorDimension){

        float[] oVector = operandVector.copyValues1D();
        
        return matrixMultiply(oVector,vectorDimension);
    
    }
    /**
    Multiply the entire matrix by a vector and return the result.
    
    @param operandVector     The vector to multiply the matrix by.
    @param vectorDimension   The dimension (0->n) of the matrix that this vector applies to.
    Ex:
    matrixMultiply(vector[],2) will multiply the matrix by the vector across the 3rd dimension  
        
    **/
    public NDimensionalMatrix matrixMultiply(float[] operandVector, int vectorDimension){
        
        if(trace)
            System.out.println("Attempting to multiply vector of length "+operandVector.length
            +" against dimension "+vectorDimension);
            
        if((dimensions-1)<vectorDimension){
            System.out.println("Error: Attempting to matrixMultiply a vector across a dimension ("+
                vectorDimension+") that is greater than the number of dimensions ("+dimensions+") in"
                +" the matrix "+matrixName);
            System.exit(1);
        }
        
        int minLength=operandVector.length;
        if(operandVector.length!=shape[vectorDimension]){
            System.out.println("Operand vector length not equal to matrix vector length in matrix "+
                matrixName);
            System.out.println("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.length, shape[vectorDimension]);
        }
       
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();

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
    public NDimensionalMatrix matrixOperate(float[] operandVector, int vectorDimension, String operand){
        
        if(trace)
            System.out.println("Attempting to multiply vector of length "+operandVector.length
            +" against dimension "+vectorDimension);
            
        if((dimensions-1)<vectorDimension){
            System.out.println("Error: Attempting to matrixMultiply a vector across a dimension ("+
                vectorDimension+") that is greater than the number of dimensions ("+dimensions+") in"
                +" the matrix "+matrixName);
            System.exit(1);
        }
        
        int minLength=operandVector.length;
        if(operandVector.length!=shape[vectorDimension]){
            System.out.println("Operand vector length not equal to matrix vector length in matrix "+
                matrixName);
            System.out.println("Common matrix elements will be multiplied");
            minLength=Math.min(operandVector.length, shape[vectorDimension]);
        }
       
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();

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
    protected NDimensionalMatrix recursivelyVectorMultiply(int k, int[] loc, int[] lower, int[] upper,float[] ov,
        NDimensionalMatrix result){
        
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
    protected NDimensionalMatrix recursivelyVectorCollapse(int k, int[] loc, int[] lower, int[] upper,
        NDimensionalMatrix resultMatrix){
        
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
    
    protected NDimensionalMatrix recursivelyVectorOperate(int k, int[] loc, int[] lower, int[] upper,float[] ov,
        String operand,NDimensionalMatrix result){
        
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
    of the NDimensionalMatrix object, and the length of the second dimensions should be equal to 
    the shape of the NDimensionalMatrix object for each dimension (ie can be non-rectangular). 
    Each element of the operand matrix is a factor to apply to the appropriate vector of the 
    NDimensionalMatrix object.  This method can be used in matrix balancing, for example.
    **/
    
    public NDimensionalMatrix matrixMultiply(float operandMatrix[][]){
        
        if(operandMatrix.length!=dimensions){
            System.out.println("Error: Trying to matrix multiply operand matrix whose first "
            +"dimension (size "+operandMatrix.length+") is not equal to number of dimensions "
            +"of NDimensionalMatrix "+matrixName+"("+dimensions+")");
            System.exit(1);
        }
        
        NDimensionalMatrix result = (NDimensionalMatrix) this.clone();

        for(int d=0;d<dimensions;++d){
        
            if(operandMatrix[d].length!=result.shape[d]){
                System.out.println("Error: Trying to matrix multiply operand matrix whose shape "
                +"is not equal to shape of NDimensionalMatrix "+matrixName);
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
                    System.out.print("Scanning text matrix file "+fileName);
                    //find out what the delimiter is
                    if(s.indexOf(",")!=-1){
                        System.out.print(" in comma-delimited format");
                        d = ",";
                    }else if(s.indexOf(" ")!=-1){
                        System.out.print(" in space-delimited format");
                        d = " ";
                    }else{
                        System.out.print(" in tab-delimited format");
                        d="\t";
                    }
                    System.out.println();
                   
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
                System.out.println(s);
                int token=0;
                while(st.hasMoreTokens() && token<dimensions){
                    location[token]= new Integer(st.nextToken()).intValue();
                    ++token;
                }
                float inValue=new Float(st.nextToken()).floatValue();
                this.setValue(inValue,location); 
            }
            System.out.println();
            
            
            
            
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
        for(int i=0;i<location.length;++i) {
            if (label[i]!=null && label[i].containsKey(location[i])){
                outLine = new String(outLine+label[i].get(location[i])+delimiter);
            } else {
                outLine = new String(outLine+location[i]+delimiter);
            }
        }
            
        logger.info(outLine+getValue(location));
    }
        
    /** 
    Print the entire matrix with the delimiter to System.out.
    
    @param delimiter  The delimiter to use to separate indices.
    
    **/    
    public void printMatrixDelimited(String delimiter){
        for(int i=0;i<value.length;++i){
            int[] location = getLocation(i);
            printValueDelimited(location,delimiter);
        }
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
        for(int i=0;i<location.length;++i) {
            if (label[i]!=null && label[i].containsKey(location[i])){
                outLine = new String(outLine+label[i].get(location[i])+delimiter);
            } else {
                outLine = new String(outLine+location[i]+delimiter);
            }
        }
            
        try{
            bw.write(outLine+getValue(location)+"\n");
        }catch(IOException e){
            e.printStackTrace();
        } 
    }
    
    
    /** 
    Print the entire matrix with the delimiter to print file.
    
    @param delimiter  The delimiter to use to separate indices.
    
    **/    
    public void printMatrixDelimited(String delimiter, String fileName){
        logger.info("Writing NDimensionalMatrix to file " + fileName); 

        try {
            //first run through file, determine shape of matrix 
            BufferedWriter bw = new BufferedWriter(new FileWriter(fileName));

            if (this.columnNames!=null) {
                String outLine = ""; 
                for (int i=0; i<columnNames.length; i++) {
                    outLine += columnNames[i] + ",";
                }
                bw.write(outLine+this.matrixName + "\n");                
            }
            
            for(int i=0;i<value.length;++i){
               int[] location = getLocation(i);
                printValueDelimited(location,delimiter,bw);
            }           
 
 
            bw.close();
       } catch (IOException e) { e.printStackTrace(); }


     }


    private void checkLookupArray(int[] lookupArray) {
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
            System.out.println("Error: Index value ("+index+") in calculateLocation() "
            +" is greater than number of elements in matrix "+matrixName);
            System.exit(1);
        }         
            
        if(dimensions==1){
            location[0]=index;
            return location;
        }else if(dimensions==2){
            
            location[0]=index % shape[0];    
            location[1]=index/shape[0];
            
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

/*
			int[] incr = new int[shape.length];
     		incr[shape.length-1] = 1;
			incr[shape.length-2] = 1;
     		for (int i=shape.length-2; i >= 0; i--)
     			incr[i] *= shape[i+1];
            
     		location[0] = (int)(index/incr[0]);
     		int tempValue = location[0]*incr[0];
     		for (int i=1; i < shape.length; i++) {
     			location[i] = (int) ((index - tempValue)/incr[i]);
     			tempValue += location[i]*incr[i];
     		}
*/
            
        }
        return location;     
    }
    

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
        NDimensionalMatrix matrix2d=new NDimensionalMatrix("matrix2d",2,dim);
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
                    float val=((i+1)*(j+1)*(j+1));
                    System.out.println("i "+i+" j "+j+" : "+val);
                    matrix2d.setValue( val, loc);
                }       
        
        System.out.println("Printing matrix values  ((i+1)*(j+1)*(j+1))");
        matrix2d.printMatrixDelimited("  ");
         
        System.out.println("Getting a row from matrix2d for i=2");
        int[] lookupRow2d = {2,-1};
        float[] row2d=matrix2d.getVectorAsFloat(lookupRow2d);
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
        NDimensionalMatrix matrix3d=new NDimensionalMatrix("matrix3d",3,dim3);
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
                    float val=((i+1)*(j+1)+(i+1))*(k+1);
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
        float[] vector3d=matrix3d.getVectorAsFloat(lookupVector3d);
        for(int i=0;i<vector3d.length;++i)
            System.out.println(i+" "+vector3d[i]);
            
        System.out.println("Sum of vector from matrix3d for i=2, j=3, all k is: "+matrix3d.getVectorSum(lookupVector3d));
        
        System.out.println("Multiplying matrix3d for i=2 j=3 by the vector");
        matrix3d.vectorMultiply(vector3d,lookupVector3d);
        for(int i=0;i<vector3d.length;++i)
            System.out.println(i+" "+vector3d[i]);
        
        matrix3d.setTrace(true);    
        System.out.println("Getting a collapsed vector for dimension 0 from matrix3d");
        float[] collapsedDimension0 = matrix3d.collapseToVectorAsFloat(0);
        System.out.println("Multiplying vector across entire matrix3d");
        NDimensionalMatrix result = matrix3d.matrixMultiply(collapsedDimension0,0); 
        result.printMatrixDelimited(" ");
       
        matrix3d.setTrace(false);
        System.out.println("Collapsing 2nd Dimension from result");
        NDimensionalMatrix collapsedResult = result.collapseDimension(1);
        collapsedResult.printMatrixDelimited(" ");
       
       /*
            
        System.out.println("-----------------------------");       

        System.out.println("Create a 4-D Matrix: {2,3,2,4}");
        
        int[] dim4={20,3,6,4};
        NDimensionalMatrix matrix4d=new NDimensionalMatrix("matrix4d",4,dim4);
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
                    float val=((i+1)*(j+1)+(i+1))*(k+1)*(l+1);
                    System.out.println("i "+i+" j "+j+" k "+k+" l "+l+" : "+val);
                    matrix4d.setValue( val, loc);
                }       
        
        System.out.println("Printing matrix values ((i+1)*(j+1)+(i+1))*(k+1)*(l+1)");
        matrix4d.printMatrixDelimited(" ");
        

//        System.out.println("Testing readMatrixFromTextFile();");
//        NDimensionalMatrix fileMatrix = new NDimensionalMatrix("c:/projects/phoenix/95mesa/autoown.dat");
//        fileMatrix.printMatrixDelimited(" ");

        System.out.println("Collapsing 4d matrix to vector for dimension 0");
        float[] collapsedVector0 = matrix4d.collapseToVectorAsFloat(0);
        for(int i=0;i<collapsedVector0.length;++i)
            System.out.println(i+" "+collapsedVector0[i]);        
                
        System.out.println("Collapsing 4d matrix to vector for dimension 2");
        float[] collapsedVector2 = matrix4d.collapseToVectorAsFloat(2);
        for(int i=0;i<collapsedVector2.length;++i)
            System.out.println(i+" "+collapsedVector2[i]);        
  */
        
    }


}
