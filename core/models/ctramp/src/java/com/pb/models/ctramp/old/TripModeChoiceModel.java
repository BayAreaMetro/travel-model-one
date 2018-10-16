package com.pb.models.ctramp.old;

import java.util.ResourceBundle;
import java.util.Random;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Stop;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.TripModeChoiceDMU;

import org.apache.log4j.Logger;

public class TripModeChoiceModel {
    
    public Logger logger = Logger.getLogger(TripModeChoiceModel.class);
    

    static final int MC_DATA_SHEET = 0;


    // A ChoiceModelApplication object and modeAltsAvailable[] is needed for each purpose
    ChoiceModelApplication mcModel[];
    TripModeChoiceDMU mcDmuObject;

    String tourCategory;

    String[][] modeAltNames;
    boolean[][] modeAltsAvailable;
    int[][] modeAltsSample;


    public TripModeChoiceModel( String uecFileName, ResourceBundle resourceBundle, ModelStructure modelStructure, TripModeChoiceDMU mcDmuObject, String tourCategory ){

        this.mcDmuObject =  mcDmuObject;
        this.tourCategory =  tourCategory;
        setupChoiceModelApplicationArray( uecFileName, resourceBundle, modelStructure, tourCategory );
    }



    private void setupChoiceModelApplicationArray( String uecFileName, ResourceBundle resourceBundle, ModelStructure modelStructure, String tourCategory ) {

        // get the number of purposes and declare the array dimension to be this size.
        String[] tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
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
            		         ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), mcDmuObject.getClass() );

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


    public void setDmuIndexValuesForTripModeChoice ( Person person, Tour tour, Stop stop ) {

        // get the Household object for this person
        Household hhObj = person.getHouseholdObject();

        // update the MC and DC dmuObjects for this person
        mcDmuObject.setHouseholdObject( hhObj );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        
        mcDmuObject.setDmuIndexValues( hhObj.getHhId(), stop.getOrig(), stop.getDest() );

    }


    public int getModeChoice ( Person person, Tour tour, Stop stop, int purposeIndex ) {

        // set index values for the mcDmuObject.
        setDmuIndexValuesForTripModeChoice ( person, tour, stop );

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

