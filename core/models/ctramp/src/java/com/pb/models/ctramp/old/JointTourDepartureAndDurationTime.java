package com.pb.models.ctramp.old;

import org.apache.log4j.Logger;

import java.util.*;
import java.io.FileWriter;
import java.io.File;
import java.io.IOException;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.model.ChoiceModelApplication;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.JointTourFrequencyModel;
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
public class JointTourDepartureAndDurationTime {


    protected static Logger logger = Logger.getLogger( JointTourDepartureAndDurationTime.class );

    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE           = "UecFile.TourModeChoice";
    public static final String PROPERTIES_UEC_JOINT_DEP_TIME_AND_DUR     = "UecFile.TourDepartureTimeAndDuration";
    public static final String PROPERTIES_RESULTS_JOINT_TOUR             = "Results.JointTour";

    private static final int[] NUM_JOINT_TOURS_SAME_PURPOSE_PER_ALTERNATIVE = { 0, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2 };


    // all the other page numbers are passed in
    public static final int UEC_DATA_PAGE = 0;
    public static final int UEC_JOINT_MODEL_PAGE = 4;


    protected int[] areaType;
    protected int[] zoneTableRow;

    protected String[] tourPurposeList;
    protected HashMap<String,Integer> tourPurposeIndexMap;

    protected int[] tourDepartureTimeChoiceSample;


    // DMU for the UEC
    protected TourDepartureTimeAndDurationDMU dmuObject;
    protected ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    protected ModelStructure modelStructure;
    protected String tourCategory;

    private int[] altStarts;
    private int[] altEnds;
    
    protected ChoiceModelApplication timeChoiceModel;
    protected ModeChoiceModel mcModel;

    protected int[][] jointTourModeChoiceFreq;

    protected double[][] jointTourModeChoiceLogsums;


    // model results are joint tour frequencies by type, departure and arrival hour: 1st dimension is joint tour purpose, 2nd dimension is departure hour (5-23), 3rd dimension is arrival hour (5-23)
    private int[][][] modelResults;

     private String jtResultsFileName;



    public JointTourDepartureAndDurationTime( String projectDirectory, TourDepartureTimeAndDurationDMU dmu, ModeChoiceDMU mcDmu, ModelStructure modelStructure, TazDataIf tazDataManager ){

        dmuObject = dmu;
        mcDmuObject = mcDmu;

        // set the model structure
        this.modelStructure = modelStructure;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();
    }


    public void setUpModels( HashMap<String, String> propertyMap, String projectDirectory, String tourCategory ){

        this.tourCategory = tourCategory;

        tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        tourPurposeIndexMap = new HashMap<String,Integer>();
        for ( int i=0; i < tourPurposeList.length; i++ )
            tourPurposeIndexMap.put ( tourPurposeList[i], i );


        String uecFileName = propertyMap.get( PROPERTIES_UEC_JOINT_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;


        // set up the models
        timeChoiceModel = new ChoiceModelApplication(uecFileName, UEC_JOINT_MODEL_PAGE, UEC_DATA_PAGE,
                propertyMap,dmuObject.getClass());

        // get the alternatives table from the work tod UEC.
        TableDataSet altsTable = timeChoiceModel.getUEC().getAlternativeData();
        altStarts = altsTable.getColumnAsInt( CtrampApplication.START_FIELD_NAME );
        altEnds = altsTable.getColumnAsInt( CtrampApplication.END_FIELD_NAME );
        altsTable = null;

        
        int numDepartureTimeChoiceAlternatives = timeChoiceModel.getNumberOfAlternatives();
        tourDepartureTimeChoiceSample = new int[numDepartureTimeChoiceAlternatives+1];
        Arrays.fill ( tourDepartureTimeChoiceSample, 1 );


        // create the mode choice model
        mcModel = new ModeChoiceModel( mcUecFileName, propertyMap, modelStructure,  mcDmuObject, tourCategory );

        jointTourModeChoiceLogsums = new double[tourPurposeList.length][numDepartureTimeChoiceAlternatives+1];

        modelResults = new int[tourPurposeList.length][numDepartureTimeChoiceAlternatives][numDepartureTimeChoiceAlternatives];

        jtResultsFileName = propertyMap.get( PROPERTIES_RESULTS_JOINT_TOUR );

    }


    public void applyModel( HouseholdDataManagerIf householdDataManager ){

        // get num mode choice alternatives from the first purpose - same number for each purpose
        int numMcAlts = mcModel.getModeAltNames( tourPurposeIndexMap.get( tourPurposeList[0] ) ).length;

        jointTourModeChoiceFreq = new int[tourPurposeList.length][numMcAlts + 1];



        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        int tenPercent = (int)( 0.10*householdArray.length );

        int totalJointTours = 0;

        // loop through households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];

            // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
            dmuObject.setHousehold(household);

            try {
                totalJointTours += applyDepartueTimeChoiceForJointTours( household );
            }
            catch ( Exception e ) {
                logger.error( String.format( "error joint departure time choice model for i=%d, hhId=%d.", i, household.getHhId() ));
                throw new RuntimeException();
            }


            if ( i % tenPercent == 0 )
                logger.info ( String.format("joint departure time, duration, and tour mode choice complete for %.0f%% of household, %d.", (100.0*i/householdArray.length), i ) );

        }

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setJtodRandomCount();

        logger.info ( String.format( "%d joint tours processed.", totalJointTours ) );

    }


    /**
     * @param hh is a Household object for which time choice should be made for the joint tours
     */
    private int applyDepartueTimeChoiceForJointTours( Household hh ) {

        int numToursProcessed = 0;

        // if no joint tours, nothing to do.
        Tour[] jointTours = hh.getJointTourArray();
        if ( jointTours != null ) {


            // set the dmu object
            dmuObject.setHousehold( hh );

            boolean multipleTours = false;
            if ( NUM_JOINT_TOURS_SAME_PURPOSE_PER_ALTERNATIVE[ hh.getJointTourFreqChosenAlt() ] == 2 )
                multipleTours = true;

            
            for ( int i=0; i < jointTours.length; i++ ) {

                try {

                    Tour t = jointTours[i];

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

                    
                    dmuObject.setFirstTour( 0 );
                    dmuObject.setSubsequentTour( 0 );
                    if ( multipleTours ) {
                        if ( i == 0 )
                            dmuObject.setFirstTour( 1 );
                        else
                            dmuObject.setSubsequentTour( 1 );
                    }

                    
                    

                    // set the choice availability and sample
                    boolean[] departureTimeChoiceAvailability = hh.getAvailableJointTourTimeWindows( t, altStarts, altEnds );
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



                    timeChoiceModel.computeUtilities ( dmuObject, dmuObject.getIndexValues(), departureTimeChoiceAvailability, tourDepartureTimeChoiceSample );


                    Random hhRandom = dmuObject.getDmuHouseholdObject().getHhRandom();
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

                        startHour = altStarts[chosen];
                        endHour = altEnds[chosen];
                        person.scheduleWindow( startHour, endHour );

                    }



                    // TODO: see if a simpler update function could/should be used
                    // given the scedules just set, update time window availability variables.
                    hh.updateTimeWindows();
                    for ( int j=0; j < persNumArray.length; j++ ) {
                        int p = persNumArray[j];
                        hh.getPersons()[p].computeIdapResidualWindows();
                    }



                    t.setTourStartHour( startHour );
                    t.setTourEndHour( endHour );

                    int startIndex = startHour - CtrampApplication.START_HOUR;
                    int endIndex = endHour - CtrampApplication.START_HOUR;

                    int purpIndex = tourPurposeIndexMap.get( t.getTourPurpose() );
                    modelResults[purpIndex][startIndex][endIndex]++;


                    // use the mcModel object already setup for computing logsums and get the mode choice, where the selected
                    // zone, subzone and departure time and duration are set for this joint tour.  Person object parameter
                    // should't be needed for joint tour, so null is passed in place.
                    int chosenMode = mcModel.getModeChoice ( hh.getPersons()[persNumArray[0]], t, purpIndex );
                    t.setTourModeChoice( chosenMode );
                    numToursProcessed++;

                    jointTourModeChoiceFreq[purpIndex][chosenMode]++;

                }
                catch ( Exception e ) {
                    logger.error ( String.format("Exception caught in %s Departure time, duration, and mode choice model for hhid=%d, i=%d", tourCategory, hh.getHhId(), i ), e );
                    throw new RuntimeException();
                }

            }

        }

        return numToursProcessed;

    }



    private void setJointTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Tour tour ) {

        Person person = tour.getPersonObject();

        String purposeName = tour.getTourPurpose();
        int purposeIndex = tourPurposeIndexMap.get( purposeName );

        mcModel.setPersonObjectForDmu ( tour, person, purposeName );


        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a];
            int endHour = altEnds[a];

            jointTourModeChoiceLogsums[purposeIndex][a] = mcModel.getModeChoiceLogsum( purposeIndex, tour.getTourDestTaz(), tour.getTourDestWalkSubzone(), startHour, endHour );

        }

    }



    /**
     * Logs the results of the model.
     *
     */
    public void logResults(){

        String[] typeLabels = tourPurposeList;
        int numTypes = typeLabels.length;

        String[] periodLabels = { "5 am", "6 am", "7 am", "8 am", "9 am", "10 am", "11 am", "12 pm", "1 pm", "2 pm", "3 pm", "4 pm", "5 pm", "6 pm", "7 pm", "8 pm", "9 pm", "10 pm", "11 pm" };
        int numPeriods = periodLabels.length;


        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info( String.format("%s Tour Departure and Duration Model Results", tourCategory) );

        // count of model results
        logger.info(" ");


        String tableRow = String.format( "%8s %-16s", "", "" );
        for ( int j=0; j < numPeriods; j++ )
            tableRow += String.format( "  %8s", periodLabels[j] );

        tableRow += String.format( "  %8s", "Total" );
        logger.info ( tableRow );
        logger.info ( "" );

        // loop over departure hours: 5-23
        int[][] periodTypeTotal = new int[numTypes][numPeriods];
        for ( int i=0; i < numPeriods; i++ ) {

            // loop over mandatory tour types: work, school
            for ( int k=0; k < numTypes; k++ ) {

                tableRow = String.format( "%8s  %-16s", periodLabels[i], typeLabels[k] );

                // loop over arrival hours: 5-23
                int rowTotal = 0;
                for ( int j=0; j < numPeriods; j++ ) {
                    tableRow += String.format( "  %8d", modelResults[k][i][j] );
                    periodTypeTotal[k][j] += modelResults[k][i][j];
                    rowTotal += modelResults[k][i][j];
                }

                tableRow += String.format( "  %8d", rowTotal );
                logger.info ( tableRow );
            }

            logger.info ( "" );
        }

        for ( int k=0; k < numTypes; k++ ) {

            tableRow = String.format( "%8s  %-16s", "Total", typeLabels[k] );

            // loop over arrival hours: 5-23
            int rowTotal = 0;
            for ( int j=0; j < numPeriods; j++ ) {
                tableRow += String.format( "  %8d", periodTypeTotal[k][j] );
                rowTotal += periodTypeTotal[k][j];
            }

            tableRow += String.format( "  %8d", rowTotal );
            logger.info ( tableRow );
        }


        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");



        // mode choice models for all purposes have same set of alternatives.
        String[] jointTourModeAltNames = mcModel.getModeAltNames( tourPurposeIndexMap.get( tourPurposeList[0] ) );

        String logRecord = "";
        String underline = "";

        logger.info ( "Tour Mode Choice Results" );
        logRecord = String.format( "%-5s   %-20s", "alt", "alt name" );
        for ( int j=0; j < tourPurposeList.length; j++ ) {
            logRecord += String.format( "   %15s", tourPurposeList[j] );
        }
        logRecord += String.format( "   %15s", "Total" );

        logger.info ( logRecord );



        int[] total = new int[tourPurposeList.length];
        for ( int i=0; i < jointTourModeAltNames.length; i++ ) {

            logRecord = String.format( "%-5d   %-20s", (i+1), jointTourModeAltNames[i] );
            underline = String.format( "%28s", "----------------------------" );
            int tot = 0;
            for ( int j=0; j < tourPurposeList.length; j++ ) {
                logRecord += String.format( "   %15d", jointTourModeChoiceFreq[j][i+1] );
                underline += String.format( "%18s", "------------------" );
                total[j] += jointTourModeChoiceFreq[j][i+1];
                tot += jointTourModeChoiceFreq[j][i+1];
            }

            logRecord += String.format( "   %15d", tot );
            underline += String.format( "%18s", "------------------" );

            logger.info ( logRecord );
        }
        logger.info ( underline );


        int tot = 0;
        logRecord = String.format( "%-5s   %-20s", "", "Total" );
        for ( int j=0; j < tourPurposeList.length; j++ ) {
            logRecord += String.format( "   %15d", total[j] );
            tot += total[j];
        }
        logRecord += String.format( "   %15d", tot );

        logger.info ( logRecord );
        

        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");

    }

    /**
            * Loops through the households in the HouseholdDataManager, gets the households and persons
            *  and writes a row with detail on each of these in a file.
            *
            * @param householdDataManager is the object from which the array of household objects can be retrieved.
            * @param projectDirectory is the root directory for the output file named
            */
           public void saveResults(HouseholdDataManagerIf householdDataManager, String projectDirectory){

               FileWriter writer;
               if ( jtResultsFileName != null ) {

                  jtResultsFileName = projectDirectory + jtResultsFileName;

                   try {
                       writer = new FileWriter(new File(jtResultsFileName));
                   }
                   catch(IOException e){
                       logger.fatal( String.format( "Exception occurred opening JT results file: %s.", jtResultsFileName) );
                       throw new RuntimeException(e);
                   }

                   try {
                       writer.write ( "HHID,PersonID,PersonType,PersonNum,Age,HomeTAZ,JTFreq,");
                       writer.write ( "JT1_Comp,JT1_Partic,JT1_Purp,JT1_Dest,JT1_Subzone,JT1_Depart,JT1_Arrive,JT1_Mode,");
                       writer.write ( "JT2_Comp,JT2_Partic,JT2_Purp,JT2_Dest,JT2_Subzone,JT2_Depart,JT2_Arrive,JT2_Mode\n");
                   }
                   catch(IOException e){
                       logger.fatal( String.format( "Exception occurred writing header to JT results file" ));
                       throw new RuntimeException(e);
                   }


                   // mode choice models for all purposes have same set of alternatives.
                   String[] jointTourModeAltNames = mcModel.getModeAltNames( tourPurposeIndexMap.get( tourPurposeList[0] ) );



                   // get the array of households
                   Household[] householdArray = householdDataManager.getHhArray();

                   for(int i=1; i < householdArray.length; ++i){


                       Household household = householdArray[i];
                       Tour[] jointTours = household.getJointTourArray();

                       int hhId = household.getHhId();

                       Person[] personArray = household.getPersons();

                       for (int j = 1; j < personArray.length; ++j) {

                           Person person = personArray[j];

                           int personId = person.getPersonId();
                           int personNum = person.getPersonNum();
                           String personType = person.getPersonType();
                           int personAge = person.getAge();
                           int homeTAZ = household.getHhTaz();

                           // initialize joint tour freq to 'N/A'.
                           // A 1 person hh, for example, is not eligible for joint tours, so a tour frequency choice is never made.
                           // An 'N/A' result is therefore distinguished from a '0_tours' chsen alternative.
                           String tourFreq = "N/A";
                           String tour1Compostion = "";
                           String tour1Partic = "";
                           String tour1Purpose = "";
                           int tour1Dest = 0;
                           int tour1SubZone = 0;
                           int tour1Depart = 0;
                           int tour1Arrive = 0;
                           String tour1Mode = "";
                           String tour2Compostion = "";
                           String tour2Partic = "";
                           String tour2Purpose = "";
                           int tour2Dest = 0;
                           int tour2SubZone = 0;
                           int tour2Depart = 0;
                           int tour2Arrive = 0;
                           String tour2Mode = "";

                           if ( jointTours != null ) {

                               tourFreq = household.getJointTourFreqChosenAltName();

                               if (jointTours.length > 0) {

                                   Tour tour1 = jointTours[0];
                                   tour1Compostion = JointTourFrequencyModel.JOINT_TOUR_COMPOSITION_NAMES[tour1.getJointTourComposition()];
                                   tour1Partic = "no";
                                   for (int personNumber: tour1.getPersonNumArray()) {
                                       if (personNumber == personNum) {
                                           tour1Partic = "yes";
                                           break;
                                       }
                                   }

                                   tour1Purpose = tour1.getTourPurpose();
                                   tour1Dest = tour1.getTourDestTaz();
                                   tour1SubZone = tour1.getTourDestWalkSubzone();
                                   tour1Depart = tour1.getTourStartHour();
                                   tour1Arrive = tour1.getTourEndHour();
                                   tour1Mode = jointTourModeAltNames[tour1.getTourModeChoice()];

                                   if (jointTours.length > 1) {
                                       Tour tour2 = jointTours[1];
                                       tour2Compostion = JointTourFrequencyModel.JOINT_TOUR_COMPOSITION_NAMES[tour2.getJointTourComposition()];
                                       tour2Partic = "no";
                                       for (int personNumber: tour2.getPersonNumArray()) {
                                           if (personNumber == personNum) {
                                               tour2Partic = "yes";
                                               break;
                                           }
                                       }

                                       tour2Purpose = tour2.getTourPurpose();
                                       tour2Dest = tour2.getTourDestTaz();
                                       tour2SubZone = tour2.getTourDestWalkSubzone();
                                       tour2Depart = tour2.getTourStartHour();
                                       tour2Arrive = tour2.getTourEndHour();
                                       tour2Mode = jointTourModeAltNames[tour2.getTourModeChoice()];
                                   }
                                   
                               }
                           }

                           try {

                               writer.write ( String.format("%d,%d,%s,%d,%d,%d,%s," ,
                                       hhId, personId, personType, personNum, personAge, homeTAZ, tourFreq));
                               writer.write( String.format("%s,%s,%s,%d,%d,%d,%d,%s," ,
                                       tour1Compostion, tour1Partic, tour1Purpose, tour1Dest, tour1SubZone, tour1Depart, tour1Arrive, tour1Mode));
                               writer.write( String.format("%s,%s,%s,%d,%d,%d,%d,%s\n" ,
                                       tour2Compostion, tour2Partic, tour2Purpose, tour2Dest, tour2SubZone, tour2Depart, tour2Arrive, tour2Mode));

                           }
                           catch(IOException e){
                               logger.fatal( String.format( "Exception occurred writing JT results file, hhId=%d", hhId) );
                               throw new RuntimeException(e);
                           }
                       }

                   }


                   try {
                       writer.close();
                       logger.info("JTF Results file written.");
                   }
                   catch(IOException e){
                       logger.fatal( String.format( "Exception occurred closing JT results file: %s.", jtResultsFileName) );
                       throw new RuntimeException(e);
                   }

               }

       }




}