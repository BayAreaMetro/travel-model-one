package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

import org.apache.log4j.Logger;

/**
 * This class is used for ...
 *
 * @author Christi Willison
 * @version Nov 4, 2008
 *          <p/>
 *          Created by IntelliJ IDEA.
 */
public class StopFrequencyDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(StopFrequencyDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    //guojy: remove the following if no longer needed
/*    // TODO: need to set/get these values from some generic structure object that was set by project specific code.
    private static final int START_AM_PEAK = 6;
    private static final int END_AM_PEAK = 9;
    private static final int START_PM_PEAK = 16;
    private static final int END_PM_PEAK = 19;
*/
    public static final int[] NUM_OB_STOPS_FOR_ALT = { -99999999, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3 };
    public static final int[] NUM_IB_STOPS_FOR_ALT = { -99999999, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3 };

    private ModelStructure modelStructure;


    protected IndexValues dmuIndex;
    protected Household household;
    protected Person person;
    protected Tour tour;

    private int originTazAreaType;
    private int destinationTazAreaType;
    private float[] pkTransitRetailAccessibility;
    private float[] opTransitRetailAccessibility;
    private float[] nonMotorRetailAccessibility;


    public StopFrequencyDMU( ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
    	dmuIndex = new IndexValues();
    }

    public void setDmuIndexValues( int hhid, int homeTaz, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhid );
        dmuIndex.setZoneIndex( homeTaz );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( household.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug SF UEC" );
        }

    }

    public void setHouseholdObject ( Household household) {
        this.household = household;
    }

    public void setPersonObject ( Person person ) {
        this.person = person;
    }

    public void setTourObject ( Tour tour ) {
        this.tour = tour;
    }

    public void setOriginTazAreaType( int at ) {
        originTazAreaType = at;
    }

    public void setDestTazAreaType( int at ) {
        destinationTazAreaType = at;
    }

    public void setZonalAccessibilities( float[] pkTransitRetailAccessibility, float[] opTransitRetailAccessibility, float[] nonMotorRetailAccessibility ) {
        this.pkTransitRetailAccessibility = pkTransitRetailAccessibility;
        this.opTransitRetailAccessibility = opTransitRetailAccessibility;
        this.nonMotorRetailAccessibility = nonMotorRetailAccessibility;
    }



    public IndexValues getDmuIndexValues(){
    	return dmuIndex;
    }

    public int getOriginAreaType() {
        return originTazAreaType;
    }

    public int getDestinationAreaType() {
        return destinationTazAreaType;
    }

    public int getIncomeInDollars() {
        return household.getIncomeInDollars();
    }

    public int getNumPersons() {
        return household.getHhSize();
    }

    public int getNumFullWork() {
        return household.getNumFtWorkers();
    }

    public int getNumStudent() {
        return household.getNumStudents();
    }

    public int getNumVeh() {
        return household.getAutoOwnershipModelResult();
    }

    public int getCarSuff() {
        int returnValue = 0;
        int numCars = household.getAutoOwnershipModelResult();
        int numWorkers = household.getNumFtWorkers() + household.getNumPtWorkers();
        if ( numCars >= numWorkers )
            returnValue = 1;
        return returnValue;
    }

    public int getNAge0to4() {
        return household.getNumPersons0to4();
    }

    public int getNAge5to15() {
        return household.getNumPersons5to15();
    }

    public int getNAdult() {
        // method getDrivers() returns the number of people 16+ in the household
        return household.getDrivers();
    }

    public int getGenderIsFemale() {
        return person.getPersonIsFemale();
    }

    public int getStartTime() {
        return tour.getTourStartHour();
    }

    public int getEndTime() {
        return tour.getTourEndHour();    
    }

    /**
     * count the number of subtours assoctiated with this work tour
     * @return
     */
    public int getNumAtWorkSubTours() {
        int numSubTours = 0;
        for ( Tour subTour : person.getListOfAtWorkSubtours() ) {
            int subtourWorkIndex = subTour.getWorkTourIndexFromSubtourId( subTour.getTourId() );
            
            // count this subtour if its work tour is the current tour
            if ( subtourWorkIndex == tour.getTourId() )
                numSubTours++;
        }
        return numSubTours;
    }

    public int getNumWorkTours() {
        return person.getNumWorkTours();
    }

    public int getNumUnivTours() {
        return person.getNumUniversityTours();
    }

    public int getNumSchoolTours() {
        return person.getNumSchoolTours();
    }

    public int getNumEscortTours() {
        return person.getNumIndividualEscortTours();
    }

    /**
     * @return number of total (individual and joint) shopping tours by household members
     */
    public int getNumHShopTours() {
        int numShopTours = 0;
        
        // add up total individual shopping tours
        Person[] persons = household.getPersons();
        for ( int i=1; i < persons.length; i++ )
            numShopTours += persons[i].getNumIndividualShoppingTours();
        
        // add in any joint shopping tours
        Tour[] jointTours = household.getJointTourArray();
        if ( jointTours != null ) {
            for ( Tour t : jointTours ) {
                if ( t.getTourPurpose().equalsIgnoreCase( ModelStructure.SHOPPING_PURPOSE_NAME ) )
                    numShopTours++;
            }
        }
        
        return numShopTours;
    }

    public int getNumShopTours() {
        return person.getNumIndividualShoppingTours();
    }

    /**
     * @return number of total (individual and joint) maintenance tours by household members
     */
    public int getNumHMaintTours() {
        int numMaintTours = 0;
        
        // add up total individual maintenance tours
        Person[] persons = household.getPersons();
        for ( int i=1; i < persons.length; i++ )
            numMaintTours += persons[i].getNumIndividualOthMaintTours();
        
        // add in any joint maintenance tours
        Tour[] jointTours = household.getJointTourArray();
        if ( jointTours != null ) {
            for ( Tour t : jointTours ) {
                if ( t.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_MAINT_PURPOSE_NAME ) )
                    numMaintTours++;
            }
        }
        
        return numMaintTours;
    }

    public int getNumMaintTours() {
        return person.getNumIndividualOthMaintTours();
    }

    public int getNumEatOutTours() {
        return person.getNumIndividualEatOutTours();
    }

    public int getNumVisitTours() {
        return person.getNumIndividualSocialTours();
    }

    public int getTourIsJoint() {
        return tour.getTourCategoryIsJointNonMandatory() ? 1 : 0;
    }
    
    public int getTourIsVisit() {
        return tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SOCIAL_PURPOSE_NAME ) ? 1 : 0;
    }
    
    public int getNumPersonsInJointTour() {
        int num = 0;
        if ( tour.getTourCategoryIsJointNonMandatory() )
            num = tour.getPersonNumArray().length;
        return num;
    }
    
    public int getJointTourHasAdultsOnly() {
        return tour.getJointTourComposition() == JointTourFrequencyModel.JOINT_TOUR_COMPOSITION_ADULTS ? 1 : 0; 
    }
    
    public int getTourModeIsTransit() {
        boolean tourModeIsTransit = modelStructure.getTourModeIsTransit( tour.getTourModeChoice() );
        return tourModeIsTransit ? 1 : 0;
    }

    public int getTourModeIsDriveTransit() {
        boolean tourModeIsDriveTransit = modelStructure.getTourModeIsDriveTransit( tour.getTourModeChoice() );
        return tourModeIsDriveTransit ? 1 : 0;
    }

    public int getTourModeIsSchoolBus() {
        boolean tourModeIsSchoolBus = modelStructure.getTourModeIsSchoolBus( tour.getTourModeChoice() );
        return tourModeIsSchoolBus ? 1 : 0;
    }

    public int getTourModeIsNonMotorized() {
        boolean tourModeIsNonMotorized = modelStructure.getTourModeIsNonMotorized( tour.getTourModeChoice() );
        return tourModeIsNonMotorized ? 1 : 0;
    }

    public double getAccesibilityAtDestination() {

        double returnValue = 0.0;
        int destinationTaz = dmuIndex.getOriginZone();

        if ( getTourModeIsTransit() == 1 )
            if ( tourStartsInPeakPeriod() )
                returnValue = pkTransitRetailAccessibility[destinationTaz];
            else
                returnValue = opTransitRetailAccessibility[destinationTaz];
        else if ( getTourModeIsNonMotorized() == 1 )
            returnValue = nonMotorRetailAccessibility[destinationTaz];

        return returnValue;
    }

    public double getAccesibilityAtOrigin() {

        double returnValue = 0.0;
        int originTaz = dmuIndex.getOriginZone();

        if ( getTourModeIsTransit() == 1 )
            if ( tourStartsInPeakPeriod() )
                returnValue = pkTransitRetailAccessibility[originTaz];
            else
                returnValue = opTransitRetailAccessibility[originTaz];
        else if ( getTourModeIsNonMotorized() == 1 )
            returnValue = nonMotorRetailAccessibility[originTaz];

        return returnValue;
    }


    // guojy: use project-level skim period definition
    private boolean tourStartsInPeakPeriod() {

    	int tourStartHour = tour.getTourStartHour();
        boolean returnValue = false;
        
        if ( ( modelStructure.getIsAmPeak(tourStartHour) == 1 ) || ( modelStructure.getIsPmPeak(tourStartHour) == 1 ) ) 
            returnValue = true;
        
        return returnValue;
    }



    public int getNumStopsAlt(int alt){
        int obStops = NUM_OB_STOPS_FOR_ALT[alt];
        int ibStops = NUM_IB_STOPS_FOR_ALT[alt];
        return obStops + ibStops;
    }


    public int getNumIbStopsAlt(int alt){
        return NUM_IB_STOPS_FOR_ALT[alt];
    }


    public int getNumObStopsAlt(int alt){
        return NUM_OB_STOPS_FOR_ALT[alt];
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
