package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;


public class IndividualNonMandatoryTourFrequencyDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(IndividualNonMandatoryTourFrequencyDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    protected Household hh;
    protected Person person;
    protected IndexValues dmuIndex;

    protected int homeTazIsUrban;


    public IndividualNonMandatoryTourFrequencyDMU(){
    	dmuIndex = new IndexValues();
    }



    public Household getHouseholdObject() {
        return hh;
    }

    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }

    public void setPersonObject ( Person persObject ) {
        person = persObject;
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
            dmuIndex.setDebugLabel ( "Debug INMTF UEC" );
        }

    }


    public IndexValues getDmuIndexValues() {
        return dmuIndex;
    }


    /**
     * @return household income in dollars
     */
    public int getIncomeInDollars() {
        return hh.getIncomeInDollars();
    }


    /**
     * @return the number of persons in the "decision making" household.
     */
    public int getHouseholdSize() {
        // 1-based indexing, so the array is dimensioned 1 more than the number of persons.
        return hh.getPersons().length - 1;
    }


    public int getNumAutos() {
        return hh.getAutoOwnershipModelResult();
    }


    /**
     * @return 1 if household has at least 1 car, and the number of cars equals the number of workers
     */
    public int getCarsEqualsWorkers() {
        int numAutos = hh.getAutoOwnershipModelResult();
        int numWorkers = hh.getWorkers();

        // household must have at least 1 car, otherwise return 0.
        if ( numAutos > 0 ) {
            // if at least one car and numWorkers == numAutos, return 1, otherwise 0.
            if ( numAutos == numWorkers )
                return 1;
            else
                return 0;
        }
        else {
            return 0;
        }
    }


    /**
     * @return 1 if household has at least 1 car, and the number of cars equals the number of workers
     */
    public int getMoreCarsThanWorkers() {
        int numAutos = hh.getAutoOwnershipModelResult();
        int numWorkers = hh.getWorkers();

        if ( numAutos > numWorkers )
            return 1;
        else
            return 0;
    }


    public int getNumAdults() {
        int num = 0;
        Person[] persons = hh.getPersons();
        for ( int i=1; i < persons.length; i++ )
            num += persons[i].getPersonIsAdult();
        return num;
    }

    public int getNumChildren() {
        int num = 0;
        Person[] persons = hh.getPersons();
        for ( int i=1; i < persons.length; i++ )
            num += ( persons[i].getPersonIsAdult() == 0 ? 1 : 0 );
        return num;
    }

    public int getPersonIsAdult() {
        return person.getPersonIsAdult();
    }

    public int getPersonIsChild() {
        return person.getPersonIsAdult() == 0 ? 1 : 0;
    }

    public int getPersonIsFullTimeWorker() {
        return person.getPersonIsFullTimeWorker();
    }

    public int getPersonIsPartTimeWorker() {
        return person.getPersonIsPartTimeWorker();
    }

    public int getPersonIsUniversity() {
        return person.getPersonIsUniversityStudent();
    }

    public int getPersonIsNonworker() {
        return person.getPersonIsNonWorkingAdultUnder65() + person.getPersonIsNonWorkingAdultOver65();
    }

    public int getPersonIsPreschool() {
        return person.getPersonIsPreschoolChild();
    }

    public int getPersonIsStudentNonDriving() {
        return person.getPersonIsStudentNonDriving();
    }

    public int getPersonIsStudentDriving() {
        return person.getPersonIsStudentDriving();
    }

    public int getPersonStaysHome() {
        return person.getCdapActivity().equalsIgnoreCase("H") ? 1 : 0;
    }


    public int getFemale() {
        return person.getPersonIsFemale();
    }


    /**
     * determines the number of persons in the "decision making" household of type: full-time worker.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of full-time workers.
     */
    public int getFullTimeWorkers() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: full time worker; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsFullTimeWorker();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: part-time worker.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of part-time workers.
     */
    public int getPartTimeWorkers() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: part-time worker; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsPartTimeWorker();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: university student.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of university students.
     */
    public int getUniversityStudents() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: university student; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsUniversityStudent();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: non-worker.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of non-workers.
     */
    public int getNonWorkers() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: nonworker + retired; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsNonWorkingAdultUnder65() + p[i].getPersonIsNonWorkingAdultOver65();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: driving-age student.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of driving-age students.
     */
    public int getDrivingAgeStudents() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: driving-age student; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsStudentDriving();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: non-driving-age student.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of non-driving-age students.
     */
    public int getNonDrivingAgeStudents() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: non-driving-age student; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsStudentNonDriving();
            if ( count == 3 )
                break;
        }

        return count;
    }

    /**
     * determines the number of persons in the "decision making" household of type: pre-school age.
     * returns the count, or 3, if count is 3 or more.
     * @return count (up to a max of 3) of the number of pre-school age children.
     */
    public int getPreSchoolers() {
        Person[] p = hh.getPersons();

        // get the count of persons of type: pre-school; if more than 3, return 3.
        int count = 0;
        for (int i=1; i < p.length; i++) {
            count += p[i].getPersonIsPreschoolChild();
            if ( count == 3 )
                break;
        }

        return count;
    }


    /**
     * set the indicater value for whether the home zone is in an urban area or not.
     * this get's determined in the method that determines joint tour frequency and has access to a
     * zonal data object, and that code calls this method to set the value for use by the UEC.
     * @param urban home zone indicater value
     */
    public void setHomeTazIsUrban( int urban ){
        homeTazIsUrban = urban;
    }

    /**
     * called by methods invoked by UEC.solve()
     * @return 1 if residential zone is in urban area, 0 otherwise
     */
    public int getHomeTazIsUrban() {
        return homeTazIsUrban;
    }

    /**
     * called by methods invoked by UEC.solve()
     * @return maximum number of hours mutually available between pairs of adults in household
     */
    public int getMaxAdultOverlaps() {
        return hh.getMaxAdultOverlaps();
    }

    /**
     * called by methods invoked by UEC.solve()
     * @return maximum number of hours mutually available between pairs of children in household
     */
    public int getMaxChildOverlaps() {
        return hh.getMaxChildOverlaps();
    }

    /**
     * called by methods invoked by UEC.solve()
     * @return maximum number of hours mutually available between pairs or adults/children where pairs consist of different types in household
     */
    public int getMaxMixedOverlaps() {
        return hh.getMaxAdultChildOverlaps();
    }



    public int getMaxPairwiseOverlapAdult() {
        int maxOverlap = 0;

        // get array of person objects for the decision making household
        Person[] dmuPersons = hh.getPersons();

        for ( int i=1; i < dmuPersons.length; i++ ) {
            if ( dmuPersons[i].getPersonIsAdult() == 1 ) {
                int overlap = getOverlap( person, dmuPersons[i] );
                if ( overlap > maxOverlap )
                    maxOverlap = overlap;
            }
        }

        return maxOverlap;
    }


    public int getMaxPairwiseOverlapChild() {
        int maxOverlap = 0;

        // get array of person objects for the decision making household
        Person[] dmuPersons = hh.getPersons();

        for ( int i=1; i < dmuPersons.length; i++ ) {
            if ( dmuPersons[i].getPersonIsAdult() == 0 ) {
                int overlap = getOverlap( person, dmuPersons[i] );
                if ( overlap > maxOverlap )
                    maxOverlap = overlap;
            }
        }

        return maxOverlap;
    }


    //TODO: find out if this is suposed to be total pairwise available hours, or largest consecutive hours available for persons.
    //TODO: right now, assuming total pairwise available hours
    private int getOverlap ( Person dmuPerson, Person otherPerson ) {
        byte[] dmuWindow = dmuPerson.getTimeWindows();
        byte[] otherWindow = otherPerson.getTimeWindows();

        int overlap = 0;
        for ( int i=0; i < dmuWindow.length; i++ ){
            if ( dmuWindow[i] == 0 && otherWindow[i] == 0 )
                overlap++;
        }

        return overlap;
    }



    public int getWindowBeforeFirstMandJointTour() {
        return person.getWindowBeforeFirstMandJointTour();
    }

    public int getWindowBetweenFirstLastMandJointTour() {
        return person.getWindowBetweenFirstLastMandJointTour();
    }

    public int getWindowAfterLastMandJointTour() {
        return person.getWindowAfterLastMandJointTour();
    }

    
    
 
    public int getNumHhFtWorkers() {
        return hh.getNumFtWorkers();
    }

    public int getNumHhPtWorkers() {
        return hh.getNumPtWorkers();
    }

    public int getNumHhUnivStudents() {
        return hh.getNumUnivStudents();
    }

    public int getNumHhNonWorkAdults() {
        return hh.getNumNonWorkAdults();
    }

    public int getNumHhRetired() {
        return hh.getNumRetired();
    }

    public int getNumHhDrivingStudents() {
        return hh.getNumDrivingStudents();
    }

    public int getNumHhNonDrivingStudents() {
        return hh.getNumNonDrivingStudents();
    }

    public int getNumHhPreschool() {
        return hh.getNumPreschool();
    }


    public int getTravelActiveAdults () {
        return hh.getTravelActiveAdults();
    }

    public int getTravelActiveChildren () {
        return hh.getTravelActiveChildren();
    }

    public int getNumMandatoryTours() {
        return person.getNumMandatoryTours();    
    }

    public int getNumJointShoppingTours() {
        return person.getNumJointShoppingTours();
    }

    public int getNumJointOthMaintTours() {
        return person.getNumJointOthMaintTours();
    }

    public int getNumJointEatOutTours() {
        return person.getNumJointEatOutTours();
    }

    public int getNumJointSocialTours() {
        return person.getNumJointSocialTours();
    }

    public int getNumJointOthDiscrTours() {
        return person.getNumJointOthDiscrTours();
    }

    public int getJTours() {
        return hh.getJointTourArray().length;
    }



    public int getPreDrivingAtHome() {
        int num = 0;
        Person[] persons = hh.getPersons();
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getPersonIsStudentNonDriving() == 1 && persons[i].getCdapActivity().equalsIgnoreCase( CoordinatedDailyActivityPatternModel.HOME_PATTERN ) )
                num++;
        }
        return num;
    }

    public int getPreschoolAtHome() {
        int num = 0;
        Person[] persons = hh.getPersons();
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getPersonIsPreschoolChild() == 1 && persons[i].getCdapActivity().equalsIgnoreCase( CoordinatedDailyActivityPatternModel.HOME_PATTERN ) )
                num++;
        }
        return num;
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