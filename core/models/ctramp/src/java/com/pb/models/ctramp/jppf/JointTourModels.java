package com.pb.models.ctramp.jppf;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.net.UnknownHostException;
import java.util.*;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.JointTourFrequencyDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 11, 2008
 * Time: 9:25:30 AM
 * To change this template use File | Settings | File Templates.
 */
public class JointTourModels implements Serializable {


    private transient Logger logger = Logger.getLogger( JointTourModels.class );
    private transient Logger tourFreq = Logger.getLogger("tourFreq");
    

    private static final String PROPERTIES_UEC_JOINT_TOUR_FREQUENCY  = "UecFile.JointTourFrequency";


    // all the other page numbers are passed in
    private static final int UEC_DATA_PAGE = 0;
    private static final int UEC_JOINT_TOUR_FREQ_MODEL_PAGE = 1;
    private static final int UEC_JOINT_TOUR_COMPOSITION_MODEL_PAGE = 2;
    private static final int UEC_JOINT_TOUR_PARTICIPATION_MODEL_PAGE = 3;

//    private static final int JOINT_TOUR_COMPOSITION_ADULTS = 1;
//    private static final int JOINT_TOUR_COMPOSITION_CHILDREN = 2;
//    private static final int JOINT_TOUR_COMPOSITION_MIXED = 3;

    public static final String[] JOINT_TOUR_COMPOSITION_NAMES = { "", "adult", "child", "mixed" };


    // DMU for the UEC
    private JointTourFrequencyDMU dmuObject;

    // model structure to compare the .properties time of day with the UECs
    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;

    private ChoiceModelApplication jointTourFrequencyModel;
    private ChoiceModelApplication jointTourComposition;
    private ChoiceModelApplication jointTourParticipation;

    //protected int[][] jointTourChoiceFreq;
    private int[] invalidCount = new int[5];

    private String threadName = null;

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

    
    public JointTourModels( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ){

        // set the model structure
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;

        try {
            threadName = "[" + java.net.InetAddress.getLocalHost().getHostName() + ": " + Thread.currentThread().getName() + "]";
        } catch (UnknownHostException e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }
        
        
        setUpModels( propertyMap, dmuFactory );
    }


    public void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ){

        logger.info( String.format( "setting up %s tour frequency model on %s", ModelStructure.JOINT_NON_MANDATORY_CATEGORY, threadName ) );

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        String uecFileName = propertyMap.get( PROPERTIES_UEC_JOINT_TOUR_FREQUENCY );
        uecFileName = projectDirectory + uecFileName;

        
        dmuObject = dmuFactory.getJointTourFrequencyDMU();

        shoppingPurposeString = modelStructure.getShoppingPurposeName();
        shoppingPurposeIndex = modelStructure.getDcModelPurposeIndex( shoppingPurposeString );
        eatOutPurposeString = modelStructure.getEatOutPurposeName();
        eatOutPurposeIndex = modelStructure.getDcModelPurposeIndex( eatOutPurposeString );
        maintPurposeString = modelStructure.getOthMaintPurposeName();
        maintPurposeIndex = modelStructure.getDcModelPurposeIndex( maintPurposeString );
        discrPurposeString = modelStructure.getOthDiscrPurposeName();
        discrPurposeIndex = modelStructure.getDcModelPurposeIndex( discrPurposeString );
        socialPurposeString = modelStructure.getSocialPurposeName();
        socialPurposeIndex = modelStructure.getDcModelPurposeIndex(socialPurposeString);

        
        // set up the models
        jointTourFrequencyModel = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_FREQ_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject);
        jointTourComposition = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_COMPOSITION_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject);
        jointTourParticipation = new ChoiceModelApplication(uecFileName, UEC_JOINT_TOUR_PARTICIPATION_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject);

    }


    public void applyModel( Household household ) {

        try {
            
            // joint tour frequency choice is not applied to a household unless it has:
            // 2 or more persons, each with at least one out-of home activity, and at least 1 of the persons not a pre-schooler.

            Logger modelLogger = tourFreq;
            if ( household.getDebugChoiceModels() )
                household.logHouseholdObject( "Pre Joint Tour Frequency Choice HHID=" + household.getHhId() + " Object", modelLogger );
            
            
            // if it's not a valid household for joint tour frequency, keep track of count for logging later, and return.
            int validIndex = household.getValidHouseholdForJointTourFrequencyModel();
            if ( validIndex != 1 ) {
                invalidCount[validIndex]++;
                switch ( validIndex ) {
                    case 2: household.setJointTourFreqResult( -2, "-2_1 person" ); break;
                    case 3: household.setJointTourFreqResult( -3, "-3_< 2 travel" ); break;
                    case 4: household.setJointTourFreqResult( -4, "-4_only preschool travel" ); break;
                }
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

            IndexValues index = dmuObject.getDmuIndexValues();
            //if ( household.getHhId() == 306640 )
            //    index.setDebug( true );

            
            
            // write debug header
            String separator = "";
            String choiceModelDescription = "" ;
            String decisionMakerLabel = "";
            String loggingHeader = "";
            if( household.getDebugChoiceModels() ) {

                choiceModelDescription = String.format ( "Joint Non-Mandatory Tour Frequency Choice Model:" );
                decisionMakerLabel = String.format ( "HH=%d, hhSize=%d.", household.getHhId(), household.getHhSize() );
                
                jointTourFrequencyModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                    
                modelLogger.info(" ");
                loggingHeader = choiceModelDescription + " for " + decisionMakerLabel;
                for (int k=0; k < loggingHeader.length(); k++)
                    separator += "+";
                modelLogger.info( loggingHeader );
                modelLogger.info( separator );
                modelLogger.info( "" );
                modelLogger.info( "" );
            }
            
            jointTourFrequencyModel.computeUtilities ( dmuObject, index );

            // get the random number from the household
            Random random = household.getHhRandom();
            int randomCount = household.getHhRandomCount();
            double rn = random.nextDouble();


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

            
            // debug output
            if( household.getDebugChoiceModels() ){

                String[] altNames = jointTourFrequencyModel.getAlternativeNames();

                double[] utilities     = jointTourFrequencyModel.getUtilities();
                double[] probabilities = jointTourFrequencyModel.getProbabilities();

                modelLogger.info("HHID: " + household.getHhId()  + ", HHSize: " + household.getHhSize() );
                modelLogger.info("Alternative                 Utility       Probability           CumProb");
                modelLogger.info("------------------   --------------    --------------    --------------");

                double cumProb = 0.0;
                for( int k=0; k < altNames.length; k++ ){
                    cumProb += probabilities[k];
                    String altString = String.format( "%-3d %10s", k+1, altNames[k] );
                    modelLogger.info(String.format("%-15s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                }

                modelLogger.info(" ");
                String altString = String.format( "%-3d %10s", chosenFreqAlt, altNames[chosenFreqAlt-1] );
                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                modelLogger.info( separator );
                modelLogger.info("");
                modelLogger.info("");
                

                // write choice model alternative info to debug log file
                jointTourFrequencyModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                jointTourFrequencyModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosenFreqAlt );

                // write UEC calculation results to separate model specific log file
                jointTourFrequencyModel.logUECResults( modelLogger, loggingHeader );
                
            }


            createJointTours ( household, chosenFreqAlt );
            
            

            // can skip composition choice if chosen alt is 1 -- no joint tours; just count the number of times alt 1 is chosen
            // in tour frequency.
            if ( chosenFreqAlt > 1 ) {

                Tour[] jointTours = household.getJointTourArray();
                for ( int i=0; i < jointTours.length; i++ ) {

                    dmuObject.setTourObject( jointTours[i] );

                    if( household.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "Joint Tour Composition Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, hhSize=%d, tourId=%d.", household.getHhId(), household.getHhSize(), jointTours[i].getTourId() );
                        
                        jointTourComposition.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        loggingHeader = choiceModelDescription + " for " + decisionMakerLabel;
                        for (int k=0; k < loggingHeader.length(); k++)
                            separator += "+";
                        modelLogger.info( loggingHeader );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                    }
                    
                    
                    jointTourComposition.computeUtilities ( dmuObject, index );


                    // get the random number from the household
                    random = household.getHhRandom();
                    randomCount = household.getHhRandomCount();
                    rn = random.nextDouble();

                    
                    
                    // if the choice model has at least one available alternative, make choice.
                    int chosenComposition = -1;
                    if ( jointTourComposition.getAvailabilityCount() > 0 )
                        chosenComposition = jointTourComposition.getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught for HHID=%d, joint tour i=%d, no available joint tour composition alternatives to choose from in choiceModelApplication.", household.getHhId(), i ) );
                        throw new RuntimeException();
                    }



                    // debug output
                    if( household.getDebugChoiceModels() ){

                        String[] altNames = jointTourComposition.getAlternativeNames();

                        double[] utilities     = jointTourComposition.getUtilities();
                        double[] probabilities = jointTourComposition.getProbabilities();

                        modelLogger.info("HHID: " + household.getHhId() + ", HHSize: " + household.getHhSize() + ", tourId: " + jointTours[i].getTourId() );
                        modelLogger.info("Alternative                 Utility       Probability           CumProb");
                        modelLogger.info("------------------   --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for( int k=0; k < altNames.length; k++ ){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d %10s", k+1, altNames[k] );
                            modelLogger.info(String.format("%-15s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d %10s", chosenComposition, altNames[chosenComposition-1] );
                        modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");
                        

                        // write choice model alternative info to debug log file
                        jointTourComposition.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        jointTourComposition.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosenComposition );

                        // write UEC calculation results to separate model specific log file
                        jointTourComposition.logUECResults( modelLogger, loggingHeader );
                        
                    }


                    jointTours[i].setJointTourComposition( chosenComposition );
                    //jointTourChoiceFreq[chosenFreqAlt][chosenComposition]++;


                    jointTourParticipation( jointTours[i] );

                }

            }

        }
        catch ( Exception e ) {
            logger.error( String.format( "error joint tour choices model for hhId=%d.", household.getHhId() ));
            throw new RuntimeException();
        }

        household.setJtfRandomCount( household.getHhRandomCount() );
        
    }


    private void jointTourParticipation( Tour jointTour ) {

        // get the Household object for this joint tour
        Household household = dmuObject.getHouseholdObject();

        // get the array of Person objects for this hh
        Person[] persons = household.getPersons();

        // define an ArrayList to hold indices of person objects participating in the joint tour
        ArrayList<Byte> jointTourPersonList = null;


        // make sure each joint tour has a valid composition before going to the next one.
        boolean validParty = false;


        int adults = 0;
        int children = 0;

        Logger modelLogger = tourFreq;

        while ( !validParty ) {

            adults = 0;
            children = 0;

            jointTourPersonList = new ArrayList<Byte>();

            String separator = "";
            String choiceModelDescription = "";
            String decisionMakerLabel = "";
            String loggingHeader = "";

            for (int p = 1; p < persons.length; p++) {

                Person person = persons[p];
                jointTour.setPersonObject( persons[p] );

                if ( household.getDebugChoiceModels() ) {
                    decisionMakerLabel = String.format ( "HH=%d, hhSize=%d, PersonNum=%d, PersonType=%s, tourId=%d.", household.getHhId(), household.getHhSize(), person.getPersonNum(), person.getPersonType(), jointTour.getTourId() );
                    household.logPersonObject( decisionMakerLabel, modelLogger, person );
                }
                
                
                // if person type is inconsistent with tour composition, person's participation is by definition no,
                // so skip making the choice and go to next person
                switch ( jointTour.getJointTourComposition() ) {

                    // adults only in joint tour
                    case 1:
                        if ( persons[p].getPersonIsAdult() == 1 ) {
                            
                            // write debug header
                            if( household.getDebugChoiceModels() ) {

                                choiceModelDescription = String.format ( "Adult Party Joint Tour Participation Choice Model:" );
                                jointTourParticipation.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                                    
                                modelLogger.info(" ");
                                loggingHeader = choiceModelDescription + " for " + decisionMakerLabel + ".";
                                for (int k=0; k < loggingHeader.length(); k++)
                                    separator += "+";
                                modelLogger.info( loggingHeader );
                                modelLogger.info( separator );
                                modelLogger.info( "" );
                                modelLogger.info( "" );
                            }
                            
                            
                            jointTourParticipation.computeUtilities ( dmuObject, dmuObject.getDmuIndexValues() );
                            // get the random number from the household
                            Random random = household.getHhRandom();
                            int randomCount = household.getHhRandomCount();
                            double rn = random.nextDouble();

                            // if the choice model has at least one available alternative, make choice.
                            int chosen = -1;
                            if ( jointTourParticipation.getAvailabilityCount() > 0 )
                                chosen = jointTourParticipation.getChoiceResult( rn );
                            else {
                                logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available adults only joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                                throw new RuntimeException();
                            }

                            
                            // debug output
                            if( household.getDebugChoiceModels() ){

                                String[] altNames = jointTourParticipation.getAlternativeNames();

                                double[] utilities     = jointTourParticipation.getUtilities();
                                double[] probabilities = jointTourParticipation.getProbabilities();

                                modelLogger.info("HHID: " + household.getHhId() + ", HHSize: " + household.getHhSize() + ", tourId: " + jointTour.getTourId() );
                                modelLogger.info("Alternative                 Utility       Probability           CumProb");
                                modelLogger.info("------------------   --------------    --------------    --------------");

                                double cumProb = 0.0;
                                for( int k=0; k < altNames.length; k++ ){
                                    cumProb += probabilities[k];
                                    String altString = String.format( "%-3d %13s", k+1, altNames[k] );
                                    modelLogger.info(String.format("%-18s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                                }

                                modelLogger.info(" ");
                                String altString = String.format( "%-3d %13s", chosen, altNames[chosen-1] );
                                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                                modelLogger.info( separator );
                                modelLogger.info("");
                                modelLogger.info("");
                                

                                // write choice model alternative info to debug log file
                                jointTourParticipation.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                                jointTourParticipation.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                                // write UEC calculation results to separate model specific log file
                                jointTourParticipation.logUECResults( modelLogger, loggingHeader );
                                
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

                            // write debug header
                            if( household.getDebugChoiceModels() ) {

                                choiceModelDescription = String.format ( "Child Party Joint Tour Participation Choice Model:" );
                                jointTourParticipation.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                                    
                                modelLogger.info(" ");
                                loggingHeader = choiceModelDescription + " for " + decisionMakerLabel + ".";
                                for (int k=0; k < loggingHeader.length(); k++)
                                    separator += "+";
                                modelLogger.info( loggingHeader );
                                modelLogger.info( separator );
                                modelLogger.info( "" );
                                modelLogger.info( "" );
                            }
                            
                            
                            jointTourParticipation.computeUtilities ( dmuObject, dmuObject.getDmuIndexValues() );
                            Random random = household.getHhRandom();
                            int randomCount = household.getHhRandomCount();
                            double rn = random.nextDouble();

                            // if the choice model has at least one available alternative, make choice.
                            int chosen = -1;
                            if ( jointTourParticipation.getAvailabilityCount() > 0 )
                                chosen = jointTourParticipation.getChoiceResult( rn );
                            else {
                                logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available children only joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                                throw new RuntimeException();
                            }

                            
                            // debug output
                            if( household.getDebugChoiceModels() ){

                                String[] altNames = jointTourParticipation.getAlternativeNames();

                                double[] utilities     = jointTourParticipation.getUtilities();
                                double[] probabilities = jointTourParticipation.getProbabilities();

                                modelLogger.info("HHID: " + household.getHhId() + ", HHSize: " + household.getHhSize() + ", tourId: " + jointTour.getTourId() );
                                modelLogger.info("Alternative                 Utility       Probability           CumProb");
                                modelLogger.info("------------------   --------------    --------------    --------------");

                                double cumProb = 0.0;
                                for( int k=0; k < altNames.length; k++ ){
                                    cumProb += probabilities[k];
                                    String altString = String.format( "%-3d %13s", k+1, altNames[k] );
                                    modelLogger.info(String.format("%-18s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                                }

                                modelLogger.info(" ");
                                String altString = String.format( "%-3d %13s", chosen, altNames[chosen-1] );
                                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                                modelLogger.info( separator );
                                modelLogger.info("");
                                modelLogger.info("");
                                

                                // write choice model alternative info to debug log file
                                jointTourParticipation.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                                jointTourParticipation.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                                // write UEC calculation results to separate model specific log file
                                jointTourParticipation.logUECResults( modelLogger, loggingHeader );
                                
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
                        
                        // write debug header
                        if( household.getDebugChoiceModels() ) {

                            choiceModelDescription = String.format ( "Mixed Party Joint Tour Participation Choice Model:" );
                            jointTourParticipation.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                                
                            modelLogger.info(" ");
                            loggingHeader = choiceModelDescription + " for " + decisionMakerLabel + ".";
                            for (int k=0; k < loggingHeader.length(); k++)
                                separator += "+";
                            modelLogger.info( loggingHeader );
                            modelLogger.info( separator );
                            modelLogger.info( "" );
                            modelLogger.info( "" );
                        }
                        
                        
                        jointTourParticipation.computeUtilities ( dmuObject, index );
                        Random random = household.getHhRandom();
                        int randomCount = household.getHhRandomCount();
                        double rn = random.nextDouble();

                        // if the choice model has at least one available alternative, make choice.
                        int chosen = -1;
                        if ( jointTourParticipation.getAvailabilityCount() > 0 )
                            chosen = jointTourParticipation.getChoiceResult( rn );
                        else {
                            logger.error ( String.format( "Exception caught for HHID=%d, person p=%d, no available mixed adult/children joint tour participation alternatives to choose from in choiceModelApplication.", jointTour.getHhId(), p ) );
                            throw new RuntimeException();
                        }

                        
                        // debug output
                        if( household.getDebugChoiceModels() ){

                            String[] altNames = jointTourParticipation.getAlternativeNames();

                            double[] utilities     = jointTourParticipation.getUtilities();
                            double[] probabilities = jointTourParticipation.getProbabilities();

                            modelLogger.info("HHID: " + household.getHhId() + ", HHSize: " + household.getHhSize() + ", tourId: " + jointTour.getTourId() );
                            modelLogger.info("Alternative                 Utility       Probability           CumProb");
                            modelLogger.info("------------------   --------------    --------------    --------------");

                            double cumProb = 0.0;
                            for( int k=0; k < altNames.length; k++ ){
                                cumProb += probabilities[k];
                                String altString = String.format( "%-3d %13s", k+1, altNames[k] );
                                modelLogger.info(String.format("%-18s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                            }

                            modelLogger.info(" ");
                            String altString = String.format( "%-3d %13s", chosen, altNames[chosen-1] );
                            modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                            modelLogger.info( separator );
                            modelLogger.info("");
                            modelLogger.info("");
                            

                            // write choice model alternative info to debug log file
                            jointTourParticipation.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                            jointTourParticipation.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                            // write UEC calculation results to separate model specific log file
                            jointTourParticipation.logUECResults( modelLogger, loggingHeader );
                            
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


        if ( household.getDebugChoiceModels() ) {
            for ( int i=0; i < personNums.length; i++ ) {
                Person person = household.getPersons()[personNums[i]];
                String decisionMakerLabel = String.format ( "Person in Party, HH=%d, hhSize=%d, PersonNum=%d, PersonType=%s, tourId=%d.", household.getHhId(), household.getHhSize(), person.getPersonNum(), person.getPersonType(), jointTour.getTourId() );
                household.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
        }            

        // create a key to use for a frequency map for "JointTourPurpose_Composition_NumAdults_NumChildren"
        //String key = String.format( "%s_%d_%d_%d", jointTour.getTourPurpose(), jointTour.getJointTourComposition(), adults, children );

        //int value = 0;
        //if ( partySizeFreq.containsKey( key ) )
            //value = partySizeFreq.get( key );
        //partySizeFreq.put( key, ++value );

    }




    /**
     * creates the tour objects in the Household object given the chosen joint tour frequency alternative.
     * @param chosenAlt
     */
    private void createJointTours ( Household household, int chosenAlt ) {
        Object[] t1Data = null;
        Object[] t2Data = null;

        
        // joint tours in a multiple tour set are created in a specific order according to the following hierarchy:
        //      maint, shop, discr, eat, visit
        
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
            case 8: t1Data = new Object[] {maintPurposeIndex,maintPurposeString};
                    t2Data = new Object[] {shoppingPurposeIndex,shoppingPurposeString}; break;
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
            case 18: t1Data = new Object[] {discrPurposeIndex,discrPurposeString};
                    t2Data = new Object[] {eatOutPurposeIndex,eatOutPurposeString}; break;
            // 2 joint visit tour
            case 19: t1Data = new Object[] {socialPurposeIndex,socialPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 1 joint visit tour and 1 joint discr tour
            case 20: t1Data = new Object[] {discrPurposeIndex,discrPurposeString};
                     t2Data = new Object[] {socialPurposeIndex,socialPurposeString}; break;
            // 2 joint discr tour
            case 21: t1Data = new Object[] {discrPurposeIndex,discrPurposeString};
                     t2Data = new Object[] {discrPurposeIndex,discrPurposeString}; break;

        }

        //create tours
        if (t1Data != null) {
            Tour t1 = new Tour( household, modelStructure, (Integer) t1Data[0], (String) t1Data[1], ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX );
            if (t2Data == null) {
                household.createJointTourArray(t1);
            } else {
                Tour t2 = new Tour( household, modelStructure, (Integer) t2Data[0], (String) t2Data[1], ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX );
                household.createJointTourArray(t1,t2);
            }
        }

    }


}