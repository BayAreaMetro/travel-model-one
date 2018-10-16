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

import org.apache.log4j.Logger;
import java.io.Serializable;

/**
 * @author Freedman
 *
 */
public class SummitHeader implements Serializable {
     
     protected int zones;
     protected int marketSegments;
     protected float transitInVehicleTime;
     protected float autoInVehicleTime;
     protected StringBuffer purpose = new StringBuffer();    //max 6 chars
     protected StringBuffer timeOfDay = new StringBuffer();  //max 6 chars
     protected StringBuffer title = new StringBuffer();      //max 60 chars
     protected static Logger logger = Logger.getLogger("com.pb.common.util");


    public SummitHeader(){
        
        this.purpose.setLength(6);
        this.timeOfDay.setLength(6);
        this.title.setLength(60);
        
    }

    public static void main(String[] args) {
        
        SummitHeader sh = new SummitHeader();
        sh.setPurpose("HBW");
        sh.setTimeOfDay("PEAK PERIOD");
        sh.setTitle("TEST HEADER TITLE");
        
        logger.info("purpose : "+sh.getPurpose());
        logger.info("period  : "+sh.getTimeOfDay());
        logger.info("title   : "+sh.getTitle());
        
        
    }
    /**
     * Returns the purpose.
     * @return String
     */
    public StringBuffer getPurpose() {
        return purpose;
    }

    /**
     * Returns the timeOfDay.
     * @return String
     */
    public StringBuffer getTimeOfDay() {
        return timeOfDay;
    }

    /**
     * Returns the title.
     * @return String
     */
    public StringBuffer getTitle() {
        return title;
    }

    /**
     * Returns the transitInVehicleTime.
     * @return float
     */
    public float getTransitInVehicleTime() {
        return transitInVehicleTime;
    }

    /**
     * Returns the zones.
     * @return int
     */
    public int getZones() {
        return zones;
    }

    /**
     * Sets the purpose.
     * @param purpose The purpose to set
     */
    public void setPurpose(String purpose) {

        int len = Math.min(purpose.length(),this.purpose.length());
        for(int i=0;i<len;++i)
            this.purpose.setCharAt(i,purpose.charAt(i));
        
        //fill the stringbuffer with spaces
        for(int i = purpose.length();i<this.purpose.length();++i)
            this.purpose.setCharAt(i,' ');
    }

    /**
     * Sets the timeOfDay.
     * @param timeOfDay The timeOfDay to set
     */
    public void setTimeOfDay(String timeOfDay) {
 
        int len = Math.min(timeOfDay.length(),this.timeOfDay.length());
        
        for(int i=0;i<len;++i)
            this.timeOfDay.setCharAt(i,timeOfDay.charAt(i));
        
        //fill the timeOfDay with " "
        for(int i = timeOfDay.length();i<this.timeOfDay.length();++i)
            this.timeOfDay.setCharAt(i,' ');
    }

    /**
     * Sets the title.
     * @param title The title to set
     */
    public void setTitle(String title) {

        int len = Math.min(title.length(),this.title.length());
        
        for(int i=0;i<len;++i)
            this.title.setCharAt(i,title.charAt(i));

        //fill the title with " "
        for(int i = title.length();i<this.title.length();++i)
            this.title.setCharAt(i,' ');
              
    }

    /**
     * Sets the transitInVehicleTime.
     * @param transitInVehicleTime The transitInVehicleTime to set
     */
    public void setTransitInVehicleTime(float transitInVehicleTime) {
        this.transitInVehicleTime = transitInVehicleTime;
    }

    /**
     * Sets the zones.
     * @param zones The zones to set
     */
    public void setZones(int zones) {
        this.zones = zones;
    }
    

    /**
     * Returns the marketSegments.
     * @return int
     */
    public int getMarketSegments() {
        return marketSegments;
    }

    /**
     * Sets the marketSegments.
     * @param marketSegments The marketSegments to set
     */
    public void setMarketSegments(int marketSegments) {
        this.marketSegments = marketSegments;
    }

    /**
     * Returns the autoInVehicleTime.
     * @return float
     */
    public float getAutoInVehicleTime() {
        return autoInVehicleTime;
    }

    /**
     * Sets the autoInVehicleTime.
     * @param autoInVehicleTime The autoInVehicleTime to set
     */
    public void setAutoInVehicleTime(float autoInVehicleTime) {
        this.autoInVehicleTime = autoInVehicleTime;
    }

}
