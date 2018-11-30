package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

public class AutoOwnershipChoiceDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(AutoOwnershipChoiceDMU.class);
    
    protected HashMap<String, Integer> methodIndexMap;

    
    protected Household hh;
    private IndexValues dmuIndex;

    private double workTourAutoTimeSavings;
    private double workTourAutoTime;
    private double schoolDriveTourAutoTimeSavings;
    private double schoolNonDriveTourAutoTimeSavings;

    
    public AutoOwnershipChoiceDMU (){
    	dmuIndex = new IndexValues();
    }
    
    
    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }
    
    
    
    // DMU methods - define one of these for every @var in the mode choice control file.

    public void setDmuIndexValues( int hhId, int zoneId, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhId );
        dmuIndex.setZoneIndex( zoneId );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( hh.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug AO UEC" );
        }

    }
    
    public IndexValues getDmuIndexValues() {
        return dmuIndex; 
    }

    
    public Household getHouseholdObject() {
        return hh;
    }
    
    public int getSize() {
        return hh.getSize();
    }
    
    public int getNumChildrenUnder16() {
        return hh.getNumChildrenUnder16();
    }
    
    public int getDrivers() {
        return hh.getDrivers();
    }
    
    public int getWorkers() {
        return hh.getWorkers();
    }

    public int getStudents() {
        return hh.getNumStudents();
    }

    public int getNumPersons16to17() {
        return hh.getNumPersons16to17();
    }
    
    public int getNumPersons18to24() {
        return hh.getNumPersons18to24();
    }    
    
    public void setWorkTourAutoTimeSavings( double value ) {
        workTourAutoTimeSavings = value;
    }
    
    public void setWorkTourAutoTime( double value ) {
        workTourAutoTime = value;
    }

    
    public double getWorkTourAutoTimeSavings() {
        return workTourAutoTimeSavings;
    }
    
    public double getWorkTourAutoTime() {
        return workTourAutoTime;
    }
   public void setSchoolDriveTourAutoTimeSavings( double value ) {
        schoolDriveTourAutoTimeSavings = value;
    }
    
    public double getSchoolDriveTourAutoTimeSavings() {
        return schoolDriveTourAutoTimeSavings;
    }
    
    public void setSchoolNonDriveTourAutoTimeSavings( double value ) {
        schoolNonDriveTourAutoTimeSavings = value;
    }
    
    public double getSchoolNonDriveTourAutoTimeSavings() {
        return schoolNonDriveTourAutoTimeSavings;
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
