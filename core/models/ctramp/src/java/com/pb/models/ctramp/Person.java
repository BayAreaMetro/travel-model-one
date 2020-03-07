package com.pb.models.ctramp;

import java.util.ArrayList;

import org.apache.log4j.Logger;
import com.pb.models.ctramp.jppf.CtrampApplication;


public class Person implements java.io.Serializable {
    
    public static final int MIN_ADULT_AGE = 19;
    public static final int MIN_STUDENT_AGE = 5;
    
	// person type strings used for data summaries
	public static final String PERSON_TYPE_FULL_TIME_WORKER_NAME    = "Full-time worker";
	public static final String PERSON_TYPE_PART_TIME_WORKER_NAME    = "Part-time worker";
	public static final String PERSON_TYPE_UNIVERSITY_STUDENT_NAME  = "University student";
	public static final String PERSON_TYPE_NON_WORKER_NAME          = "Non-worker";
	public static final String PERSON_TYPE_RETIRED_NAME             = "Retired";
	public static final String PERSON_TYPE_STUDENT_DRIVING_NAME     = "Student of driving age";
	public static final String PERSON_TYPE_STUDENT_NON_DRIVING_NAME = "Student of non-driving age";
	public static final String PERSON_TYPE_PRE_SCHOOL_CHILD_NAME    = "Child too young for school";

    public static final String[] personTypeNameArray = {PERSON_TYPE_FULL_TIME_WORKER_NAME,PERSON_TYPE_PART_TIME_WORKER_NAME,
		PERSON_TYPE_UNIVERSITY_STUDENT_NAME,PERSON_TYPE_NON_WORKER_NAME,PERSON_TYPE_RETIRED_NAME,PERSON_TYPE_STUDENT_DRIVING_NAME,
		PERSON_TYPE_STUDENT_NON_DRIVING_NAME,PERSON_TYPE_PRE_SCHOOL_CHILD_NAME};

    // Employment category (1-employed FT, 2-employed PT, 3-not employed, 4-under age 16)
    // Student category (1 - student in grade or high school; 2 - student in college or higher; 3 - not a student)

    public static final String EMPLOYMENT_CATEGORY_FULL_TIME_WORKER_NAME    = "Full-time worker";
    public static final String EMPLOYMENT_CATEGORY_PART_TIME_WORKER_NAME    = "Part-time worker";
    public static final String EMPLOYMENT_CATEGORY_NOT_EMPLOYED_NAME        = "Not employed";
    public static final String EMPLOYMENT_CATEGORY_UNDER_AGE_16_NAME        = "Under age 16";

    public static final String[] employmentCategoryNameArray = {EMPLOYMENT_CATEGORY_FULL_TIME_WORKER_NAME,
        EMPLOYMENT_CATEGORY_PART_TIME_WORKER_NAME,EMPLOYMENT_CATEGORY_NOT_EMPLOYED_NAME,EMPLOYMENT_CATEGORY_UNDER_AGE_16_NAME};

    public static final String STUDENT_CATEGORY_GRADE_OR_HIGH_SCHOOL_NAME   = "Grade or high school";
    public static final String STUDENT_CATEGORY_COLLEGE_OR_HIGHER_NAME      = "College or higher";
    public static final String STUDENT_CATEGORY_NOT_STUDENT_NAME            = "Not student";

    public static final String[] studentCategoryNameArray = {STUDENT_CATEGORY_GRADE_OR_HIGH_SCHOOL_NAME,
        STUDENT_CATEGORY_COLLEGE_OR_HIGHER_NAME, STUDENT_CATEGORY_NOT_STUDENT_NAME};

    private Household hhObj;
    
    private byte persNum;
    private int persId;
    private byte persAge;
    private byte persGender;
    private byte persEmploymentCategory;
    private byte persStudentCategory;
    private byte personType;
    private float persValueOfTime;         // individual value-of-time in $/hr 
    private byte persPecasOcc;			   // occupation code used in PECAS model
    private short workLoc;
    private byte workLocSubzone;
    private short schoolLoc;
    private byte schoolLocSubzone;

    private byte workLocationPurposeIndex;
    private byte universityLocationPurposeIndex;
    private byte schoolLocationPurposeIndex;
    
    private float workLocationLogsum;
    private float schoolLocationLogsum;

    private byte freeParkingAvailable;
    
    private String cdapActivity;
    private byte imtfChoice;
    private byte inmtfChoice;

    private byte maxAdultOverlaps;
    private byte maxChildOverlaps;

    private byte maxTourId; 
    private ArrayList<Tour> workTourArrayList;
    private ArrayList<Tour> schoolTourArrayList;
    private ArrayList<Tour> indNonManTourArrayList;
    private ArrayList<Tour> atWorkSubtourArrayList;

    // guojy: added for M. Gucwa's research on automated vehicles
    private int pAnalyst; 


//  private Scheduler scheduler;
    private byte[] windows;
    
    private byte windowBeforeFirstMandJointTour;
    private byte windowBetweenFirstLastMandJointTour;
    private byte windowAfterLastMandJointTour;

    private byte[] halfHourWindow;
    
    private float sampleRate;

    
    public Person( Household hhObj, int persNum ) {
        this.hhObj = hhObj;
        this.persNum = (byte)persNum;
        this.maxTourId = 0; 
        this.workTourArrayList = new ArrayList<Tour>();
        this.schoolTourArrayList = new ArrayList<Tour>();
        this.indNonManTourArrayList = new ArrayList<Tour>();
        this.atWorkSubtourArrayList = new ArrayList<Tour>();
        
        if(hhObj!=null)
        	this.sampleRate = hhObj.getSampleRate();
        
        initializeWindows();
    }


    public Household getHouseholdObject() {
        return hhObj;
    }
    

    public ArrayList<Tour> getListOfWorkTours(){
    	return workTourArrayList;
    }


    public ArrayList<Tour> getListOfSchoolTours(){
    	return schoolTourArrayList;
    }

    public ArrayList<Tour> getListOfIndividualNonMandatoryTours() {
        return indNonManTourArrayList;
    }

    public ArrayList<Tour> getListOfAtWorkSubtours() {
        return atWorkSubtourArrayList;
    }

    public byte[] getTimeWindows() {
        return windows;
    }

    public void initializeWindows(){
        windows = new byte[CtrampApplication.LAST_HOUR - CtrampApplication.START_HOUR + 1];
        resetTimeWindow(CtrampApplication.START_HOUR, CtrampApplication.LAST_HOUR); 
    }

    
    public void resetTimeWindow(int startHour, int endHour){
        for ( int i=startHour; i <= endHour; i++ ) {
            int index = i - CtrampApplication.START_HOUR;
            windows[index] = 0;
        }
    }

    
    // code the timw window array for this tour being scheduled.
    // 0: unscheduled, 1: scheduled, middle of tour, 2: scheduled, start of tour,, 3: scheduled, end of tour,
    // 4: scheduled, end of previous tour, start of current tour or end of current tour, start of subsequent tour;
    //    or current tour start/end same hour.
    public void scheduleWindow( int start, int end ){

        int startIndex = start - CtrampApplication.START_HOUR;
        int endIndex = end - CtrampApplication.START_HOUR;
        
        if ( start == end ) {
            windows[startIndex] = 4;
        }
        else {
            if ( windows[startIndex] == 3 )
                windows[startIndex] = 4;
            else if ( windows[startIndex] == 0 )
                windows[startIndex] = 2;
            
            if ( windows[endIndex] == 2 )
                windows[endIndex] = 4;
            else if ( windows[endIndex] == 0 )
                windows[endIndex] = 3;
        }
        
        
        for ( int h=start+1; h < end; h++ ) {
            int index = h - CtrampApplication.START_HOUR;
            windows[index] = 1;
        }
    }
    

    public boolean[] getAvailableTimeWindows( int[] altStarts, int[] altEnds ) {

        // availability array is used by UEC based choice model, which uses 1-based indexing
        boolean[] availability = new boolean[altStarts.length+1];

        for ( int i=1; i <= altStarts.length; i++ ) {
            int start = altStarts[i-1];
            int end = altEnds[i-1];
            availability[i] = isWindowAvailable( start, end );
        }

        return availability;
    }

    
    /**
	 * @return the halfHourWindow
	 */
	public byte[] getHalfHourWindow() {
		return halfHourWindow;
	}


	/**
	 * @param halfHourWindow the halfHourWindow to set
	 */
	public void setHalfHourWindow(byte[] halfHourWindow) {
		this.halfHourWindow = halfHourWindow;
	}


	public boolean isWindowAvailable( int start, int end ) {
        
        // check start hour, if window is 0, it is unscheduled; if window is 3, it is the last hour of another tour, and available as the first hour of this tour. 
        int index = start - CtrampApplication.START_HOUR;
        if ( windows[index] == 1 )
            return false;
        else if ( windows[index] == 2 && start != end )
            return false;
        
        // check end hour, if window is 0, it is unscheduled; if window is 2, it is the first hour of another tour, and available as the last hour of this tour. 
        index = end - CtrampApplication.START_HOUR;
        if ( windows[index] == 1 )
            return false;
        else if ( windows[index] == 3 && start != end )
            return false;
        
        // the alternative is available if start and end are available, and all hours from start+1,...,end-1 are available.
        for ( int h=start+1; h < end; h++ ) {
            index = h - CtrampApplication.START_HOUR;
            if ( windows[index] > 0 )
                return false;
        }
        
        return true;
    }

    /**
     * @return true if the window for the argument is the end of a previously scheduled tour
     * and this hour does not overlap with any other tour.
     */
    public boolean isPreviousArrival( int hour ) {
        
        int index = hour - CtrampApplication.START_HOUR;

        if ( windows[index] == 3 || windows[index] == 4 )
            return true;
        else
            return false;
            
    }
    
    
    /**
     * @return true if the window for the argument is the start of a previously scheduled tour
     * and this hour does not overlap with any other tour.
     */
    public boolean isPreviousDeparture( int hour ) {
        
        int index = hour - CtrampApplication.START_HOUR;

        if ( windows[index] == 2 || windows[index] == 4 )
            return true;
        else
            return false;
            
    }
    
    
    public boolean isHourAvailable( int hour ){
        // if windows[index] == 0, the hour is available.
        int index = hour - CtrampApplication.START_HOUR;
        
        // if window[index] is 0 (available), 2 (start of another tour), 3 (end of another tour), 4 available for this hour only,
        // the hour is available;  otherwise, if window[index] is 1 (middle of another tour), it is not available.
        if ( windows[index] == 1 )
            return false;
        else
            return true;
    }
    
    

    public void setPersId( int id ) {
        persId = id;
    }

    public void setWorkLocationPurposeIndex( int workPurpose ) {
        workLocationPurposeIndex = (byte)workPurpose;
    }

    public void setUniversityLocationPurposeIndex( int universityPurpose ) {
        universityLocationPurposeIndex = (byte)universityPurpose;
    }

    public void setSchoolLocationPurposeIndex( int schoolPurpose ) {
        schoolLocationPurposeIndex = (byte)schoolPurpose;
    }

    public void setPersAge( int age ) {
        persAge = (byte)age;
    }
    
    public void setPersGender( int gender ) {
        persGender = (byte)gender;
    }
    
    public void setPersEmploymentCategory( int category ) {
        persEmploymentCategory = (byte)category;
    }
    
    public void setPersStudentCategory( int category ){
    	persStudentCategory = (byte)category;
    }
    
    public void setPersonTypeCategory ( int personTypeCategory ) {
        personType = (byte)personTypeCategory;
    }
    
    public void setValueOfTime ( float vot ) {
    	persValueOfTime = vot; 
    }

    public void setWorkLoc( int loc ) {
        workLoc= (short)loc;
    }
    
    public void setWorkLocSubzone( int subzone ) {
        workLocSubzone= (byte)subzone;
    }
    
    public void setSchoolLoc( int loc ) {
        schoolLoc= (short)loc;
    }
    
    public void setSchoolLocSubzone( int subzone ) {
        schoolLocSubzone= (byte)subzone;
    }

    public void setFreeParkingAvailableResult( int fpResult ) {
        freeParkingAvailable = (byte)fpResult;
    }
    
    public int getFreeParkingAvailableResult() {
        return freeParkingAvailable;
    }
    
    public void setImtfChoice ( int choice ) {
        imtfChoice = (byte)choice;
    }

    public void setInmtfChoice ( int choice ) {
        inmtfChoice = (byte)choice;
    }

    public int getImtfChoice () {
        return imtfChoice;
    }

    public int getInmtfChoice () {
        return inmtfChoice;
    }

    public void clearIndividualNonMandatoryToursArray() {
        indNonManTourArrayList.clear();
    }
    
    public void createIndividualNonMandatoryTours( int numberOfTours, String purposeName, ModelStructure modelStructure ){

        // if purpose is escort, need to determine if household has kids or not
        if ( purposeName.equalsIgnoreCase( ModelStructure.ESCORT_PURPOSE_NAME ) ) {
            if ( hhObj.getNumChildrenUnder19() > 0 )
                purposeName += "_" + modelStructure.ESCORT_SEGMENT_NAMES[0];
            else
                purposeName += "_" + modelStructure.ESCORT_SEGMENT_NAMES[1];
        }
        
        int purposeIndex = modelStructure.getDcModelPurposeIndex( purposeName );
          
        int startId = indNonManTourArrayList.size();
        
        for(int i=0;i<numberOfTours;i++){
            
            int id = startId + i;
            Tour tempTour = new Tour( id, this.hhObj, this, modelStructure, purposeIndex, purposeName, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY_INDEX );
            maxTourId++;

            tempTour.setTourOrigTaz(this.hhObj.getHhTaz());
    		tempTour.setTourOrigWalkSubzone(this.hhObj.getHhWalkSubzone());

    		tempTour.setTourDestTaz(-1);
    		tempTour.setTourDestWalkSubzone(-1);
            tempTour.setSampleRate(sampleRate);

            indNonManTourArrayList.add(tempTour);
            
    	}

    }

    public void createWorkTours( int numberOfTours, int startId, String tourPurpose, ModelStructure modelStructure ){

        workTourArrayList.clear();
        
        for(int i=0;i<numberOfTours;i++){
            int id = startId + i;
            Tour tempTour = new Tour(this, id);
            maxTourId++;

            tempTour.setTourOrigTaz(this.hhObj.getHhTaz());
            tempTour.setTourOrigWalkSubzone(this.hhObj.getHhWalkSubzone());

            tempTour.setTourDestTaz(workLoc);
            tempTour.setTourDestWalkSubzone(workLocSubzone);
            
            tempTour.setDestinationChoiceLogsum(workLocationLogsum);

            tempTour.setTourPurpose( tourPurpose );
            tempTour.setSampleRate(sampleRate);

            modelStructure.setSegmentedIndexPurpose( modelStructure.getDcModelPurposeIndex(tourPurpose), tourPurpose );
            modelStructure.setSegmentedPurposeIndex( tourPurpose, modelStructure.getDcModelPurposeIndex(tourPurpose) );

            workTourArrayList.add(tempTour);
        }

    }

    public void clearAtWorkSubtours(){

        atWorkSubtourArrayList.clear();
        
    }
    

    public void createAtWorkSubtour( int id, int choice, int workTaz, int workSubZone, String tourPurpose, ModelStructure modelStructure ){

            
        String segmentedPurpose = ModelStructure.AT_WORK_PURPOSE_NAME + "_" + tourPurpose;
        int purposeIndex = modelStructure.getDcModelPurposeIndex( segmentedPurpose );
        
        Tour tempTour = new Tour( id, this.hhObj, this, modelStructure, purposeIndex, segmentedPurpose, ModelStructure.AT_WORK_CATEGORY_INDEX );
        maxTourId++;

        tempTour.setTourOrigTaz(workTaz);
        tempTour.setTourOrigWalkSubzone(workSubZone);
        tempTour.setSampleRate(sampleRate);

        atWorkSubtourArrayList.add(tempTour);

    }
    

    public void createSchoolTours( int numberOfTours, int startId, String tourPurpose, ModelStructure modelStructure ){
    	
        schoolTourArrayList.clear();
        
    	for(int i=0;i<numberOfTours;i++){
            int id = startId + i;
            Tour tempTour = new Tour(this, id);
            maxTourId++;

    		tempTour.setTourOrigTaz(this.hhObj.getHhTaz());
    		tempTour.setTourOrigWalkSubzone(this.hhObj.getHhWalkSubzone());
    		
    		tempTour.setTourDestTaz(schoolLoc);
    		tempTour.setTourDestWalkSubzone(schoolLocSubzone);
    		
    		tempTour.setDestinationChoiceLogsum(schoolLocationLogsum);

            tempTour.setTourPurpose( tourPurpose );

            modelStructure.setSegmentedIndexPurpose( modelStructure.getDcModelPurposeIndex(tourPurpose), tourPurpose );
            modelStructure.setSegmentedPurposeIndex( tourPurpose, modelStructure.getDcModelPurposeIndex(tourPurpose) );
            tempTour.setSampleRate(sampleRate);

            schoolTourArrayList.add(tempTour);
    	}
    }



    public int getWorkLocationPurposeIndex() {
        return workLocationPurposeIndex;
    }

    public int getUniversityLocationPurposeIndex() {
        return universityLocationPurposeIndex;
    }

    public int getSchoolLocationPurposeIndex() {
        return schoolLocationPurposeIndex;
    }



    public void setDailyActivityResult(String activity){
    	this.cdapActivity = activity;
    }
    
    public int getPersonIsChildUnder16WithHomeOrNonMandatoryActivity(){
    	
    	// check the person type
    	if(persIsStudentNonDrivingAge()==1 || persIsPreschoolChild()==1){
    		
    		// check the activity type
    		if(cdapActivity.equalsIgnoreCase(CoordinatedDailyActivityPatternModel.HOME_PATTERN)) 
    			return(1);
    		
    		if(cdapActivity.equalsIgnoreCase(CoordinatedDailyActivityPatternModel.NONMANDATORY_PATTERN)) 
    			return(1);
    		
    	}
    	
    	return(0);
    }
    
    // methods DMU will use to get info from household object
    
    public int getAge() {
        return persAge;
    }
    
    public int getHomemaker() {
        return persIsHomemaker();
    }
    
    public int getGender() {
        return persGender;
    }
    
    public int getPersonIsFemale() {
    	if(persGender==2) return 1;
    	return 0;
    }

    public int getPersonIsMale() {
    	if(persGender==1) return 1;
    	return 0;
    }

    public int getPersonId(){
    	return this.persId;
    }

    public int getPersonNum(){
        return this.persNum;
    }

    public String getPersonType() {
        return personTypeNameArray[personType-1];
    }

    public int getPersonTypeNumber() {
        return personType;
    }

    public String getPersonEmploymentCategory() {
        return employmentCategoryNameArray[persEmploymentCategory-1];
    }

    public String getPersonStudentCategory() {
        return studentCategoryNameArray[persStudentCategory-1];
    }
    
    public float getValueOfTime() {
        return persValueOfTime;
    }

    public int getPersonWorkLocationZone() {
        return workLoc;
    }

    public int getPersonWorkLocationSubZone() {
        return workLocSubzone;
    }

    public int getPersonSchoolLocationSubZone() {
        return schoolLocSubzone;
    }

    public int getPersonSchoolLocationZone() {
        return schoolLoc;
    }

    public String getCdapActivity(){
    	return this.cdapActivity;
    }
    
    public int getUsualWorkLocation(){
    	return this.workLoc;
    }
    
    public int getUsualSchoolLocation(){
    	return this.schoolLoc;
    }


    public int getNumWorkTours() {
        return getListOfWorkTours().size();
    }

    public int getNumUniversityTours() {
        int num = 0;
        for ( Tour tour : getListOfSchoolTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.UNIVERSITY_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumSchoolTours() {
        int num = 0;
        for ( Tour tour : getListOfSchoolTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SCHOOL_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualEscortTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.ESCORT_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualShoppingTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SHOPPING_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualEatOutTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.EAT_OUT_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualOthMaintTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_MAINT_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualSocialTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SOCIAL_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumIndividualOthDiscrTours() {
        int num = 0;
        for ( Tour tour : getListOfIndividualNonMandatoryTours() )
            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_DISCR_PURPOSE_NAME ) )
                num++;
        return num;
    }

    public int getNumMandatoryTours() {
        return getListOfWorkTours().size() + getListOfSchoolTours().size();
    }

    public int getNumJointShoppingTours() {
        return getNumJointToursForPurpose( ModelStructure.SHOPPING_PURPOSE_NAME );
    }

    public int getNumJointOthMaintTours() {
        return getNumJointToursForPurpose( ModelStructure.OTH_MAINT_PURPOSE_NAME );
    }

    public int getNumJointEatOutTours() {
        return getNumJointToursForPurpose( ModelStructure.EAT_OUT_PURPOSE_NAME );
    }

    public int getNumJointSocialTours() {
        return getNumJointToursForPurpose( ModelStructure.SOCIAL_PURPOSE_NAME );
    }

    public int getNumJointOthDiscrTours() {
        return getNumJointToursForPurpose( ModelStructure.OTH_DISCR_PURPOSE_NAME ); 
    }

    private int getNumJointToursForPurpose( String purposeName ) {
        int count = 0;
        Tour[] jt = hhObj.getJointTourArray();
        if ( jt == null )
            return count;

        for (int i=0; i < jt.length; i++)
            if ( jt[i].getTourPurpose().equalsIgnoreCase( purposeName ) )
                count++;

        return count;
    }




    public void computeIdapResidualWindows() {

        // find the start of the earliest mandatory or joint tour for this person
        // and end of last one.
        int firstTourStartHour = 99;
        int lastTourEndHour = -1;
        int firstTourEndHour = 0;
        int lastTourStartHour = 0;

        // first check mandatory tours
        for ( Tour tour : workTourArrayList ) {
            int tourStartHour = tour.getTourStartHour();
            int tourEndHour = tour.getTourEndHour();

            if ( tourStartHour  < firstTourStartHour ) {
                firstTourStartHour = tourStartHour;
                firstTourEndHour = tourEndHour;
            }

            if ( tourEndHour  > lastTourEndHour ) {
                lastTourStartHour = tourStartHour;
                lastTourEndHour = tourEndHour;
            }
        }

        for ( Tour tour : schoolTourArrayList ) {
            int tourStartHour = tour.getTourStartHour();
            int tourEndHour = tour.getTourEndHour();

            if ( tourStartHour  < firstTourStartHour ) {
                firstTourStartHour = tourStartHour;
                firstTourEndHour = tourEndHour;
            }

            if ( tourEndHour  > lastTourEndHour ) {
                lastTourStartHour = tourStartHour;
                lastTourEndHour = tourEndHour;
            }
        }


        // now check joint tours
        Tour[] jointTourArray = hhObj.getJointTourArray();
        if ( jointTourArray != null ) {
            for ( Tour tour : jointTourArray ) {
                
                if ( tour == null )
                    continue;
                
                // see if this person is in the joint tour or not
                if ( tour.getPersonInJointTour( this ) ) {
                    
                    int tourStartHour = tour.getTourStartHour();
                    int tourEndHour = tour.getTourEndHour();
        
                    if ( tourStartHour  < firstTourStartHour ) {
                        firstTourStartHour = tourStartHour;
                        firstTourEndHour = tourEndHour;
                    }
                    
                    if ( tourEndHour  > lastTourEndHour ) {
                        lastTourStartHour = tourStartHour;
                        lastTourEndHour = tourEndHour;
                    }
                    
                }
                
            }
        }
        
        
        if ( firstTourStartHour > CtrampApplication.LAST_HOUR && lastTourEndHour < 0 ) {
            byte numHours = (byte)windows.length;
            windowBeforeFirstMandJointTour = numHours;
            windowAfterLastMandJointTour = numHours;
            windowBetweenFirstLastMandJointTour = numHours;
        }
        else {
            
            // since first tour first hour and last tour last hour must be available, add 1 each to the difference.
            windowBeforeFirstMandJointTour = (byte)(firstTourStartHour - CtrampApplication.START_HOUR + 1);
            windowAfterLastMandJointTour = (byte)(CtrampApplication.LAST_HOUR - lastTourEndHour + 1);

            // find the number of unscheduled hours between end of first tour and start of last tour
            windowBetweenFirstLastMandJointTour = 0;
            for ( int i=firstTourEndHour; i <= lastTourStartHour; i++ ) {
                if ( isHourAvailable( i ) )
                    windowBetweenFirstLastMandJointTour++;
            }
        }

        
    }



    public int getWindowBeforeFirstMandJointTour() {
        return windowBeforeFirstMandJointTour;
    }

    public int getWindowBetweenFirstLastMandJointTour() {
        return windowBetweenFirstLastMandJointTour;
    }

    public int getWindowAfterLastMandJointTour() {
        return windowAfterLastMandJointTour;
    }




//    public int getNumberOfMandatoryWorkTours( String workPurposeName ){
//
//    	int numberOfTours = 0;
//    	for(int i=0;i<tourArrayList.size();++i){
//    		if(tourArrayList.get(i).getTourPurposeString().equalsIgnoreCase( workPurposeName ))
//    			numberOfTours++;
//    	}
//
//    	return(numberOfTours);
//    }
//
//    public int getNumberOfMandatorySchoolTours( String schoolPurposeName ){
//
//    	int numberOfTours = 0;
//    	for(int i=0;i<tourArrayList.size();++i){
//    		if(tourArrayList.get(i).getTourPurposeString().equalsIgnoreCase( schoolPurposeName ))
//    			numberOfTours++;
//    	}
//
//    	return(numberOfTours);
//    }
//
//    public int getNumberOfMandatoryWorkAndSchoolTours( String workAndschoolPurposeName ){
//
//    	int numberOfTours = 0;
//    	for(int i=0;i<tourArrayList.size();++i){
//    		if(tourArrayList.get(i).getTourPurposeString().equalsIgnoreCase( workAndschoolPurposeName ))
//    			numberOfTours++;
//    	}
//
//    	return(numberOfTours);
//    }
    
    /**
     * determine if person is a worker (indepdent of person type).
     * @return 1 if worker, 0 otherwise.
     */
    public int getPersonIsWorker() {
        return persIsWorker();
    }
    
    /**
     * Determine if person is a student (of any age, independent of person type)
     * @return 1 if student, 0 otherwise
     */
    public int getPersonIsStudent() {
    	return persIsStudent();
    }

    public int getPersonIsUniversityStudent() {
        return persIsUniversity();
    }

    public int getPersonIsStudentDriving() {
        return persIsStudentDrivingAge();
    }

    public int getPersonIsStudentNonDriving() {
        return persIsStudentNonDrivingAge();
    }
    
    /**
     * Determine if person is a full-time worker (independent of person type)
     * @return 1 if full-time worker, 0 otherwise
     */
    public int getPersonIsFullTimeWorker() {
    	return persIsFullTimeWorker();	
    }
    
    /**
     * Determine if person is a part-time worker (indepdent of person type)
     */
    public int getPersonIsPartTimeWorker() {
    	return persIsPartTimeWorker();
    }
    
    public int getPersonTypeIsFullTimeWorker(){
    	return persTypeIsFullTimeWorker();
    }
    
    public int getPersonTypeIsPartTimeWorker(){
    	return persTypeIsPartTimeWorker();
    }
    
    
    
    public int getPersonIsNonWorkingAdultUnder65() {
    	return persIsNonWorkingAdultUnder65();
    }
    
    public int getPersonIsNonWorkingAdultOver65() {
    	return persIsNonWorkingAdultOver65();
    }
    
    public int getPersonIsPreschoolChild(){
    	return persIsPreschoolChild();
    }
    
    public int getPersonIsAdult(){
    	return persIsAdult();
    }
    


    private int persIsHomemaker() {
        if ( persAge >= MIN_ADULT_AGE && persEmploymentCategory == EmployStatus.NOT_EMPLOYED.ordinal() )
            return 1;
        else
            return 0;
    }
    
    private int persIsAdult(){
    	if(persAge>=MIN_ADULT_AGE)
    		return 1;
    	else
    		return 0;
    }
    
    private int persIsWorker() {
        if ( persEmploymentCategory == EmployStatus.FULL_TIME.ordinal() || persEmploymentCategory == EmployStatus.PART_TIME.ordinal() )
            return 1;
        else
            return 0;
    }
    
    private int persIsStudent() {
    	if ( persStudentCategory == StudentStatus.STUDENT_HIGH_SCHOOL_OR_LESS.ordinal() ||
    			persStudentCategory == StudentStatus.STUDENT_COLLEGE_OR_HIGHER.ordinal()){
    		return 1;
    	}
    	else{
    		return 0;
    	}
    }
    
    private int persIsFullTimeWorker() {
        if ( persEmploymentCategory == EmployStatus.FULL_TIME.ordinal() )
            return 1;
        else
            return 0;
    }
    
    private int persIsPartTimeWorker() {
        if ( persEmploymentCategory == EmployStatus.PART_TIME.ordinal() )
            return 1;
        else
            return 0;
    }
    
    private int persTypeIsFullTimeWorker() {
    	if (personType == PersonType.FT_worker_age_16plus.ordinal() )
    		return 1;
    	else
    		return 0;
    }
    
    private int persTypeIsPartTimeWorker() {
    	if (personType == PersonType.PT_worker_nonstudent_age_16plus.ordinal() )
    		return 1;
    	else
    		return 0;
    }

    private int persIsUniversity() {
        if ( personType == PersonType.University_student.ordinal() )
            return 1;
        else
            return 0;
    }

    private int persIsStudentDrivingAge() {
        if ( personType == PersonType.Student_age_16_19_not_FT_wrkr_or_univ_stud.ordinal() )
            return 1;
        else
            return 0;
    }

    private int persIsStudentNonDrivingAge() {
        if ( personType == PersonType.Student_age_6_15_schpred.ordinal() )
            return 1;
        else
            return 0;
    }
    
    private int persIsPreschoolChild(){
    	if ( personType == PersonType.Preschool_under_age_6.ordinal())
    	   return 1;
    	else
    		return 0;

    }
    
    private int persIsNonWorkingAdultUnder65() {
    	if( personType == PersonType.Nonworker_nonstudent_age_16_64.ordinal() )
    		return 1;
    	else
    		return 0;
    }

    private int persIsNonWorkingAdultOver65() {
    	if( personType == PersonType.Nonworker_nonstudent_age_65plus.ordinal() ){
    		return 1;
    	}
    	else{
    		return 0;
    	}
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
     * return available time window for this person in the household.
     * @return the total number of hours available for this person
     */
    public int getAvailableWindow () {
        int numHoursAvailable = 0;
        for ( int i=0; i < windows.length; i++ )
            if ( windows[i] != 1 )
                numHoursAvailable++;
        
        return numHoursAvailable;
    }


    
    public void setTimeWindows ( byte[] win ) {
        windows = win;
    }

    
    
    public void initializeForAoRestart() {
        
    	freeParkingAvailable = 0;     	
        cdapActivity = "-";
        imtfChoice = 0;
        inmtfChoice = 0;
        
        
        maxAdultOverlaps = 0;
        maxChildOverlaps = 0;

        
        workTourArrayList.clear();
        schoolTourArrayList.clear();
        indNonManTourArrayList.clear();
        atWorkSubtourArrayList.clear();

        initializeWindows(); 

        windowBeforeFirstMandJointTour = 0;
        windowBetweenFirstLastMandJointTour = 0;
        windowAfterLastMandJointTour = 0;

    }
    

    public void initializeForImtfRestart() {
        
        imtfChoice = 0;
        inmtfChoice = 0;

        maxAdultOverlaps = 0;
        maxChildOverlaps = 0;

        workTourArrayList.clear();
        schoolTourArrayList.clear();
        indNonManTourArrayList.clear();
        atWorkSubtourArrayList.clear();

        initializeWindows(); 

        windowBeforeFirstMandJointTour = 0;
        windowBetweenFirstLastMandJointTour = 0;
        windowAfterLastMandJointTour = 0;

    }
    

    /**
     * initialize the person attributes and tour objects for restarting the model at joint tour frequency
     */
    public void initializeForJtfRestart() {
        
        inmtfChoice = 0;

        indNonManTourArrayList.clear();
        atWorkSubtourArrayList.clear();

        resetTimeWindow(CtrampApplication.START_HOUR, CtrampApplication.LAST_HOUR); 
        for ( int i=0; i < workTourArrayList.size(); i++ ) {
            Tour t = workTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < schoolTourArrayList.size(); i++ ) {
            Tour t = schoolTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }

        hhObj.updateTimeWindows();

        windowBeforeFirstMandJointTour = 0;
        windowBetweenFirstLastMandJointTour = 0;
        windowAfterLastMandJointTour = 0;

    }
    

    /**
     * initialize the person attributes and tour objects for restarting the model at individual non-mandatory tour frequency.
     */
    public void initializeForInmtfRestart() {
        
        inmtfChoice = 0;

        indNonManTourArrayList.clear();
        atWorkSubtourArrayList.clear();

        resetTimeWindow(CtrampApplication.START_HOUR, CtrampApplication.LAST_HOUR); 
        for ( int i=0; i < workTourArrayList.size(); i++ ) {
            Tour t = workTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < schoolTourArrayList.size(); i++ ) {
            Tour t = schoolTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }

        hhObj.updateTimeWindows();

        windowBeforeFirstMandJointTour = 0;
        windowBetweenFirstLastMandJointTour = 0;
        windowAfterLastMandJointTour = 0;

    }
    

    /**
     * initialize the person attributes and tour objects for restarting the model at at-work sub-tour frequency.
     */
    public void initializeForAwfRestart() {
        
        atWorkSubtourArrayList.clear();

        resetTimeWindow(CtrampApplication.START_HOUR, CtrampApplication.LAST_HOUR); 
        for ( int i=0; i < workTourArrayList.size(); i++ ) {
            Tour t = workTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < schoolTourArrayList.size(); i++ ) {
            Tour t = schoolTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < indNonManTourArrayList.size(); i++ ) {
            Tour t = indNonManTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }

        hhObj.updateTimeWindows();
    }
    

    /**
     * initialize the person attributes and tour objects for restarting the model at stop frequency.
     */
    public void initializeForStfRestart() {

        resetTimeWindow(CtrampApplication.START_HOUR, CtrampApplication.LAST_HOUR); 
        for ( int i=0; i < workTourArrayList.size(); i++ ) {
            Tour t = workTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < schoolTourArrayList.size(); i++ ) {
            Tour t = schoolTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < indNonManTourArrayList.size(); i++ ) {
            Tour t = indNonManTourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }
        for ( int i=0; i < atWorkSubtourArrayList.size(); i++ ) {
            Tour t = atWorkSubtourArrayList.get(i);
            scheduleWindow( t.getTourStartHour(), t.getTourEndHour() );
            t.clearStopModelResults();
        }

        hhObj.updateTimeWindows();
    }
    

    public void logPersonObject( Logger logger, int totalChars ) {
        
        Household.logHelper( logger, "persNum: ", persNum, totalChars );
        Household.logHelper( logger, "persId: ", persId, totalChars );
        Household.logHelper( logger, "persAge: ", persAge, totalChars );
        Household.logHelper( logger, "persGender: ", persGender, totalChars );
        Household.logHelper( logger, "persEmploymentCategory: ", persEmploymentCategory, totalChars );
        Household.logHelper( logger, "persStudentCategory: ", persStudentCategory, totalChars );
        Household.logHelper( logger, "personType: ", personType, totalChars );
        Household.logHelper( logger, "persValueOfTime: ", String.format("%6.2f", persValueOfTime), totalChars );
        Household.logHelper( logger, "workLoc: ", workLoc, totalChars );
        Household.logHelper( logger, "workLocSubzone: ", workLocSubzone, totalChars );
        Household.logHelper( logger, "schoolLoc: ", schoolLoc, totalChars );
        Household.logHelper( logger, "schoolLocSubzone: ", schoolLocSubzone, totalChars );
        Household.logHelper( logger, "workLocationPurposeIndex: ", workLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "universityLocationPurposeIndex: ", universityLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "schoolLocationPurposeIndex: ", schoolLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "freeParkingAvailable: ", freeParkingAvailable, totalChars); 
        Household.logHelper( logger, "cdapActivity: ", cdapActivity, totalChars );
        Household.logHelper( logger, "imtfChoice: ", imtfChoice, totalChars );
        Household.logHelper( logger, "inmtfChoice: ", inmtfChoice, totalChars );
        Household.logHelper( logger, "maxAdultOverlaps: ", maxAdultOverlaps, totalChars );
        Household.logHelper( logger, "maxChildOverlaps: ", maxChildOverlaps, totalChars );
        Household.logHelper( logger, "windowBeforeFirstMandJointTour: ", windowBeforeFirstMandJointTour, totalChars );
        Household.logHelper( logger, "windowBetweenFirstLastMandJointTour: ", windowBetweenFirstLastMandJointTour, totalChars );
        Household.logHelper( logger, "windowAfterLastMandJointTour: ", windowAfterLastMandJointTour, totalChars );

        String header = "        Hour:     |";
        String windowString = "        Window:   |";
        String hourString = "";
        for ( int i=0; i < windows.length; i++ ) {
            int index = i + CtrampApplication.START_HOUR;
            header += String.format(" %2d |", index);
            switch ( windows[i] ) {
            case 0:
                hourString = "    ";
                break;
            case 1:
                hourString = "XXXX";
                break;
            case 2:
                hourString = "SSSS";
                break;
            case 3:
                hourString = "EEEE";
                break;
            case 4:
                hourString = "EESS";
                break;
            }
            windowString += String.format("%4s|", hourString );
        }

        logger.info(header);
        logger.info(windowString);
        
        if ( workTourArrayList.size() > 0 ) {
            for ( Tour tour : workTourArrayList ) {
                int id = tour.getTourId();
                logger.info( tour.getTourWindow( String.format("W%d", id) ) );
            }
        }
        if ( atWorkSubtourArrayList.size() > 0 ) {
            for ( Tour tour : atWorkSubtourArrayList ) {
                int id = tour.getTourId();
                String alias = "";
                int index = tour.getTourPurpose().indexOf('_');
                
                String segmentName = tour.getTourPurpose();
                if ( index >= 0 )
                    segmentName = tour.getTourPurpose().substring( index+1 );
                    
                if ( segmentName.equalsIgnoreCase( ModelStructure.AT_WORK_BUSINESS_PURPOSE_NAME ) )
                    alias = "aB";
                else if ( segmentName.equalsIgnoreCase( ModelStructure.AT_WORK_EAT_PURPOSE_NAME ) )
                    alias = "aE";
                else if ( segmentName.equalsIgnoreCase( ModelStructure.AT_WORK_MAINT_PURPOSE_NAME ) )
                    alias = "aM";
                logger.info( tour.getTourWindow( String.format("%s%d", alias, id) ) );
            }
        }
        if ( schoolTourArrayList.size() > 0 ) {
            for ( Tour tour : schoolTourArrayList ) {
                int id = tour.getTourId();
                String alias = tour.getTourPurpose().equalsIgnoreCase("university") ? "U" : "S";
                logger.info( tour.getTourWindow( String.format("%s%d", alias, id) ) );
            }
        }
        if ( hhObj.getJointTourArray() != null && hhObj.getJointTourArray().length > 0 ) {
            for ( Tour tour : hhObj.getJointTourArray() ) {
                if ( tour == null )
                    continue;

                // log this persons time window if they are in the joint tour party.
                byte[] persNumArray = tour.getPersonNumArray();
                if ( persNumArray != null ) {
                    for ( int num : persNumArray ) {
                        if ( num == persNum ) {
                            
                            Person person = hhObj.getPersons()[num];
                            tour.setPersonObject( person );
                            
                            int id = tour.getTourId();
                            String alias = "";
                            if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.EAT_OUT_PURPOSE_NAME ) )
                                alias = "jE";
                            else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SHOPPING_PURPOSE_NAME ) )
                                alias = "jS";
                            else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_MAINT_PURPOSE_NAME ) )
                                alias = "jM";
                            else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SOCIAL_PURPOSE_NAME ) )
                                alias = "jV";
                            else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_DISCR_PURPOSE_NAME ) )
                                alias = "jD";
                            logger.info( tour.getTourWindow( String.format("%s%d", alias, id) ) );
                        }
                    }
                }
            }
        }
        if ( indNonManTourArrayList.size() > 0 ) {
            for ( Tour tour : indNonManTourArrayList ) {
                int id = tour.getTourId();
                String alias = "";
                if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.ESCORT_PURPOSE_NAME ) )
                    alias = "ie";
                else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.EAT_OUT_PURPOSE_NAME ) )
                    alias = "iE";
                else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SHOPPING_PURPOSE_NAME ) )
                    alias = "iS";
                else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_MAINT_PURPOSE_NAME ) )
                    alias = "iM";
                else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.SOCIAL_PURPOSE_NAME ) )
                    alias = "iV";
                else if ( tour.getTourPurpose().equalsIgnoreCase( ModelStructure.OTH_DISCR_PURPOSE_NAME ) )
                    alias = "iD";
                logger.info( tour.getTourWindow( String.format("%s%d", alias, id) ) );
            }
        }
            
    }

    
    public void logTourObject( Logger logger, int totalChars, Tour tour ) {
        tour.logTourObject( logger, totalChars );
    }

    
    public void logEntirePersonObject( Logger logger, ModelStructure modelStructure ) {
        
        int totalChars = 60;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "-";

        
        Household.logHelper( logger, "persNum: ", persNum, totalChars );
        Household.logHelper( logger, "persId: ", persId, totalChars );
        Household.logHelper( logger, "persAge: ", persAge, totalChars );
        Household.logHelper( logger, "persGender: ", persGender, totalChars );
        Household.logHelper( logger, "persEmploymentCategory: ", persEmploymentCategory, totalChars );
        Household.logHelper( logger, "persStudentCategory: ", persStudentCategory, totalChars );
        Household.logHelper( logger, "personType: ", personType, totalChars );
        Household.logHelper( logger, "persValueOfTime: ", String.format("%6.2f", persValueOfTime), totalChars );
        Household.logHelper( logger, "workLoc: ", workLoc, totalChars );
        Household.logHelper( logger, "workLocSubzone: ", workLocSubzone, totalChars );
        Household.logHelper( logger, "schoolLoc: ", schoolLoc, totalChars );
        Household.logHelper( logger, "schoolLocSubzone: ", schoolLocSubzone, totalChars );
        Household.logHelper( logger, "workLocationPurposeIndex: ", workLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "universityLocationPurposeIndex: ", universityLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "schoolLocationPurposeIndex: ", schoolLocationPurposeIndex, totalChars );
        Household.logHelper( logger, "freeParkingAvailable: ", freeParkingAvailable, totalChars ); 
        Household.logHelper( logger, "cdapActivity: ", cdapActivity, totalChars );
        Household.logHelper( logger, "imtfChoice: ", imtfChoice, totalChars );
        Household.logHelper( logger, "inmtfChoice: ", inmtfChoice, totalChars );
        Household.logHelper( logger, "maxAdultOverlaps: ", maxAdultOverlaps, totalChars );
        Household.logHelper( logger, "maxChildOverlaps: ", maxChildOverlaps, totalChars );
        Household.logHelper( logger, "windowBeforeFirstMandJointTour: ", windowBeforeFirstMandJointTour, totalChars );
        Household.logHelper( logger, "windowBetweenFirstLastMandJointTour: ", windowBetweenFirstLastMandJointTour, totalChars );
        Household.logHelper( logger, "windowAfterLastMandJointTour: ", windowAfterLastMandJointTour, totalChars );
        // guojy: added for M. Gucwa's research on automated vehicles
        Household.logHelper( logger, "pAnalyst: ", pAnalyst, totalChars );

        String header = "        Hour:     |";
        String windowString = "        Window:   |";
        for ( int i=0; i < windows.length; i++ ) {
            int index = i + CtrampApplication.START_HOUR;
            header += String.format(" %2d |", index);
            windowString += String.format("%4s|", windows[i] == 0 ? "    " : "XXXX");
        }

        logger.info(header);
        logger.info(windowString);
        
        if ( workTourArrayList.size() > 0 ) {
            for ( Tour tour : workTourArrayList ) {
                int id = tour.getTourId();
                logger.info( tour.getTourWindow( String.format("W%d", id) ) );
            }
        }
        if ( schoolTourArrayList.size() > 0 ) {
            for ( Tour tour : schoolTourArrayList ) {
                logger.info( tour.getTourWindow( tour.getTourPurpose().equalsIgnoreCase("university") ? "U" : "S" ) );
            }
        }
        if ( indNonManTourArrayList.size() > 0 ) {
            for ( Tour tour : indNonManTourArrayList ) {
                logger.info( tour.getTourWindow( "N" ) );
            }
        }
        if ( atWorkSubtourArrayList.size() > 0 ) {
            for ( Tour tour : atWorkSubtourArrayList ) {
                logger.info( tour.getTourWindow( "A" ) );
            }
        }
        if ( hhObj.getJointTourArray() != null && hhObj.getJointTourArray().length > 0 ) {
            for ( Tour tour : hhObj.getJointTourArray() ) {
                if ( tour != null )
                    logger.info( tour.getTourWindow( "J" ) );
            }
        }
            
        logger.info(separater);

        
        logger.info("Work Tours:");
        if ( workTourArrayList.size() > 0 ) {
            for ( Tour tour : workTourArrayList ) {
                tour.logEntireTourObject( logger, modelStructure  );
            }
        }
        else {
            logger.info ( "     No work tours" );
        }
        
        logger.info("School Tours:");
        if ( schoolTourArrayList.size() > 0 ) {
            for ( Tour tour : schoolTourArrayList ) {
                tour.logEntireTourObject( logger, modelStructure  );
            }
        }
        else {
            logger.info ( "     No school tours" );
        }

        logger.info("Individual Non-mandatory Tours:");
        if ( indNonManTourArrayList.size() > 0 ) {
            for ( Tour tour : indNonManTourArrayList ) {
                tour.logEntireTourObject( logger, modelStructure  );
            }
        }
        else {
            logger.info ( "     No individual non-mandatory tours" );
        }
            
        logger.info("Work based subtours Tours:");
        if ( atWorkSubtourArrayList.size() > 0 ) {
            for ( Tour tour : atWorkSubtourArrayList ) {
                tour.logEntireTourObject( logger, modelStructure  );
            }
        }
        else {
            logger.info ( "     No work based subtours" );
        }
        
        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    public byte getMaxTourId(){
        return maxTourId;
    }
    
    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst() {
		return pAnalyst;
	}

    // guojy: added for M. Gucwa's research on automated vehicles
	public void setPAnalyst(int pAnalyst) {
		this.pAnalyst = pAnalyst;
	}

	public int getPersPecasOcc() {
		return persPecasOcc;
	}


	public void setPersPecasOcc(int PecasOcc) {
		this.persPecasOcc = (byte) PecasOcc;
	}

	public float getWorkLocationLogsum() {
		return workLocationLogsum;
	}


	public void setWorkLocationLogsum(float workLocationLogsum) {
		this.workLocationLogsum = workLocationLogsum;
	}


	public float getSchoolLocationLogsum() {
		return schoolLocationLogsum;
	}


	public void setSchoolLocationLogsum(float schoolLocationLogsum) {
		this.schoolLocationLogsum = schoolLocationLogsum;
	}

	public enum EmployStatus {
        nul,
        FULL_TIME,
        PART_TIME,
        NOT_EMPLOYED,
        UNDER16
    }
    
    public enum StudentStatus {
    	nul,
    	STUDENT_HIGH_SCHOOL_OR_LESS,
    	STUDENT_COLLEGE_OR_HIGHER,
    	NON_STUDENT
    }


    public enum PersonType {
        nul,
        FT_worker_age_16plus,
        PT_worker_nonstudent_age_16plus,
        University_student,
        Nonworker_nonstudent_age_16_64,
        Nonworker_nonstudent_age_65plus,
        Student_age_16_19_not_FT_wrkr_or_univ_stud,
        Student_age_6_15_schpred,
        Preschool_under_age_6
    }

    public float getSampleRate() {
 		return sampleRate;
 	}

 	public void setSampleRate(float sampleRate) {
 		this.sampleRate = sampleRate;
 	}

}
