package com.pb.models.ctramp;

import org.apache.log4j.Logger;
import com.pb.models.ctramp.jppf.CtrampApplication;


public class Tour implements java.io.Serializable {
    
    private Person perObj;
    private Household hhObj;

    private byte tourCategoryIndex;
    private byte tourPurposeIndex;
    private String tourPurpose;

    // use this array to hold personNum (i.e. index values for Household.persons array) for persons in tour.
    // for individual tour types, this array is null.
    // for joint tours, there will be an entry for each participating person.
    private byte[] personNumArray;

    // alternative number chosen by the joint tour composition model ( 1=adults, 2=children, 3=mixed ).
    private byte jointTourComposition;

    private byte tourId;
    private byte personTourId;
    private short tourOrigTaz;
    private short tourDestTaz;
    private byte tourOrigWalkSubzone;
    private byte tourDestWalkSubzone;
    private byte tourStartHour;
    private byte tourEndHour;
    private byte tourMode;
    private byte subtourFreqChoice;
    private short tourParkTaz;
    private float destinationChoiceLogsum;
    
    private float[] tourModalProbabilities;
    private float[] tourModalUtilities;
    
    private byte stopFreqChoice;
    private Stop[] outboundStops;
    private Stop[] inboundStops;

    //added by JEF to track half-hour departure/arrival periods
    private byte departPeriod;
    private byte arrivePeriod;
    private int parentTourId; //for at-work subtours
    
    private boolean useOwnedAV;
    
    private float sampleRate;

 	// this constructor used for individual mandatory tour creation
    public Tour( Person perObj, int tourId ) {
        
        hhObj = perObj.getHouseholdObject();
        this.perObj = perObj;
        this.personTourId = perObj.getMaxTourId();
        this.tourId = (byte)tourId;
        tourCategoryIndex = ModelStructure.MANDATORY_CATEGORY_INDEX;
        
        if(perObj!=null)
        	sampleRate = perObj.getSampleRate();

    }

    // this constructor used to create a temporary tour object for mandatory mode choice logsum calculation in usual work/school location where a tour doesn't yet exist.
    public Tour(Person perObj, String tourPurpose){
        hhObj = perObj.getHouseholdObject();
    	this.perObj      = perObj;
    	this.tourPurpose = tourPurpose;
        tourId = -1;
        tourCategoryIndex = ModelStructure.MANDATORY_CATEGORY_INDEX;
        if(perObj!=null)
        	sampleRate = perObj.getSampleRate();

    }

    // this constructor used for joint tour creation
    public Tour( Household hhObj, ModelStructure modelStructure, int purposeIndex, String tourPurpose, byte tourCategoryIndex ) {
        this.hhObj = hhObj;
        this.tourPurpose = tourPurpose;
        tourPurposeIndex = (byte)purposeIndex;
        modelStructure.setSegmentedIndexPurpose( tourPurposeIndex, tourPurpose );
        modelStructure.setSegmentedPurposeIndex( tourPurpose, tourPurposeIndex );
        this.tourCategoryIndex = tourCategoryIndex;
        if(hhObj!=null)
        	sampleRate = hhObj.getSampleRate();
 
    }

    // this constructor also used for joint tour creation (JEF)
    public Tour( Household hhObj,int tourId ) {
        this.hhObj = hhObj;
        this.perObj = null;
        this.personTourId = (byte) tourId;
        this.tourId = (byte) tourId;
        tourCategoryIndex = ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX;
        if(hhObj!=null)
        	sampleRate = hhObj.getSampleRate();

    }
    // this constructor used for individual non-mandatory or at-work subtour creation
    public Tour( int id, Household hhObj, Person persObj, ModelStructure modelStructure, int purposeIndex, String tourPurpose, byte tourCategoryIndex ) {
        
        this.hhObj = hhObj;
        this.perObj = persObj;
        this.tourId = (byte)id;
        //guojy: compute and store parent (work) tour index (applies if this is an at-work subtour)
        this.parentTourId = (id / 10) - 1;

        this.personTourId = perObj.getMaxTourId();
        tourPurposeIndex = (byte)purposeIndex;
        this.tourPurpose = tourPurpose;
        modelStructure.setSegmentedIndexPurpose( tourPurposeIndex, tourPurpose );
        modelStructure.setSegmentedPurposeIndex( tourPurpose, tourPurposeIndex );
        this.tourCategoryIndex = tourCategoryIndex;
        if(hhObj!=null)
        	sampleRate = hhObj.getSampleRate();
    }

    /**
	 * @param tourCategoryIndex the tourCategoryIndex to set
	 */
	public void setTourCategoryIndex(byte tourCategoryIndex) {
		this.tourCategoryIndex = tourCategoryIndex;
	}

	/**
 	 * @return the parentTourId
 	 */
 	public int getParentTourId() {
 		return parentTourId;
 	}

 	/**
 	 * @param parentTourId the parentTourId to set
 	 */
 	public void setParentTourId(int parentTourId) {
 		this.parentTourId = parentTourId;
 	}


    public Person getPersonObject() {
        return perObj;
    }

    public void setPersonObject( Person p ) {
        perObj = p;
    }

    public void setPersonNumArray( byte[] personNums ) {
        personNumArray = personNums;
    }

    public byte[] getPersonNumArray() {
        return personNumArray;
    }

    public boolean getPersonInJointTour( Person person ) {
        boolean inTour = false;
        for ( int num : personNumArray ){
            if ( person.getPersonNum() == num ){
                inTour = true;
                break;
            }
        }
        return inTour;
    }
    
    public void setJointTourComposition ( int compositionAlternative ){
        jointTourComposition = (byte)compositionAlternative;
    }

    public int getJointTourComposition (){
        return jointTourComposition;
    }

    public void setTourPurpose ( String name ) {
        tourPurpose = name;
    }

    public byte getTourCategoryIndex() {
        return tourCategoryIndex;
    }

    public String getTourPurpose() {
        return tourPurpose;
    }

    public boolean getTourCategoryIsMandatory() {
        return tourCategoryIndex == ModelStructure.MANDATORY_CATEGORY_INDEX;
    }

    public boolean getTourCategoryIsAtWork() {
        return tourCategoryIndex == ModelStructure.AT_WORK_CATEGORY_INDEX;
    }

    public boolean getTourCategoryIsJointNonMandatory() {
        return tourCategoryIndex == ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX;
    }

    public boolean getTourCategoryIsIndivNonMandatory() {
        return tourCategoryIndex == ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY_INDEX;
    }

    public String getTourPrimaryPurpose() {
        int index = tourPurpose.indexOf('_');
        if ( index < 0 )
            return tourPurpose;
        else
            return tourPurpose.substring(0,index);
    }

    public int getTourPurposeIndex() {
        return tourPurposeIndex;
    }

    public int getTourModeChoice() {
        return tourMode;
    }


    //TODO: probably need to add a setter method so the project specific code can
    // set the mode alternatives that are SOV, rather than have them hard-coded as they are.
    public void setTourId(int id){
        tourId = (byte)id;
    }

    public void setTourOrigTaz( int origTaz ) {
        tourOrigTaz = (short)origTaz;
    }

    public void setTourDestTaz( int destTaz ) {
        tourDestTaz = (short)destTaz;
    }

    public void setTourOrigWalkSubzone( int subzone ) {
        tourOrigWalkSubzone = (byte)subzone;
    }

    public void setTourDestWalkSubzone( int subzone ) {
        tourDestWalkSubzone = (byte)subzone;
    }

    public void setTourStartHour( int startHour ) {
        tourStartHour = (byte)startHour;
    }

    public void setTourEndHour( int endHour ) {
        tourEndHour = (byte)endHour;
    }

    /**
	 * @return the departPeriod
	 */
	public byte getDepartPeriod() {
		return departPeriod;
	}

	/**
	 * @param departPeriod the departPeriod to set
	 */
	public void setDepartPeriod(byte departPeriod) {
		this.departPeriod = departPeriod;
	}

	/**
	 * @return the arrivePeriod
	 */
	public byte getArrivePeriod() {
		return arrivePeriod;
	}

	/**
	 * @param arrivePeriod the arrivePeriod to set
	 */
	public void setArrivePeriod(byte arrivePeriod) {
		this.arrivePeriod = arrivePeriod;
	}

	public void setTourModeChoice( int modeIndex ) {
        tourMode = (byte)modeIndex;
    }
    
    public void setTourParkTaz( int parkTaz ){
        tourParkTaz = (short)parkTaz;
    }
    

    // methods DMU will use to get info from household object

    public int getTourOrigTaz() {
        return tourOrigTaz;
    }

    public int getTourDestTaz() {
        return tourDestTaz;
    }

    public int getTourOrigWalkSubzone() {
        return tourOrigWalkSubzone;
    }

    public int getTourDestWalkSubzone() {
        return tourDestWalkSubzone;
    }

    public int getTourStartHour() {
        return tourStartHour;
    }

    public int getTourEndHour() {
        return tourEndHour;
    }

    public int getTourParkTaz(){
        return tourParkTaz;
    }



    public int getHhId() {
        return hhObj.getHhId();
    }

    public int getHhTaz() {
        return hhObj.getHhTaz();
    }

    public int getTourId() {
        return tourId;
    }

    public int getWorkTourIndexFromSubtourId( int subtourId ) {
        // when subtour was created, it's tour id was set to 10*(work tour index + 1) + at-work subtour index
        return (subtourId / 10) - 1;
    }

    public int getSubtourIdFromIndices(int workTourIndex, int subtourIndex ) {
        // this is used to create the subtour, it's tour id was set to 10*(work tour index + 1) + at-work subtour index
        return 10*(workTourIndex+1) + subtourIndex;	
    }
    
    public void setSubtourFreqChoice( int choice ) {
        subtourFreqChoice = (byte)choice;
    }

    public int getSubtourFreqChoice() {
        return subtourFreqChoice;
    }

    public void setStopFreqChoice ( int chosenAlt ){
        stopFreqChoice = (byte)chosenAlt;
    }

    public int getStopFreqChoice (){
        return stopFreqChoice;
    }

    public void createOutboundStops( ModelStructure modelStructure, String[] stopOrigPurposes, String[] stopDestPurposes ){
        outboundStops = new Stop[stopOrigPurposes.length];
        for (int i = 0; i < stopOrigPurposes.length; i++) {
            int origPurpIndex = modelStructure.getPrimaryIndexForPurpose( stopOrigPurposes[i] );
            int destPurpIndex = modelStructure.getPrimaryIndexForPurpose( stopDestPurposes[i] );
            outboundStops[i] = new Stop( this, origPurpIndex, destPurpIndex, i, false );
        }
    }

    public void createInboundStops( ModelStructure modelStructure, String[] stopOrigPurposes, String[] stopDestPurposes ){
        //needs outbound stops to be created first to get id numbering correct
        
        inboundStops = new Stop[stopOrigPurposes.length];
        for (int i = 0; i < stopOrigPurposes.length; i++) {
            int origPurpIndex = modelStructure.getPrimaryIndexForPurpose( stopOrigPurposes[i] );
            int destPurpIndex = modelStructure.getPrimaryIndexForPurpose( stopDestPurposes[i] );
            inboundStops[i] = new Stop( this, origPurpIndex, destPurpIndex, i, true );
        }
    }

    /**
     * Create a Stop object to represent a half-tour where no stops were generated.  The id for the stop is set
     * to -1 so that trips for half-tours without stops can be distinguished in the output trip files from
     * turs that have stops.  Trips for these tours come from stop objects with ids in the range 0,...,3.
     * 
     * @param origPurp is "home" or "work" (for at-work subtours) if outbound, or the primary tour purpose if inbound
     * @param destPurp is "home" or "work" (for at-work subtours) if inbound, or the primary tour purpose if outbound
     * @param inbound is true if the half-tour is inbound, or false if outbound.
     * @return the created Stop object.
     */
    public Stop createStop( ModelStructure modelStructure, String origPurp, String destPurp, boolean inbound, boolean subtour ) {
        Stop stop = null;
        int id = -1;
        if ( inbound ) {
            int origPurpIndex = modelStructure.getPrimaryIndexForPurpose( origPurp );
            int destPurpIndex = subtour ? -2 : -1;
            inboundStops = new Stop[1];
            inboundStops[0] = new Stop( this, origPurpIndex, destPurpIndex, id, inbound );
            stop = inboundStops[0]; 
        }
        else {
            int origPurpIndex = subtour ? -2 : -1;
            int destPurpIndex = modelStructure.getPrimaryIndexForPurpose( destPurp );
            outboundStops = new Stop[1];
            outboundStops[0] = new Stop( this, origPurpIndex, destPurpIndex, id, inbound );
            stop = outboundStops[0]; 
        }
        return stop;
    }
    
    public int getNumOutboundStops() {
        if ( outboundStops == null )
            return 0;
        else
            return outboundStops.length - 1;
    }

    public int getNumInboundStops() {
        if ( inboundStops == null )
            return 0;
        else
            return inboundStops.length - 1;
    }

    public Stop[] getOutboundStops() {
        return outboundStops;
    }

    public Stop[] getInboundStops() {
        return inboundStops;
    }

    public void clearStopModelResults() {
        stopFreqChoice = 0;
        
        outboundStops = null;
        inboundStops = null;
    }

    

    
    

    public String getTourWindow( String purposeAbbreviation ) {
        String returnString = String.format("         %5s:   |", purposeAbbreviation );
        byte[] windows = perObj.getTimeWindows();
        for ( int i=0; i < windows.length; i++ ) {
            int index = i + CtrampApplication.START_HOUR;
            String tempString = String.format("%s", index >= tourStartHour && index <= tourEndHour ? purposeAbbreviation : "    " );
            if ( tempString.length() == 2 || tempString.length() == 3 )
                tempString = " " + tempString;
            returnString += String.format("%4s|", tempString );
        }
        return returnString;
    }
    
    
    public void logTourObject( Logger logger, int totalChars ) {
        
        String personNumArrayString = "-";
        if ( personNumArray != null ) {
            personNumArrayString = "[ ";
            personNumArrayString += String.format("%d", personNumArray[0]);
            for (int i=1; i < personNumArray.length; i++)
                personNumArrayString += String.format(", %d", personNumArray[i]);
            personNumArrayString += " ]";
        }

        Household.logHelper( logger, "tourId: ", tourId, totalChars );
        Household.logHelper( logger, "tourCategoryIndex: ", tourCategoryIndex, totalChars );
        Household.logHelper( logger, "tourCategoryName: ", ModelStructure.TOUR_CATEGORY_LABELS[tourCategoryIndex], totalChars );
        Household.logHelper( logger, "tourPurpose: ", tourPurpose, totalChars );
        Household.logHelper( logger, "tourPurposeIndex: ", tourPurposeIndex, totalChars );
        Household.logHelper( logger, "personNumArray: ", personNumArrayString, totalChars );
        Household.logHelper( logger, "jointTourComposition: ", jointTourComposition, totalChars );
        Household.logHelper( logger, "tourOrigTaz: ", tourOrigTaz, totalChars );
        Household.logHelper( logger, "tourDestTaz: ", tourDestTaz, totalChars );
        Household.logHelper( logger, "tourOrigWalkSubzone: ", tourOrigWalkSubzone, totalChars );
        Household.logHelper( logger, "tourDestWalkSubzone: ", tourDestWalkSubzone, totalChars );
        Household.logHelper( logger, "tourStartHour: ", tourStartHour, totalChars );
        Household.logHelper( logger, "tourEndHour: ", tourEndHour, totalChars );
        Household.logHelper( logger, "tourMode: ", tourMode, totalChars );
        Household.logHelper( logger, "stopFreqChoice: ", stopFreqChoice, totalChars );
        
        String tempString = String.format( "outboundStops[%s]:", outboundStops == null ? "" : String.valueOf(outboundStops.length) );
        logger.info( tempString );

        tempString = String.format( "inboundStops[%s]:", inboundStops == null ? "" : String.valueOf(inboundStops.length) );
        logger.info( tempString );

    }

    
    
    public void logEntireTourObject( Logger logger, ModelStructure modelStructure ) {
        
        int totalChars = 60;
        String separater = "";
        for (int i=0; i < totalChars; i++)
            separater += "-";

        
        String personNumArrayString = "-";
        if ( personNumArray != null ) {
            personNumArrayString = "[ ";
            personNumArrayString += String.format("%d", personNumArray[0]);
            for (int i=1; i < personNumArray.length; i++)
                personNumArrayString += String.format(", %d", personNumArray[i]);
            personNumArrayString += " ]";
        }

        Household.logHelper( logger, "tourId: ", tourId, totalChars );
        Household.logHelper( logger, "tourCategoryIndex: ", tourCategoryIndex, totalChars );
        Household.logHelper( logger, "tourCategoryName: ", ModelStructure.TOUR_CATEGORY_LABELS[tourCategoryIndex], totalChars );
        Household.logHelper( logger, "tourPurpose: ", tourPurpose, totalChars );
        Household.logHelper( logger, "tourPurposeIndex: ", tourPurposeIndex, totalChars );
        Household.logHelper( logger, "personNumArray: ", personNumArrayString, totalChars );
        Household.logHelper( logger, "jointTourComposition: ", jointTourComposition, totalChars );
        Household.logHelper( logger, "tourOrigTaz: ", tourOrigTaz, totalChars );
        Household.logHelper( logger, "tourDestTaz: ", tourDestTaz, totalChars );
        Household.logHelper( logger, "tourOrigWalkSubzone: ", tourOrigWalkSubzone, totalChars );
        Household.logHelper( logger, "tourDestWalkSubzone: ", tourDestWalkSubzone, totalChars );
        Household.logHelper( logger, "tourStartHour: ", tourStartHour, totalChars );
        Household.logHelper( logger, "tourEndHour: ", tourEndHour, totalChars );
        Household.logHelper( logger, "tourMode: ", tourMode, totalChars );
        Household.logHelper( logger, "stopFreqChoice: ", stopFreqChoice, totalChars );
        
        if ( outboundStops != null ) {
            logger.info("Outbound Stops:");
            if ( outboundStops.length > 0 ) {
                for ( int i=0; i < outboundStops.length; i++ )
                    outboundStops[i].logStopObject( logger, totalChars, modelStructure );
            }
            else {
                logger.info( "     No outbound stops" );
            }
        }
        else {
            logger.info( "     No outbound stops" );
        }
        
        if ( inboundStops != null ) {
            logger.info("Inbound Stops:");
            if ( inboundStops.length > 0 ) {
                for ( int i=0; i < inboundStops.length; i++ )
                    inboundStops[i].logStopObject( logger, totalChars, modelStructure );
                }
            else {
                logger.info( "     No inbound stops" );
            }
        }
        else {
            logger.info( "     No inbound stops" );
        }
        
        logger.info(separater);
        logger.info( "" );
        logger.info( "" );

    }

    
        
    public void setTourModalUtilities( float[] utils ) {
        tourModalUtilities = utils;
    }

    public float[] getTourModalUtilities() {
        return tourModalUtilities;
    }

    public void setTourModalProbabilities( float[] probs ) {
        tourModalProbabilities = probs;
    }

    public float[] getTourModalProbabilities() {
        return tourModalProbabilities;
    }

	public boolean getUseOwnedAV() {
		return useOwnedAV;
	}

	public void setUseOwnedAV(boolean useOwnedAV) {
		this.useOwnedAV = useOwnedAV;
	}

	public float getDestinationChoiceLogsum() {
		return destinationChoiceLogsum;
	}

	public void setDestinationChoiceLogsum(float destinationChoiceLogsum) {
		this.destinationChoiceLogsum = destinationChoiceLogsum;
	}
	public float getSampleRate() {
		return sampleRate;
	}

	public void setSampleRate(float sampleRate) {
		this.sampleRate = sampleRate;
	}


    
}
