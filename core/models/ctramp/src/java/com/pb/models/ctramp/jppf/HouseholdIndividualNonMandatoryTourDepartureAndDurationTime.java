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


/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 11, 2008
 * Time: 9:25:30 AM
 * To change this template use File | Settings | File Templates.
 */
public class HouseholdIndividualNonMandatoryTourDepartureAndDurationTime implements Serializable {

    
    private transient Logger logger = Logger.getLogger( HouseholdIndividualNonMandatoryTourDepartureAndDurationTime.class );
    private transient Logger todLogger = Logger.getLogger( "todLogger" );
    private transient Logger tourMCNonManLogger = Logger.getLogger( "tourMcNonMan" );

    private static final String PROPERTIES_UEC_TOUR_MODE_CHOICE           = "UecFile.TourModeChoice";
    private static final String PROPERTIES_UEC_INDIV_NON_MANDATORY_DEP_TIME_AND_DUR     = "UecFile.TourDepartureTimeAndDuration";



    // all the other page numbers are passed in
    private static final int UEC_DATA_PAGE = 0;
    private static final int UEC_INDIV_NON_MANDATORY_MODEL_PAGE = 5;


    private int[] areaType;
    private int[] zoneTableRow;

    private HashMap<String,Integer> toursCountMap;
    private HashMap<String,Integer> numToursMap;

    
    private int[] tourDepartureTimeChoiceSample;


    // DMU for the UEC
    private TourDepartureTimeAndDurationDMU dmuObject;
    private ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    private ModelStructure modelStructure;

    private ChoiceModelApplication timeChoiceModel;
    private ModeChoiceModel mcModel;

    private int[] altStarts;
    private int[] altEnds;
    

    private boolean[] needToComputeLogsum;
    private double[] tourModeChoiceLogsums;





    public HouseholdIndividualNonMandatoryTourDepartureAndDurationTime( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory, ModeChoiceModel mcModel ){

        // set the model structure
        this.modelStructure = modelStructure;
        this.mcModel = mcModel;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();
        
        setUpModels( propertyMap, dmuFactory );
    }


    public void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {

        logger.info( String.format( "setting up %s time-of-day choice model.", ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY ) );

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        String uecFileName = propertyMap.get( PROPERTIES_UEC_INDIV_NON_MANDATORY_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;

        
        dmuObject = dmuFactory.getTourDepartureTimeAndDurationDMU();
        mcDmuObject = dmuFactory.getModeChoiceDMU();
    
        toursCountMap = new HashMap<String,Integer>();
        numToursMap = new HashMap<String,Integer>();


        // set up the models
        timeChoiceModel = new ChoiceModelApplication( uecFileName, UEC_INDIV_NON_MANDATORY_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );

        // get the alternatives table from the work tod UEC.
        TableDataSet altsTable = timeChoiceModel.getUEC().getAlternativeData();
        altStarts = altsTable.getColumnAsInt( CtrampApplication.START_FIELD_NAME );
        altEnds = altsTable.getColumnAsInt( CtrampApplication.END_FIELD_NAME );
        altsTable = null;

        
        dmuObject.setTodAlts(altStarts, altEnds);

        int numDepartureTimeChoiceAlternatives = timeChoiceModel.getNumberOfAlternatives();
        tourDepartureTimeChoiceSample = new int[numDepartureTimeChoiceAlternatives+1];
        Arrays.fill ( tourDepartureTimeChoiceSample, 1 );


        int numLogsumIndices = modelStructure.getSkimPeriodCombinationIndices().length;
        needToComputeLogsum = new boolean[numLogsumIndices];
        tourModeChoiceLogsums = new double[numLogsumIndices];

    }


    public void applyModel( Household hh ){

        Logger modelLogger = todLogger;
        
        // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        dmuObject.setHousehold( hh );

        
        

        // get the peron objects for this household
        Person[] persons = hh.getPersons();
        for ( int p=1; p < persons.length; p++ ) {

            Person person = persons[p];
            
            // get the individual non-mandatory tours for the person
            ArrayList<Tour> tourList = person.getListOfIndividualNonMandatoryTours();

            // if no individual non-mandatory tours, nothing to do.
            if ( tourList.size() == 0 )
                continue;

            
            // count up number of tours by purpose to use to determine multiple tour sets by purpose
            numToursMap.clear();
            toursCountMap.clear();
            for ( Tour t : tourList ) {
                String purpose = t.getTourPurpose();
                
                int num = 0;
                if ( numToursMap.containsKey( purpose ) )
                    num = numToursMap.get(purpose);
                
                num++;
                numToursMap.put(purpose, num);
            }
                

            
            // process each individual non-mandatory tour from the list
            int elementCount = 0;
            for ( Tour t : tourList ) {

                try {

                    // get the sequence number for this tour in the group of tours of this type
                    int num = 0;
                    String purpose = t.getTourPurpose();
                    if ( toursCountMap.containsKey( purpose ) )
                        num = toursCountMap.get(purpose);
                    toursCountMap.put(purpose, ++num);
                    
                    // get the number of tours of this type
                    int totalNum = 0;
                    if ( numToursMap.containsKey( purpose ) )
                        totalNum = numToursMap.get(purpose);

                    
                    
                    // write debug header
                    String separator = "";
                    String choiceModelDescription = "" ;
                    String decisionMakerLabel = "";
                    String loggingHeader = "";
                    if( hh.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "Individual Non-Mandatory Tour Departure Time Choice Model for: Purpose=%s", purpose );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d, num=%d of %d %s tours", hh.getHhId(), person.getPersonNum(), person.getPersonType(), t.getTourId(), num, totalNum, purpose );
                        
                        timeChoiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        String loggerString = "Individual Non-Mandatory Tour Departure Time Choice Model: Debug Statement for Household ID: " + hh.getHhId() + ", Person Num: " + person.getPersonNum() + ", Person Type: " + person.getPersonType() + ", Tour Id: " + t.getTourId() + ", num " + num + " of " + totalNum + " " + purpose + " tours.";
                        for (int k=0; k < loggerString.length(); k++)
                            separator += "+";
                        modelLogger.info( loggerString );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                        loggingHeader = String.format( "%s for %s", choiceModelDescription, decisionMakerLabel );
                        
                    }

                    
                    
                    // set the dmu object
                    dmuObject.setHousehold( hh );
                    dmuObject.setTour( t );
                    dmuObject.setPerson( person );


                    int destinationTaz = t.getTourDestTaz();
                    dmuObject.setDestinationZone( destinationTaz );

                    int originTaz = t.getTourOrigTaz();
                    dmuObject.setOriginZone( originTaz );


                    // get and set the area types for the tour origin and usual work location zones
                    int tableRow = zoneTableRow[originTaz];
                    dmuObject.setOriginAreaType( areaType[tableRow-1] );

                    tableRow = zoneTableRow[destinationTaz];
                    dmuObject.setDestinationAreaType( areaType[tableRow-1] );


                    
                    // check for multiple tours for this person, by purpose
                    // set the first or second switch if multiple tours for person, by purpose
                    if ( totalNum == 1 ) {
                        // not a multiple tour pattern
                        dmuObject.setFirstTour( 0 );
                        dmuObject.setSubsequentTour( 0 );
                        dmuObject.setTourNumber( 1 );
                        dmuObject.setEndOfPreviousScheduledTour( 0 );
                    }
                    else if ( totalNum > 1 ) {
                        // Two-plus tour multiple tour pattern
                        if ( num == 1 ) {
                            // first of 2+ tours
                            dmuObject.setFirstTour( 1 );
                            dmuObject.setSubsequentTour( 0 );
                            dmuObject.setTourNumber( elementCount + 1 );
                            dmuObject.setEndOfPreviousScheduledTour( 0 );
                        }
                        else {
                            // 2nd or greater tours
                            dmuObject.setFirstTour( 0 );
                            dmuObject.setSubsequentTour( 1 );
                            dmuObject.setTourNumber( elementCount + 1 );
                            int otherTourEndHour = tourList.get( elementCount - 1 ).getTourEndHour();
                            dmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                        }
                    }

                    

                    // set the choice availability and sample
                    boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );
                    Arrays.fill(tourDepartureTimeChoiceSample, 1);
                    
                    
                    if ( departureTimeChoiceAvailability.length != tourDepartureTimeChoiceSample.length ) {
                        logger.error( String.format( "error in individual non-mandatory departure time choice model for hhId=%d, personNum=%d, tour list index=%d.", hh.getHhId(), person.getPersonNum(), elementCount ));
                        logger.error( String.format( "length of the availability array determined by the number of alternatives set in the person scheduler=%d", departureTimeChoiceAvailability.length ));
                        logger.error( String.format( "does not equal the length of the sample array determined by the number of alternatives in the individual non-mandatory tour UEC=%d.", tourDepartureTimeChoiceSample.length ));
                        throw new RuntimeException();
                    }

                    
                    // if no time window is available for the tour, make the first and last alternatives available
                    // for that alternative, and keep track of the number of times this condition occurs.
                    int alternativeAvailable = -1;
                    for (int a=0; a < departureTimeChoiceAvailability.length; a++) {
                        if ( departureTimeChoiceAvailability[a] ) {
                            alternativeAvailable = a;
                            break;
                        }
                    }

                    if ( alternativeAvailable < 0 ) {
                        departureTimeChoiceAvailability[1] = true;
                        departureTimeChoiceAvailability[departureTimeChoiceAvailability.length-1] = true;
                    }



                    // calculate and store the mode choice logsum for the usual work location for this worker at the various
                    // departure time and duration alternativees
                    setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( t );


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
                        String errorMessage = String.format( "Exception caught for HHID=%d, personNum=%d, individual non-mandatory tour list index=%d, no available time of day choice alternatives to choose from in choiceModelApplication.", hh.getHhId(), person.getPersonNum(), elementCount );
                        logger.error ( errorMessage );
                        throw new RuntimeException();
                    }




                    // schedule the chosen alternative
                    int startHour = altStarts[chosen-1];
                    int endHour = altEnds[chosen-1];
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
                        modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString + ", Tour Id: " + t.getTourId() + ", Tour num: " + num + " of " + totalNum + " " + purpose + " tours." );
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
                        loggingHeader = String.format("%s for %s", choiceModelDescription, decisionMakerLabel );
                        timeChoiceModel.logUECResults( modelLogger, loggingHeader );
                        
                    }

                }
                catch ( Exception e ) {
                    String errorMessage = String.format( "Exception caught for HHID=%d, personNum=%d, individual non-mandatory Departure time choice, tour list index=%d, no available time of day choice alternatives to choose from in choiceModelApplication.", hh.getHhId(), person.getPersonNum(), elementCount );
                    String decisionMakerLabel = String.format ( "Final Individual Non-Mandatory Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", hh.getHhId(), person.getPersonNum(), person.getPersonType() );
                    hh.logPersonObject( decisionMakerLabel, modelLogger, person );
                    timeChoiceModel.logUECResults( modelLogger, errorMessage );

                    logger.error ( errorMessage );
                    throw new RuntimeException();
                }

                elementCount++;

            }
            
            if ( hh.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "Final Individual Non-Mandatory Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", hh.getHhId(), person.getPersonNum(), person.getPersonType() );
                hh.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
        
        }

        hh.setInmtodRandomCount( hh.getHhRandomCount() );
        
    }



    private void setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Tour tour ) {

        Person person = tour.getPersonObject();
        Household household = person.getHouseholdObject();

       
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject( household );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setDmuIndexValues( household.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

        
        Arrays.fill( needToComputeLogsum, true );
        Arrays.fill( tourModeChoiceLogsums, Double.NaN );
        

        Logger modelLogger = todLogger;
        String choiceModelDescription = String.format ( "Individual Non-Mandatory Tour Mode Choice Logsum calculation for %s Departure Time Choice", tour.getTourPurpose() );
        String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d tours", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourId(), person.getListOfIndividualNonMandatoryTours().size() );
        String loggingHeader = String.format( "%s for %s", choiceModelDescription, decisionMakerLabel );
        

        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a-1];
            int endHour = altEnds[a-1];
            
            int index = modelStructure.getSkimPeriodCombinationIndex(startHour, endHour);
            if ( needToComputeLogsum[index] ) {

                String periodString = modelStructure.getSkimMatrixPeriodString( startHour ) + " to " + modelStructure.getSkimMatrixPeriodString( endHour );
                
                mcDmuObject.setTourStartHour( startHour );
                mcDmuObject.setTourEndHour( endHour );
    
                if ( household.getDebugChoiceModels() )
                    household.logTourObject( loggingHeader + ", " + periodString, modelLogger, person, tour );
                
                tourModeChoiceLogsums[index] = mcModel.getModeChoiceLogsum( mcDmuObject, tour.getTourPurpose(), modelLogger, choiceModelDescription, decisionMakerLabel + ", " + periodString );
                
                needToComputeLogsum[index] = false;
            }

        }
        
        dmuObject.setModeChoiceLogsums( tourModeChoiceLogsums );

        mcDmuObject.setTourStartHour( 0 );
        mcDmuObject.setTourEndHour( 0 );
    }



}