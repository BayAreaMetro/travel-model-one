package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

/**
 * This class is used for ...
 *
 * @author Christi Willison
 * @version Nov 4, 2008
 *          <p/>
 *          Created by IntelliJ IDEA.
 */
public class StopLocationDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(StopLocationDMU.class);

    public HashMap<String, Integer> methodIndexMap;
    
    public IndexValues dmuIndex;
    public Household household;
    public Person person;
    public Tour tour;
    public Stop stop;


    public int[] altToZone;
    public int[] altToSubZone;

    // mode choice logsums for stop origin to stop destination alternatives
    public double[][] mcLogsumsIk;
    // mode choice logsums for stop destination apublices to tour primary destination
    public double[][] mcLogsumsKj;
    
    public double[][] dcSoaCorrections;
    private double[] logSizeTerms;

    private int stopNumber = -1;
    private int inboundStop = -1;

    private TazDataIf tazDataManager;
    private ModelStructure modelStructure;

    public StopLocationDMU(TazDataIf tazDataManager, ModelStructure modelStructure){
    	dmuIndex = new IndexValues();

        altToZone = tazDataManager.getAltToZoneArray();
        altToSubZone = tazDataManager.getAltToSubZoneArray();


        int numZones = tazDataManager.getNumberOfZones();
        int numSubZones = tazDataManager.getNumberOfSubZones();

        mcLogsumsIk = new double[numZones+1][numSubZones];
        mcLogsumsKj = new double[numZones+1][numSubZones];
        dcSoaCorrections = new double[numZones+1][numSubZones];

        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;
    }

    
    public void setDmuIndexValues( int hhid, int homeTaz, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhid );
        dmuIndex.setZoneIndex( homeTaz );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone(destTaz);

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( household.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug SL UEC" );
        }

    }

    public void setDcSoaCorrections( int zone, int subzone, double correction ){
        dcSoaCorrections[zone][subzone] = correction;
    }

    public void setTripMcLogsumIk( int zone, int subzone, double logsum ){
        mcLogsumsIk[zone][subzone] = logsum;
    }

    public void setTripMcLogsumKj( int zone, int subzone, double logsum ){
        mcLogsumsKj[zone][subzone] = logsum;
    }

    public void setLogSizeTerms( double[] stopLocSize ){
        logSizeTerms = stopLocSize;
    }

    public double getDcSoaCorrectionsAlt( int alt ){
        int zone = altToZone[alt];
        int subzone = altToSubZone[alt];
        return dcSoaCorrections[zone][subzone];
    }

    public double getTripModeChoiceLogsumOrigToStopAlt( int alt ) {
        int zone = altToZone[alt];
        int subzone = altToSubZone[alt];
        return mcLogsumsIk[zone][subzone];
    }

    public double getTripModeChoiceLogsumStopAltToDest( int alt ) {
        int zone = altToZone[alt];
        int subzone = altToSubZone[alt];
        return mcLogsumsKj[zone][subzone];
    }

    public int getStopDestAreaTypeAlt(int alt) {
        int[] at = tazDataManager.getZonalAreaType();
        return at[altToZone[alt]-1];
    }
    
    public double getLnStopDcSizeAlt( int alt ) {
        return logSizeTerms[alt];
    }

    public void setHouseholdObject ( Household household) {
        this.household = household;
    }

    public void setPersonObject ( Person person ) {
        this.person = person;
    }

    public void setTourObject(Tour tour) {
        this.tour = tour;
    }

    public void setStopObject(Stop stop) {
        this.stop = stop;
    }

    public Household getHouseholdObject() {
        return household;
    }

    public Person getPersonObject() {
        return person;
    }

    public IndexValues getDmuIndexValues(){
    	return dmuIndex;
    }

    public int getTourIsJoint() {
        return tour.getTourCategoryIsJointNonMandatory() ? 1 : 0;
    }
    

    public int getStopPurposeIsWork() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.WORK_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsEscort() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.ESCORT_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsShopping() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.SHOPPING_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsEatOut() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.EAT_OUT_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsOthMaint() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.OTH_MAINT_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsSocial() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.SOCIAL_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getStopPurposeIsOthDiscr() {
        return stop.getDestPurpose(modelStructure).equalsIgnoreCase( ModelStructure.OTH_DISCR_PURPOSE_NAME ) ? 1 : 0;
    }


    public int getTourOriginZone() {
        return tour.getTourOrigTaz();
    }

    public int getTourDestZone() {
        return tour.getTourDestTaz();
    }

    public int getTourMode() {
        return tour.getTourModeChoice();
    }

    public int getStopNumber() {
        return stopNumber;
    }

    public int getInboundStop() {
        return inboundStop;
    }

    public void setStopNumber(int stopNumber) {
        this.stopNumber = stopNumber;
    }

    public void setInboundStop(boolean inboundStop) {
        this.inboundStop = inboundStop ? 1 : 0;
    }





    public int getIndexValue(String variableName) {
        return methodIndexMap.get(variableName);
    }



    public int getAssignmentIndexValue(String variableName) {
        throw new UnsupportedOperationException();
    }

    public double getValueForIndex(int variableIndex) {
        throw new UnsupportedOperationException();
    }

    public double getValueForIndex(int variableIndex, int arrayIndex) {
        throw new UnsupportedOperationException();
    }

    public void setValue(String variableName, double variableValue) {
        throw new UnsupportedOperationException();
    }

    public void setValue(int variableIndex, double variableValue) {
        throw new UnsupportedOperationException();
    }
    
}