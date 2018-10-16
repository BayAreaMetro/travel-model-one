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
package com.pb.common.model;

import com.pb.common.math.MathUtil;
import com.pb.common.matrix.ColumnVector;
import com.pb.common.matrix.Matrix;

import com.pb.common.model.ModelException;
import org.apache.log4j.Logger;


/**
 * Implementation of the Event model for special events.
 *
 * The Event model is a trip generation and distribution model.  The form of
 * the model is:
 *
 *      P = A^theta * exp(lambda * cu + omega * min(D, cap))
 *
 *      where:  P - probability of a trip
 *              A - zonal activity size
 *              cu - measure of impedance or combined utility
 *              theta, lambda, omega - estimated coefficients
 *              D - distance between PA zones
 *              Cap - the upper limit of distance
 *
 *  @author   Andrew Stryker <stryker@pbworld.com>
 *  @version  1.1 2/9/2004
 */
public class EventModel {
    protected Logger logger = Logger.getLogger("com.pb.miami.events");
    protected String name;
    protected boolean available;
    protected double theta;
    protected double lambda;
    protected double omega;
    protected double cap;
    protected Matrix impedance;
    protected Matrix distance;
    private boolean useDistance;
    protected ColumnVector size;
    protected Matrix trips;
    protected int eventZone;

    /**
     * Constructor.
     *
     * Default.
     */
    public EventModel() {
    }

    /**
     * Constructor.
     *
     * Sets model parameters.
     *
     * @param name of the model/scenario
     * @param eventZone location of event
     * @param theta size term coefficient
     * @param lambda impedance coefficient
     */
    public EventModel(String name, int eventZone, double theta, double lambda) {
        this(name,eventZone,theta,lambda,-1,-1,false);
    }

    /**
     * Constructor.
     *
     * Sets model parameters.
     *
     * @param name of the model/scenario
     * @param eventZone location of event
     * @param theta size term coefficient
     * @param lambda impedance coefficient
     * @param omega distance coefficient
     * @param cap max distance
     */
    public EventModel(String name, int eventZone, double theta, double lambda, double omega, double cap) { 
        this(name,eventZone,theta,lambda,omega,cap,true);
    }
    
    private EventModel(String name, int eventZone, double theta, double lambda, double omega, double cap, boolean useDistance) {
        this.name = name;
        this.eventZone = eventZone;
        this.theta = theta;
        this.lambda = lambda;
        this.omega = omega;
        this.cap = cap;
        this.useDistance = useDistance;
        logger.debug("EventModel object constructed with theta = " + theta +
            ", lambda = " + lambda + ", omega = " + omega + " and cap = " + cap);
    }

    /*---------- setters and getters ----------*/

    /**
     * Set eventZone.
     *
     * @param eventZone location of the event
     */
    public void setEventZone(int eventZone) {
        this.eventZone = eventZone;
    }

    /**
     * Get eventZone.
     */
    public int getEventZone() {
        return eventZone;
    }

    /**
     * Set theta.
     *
     * @param theta activity size coefficient
     */
    public void setTheta(double theta) {
        this.theta = theta;
        available = false;
    }

    /**
     * Set lambda.
     *
     * @param lambda impedance coefficient
     */
    public void setLambda(double lambda) {
        this.lambda = lambda;
        available = false;
    }

    /**
     * Set name.
     *
     * @param name of the model/scenario
     */
    public void setName(String name) {
        this.name = name;
        available = false;
    }

    /**
     * Set impdenace matrix.
     *
     * @param impedance production to Event zones impedance
     */
    public void setImpedance(Matrix impedance) {
        this.impedance = impedance;
        available = false;
    }

    /**
     * Set distance matrix.
     *
     * @param distance production to Event zones 
     */
    public void setDistance(Matrix distance) {
        this.distance = distance;
        available = false;
    }

    /**
     * Set size vector.
     *
     * @param size zone activity size
     */
    public void setSize(ColumnVector size) {
        this.size = size;
        available = false;
    }

    /**
     * Get theta.
     *
     * @return theta, the size parameter.
     */
    public double getTheta() {
        return theta;
    }

    /**
     * Get lambda.
     *
     * @return lambda, the impedance parameter.
     */
    public double getLambda() {
        return lambda;
    }

    /**
     * Get omega.
     *
     * @return omega, the distance parameter.
     */
    public double getOmega() {
        return omega;
    }

    /**
     * Get cap.
     *
     * @return cap, the max distance.
     */
    public double getCap() {
        return cap;
    }

    /**
     * Get name of model.
     *
     * @return name.
     */
    public String getName() {
        return name;
    }

    /*---------- general methods ----------*/

    /**
     * Indicator for available probabilities.
     */
    public boolean isAvailable() {
        return available;
    }

    /**
     * Indicator of calculation readiness.
     */
    public boolean isReady() {
        if ((impedance == null) || (useDistance && distance == null) || (size == null)) {
            return false;
        }

        return true;
    }

    /**
     * Calculate probabilities in the Event framework.
     *
     * The results are scaled so that each column sums to one.
     *
     * @throws ModelException if size, distance or impedance is not set.
     */
    public void calculateProbalities() throws ModelException {
        calculateTrips((float) 1.0);
    }

    /**
     * Calculate trips in the Event framework.
     *
     * The results are scaled so that each column sums to number of trips,
     * which should be the exogenously determined total number of attractions.
     *
     * @param attractions trip attractions is an int
     *
     * @throws ModelException if size or impedance is not set.
     */
    public void calculateTrips(int attractions) throws ModelException {
        calculateTrips((float) attractions);
    }

    /**
     * Calculate trips in the Event framework.
     *
     * The results are scaled so that each column sums to number of trips,
     * which should be the exogenously determined total number of attractions.
     *
     * @throws ModelException if size or impedance is not set.
     */
    public void calculateTrips(float attractions) throws ModelException {
        if (!isReady()) {
            throw new ModelException("Size, distance and impedance must be set first.");
        }

        logger.debug("calculating trips.");
        logger.debug("        zone  site  theta lambda omega cap     size distance impedance probability");

        int rowCount = impedance.getRowCount();
        int columnCount = impedance.getColumnCount();
        trips = new Matrix(name, "Event model trips", rowCount, columnCount);
        
        int[] externals =impedance.getExternalNumbers();
        logger.info("externals[0]="+externals[0]);
        
        if( externals[0]==0)
            trips.setExternalNumbers(impedance.getExternalNumbers());
        else
            trips.setExternalNumbersZeroBased(impedance.getExternalNumbers());
            
        // loop through the rowCount of size as this can be smaller than that
        // of impedance
        int sizeRowCount = size.getRowCount();
        float value;
        int extRow;

        for (int row = 1; row <= sizeRowCount; row++) {
        	//Wu added next line, it seem like a bug if matrix index numbers are not sequential
        	//getValueAt(row, column) of Matrix or getValueAt(row) of ColumnVector always assume external row and column index
        	extRow=size.getExternalNumber(row-1);
            
           float s = size.getValueAt(extRow);

            if (s > 0) {
                value = (float) (Math.pow(s, theta) * MathUtil.exp(lambda * impedance.getValueAt(
                            extRow, eventZone) + (useDistance ? omega * Math.min(distance.getValueAt(extRow, eventZone),cap) : 0)));
            } else {
                value = 0;
            }

            if (Double.isNaN(value)) {
                throw new ModelException(ModelException.INVALID_UTILITY);
            }

            trips.setValueAt(extRow, eventZone, value);

            if ((row < 10) || ((row % 100) == 0)) {
                float imp = 0;
                float dist = 0;
                if (s > 0) {
                   imp = impedance.getValueAt(extRow, eventZone);
                   dist = useDistance ? distance.getValueAt(extRow, eventZone) : 0;
                }
 
                if (useDistance) {
                    logger.debug("      " + String.format("%5d ", extRow) +
                                            String.format("%5d ", eventZone) +
                                            String.format("%6.3f ", theta) +
                                            String.format("%6.3f ", lambda) +
                                            String.format("%6.3f ", omega) +
                                            String.format("%6.3f ", cap) +
                                            String.format("%6f ", size.getValueAt(extRow)) +
                                            String.format("%9f ", imp) +
                                            String.format("%9f ", dist) +
                                            String.format("%19.17f", trips.getValueAt(extRow, eventZone)));
                } else {
                    logger.debug("      " + String.format("%5d ", extRow) +
                                            String.format("%5d ", eventZone) +
                                            String.format("%6.3f ", theta) +
                                            String.format("%6.3f ", lambda) +
                                            String.format("%6f ", size.getValueAt(extRow)) +
                                            String.format("%9f ", imp) +
                                            String.format("%19.17f", trips.getValueAt(extRow, eventZone)));
                }
            }
        }

        scale(attractions);
        available = true;
    }

    /**
     * Scale so that each column sum to the target.
     */
    protected void scale(float target) {
        float columnSum;

        logger.debug("scalingtrips.");
        logger.debug(" zone probalility factor scaled");

        int rowTotal = trips.getRowCount();

        columnSum = (float) trips.getColumnSum(eventZone);

        // Dividing each matrix cell in a column by the column sum results
        // in a column summing to 1.0.  Multiply by the target to get
        // a column summing to the target.
        float factor = target / columnSum;
        float prob;
        float scaled;
        int extRow;

        for (int row = 1; row <= rowTotal; row++) {
            
        	//Wu added next lines, it seem like a bug if matrix zones are not sequential
        	//getValueAt(row, column) of Matrix or getValueAt(row) of ColumnVector always assume external row and column index
        	//eventZone is ok, because usually is is read in as an external zone
        	extRow=trips.getExternalNumber(row-1);
        	
            prob = trips.getValueAt(extRow, eventZone);
            scaled = prob * factor;
            trips.setValueAt(extRow, eventZone, scaled);

            if ((row < 10) || ((row % 100) == 0)) {
                logger.debug("      " + String.format("%5d ", extRow) +
                    String.format("%9f ", prob) +
                    String.format("%10.5f ", factor) +
                    String.format("%18.16f", trips.getValueAt(extRow, eventZone)));
            }
        }
    }

    /**
     * Get the choice probabilities.
     *
     * @return an array containing the choice probabilities.
     */
    public Matrix getTrips() {
        return trips;
    }

    /**
     * Summarize application.
     *
     * @return string describing model application.
     */
    public String summarize() {
        String status = "EventModel summary for " + name + ":\n" + "theta = " +
            theta + "\n" + "lambda = " + lambda + "\n" + "omega = " + omega + "\n" + "cap = " + cap + "\n";

        if (isAvailable()) {
            status += ("sum of probabilities: " + trips.getSum());
        } else {
            status += "probabilities not yet calculated";
        }

        return status;
    }
}
