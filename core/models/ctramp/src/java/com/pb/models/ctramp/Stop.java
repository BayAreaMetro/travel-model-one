package com.pb.models.ctramp;

import java.io.Serializable;

import org.apache.log4j.Logger;

public class Stop implements Serializable {

    byte id;
    short orig;
    byte origWalkSegment;
    short dest;
    byte destWalkSegment;
    short parkTaz;
    byte mode;
    boolean inbound;
    short departHour;

    byte origPurposeIndex;
    byte destPurposeIndex;

    Tour parentTour;
    

    public Stop( Tour parentTour, int origPurposeIndex, int destPurposeIndex, int id, boolean inbound ){
        this.parentTour = parentTour;
        this.origPurposeIndex = (byte)origPurposeIndex;
        this.destPurposeIndex = (byte)destPurposeIndex;
        this.id = (byte)id;
        this.inbound = inbound;
        this.setDepartHour(this.getTourTodOut()); //default to tour depart/arrival hour
    }

    public void setOrig(int orig){
        this.orig = (short)orig;
    }

    public void setDest(int dest){
        this.dest = (short)dest;
    }

    public void setParkTaz(int park){
        this.parkTaz = (short)park;
    }

    public void setMode(int mode) {
        this.mode = (byte)mode;
    }
    
    public void setDepartHour(int hour) {
    	this.departHour = (short)hour;
    }

    public int getOrig(){
        return orig;
    }

    public int getDest(){
        return dest;
    }

    public int getParkTaz(){
        return parkTaz;
    }

    public int getOrigWalkSegment() {
        return origWalkSegment;
    }

    public void setOrigWalkSegment(int origWalkSegment) {
        this.origWalkSegment = (byte)origWalkSegment;
    }

    public int getDestWalkSegment() {
        return destWalkSegment;
    }

    public void setDestWalkSegment(int destWalkSegment) {
        this.destWalkSegment = (byte)destWalkSegment;
    }

    public String getOrigPurpose( ModelStructure modelStructure ) {
        return modelStructure.getPrimaryPurposeForIndex( origPurposeIndex );
    }
    
    public String getDestPurpose( ModelStructure modelStructure ) {
        return modelStructure.getPrimaryPurposeForIndex( destPurposeIndex );
    }
    
    public int getOrigPurposeIndex(){
        return origPurposeIndex;
    }

    public int getDestPurposeIndex(){
        return destPurposeIndex;
    }

    public int getMode() {
        return mode;
    }
    
    // guojy: this returns hour of day, not skim time period
    public int getTourTodOut() {
        if ( isInboundStop() ) {
            return parentTour.getTourEndHour();
        }
        else {
            return parentTour.getTourStartHour();
        }
    }
    
    public int getDepartHour() {
        return (int) departHour;
    }

    public Tour getTour() {
        return parentTour;
    }

    public boolean isInboundStop() {
        return inbound;
    }

    public int getStopId() {
        return id;
    }

    
    public void logStopObject( Logger logger, int totalChars, ModelStructure modelStructure ) {
        
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "-";

        String origPurpose = modelStructure.getSegmentedPurposeForIndex( origPurposeIndex );
        String destPurpose = modelStructure.getSegmentedPurposeForIndex( destPurposeIndex );
        
        Household.logHelper( logger, "stopId: ", id, totalChars );
        Household.logHelper( logger, "origPurposeIndex: ", origPurposeIndex, totalChars );
        Household.logHelper( logger, "destPurposeIndex: ", destPurposeIndex, totalChars );
        Household.logHelper( logger, "origPurpose: ", origPurpose, totalChars );
        Household.logHelper( logger, "destPurpose: ", destPurpose, totalChars );
        Household.logHelper( logger, "orig: ", orig, totalChars );
        Household.logHelper( logger, "origWalkSegment: ", origWalkSegment, totalChars );
        Household.logHelper( logger, "dest: ", dest, totalChars );
        Household.logHelper( logger, "destWalkSegment: ", destWalkSegment, totalChars );
        Household.logHelper( logger, "mode: ", mode, totalChars );
        Household.logHelper( logger, "direction: ", inbound ? "inbound" : "outbound", totalChars );
        Household.logHelper( logger, "departHour: ", departHour, totalChars );
        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }
    
}

