package com.pb.models.ctramp;

import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;
import com.pb.models.ctramp.jppf.CtrampApplication;

public class Household implements java.io.Serializable {
    
    private boolean debugChoiceModels;
    
    private int hhId;
    private int hhIncomeInDollars;
    private byte hhSize;
    private byte hhType;
    private byte hhWorkers;

    private short homeTaz;
    private byte homeWalkSubzone;

    // note that this is a 1-based array
    private Person[] persons;

    private Tour[] jointTours;
    
    private byte aoModelAutos;
    private String cdapModelPattern;
    private byte imtfModelPattern;
    private String jtfModelPattern;
    
    private Random hhRandom;
    private short randomCount = 0;
    private short uwslRandomCount;
    private short aoRandomCount;
    private short fpRandomCount;
    private short cdapRandomCount;
    private short imtfRandomCount;
    private short imtodRandomCount;
    private short immcRandomCount; 
    private short awfRandomCount;
    private short awlRandomCount;
    private short awtodRandomCount;
    private short awmcRandomCount; 
    private short jtfRandomCount;
    private short jtlRandomCount;
    private short jtodRandomCount;
    private short jmcRandomCount; 
    private short inmtfRandomCount;
    private short inmtlRandomCount;
    private short inmtodRandomCount;
    private short inmmcRandomCount; 
    private short stfRandomCount;
    private short stlRandomCount;


    private byte maxAdultOverlaps;
    private byte maxChildOverlaps;
    private byte maxAdultChildOverlaps;
    private byte maxHoursAvailableAdult;
    private byte maxHoursAvailableChild;
    

    // guojy: added for M. Gucwa's research on automated vehicles
    private int hAnalyst; 
    
    public Household() {
        hhRandom = new Random();
     }
    
    
    /**
     * 
     * @return a 1-based array of the person objects in the household
     */
    public Person[] getPersons() {
        return persons;
    }
    
    
    
    /**
	 * @param persons the persons to set
	 */
	public void setPersons(Person[] persons) {
		this.persons = persons;
	}


	public void initializeWindows(){
    	
    	// loop through the person array (1-based)
    	for(int i=1;i<persons.length;++i){
    		persons[i].initializeWindows();
    	}
    	
    }
    
    public void setDebugChoiceModels ( boolean value ) {
        debugChoiceModels = value;
    }
    
    public void setHhId( int id, int baseSeed ) {
        hhId = id;
        randomCount = 0;
        hhRandom.setSeed( baseSeed + hhId );
    }

    public void setRandomObject ( Random r ) {
        hhRandom = r;
    }

    public void setHhRandomCount( int count ) {
        randomCount = (short)count;
    }

    public void setUwslRandomCount( int count ) {
        uwslRandomCount = (short) count ;
    }

    public void setAoRandomCount( int count ) {
        aoRandomCount = (short)count;
    }

    public void setFpRandomCount( int count ) {
        fpRandomCount = (short)count;
    }

    public void setCdapRandomCount( int count ) {
        cdapRandomCount = (short)count;
    }

    public void setImtfRandomCount( int count ) {
        imtfRandomCount = (short)count;
    }

    public void setImtodRandomCount( int count ) {
        imtodRandomCount = (short)count;
    }

    public void setImmcRandomCount( int count ) {
        immcRandomCount = (short)count;
    }
    
    public void setAwfRandomCount( int count ) {
        awfRandomCount = (short)count;
    }

    public void setAwlRandomCount( int count ) {
        awlRandomCount = (short)count;
    }

    public void setAwtodRandomCount( int count ) {
        awtodRandomCount = (short)count;
    }

    public void setAwmcRandomCount( int count ) {
        awmcRandomCount = (short)count;
    }
    
    public void setJtfRandomCount( int count ) {
        jtfRandomCount = (short)count;
    }

    public void setJtlRandomCount( int count ) {
        jtlRandomCount = (short)count;
    }

    public void setJtodRandomCount( int count ) {
        jtodRandomCount = (short)count;
    }
    
    public void setJmcRandomCount( int count ) {
        jmcRandomCount = (short)count;
    }

    public void setInmtfRandomCount( int count ) {
        inmtfRandomCount = (short)count;
    }

    public void setInmtlRandomCount( int count ) {
        inmtlRandomCount = (short)count;
    }

    public void setInmtodRandomCount( int count ) {
        inmtodRandomCount = (short)count;
    }

    public void setInmmcRandomCount( int count ) {
        inmmcRandomCount = (short)count;
    }
    
    public void setStfRandomCount( int count ) {
        stfRandomCount = (short)count;
    }

    public void setStlRandomCount( int count ) {
        stlRandomCount = (short)count;
    }

    public void setHhTaz( short taz ) {
        homeTaz = taz;
    }
    
    public void setHhWalkSubzone( int subzone ) {
        homeWalkSubzone = (byte)subzone;
    }
    
    public void setHhAutos( int autos ) {
        // this sets the variable that will be used in work/school location choice.
        // after auto ownership runs, this variable gets updated with number of autos for result.
        aoModelAutos = (byte)autos;   
    }
    
    public void setAutoOwnershipModelResult( int aoModelAlternativeChosen ) {
        // store the number of autos owned by the household (AO model alternative - 1).
        aoModelAutos = (byte)(aoModelAlternativeChosen - 1);
    }

    public int getAutoOwnershipModelResult() {
        return aoModelAutos;
    }
    
    public void setCoordinatedDailyActivityPatternResult(String pattern){
    	cdapModelPattern = pattern;
    }

    public String getCoordinatedDailyActivityPattern(){
    	return cdapModelPattern;
    }

    public void setJointTourFreqResult( int altIndex, String altName ) {
        jtfModelPattern = String.format( "%d_%s", altIndex, altName );
    }

    public int getJointTourFreqChosenAlt() {
        int returnValue = 0;
        if ( jtfModelPattern == null ) {
            returnValue = 1;
        }
        else {
            int endIndex = jtfModelPattern.indexOf('_');
            returnValue = Integer.parseInt( jtfModelPattern.substring( 0, endIndex ) );
        }
        return returnValue;
    }

    public String getJointTourFreqChosenAltName() {
        String returnValue = "none";
        if ( jtfModelPattern != null ) {
            int startIndex = jtfModelPattern.indexOf('_') + 1;
            returnValue = jtfModelPattern.substring( startIndex );
        }
        return returnValue;
    }



    public void setHhSize( int numPersons ) {
        hhSize = (byte)numPersons;
        persons = new Person[numPersons+1];
        for (int i=1; i <= numPersons; i++)
            persons[i] = new Person( this, i );
        
    }
    
    private int numberOfPersonsSet;
    
    public int getNumberOfPersonsSet(){
    	return numberOfPersonsSet;
    }
    
    /**
     * Set a person in the persons array for the household.  THe method 
     * automatically tracks the number of persons already set and sets the 
     * appropriate element of the person array accordingly.  If the person
     * array isn't big enough, it is updated and the household size is reset.
     * 
     * @param person
     */
    public void setPerson(Person person){
    	
    	//household size not big enough - create new person array
    	if(numberOfPersonsSet==persons.length){
    		Person[] newPersons = new Person[persons.length+1];
    		for(int i = 1; i < persons.length;++i)
    			newPersons[i] = persons[i];
    		newPersons[newPersons.length-1]=person;
    		++hhSize;
    	}else{
    		persons[numberOfPersonsSet+1] = person;
    	}
    	++numberOfPersonsSet;
    }
        
    public void setHhIncomeInDollars (int dollars){
    	hhIncomeInDollars = dollars;
    }
    
    public void setHhWorkers( int numWorkers ) {
        hhWorkers = (byte)numWorkers;
    }
    
    public void setHhType (int type ) {
    	hhType = (byte)type;
    }

    
    
    public boolean getDebugChoiceModels () {
        return debugChoiceModels;
    }
    
    public int getHhSize() {
        return hhSize;
    }

    public int getNumberOfNonWorkingAdults(){
    	int count = 0;
    	for( int i=1; i < persons.length; i++ )
    		count += persons[i].getPersonIsNonWorkingAdultUnder65() + persons[i].getPersonIsNonWorkingAdultOver65();
    	return count;
    }
    
    public int getIsNonFamilyHousehold(){
    	
    	if(hhType==HouseholdType.NON_FAMILY_MALE_ALONE.ordinal())       return (1);
    	if(hhType==HouseholdType.NON_FAMILY_MALE_NOT_ALONE.ordinal())   return (1);
    	if(hhType==HouseholdType.NON_FAMILY_FEMALE_ALONE.ordinal())     return (1);
    	if(hhType==HouseholdType.NON_FAMILY_FEMALE_NOT_ALONE.ordinal()) return (1);
    	
    	return(0);
    }
    
    public int getNumStudents(){
    	int count = 0;
    	for(int i=1;i<persons.length;++i){
    		count += persons[i].getPersonIsStudent();
    	}
    	return(count);
    }

    public int getNumberOfChildrenUnder16WithHomeOrNonMandatoryActivity(){

    	int count = 0;

    	for(int i=1;i<persons.length;++i){
    		count += persons[i].getPersonIsChildUnder16WithHomeOrNonMandatoryActivity();
    	}

    	return(count);
    }



    /**
     * return the number of workers this household has for the purpose index.
     * @param purposeIndex is the DC purpose index to be compared to the usual school location index saved for this
     * person upon reading synthetic population file.
     * @return num, a value of the number of workers in the household for this purpose index.
     */
    public int getNumberOfWorkersWithDcPurposeIndex ( int purposeIndex ) {
        int num = 0;
        for (int j=1; j < persons.length; j++) {
            if ( persons[j].getPersonIsWorker() == 1 && persons[j].getWorkLocationPurposeIndex() == purposeIndex )
                num++;
        }
        return num;
    }

    /**
     * return the number of university students this household has for the purpose index.
     * @param purposeIndex is the DC purpose index to be compared to the usual school location index saved for this
     * person upon reading synthetic population file.
     * @return num, a value of the number of university students in the household for this purpose index.
     */
    public int getNumberOfUniversityStudentsWithDcPurposeIndex ( int purposeIndex ) {
        int num = 0;
        for (int j=1; j < persons.length; j++) {
            if ( persons[j].getPersonIsUniversityStudent() == 1 && persons[j].getUniversityLocationPurposeIndex() == purposeIndex )
                num++;
        }
        return num;
    }

    /**
     * return the number of school age students this household has for the purpose index.
     * @param purposeIndex is the DC purpose index to be compared to the usual school location index saved for this
     * person upon reading synthetic population file.
     * @return num, a value of the number of school age students in the household for this purpose index.
     */
    public int getNumberOfDrivingAgedStudentsWithDcPurposeIndex ( int purposeIndex ) {
        int num = 0;
        for (int j=1; j < persons.length; j++) {
            if ( persons[j].getPersonIsStudentDriving() == 1 && persons[j].getSchoolLocationPurposeIndex() == purposeIndex )
                num++;
        }
        return num;
    }
    public int getNumberOfNonDrivingAgedStudentsWithDcPurposeIndex ( int purposeIndex ) {
        int num = 0;
        for (int j=1; j < persons.length; j++) {
            if ( persons[j].getPersonIsStudentNonDriving() == 1 || persons[j].getPersonIsPreschoolChild() == 1 && persons[j].getSchoolLocationPurposeIndex() == purposeIndex )
                num++;
        }
        return num;
    }



    public Person getPerson ( int persNum ) {
        if ( persNum < 1 || persNum > hhSize ) {
            throw new RuntimeException( String.format("persNum value = %d is out of range for hhSize = %d", persNum, hhSize) );
        }
        
        return persons[persNum];
    }
    
    
    
    // methods DMU will use to get info from household object
    
    public int getHhId() {
        return hhId;
    }
    
    public Random getHhRandom() {
        randomCount++;
        return hhRandom;
    }

    public int getHhRandomCount() {
        return randomCount;
    }

    public int getUwslRandomCount() {
        return uwslRandomCount;
    }

    public int getAoRandomCount() {
        return aoRandomCount;
    }

    public int getFpRandomCount() {
        return fpRandomCount;
    }

    public int getCdapRandomCount() {
        return cdapRandomCount;
    }

    public int getImtfRandomCount() {
        return imtfRandomCount;
    }

    public int getImtodRandomCount() {
        return imtodRandomCount;
    }

    public int getImmcRandomCount() {
        return immcRandomCount;
    }
    
    public int getJtfRandomCount() {
        return jtfRandomCount;
    }

    public int getAwfRandomCount() {
        return awfRandomCount;
    }

    public int getAwlRandomCount() {
        return awlRandomCount;
    }

    public int getAwtodRandomCount() {
        return awtodRandomCount;
    }

    public int getAwmcRandomCount() {
        return awmcRandomCount;
    }
    
    public int getJtlRandomCount() {
        return jtlRandomCount;
    }

    public int getJtodRandomCount() {
        return jtodRandomCount;
    }

    public int getJmcRandomCount() {
        return jmcRandomCount;
    }
    
    public int getInmtfRandomCount() {
        return inmtfRandomCount;
    }

    public int getInmtlRandomCount() {
        return inmtlRandomCount;
    }

    public int getInmtodRandomCount() {
        return inmtodRandomCount;
    }

    public int getInmmcRandomCount() {
        return inmmcRandomCount;
    }
    
    public int getStfRandomCount() {
        return stfRandomCount;
    }

    public int getStlRandomCount() {
        return stlRandomCount;
    }

    public int getHhTaz() {
        return homeTaz;
    }
    
    public int getHhWalkSubzone() {
        return homeWalkSubzone;
    }
    

    //TODO suggest getting rid of hhIncome groupings, or moving them down to the project level.
    //these vary for different regions, and it can be a source of error to use it here. 
    //the values here are for ARC only. 
    // guojy: this function is not used for ARC anymore
    public int getIncomeSegment() {
    	int[] ARC_INCOME_SEGMENT_DOLLAR_LIMITS = {20000, 50000, 100000, Integer.MAX_VALUE}; 

    	for (int i=0; i<ARC_INCOME_SEGMENT_DOLLAR_LIMITS.length; i++) {
    		if (hhIncomeInDollars<ARC_INCOME_SEGMENT_DOLLAR_LIMITS[i]) {
    			return i+1; 
    		}
    	}
    	throw new RuntimeException("Invalid income segments defined in Household"); 
    }
    
    public int getIncomeInDollars() {
    	return hhIncomeInDollars;
    }
    
    public int getWorkers() {
        return hhWorkers;
    }

    public int getDrivers() {
        return getNumPersons16plus();
    }

    public int getSize() {
        return hhSize;
    }
   
    public int getChildunder16() {
        if ( getNumChildrenUnder16() > 0 )
            return 1;
        else
            return 0;
    }
    
    public int getChild16plus() {
        if ( getNumPersons16plus() > 0 )
            return 1;
        else
            return 0;
    }

    public int getNumChildrenUnder16() {
        int numChildrenUnder16 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() < 16 )
                numChildrenUnder16 ++;
        }
        return numChildrenUnder16;
    }

    public int getNumChildrenUnder19() {
        int numChildrenUnder19 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() < 19 )
                numChildrenUnder19 ++;
        }
        return numChildrenUnder19;
    }

    public int getNumPersons0to4() {
        int numPersons0to4 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() < 5 )
                numPersons0to4 ++;
        }
        return numPersons0to4;
    }

    public int getNumPersons5to15() {
        int numPersons5to15 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() >= 5 && persons[i].getAge() <= 15 )
                numPersons5to15 ++;
        }
        return numPersons5to15;
    }

    public int getNumPersons16to17() {
        int numPersons16to17 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() >= 16 && persons[i].getAge() <= 17 )
                numPersons16to17 ++;
        }
        return numPersons16to17;
    }

    public int getNumPersons16plus() {
        int numPersons16plus = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() >= 16 )
                numPersons16plus ++;
        }
        return numPersons16plus;
    }

    public int getNumPersons18to24() {
        int numPersons18to24 = 0;
        for (int i=1; i < persons.length; i++) {
            if ( persons[i].getAge() >= 18 && persons[i].getAge() <= 24 )
                numPersons18to24 ++;
        }
        return numPersons18to24;
    }


    public int getNumFtWorkers() {
        int numFtWorkers = 0;
        for (int i=1; i < persons.length; i++)
            numFtWorkers += persons[i].getPersonIsFullTimeWorker();
        return numFtWorkers;
    }

    public int getNumPtWorkers() {
        int numPtWorkers = 0;
        for (int i=1; i < persons.length; i++)
            numPtWorkers += persons[i].getPersonIsPartTimeWorker();
        return numPtWorkers;
    }

    public int getNumUnivStudents() {
        int numUnivStudents = 0;
        for (int i=1; i < persons.length; i++)
            numUnivStudents += persons[i].getPersonIsUniversityStudent();
        return numUnivStudents;
    }

    public int getNumNonWorkAdults() {
        int numNonWorkAdults = 0;
        for (int i=1; i < persons.length; i++)
            numNonWorkAdults += persons[i].getPersonIsNonWorkingAdultUnder65();
        return numNonWorkAdults;
    }

    public int getNumRetired() {
        int numRetired = 0;
        for (int i=1; i < persons.length; i++)
            numRetired += persons[i].getPersonIsNonWorkingAdultOver65();
        return numRetired;
    }

    public int getNumDrivingStudents() {
        int numDrivingStudents = 0;
        for (int i=1; i < persons.length; i++)
            numDrivingStudents += persons[i].getPersonIsStudentDriving();
        return numDrivingStudents;
    }

    public int getNumNonDrivingStudents() {
        int numNonDrivingStudents = 0;
        for (int i=1; i < persons.length; i++)
            numNonDrivingStudents += persons[i].getPersonIsStudentNonDriving();
        return numNonDrivingStudents;
    }

    public int getNumPreschool() {
        int numPreschool = 0;
    for (int i=1; i < persons.length; i++)
        numPreschool += persons[i].getPersonIsPreschoolChild();
    return numPreschool;
}




    /**
     * joint tour frequency choice is not applied to a household unless it has:
     * 2 or more persons, each with at least one out-of home activity, and at least 1 of the persons not a pre-schooler.
     * */
    public int getValidHouseholdForJointTourFrequencyModel() {

        // return one of the following condition codes for this household producing joint tours:
        //  1: household eligible for joint tour production
        //  2: household ineligible due to 1 person hh.
        //  3: household ineligible due to fewer than 2 persons traveling out of home
        //  4: household ineligible due to fewer than 1 non-preschool person traveling out of home

        // no joint tours for single person household
        if ( hhSize == 1 )
            return 2;

        int leavesHome = 0;
        int nonPreSchoolerLeavesHome = 0;
        for ( int i=1; i < persons.length; i++ ) {
            if ( ! persons[i].getCdapActivity().equalsIgnoreCase("H") ) {
                leavesHome++;
                if ( persons[i].getPersonIsPreschoolChild() == 0 )
                    nonPreSchoolerLeavesHome++;
            }
        }

        // if the number of persons leaving home during the day is not at least 2, no joint tours
        if ( leavesHome < 2 )
            return 3;

        // if the number of non-preschool persons leaving home during the day is not at least 1, no joint tours
        if ( nonPreSchoolerLeavesHome < 1 )
            return 4;

        // if all conditions are met, we can apply joint tour frequency model to this household
        return 1;

    }

    /**
     * return maximum hours of overlap between this person and other adult persons in the household.
     * @return the most number of hours mutually available between this person and other adult household members
     */
    public int getMaxAdultOverlaps () {
        return maxAdultOverlaps;
    }


    /**
     * set maximum hours of overlap between this person and other adult persons in the household.
     * @param overlaps are the most number of hours mutually available between this person and other adult household members
     */
    public void setMaxAdultOverlaps (int overlaps) {
        maxAdultOverlaps = (byte)overlaps;
    }


    /**
     * return maximum hours of overlap between this person and other children in the household.
     * @return the most number of hours mutually available between this person and other child household members
     */
    public int getMaxChildOverlaps () {
        return maxChildOverlaps;
    }


    /**
     * set maximum hours of overlap between this person and other children in the household.
     * @param overlaps are the most number of hours mutually available between this person and other child household members
     */
    public void setMaxChildOverlaps (int overlaps) {
        maxChildOverlaps = (byte)overlaps;
    }


    /**
     * return maximum hours of overlap between this person(adult/child) and other persons(child/adult) in the household.
     * @return the most number of hours mutually available between this person and other type household members
     */
    public int getMaxAdultChildOverlaps () {
        return maxAdultChildOverlaps;
    }


    /**
     * set maximum hours of overlap between this person(adult/child) and other persons(child/adult) in the household.
     * @param overlaps are the most number of hours mutually available between this person and other type household members
     */
    public void setMaxAdultChildOverlaps (int overlaps) {
        maxAdultChildOverlaps = (byte)overlaps;
    }


    /**
     * return maximum available time window over all adults in the household.
     * @return the total number of hours available in the maximum window over adults in this household
     */
    public int getMaxAdultWindow () {
        return maxHoursAvailableAdult;
    }


    /**
     * set maximum available time window over all adults in the household.
     * @param availWindow is the total number of hours available in the maximum window over adults in this household.
     */
    public void setMaxAdultWindow (int availWindow) {
        maxHoursAvailableAdult = (byte)availWindow;
    }

    
    /**
     * return maximum available time window over all children in the household.
     * @return the total number of hours available in the maximum window over children in this household
     */
    public int getMaxChildWindow () {
        return maxHoursAvailableChild;
    }


    /**
     * set maximum available time window over all children in the household.
     * @param availWindow is the total number of hours available in the maximum window over children in this household.
     */
    public void setMaxChildWindow (int availWindow) {
        maxHoursAvailableChild = (byte)availWindow;
    }


    /**
     * @return number of adults in household with "M" or "N" activity pattern - that is, traveling adults.
     */
    public int getTravelActiveAdults () {

        int adultsStayingHome = 0;
        int adults = 0;
        for ( int p=1; p < persons.length; p++ ) {
             // person is an adult
            if ( persons[p].getPersonIsAdult() == 1 ) {
                adults++;
                if ( persons[p].getCdapActivity().equalsIgnoreCase("H") )
                    adultsStayingHome++;
            }
        }

        // return the number of adults traveling = number of adults minus the number of adults staying home.
        return adults - adultsStayingHome;

    }


    /**
     * @return number of children in household with "M" or "N" activity pattern - that is, traveling children.
     */
    public int getTravelActiveChildren () {

        int childrenStayingHome = 0;
        int children = 0;
        for ( int p=1; p < persons.length; p++ ) {
             // person is not an adult
            if ( persons[p].getPersonIsAdult() == 0 ) {
                children++;
                if ( persons[p].getCdapActivity().equalsIgnoreCase("H") )
                    childrenStayingHome++;
            }
        }

        // return the number of adults traveling = number of adults minus the number of adults staying home.
        return children - childrenStayingHome;

    }


    public void updateTimeWindows () {

        boolean pAdult;
        boolean qAdult;

        short numHoursAvailable = 0;

        short maxAdultOverlapsHH = 0;
        short maxChildOverlapsHH = 0;
        short maxMixedOverlapsHH = 0;

        short maxAdultHoursAvailHH = 0;
        short maxChildHoursAvailHH = 0;

        short[] maxAdultOverlapsP = new short[persons.length];
        short[] maxChildOverlapsP = new short[persons.length];


        // loop over persons in the household and count available time windows
        for (int p=1; p < persons.length; p++) {

            // determine if person p is an adult -- that is, person is not any of the three child types
            pAdult =  persons[p].getPersonIsPreschoolChild() == 0 && persons[p].getPersonIsStudentNonDriving() == 0 && persons[p].getPersonIsStudentDriving() == 0;


            // loop over time windows between CtrampApplication.START_HOUR & CtrampApplication.LAST_HOUR (hours in which to count avaiable hours)
            // and count instances where the hour is available for person p.
            numHoursAvailable = 0;
            for (int w=CtrampApplication.START_HOUR; w <= CtrampApplication.LAST_HOUR; w++) {
                if ( persons[p].isHourAvailable( w ) )
                    numHoursAvailable++;
            }

            if (pAdult && numHoursAvailable > maxAdultHoursAvailHH)
                maxAdultHoursAvailHH = numHoursAvailable;
            else if (!pAdult && numHoursAvailable > maxChildHoursAvailHH)
                maxChildHoursAvailHH = numHoursAvailable;


            // loop over person indices greater than p and compute available time window overlaps.
            // Don't need q,p if we've already done p,q,
            // so we only need triangular part of matrix above diagonal.
            for (int q=1; q < persons.length; q++) {
                
                if ( p == q )
                    continue;

                // determine if person q is an adult -- that is, person is not any of the three child types
                qAdult =  persons[q].getPersonIsPreschoolChild() == 0 && persons[q].getPersonIsStudentNonDriving() == 0 && persons[q].getPersonIsStudentDriving() == 0;


                // loop over time windows between CtrampApplication.START_HOUR & CtrampApplication.LAST_HOUR (hours in which to start a joint tour)
                // and count instances where the hour is available for both persons
                short overlaps = 0;
                for (int w=CtrampApplication.START_HOUR; w <= CtrampApplication.LAST_HOUR; w++) {
                    if ( persons[p].isHourAvailable( w ) && persons[q].isHourAvailable( w ) )
                        overlaps++;
                }


                // determine max time window overlap between pairs of adults,
                // pairs of children, and pairs of 1 adult 1 child
                if (pAdult && qAdult) {
                    if (overlaps > maxAdultOverlapsHH)
                        maxAdultOverlapsHH = overlaps;
                    if (overlaps > maxAdultOverlapsP[p])
                        maxAdultOverlapsP[p] = overlaps;
                }
                else if (!pAdult && !qAdult) {
                    if (overlaps > maxChildOverlapsHH)
                        maxChildOverlapsHH = overlaps;
                    if (overlaps > maxChildOverlapsP[p])
                        maxChildOverlapsP[p] = overlaps;
                }
                else {
                    if (overlaps > maxMixedOverlapsHH)
                        maxMixedOverlapsHH = overlaps;
                }

            } // end of person q

            // set person attributes
            persons[p].setMaxAdultOverlaps( maxAdultOverlapsP[p] );
            persons[p].setMaxChildOverlaps( maxChildOverlapsP[p] );


        } // end of person p

        // set household attributes
        setMaxAdultOverlaps( maxAdultOverlapsHH );
        setMaxChildOverlaps( maxChildOverlapsHH );
        setMaxAdultChildOverlaps( maxMixedOverlapsHH );

        setMaxAdultWindow (maxAdultHoursAvailHH);
        setMaxChildWindow (maxChildHoursAvailHH);

    }


    public boolean[] getAvailableJointTourTimeWindows( Tour t, int[] altStarts, int[] altEnds ) {
        byte[] participatingPersonIndices = t.getPersonNumArray();

        // availability array for each person
        boolean[][] availability = new boolean[participatingPersonIndices.length][];

        for ( int i=0; i < participatingPersonIndices.length; i++ ) {

            int personNum = participatingPersonIndices[i];
            Person person = persons[personNum];
            
            // availability array is 1-based indexing
            availability[i] = new boolean[altStarts.length+1];

            for ( int k=1; k <= altStarts.length; k++ ) {
                int start = altStarts[k-1];
                int end = altEnds[k-1];
                availability[i][k] = person.isWindowAvailable(start, end);
            }

        }


        boolean[] jointAvailability = new boolean[availability[0].length];

        for ( int k=0; k < jointAvailability.length; k++ ) {
            jointAvailability[k] = true;
            for ( int i=0; i < participatingPersonIndices.length; i++ ) {
                if ( ! availability[i][k] ) {
                    jointAvailability[k] = false;
                    break;
                }
            }
        }

        return jointAvailability;

    }


    public void createJointTourArray () {
        jointTours = new Tour[0];
    }


    public void createJointTourArray ( Tour tour1 ) {
        jointTours = new Tour[1];
        tour1.setTourOrigTaz( homeTaz );
        tour1.setTourOrigWalkSubzone( homeWalkSubzone );
        jointTours[0] = tour1;
    }


    public void createJointTourArray ( Tour tour1, Tour tour2 ) {
        jointTours = new Tour[2];
        tour1.setTourOrigTaz( homeTaz );
        tour1.setTourOrigWalkSubzone( homeWalkSubzone );
        tour1.setTourId(0);
        tour2.setTourOrigTaz( homeTaz );
        tour2.setTourOrigWalkSubzone( homeWalkSubzone );
        tour2.setTourId(1);
        jointTours[0] = tour1;
        jointTours[1] = tour2;
    }


    public Tour[] getJointTourArray() {
        return jointTours;
    }
    

    /**
     * Set the joint tour array.
     * 
     * @param jointTours
     */
    public void setJointTourArray(Tour[] jointTours) {
        this.jointTours = jointTours;
    }
  
    public void initializeForAoRestart() {
        jointTours = null;        

        aoModelAutos = 0;
        cdapModelPattern = null;
        imtfModelPattern = 0;
        jtfModelPattern = null;

        fpRandomCount = 0;
        cdapRandomCount = 0;
        imtfRandomCount = 0;
        imtodRandomCount = 0;
        awfRandomCount = 0;
        awlRandomCount = 0;
        awtodRandomCount = 0;
        jtfRandomCount = 0;
        jtlRandomCount = 0;
        jtodRandomCount = 0;
        inmtfRandomCount = 0;
        inmtlRandomCount = 0;
        inmtodRandomCount = 0;
        stfRandomCount = 0;
        stlRandomCount = 0;

        maxAdultOverlaps = 0;
        maxChildOverlaps = 0;
        maxAdultChildOverlaps = 0;
        maxHoursAvailableAdult = 0;
        maxHoursAvailableChild = 0;

        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForAoRestart();
        
    }

    
    
    public void initializeForImtfRestart() {
        jointTours = null;        

        imtfModelPattern = 0;
        jtfModelPattern = null;

        imtodRandomCount = 0;
        jtfRandomCount = 0;
        jtlRandomCount = 0;
        jtodRandomCount = 0;
        inmtfRandomCount = 0;
        inmtlRandomCount = 0;
        inmtodRandomCount = 0;
        awfRandomCount = 0;
        awlRandomCount = 0;
        awtodRandomCount = 0;
        stfRandomCount = 0;
        stlRandomCount = 0;

        maxAdultOverlaps = 0;
        maxChildOverlaps = 0;
        maxAdultChildOverlaps = 0;
        maxHoursAvailableAdult = 0;
        maxHoursAvailableChild = 0;
        
        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForImtfRestart();

        jointTours = null;        
        
    }

    public void initializeForImmcRestart(boolean runJointTourFrequencyModel, boolean runIndividualNonMandatoryTourFrequencyModel, boolean runAtWorkSubtourFrequencyModel) {

        immcRandomCount = 0;
        jmcRandomCount = 0; 
        inmmcRandomCount = 0; 
        awmcRandomCount = 0; 
        
    	if (runJointTourFrequencyModel) initializeForJtfRestart();
    	if (runIndividualNonMandatoryTourFrequencyModel) initializeForInmtfRestart();
    	if (runAtWorkSubtourFrequencyModel) initializeForAwfRestart();
        initializeForStfRestart(); 
        
    }    
    
    public void initializeForJtfRestart() {

        jtfModelPattern = null;

        jtlRandomCount = 0;
        jtodRandomCount = 0;
        inmtfRandomCount = 0;
        inmtlRandomCount = 0;
        inmtodRandomCount = 0;
        awfRandomCount = 0;
        awlRandomCount = 0;
        awtodRandomCount = 0;
        stfRandomCount = 0;
        stlRandomCount = 0;

        initializeWindows(); 

        if ( jointTours != null ) {
            for ( Tour t : jointTours ) {
                t.clearStopModelResults();
            }
        }

        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForJtfRestart();
        
        
        jointTours = null;        

    }


    public void initializeForJmcRestart(boolean runIndividualNonMandatoryTourFrequencyModel, boolean runAtWorkSubtourFrequencyModel) {

        jmcRandomCount = 0; 
        inmmcRandomCount = 0; 
        awmcRandomCount = 0; 
        
    	if (runIndividualNonMandatoryTourFrequencyModel) initializeForInmtfRestart();
    	if (runAtWorkSubtourFrequencyModel) initializeForAwfRestart();
        initializeForStfRestart(); 
        
    }    
    
    public void initializeForInmtfRestart() {

        inmtlRandomCount = 0;
        inmtodRandomCount = 0;
        awfRandomCount = 0;
        awlRandomCount = 0;
        awtodRandomCount = 0;
        stfRandomCount = 0;
        stlRandomCount = 0;

        initializeWindows(); 

        if ( jointTours != null ) {
            for ( Tour t : jointTours ) {
                for ( int i : t.getPersonNumArray() )
                    persons[i].scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
                t.clearStopModelResults();
            }
        }

        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForInmtfRestart();
        
    }


    public void initializeForInmmcRestart(boolean runAtWorkSubtourFrequencyModel) {

        inmmcRandomCount = 0; 
        awmcRandomCount = 0; 
        
    	if (runAtWorkSubtourFrequencyModel) initializeForAwfRestart();
        initializeForStfRestart(); 
        
    }    
    
    public void initializeForAwfRestart() {

        awlRandomCount = 0;
        awtodRandomCount = 0;
        stfRandomCount = 0;
        stlRandomCount = 0;

        initializeWindows(); 

        if ( jointTours != null ) {
            for ( Tour t : jointTours ) {
                for ( int i : t.getPersonNumArray() )
                    persons[i].scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
                t.clearStopModelResults();
            }
        }

        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForAwfRestart();
        
    }


    public void initializeForAwmcRestart() {

        awmcRandomCount = 0; 
        initializeForStfRestart(); 
                
    }    
    
    public void initializeForStfRestart() {

        stlRandomCount = 0;

        Tour[] jt = getJointTourArray();
        if ( jt != null ) {

            for ( Tour t : jt )
                t.clearStopModelResults();

        }
        
        
        for ( int i=1; i < persons.length; i++ )
            persons[i].initializeForStfRestart();
        
    }

    
    
    
    public void logHouseholdObject( String titleString, Logger logger ) {
        
        int totalChars = 72;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "H";

       
        logger.info( separater );
        logger.info( titleString );
        logger.info( separater );

        
        Household.logHelper( logger, "hhId: ", hhId, totalChars );
        Household.logHelper( logger, "debugChoiceModels: ", debugChoiceModels ? "True" : "False", totalChars );
        Household.logHelper( logger, "hhIncomeInDollars: ", hhIncomeInDollars, totalChars );
        Household.logHelper( logger, "hhSize: ", hhSize, totalChars );
        Household.logHelper( logger, "hhType: ", hhType, totalChars );
        Household.logHelper( logger, "hhWorkers: ", hhWorkers, totalChars );
        Household.logHelper( logger, "homeTaz: ", homeTaz, totalChars );
        Household.logHelper( logger, "homeWalkSubzone: ", homeWalkSubzone, totalChars );
        Household.logHelper( logger, "aoModelAutos: ", aoModelAutos, totalChars );
        Household.logHelper( logger, "cdapModelPattern: ", cdapModelPattern, totalChars );
        Household.logHelper( logger, "imtfModelPattern: ", imtfModelPattern, totalChars );
        Household.logHelper( logger, "jtfModelPattern: ", jtfModelPattern, totalChars );
        Household.logHelper( logger, "randomCount: ", randomCount, totalChars );
        Household.logHelper( logger, "uwslRandomCount: ", uwslRandomCount, totalChars );
        Household.logHelper( logger, "aoRandomCount: ", aoRandomCount, totalChars );
        Household.logHelper( logger, "fpRandomCount: ", fpRandomCount, totalChars );
        Household.logHelper( logger, "cdapRandomCount: ", cdapRandomCount, totalChars );
        Household.logHelper( logger, "imtfRandomCount: ", imtfRandomCount, totalChars );
        Household.logHelper( logger, "imtodRandomCount: ", imtodRandomCount, totalChars );
        Household.logHelper( logger, "awfRandomCount: ", awfRandomCount, totalChars );
        Household.logHelper( logger, "awlRandomCount: ", awlRandomCount, totalChars );
        Household.logHelper( logger, "awtodRandomCount: ", awtodRandomCount, totalChars );
        Household.logHelper( logger, "jtfRandomCount: ", jtfRandomCount, totalChars );
        Household.logHelper( logger, "jtlRandomCount: ", jtlRandomCount, totalChars );
        Household.logHelper( logger, "jtodRandomCount: ", jtodRandomCount, totalChars );
        Household.logHelper( logger, "inmtfRandomCount: ", inmtfRandomCount, totalChars );
        Household.logHelper( logger, "inmtlRandomCount: ", inmtlRandomCount, totalChars );
        Household.logHelper( logger, "inmtodRandomCount: ", inmtodRandomCount, totalChars );
        Household.logHelper( logger, "stfRandomCount: ", stfRandomCount, totalChars );
        Household.logHelper( logger, "stlRandomCount: ", stlRandomCount, totalChars );
        Household.logHelper( logger, "maxAdultOverlaps: ", maxAdultOverlaps, totalChars );
        Household.logHelper( logger, "maxChildOverlaps: ", maxChildOverlaps, totalChars );
        Household.logHelper( logger, "maxAdultChildOverlaps: ", maxAdultChildOverlaps, totalChars );
        Household.logHelper( logger, "maxHoursAvailableAdult: ", maxHoursAvailableAdult, totalChars );
        Household.logHelper( logger, "maxHoursAvailableChild: ", maxHoursAvailableChild, totalChars );
        
        String tempString = String.format( "Joint Tours[%s]:", jointTours == null ? "" : String.valueOf(jointTours.length) );
        logger.info( tempString );

        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
    public void logPersonObject( String titleString, Logger logger, Person person ) {
        
        int totalChars = 114;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "P";

       
        logger.info( separater );
        logger.info( titleString );
        logger.info( separater );

        person.logPersonObject( logger, totalChars );

        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
    public void logTourObject( String titleString, Logger logger, Person person, Tour tour ) {
        
        int totalChars = 119;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "T";

       
        logger.info( separater );
        logger.info( titleString );
        logger.info( separater );

        
        person.logTourObject( logger, totalChars, tour );

        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
    public void logStopObject( String titleString, Logger logger, Stop stop, ModelStructure modelStructure ) {
        
        int totalChars = 119;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "S";

       
        logger.info( separater );
        logger.info( titleString );
        logger.info( separater );

        
        stop.logStopObject( logger, totalChars, modelStructure );

        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
    public void logEntireHouseholdObject( String titleString, Logger logger, ModelStructure modelStructure ) {
        
        int totalChars = 60;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "=";

       
        logger.info( separater );
        logger.info( titleString );
        logger.info( separater );

        
        separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "-";
        
        Household.logHelper( logger, "hhId: ", hhId, totalChars );
        Household.logHelper( logger, "debugChoiceModels: ", debugChoiceModels ? "True" : "False", totalChars );
       Household.logHelper( logger, "hhIncomeInDollars: ", hhIncomeInDollars, totalChars );
        Household.logHelper( logger, "hhSize: ", hhSize, totalChars );
        Household.logHelper( logger, "hhType: ", hhType, totalChars );
        Household.logHelper( logger, "hhWorkers: ", hhWorkers, totalChars );
        Household.logHelper( logger, "homeTaz: ", homeTaz, totalChars );
        Household.logHelper( logger, "homeWalkSubzone: ", homeWalkSubzone, totalChars );
        Household.logHelper( logger, "aoModelAutos: ", aoModelAutos, totalChars );
        Household.logHelper( logger, "cdapModelPattern: ", cdapModelPattern, totalChars );
        Household.logHelper( logger, "imtfModelPattern: ", imtfModelPattern, totalChars );
        Household.logHelper( logger, "jtfModelPattern: ", jtfModelPattern, totalChars );
        Household.logHelper( logger, "randomCount: ", randomCount, totalChars );
        Household.logHelper( logger, "uwslRandomCount: ", uwslRandomCount, totalChars );
        Household.logHelper( logger, "aoRandomCount: ", aoRandomCount, totalChars );
        Household.logHelper( logger, "fpRandomCount: ", fpRandomCount, totalChars );
        Household.logHelper( logger, "cdapRandomCount: ", cdapRandomCount, totalChars );
        Household.logHelper( logger, "imtfRandomCount: ", imtfRandomCount, totalChars );
        Household.logHelper( logger, "imtodRandomCount: ", imtodRandomCount, totalChars );
        Household.logHelper( logger, "awfRandomCount: ", awfRandomCount, totalChars );
        Household.logHelper( logger, "awlRandomCount: ", awlRandomCount, totalChars );
        Household.logHelper( logger, "awtodRandomCount: ", awtodRandomCount, totalChars );
        Household.logHelper( logger, "jtfRandomCount: ", jtfRandomCount, totalChars );
        Household.logHelper( logger, "jtlRandomCount: ", jtlRandomCount, totalChars );
        Household.logHelper( logger, "jtodRandomCount: ", jtodRandomCount, totalChars );
        Household.logHelper( logger, "inmtfRandomCount: ", inmtfRandomCount, totalChars );
        Household.logHelper( logger, "inmtlRandomCount: ", inmtlRandomCount, totalChars );
        Household.logHelper( logger, "inmtodRandomCount: ", inmtodRandomCount, totalChars );
        Household.logHelper( logger, "stfRandomCount: ", stfRandomCount, totalChars );
        Household.logHelper( logger, "stlRandomCount: ", stlRandomCount, totalChars );
        Household.logHelper( logger, "maxAdultOverlaps: ", maxAdultOverlaps, totalChars );
        Household.logHelper( logger, "maxChildOverlaps: ", maxChildOverlaps, totalChars );
        Household.logHelper( logger, "maxAdultChildOverlaps: ", maxAdultChildOverlaps, totalChars );
        Household.logHelper( logger, "maxHoursAvailableAdult: ", maxHoursAvailableAdult, totalChars );
        Household.logHelper( logger, "maxHoursAvailableChild: ", maxHoursAvailableChild, totalChars );
        // guojy: added for M. Gucwa's research on automated vehicles
        Household.logHelper( logger, "hAnalyst: ", hAnalyst, totalChars );

        if ( jointTours != null ) {
            logger.info("Joint Tours:");
            if ( jointTours.length > 0 ) { 
                for ( int i=0; i < jointTours.length; i++ )
                    jointTours[i].logEntireTourObject( logger, modelStructure );
            }
            else
                logger.info("     No joint tours");
        }
        else
            logger.info("     No joint tours");

        logger.info("Person Objects:");
        for ( int i=1; i < persons.length; i++ )
            persons[i].logEntirePersonObject( logger, modelStructure );

        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
    public static void logHelper( Logger logger, String label, int value, int totalChars ){
        int labelChars = label.length() + 2;
        int remainingChars = totalChars - labelChars - 4;
        String formatString = String.format("     %%%ds %%%dd", label.length(), remainingChars);
        String logString = String.format( formatString, label, value );
        logger.info( logString );        
    }
    
    public static void logHelper( Logger logger, String label, String value, int totalChars ){
        int labelChars = label.length() + 2;
        int remainingChars = totalChars - labelChars - 4;
        String formatString = String.format("     %%%ds %%%ds", label.length(), remainingChars);
        String logString = String.format( formatString, label, value );
        logger.info( logString );        
    }
    
    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst() {
		return hAnalyst;
	}


    // guojy: added for M. Gucwa's research on automated vehicles
	public void setHAnalyst(int hAnalyst) {
		this.hAnalyst = hAnalyst;
	}


	public enum HouseholdType {
        nul,
        FAMILY_MARRIED,
        FAMILY_MALE_NO_WIFE,
        FAMILY_FEMALE_NO_HUSBAND,
        NON_FAMILY_MALE_ALONE,
        NON_FAMILY_MALE_NOT_ALONE,
        NON_FAMILY_FEMALE_ALONE,
        NON_FAMILY_FEMALE_NOT_ALONE
    }

}
