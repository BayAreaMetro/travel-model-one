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
package com.pb.common.summit;

import java.io.Serializable;

import org.apache.log4j.Logger;


/**
 * This class contains a record for the FTA SUMMIT User Benefit program.
 * The record can be used for either an aggregate trip-based model
 * or a microsimulation model. 
 * 
 * In the case of the microsimulation model,
 * the number of trips is always 1.  
 * 
 * motorizedTrips is either 0 or 1 depending on the chosen mode.  
 * 
 * walkTransitAvailableShare is 0 or 1 depending on whether walk-transit
 * is available for the trip.
 * 
 * transitShareOfWalkTransit is the probability of transit if walk-transit
 * mode is available for the trip (walkTransitAvailableShare is 1). 
 * 
 * driveTransitOnlyShare is 0 or 1 depending on if drive-transit is available.
 * If walkTransitAvailableShare is 1 then driveTransitOnlyShare must be 0.
 * 
 * transitShareOfDriveTransitOnly is the probability of transit if
 * driveTransitOnlyShare is 1.
 * 
 * @author Freedman
 *
 */
public class ConcreteSummitRecord implements SummitRecord, Serializable, Comparable{
    
    protected int ptazI;
    protected int atazI;
    protected short ptaz;
    protected short ataz;
    protected short market;
    protected float trips;
    protected float motorizedTrips;
    protected float expAuto;
    protected float walkTransitAvailableShare;  //0 or 1 for micro sample
    protected float transitShareOfWalkTransit;  //probability of transit if walk-only 
    protected float driveTransitOnlyShare;      //0 or 1 for micro sample
    protected float transitShareOfDriveTransitOnly; //prob transit if drive-only
    
    /**
     * Default constructor.
     */
    public ConcreteSummitRecord(){
    	
    }
    
    public static void main(String[] args) {
    }
    /**
     * Returns the ataz.
     * @return short
     */
    public short getAtaz() {
        return ataz;
    }
    
    public int getIntAtaz() {
        return atazI;
    }

    /**
     * Returns the driveTransitOnlyShare.
     * @return float
     */
    public float getDriveTransitOnlyShare() {
        return driveTransitOnlyShare;
    }

    /**
     * Returns the expAuto.
     * @return float
     */
    public float getExpAuto() {
        return expAuto;
    }

    /**
     * Returns the market.
     * @return short
     */
    public short getMarket() {
        return market;
    }

    /**
     * Returns the motorizedTrips.
     * @return float
     */
    public float getMotorizedTrips() {
        return motorizedTrips;
    }

    /**
     * Returns the ptaz.
     * @return short
     */
    public short getPtaz() {
        return ptaz;
    }
    
    /**
     * Returns the ptaz.
     * @return short
     */
    public int getIntPtaz() {
        return ptazI;
    }

    /**
     * Returns the transitShareOfDriveTransitOnly.
     * @return float
     */
    public float getTransitShareOfDriveTransitOnly() {
        return transitShareOfDriveTransitOnly;
    }

    /**
     * Returns the transitShareOfWalkTransit.
     * @return float
     */
    public float getTransitShareOfWalkTransit() {
        return transitShareOfWalkTransit;
    }

    /**
     * Returns the trips.
     * @return float
     */
    public float getTrips() {
        return trips;
    }

    /**
     * Returns the walkTransitAvailableShare.
     * @return float
     */
    public float getWalkTransitAvailableShare() {
        return walkTransitAvailableShare;
    }

    /**
     * Sets the ataz.
     * @param ataz The ataz to set
     */
    public void setAtaz(short ataz) {
        this.ataz = ataz;
    }
    
    /**
     * Sets the ataz.
     * @param ataz The ataz to set
     */
    public void setIntAtaz(int atazI) {
        this.atazI = atazI;
    }

    /**
     * Sets the driveTransitOnlyShare.
     * @param driveTransitOnlyShare The driveTransitOnlyShare to set
     */
    public void setDriveTransitOnlyShare(float driveTransitOnlyShare) {
        this.driveTransitOnlyShare = driveTransitOnlyShare;
    }

    /**
     * Sets the expAuto.
     * @param expAuto The expAuto to set
     */
    public void setExpAuto(float expAuto) {
        this.expAuto = expAuto;
    }

    /**
     * Sets the market.
     * @param market The market to set
     */
    public void setMarket(short market) {
        this.market = market;
    }

    /**
     * Sets the motorizedTrips.
     * @param motorizedTrips The motorizedTrips to set
     */
    public void setMotorizedTrips(float motorizedTrips) {
        this.motorizedTrips = motorizedTrips;
    }

    /**
     * Sets the ptaz.
     * @param ptaz The ptaz to set
     */
    public void setPtaz(short ptaz) {
        this.ptaz = ptaz;
    }
    
    /**
     * Sets the ptaz as long integer.
     * @param ptaz The ptaz to set
     */
    public void setIntPtaz(int ptazI) {
        this.ptazI = ptazI;
    }

    /**
     * Sets the transitShareOfDriveTransitOnly.
     * @param transitShareOfDriveTransitOnly The transitShareOfDriveTransitOnly to set
     */
    public void setTransitShareOfDriveTransitOnly(float transitShareOfDriveTransitOnly) {
        this.transitShareOfDriveTransitOnly = transitShareOfDriveTransitOnly;
    }

    /**
     * Sets the transitShareOfWalkTransit.
     * @param transitShareOfWalkTransit The transitShareOfWalkTransit to set
     */
    public void setTransitShareOfWalkTransit(float transitShareOfWalkTransit) {
        this.transitShareOfWalkTransit = transitShareOfWalkTransit;
    }

    /**
     * Sets the trips.
     * @param trips The trips to set
     */
    public void setTrips(float trips) {
        this.trips = trips;
    }

    /**
     * Sets the walkTransitAvailableShare.
     * @param walkTransitAvailableShare The walkTransitAvailableShare to set
     */
    public void setWalkTransitAvailableShare(float walkTransitAvailableShare) {
        this.walkTransitAvailableShare = walkTransitAvailableShare;
    }

    /**
     * Use for sorting a collection of ConcreteSummitRecords by origin, destination, and market.
     * Supports zone numbers up to 99999 and up to 99 markets.
     * 
     * @param record  A comparison ConcreteSummitRecord
     * @return -1: this < than record; 0: this==equal; 1: this > record
     */
    public int compareTo(Object record){
       
        long thisIndex=this.getKey();
        
        ConcreteSummitRecord sr = (ConcreteSummitRecord) record;
        long recordIndex=sr.getKey();
        
        if(thisIndex<recordIndex)
            return -1;
        else if(thisIndex>recordIndex)
            return 1;
        
        return 0;
        
    }
    
    /**
     * Calculate the key for this record, based on origin, destination, market.
     * 
     * @return  The key for the record
     */
    public long getKey(){
        long pt=(long)this.ptaz;
        long at=(long)this.ataz;
        long mk=(long)this.market;
        long thisIndex=pt*100000*100+at*100+mk;
        return thisIndex;
    }
    
    /**
     * Write the summit record to the logger. 
     * 
     * @param localLogger - the logger to which to send the results
     */
    public void logSummitRecord(Logger localLogger) {

    	localLogger.info("\n");
    	localLogger.info("Summit Record Information: ");    	
    	localLogger.info(String.format("  PTAZ                                = %16d", getPtaz()));
    	localLogger.info(String.format("  ATAZ                                = %16d", getAtaz()));
    	localLogger.info(String.format("  Market                              = %16d", getMarket()));
    	localLogger.info(String.format("  Trips                               = %16.8f", getTrips()));
    	localLogger.info(String.format("  Motorized Trips                     = %16.8f", getMotorizedTrips()));
    	localLogger.info(String.format("  Exp Auto Utility                    = %16.8f", getExpAuto()));
    	localLogger.info(String.format("  Walk Transit Available Share        = %16.8f", getWalkTransitAvailableShare()));
    	localLogger.info(String.format("  Transit Share of Walk Transit       = %16.8f", getTransitShareOfWalkTransit()));
    	localLogger.info(String.format("  Drive Transit Only Share            = %16.8f", getDriveTransitOnlyShare()));
    	localLogger.info(String.format("  Transit Share of Drive Transit Only = %16.8f", getTransitShareOfDriveTransitOnly()));
    	localLogger.info("\n"); 
        
    }
    
}
