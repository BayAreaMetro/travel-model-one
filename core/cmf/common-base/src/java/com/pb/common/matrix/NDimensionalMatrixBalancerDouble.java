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
 * NDimensionalMatrixBalancer 
 *
 * @author    Joel Freedman
 * @version   1.0, 11/2002
 *
 *
 * A class that performs matrix balancing using Evans Iterative Proportional Fitting
 * algorithm (multiplicative balancing).  The class uses the NDimensionalMatrix class
 * for balancing arrays of any length and shape.
 */

import org.apache.log4j.Logger;
public class NDimensionalMatrixBalancerDouble  {

    protected NDimensionalMatrixDouble seed;
    protected NDimensionalMatrixDouble balance;
    protected double[][] targets;
    protected double[][] factors;
    protected double maxError= 0.001;
    protected int maxIterations=50;
    protected boolean trace;
    protected static Logger logger = Logger.getLogger(NDimensionalMatrixBalancerDouble.class);

    /**
    Use to give constructor seed matrix and array of balancing targets.
    @param seedMatrix        A matrix of values to balance.
    @param balancingTargets  An array of targets to balance the seed matrix to.  The number of dimensions
    should be equal to the number of dimensions of the seed matrix.
    **/
    public NDimensionalMatrixBalancerDouble(NDimensionalMatrixDouble seedMatrix, double[][] balancingTargets){
        
        targets=balancingTargets;
        if(seedMatrix.getDimensions()!=balancingTargets.length){
            logger.error("Error: length of balancing targets ("+balancingTargets.length+") not equal to seed dimensions("
            + seedMatrix.getDimensions()+")");
            throw new RuntimeException("length of balancing targets ("+balancingTargets.length+") not equal to seed dimensions(" +
                    + seedMatrix.getDimensions()+")");
        }
        for(int i=0;i<targets.length;++i){
            if(targets[i].length!=seedMatrix.getShape(i)){
                logger.error("Error:  Length of target array for dimension "+i+" ("+targets[i].length+") not equal to "+
                "shape of seedMatrix ("+seedMatrix.getShape(i)+")");
                throw new RuntimeException("Error:  Length of target array for dimension "+i+" ("+targets[i].length+") not equal to "+
                "shape of seedMatrix ("+seedMatrix.getShape(i)+")");
            }
        }    
        setSeed(seedMatrix);   
        // need to do this again because setSeed() messes up the targets.
        targets=balancingTargets;
                
    }

    /**
    Use to set seedMatrix and balancingTargets through methods instead of passing this constructor
    a seed matrix and balancing targets.
    **/
    public NDimensionalMatrixBalancerDouble(){
        
        
        
    }
    /**
    Sets the seed matrix to balance.
    @param seedMatrix  The seed matrix to balance.
    **/
    public void setSeed(NDimensionalMatrixDouble seedMatrix){
        seed=seedMatrix;
        balance = new NDimensionalMatrixDouble("balanceMatrix",seed.getDimensions(),seed.getShape());
        targets = new double[seed.getDimensions()][];
        for(int i=0;i<targets.length;++i)
            targets[i]=new double[seed.getShape(i)];
    }
    
    /**
    Get a reference to the seed matrix.
    **/
    public NDimensionalMatrixDouble getSeed(){
        return seed;
    }
    /**
    Get a reference to the balanced matrix.
    **/
    public NDimensionalMatrixDouble getBalancedMatrix(){
        return balance;
    }
    /**
    Sets the maximum error for convergence.
    @param max  The maximum error.  The seed matrix will be balanced until either
    the error every margin is lower than the maximum error or until the maximum
    number of iterations is reached.
    **/
    public void setMaximumError(float max){
        maxError=max;
    }
    /**
    Sets the maximum number of iterations.
    @param max  The maximum number of iterations.  The seed matrix will be balanced until either
    the error for every margin is lower than the maximum error or until the maximum
    number of iterations is reached.
    **/
    public void setMaximumIterations(int max){
        maxIterations=max;
    }
    
    /**
    Sets the trace option
    **/
    public void setTrace(boolean tf){
        trace=tf;
    }
    /**
    Sets the array of target values for a given dimension. Use setSeed before using this method.
    @param target  An array of target values.
    @param dimension  The dimension that the target values correspond to.
    **/
    public void setTarget(double[] target, int dimension){
        
        if(seed==null){    
            logger.error("Error: Use setSeed before using setTarget()");
            System.exit(1);
        }
        
        if(target.length != seed.getShape(dimension)){
            logger.error("Error:  Target length ("+target.length+") is not equal to "+
            "the length of the seed matrix for dimension "+dimension+" ("+seed.getShape(dimension)+")");
            System.exit(1);
        }
        //set the target for the dimension 
        for(int i=0;i<target.length;++i)
            targets[dimension][i]=target[i];
            
        
    }
    /**
    Sets the array of target values for a given dimension. Use setSeed before using this method.
    @param target  A Vector of target values.
    @param dimension  The dimension that the target values correspond to.
    **/
    public void setTarget(RowVector target, int dimension){
        
        if(seed==null){    
            logger.error("Error: Use setSeed before using setTarget()");
            System.exit(1);
        }
        
        if(target.size() != seed.getShape(dimension)){
            logger.error("Error:  Target length ("+target.size()+") is not equal to "+
            "the length of the seed matrix for dimension "+dimension+" ("+seed.getShape(dimension)+")");
            System.exit(1);
        }
        //set the target for the dimension 
        for(int i=0;i<target.size();++i)
            targets[dimension][i]=target.getValueAt(i+1);
            
        
    }
    /**
    Balances the seed matrix to the targets set by the constructor or the setTarget() method.
    **/
    public void balance(){
        
        balance = (NDimensionalMatrixDouble) seed.clone();
        double[] maxErrors = new double[seed.getDimensions()];
        double previousError=0;
        
        
        //check the targets to make sure they agree with one another; if not, scale the 
        //targets to the sum of the targets for the first dimension
        double[] sumTargets= new double[seed.getDimensions()];
        for(int i=0;i<targets.length;++i){
            
            for(int j=0;j<targets[i].length;++j)
                sumTargets[i] += targets[i][j];
             
             if(i>0){
                if(Math.abs(sumTargets[i]- sumTargets[0])>maxError){
                    logger.info("Sum of targets for dimension "+i+"("+sumTargets[i]+
                        ") not equal to sum of targets for dimension 0 ("+sumTargets[0]+")");
                    logger.info("Scaling targets for dimension "+i+" to dimension 0 sum");
                        
                    for(int j=0;j<targets[i].length;++j)
                        targets[i][j] *= sumTargets[0]/sumTargets[i];
                }
            } //end if not dimension 0
        } //end dimensions
        
        
        //initialize factors array
        factors = new double[seed.getDimensions()][];
        for(int i=0;i<factors.length;++i)
            factors[i] = new double[seed.getShape(i)];
        
        // set factors to 1.0 if target>0.0
        for(int i=0;i<factors.length;++i) 
            for(int j=0;j<factors[i].length;++j)
                if(targets[i][j] > 0.000001)
                    factors[i][j] = (double) 1.0;
        
        // the operand matrix will be used to multiply each dimension of the seed
        // by the factors for the other dimension to get a result matrix that is 
        // collapsed for the current dimension into a vector that is used to create
        // the factors for the current dimension 
        double[][] oMatrix = new double[seed.getDimensions()][];
        for(int i=0;i<oMatrix.length;++i)
            oMatrix[i] = new double[seed.getShape(i)];
        
        //loop on iterations and dimensions 
        for(int iteration=0;iteration<maxIterations;++iteration){
            if(trace)
                logger.info("----- iteration "+iteration+" -----");
            for(int dimension=0; dimension<seed.getDimensions();++dimension){

                maxErrors[dimension]=(double)0.0;
                double[] totals = new double[seed.getShape(dimension)];
                
                for(int i=0;i<factors.length;++i)
                    for(int j=0;j<factors[i].length;++j)
                        oMatrix[i][j]=factors[i][j];
                    
                //set the factors for the current dimension to 1.0
                //if the target !=0
                for(int i=0;i<oMatrix[dimension].length;++i)
                    if(targets[dimension][i]>0.00000001)
                        oMatrix[dimension][i]=(double)1.0;
                    else
                        oMatrix[dimension][i]=(double)0;
                if(trace)
                    logger.info("dimension "+dimension);
                totals = (seed.matrixMultiply(oMatrix)).collapseToVectorAsDouble(dimension);

                for(int i=0;i<seed.getShape(dimension);++i){
                    double lastError = factors[dimension][i];
                    if(totals[i]>0.0 && targets[dimension][i]>0.0){
                        factors[dimension][i] = targets[dimension][i]/totals[i]; 
                        maxErrors[dimension]=Math.max(maxErrors[dimension],Math.abs((factors[dimension][i]-lastError)/factors[dimension][i]));
                    }
                    if (trace)
                        logger.info("dimension "+dimension+" element "+i+" lastError= "+lastError+" target="+targets[dimension][i]
    	                +" total= "+totals[i]+" factor="+factors[dimension][i]+" maxErrors= "+maxErrors[dimension]);
                } 
            } //end for dimensions
            
            //evaluate stopping criteria
            double thisIterationMaxError = 0;
            for(int d=0;d<(seed.getDimensions()-1);++d)
                thisIterationMaxError = Math.max(maxErrors[d],maxErrors[d+1]);
            if (trace)
                logger.info("iteration=" +iteration+" error="+thisIterationMaxError);  
            
            if(thisIterationMaxError<maxError || thisIterationMaxError==previousError)
                break;   
            previousError = thisIterationMaxError;

        } //end for iterations
        
        //create the balanced matrix
        balance = (NDimensionalMatrixDouble) seed.clone();
        
        balance = seed.matrixMultiply(factors);
    }
    
    
    /**
    for testing
    **/

    public static void main(String[] args){
        
        logger.info("Testing NDimensional MatrixBalancer");
        
        logger.info("Create a 2-D Seed Matrix: {3,8}");
        int[] dim={3,8};
        NDimensionalMatrixDouble matrix2d=new NDimensionalMatrixDouble("matrix2d",2,dim);
        
        logger.info("Setting matrix values ((i+1)*(j+1)*(j+1))");
        for(int i=0;i<dim[0];++i)
            for(int j=0;j<dim[1];++j){
                    int loc[] = {i,j};
                    float val=((i+1)*(j+1)*(j+1));
                    System.out.println("i "+i+" j "+j+" : "+val);
                    matrix2d.setValue( val, loc);
                }       
        logger.info("Targets will be equal to 50% of sum of matrix, "+
        "with equal percentages in each vector total"); 

        double sum = matrix2d.getSum();

        logger.info("Setting targets for dimension 0");
        double[] target0 = matrix2d.collapseToVectorAsDouble(0);
        for(int d = 0;d<target0.length;++d){
            target0[d]=(double)0.5*(sum/target0.length);
            logger.info("target0["+d+"]="+target0[d]);
        }

        logger.info("Setting targets for dimension 1");
        double[] target1 = new double[dim[1]];
        for(int d = 0;d<target1.length;++d){
            target1[d]=(double)0.5*(sum/target1.length);
            logger.info("target1["+d+"]="+target1[d]);
        }

        logger.info("Creating NDimensionalMatrixBalancer for 2d matrix");
       NDimensionalMatrixBalancerDouble mb2 = new NDimensionalMatrixBalancerDouble();
       mb2.setTrace(true);
       mb2.setSeed(matrix2d);
       mb2.setTarget(target0,0);
       mb2.setTarget(target1,1);

       logger.info("Balancing 2d matrix");
       mb2.balance();
       
       //get and print the balanced matrix
       NDimensionalMatrixDouble mb2Balanced = mb2.getBalancedMatrix();
       mb2Balanced.printMatrixDelimited(" ");
        
       logger.info("Create a 3-D Matrix: {3,5,2}");
        
        int[] dim3={3,5,2};
        NDimensionalMatrixDouble matrix3d=new NDimensionalMatrixDouble("matrix3d",3,dim3);
//        matrix3d.setTrace(true);
        
        logger.info("Setting matrix values ((i+1)*(j+1)+(i+1))*(k+1)");
        for(int i=0;i<dim3[0];++i)
            for(int j=0;j<dim3[1];++j)
                for(int k=0;k<dim3[2];++k){
                    int loc[] = {i,j,k};
                    float val=((i+1)*(j+1)+(i+1))*(k+1);
                    System.out.println("i "+i+" j "+j+" k "+k+" : "+val);
                    matrix3d.setValue( val, loc);
                }       

        logger.info("Targets will be equal to 20% of sum of matrix, "+
        "with equal percentages in each vector total"); 

        sum = matrix3d.getSum();

        logger.info("Setting targets for dimension 0");
        double[] t3d0  = new double[dim3[0]];
        for(int d = 0;d<t3d0.length;++d){
            t3d0[d]=(double)0.2*(sum/t3d0.length);
            logger.info("t3d0["+d+"]="+t3d0[d]);
        }

        logger.info("Setting targets for dimension 1");
        double[] t3d1 = new double[dim3[1]];
        for(int d = 0;d<t3d1.length;++d){
            t3d1[d]=(double)0.2*(sum/t3d1.length);
            logger.info("t3d1["+d+"]="+t3d1[d]);
        }

        logger.info("Setting targets for dimension 2");
        double[] t3d2 = new double[dim3[2]];
        for(int d = 0;d<t3d2.length;++d){
            t3d2[d]=(double)0.2*(sum/t3d2.length);
            System.out.println("t3d2["+d+"]="+t3d2[d]);
        }
        
        logger.info("Creating NDimensionalMatrixBalancer for 3d matrix");
       NDimensionalMatrixBalancerDouble mb3 = new NDimensionalMatrixBalancerDouble();
       mb3.setTrace(true);
       mb3.setSeed(matrix3d);
       mb3.setTarget(t3d0,0);
       mb3.setTarget(t3d1,1);
       mb3.setTarget(t3d2,2);

       logger.info("Balancing 3d matrix");
       mb3.balance();

       //get and print the balanced matrix
       NDimensionalMatrixDouble mb3Balanced = mb3.getBalancedMatrix();
       mb3Balanced.printMatrixDelimited(" ");

       //set one of the values to 0 and rebalance
       logger.info("Creating NDimensionalMatrixBalancer for 3d matrix");
       NDimensionalMatrixBalancerDouble mb3Again = new NDimensionalMatrixBalancerDouble();
       logger.info("Resetting one of the elements of the first dimension targets to 0");
  
        t3d0[1]=t3d0[0]+t3d0[1];
        t3d0[0]=0;
        logger.info("New targets for dimension 0");
        for(int d = 0;d<t3d0.length;++d){
            logger.info("t3d0["+d+"]="+t3d0[d]);
        }
        mb3Again.setTrace(true);
        mb3Again.setSeed(matrix3d);
        mb3Again.setTarget(t3d0,0);
        mb3Again.setTarget(t3d1,1);
        mb3Again.setTarget(t3d2,2);

        logger.info("Balancing 3d matrix");
        mb3Again.balance();
        
        //get and print the balanced matrix
        NDimensionalMatrixDouble mb3BalancedAgain = mb3Again.getBalancedMatrix();
        mb3BalancedAgain.printMatrixDelimited(" ");
       

    }
    
 

}

