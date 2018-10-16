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

/**
 * MatrixExpansion2.java This class expands a betaZone matrix to an alphaZone
 * matrix
 * 
 * A betaZone is an aggregation of alphaZones. For example, alphaZones are TAZs,
 * while betaZones are districts containing a group of TAZs.
 * 
 * The formula for the expansion is: F(alpha) = F(beta) *
 * alphaProduction(aOrigin)/sum of alphaProduction for all alphaZones in bOrigin *
 * alphaConsumption(aDestination)/sum of alphaConsumption for all alphaZones in
 * bOrigin * alphaPropensity(aOrigin,aDestination)/sum of alphaPropensity for
 * all alphaZones in bOrigin and bDestination
 * 
 * The inputs for performing the expansion are: AlphaToBeta - an alpha to beta
 * zone mapping (passed in constructor) betaFlowMatrix alphaProductionVector
 * alphaConsumptionVector alphaPropensityMatrix
 * 
 * @author Steve Hansen, modified by Andrew Stryker
 * @version 2.0
 * 
 */
public class MatrixExpansion2 {
    protected static Logger logger = Logger.getLogger(MatrixExpansion2.class);
    private static int nWarnMessages = 0;

    // Matrix representing the "production" of each alphaZone
    // This Matrix has one column
    protected ColumnVector alphaProductions;

    protected ColumnVector betaProductions;

    // Matrix containing the "consumption" of each alphaZone
    // This Matrix has one column
    protected RowVector alphaConsumptions;

    protected RowVector betaConsumptions;

    // the propensity to travel between alphaZones
    protected Matrix alphaPropensity;

    // flows between betaZones
    protected Matrix betaFlow;

    // MatrixCompression - class used to compress alpha Matrices to beta
    // Matrices
    protected MatrixCompression compress;

    protected Matrix betaPropensity;

    // output - alphaFlowMatrix - a Matrix of alpha flows
    protected Matrix alphaFlow;

    // output - alphaFlowProbabilityMatrix - a Matrix of probabilities of flow
    // between alphazones
    protected Matrix alphaFlowProbability;

    /**
     * Constructor.
     * 
     * @param a2b
     *            alphaZone to betaZone mapping
     */
    public MatrixExpansion2(AlphaToBeta a2b) {
        compress = new MatrixCompression(a2b);

        betaProductions = new ColumnVector(a2b.betaSize());
        betaProductions.setExternalNumbers(a2b.getBetaExternals1Based());

        betaConsumptions = new RowVector(a2b.betaSize());
        betaConsumptions.setExternalNumbers(a2b.getBetaExternals1Based());
    }

    /**
     * Set the matrix of $ flows between betaZones
     * 
     * @param m -
     *            the beta flow matrix
     */
    public void setBetaFlowMatrix(Matrix m) {
        betaFlow = m;
        
        int[] extNumbers = betaFlow.getExternalNumbers();
        
        for (int i = 1; i < extNumbers.length; ++i) {
            int district = extNumbers[i];

            float sum = betaFlow.getRowSum(district);
            betaProductions.setValueAt(district, sum);

            sum = betaFlow.getColumnSum(district);
            betaConsumptions.setValueAt(district, sum);
        }
    }

    /**
     * Set the ColumnVector that contains the production numbers for each
     * alphaZone
     * 
     * @param m -
     *            column vector
     */
    public void setProductionMatrix(ColumnVector m) {
        alphaProductions = m;
    }

    /**
     * Set the RowVector that contains the production numbers for each alphaZone
     * 
     * @param m -
     *            row vector
     */
    public void setConsumptionMatrix(RowVector m) {
        alphaConsumptions = m;
    }

    /**
     * Set the Matrix that contains the propensity to travel between alphaZones
     * Also sets the betaPropensityMatrix by compressing the
     * alphaPropensityMatrix
     * 
     * @param m -
     *            the propensity matrix
     */
    public void setPropensityMatrix(Matrix m) {
        alphaPropensity = m;
        betaPropensity = compress.getCompressedMatrix(m, "MEAN");
    }

    /**
     * Get the flows between two given betaZones
     * 
     * @param origin
     * @param destination
     * @return betaFlowMatrix.getValueAt(origin, destination)
     */
    public float getBetaFlow(int origin, int destination) {
        return betaFlow.getValueAt(origin, destination);
    }

    /**
     * Get the full alphaFlowMatrix
     * 
     * @return alphaFlowMatrix
     */
    public Matrix getAlphaFlowMatrix() {
        return alphaFlow;
    }

    /**
     * gets the full alphaFlowProbabilityMatrix
     * 
     * @return alphaFlowMatrix
     */
    public Matrix getAlphaFlowProbabilityMatrix() {
        return alphaFlowProbability;
    }

    /**
     * calculates the flow between an alphaZone pair flow is based on the
     * following formula:
     * 
     * F(alpha) = F(beta) 
     *      * alphaProduction(aOrigin) / sum(alphaProduction * alphaZone in bOrigin)
     *      * alphaConsumption(aDestination) / sum(alphaConsumption * alphaZones in bOrigin)
     *      * alphaPropensity(aOrigin, aDestination) /
     *           sum(alphaPropensity * alphaZone in bOrigin * alphaZone * bDestination)
     * 
     * @param aOrigin -
     *            alphaZone origin
     * @param aDestination -
     *            alphaZone destination
     * @param a2b
     *            AlphaToBeta districting system
     *
     * @return flow - flow between the alphaZone pair
     */
    public float calculateAlphaFlow(int aOrigin, int aDestination,
            AlphaToBeta a2b) {
        int bOrigin = a2b.getBetaZone(aOrigin);
        int bDestination = a2b.getBetaZone(aDestination);

        float betaProductionValue = betaProductions.getValueAt(bOrigin);

        if (betaProductionValue == 0) {
            if (nWarnMessages < 50) {
                logger.warn("betaProductionValue is 0 in origin " + bOrigin);
                nWarnMessages ++;
            }
            return 0;
        }

        float originZoneFlow = alphaProductions.getValueAt(aOrigin)
                / betaProductionValue;

        float betaConsumptionValue = betaConsumptions.getValueAt(bDestination);

        if (betaConsumptionValue == 0) {
            if (nWarnMessages < 50) {
                logger.warn("betaConsumptionValue is 0 in destination "
                        + bDestination);
                nWarnMessages ++;
            }
            return 0;
        }

        float destinationZoneFlow = alphaConsumptions.getValueAt(aDestination)
                / betaConsumptionValue;

        float betaPropensityValue = betaPropensity.getValueAt(bOrigin,
                bDestination);

        if (betaPropensityValue == 0) {
            if (nWarnMessages < 50) {
                logger.warn("betaPropensityValue is 0 in O-D " + bOrigin + " "
                        + bDestination);
                nWarnMessages ++;
            }
            return 0;
        }

        float propensityFlow = alphaPropensity.getValueAt(aOrigin,
                aDestination)
                / betaPropensityValue;

        float flow = (getBetaFlow(bOrigin, bDestination) * originZoneFlow
                * destinationZoneFlow * propensityFlow);


        if (logger.isDebugEnabled()) {
            if (new Float(flow).isNaN()) {
                logger.info("Beta Origin: " + bOrigin + " Beta Destination: "+
                        bDestination + " Beta Flow: " +  getBetaFlow(bOrigin, bDestination));
                logger.info("Origin: " + aOrigin + " alphaProd: " + alphaProductions.getValueAt(aOrigin) +
                        " betaProd: " + betaProductionValue + " Flow: " + originZoneFlow);
                logger.info("Destination: " + aDestination+ " alphaCons: " + alphaConsumptions.getValueAt(aDestination) +
                        " betaCons: " + betaConsumptionValue + " Flow: " + destinationZoneFlow);
                logger.info("Propensity Flow: " + propensityFlow);
                logger.info("flow = " + flow);
                logger.info("");
            }
        }

        return flow;
    }

    /**
     * Fills the alphaFlowMatrix - calculates alphaZoneFlows for each alphaZone
     * pair using calculateAlphaFlow method
     * 
     * @param a2b -
     *            Alpha to Beta Matrix
     */
    public void setAlphaFlowMatrix(AlphaToBeta a2b) {
        int originTaz;
        int destinationTaz;
        alphaFlow = new Matrix(a2b.alphaSize(), a2b.alphaSize());
        alphaFlow.setExternalNumbers(a2b.getAlphaExternals1Based());
        // Loop through all alpha zones
        int[] externalAlphaZones = a2b.getAlphaExternals1Based();
        for (int i = 1; i <= a2b.alphaSize(); i++) {
            originTaz = externalAlphaZones[i];
            for (int j = 1; j <= a2b.alphaSize(); j++) {
                destinationTaz = externalAlphaZones[j];
                alphaFlow.setValueAt(originTaz, destinationTaz,
                        calculateAlphaFlow(originTaz, destinationTaz, a2b));
            }
        }
    }

    /**
     * Computes a probability matrix, where P =
     * m.getValueAt(origin,destination)/m.getRowSum(origin) = Value at the
     * origin-destination pair / sum(all destinations for the origin)
     * 
     * @param m -
     *            Matrix on which probabilities are calculated
     */
    public void setProbabilityMatrix(Matrix m, String name) {
        alphaFlowProbability = new Matrix(m.getRowCount(), m
                .getColumnCount());
        alphaFlowProbability.setExternalNumbers(m.getExternalNumbers());
        if(name != null)
            alphaFlowProbability.setName(name);
        float probability;
        for (int i = 0; i < m.getRowCount(); i++) {
            int origin = m.getExternalNumber(i);
            float rowSum = m.getRowSum(origin);
            // Loop through destination zones
            for (int j = 0; j < m.getColumnCount(); j++) {

                int destination = m.getExternalNumber(j);
                if (rowSum > 0) {
                    probability = m.getValueAt(origin, destination) / rowSum;
                } else
                    probability = 0;

                alphaFlowProbability.setValueAt(origin, destination,
                        probability);
            }
        }
    }
}