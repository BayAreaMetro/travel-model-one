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
import java.io.File;

/**
 * MatrixExpansion.java
 * This class expands a betaZone matrix to an alphaZone matrix
 *
 * A betaZone is an aggregation of alphaZones.  
 * For example, alphaZones are TAZs, while betaZones are districts containing a group of TAZs.
 * 
 * The formula for the expansion is:
 * F(alpha) = F(beta) 
 *            * alphaProduction(aOrigin)/sum of alphaProduction for all alphaZones in bOrigin
 *            * alphaConsumption(aDestination)/sum of alphaConsumption for all alphaZones in bOrigin 
 *            * alphaPropensity(aOrigin,aDestination)/sum of alphaPropensity for all alphaZones in bOrigin and bDestination
 * 
 * The inputs for performing the expansion are:
 *      AlphaToBeta - an alpha to beta zone mapping (passed in constructor)
 *      betaFlowMatrix
 *      alphaProductionVector
 *      alphaConsumptionVector
 *      alphaPropensityMatrix
 *
 * @author Steve Hansen
 * @version 1.0 Apr 6, 2004
 *
 * @deprecated by Andrew Stryker, use MatrixExpansion2 instead for a more robust solution.
 */

public class MatrixExpansion {
    public static final boolean debug = false;
    public static final int ORIGIN_DEBUG = 0;
    public static final int DESTINATION_DEBUG = 0;
    
    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");

    //Mapping of alphaZones to BetaZones
    //protected AlphaToBeta a2b;
    
    //Matrix representing the "production" of each alphaZone
    //This Matrix has one column
    protected Matrix alphaProductionMatrix;
    
    //Matrix containing the "consumption" of each alphaZone
    //This Matrix has one column
    protected Matrix alphaConsumptionMatrix;
    
    //the propensity to travel between alphaZones
    protected Matrix alphaPropensityMatrix;
    
    //flows between betaZones
    protected Matrix betaFlowMatrix;
    
    //MatrixCompression - class used to compress alpha Matrices to beta Matrices
    protected MatrixCompression compress;
    
    //The corresponding alphaZone matrices are compressed to create the following beta matrices
    protected Matrix betaProductionMatrix;
    protected Matrix betaConsumptionMatrix;
    protected Matrix betaPropensityMatrix;
    
    //output - alphaFlowMatrix - a Matrix of alpha flows
    protected Matrix alphaFlowMatrix;
    
    //output - alphaFlowProbabilityMatrix - a Matrix of probabilities of flow between alphazones
    protected Matrix alphaFlowProbabilityMatrix;
      

    /** 
     * Constructor.
     * @param a2b alphaZone to betaZone mapping
     */
    public MatrixExpansion(AlphaToBeta a2b){
        compress = new MatrixCompression(a2b);
    }
    
    /**
     * Set the matrix of $ flows between betaZones
     * @param m - the beta flow matrix
     */
    public void setBetaFlowMatrix(Matrix m){
        betaFlowMatrix = m;
    }
    
    /**
     * Set the ColumnVector that contains the production numbers for each alphaZone
     * @param m - Matrix
     * TODO make a column vector
     */
    public void setProductionMatrix(Matrix m){
        alphaProductionMatrix = m;
        betaProductionMatrix = compress.getCompressedMatrix(m,"SUM");
    }
    
    /**
     * Set the RowVector that contains the production numbers for each alphaZone
     * @param m - Matrix
     * TODO does this need to be a row vector
     */
    public void setConsumptionMatrix(Matrix m){
        alphaConsumptionMatrix = m;
        betaConsumptionMatrix = compress.getCompressedMatrix(m,"SUM");
        
    }
    /**
     * Sets the Matrix that contains the propensity to travel between alphaZones
     * Also sets the betaPropensityMatrix by compressing the alphaPropensityMatrix
     * @param m - the propensity matrix
     */
    public void setPropensityMatrix(Matrix m){
        alphaPropensityMatrix = m;
        betaPropensityMatrix = compress.getCompressedMatrix(m,"MEAN");

        if(debug){
            MatrixWriter aWriter = MatrixWriter.createWriter(MatrixType.ZIP,new File("/models/tlumip/debug/" + alphaPropensityMatrix.getName() + ".zip"));
            aWriter.writeMatrix(alphaPropensityMatrix);

            MatrixWriter bWriter = MatrixWriter.createWriter(MatrixType.ZIP, new File("/models/tlumip/debug/" + betaPropensityMatrix.getName() + ".zip"));
            bWriter.writeMatrix(betaPropensityMatrix);
        }
    }
    
    /**
     * gets the flows between two given betaZones
     * @param origin
     * @param destination
     * @return betaFlowMatrix.getValueAt(origin, destination) 
     */
    public float getBetaFlow(int origin, int destination){
        return betaFlowMatrix.getValueAt(origin, destination);
    }
    
    /**
     * gets the full alphaFlowMatrix
     * @return alphaFlowMatrix 
     */
    public Matrix getAlphaFlowMatrix(){
        return alphaFlowMatrix;
    }
    
    /**
     * gets the full alphaFlowProbabilityMatrix
     * @return alphaFlowMatrix 
     */
    public Matrix getAlphaFlowProbabilityMatrix(){
        return alphaFlowProbabilityMatrix;
    }
    
    /** calculates the flow between an alphaZone pair
     *  flow is based on the following formula:
     * 
     * F(alpha) = F(beta) 
     *            * alphaProduction(aOrigin)/sum of alphaProduction for all alphaZones in bOrigin
     *            * alphaConsumption(aDestination)/sum of alphaConsumption for all alphaZones in bOrigin
     *            * alphaPropensity(aOrigin,aDestination)/sum of alphaPropensity for all alphaZones in bOrigin and bDestination
     * 
     * @param aOrigin - alphaZone origin
     * @param aDestination - alphaZone destination
     * @return flow - flow between the alphaZone pair
     */
    public float calculateAlphaFlow(int aOrigin, int aDestination, AlphaToBeta a2b){
        int bOrigin = a2b.getBetaZone(aOrigin);
        int bDestination = a2b.getBetaZone(aDestination);
        //logger.debug("aOrigin = "+aOrigin);
        //logger.debug("aDestination = "+aDestination);
        //logger.debug("bOrigin = "+bOrigin);
        //logger.debug("bDestination = "+bDestination);
        float betaProductionValue = betaProductionMatrix.getValueAt(bOrigin,0);
        if(betaProductionValue == 0) {
            //logger.error("betaProductionValue is 0 in origin " + bOrigin);
            return 0;
        }
        float originZoneFlow=alphaProductionMatrix.getValueAt(aOrigin,0)/betaProductionMatrix.getValueAt(bOrigin,0);
        if(betaConsumptionMatrix.getValueAt(bDestination,0) == 0) {
            //logger.error("betaConsumptionValue is 0 in destination " + bDestination);
            return 0;
        }
        float destinationZoneFlow=alphaConsumptionMatrix.getValueAt(aDestination,0)/betaConsumptionMatrix.getValueAt(bDestination,0);
        if(betaPropensityMatrix.getValueAt(bOrigin,bDestination) ==0 ) {
            //logger.error("betaPropensityValue is 0 in O-D " + bOrigin + " " + bDestination);
            return 0;
        }
                
        float propensityFlow=alphaPropensityMatrix.getValueAt(aOrigin,aDestination)/
                             betaPropensityMatrix.getValueAt(bOrigin,bDestination);

        float flow = (getBetaFlow(bOrigin,bDestination)*originZoneFlow*destinationZoneFlow*propensityFlow);
        if(Float.isNaN(flow)) logger.error("Calculated a NaN for labor flow from " + aOrigin + " to " + aDestination);
        if (debug) {
            if(aOrigin==ORIGIN_DEBUG && aDestination==DESTINATION_DEBUG){
                logger.info("Origin: "+aOrigin+" originZoneFlow: "+originZoneFlow);
                logger.info("Destination: "+aDestination+" destinationZoneFlow: "+destinationZoneFlow);
                logger.info("Propensity Flow: "+propensityFlow);
                logger.info("flow = "+flow);
            }
        }

        return flow;
    }
    
    /**
     * Fills the alphaFlowMatrix - calculates alphaZoneFlows for each alphaZone pair using calculateAlphaFlow method
     * @param a2b - Alpha to Beta Matrix
     */
    public void setAlphaFlowMatrix(AlphaToBeta a2b){
        int originTaz;
        int destinationTaz;
        alphaFlowMatrix = new Matrix(a2b.alphaSize(),a2b.alphaSize());
        alphaFlowMatrix.setExternalNumbers(a2b.getAlphaExternals1Based());
        //Loop through all alpha zones
        int[] externalAlphaZones = a2b.getAlphaExternals1Based();
        for(int i=1;i<=a2b.alphaSize();i++){
            for(int j=1;j<=a2b.alphaSize();j++){
                originTaz=externalAlphaZones[i];
                destinationTaz=externalAlphaZones[j];
                alphaFlowMatrix.setValueAt(originTaz,
                                           destinationTaz,
                                           calculateAlphaFlow(originTaz,destinationTaz,a2b));
            }
        }        
    }
    /**
     * Computes a probability matrix, where P = m.getValueAt(origin,destination)/m.getRowSum(origin) 
     *                                        = Value at the origin-destination pair / sum(all destinations for the origin)
     * @param m - Matrix  on which probabilities are calculated
     */
    public void setProbabilityMatrix(Matrix m){
        alphaFlowProbabilityMatrix = new Matrix(m.getRowCount(),m.getColumnCount());
        alphaFlowProbabilityMatrix.setExternalNumbers(m.getExternalNumbers());
        float probability;
        for(int i=0;i<m.getRowCount();i++){
            int origin = m.getExternalNumber(i);
            float rowSum = (float) m.getSum();
            //Loop through destination zones
            for(int j=0;j<m.getColumnCount();j++){
              
                int destination = m.getExternalNumber(j);
                if(rowSum>0){
                    probability = m.getValueAt(origin, destination)
                                    / rowSum;
                }
                else probability = 0;
                if(origin==ORIGIN_DEBUG && destination==DESTINATION_DEBUG)
                    logger.debug("Probability at "+origin+","+destination+"="+probability);
               
                alphaFlowProbabilityMatrix.setValueAt(origin,destination, probability);
            }
        }
    }
}
