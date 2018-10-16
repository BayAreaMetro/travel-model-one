package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.models.ctramp.jppf.CtrampApplication;
import com.pb.models.ctramp.jppf.HouseholdIndividualMandatoryTourFrequencyModel;


public class TourDepartureTimeAndDurationDMU implements Serializable, VariableTable {
	
	protected transient Logger logger = Logger.getLogger(TourDepartureTimeAndDurationDMU.class);

	private static int JOINT_TOUR_COMPOSITION_CHILDREN_ONLY = 2;
	
    protected HashMap<String, Integer> methodIndexMap;

    
    protected IndexValues dmuIndex;
    
    protected Person person;
    protected Household household;
    protected Tour tour;

    protected double[] modeChoiceLogsums;

    private int[] altStarts;
    private int[] altEnds;
    
    protected int originAreaType, destinationAreaType;

    protected int tourNumber;
    
    protected int firstTour;
    protected int subsequentTour;
    protected int endOfPreviousScheduledTour;
    
    
    protected ModelStructure modelStructure;
	
	public TourDepartureTimeAndDurationDMU( ModelStructure modelStructure ){
	    this.modelStructure = modelStructure;
		dmuIndex = new IndexValues();
	}
	
	public void setPerson(Person passedInPerson){
		person = passedInPerson;
	}
	
    public void setHousehold(Household passedInHousehold){
    	household = passedInHousehold;

    	// set the origin and zone indices
        dmuIndex.setZoneIndex(household.getHhTaz());
        dmuIndex.setHHIndex(household.getHhId());

        // set the debug flag that can be used in the UEC
        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( household.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug DepartTime UEC" );
        }

    }

	public void setTour(Tour passedInTour){
		tour = passedInTour;
	}
	
	public void setOriginZone(int zone){
		dmuIndex.setOriginZone(zone);
	}
	
	public void setDestinationZone(int zone){
		dmuIndex.setDestZone(zone);
	}
	
	public void setOriginAreaType(int areaType){
		originAreaType = areaType;
	}
	
	public void setDestinationAreaType(int areaType){
		destinationAreaType = areaType;
	}
	
    public void setFirstTour( int trueOrFalse ){
        firstTour = trueOrFalse;
    }

    public void setSubsequentTour( int trueOrFalse ){
        subsequentTour = trueOrFalse;
    }

    /**
     * Set the sequence number of this tour among all scheduled 
     * @param tourNum
     */
    public void setTourNumber( int tourNum ){
        tourNumber = tourNum;
    }

    public void setEndOfPreviousScheduledTour ( int endHr ){
        endOfPreviousScheduledTour = endHr;    
    }
    
    public void setModeChoiceLogsums( double[] logsums ) {
        modeChoiceLogsums = logsums;
    }

    public void setTodAlts( int[] altStarts, int[] altEnds ){
        this.altStarts = altStarts;
        this.altEnds = altEnds;
    }
    
    public IndexValues getIndexValues(){
		return(dmuIndex);
	}

    public Household getDmuHouseholdObject() {
        return household;
    }

    public int getOriginZone(){
		return(dmuIndex.getOriginZone());
	}
	
	public int getDestinationZone(){
		return(dmuIndex.getDestZone());
	}
	                                                         	
	public float getIncomeInThousands(){
		float incomeInDollars = (float) household.getIncomeInDollars();
		incomeInDollars /= 1000.0;
		return(incomeInDollars);
	}
	
    public int getOriginAreaType(){
    	return(originAreaType);
    }
    
    public int getDestinationAreaType(){
    	return(destinationAreaType);
    }
    
    public int getPersonIsAdult() {
        return person.getPersonIsAdult();
    }
    
    // for joint tours - if an adult is in the party, return 1.
    public int getAdultInTour() {
        return tour.getJointTourComposition() != JOINT_TOUR_COMPOSITION_CHILDREN_ONLY ? 1 : 0;
    }
    
    public int getNumChildrenInHh() {
        return household.getNumChildrenUnder19();
    }
    
    public int getFullTimeWorker(){
    	return(this.person.getPersonTypeIsFullTimeWorker());
    }
    
    public int getPartTimeWorker(){
    	return(this.person.getPersonTypeIsPartTimeWorker());
    }
    
    public int getUniversityStudent(){
    	return(this.person.getPersonIsUniversityStudent());
    }

    public int getStudentDrivingAge() {
        return(this.person.getPersonIsStudentDriving());
    }

    public int getStudentNonDrivingAge() {
        return(this.person.getPersonIsStudentNonDriving());
    }

    public int getNonWorker(){
    	return(this.person.getPersonIsNonWorkingAdultUnder65());
    }
    
    public int getRetired(){
    	return(this.person.getPersonIsNonWorkingAdultOver65());
    }

    public int getAllAdultsFullTimeWorkers() {
        Person[] p = household.getPersons();
        boolean allAdultsAreFullTimeWorkers = true;
        for (int i=1; i < p.length; i++) {
            if ( p[i].getPersonIsAdult() == 1 && p[i].getPersonIsFullTimeWorker() == 0 ) {
                allAdultsAreFullTimeWorkers = false;
                break;
            }
        }

        if ( allAdultsAreFullTimeWorkers )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeIsShopping() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.SHOPPING_PURPOSE_NAME ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeIsEatOut() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.EAT_OUT_PURPOSE_NAME ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeIsMaint() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.OTH_MAINT_PURPOSE_NAME ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeIsVisit() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.SOCIAL_PURPOSE_NAME ) )
            return 1;
        else
            return 0;
    }

    public int getTourPurposeIsDiscr() {
        if ( tour.getTourPurpose().equalsIgnoreCase( modelStructure.OTH_DISCR_PURPOSE_NAME ) )
            return 1;
        else
            return 0;
    }

    public int getSubtourPurposeIndex() {
        if ( tour.getTourCategoryIsAtWork() ) {
            return tour.getTourPurposeIndex();
        }
        else {
            return 0;
        }
    }

    public int getAdultsInTour() {

        int count = 0;
        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            Person[] persons = household.getPersons();

            byte[] personNums = tour.getPersonNumArray();
            for (int i=0; i < personNums.length; i++) {
                int p = personNums[i];
                if ( persons[p].getPersonIsAdult() == 1 )
                    count++;
            }
        }
        else if ( tour.getTourCategoryIsIndivNonMandatory() ) {
            if ( person.getPersonIsAdult() == 1 )
                count = 1;
        }

        return count;
    }

    public int getChildrenInTour() {

        int count = 0;
        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            Person[] persons = household.getPersons();

            byte[] personNums = tour.getPersonNumArray();
            for (int i=0; i < personNums.length; i++) {
                int p = personNums[i];
                if ( persons[p].getPersonIsAdult() == 0 )
                    count++;
            }
        }
        else if ( tour.getTourCategoryIsIndivNonMandatory() ) {
            if ( person.getPersonIsAdult() == 0 )
                count = 1;
        }

        return count;

    }

    // return 1 if at least one preschool or pre-driving child is in joint tour, otherwise 0.
    public int getPreschoolPredrivingInTour() {

        int count = 0;
        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            Person[] persons = household.getPersons();
            byte[] personNums = tour.getPersonNumArray();
            for (int i=0; i < personNums.length; i++) {
                int p = personNums[i];
                if ( persons[p].getPersonIsPreschoolChild() == 1 || persons[p].getPersonIsStudentNonDriving() == 1 )
                    return 1;
            }
        }
        else if ( tour.getTourCategoryIsIndivNonMandatory() ) {
            if ( person.getPersonIsPreschoolChild() == 1 || person.getPersonIsStudentNonDriving() == 1 )
                count = 1;
        }

        return count;

    }

    // return 1 if at least one university student is in joint tour, otherwise 0.
    public int getUnivInTour() {

        int count = 0;
        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            Person[] persons = household.getPersons();
            byte[] personNums = tour.getPersonNumArray();
            for (int i=0; i < personNums.length; i++) {
                int p = personNums[i];
                if ( persons[p].getPersonIsUniversityStudent() == 1 )
                    return 1;
            }
        }
        else if ( tour.getTourCategoryIsIndivNonMandatory() ) {
            if ( person.getPersonIsUniversityStudent() == 1 )
                count = 1;
        }

        return count;

    }

    // return 1 if all adults in joint tour are fulltime workers, 0 otherwise;
    public int getAllWorkFull() {

        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            int adultCount = 0;
            int ftWorkerAdultCount = 0;

            Person[] persons = household.getPersons();
            byte[] personNums = tour.getPersonNumArray();
            for (int i=0; i < personNums.length; i++) {
                int p = personNums[i];
                if ( persons[p].getPersonIsAdult() == 1 ) {
                    adultCount++;
                    if ( persons[p].getPersonIsFullTimeWorker() == 1 )
                        ftWorkerAdultCount++;
                }
            }

            if ( adultCount > 0 && adultCount == ftWorkerAdultCount )
                return 1;
            else
                return 0;
        }

        return 0;

    }

    public int getPartyComp() {
        if ( tour.getTourCategoryIsJointNonMandatory() ) {
            return tour.getJointTourComposition();
        }
        else {
            return 0;
        }
    }

    /**
     * @return number of individual non-mandatory tours, including escort, for the person
     */
    public int getPersonNonMandatoryTotalWithEscort() {
        return person.getListOfIndividualNonMandatoryTours().size();
    }

    /**
     * @return number of individual non-mandatory tours, excluding escort, for the person
     */
    public int getPersonNonMandatoryTotalNoEscort() {
        int count = 0;
        for ( Tour t : person.getListOfIndividualNonMandatoryTours() )
            if ( ! t.getTourPurpose().startsWith("escort") )
                count++;
        return count;
    }

    /**
     * @return number of individual non-mandatory tours, excluding escort, for the person
     */
    public int getPersonEscortTotal() {
        int count = 0;
        for ( Tour t : person.getListOfIndividualNonMandatoryTours() )
            if ( t.getTourPurpose().startsWith("escort") )
                count++;
        return count;
    }

    public int getHhJointTotal() {
        Tour[] jt = household.getJointTourArray();
        if ( jt == null)
            return 0;
        else
            return jt.length;
    }

    public int getPersonMandatoryTotal() {
        return person.getListOfWorkTours().size() + person.getListOfSchoolTours().size();
    }

    public int getPersonJointTotal() {
        Tour[] jtArray = household.getJointTourArray();
        if ( jtArray == null) {
            return 0;
        }
        else {
            int numJtParticipations = 0;
            for ( Tour jt : jtArray ) {
                byte[] personJtIndices = jt.getPersonNumArray();
                for ( int pNum : personJtIndices ) {
                    if ( pNum == person.getPersonNum() ) {
                        numJtParticipations++;
                        break;
                    }
                }
            }
            return numJtParticipations;
        }
    }

    public int getFirstTour(){
    	return firstTour;
    }
    
    public int getSubsequentTour(){
        return subsequentTour;
    }
    
    public int getNumberOfOutboundStops(){
    	return(tour.getNumOutboundStops());
    }
    
    public int getNumberOfInboundStops(){
    	return(tour.getNumInboundStops());
    }
    
    public int getWorkAndSchoolToursByWorker(){
        int returnValue = 0;
        if( person.getPersonIsWorker() == 1 ){
            if ( person.getImtfChoice() == HouseholdIndividualMandatoryTourFrequencyModel.CHOICE_WORK_AND_SCHOOL )
                returnValue = 1;
        }
    	return returnValue;
    }
    
    public int getWorkAndSchoolToursByStudent(){
        int returnValue = 0;
        if( person.getPersonIsStudent() == 1 ){
            if ( person.getImtfChoice() == HouseholdIndividualMandatoryTourFrequencyModel.CHOICE_WORK_AND_SCHOOL )
                returnValue = 1;
        }
    	return returnValue;
    }

    public double getModeChoiceLogsumAlt (int alt) {

        int startHour = altStarts[alt-1];
        int endHour = altEnds[alt-1];

        int index = modelStructure.getSkimPeriodCombinationIndex(startHour, endHour);
        
        return modeChoiceLogsums[index];
        
    }

    public int getPrevTourEndsThisDepartureHourAlt (int alt) {

        // get the departure hour for the current alternative
        int thisTourStartsHour = altStarts[alt-1];

        if ( person.isPreviousArrival( thisTourStartsHour ) )
            return 1;
        else
            return 0;

    }


    public int getPrevTourBeginsThisArrivalHourAlt (int alt) {

        // get the arrival hour for the current alternative
        int thisTourEndsHour = altStarts[alt-1];

        if ( person.isPreviousDeparture( thisTourEndsHour ) )
            return 1;
        else
            return 0;

    }


    public int getAdjWindowBeforeThisHourAlt(int alt){

        int thisTourStartsHour = altStarts[alt-1];

        int numAdjacentHoursAvailable = 0;
        for (int i=thisTourStartsHour-1; i >= CtrampApplication.START_HOUR; i--) {
            if ( person.isHourAvailable(i) )
                numAdjacentHoursAvailable++;
            else
                break;
        }

        return numAdjacentHoursAvailable;

    }

    public int getAdjWindowAfterThisHourAlt(int alt){

        int thisTourEndsHour = altEnds[alt-1];

        int numAdjacentHoursAvailable = 0;
        for (int i=thisTourEndsHour+1; i <= CtrampApplication.LAST_HOUR; i++) {
            if ( person.isHourAvailable(i) )
                numAdjacentHoursAvailable++;
            else
                break;
        }

        return numAdjacentHoursAvailable;

    }


    public int getRemainingHoursAvailableAlt( int alt ){

        int hoursAvail = person.getAvailableWindow();
        
        int start = altStarts[alt-1];
        int end = altEnds[alt-1];
            
        // determine the availabilty of each hour after the alternative time window is hypothetically scheduled
        // if start == end, the availability won't change, so no need to compute.
        if ( start != end ) {

            // the start and end hours will always be available after scheduling, so don't need to check them.
            // the hours between start/end must be 0 or the alternative could not have been available,
            // so count them all as unavailable after scheduling this window.
            hoursAvail -= ( end - start - 1 );

        }
                
        return hoursAvail;
        
    }


    public float getRemainingInmToursToAvailableHoursRatioAlt( int alt ){
        int hoursAvail = getRemainingHoursAvailableAlt( alt );
        if ( hoursAvail > 0 ) {
            float ratio = (float)( person.getListOfIndividualNonMandatoryTours().size() - tourNumber ) / hoursAvail;
            return ratio;
        }
        else
            return -999;
    }


    public int getEndOfPreviousTour() {
        return endOfPreviousScheduledTour;
    }


    public int getTourCategoryIsJoint() {
        return tour.getTourCategoryIsJointNonMandatory() ? 1 : 0;
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
