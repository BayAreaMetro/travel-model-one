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
public class JointTourDepartureAndDurationTime implements Serializable {


    private transient Logger logger = Logger.getLogger( JointTourDepartureAndDurationTime.class );
    private transient Logger todLogger = Logger.getLogger( "todLogger" );
    private transient Logger mcLogger = Logger.getLogger( "tourMcNonMan" );

    private static final String PROPERTIES_UEC_TOUR_MODE_CHOICE           = "UecFile.TourModeChoice";
    private static final String PROPERTIES_UEC_JOINT_DEP_TIME_AND_DUR     = "UecFile.TourDepartureTimeAndDuration";


    // all the other page numbers are passed in
    private static final int UEC_DATA_PAGE = 0;
    private static final int UEC_JOINT_MODEL_PAGE = 4;


    private int[] areaType;
    private int[] zoneTableRow;

    private String[] tourPurposeList;
    private HashMap<String,Integer> tourPurposeIndexMap;

    private HashMap<String,Integer> toursCountMap;
    private HashMap<String,Integer> numToursMap;
    
    private int[] tourDepartureTimeChoiceSample;


    // DMU for the UEC
    private TourDepartureTimeAndDurationDMU dmuObject;
    private ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    private ModelStructure modelStructure;

    private int[] altStarts;
    private int[] altEnds;
    
    private ChoiceModelApplication timeChoiceModel;
    private ModeChoiceModel mcModel;


    private double[] jointTourModeChoiceLogsums;
    private boolean[] needToComputeLogsum;




    public JointTourDepartureAndDurationTime( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory, ModeChoiceModel mcModel ){

        // set the model structure
        this.modelStructure = modelStructure;
        this.mcModel = mcModel;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        setUpModels( propertyMap, dmuFactory );
    }


    public void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {

        logger.info( String.format( "setting up %s time-of-day choice model.", ModelStructure.JOINT_NON_MANDATORY_CATEGORY ) );

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        String uecFileName = propertyMap.get( PROPERTIES_UEC_JOINT_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;

        
        dmuObject = dmuFactory.getTourDepartureTimeAndDurationDMU();
        mcDmuObject = dmuFactory.getModeChoiceDMU();
    
        toursCountMap = new HashMap<String,Integer>();
        numToursMap = new HashMap<String,Integer>();

        
        tourPurposeList = modelStructure.getDcModelPurposeList( ModelStructure.JOINT_NON_MANDATORY_CATEGORY );
        tourPurposeIndexMap = new HashMap<String,Integer>();
        for ( int i=0; i < tourPurposeList.length; i++ )
            tourPurposeIndexMap.put ( tourPurposeList[i], i );


        // set up the models
        timeChoiceModel = new ChoiceModelApplication(uecFileName, UEC_JOINT_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );

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
        jointTourModeChoiceLogsums = new double[numLogsumIndices];

    }


    public void applyModel( Household hh ){

        // if no joint tours, nothing to do.
        Tour[] jointTours = hh.getJointTourArray();
        if ( jointTours != null ) {

            Logger modelLogger = todLogger;
            if( hh.getDebugChoiceModels() )
                hh.logHouseholdObject( "Pre Joint Tour Departure Time Choice HHID=" + hh.getHhId() + " Object", modelLogger );


            // set the dmu object
            dmuObject.setHousehold( hh );

            
            // count up number of tours by purpose to use to determine multiple tour sets by purpose
            numToursMap.clear();
            toursCountMap.clear();
            for ( Tour t : jointTours ) {
                String purpose = t.getTourPurpose();
                
                int num = 0;
                if ( numToursMap.containsKey( purpose ) )
                    num = numToursMap.get(purpose);
                
                num++;
                numToursMap.put(purpose, num);
            }
            

            
            for ( int i=0; i < jointTours.length; i++ ) {

                try {

                    
                    Tour t = jointTours[i];

                    
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

                        choiceModelDescription = String.format ( "Joint Tour Departure Time Choice Model for: Purpose=%s", t.getTourPurpose() );
                        decisionMakerLabel = String.format ( "HH=%d, Persons in joint tour=%d, tourId=%d of %d joint tours.", hh.getHhId(), t.getPersonNumArray().length, t.getTourId(), jointTours.length );
                        
                        timeChoiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        loggingHeader = choiceModelDescription + " for " + decisionMakerLabel + ".";
                        for (int k=0; k < loggingHeader.length(); k++)
                            separator += "+";
                        modelLogger.info( loggingHeader );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                    }

                    
                    
                    int destinationTaz = t.getTourDestTaz();
                    dmuObject.setDestinationZone( destinationTaz );

                    // set the dmu object
                    dmuObject.setTour( t );
                    dmuObject.setPerson( hh.getPersons()[1] );


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
                        dmuObject.setTourNumber( i + 1 );
                        dmuObject.setEndOfPreviousScheduledTour( 0 );
                    }
                    else if ( totalNum > 1 ) {
                        // Two joint tour multiple tour pattern
                        if ( num == 1 ) {
                            // first of 2+ tours
                            dmuObject.setFirstTour( 1 );
                            dmuObject.setSubsequentTour( 0 );
                            dmuObject.setTourNumber( i + 1 );
                            dmuObject.setEndOfPreviousScheduledTour( 0 );
                        }
                        else {
                            // 2nd tour
                            dmuObject.setFirstTour( 0 );
                            dmuObject.setSubsequentTour( 1 );
                            dmuObject.setTourNumber( i + 1 );
                            int otherTourEndHour = jointTours[0].getTourEndHour();
                            dmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                        }
                    }


                    // set the choice availability and sample
                    boolean[] departureTimeChoiceAvailability = hh.getAvailableJointTourTimeWindows( t, altStarts, altEnds );
                    Arrays.fill ( tourDepartureTimeChoiceSample, 1 );
                    
                    if ( departureTimeChoiceAvailability.length != tourDepartureTimeChoiceSample.length ) {
                        logger.error( String.format( "error in joint departure time choice model for hhId=%d, joint tour %d of %d.", hh.getHhId(), i, jointTours.length ));
                        logger.error( String.format( "length of the availability array determined by the number of alternatiuves set in the person scheduler=%d", departureTimeChoiceAvailability.length ));
                        logger.error( String.format( "does not equal the length of the sample array determined by the number of alternatives in the work tour UEC=%d.", tourDepartureTimeChoiceSample.length ));
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
                    setJointTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( t );


                    if( hh.getDebugChoiceModels() ){

                        String label = "";
                        byte[] personNums = t.getPersonNumArray();
                        for ( int p=0; p < personNums.length; p++ ) {
                            Person person = hh.getPersons()[personNums[p]];
                            label = String.format ( "Person in Party, HH=%d, hhSize=%d, PersonNum=%d, PersonType=%s, tourId=%d.", hh.getHhId(), hh.getHhSize(), person.getPersonNum(), person.getPersonType(), t.getTourId() );
                            hh.logPersonObject( label, modelLogger, person );
                        }
                        
                        label = String.format ( "Household with Joint Tour, HH=%d, hhSize=%d, tourId=%d.", hh.getHhId(), hh.getHhSize(), t.getTourId() );
                        hh.logTourObject( label, modelLogger, hh.getPersons()[t.getPersonNumArray()[0]], t );
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
                        logger.error ( String.format( "Exception caught for HHID=%d, joint tour i=%d, no available mixed adult/children joint tour participation alternatives to choose from in choiceModelApplication.", hh.getHhId(), i ) );
                        throw new RuntimeException();
                    }



                    int startHour = -1;
                    int endHour = -1;
                    
                    byte[] persNumArray = t.getPersonNumArray();
                    for ( int j=0; j < persNumArray.length; j++ ) {
                        int p = persNumArray[j];
                        Person person = hh.getPersons()[p];

                        // schedule the chosen alternative
                        startHour = altStarts[chosen-1];
                        endHour = altEnds[chosen-1];
                        person.scheduleWindow( startHour, endHour );
                    }



                    hh.updateTimeWindows();


                    t.setTourStartHour( startHour );
                    t.setTourEndHour( endHour );

                    
                    // debug output
                    if( hh.getDebugChoiceModels() ){

                        double[] utilities     = timeChoiceModel.getUtilities();
                        double[] probabilities = timeChoiceModel.getProbabilities();
                        boolean[] availabilities = timeChoiceModel.getAvailabilities();

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
                        timeChoiceModel.logUECResults( todLogger, loggingHeader );
                        
                    }
                    
                    if( hh.getDebugChoiceModels() ){

                        String label = "";
                        byte[] personNums = t.getPersonNumArray();
                        for ( int p=0; p < personNums.length; p++ ) {
                            Person person = hh.getPersons()[personNums[p]];
                            label = String.format ( "Person in Party, HH=%d, hhSize=%d, PersonNum=%d, PersonType=%s, tourId=%d.", hh.getHhId(), hh.getHhSize(), person.getPersonNum(), person.getPersonType(), t.getTourId() );
                            hh.logPersonObject( label, modelLogger, person );
                        }
                        
                        label = String.format ( "Household with Joint Tour, HH=%d, hhSize=%d, tourId=%d.", hh.getHhId(), hh.getHhSize(), t.getTourId() );
                        hh.logTourObject( label, modelLogger, hh.getPersons()[t.getPersonNumArray()[0]], t );
                    }
                    

                }
                catch ( Exception e ) {
                    logger.error ( String.format("Exception caught in %s Departure time, duration, and mode choice model for hhid=%d, i=%d", ModelStructure.JOINT_NON_MANDATORY_CATEGORY, hh.getHhId(), i ), e );
                    throw new RuntimeException();
                }

            }
            
        }

        hh.setJtodRandomCount( hh.getHhRandomCount() );

    }



    private void setJointTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Tour tour ) {

        Person person = tour.getPersonObject();
        Household household = person.getHouseholdObject();

        String purposeName = tour.getTourPurpose();
        
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject( household );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );


        Arrays.fill( needToComputeLogsum, true );
        Arrays.fill( jointTourModeChoiceLogsums, Double.NaN );
        

        Logger modelLogger = todLogger;
        String choiceModelDescription = String.format ( "Joint Tour Mode Choice Logsum calculation for %s Departure Time Choice", tour.getTourPurpose() );
        String decisionMakerLabel = String.format ( "HH=%d, tourId=%d of %d joint tours.", household.getHhId(), tour.getTourId(), household.getJointTourArray().length );
        String loggingHeader = String.format( "%s for %s", choiceModelDescription, decisionMakerLabel );
        
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
                
                jointTourModeChoiceLogsums[index] = mcModel.getModeChoiceLogsum( mcDmuObject, purposeName, modelLogger, choiceModelDescription, decisionMakerLabel + ", " + periodString );
                
                needToComputeLogsum[index] = false;
            }
            
        }
        
        dmuObject.setModeChoiceLogsums( jointTourModeChoiceLogsums );

        mcDmuObject.setTourStartHour( 0 );
        mcDmuObject.setTourEndHour( 0 );
    }


}