package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

public class TripModeChoiceDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(TripModeChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    protected Stop stop;
    protected Tour tour;
    protected Person person;
    protected Household hh;
    protected IndexValues dmuIndex;

    protected int origType;
    protected int destType;
    protected float origParkRate;
    protected float primDestParkRate;
    protected float intStopParkRate;
    
    protected int stopIsFirst;
    protected int stopIsLast;
    

    private ModelStructure modelStructure;
    
    /**
     * Real constructor
     * @param modelStructure  An object with all model structure variables
     */
    public TripModeChoiceDMU( ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
    	dmuIndex = new IndexValues();
    }
    
    /**
     * Constructor for testing purposes only
     */
    public TripModeChoiceDMU(){
    	
    }


    /**
     * Get the household object
     * @return The household
     */
    public Household getHouseholdObject() {
        return hh;
    }
    
    /**
     * Get the tour object
     * @return The tour
     */
    public Tour getTourObject() {
        return tour;
    }
    
    /**
     * Set the household object
     * @param hhObject  The household
     */
    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }
    
    /**
     * Set the person object
     * @param personObject The person
     */
    public void setPersonObject ( Person personObject ) {
        person = personObject;
    }
    
    /**
     * Set the tour object
     * @param tourObject  The tour
     */
    public void setTourObject ( Tour tourObject ) {
        tour = tourObject;
    }
    
    /**
     * Set the stop object
     * @param stopObject  The stop
     */
    public void setStopObject ( Stop stopObject ) {
        stop = stopObject;
    }
    
    /**
     * Set a flag indicating whether this is the first stop
     * @param flag True if first stop, else false.
     */
    public void setStopObjectIsFirst ( int flag ) {
        stopIsFirst = flag;
    }
    
    /**
     * Set a flag indicating whether this is the last stop
     * @param flag
     */
    public void setStopObjectIsLast ( int flag ) {
        stopIsLast = flag;
    }
    
    
    
    // DMU methods - define one of these for every @var in the mode choice control file.

    public void setDmuIndexValues( int hhId, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhId );
        dmuIndex.setZoneIndex( destTaz );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( hh.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug Trip MC UEC" );
        }

    }
    
    
    /**
     * origin type is 1 if home, 2 if primary dest, 3 if intermediate stop, for home-based tours.
     * origin type is 1 if work, 2 if primary dest, 3 if intermediate stop, for work-based tours.
     */
    public void setOrigType( int type ) {
        origType = type;
    }

    /**
     * destination type is 1 if home, 2 if primary dest, 3 if intermediate stop, for home-based tours.
     * destination type is 1 if work, 2 if primary dest, 3 if intermediate stop, for work-based tours.
     */
    public void setDestType( int type ) {
        destType = type;
    }

    public void setOrigParkRate( float cost ) {
        origParkRate = cost;
    }

    public void setIntStopParkRate( float cost ) {
        intStopParkRate = cost;
    }

    public void setPrimDestParkRate( float cost ) {
        primDestParkRate = cost;
    }


    public int getFreeParking() {
        return person.getFreeParkingAvailableResult();
    }
    
    
    public int getOrigType() {
        return origType;
    }
    
    public int getDestType() {
        return destType;
    }
    
    public float getOrigParkRate() {
        return origParkRate;
    }
    
    public float getIntStopParkRate() {
        return intStopParkRate;
    }
    
    public float getPrimDestParkRate() {
        return primDestParkRate;
    }
    
    

    
    
    public IndexValues getDmuIndexValues() {
        return dmuIndex; 
    }
  

    public int getZonalShortWalkAccessOrig() {
        if ( stop.getOrigWalkSegment() == 1 )
            return 1;
        else
            return 0;
    }

    public int getZonalShortWalkAccessDest() {
        if ( stop.getDestWalkSegment() == 1 )
            return 1;
        else
            return 0;
    }

    public int getZonalLongWalkAccessOrig() {
        if ( stop.getOrigWalkSegment() == 2 )
            return 1;
        else
            return 0;
    }

    public int getZonalLongWalkAccessDest() {
        if ( stop.getDestWalkSegment() == 2 )
            return 1;
        else
            return 0;
    }

    
    public int getTourCategoryJoint() {
        if ( tour.getTourCategoryIsJointNonMandatory() )
            return 1;
        else
            return 0;
    }

    public int getTourCategorySubtour() {
        if ( tour.getTourCategoryIsAtWork() )
            return 1;
        else
            return 0;
    }
    
    public int getTourModeIsAuto() {
        boolean tourModeIsAuto = modelStructure.getTourModeIsSovOrHov( tour.getTourModeChoice() );
        return tourModeIsAuto ? 1 : 0;
    }

    public int getTourModeIsWalkTransit() {
        boolean tourModeIsWalkLocal = modelStructure.getTourModeIsWalkLocal( tour.getTourModeChoice() );
        boolean tourModeIsWalkPremium = modelStructure.getTourModeIsWalkPremium( tour.getTourModeChoice() );
        return tourModeIsWalkLocal || tourModeIsWalkPremium ? 1 : 0;
    }

    public int getTourModeIsDriveTransit() {
        boolean tourModeIsDriveTransit = modelStructure.getTourModeIsDriveTransit( tour.getTourModeChoice() );
        return tourModeIsDriveTransit ? 1 : 0;
    }

    public int getWorkTourModeIsSOV() {
        boolean workTourModeIsSov = modelStructure.getTourModeIsSov( tour.getTourModeChoice() );
        return workTourModeIsSov ? 1 : 0;
    }

    public int getWorkTourModeIsBike() {
        boolean tourModeIsBike = modelStructure.getTourModeIsBike( tour.getTourModeChoice() );
        return tourModeIsBike ? 1 : 0;
    }

    public int getTourModeIsSOV() {
        boolean tourModeIsSov = modelStructure.getTourModeIsSov( tour.getTourModeChoice() );
        return tourModeIsSov ? 1 : 0;
    }

    public int getTourModeIsBike() {
        boolean tourModeIsBike = modelStructure.getTourModeIsBike( tour.getTourModeChoice() );
        return tourModeIsBike ? 1 : 0;
    }

    public int getTourModeIsWalk() {
        boolean tourModeIsWalk = modelStructure.getTourModeIsWalk( tour.getTourModeChoice() );
        return tourModeIsWalk ? 1 : 0;
    }

    public int getTourMode() {
        return tour.getTourModeChoice();
    }

    public int getSubtourType() {
        return tour.getTourPurposeIndex();
    }

    
    public int getNumberOfParticipantsInJointTour() {
        return tour.getPersonNumArray().length;
    }

    
    
    public int getStopIsFirst() {
        return stopIsFirst;
    }
    
    public int getStopIsLast() {
        return stopIsLast;
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
