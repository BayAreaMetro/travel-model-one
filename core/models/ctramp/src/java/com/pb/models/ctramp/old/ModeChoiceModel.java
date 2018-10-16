package com.pb.models.ctramp.old;

import java.util.HashMap;
import java.util.Random;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.calculator.IndexValues;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;

import org.apache.log4j.Logger;

public class ModeChoiceModel {
    
    public Logger logger = Logger.getLogger(ModeChoiceModel.class);
    

    static final int MC_DATA_SHEET = 0;


    // A MyChoiceModelApplication object and modeAltsAvailable[] is needed for each purpose
    ChoiceModelApplication mcModel[];
    ModeChoiceDMU mcDmuObject;

    String tourCategory;
    String[] tourPurposeList;

    String[][] modeAltNames;
    boolean[][] modeAltsAvailable;
    int[][] modeAltsSample;


    public ModeChoiceModel( String uecFileName, HashMap<String, String> propertyMap, ModelStructure modelStructure, ModeChoiceDMU mcDmuObject, String tourCategory ){

        this.mcDmuObject =  mcDmuObject;
        this.tourCategory =  tourCategory;
        setupChoiceModelApplicationArray( uecFileName, propertyMap, modelStructure, tourCategory );
    }



    private void setupChoiceModelApplicationArray( String uecFileName, HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory ) {

        // get the number of purposes and declare the array dimension to be this size.
        tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        int numPurposes = tourPurposeList.length;
        mcModel = new ChoiceModelApplication[numPurposes];

        // declare dimensions for the array of choice alternative availability by purpose and
        // set elements to true.
        modeAltNames = new String[numPurposes][];
        modeAltsAvailable = new boolean[numPurposes][];
        modeAltsSample = new int[numPurposes][];

        // for each purpose, create the MyChoiceModelApplication object and the availabilty array
        for (int p=0;p<numPurposes;++p) {
        	
        	// get the uec index
        	int uecIndex = modelStructure.getTourModeChoiceUecIndexForPurpose(tourPurposeList[p]);
        	
            mcModel[p] = new ChoiceModelApplication ( uecFileName, uecIndex, MC_DATA_SHEET,
                    propertyMap, mcDmuObject.getClass() );

            int numAlts = mcModel[p].getNumberOfAlternatives();
            modeAltsAvailable[p] = new boolean[numAlts+1];
            modeAltsSample[p] = new int[numAlts+1];

            // set the modeAltsAvailable array to true for all mode choice alternatives for each purpose
            for (int k=1; k <= numAlts; k++)
                    modeAltsAvailable[p][k] = true;

            // set the modeAltsSample array to 1 for all mode choice alternatives for each purpose
            for (int k=1; k <= numAlts; k++)
                    modeAltsSample[p][k] = 1;

            modeAltNames[p] = mcModel[p].getAlternativeNames();
            
        }

    }


    public void setPersonObjectForDmu ( Person person, String purposeName ) {

        // get the Household object for this person
        Household hhObj = person.getHouseholdObject();

        // make a Tour object for use by the MC DMU for work/school location choice
        Tour tourObj = new Tour( person, purposeName );

        // update the MC and DC dmuObjects for this person
        mcDmuObject.setHouseholdObject( hhObj );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tourObj );
        mcDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhWalkSubzone(), 0 );

    }


    public void setPersonObjectForDmu ( Tour tour, Person person, String purposeName ) {

        // get the Household object for this person
        Household hhObj = person.getHouseholdObject();

        // update the MC and DC dmuObjects for this person
        mcDmuObject.setHouseholdObject( hhObj );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        
        
        mcDmuObject.setDmuIndexValues( hhObj.getHhId(), tour.getTourOrigTaz(), 0 );

    }


    /**
     *
     * @param purposeIndex is the tour purpose index for the mode choice being applied
     * @param dest is the destination zone index for the mode choice being applied
     * @param subzone is the walk access subzone zone index for the mode choice being applied
     * @param startHour is the time at which the tour started
     * @param endHour is the time at which the tour ended
     * @return the logsum calculated over the mode choice alternatives specific to the other parameters.
     */
    public double getModeChoiceLogsum ( int purposeIndex, int dest, int subzone, int startHour, int endHour ) {

        // set the zone and walk subzone values for the mcDmuObject and calculate the logsum.
        mcDmuObject.setIndexDest( dest );
        mcDmuObject.setTourDestTaz( dest );
        mcDmuObject.setTourDestWalkSubzone( subzone );
        mcDmuObject.setTourStartHour( startHour );
        mcDmuObject.setTourEndHour( endHour );

        IndexValues index = mcDmuObject.getDmuIndexValues();

        Household household = mcDmuObject.getHouseholdObject();
        
        // apply sample of alternatives model for the work segment to which this worker belongs.
        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( household.getDebugChoiceModels() ) {

            Person person = mcDmuObject.getPersonObject();
            Tour tour = mcDmuObject.getTourObject();
            String purposeName = tourPurposeList[purposeIndex];
            
            String choiceModelDescription = "";
            String decisionMakerLabel = "";

            if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) ) {
                // null tour means the DC is a mandatory usual location choice
                choiceModelDescription = String.format ( "Usual Location Choice -- Mode Choice Logsum for: Category=%s, Purpose=%s, Orig=%d, OrigSubZ=%d, Dest=%d, DestSubZ=%d", tourCategory, purposeName, household.getHhTaz(), household.getHhWalkSubzone(), dest, subzone );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            else {
                choiceModelDescription = String.format ( "Destination Choice -- Mode Choice Logsum for: Category=%s, Purpose=%s, TourId=%d, Orig=%d, OrigSubZ=%d, Dest=%d, DestSubZ=%d", tourCategory, purposeName, tour.getTourId(), tour.getTourOrigTaz(), tour.getTourOrigWalkSubzone(), dest, subzone );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            
            mcModel[purposeIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }

        mcModel[purposeIndex].computeUtilities( mcDmuObject, index, modeAltsAvailable[purposeIndex], modeAltsSample[purposeIndex] );

        return mcModel[purposeIndex].getLogsum();

    }


    public void setDmuIndexValuesForModeChoice ( Person person, Tour tour ) {

        // get the Household object for this person
        Household hhObj = person.getHouseholdObject();

        // update the MC and DC dmuObjects for this person
        mcDmuObject.setHouseholdObject( hhObj );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setDmuIndexValues( hhObj.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

    }


    public int getModeChoice ( Person person, Tour tour, int purposeIndex ) {

        // set index values for the mcDmuObject.
        setDmuIndexValuesForModeChoice ( person, tour );


        Household household = mcDmuObject.getHouseholdObject();
        
        // apply sample of alternatives model for the work segment to which this worker belongs.
        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( household.getDebugChoiceModels() ) {

            String purposeName = tourPurposeList[purposeIndex];
            
            String choiceModelDescription = "";
            String decisionMakerLabel = "";

            choiceModelDescription = String.format ( "Mode Choice Model for: Category=%s, Purpose=%s, TourId=%d", tourCategory, purposeName, tour.getTourId() );
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            
            mcModel[purposeIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }

        mcModel[purposeIndex].computeUtilities( mcDmuObject, mcDmuObject.getDmuIndexValues(), modeAltsAvailable[purposeIndex], modeAltsSample[purposeIndex] );

        Random hhRandom = mcDmuObject.getHouseholdObject().getHhRandom();

        // if the choice model has at least one available alternative, make choice.
        int chosen;
        if ( mcModel[purposeIndex].getAvailabilityCount() > 0 )
            chosen = mcModel[purposeIndex].getChoiceResult( hhRandom.nextDouble() );
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available %s tour mode alternatives to choose from in choiceModelApplication.", tour.getHhId(), tourCategory ) );
            throw new RuntimeException();
        }
        return chosen;

    }


    public String[] getModeAltNames( int purposeIndex ) {
        return modeAltNames[purposeIndex];
    }
    
}

