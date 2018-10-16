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
public class AtWorkSubtourDepartureAndDurationTime {

    
    protected static Logger logger = Logger.getLogger( AtWorkSubtourDepartureAndDurationTime.class );

    private static final int MAX_AT_WORK_SUBTOURS = 2;
    private static final int[] NUM_SUBTOURS_PER_ALTERNATIVE = { 0, 1, 1, 1, 2, 2 };
    
    
    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE     = "UecFile.TourModeChoice";
    public static final String PROPERTIES_UEC_DEP_TIME_AND_DUR     = "UecFile.TourDepartureTimeAndDuration";
    public static final String PROPERTIES_RESULTS_AT_WORK_SUBTOUR  = "Results.AtWorkSubour";

    // all the other page numbers are passed in
    public static final int UEC_DATA_PAGE = 0;
    public static final int UEC_AT_WORK_MODEL_PAGE = 5;


    protected String[] tourPurposeList;
    protected HashMap<String,Integer> tourPurposeIndexMap;

    protected int[] tourDepartureTimeChoiceSample;


    // DMU for the UEC
    protected TourDepartureTimeAndDurationDMU dmuObject;
    protected ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    protected ModelStructure modelStructure;
    protected String tourCategory;

    protected ChoiceModelApplication timeChoiceModel;
    protected ModeChoiceModel mcModel;

    private int[] altStarts;
    private int[] altEnds;
    
    protected int[][] tourModeChoiceChosenFreq;

    protected double[][] tourModeChoiceLogsums;


    private String[] tourModeAltNames;


    // model results are at-work subtour frequencies by type, departure and arrival hour: 1st dimension is tour purpose, 2nd dimension is departure hour (5-23), 3rd dimension is arrival hour (5-23)
    private int[][][] modelResults;

    private String awResultsFileName;



    public AtWorkSubtourDepartureAndDurationTime( String projectDirectory, TourDepartureTimeAndDurationDMU dmu, ModeChoiceDMU mcDmu, ModelStructure modelStructure, TazDataIf tazDataManager ){

        dmuObject = dmu;
        mcDmuObject = mcDmu;

        // set the model structure
        this.modelStructure = modelStructure;

    }


    public void setUpModels( HashMap<String, String> propertyMap, String projectDirectory, String tourCategory ){

        this.tourCategory = tourCategory;

        tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        tourPurposeIndexMap = new HashMap<String,Integer>();

        int count = 0;
        for ( int i=0; i < tourPurposeList.length; i++ ) {
            int index = tourPurposeList[i].indexOf('_');
            String purpName = "";
            if ( index < 0 )
                purpName = tourPurposeList[i];
            else
                purpName = tourPurposeList[i].substring(0,index);

            tourPurposeIndexMap.put ( purpName, count++ );
        }


        String uecFileName = propertyMap.get( PROPERTIES_UEC_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;


        // set up the models
        timeChoiceModel = new ChoiceModelApplication(uecFileName, UEC_AT_WORK_MODEL_PAGE, UEC_DATA_PAGE,
                propertyMap, dmuObject.getClass());

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

        tourModeChoiceLogsums = new double[tourPurposeList.length][numDepartureTimeChoiceAlternatives+1];

        modelResults = new int[tourPurposeList.length][numDepartureTimeChoiceAlternatives][numDepartureTimeChoiceAlternatives];

        awResultsFileName = propertyMap.get( PROPERTIES_RESULTS_AT_WORK_SUBTOUR );
        
    }


    public void applyModel( HouseholdDataManagerIf householdDataManager ){


        // get num mode choice alternatives from the purpose with index 1 - same number of mode alternatives for each purpose
        tourModeAltNames = mcModel.getModeAltNames( 1 );
        int numMcAlts = tourModeAltNames.length;

        tourModeChoiceChosenFreq = new int[tourPurposeList.length][numMcAlts + 1];



        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        int tenPercent = (int)( 0.10*householdArray.length );

        int totalTours = 0;

        // loop through households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];

            try {
                totalTours += applyDepartueTimeChoiceForAtWorkSubtours( household );
            }
            catch ( Exception e ) {
                logger.error( String.format( "error at-work subtour departure time choice model for i=%d, hhId=%d.", i, household.getHhId() ));
                throw new RuntimeException();
            }


            if ( i % tenPercent == 0 )
                logger.info ( String.format("at-work subtour departure time, duration, and mode choice complete for %.0f%% of household, %d.", (100.0*i/householdArray.length), i ) );

        }

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setAwtodRandomCount();

        logger.info ( String.format( "%d at-work subtours processed.", totalTours ) );

    }


    /**
     * @param hh is a Household object for which time choice should be made for the at-work subtour
     */
    private int applyDepartueTimeChoiceForAtWorkSubtours( Household hh ) {

        int numToursProcessed = 0;

        // get the peron objects for this household
        Person[] persons = hh.getPersons();
        for ( int p=1; p < persons.length; p++ ) {

            // get the work tours for the person
            ArrayList<Tour> subtourList = persons[p].getListOfAtWorkSubtours();

            // if no work subtours for person, nothing to do.
            if ( subtourList.size() == 0 )
                continue;


            // process each subtour from the list
            int elementCount = 0;

            for ( Tour t : subtourList ) {

                try {


                    // set the dmu object
                    dmuObject.setHousehold( hh );
                    dmuObject.setTour( t );
                    dmuObject.setPerson( persons[p] );


                    int destinationTaz = t.getTourDestTaz();
                    dmuObject.setDestinationZone( destinationTaz );

                    int originTaz = t.getTourOrigTaz();
                    dmuObject.setOriginZone( originTaz );


                    dmuObject.setFirstTour( 0 );
                    dmuObject.setSubsequentTour( 0 );
                    if ( NUM_SUBTOURS_PER_ALTERNATIVE[ t.getSubtourFreqChoice() ] == 2 && elementCount == 0 )
                        dmuObject.setFirstTour( 1 );
                    else if ( NUM_SUBTOURS_PER_ALTERNATIVE[ t.getSubtourFreqChoice() ] == 2 && elementCount > 0 )
                        dmuObject.setSubsequentTour( 1 );

                    
                    // set the choice availability and sample
                    boolean[] departureTimeChoiceAvailability = persons[p].getAvailableTimeWindows(altStarts, altEnds);
                    if ( departureTimeChoiceAvailability.length != tourDepartureTimeChoiceSample.length ) {
                        logger.error( String.format( "error in at-work subtour departure time choice model for hhId=%d, personNum=%d, tour list index=%d.", hh.getHhId(), persons[p].getPersonNum(), elementCount ));
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
                    setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( t );



                    timeChoiceModel.computeUtilities ( dmuObject, dmuObject.getIndexValues(), departureTimeChoiceAvailability, tourDepartureTimeChoiceSample );


                    Random hhRandom = hh.getHhRandom();
                    double rn = hhRandom.nextDouble();

                    // if the choice model has at least one available alternative, make choice.
                    int chosen;
                    if ( timeChoiceModel.getAvailabilityCount() > 0 )
                        chosen = timeChoiceModel.getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught for HHID=%d, personNum=%d, at-work subtour list index=%d, no available time of day choice alternatives to choose from in choiceModelApplication.", hh.getHhId(), persons[p].getPersonNum(), elementCount ) );
                        throw new RuntimeException();
                    }



                    // schedule the chosen alternative
                    int startHour = altStarts[chosen];
                    int endHour = altEnds[chosen];
                    persons[p].scheduleWindow( startHour, endHour );

                    int startIndex = startHour - CtrampApplication.START_HOUR;
                    int endIndex = endHour - CtrampApplication.START_HOUR;


                    // TODO: see if a simpler update function could/should be used
                    // given the scedules just set, update time window availability variables.
                    hh.updateTimeWindows();

                    t.setTourStartHour( startHour );
                    t.setTourEndHour( endHour );

                    int purpIndex = t.getTourPurposeIndex() - 1;
                    modelResults[purpIndex][startIndex][endIndex]++;


                    // use the mcModel object already setup for computing logsums and get the mode choice, where the selected
                    // zone, subzone and departure time and duration are set for this at-work subtour.
                    int chosenMode = mcModel.getModeChoice ( persons[p], t, purpIndex );
                    t.setTourModeChoice( chosenMode );
                    numToursProcessed++;

                    tourModeChoiceChosenFreq[purpIndex][chosenMode]++;

                }
                catch ( Exception e ) {
                    logger.error ( String.format("Exception caught in %s Departure time, duration, and mode choice model for hhid=%d, personNum=%d, at-work subtour list index=%d", tourCategory, hh.getHhId(), persons[p].getPersonNum(), elementCount ), e );
                    throw new RuntimeException();
                }

                elementCount++;

            }

        }

        return numToursProcessed;

    }



    private void setTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Tour tour ) {

        Person person = tour.getPersonObject();

        String purposeName = tour.getTourPurpose();
        int purposeIndex = tour.getTourPurposeIndex() - 1;

        mcModel.setPersonObjectForDmu ( tour, person, purposeName );


        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a];
            int endHour = altEnds[a];

            tourModeChoiceLogsums[purposeIndex][a] = mcModel.getModeChoiceLogsum( purposeIndex, tour.getTourDestTaz(), tour.getTourDestWalkSubzone(), startHour, endHour );

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

            // loop over non-mandatory tour types:
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
        for ( int i=0; i < tourModeAltNames.length; i++ ) {

            logRecord = String.format( "%-5d   %-20s", (i+1), tourModeAltNames[i] );
            underline = String.format( "%28s", "----------------------------" );
            int tot = 0;
            for ( int j=0; j < tourPurposeList.length; j++ ) {
                logRecord += String.format( "   %15d", tourModeChoiceChosenFreq[j][i+1] );
                underline += String.format( "%18s", "------------------" );
                total[j] += tourModeChoiceChosenFreq[j][i+1];
                tot += tourModeChoiceChosenFreq[j][i+1];
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
        if ( awResultsFileName != null ) {

           awResultsFileName = projectDirectory + awResultsFileName;

            try {
                writer = new FileWriter(new File(awResultsFileName));
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred opening at-work subtour results file: %s.", awResultsFileName) );
                throw new RuntimeException(e);
            }

            try {
                writer.write ( "HHID,PersonID,PersonNum,PersonType,Age,CDAP,HomeTAZ,SubtourFrequency,");
                int i = 0;
                String outputString = "";
                for ( i=1; i < MAX_AT_WORK_SUBTOURS; i++ )
                    outputString += String.format("AW%d_Purp,AW%d_Dest,AW%d_Subzone,AW%d_Depart,AW%d_Arrive,AW%d_Mode,", i, i, i, i, i, i );
                i = MAX_AT_WORK_SUBTOURS;
                outputString += String.format("AW%d_Purp,AW%d_Dest,AW%d_Subzone,AW%d_Depart,AW%d_Arrive,AW%d_Mode\n", i, i, i, i, i, i );
                writer.write ( outputString );
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred writing header to at-work subtour results file" ));
                throw new RuntimeException(e);
            }



            // get the array of households
            Household[] householdArray = householdDataManager.getHhArray();

            for(int i=1; i < householdArray.length; ++i){

                Household household = householdArray[i];
                int hhId = household.getHhId();
                int hhTaz = household.getHhTaz();

                Person[] personArray = household.getPersons();
                for (int j = 1; j < personArray.length; ++j) {

                    Person person = personArray[j];

                    int personId = person.getPersonId();
                    int personNum = person.getPersonNum();
                    int personAge = person.getAge();
                    String personType = person.getPersonType();
                    String cdap = person.getCdapActivity();
                    int tourFrequency = person.getInmtfChoice();

                    String outputString = String.format( "%d,%d,%d,%s,%d,%s,%d,%d" , hhId, personId, personNum, personType, personAge, cdap, hhTaz, tourFrequency );


                    ArrayList<Tour> tourList = person.getListOfAtWorkSubtours();

                    String purp = "NA";
                    String dest = "NA";
                    String subZone = "NA";
                    String depart = "NA";
                    String arrive = "NA";
                    String mode = "NA";

                    Tour tour = null;

                    // write tour choice results for non-mandatory tours
                    int numTours = tourList.size();
                    for ( int k=0; k < numTours; k++ ) {
                        tour = tourList.get(k);
                        purp = tour.getTourPurpose();
                        dest = String.format("%d", tour.getTourDestTaz());
                        subZone = String.format("%d", tour.getTourDestWalkSubzone());
                        depart = String.format("%d", tour.getTourStartHour());
                        arrive = String.format("%d", tour.getTourEndHour());
                        mode = tourModeAltNames[tour.getTourModeChoice()];

                        outputString += String.format( ",%s,%s,%s,%s,%s,%s", purp, dest, subZone, depart, arrive, mode );
                    }


                    // write results file filler values for remaining possible tours (5 possible per person)
                    purp = "NA";
                    dest = "NA";
                    subZone = "NA";
                    depart = "NA";
                    arrive = "NA";
                    mode = "NA";
                    for ( int k=numTours; k < MAX_AT_WORK_SUBTOURS; k++ ) {
                        outputString += String.format( ",%s,%s,%s,%s,%s,%s", purp, dest, subZone, depart, arrive, mode );
                    }

                    outputString += "\n";


                    try {
                        writer.write ( outputString );
                    }
                    catch(IOException e){
                        logger.fatal( String.format( "Exception occurred writing at-work subtour results file, hhId=%d, personNum=%d", hhId, personNum) );
                        throw new RuntimeException(e);
                    }

                }

            }


            try {
                writer.close();
                logger.info("At-work subtour Choice Results file written.");
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred closing at-work subtour results file: %s.", awResultsFileName) );
                throw new RuntimeException(e);
            }

        }

    }

}