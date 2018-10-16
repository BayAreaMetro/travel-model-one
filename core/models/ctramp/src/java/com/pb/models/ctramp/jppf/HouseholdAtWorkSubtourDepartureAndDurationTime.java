package com.pb.models.ctramp.jppf;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.util.*;


import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.TourDepartureTimeAndDurationDMU;
//
/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 11, 2008
 * Time: 9:25:30 AM
 * To change this template use File | Settings | File Templates.
 */
public class HouseholdAtWorkSubtourDepartureAndDurationTime implements Serializable {

    
    private transient Logger logger = Logger.getLogger( HouseholdAtWorkSubtourDepartureAndDurationTime.class );
    private transient Logger todLogger = Logger.getLogger( "todLogger" );
    private transient Logger tourMCNonManLogger = Logger.getLogger( "tourMcNonMan" );
    

    
    private static final String PROPERTIES_UEC_TOUR_MODE_CHOICE     = "UecFile.TourModeChoice";
    private static final String PROPERTIES_UEC_DEP_TIME_AND_DUR     = "UecFile.TourDepartureTimeAndDuration";

    
    // all the other page numbers are passed in
    private static final int UEC_DATA_PAGE = 0;
    private static final int UEC_AT_WORK_MODEL_PAGE = 6;


    private String[] tourPurposeList;
    private HashMap<String,Integer> tourPurposeIndexMap;

    private int[] tourDepartureTimeChoiceSample;


    // DMU for the UEC
    private TourDepartureTimeAndDurationDMU dmuObject;
    private ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    private ModelStructure modelStructure;
    private String tourCategory = ModelStructure.AT_WORK_CATEGORY;

    private ChoiceModelApplication timeChoiceModel;
    private ModeChoiceModel mcModel;

    private int[] altStarts;
    private int[] altEnds;
    
    //protected int[][] tourModeChoiceChosenFreq;

    private double[] tourModeChoiceLogsums;
    private boolean[] needToComputeLogsum;


    //private String[] tourModeAltNames;


    // model results are at-work subtour frequencies by type, departure and arrival hour: 1st dimension is tour purpose, 2nd dimension is departure hour (5-23), 3rd dimension is arrival hour (5-23)
    //private int[][][] modelResults;

    //private String awResultsFileName;



    public HouseholdAtWorkSubtourDepartureAndDurationTime( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory, ModeChoiceModel mcModel ){

        // set the model structure
        this.modelStructure = modelStructure;
        this.mcModel = mcModel;

        setUpModels( propertyMap, dmuFactory );
    }


    private void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {

        logger.info( String.format( "setting up %s tour time-of-day choice model.", tourCategory ) );
        
        tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        tourPurposeIndexMap = new HashMap<String,Integer>();

//        int count = 0;
        for ( int i=0; i < tourPurposeList.length; i++ ) {
//            int index = tourPurposeList[i].indexOf('_');
//            String purpName = "";
//            if ( index < 0 )
//                purpName = tourPurposeList[i];
//            else
//                purpName = tourPurposeList[i].substring(0,index);
//            tourPurposeIndexMap.put ( purpName, count++ );

            int index = modelStructure.getDcModelPurposeIndex( tourPurposeList[i] );
            tourPurposeIndexMap.put ( tourPurposeList[i], index );
        }


        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String uecFileName = propertyMap.get( PROPERTIES_UEC_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;

        
        dmuObject = dmuFactory.getTourDepartureTimeAndDurationDMU();
        mcDmuObject = dmuFactory.getModeChoiceDMU();
        
        // set up the models
        timeChoiceModel = new ChoiceModelApplication(uecFileName, UEC_AT_WORK_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );

        // get the alternatives table from the work tod UEC.
        TableDataSet altsTable = timeChoiceModel.getUEC().getAlternativeData();
        altStarts = altsTable.getColumnAsInt( CtrampApplication.START_FIELD_NAME );
        altEnds = altsTable.getColumnAsInt( CtrampApplication.END_FIELD_NAME );
        altsTable = null;

        dmuObject.setTodAlts(altStarts, altEnds);

        
        int numDepartureTimeChoiceAlternatives = timeChoiceModel.getNumberOfAlternatives();
        tourDepartureTimeChoiceSample = new int[numDepartureTimeChoiceAlternatives+1];


        int numLogsumIndices = modelStructure.getSkimPeriodCombinationIndices().length;
        needToComputeLogsum = new boolean[numLogsumIndices];
        tourModeChoiceLogsums = new double[numLogsumIndices];

        //modelResults = new int[tourPurposeList.length][numDepartureTimeChoiceAlternatives][numDepartureTimeChoiceAlternatives];

        //awResultsFileName = propertyMap.get( PROPERTIES_RESULTS_AT_WORK_SUBTOUR );


        //if ( mcModel != null ) {
            // get num mode choice alternatives from the purpose with index 1 - same number of mode alternatives for each purpose
        //    tourModeAltNames = mcModel.getModeAltNames( 1 );
        //    int numMcAlts = tourModeAltNames.length;
    
        //    tourModeChoiceChosenFreq = new int[tourPurposeList.length][numMcAlts + 1];
        //}
        
    }
    


    public void applyModel( Household hh ){


        int startHour;
        int endHour;
        
        
        Logger modelLogger = todLogger;
        if( hh.getDebugChoiceModels() )
            hh.logHouseholdObject( "Pre At-Work SubTour Departure Time Choice HHID=" + hh.getHhId() + " Object", modelLogger );

        
        
        // get the peron objects for this household
        Person[] persons = hh.getPersons();
        for ( int p=1; p < persons.length; p++ ) {

            // get the work tours for the person
            ArrayList<Tour> subtourList = persons[p].getListOfAtWorkSubtours();
            ArrayList<Tour> workTourList = persons[p].getListOfWorkTours();

            // if no work subtours for person, nothing to do.
            if ( subtourList.size() == 0 )
                continue;

            Person person = persons[p];

            byte[] savedWindow = person.getTimeWindows();
            
            if ( hh.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
                hh.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
            

            
            int numWorkTours = workTourList.size();
            
            // process each subtour from the list
            int[] elementCount = new int[numWorkTours];

            for ( Tour t : subtourList ) {
                Tour workTour = null;
                int workTourIndex = 0;
                try {

                    workTourIndex = t.getWorkTourIndexFromSubtourId( t.getTourId() );
                    workTour = workTourList.get( workTourIndex );
                    
                    
                    // write debug header
                    String separator = "";
                    String choiceModelDescription = "" ;
                    String decisionMakerLabel = "";
                    String loggingHeader = "";
                    if( hh.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "At-Work SubTour Departure Time Choice Model for: Purpose=%s", t.getTourPurpose() );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d subtours.", hh.getHhId(), person.getPersonNum(), person.getPersonType(), t.getTourId(), subtourList.size() );
                        
                        timeChoiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        String loggerString = "At-Work SubTour Departure Time Choice Model: Debug Statement for Household ID: " + hh.getHhId() + ", Person Num: " + person.getPersonNum() + ", Person Type: " + person.getPersonType() + ", Work Tour Id: " + t.getTourId() + " of " + subtourList.size() + " subtours.";
                        for (int k=0; k < loggerString.length(); k++)
                            separator += "+";
                        modelLogger.info( loggerString );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                        loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
                        
                    }

                    
                    

                    // set the dmu object
                    dmuObject.setHousehold( hh );
                    dmuObject.setTour( t );
                    dmuObject.setPerson( persons[p] );


                    int destinationTaz = t.getTourDestTaz();
                    dmuObject.setDestinationZone( destinationTaz );

                    int originTaz = t.getTourOrigTaz();
                    dmuObject.setOriginZone( originTaz );


                    // set the first tour switch based on if the tour is the first for the tour purpose or not.
                    dmuObject.setFirstTour( 0 );
                    dmuObject.setSubsequentTour( 0 );
                    dmuObject.setTourNumber( elementCount[workTourIndex] + 1 );
                    if ( subtourList.size() == 2 && elementCount[workTourIndex] == 0 )
                        dmuObject.setFirstTour( 1 );
                    else if ( subtourList.size() == 2 && elementCount[workTourIndex] > 0 ) {
                        dmuObject.setSubsequentTour( 1 );
                        int otherTourEndHour = subtourList.get(0).getTourEndHour();
                        dmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                    }


                    int wStart = workTour.getTourStartHour();
                    int wEnd = workTour.getTourEndHour();

                    if ( elementCount[workTourIndex] == 0 ) {
                        
                        byte[] newWindow = Arrays.copyOf(savedWindow, savedWindow.length);
                        
                        for( int i=CtrampApplication.START_HOUR; i <= CtrampApplication.LAST_HOUR; i++ ) {
                            int index = i - CtrampApplication.START_HOUR;
                            if ( index >= wStart - CtrampApplication.START_HOUR && index <= wEnd - CtrampApplication.START_HOUR )
                                newWindow[index] = 0;
                            else
                                newWindow[index] = 1;
                        }
                        
                        person.setTimeWindows( newWindow );
                    }

                    
                    // set the choice availability and sample
                    boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );

                    // restrict alternatives to be only those within the work tour window
                    Arrays.fill ( tourDepartureTimeChoiceSample, 1 );

                    for ( int i=1; i <= altStarts.length; i++ ) {
                        int start = altStarts[i-1];
                        int end = altEnds[i-1];
                        if ( start < wStart || start > wEnd || end < wStart || end > wEnd ) {
                            departureTimeChoiceAvailability[i] = false;
                            tourDepartureTimeChoiceSample[i] = 0;
                        }
                    }

            
                    
                    if ( departureTimeChoiceAvailability.length != tourDepartureTimeChoiceSample.length ) {
                        logger.error( String.format( "error in at-work subtour departure time choice model for hhId=%d, personNum=%d, tour list index=%d.", hh.getHhId(), persons[p].getPersonNum(), elementCount[workTourIndex] ));
                        logger.error( String.format( "length of the availability array determined by the number of alternatives set in the person scheduler=%d", departureTimeChoiceAvailability.length ));
                        logger.error( String.format( "does not equal the length of the sample array determined by the number of alternatives in the at-work subtour UEC=%d.", tourDepartureTimeChoiceSample.length ));
                        throw new RuntimeException();
                    }

                    // if no time window is available for the tour, make the first and last alternatives available
                    // for that alternative, and keep track of the number of times this condition occurs.
                    boolean noAlternativeAvailable = true;
                    for (int a=0; a < departureTimeChoiceAvailability.length; a++) {
                        if ( departureTimeChoiceAvailability[a] ) {
                            noAlternativeAvailable = false;
                            break;
                        }
                    }

                    if ( noAlternativeAvailable ) {
                        departureTimeChoiceAvailability[1] = true;
                        departureTimeChoiceAvailability[departureTimeChoiceAvailability.length-1] = true;
                    }



                    // calculate and store the mode choice logsum for the usual work location for this worker at the various
                    // departure time and duration alternativees
                    setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( t, workTour );


                    if( hh.getDebugChoiceModels() ){
                        hh.logTourObject( loggingHeader, modelLogger, person, t );
                    }



                    timeChoiceModel.computeUtilities ( dmuObject, dmuObject.getIndexValues(), departureTimeChoiceAvailability, tourDepartureTimeChoiceSample );


                    Random hhRandom = hh.getHhRandom();
                    int randomCount = hh.getHhRandomCount();
                    double rn = hhRandom.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    int chosen;
                    if ( timeChoiceModel.getAvailabilityCount() > 0 )
                        chosen = timeChoiceModel.getChoiceResult( rn );
                    else {
                        String errorMessage = String.format( "Exception caught for HHID=%d, personNum=%d, at-work subtour list index=%d, no available time of day choice alternatives to choose from in choiceModelApplication.", hh.getHhId(), persons[p].getPersonNum(), elementCount[workTourIndex] );
                        decisionMakerLabel = String.format ( "Final At-work SubTour Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", hh.getHhId(), person.getPersonNum(), person.getPersonType() );
                        hh.logPersonObject( decisionMakerLabel, modelLogger, person );
                        timeChoiceModel.logUECResults( modelLogger, errorMessage );

                        logger.error ( errorMessage );
                        throw new RuntimeException();
                    }



                    // schedule the tour at the chosen time
                    startHour = altStarts[chosen-1];
                    endHour = altEnds[chosen-1];
                    persons[p].scheduleWindow( startHour, endHour );

                    
                    hh.updateTimeWindows();

                    t.setTourStartHour( startHour );
                    t.setTourEndHour( endHour );

                    
                    

                    // debug output
                    if( hh.getDebugChoiceModels() ){

                        double[] utilities     = timeChoiceModel.getUtilities();
                        double[] probabilities = timeChoiceModel.getProbabilities();
                        boolean[] availabilities = timeChoiceModel.getAvailabilities();

                        String personTypeString = person.getPersonType();
                        int personNum = person.getPersonNum();
                        modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString + ", Tour Id: " + t.getTourId() );
                        modelLogger.info("Alternative            Availability           Utility       Probability           CumProb");
                        modelLogger.info("--------------------   ------------    --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for(int k=0; k < timeChoiceModel.getNumberOfAlternatives(); k++){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d out=%-3d, in=%-3d", k+1, altStarts[k], altEnds[k] );
                            modelLogger.info( String.format( "%-20s%15s%18.6e%18.6e%18.6e", altString, availabilities[k+1], utilities[k], probabilities[k], cumProb ) );
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d out=%-3d, in=%-3d", chosen, altStarts[chosen-1], altEnds[chosen-1] );
                        modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");


                        // write choice model alternative info to debug log file
                        timeChoiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        timeChoiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                        // write UEC calculation results to separate model specific log file
                        loggingHeader = String.format("%s  %s", choiceModelDescription, decisionMakerLabel );
                        timeChoiceModel.logUECResults( modelLogger, loggingHeader );
                        
                    }

                }
                catch ( Exception e ) {
                    logger.error ( String.format("Exception caught in %s Subtour departure time choice model for hhid=%d, personNum=%d, at-work subtour list index=%d", tourCategory, hh.getHhId(), persons[p].getPersonNum(), elementCount[workTourIndex] ), e );
                    throw new RuntimeException();
                }

                elementCount[workTourIndex]++;               
            }

            
            person.setTimeWindows( savedWindow );

            
            if ( hh.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "Final At-work subtour Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", hh.getHhId(), person.getPersonNum(), person.getPersonType() );
                hh.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
        
            
        }

        hh.setAwtodRandomCount( hh.getHhRandomCount() );
        
    }



    private void setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Tour tour, Tour workTour ) {

        Person person = tour.getPersonObject();
        Household household = person.getHouseholdObject();

                
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject( household );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setWorkTourObject( workTour );


        Arrays.fill( needToComputeLogsum, true );
        Arrays.fill( tourModeChoiceLogsums, Double.NaN );
        

        Logger modelLogger = todLogger;
        String choiceModelDescription = String.format ( "At-Work Subtour Mode Choice Logsum calculation for %s Departure Time Choice", tour.getTourPurpose() );
        String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d subtours.", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourId(), person.getListOfAtWorkSubtours().size() );
        String loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
        
        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a-1];
            int endHour = altEnds[a-1];
            
            int index = modelStructure.getSkimPeriodCombinationIndex(startHour, endHour);
            if ( needToComputeLogsum[index] ) {

                String periodString = modelStructure.getSkimMatrixPeriodString( startHour ) + " to " + modelStructure.getSkimMatrixPeriodString( endHour );
                
                mcDmuObject.setTourStartHour( startHour );
                mcDmuObject.setTourEndHour( endHour );
                mcDmuObject.setDmuIndexValues( household.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );
    
                if ( household.getDebugChoiceModels() )
                    household.logTourObject( loggingHeader + ", " + periodString, modelLogger, person, mcDmuObject.getTourObject() );
                
                tourModeChoiceLogsums[index] = mcModel.getModeChoiceLogsum( mcDmuObject, tour.getTourPurpose(), modelLogger, choiceModelDescription, decisionMakerLabel + ", " + periodString );
                
                needToComputeLogsum[index] = false;
            }
            
        }
        
        dmuObject.setModeChoiceLogsums( tourModeChoiceLogsums );

        mcDmuObject.setTourStartHour( 0 );
        mcDmuObject.setTourEndHour( 0 );
    }


}