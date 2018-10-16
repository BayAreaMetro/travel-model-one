package com.pb.models.ctramp;

import org.apache.log4j.Logger;

import java.util.*;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.common.calculator.IndexValues;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 11, 2008
 * Time: 9:25:30 AM
 * To change this template use File | Settings | File Templates.
 */
public class JointTourFrequencyModel {


    protected static Logger logger = Logger.getLogger( JointTourFrequencyModel.class );
    

    public static final String PROPERTIES_UEC_JOINT_TOUR_FREQUENCY  = "UecFile.JointTourFrequency";


    // all the other page numbers are passed in
    public static final int UEC_DATA_PAGE = 0;
    public static final int UEC_JOINT_TOUR_FREQ_MODEL_PAGE = 1;
    public static final int UEC_JOINT_TOUR_COMPOSITION_MODEL_PAGE = 2;
    public static final int UEC_JOINT_TOUR_PARTICIPATION_MODEL_PAGE = 3;

    public static final int JOINT_TOUR_COMPOSITION_ADULTS = 1;
    public static final int JOINT_TOUR_COMPOSITION_CHILDREN = 2;
    public static final int JOINT_TOUR_COMPOSITION_MIXED = 3;

    public static String[] JOINT_TOUR_COMPOSITION_NAMES = { "", "adult", "child", "mixed" };

    // DMU for the UEC
    protected JointTourFrequencyDMU dmuObject;

    // model structure to compare the .properties time of day with the UECs
    protected ModelStructure modelStructure;
    protected TazDataIf tazDataManager;

    protected ChoiceModelApplication jointTourFrequencyModel;
    protected ChoiceModelApplication jointTourComposition;
    protected ChoiceModelApplication jointTourParticipation;

    protected int[][] jointTourChoiceFreq;
    protected int[] invalidCount = new int[5];

    boolean[] participationAvailability;
    int[] participationSample;

    TreeMap<String, Integer> partySizeFreq = new TreeMap<String, Integer>();

    private String shoppingPurposeString;
    private String eatOutPurposeString;
    private String maintPurposeString;
    private String discrPurposeString;
    private String socialPurposeString;

    private int shoppingPurposeIndex;
    private int eatOutPurposeIndex;
    private int maintPurposeIndex;
    private int discrPurposeIndex;
    private int socialPurposeIndex;

    
    public JointTourFrequencyModel( String projectDirectory, JointTourFrequencyDMU dmu, ModelStructure modelStructure, TazDataIf tazDataManager ){

        dmuObject = dmu;

        // set the model structure
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;

        shoppingPurposeString = modelStructure.getShoppingPurposeName();
        shoppingPurposeIndex = modelStructure.getDcModelPurposeIndex( shoppingPurposeString );
        eatOutPurposeString = modelStructure.getEatOutPurposeName();
        eatOutPurposeIndex = modelStructure.getDcModelPurposeIndex( eatOutPurposeString );
        maintPurposeString = modelStructure.getOthMaintPurposeName();
        maintPurposeIndex = modelStructure.getDcModelPurposeIndex( maintPurposeString );
        discrPurposeString = modelStructure.getOthDiscrPurposeName();
        discrPurposeIndex = modelStructure.getDcModelPurposeIndex( discrPurposeString );
        socialPurposeString = modelStructure.getSocialPurposeName();
        socialPurposeIndex = modelStructure.getSoaUecIndexForPurpose(socialPurposeString);

    }


    public void setUpModels( ResourceBundle resourceBundle, String projectDirectory ){

        String uecFileName = resourceBundle.getString( PROPERTIES_UEC_JOINT_TOUR_FREQUENCY );
        uecFileName = projectDirectory + uecFileName;


        // set up the models
        jointTourFrequencyModel = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_FREQ_MODEL_PAGE, UEC_DATA_PAGE,
                ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass());

        jointTourComposition = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_COMPOSITION_MODEL_PAGE, UEC_DATA_PAGE,
                ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass());

        jointTourParticipation = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_PARTICIPATION_MODEL_PAGE, UEC_DATA_PAGE,
                ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass());
        int numAlts = jointTourParticipation.getNumberOfAlternatives();
        participationAvailability = new boolean[numAlts+1];
        Arrays.fill( participationAvailability, true );
        participationSample = new int[numAlts+1];
        Arrays.fill( participationSample, 1 );


        jointTourChoiceFreq = new int[jointTourFrequencyModel.getNumberOfAlternatives()+1][jointTourComposition.getNumberOfAlternatives()+1];

    }


    public void applyModel(HouseholdDataManagerIf householdDataManager){

        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        int tenPercent = (int)( 0.10*householdArray.length );

        // loop through households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];

            try {
                applyJointTourFrequencyChoice( household );
            }
            catch ( Exception e ) {
                logger.error( String.format( "error joint tour frequency choice model for i=%d, hhId=%d.", i, household.getHhId() ));
                throw new RuntimeException();
            }


            if ( i % tenPercent == 0 )
                logger.info ( String.format("joint tour frequency choice complete for %.0f%% of household, %d.", (100.0*i/householdArray.length), i ) );

        }

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setJtfRandomCount();

    }



    private void applyJointTourFrequencyChoice( Household household ) {

        // joint tour frequency choice is not applied to a household unless it has:
        // 2 or more persons, each with at least one out-of home activity, and at least 1 of the persons not a pre-schooler.

        // if it's not a valid household for joint tour frequency, keep track of count for loogging later, and return.
        int validIndex = household.getValidHouseholdForJointTourFrequencyModel();
        if ( validIndex != 1 ) {
            invalidCount[validIndex]++;
            return;
        }

        // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        dmuObject.setHouseholdObject(household);

        // get and set the area type indicaters for the hh taz
        int hhTaz = household.getHhTaz();

        int urban = tazDataManager.getZoneIsUrban( hhTaz );
        dmuObject.setHomeTazIsUrban( urban );

        int suburban = tazDataManager.getZoneIsSuburban( hhTaz );
        dmuObject.setHomeTazIsSuburban( suburban );
        dmuObject.setWalkRetailAccessibility(tazDataManager.getNonMotorizedRetailAccessibity()[hhTaz]);

        boolean[] availability = new boolean[jointTourFrequencyModel.getNumberOfAlternatives()+1];
        int[] sample = new int[jointTourFrequencyModel.getNumberOfAlternatives()+1];
        Arrays.fill(availability, true);
        Arrays.fill(sample, 1);

        IndexValues index = dmuObject.getDmuIndexValues();
        //if ( household.getHhId() == 306640 )
        //    index.setDebug( true );

        jointTourFrequencyModel.computeUtilities ( dmuObject, index, availability, sample );

        Random hhRandom = household.getHhRandom();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosenFreqAlt = -1;
        if ( jointTourFrequencyModel.getAvailabilityCount() > 0 ) {
            chosenFreqAlt = jointTourFrequencyModel.getChoiceResult( rn );
            household.setJointTourFreqResult( chosenFreqAlt, jointTourFrequencyModel.getAlternativeNames()[chosenFreqAlt-1] );
        }
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available joint tour frequency alternatives to choose from in choiceModelApplication.", household.getHhId() ) );
            throw new RuntimeException();
        }


        createJointTours ( household, chosenFreqAlt );

        // can skip composition choice if chosen alt is 1 -- no joint tours; just count the number of times alt 1 is chosen
        // in tour frequency.
        if ( chosenFreqAlt == 1 ) {

            jointTourChoiceFreq[0][0]++;

        }
        else {

            Tour[] jointTours = household.getJointTourArray();
            for ( int i=0; i < jointTours.length; i++ ) {

                dmuObject.setTourObject( jointTours[i] );

                jointTourComposition.computeUtilities ( dmuObject, index, availability, sample );

                hhRandom = household.getHhRandom();
                rn = hhRandom.nextDouble();

                // if the choice model has at least one available alternative, make choice.
                int chosenComposition = -1;
                if ( jointTourComposition.getAvailabilityCount() > 0 )
                    chosenComposition = jointTourComposition.getChoiceResult( rn );
                else {
                    logger.error ( String.format( "Exception caught for HHID=%d, joint tour i=%d, no available joint tour composition alternatives to choose from in choiceModelApplication.", household.getHhId(), i ) );
                    throw new RuntimeException();
                }



                jointTours[i].setJointTourComposition( chosenComposition );
                jointTourChoiceFreq[chosenFreqAlt][chosenComposition]++;


                jointTourParticipation( jointTours[i] );

            }

        }

    }


    private void jointTourParticipation( Tour jointTour ) {

        // get the Household object for this joint tour
        Household hh = dmuObject.getHouseholdObject();

        // get the array of Person objects for this hh
        Person[] persons = hh.getPersons();

        // define an ArrayList to hold indices of person objects participating in the joint tour
        ArrayList<Byte> jointTourPersonList = null;


        // make sure each joint tour has a valid composition before going to the next one.
        boolean validParty = false;


        int adults = 0;
        int children = 0;

        while ( !validParty ) {

            adults = 0;
            children = 0;

            jointTourPersonList = new ArrayList<Byte>();


            for (int p = 1; p < persons.length; p++) {

                jointTour.setPersonObject( persons[p] );

                // if person type is inconsistent with tour composition, person's participation is by definition no,
                // so skip making the choice and go to next person
                switch ( jointTour.getJointTourComposition() ) {

                    // adults only in joint tour
                    case 1:
                        if ( persons[p].getPersonIsAdult() == 1 ) {
                            jointTourParticipation.computeUtilities ( dmuObject, dmuObject.getDmuIndexValues(), participationAvailability, participationSample );
                            Random hhRandom = hh.getHhRandom();
                            double rn = hhRandom.nextDouble();

                            // if the choice model has at least one available alternative, make choice.
                            int chosen = -1;
                            if ( jointTourParticipation.getAvailabilityCount() > 0 )
                                chosen = jointTourParticipation.getChoiceResult( rn );
                            else {
                                logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available adults only joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                                throw new RuntimeException();
                            }

                            // particpate is alternative 1, not participating is alternative 2.
                            if ( chosen == 1 ) {
                                jointTourPersonList.add((byte)p);
                                adults++;
                            }
                        }
                        break;

                    // children only in joint tour
                    case 2:
                        if ( persons[p].getPersonIsAdult() == 0 ) {
                            jointTourParticipation.computeUtilities ( dmuObject, dmuObject.getDmuIndexValues(), participationAvailability, participationSample );
                            Random hhRandom = hh.getHhRandom();
                            double rn = hhRandom.nextDouble();

                            // if the choice model has at least one available alternative, make choice.
                            int chosen = -1;
                            if ( jointTourParticipation.getAvailabilityCount() > 0 )
                                chosen = jointTourParticipation.getChoiceResult( rn );
                            else {
                                logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available children only joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                                throw new RuntimeException();
                            }

                            // particpate is alternative 1, not participating is alternative 2.
                            if ( chosen == 1 ) {
                                jointTourPersonList.add((byte)p);
                                children++;
                            }
                        }
                        break;

                    // mixed, adults and children in joint tour
                    case 3:
                        IndexValues index = dmuObject.getDmuIndexValues();
                        //if ( hh.getHhId() == 306640 )
                        //    index.setDebug(true);
                        jointTourParticipation.computeUtilities ( dmuObject, index, participationAvailability, participationSample );
                        Random hhRandom = hh.getHhRandom();
                        double rn = hhRandom.nextDouble();

                        // if the choice model has at least one available alternative, make choice.
                        int chosen = -1;
                        if ( jointTourParticipation.getAvailabilityCount() > 0 )
                            chosen = jointTourParticipation.getChoiceResult( rn );
                        else {
                            logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available mixed adult/children joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                            throw new RuntimeException();
                        }
                            
                        // particpate is alternative 1, not participating is alternative 2.
                        if ( chosen == 1 ) {
                            jointTourPersonList.add((byte)p);
                            if ( persons[p].getPersonIsAdult() == 1 )
                                adults++;
                            else
                                children++;
                        }
                        break;

                }

            }


            // done with all persons, so see if the chosen participation is a valid composition, and if not, repeat the participation choice.
            switch ( jointTour.getJointTourComposition() ) {

                case 1:
                    if ( adults > 1 && children == 0 )
                        validParty = true;
                    break;

                case 2:
                    if ( adults == 0 && children > 1 )
                        validParty = true;
                    break;

                case 3:
                    if ( adults > 0 && children > 0 )
                        validParty = true;
                    break;

            }

        } // end while


        // create an array of person indices for participation in the tour
        byte[] personNums = new byte[jointTourPersonList.size()];
        for ( int i=0; i < personNums.length; i++ )
            personNums[i] = jointTourPersonList.get(i);
        jointTour.setPersonNumArray( personNums );



        // create a key to use for a frequency map for "JointTourPurpose_Composition_NumAdults_NumChildren"
        String key = String.format( "%s_%d_%d_%d", jointTour.getTourPurpose(), jointTour.getJointTourComposition(), adults, children );

        int value = 0;
        if ( partySizeFreq.containsKey( key ) )
            value = partySizeFreq.get( key );
        partySizeFreq.put( key, ++value );

    }




    /**
     * creates the tour objects in the Household object given the chosen joint tour frequency alternative.
     * @param chosenAlt
     */
    private void createJointTours ( Household household, int chosenAlt ) {
        Object[] t1Data = null;
        Object[] t2Data = null;

        switch ( chosenAlt ) {

            // no joint tours
            case 1:
                // call a method to create a joint tour array with zero elements.  A zero element array indicates a 0_tours choice was made.
                // as opposed to a null jointTours array which indicates that the household was not eligible to make any joint tours.
                break;

            // 1 joint shop tour
            case 2: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString}; break;
            // 1 joint maint tour
            case 3: t1Data = new Object[] {maintPurposeIndex,maintPurposeString}; break;
            // 1 joint eat tour
            case 4: t1Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString}; break;
            // 1 joint visit tour
            case 5: t1Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint disc tour
            case 6: t1Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;
            // 2 joint shop tour
            case 7: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString};
                    t2Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString}; break;
            // 1 joint shop tour and 1 joint maint tour
            case 8: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString};
                    t2Data = new Object[] {maintPurposeIndex,maintPurposeString}; break;
            // 1 joint shop tour and 1 joint eat tour
            case 9: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString};
                    t2Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString}; break;
            // 1 joint shop tour and 1 joint visit tour
            case 10: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint shop tour and 1 joint discr tour
            case 11: t1Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;
            // 2 joint maint tour
            case 12: t1Data = new Object[] {maintPurposeIndex,maintPurposeString};
                     t2Data = new Object[] {maintPurposeIndex,maintPurposeString}; break;
            // 1 joint maint tour and 1 joint eat tour
            case 13: t1Data = new Object[] {maintPurposeIndex,maintPurposeString};
                     t2Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString}; break;
            // 1 joint maint tour and 1 joint visit tour
            case 14: t1Data = new Object[] {maintPurposeIndex,maintPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint maint tour and 1 joint discr tour
            case 15: t1Data = new Object[] {maintPurposeIndex,maintPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;
            // 2 joint eat tour
            case 16: t1Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString};
                     t2Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString}; break;
            // 1 joint eat tour and 1 joint visit tour
            case 17: t1Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint eat tour and 1 joint discr tour
            case 18: t1Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;
            // 2 joint visit tour
            case 19: t1Data = new Object[] {socialPurposeIndex,socialPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint visit tour and 1 joint discr tour
            case 20: t1Data = new Object[] {socialPurposeIndex,socialPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;
            // 2 joint discr tour
            case 21: t1Data = new Object[] {discrPurposeIndex,discrPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;

        }

        //create tours
        if (t1Data == null) {
            household.createJointTourArray();
        } else{
            Tour t1 = new Tour( household, modelStructure, (Integer) t1Data[0], (String) t1Data[1], ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX );
            if (t2Data == null) {
                household.createJointTourArray(t1);
            } else {
                Tour t2 = new Tour( household, modelStructure, (Integer) t2Data[0], (String) t2Data[1], ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX );
                household.createJointTourArray(t1,t2);
            }
        }

    }


    /**
     * Logs the results of the model.
     *
     */
    public void logResults(){

        String[] altLabels = jointTourFrequencyModel.getAlternativeNames();

        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info("Joint Tour Frequency and Joint Tour Composition Model Results");


        logger.info(" ");
        logger.info ( String.format( "%-5s   %-20s   %8s   %8s   %8s   %8s", "alt", "alt name", "adult", "child", "mixed", "total" ) );


        // treat the first row of the table differently - no joint tours chosen and therefore no composition chosen.
        // so we just want to print the total households chhosing no joint tours in the "total" column.
        // later we'll add this total to the tanle total in the last row.
        String logString = String.format( "%-5d   %-20s", 1, altLabels[0] );
        for ( int j=0; j < 3; j++ )
            logString += String.format( "   %8s", "N/A" );
        logString += String.format( "   %8d", jointTourChoiceFreq[0][0] );
        logger.info ( logString );




        int[] columnTotals = new int[3];
        for ( int i=1; i < altLabels.length; i++ ) {

            logString = String.format( "%-5d   %-20s", (i+1), altLabels[i] );

            int rowTotal = 0;
            for ( int j=0; j < columnTotals.length; j++ ) {
                columnTotals[j] += jointTourChoiceFreq[i+1][j+1];
                rowTotal += jointTourChoiceFreq[i+1][j+1];
                logString += String.format( "   %8d", jointTourChoiceFreq[i+1][j+1] );
            }

            logString += String.format( "   %8d", rowTotal );
            logger.info ( logString );

        }

        int rowTotal = 0;
        logString = String.format( "%-5s   %-20s", "total", "" );
        for ( int j=0; j < columnTotals.length; j++ ) {
            rowTotal += columnTotals[j];
            logString += String.format( "   %8d", columnTotals[j] );
        }

        rowTotal += jointTourChoiceFreq[0][0];
        logString += String.format( "   %8d", rowTotal );
        logger.info ( logString );



        logger.info(" ");
        logger.info ( String.format( "Single person hhs could not produce joint tours: %d.", invalidCount[2] ) );
        logger.info ( String.format( "hhs with fewer than 2 persons leaving home could not produce joint tours: %d.", invalidCount[3] ) );
        logger.info ( String.format( "hhs with fewer than 1 non-preschool persons leaving home could not produce joint tours: %d.", invalidCount[4] ) );

        logger.info(" ");
        logger.info(" ");
        logger.info(" ");


        logger.info ( String.format( "%-5s   %-10s   %-10s   %10s   %10s   %10s", "N", "Purpose", "Type", "Adults", "Children", "Freq" ) );


        int count = 1;
        for ( String key : partySizeFreq.keySet() ) {

            int start = 0;
            int end = 0;
            int compIndex = 0;
            int adults = 0;
            int children = 0;
            String indexString = "";
            String purpose = "";

            start = 0;
            end = key.indexOf( '_', start );
            purpose = key.substring( start, end );

            start = end+1;
            end = key.indexOf( '_', start );
            indexString = key.substring( start, end );
            compIndex = Integer.parseInt ( indexString );

            start = end+1;
            end = key.indexOf( '_', start );
            indexString = key.substring( start, end );
            adults = Integer.parseInt ( indexString );

            start = end+1;
            indexString = key.substring( start );
            children = Integer.parseInt ( indexString );

            logger.info ( String.format( "%-5d   %-10s   %-10s   %10d   %10d   %10d", count++, purpose, JOINT_TOUR_COMPOSITION_NAMES[compIndex], adults, children, partySizeFreq.get(key) ) );
        }


        logger.info(" ");
        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");

    }



}