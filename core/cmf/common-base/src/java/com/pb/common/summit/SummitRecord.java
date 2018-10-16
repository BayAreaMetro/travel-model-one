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
public interface SummitRecord {
                    
    /**
     * Returns the ataz.
     * @return short
     */
    public short getAtaz();

    /**
     * Returns the driveTransitOnlyShare.
     * @return float
     */
    public float getDriveTransitOnlyShare();

    /**
     * Returns the expAuto.
     * @return float
     */
    public float getExpAuto();

    /**
     * Returns the market.
     * @return short
     */
    public short getMarket();

    /**
     * Returns the motorizedTrips.
     * @return float
     */
    public float getMotorizedTrips();

    /**
     * Returns the ptaz.
     * @return short
     */
    public short getPtaz();

    /**
     * Returns the transitShareOfDriveTransitOnly.
     * @return float
     */
    public float getTransitShareOfDriveTransitOnly();

    /**
     * Returns the transitShareOfWalkTransit.
     * @return float
     */
    public float getTransitShareOfWalkTransit();

    /**
     * Returns the trips.
     * @return float
     */
    public float getTrips();

    /**
     * Returns the walkTransitAvailableShare.
     * @return float
     */
    public float getWalkTransitAvailableShare();

    /**
     * Sets the ataz.
     * @param ataz The ataz to set
     */
    public void setAtaz(short ataz);
    /**
     * Sets the driveTransitOnlyShare.
     * @param driveTransitOnlyShare The driveTransitOnlyShare to set
     */
    public void setDriveTransitOnlyShare(float driveTransitOnlyShare);

    /**
     * Sets the expAuto.
     * @param expAuto The expAuto to set
     */
    public void setExpAuto(float expAuto);

    /**
     * Sets the market.
     * @param market The market to set
     */
    public void setMarket(short market);

    /**
     * Sets the motorizedTrips.
     * @param motorizedTrips The motorizedTrips to set
     */
    public void setMotorizedTrips(float motorizedTrips);

    /**
     * Sets the ptaz.
     * @param ptaz The ptaz to set
     */
    public void setPtaz(short ptaz);

    /**
     * Sets the transitShareOfDriveTransitOnly.
     * @param transitShareOfDriveTransitOnly The transitShareOfDriveTransitOnly to set
     */
    public void setTransitShareOfDriveTransitOnly(float transitShareOfDriveTransitOnly);

    /**
     * Sets the transitShareOfWalkTransit.
     * @param transitShareOfWalkTransit The transitShareOfWalkTransit to set
     */
    public void setTransitShareOfWalkTransit(float transitShareOfWalkTransit);

    /**
     * Sets the trips.
     * @param trips The trips to set
     */
    public void setTrips(float trips);

    /**
     * Sets the walkTransitAvailableShare.
     * @param walkTransitAvailableShare The walkTransitAvailableShare to set
     */
    public void setWalkTransitAvailableShare(float walkTransitAvailableShare);
}
