package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

public class ModeChoiceDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(ModeChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    protected Tour tour;
    protected Tour workTour;
    protected Person person;
    protected Household hh;
    public IndexValues dmuIndex;

    // these attributes are used for accessibility logsum utility calculations where a tour object does not exist
    protected int origSubzone;
    protected int destSubzone;
    protected int origCounty;
    protected int origCordon;     // from TazData
    protected int origCordonCost; // from TazData
    protected double accessibilityValueOfTime;
    
    protected float origTaxiWaitTime;
    protected float destTaxiWaitTime;
    protected float origSingleTNCWaitTime;
    protected float destSingleTNCWaitTime;
    protected float origSharedTNCWaitTime;
    protected float destSharedTNCWaitTime;
    
    private ModelStructure modelStructure;
    
    public ModeChoiceDMU( ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
        dmuIndex = new IndexValues();
    }
    


    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }
    
    public Household getHouseholdObject() {
        return hh;
    }
    
    public void setPersonObject ( Person personObject ) {
        person = personObject;
    }
    
    public Person getPersonObject () {
        return person;
    }
    
    public void setTourObject ( Tour tourObject ) {
        tour = tourObject;
    }
    
    public void setWorkTourObject ( Tour tourObject ) {
        workTour = tourObject;
    }
    
    public Tour getTourObject () {
        return tour;
    }
    
    public Tour getWorkTourObject () {
        return workTour;
    }
    
    
    
    /**
     * Set this index values for this tour mode choice DMU object.
     * @param hhIndex is the DMU household index
     * @param origIndex is the DMU origin index
     * @param destIndex is the DMU desatination index
     */
    public void setDmuIndexValues( int hhIndex, int origIndex, int destIndex ) {
        dmuIndex.setHHIndex( hhIndex );
        dmuIndex.setZoneIndex( destIndex );
        dmuIndex.setOriginZone( origIndex );
        dmuIndex.setDestZone( destIndex );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( hh!= null && hh.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug MC UEC" );
        }

    }

    
    public IndexValues getDmuIndexValues() {
        return dmuIndex; 
    }
    
    public void setIndexOrig( int o ) {
        dmuIndex.setOriginZone( o );
    }

    public void setIndexDest( int d ) {
        dmuIndex.setDestZone( d );
    }

    public void setTourDestTaz( int d ) {
        tour.setTourDestTaz( d );
    }

    public void setTourDestWalkSubzone( int subzone ) {
        tour.setTourDestWalkSubzone( subzone );
    }

    public void setTourOrigTaz( int o ) {
        tour.setTourOrigTaz( o );
    }

    public void setTourOrigWalkSubzone( int subzone ) {
        tour.setTourOrigWalkSubzone( subzone );
    }

    public void setTourStartHour( int hour ) {
        tour.setTourStartHour ( hour );
    }

    public void setTourEndHour( int hour ) {
        tour.setTourEndHour( hour );
    }

    
    public int getWorkTourModeIsSOV() {
        boolean tourModeIsSov = modelStructure.getTourModeIsSov( workTour.getTourModeChoice() );
        return tourModeIsSov ? 1 : 0;
    }

    // guojy: added for ARC
    public int getWorkTourModeIsAuto() {
        boolean tourModeIsSov = modelStructure.getTourModeIsSovOrHov( workTour.getTourModeChoice() );
        return tourModeIsSov ? 1 : 0;
    }

    public int getWorkTourModeIsBike() {
        boolean tourModeIsBike = modelStructure.getTourModeIsBike( workTour.getTourModeChoice() );
        return tourModeIsBike ? 1 : 0;
    }


    public int getSubtourType() {
        return tour.getTourPurposeIndex();
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
    
    public int getTourPurposeEscort() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.getEscortPurposeName() ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeShopping() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.getShoppingPurposeName() ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeEatOut() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.getEatOutPurposeName() ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeSocial() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.getSocialPurposeName() ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeOthDiscr() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.getOthDiscrPurposeName() ) )
            return 1;
        else
            return 0;
    }

    
    public int getNumberOfParticipantsInJointTour() {
        byte[] participants = tour.getPersonNumArray();
        int returnValue = 0;
        if ( participants != null )
            returnValue = participants.length;
        return returnValue;
    }

    public int getAgeUnder40() {
        if ( person.getAge() < 40 )
            return 1;
        else
            return 0;
    }

    public int getAge40to59() {
        if ( person.getAge() >= 40 && person.getAge() < 60 )
            return 1;
        else
            return 0;
    }

    public int getAge60to79() {
        if ( person.getAge() >= 60 && person.getAge() < 79 )
            return 1;
        else
            return 0;
    }

    public int getAge60plus() {
        if ( person.getAge() >= 60 )
            return 1;
        else
            return 0;
    }
    
    public int getPersonIsWorker() {
        return person.getPersonIsWorker();
    }

    public int getPersonIsNonWorkingAdult() {
        if ( person.getPersonIsNonWorkingAdultUnder65() == 1 )
            return 1;
        else
            return 0;
    }

    public int getPersonIsMale() {
        if ( person.getPersonIsMale() == 1 )
            return 1;
        else
            return 0;
    }


    public int getPreDrivingChildInHh() {
        if ( hh.getNumChildrenUnder16() > 0 )
            return 1;
        else
            return 0;
    }

    public int getNumFemalesInHh() {
        int count = 0;
        Person[] persons = hh.getPersons();
        for (int i=1; i < persons.length; i++){
            if ( persons[i].getPersonIsFemale() == 1 )
                count++;
        }
        return count;
    }

    public int getTourDepartsAfter4pm() {
        if ( tour.getTourStartHour() >= 16 )
            return 1;
        else
            return 0;
    }

    public int getTourArrivesAfter7pm() {
        if ( tour.getTourEndHour() >= 19 )
            return 1;
        else
            return 0;
    }

    public int getFreeParking() {
        return person.getFreeParkingAvailableResult();
    }
    public int getHhSize() {
        return hh.getHhSize();
    }
    
    public int getAutos() {
        return hh.getAutoOwnershipModelResult();
    }

    public int getDrivers() {
        return hh.getDrivers();
    }

    public int getAge() {
        return person.getAge();
    }

    public int getHomemaker() {
        return person.getHomemaker();
    }

    public int getWorkers() {
        return hh.getWorkers();
    }

    public int getOutboundStops() {
        return tour.getNumOutboundStops();
    }

    public int getInboundStops() {
        return tour.getNumInboundStops();
    }

    public int getSize() {
        return hh.getSize();
    }

    public int getGender() {
        return person.getGender();
    }

    public int getChildunder16() {
        return hh.getChildunder16();
    }

    public int getChild16plus() {
        return hh.getChild16plus();
    }

    public int getHhIncomeInDollars(){
        return hh.getIncomeInDollars();
    }
    
    public short getHhIncomePctOfPoverty(){
        return hh.getIncomePercentOfPoverty();
    }
    
    
    /**
     * Method returns the value for the walk-transit access Subzone index associated with the origin alternative for which utility is being calculated.
     * This is used specifically in utility calculations for accessibility logsum values.
     * 
     * The attribute dcAltTaz must have been set prior to this get() being called by a UEC.
     * 
     * @return TAZ associated with a DC alternative
     */
    public int getOrigSubzone() {
        return origSubzone;
    }

    /**
     * Method returns the value for the walk-transit access Subzone index associated with the DC alternative for which utility is being calculated.
     * This is used specifically in utility calculations for accessibility logsum values.
     * 
     * The attribute dcAltSubzone must have been set prior to this get() being called by a UEC.
     * 
     * @return Subzone index associated with a DC alternative
     */
    public int getDestSubzone() {
        return destSubzone;
    }

    /**
     * Method sets the value for the walk-transit access Subzone index associated with the origin alternative for which utility is being calculated.
     * This is used specifically in utility calculations for accessibility logsum values.
     * 
     * This method sets the attribute dcAltTaz prior to any get() being called by a UEC.
     * 
     */
    public void setOrigSubzone( int subzone ) {
        origSubzone = subzone;
    }

    /**
     * Method sets the value for the walk-transit access Subzone index associated with the DC alternative for which utility is being calculated.
     * This is used specifically in utility calculations for accessibility logsum values.
     * 
     * This method sets the attribute dcAltTaz prior to any get() being called by a UEC.
     * 
     */
    public void setDestSubzone( int subzone ) {
        destSubzone = subzone;
    }

    public float getOrigCounty() {
        return origCounty;
    }

    public void setOrigCounty(int origCounty) {
        this.origCounty = origCounty;
    }

    public int getOrigCordon() {
        return origCordon;
    }

    public void setOrigCordon(int origCordon) {
        this.origCordon = origCordon;
    }

    public int getOrigCordonCost() {
        return origCordonCost;
    }

    public void setOrigCordonCost(int origCordonCost) {
        this.origCordonCost = origCordonCost;
    }
    
    public void setAccessibilityValueOfTime( double valueOfTime ) {
        accessibilityValueOfTime = valueOfTime;
    }

    public double getAccessibilityValueOfTime(){ 
        return accessibilityValueOfTime; 
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


	
    public int getUseOwnedAV(){
    	
    	if(tour==null)
    		return 0;
    	
    	return (tour.getUseOwnedAV() ? 1: 0);
    }



	public float getOrigTaxiWaitTime() {
		return origTaxiWaitTime;
	}



	public void setOrigTaxiWaitTime(float origTaxiWaitTime) {
		this.origTaxiWaitTime = origTaxiWaitTime;
	}



	public float getDestTaxiWaitTime() {
		return destTaxiWaitTime;
	}



	public void setDestTaxiWaitTime(float destTaxiWaitTime) {
		this.destTaxiWaitTime = destTaxiWaitTime;
	}



	public float getOrigSingleTNCWaitTime() {
		return origSingleTNCWaitTime;
	}



	public void setOrigSingleTNCWaitTime(float origSingleTNCWaitTime) {
		this.origSingleTNCWaitTime = origSingleTNCWaitTime;
	}



	public float getDestSingleTNCWaitTime() {
		return destSingleTNCWaitTime;
	}



	public void setDestSingleTNCWaitTime(float destSingleTNCWaitTime) {
		this.destSingleTNCWaitTime = destSingleTNCWaitTime;
	}



	public float getOrigSharedTNCWaitTime() {
		return origSharedTNCWaitTime;
	}



	public void setOrigSharedTNCWaitTime(float origSharedTNCWaitTime) {
		this.origSharedTNCWaitTime = origSharedTNCWaitTime;
	}



	public float getDestSharedTNCWaitTime() {
		return destSharedTNCWaitTime;
	}



	public void setDestSharedTNCWaitTime(float destSharedTNCWaitTime) {
		this.destSharedTNCWaitTime = destSharedTNCWaitTime;
	}

}
