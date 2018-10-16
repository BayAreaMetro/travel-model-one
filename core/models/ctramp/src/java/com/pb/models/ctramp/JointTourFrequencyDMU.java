package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;


public class JointTourFrequencyDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(ModeChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    protected Household hh;
    protected Tour tour;
    protected IndexValues dmuIndex;
    private float walkRetailAccessibility = 0.0f;
    protected ModelStructure modelStructure;
    
    protected int homeTazIsUrban;
    protected int homeTazIsSuburban;

    public JointTourFrequencyDMU( ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
    	dmuIndex = new IndexValues();
    }



    public Household getHouseholdObject() {
        return hh;
    }

    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }

    public void setTourObject ( Tour tourObject ) {
        tour = tourObject;
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
            dmuIndex.setDebugLabel ( "Debug JTF UEC" );
        }

    }


    public IndexValues getDmuIndexValues() {
        return dmuIndex;
    }

    public void setIndexDest( int d ) {
        dmuIndex.setDestZone( d );
    }

    public int getStayHomePatternCountFullTime() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsFullTimeWorker() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getStayHomePatternCountPartTime() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsPartTimeWorker() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getStayHomePatternCountHomemaker() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsNonWorkingAdultUnder65() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getStayHomePatternCountRetiree() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsNonWorkingAdultOver65() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getStayHomePatternCountUnivDrivingStudent() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && (p.getPersonIsUniversityStudent() == 1 || p.getPersonIsStudentDriving() == 1))
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getStayHomePatternCountNonDrivingChild() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && (p.getPersonIsStudentNonDriving() == 1 || p.getPersonIsPreschoolChild() == 1))
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountFullTime() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsFullTimeWorker() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountPartTime() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsPartTimeWorker() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountHomemaker() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsNonWorkingAdultUnder65() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountRetiree() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsNonWorkingAdultOver65() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountUnivDrivingStudent() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && (p.getPersonIsUniversityStudent() == 1 || p.getPersonIsStudentDriving() == 1))
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getNonMandatoryPatternCountNonDrivingChild() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && (p.getPersonIsStudentNonDriving() == 1 || p.getPersonIsPreschoolChild() == 1))
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getMandatoryPatternCountFullTime() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsFullTimeWorker() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.MANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getMandatoryPatternCountDrivingStudent() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && p.getPersonIsStudentDriving() == 1)
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.MANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public int getMandatoryPatternCountNonDrivingChild() {
        int count = 0;
        for (Person p : hh.getPersons())
            if (p != null && (p.getPersonIsStudentNonDriving() == 1 || p.getPersonIsPreschoolChild() == 1))
                if (p.getCdapActivity().equalsIgnoreCase(CoordinatedDailyActivityPatternModel.MANDATORY_PATTERN))
                    count ++;
        return count;
    }

    public float getTimeWindowOverlapAdult() {
        return hh.getMaxAdultOverlaps();
    }

    public float getTimeWindowOverlapChild() {
        return hh.getMaxChildOverlaps();
    }

    public float getTimeWindowOverlapAdultChild() {
        return hh.getMaxAdultChildOverlaps();
    }

    public int getIncomeBetween50And100() {
        int income = hh.getIncomeInDollars();
        return (income > 50000 && income <= 100000) ? 1 : 0;
    }

    public int getIncomeGreaterThan100() {
        return hh.getIncomeInDollars() > 100000 ? 1 : 0;
    }

    public int getAutosInHH() {
        return hh.getAutoOwnershipModelResult();
    }

    public int getDriverCount() {
        return hh.getDrivers();
    }

    public int getWorkerCount() {
        return hh.getWorkers();
    }


    public void setWalkRetailAccessibility(float walkRetailAccessibility) {
        this.walkRetailAccessibility = walkRetailAccessibility;
    }

    public float getWalkRetailAccessibility() {
        return walkRetailAccessibility;
    }






    /**************original dmu methods************************/

    /**
     * @return the number of persons in the "decision making" household.
     */
    public int getHouseholdSize() {
        // 1-based indexing, so the array is dimensioned 1 more than the number of persons.
        return hh.getPersons().length - 1;
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
        Person p = tour.getPersonObject();
        return p.getPersonIsAdult();
    }

    public int getPersonIsChild() {
        Person p = tour.getPersonObject();
        return p.getPersonIsAdult() == 0 ? 1 : 0;
    }

    public int getPersonIsFullTimeWorker() {
        Person p = tour.getPersonObject();
        return p.getPersonIsFullTimeWorker();
    }

    public int getPersonIsPartTimeWorker() {
        Person p = tour.getPersonObject();
        return p.getPersonIsPartTimeWorker();
    }

    public int getPersonIsUniversity() {
        Person p = tour.getPersonObject();
        return p.getPersonIsUniversityStudent();
    }

    public int getPersonIsNonworker() {
        Person p = tour.getPersonObject();
        return p.getPersonIsNonWorkingAdultUnder65() + p.getPersonIsNonWorkingAdultOver65();
    }

    public int getPersonIsPreschool() {
        Person p = tour.getPersonObject();
        return p.getPersonIsPreschoolChild();
    }

    public int getPersonIsStudentNonDriving() {
        Person p = tour.getPersonObject();
        return p.getPersonIsStudentNonDriving();
    }

    public int getPersonIsStudentDriving() {
        Person p = tour.getPersonObject();
        return p.getPersonIsStudentDriving();
    }

    public int getPersonStaysHome() {
        Person p = tour.getPersonObject();
        return p.getCdapActivity().equalsIgnoreCase("H") ? 1 : 0;
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
     * set the indicater value for whether the home zone is in a suburban area or not.
     * this get's determined in the method that determines joint tour frequency and has access to a
     * zonal data object, and that code calls this method to set the value for use by the UEC.
     * @param suburban home zone indicater value
     */
    public void setHomeTazIsSuburban( int suburban ){
        homeTazIsSuburban = suburban;
    }

    /**
     * called by methods invoked by UEC.solve()
     * @return 1 if residential zone is in suburban area, 0 otherwise
     */
    public int getHomeTazIsSuburban() {
        return homeTazIsSuburban;
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
        return hh.getMaxAdultOverlaps();
    }


    public int getMaxPairwiseOverlapChild() {
        return hh.getMaxChildOverlaps();
    }


    public int getTravelActiveAdults () {
        return hh.getTravelActiveAdults();
    }

    public int getTravelActiveChildren () {
        return hh.getTravelActiveChildren();
    }

    public int getTourPurposeIsEat () {
        return tour.getTourPurpose().equalsIgnoreCase( modelStructure.EAT_OUT_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getTourPurposeIsDiscretionary () {
        return tour.getTourPurpose().equalsIgnoreCase( modelStructure.OTH_DISCR_PURPOSE_NAME ) ? 1 : 0;
    }

    public int getJointTourComposition() {
        return tour.getJointTourComposition();
    }

    public int getJointTourPurposeIndex() {
        return tour.getTourPurposeIndex();
    }

    public int getJTours() {
        return hh.getJointTourArray().length;
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
