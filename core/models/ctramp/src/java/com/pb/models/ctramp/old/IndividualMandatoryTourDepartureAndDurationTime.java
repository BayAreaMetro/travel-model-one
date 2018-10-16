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
public class IndividualMandatoryTourDepartureAndDurationTime {


    protected static Logger logger = Logger.getLogger( IndividualMandatoryTourDepartureAndDurationTime.class );

    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE           = "UecFile.TourModeChoice";
    public static final String PROPERTIES_UEC_MAND_TOUR_DEP_TIME_AND_DUR = "UecFile.TourDepartureTimeAndDuration";



    //TODO: These need to be retrieved from tour frequency choice model UECs somehow.
    public static final String[] MANDATORY_TOUR_FREQ_ALTS_NAMES = { "", "1 work", "2 work", "1 school", "2 school", "work & school" };

    // all the other page numbers are passed in
    public static final int UEC_DATA_PAGE = 0;
    public static final int UEC_WORK_MODEL_PAGE    = 2;
    public static final int UEC_SCHOOL_MODEL_PAGE    = 3;

    protected int[] areaType;
    protected int[] zoneTableRow;

    protected int[] workTourDepartureTimeChoiceSample;
    protected int[] schoolTourDepartureTimeChoiceSample;


    // DMU for the UEC
    protected TourDepartureTimeAndDurationDMU dmuObject;
    protected ModeChoiceDMU mcDmuObject;

    // model structure to compare the .properties time of day with the UECs
    protected ModelStructure modelStructure;
    protected String tourCategory;

    protected ChoiceModelApplication workTourChoiceModel;
    protected ChoiceModelApplication schoolTourChoiceModel;
    protected ModeChoiceModel mcModel;

    protected int[] workTourModeChoiceFreq;
    protected int[] universityTourModeChoiceFreq;
    protected int[] schoolTourModeChoiceFreq;

    protected double[] workModeChoiceLogsums;
    protected double[] schoolModeChoiceLogsums;

    private int[] altStarts;
    private int[] altEnds;
    
    private int noAvailableWorkWindowCount = 0;
    private int noAvailableSchoolWindowCount = 0;

    private int noUsualWorkLocationForMandatoryActivity = 0;
    private int noUsualSchoolLocationForMandatoryActivity = 0;



    // model results are mandatory tour frequencies by type, departure and arrival hour: 1st dimension is mandatory tour type (work/school), 2nd dimension is departure hour (5-23), 3rd dimension is arrival hour (5-23)
    private int[][][] modelResults;

    private String imtResultsFileName;

    private static final String PROPERTIES_RESULTS_INDIVIDUAL_MANDATORY_TOUR_FREQUENCY = "Results.IndividualMandatoryTourResults";




    public IndividualMandatoryTourDepartureAndDurationTime( String projectDirectory, TourDepartureTimeAndDurationDMU dmu, ModeChoiceDMU mcDmu, ModelStructure modelStructure, TazDataIf tazDataManager ){

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

        String uecFileName = propertyMap.get( PROPERTIES_UEC_MAND_TOUR_DEP_TIME_AND_DUR );
        uecFileName = projectDirectory + uecFileName;

        String mcUecFileName = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFileName = projectDirectory + mcUecFileName;


        // set up the models
        workTourChoiceModel = new ChoiceModelApplication(uecFileName, UEC_WORK_MODEL_PAGE, UEC_DATA_PAGE,
                propertyMap ,dmuObject.getClass());

        schoolTourChoiceModel = new ChoiceModelApplication(uecFileName, UEC_SCHOOL_MODEL_PAGE, UEC_DATA_PAGE,
                propertyMap ,dmuObject.getClass());


        // get the alternatives table from the work tod UEC.
        TableDataSet altsTable = workTourChoiceModel.getUEC().getAlternativeData();
        altStarts = altsTable.getColumnAsInt( CtrampApplication.START_FIELD_NAME );
        altEnds = altsTable.getColumnAsInt( CtrampApplication.END_FIELD_NAME );
        altsTable = null;

        dmuObject.setTodAlts(altStarts, altEnds);
        
        int numWorkDepartureTimeChoiceAlternatives = workTourChoiceModel.getNumberOfAlternatives();
        workTourDepartureTimeChoiceSample = new int[numWorkDepartureTimeChoiceAlternatives+1];
        Arrays.fill(workTourDepartureTimeChoiceSample, 1);

        int numSchoolDepartureTimeChoiceAlternatives = schoolTourChoiceModel.getNumberOfAlternatives();
        schoolTourDepartureTimeChoiceSample = new int[numSchoolDepartureTimeChoiceAlternatives+1];
        Arrays.fill(schoolTourDepartureTimeChoiceSample, 1);

        // create the mode choice model
        mcModel = new ModeChoiceModel( mcUecFileName, propertyMap, modelStructure,  mcDmuObject, tourCategory );

        workModeChoiceLogsums = new double[numWorkDepartureTimeChoiceAlternatives+1];
        schoolModeChoiceLogsums = new double[numSchoolDepartureTimeChoiceAlternatives+1];

        modelResults = new int[2][numWorkDepartureTimeChoiceAlternatives][numWorkDepartureTimeChoiceAlternatives];
    }


    public void applyModel( HouseholdDataManagerIf householdDataManager ){

        String[] tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        int workPurposeIndex = -1;
        int univPurposeIndex = -1;
        int schlPurposeIndex = -1;
        for ( int i=0; i < tourPurposeList.length; i++ ) {
            if ( workPurposeIndex < 0 && modelStructure.getDcModelPurposeIsWorkPurpose( tourPurposeList[i] ))
                workPurposeIndex = i;
            else if ( univPurposeIndex < 0 && modelStructure.getDcModelPurposeIsUniversityPurpose( tourPurposeList[i] ))
                univPurposeIndex = i;
            else if ( schlPurposeIndex < 0 && modelStructure.getDcModelPurposeIsSchoolPurpose( tourPurposeList[i] ))
                schlPurposeIndex = i;
        }

        workTourModeChoiceFreq = new int[mcModel.getModeAltNames( workPurposeIndex ).length + 1];
        universityTourModeChoiceFreq = new int[mcModel.getModeAltNames( univPurposeIndex ).length + 1];
        schoolTourModeChoiceFreq = new int[mcModel.getModeAltNames( schlPurposeIndex ).length + 1];




        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        int tenPercent = (int)( 0.10*householdArray.length );

        int totalWorkTours = 0;
        int totalSchoolTours = 0;

        // loop through households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];

            // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
            dmuObject.setHousehold(household);


            // get the array of persons for this household
            Person[] personArray = household.getPersons();

            // loop through the persons (1-based array)
            for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];

                // mandatory tour departure time and dureation choice models for each worker/student require a specific order:
                // 1. Work tours made by workers, school/university tours made by students.
                // 2. Work tours made by students, school/university tours made by workers.
                //TODO: check consistency of these definitions -
                //TODO: workers can also be students (school-age and university)?, non-driving students can be workers?,
                //TODO: cannot be school-age student and university? etc...

                try {

                    totalWorkTours += applyDepartueTimeChoiceForWorkTours( person );
                    totalSchoolTours += applyDepartueTimeChoiceForSchoolTours( person );

                }
                catch ( Exception e ) {

                    logger.error( String.format( "error mandatory departure time choice model for i=%d, j=%d, hhId=%d, persId=%d, persNum=%d.", i, j, person.getHouseholdObject().getHhId(), person.getPersonId(), person.getPersonNum() ));
                    throw new RuntimeException();

                }

            }

            // given the scedules just set, update time window availability variables used in joint tour frequency
            // and participation models.  Can skip if single person household as no joint tour frequency model will be run.
            try {
                if ( personArray.length > 2  )
                    household.updateTimeWindows();                
            }
            catch ( Exception e ) {
                logger.error ( String.format("exception thrown updating time windows in mandatory departure time, duration, and tour mode choice for i=%d, household, %d.", i, household.getHhId() ), e );
                throw new RuntimeException();
            }


            if ( i % tenPercent == 0 )
                logger.info ( String.format("mandatory departure time, duration, and tour mode choice complete for %.0f%% of household, %d.", (100.0*i/householdArray.length), i ) );

        }

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setImtodRandomCount();

        logger.info ( String.format( "%d work tours and %d school tours processed.", totalWorkTours, totalSchoolTours ) );
        logger.info ( String.format( "%d work tours and %d school tours without a usual location processed.", noUsualWorkLocationForMandatoryActivity, noUsualSchoolLocationForMandatoryActivity ) );

    }


    /**
     *
     * @param person object for which time choice should be made
     * @return the number of work tours this person had scheduled.
     */
    private int applyDepartueTimeChoiceForWorkTours( Person person ) {

        // set the dmu object
        dmuObject.setPerson(person);


        ArrayList<Tour> workTours = person.getListOfWorkTours();

        for ( int i=0; i < workTours.size(); i++ ) {

            Tour t = workTours.get(i);

            // dest taz was set from result of usual school location choice when tour object was created in mandatory tour frequency model.
            //TODO: if the destinationTaz value is -1, then this mandatory tour was created for a non-student (retired probably)
            //TODO: and we have to resolve this somehow - either genrate a work/school location for retired, or change activity type for person.
            //TODO: for now, we'll just skip the tour, and keep count of them.
            int destinationTaz = t.getTourDestTaz();
            if ( destinationTaz <= 0 ) {
                noUsualWorkLocationForMandatoryActivity++;
                continue;
            }

            dmuObject.setDestinationZone( destinationTaz );

            // set the dmu object
            dmuObject.setTour( t );


            int originTaz = t.getTourOrigTaz();
            dmuObject.setOriginZone( originTaz );


            // get and set the area types for the tour origin and usual work location zones
            int tableRow = zoneTableRow[originTaz];
            dmuObject.setOriginAreaType( areaType[tableRow-1] );

            tableRow = zoneTableRow[destinationTaz];
            dmuObject.setDestinationAreaType( areaType[tableRow-1] );



            dmuObject.setFirstTour( 0 );
            dmuObject.setSubsequentTour( 0 );
            if ( workTours.size() > 1 && i == 0 )
                dmuObject.setFirstTour( 1 );
            else if ( workTours.size() > 1 && i > 0 )
                dmuObject.setSubsequentTour( 1 );

            


            // set the choice availability and sample
            boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );
            if ( departureTimeChoiceAvailability.length != workTourDepartureTimeChoiceSample.length ) {
                logger.error( String.format( "error in work departure time choice model for hhId=%d, persId=%d, persNum=%d, work tour %d of %d.", person.getHouseholdObject().getHhId(), person.getPersonId(), person.getPersonNum(), i, workTours.size() ));
                logger.error( String.format( "length of the availability array determined by the number of alternatiuves set in the person scheduler=%d", departureTimeChoiceAvailability.length ));
                logger.error( String.format( "does not equal the length of the sample array determined by the number of alternatives in the work tour UEC=%d.", workTourDepartureTimeChoiceSample.length ));
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
                noAvailableWorkWindowCount++;
                departureTimeChoiceAvailability[1] = true;
                workTourDepartureTimeChoiceSample[1] = 1;
                departureTimeChoiceAvailability[departureTimeChoiceAvailability.length-1] = true;
                workTourDepartureTimeChoiceSample[workTourDepartureTimeChoiceSample.length-1] = 1;
            }



            // calculate and store the mode choice logsum for the usual work location for this worker at the various
            // departure time and duration alternativees
            setWorkTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( person, t );



            workTourChoiceModel.computeUtilities ( dmuObject, dmuObject.getIndexValues(), departureTimeChoiceAvailability, workTourDepartureTimeChoiceSample );


            Random hhRandom = dmuObject.getDmuHouseholdObject().getHhRandom();
            double rn = hhRandom.nextDouble();


            // if the choice model has no available alternatives, choose between the first and last alternative.
            int chosen;
            if ( workTourChoiceModel.getAvailabilityCount() > 0 )
                chosen = workTourChoiceModel.getChoiceResult( rn );
            else
                chosen = rn < 0.5 ? 1 : 190;



            // schedule the chosen alternative
            int startHour = altStarts[chosen];
            int endHour = altEnds[chosen];
            person.scheduleWindow( startHour, endHour );

            int startIndex = startHour - CtrampApplication.START_HOUR;
            int endIndex = endHour - CtrampApplication.START_HOUR;

            t.setTourStartHour( startHour );
            t.setTourEndHour( endHour );


            modelResults[0][startIndex][endIndex]++;


            // use the mcModel object already setup for computing logsums and get the mode choice, where the selected
            // worklocation and subzone an departure time and duration are set for this work tour.
            int chosenMode = mcModel.getModeChoice ( person, t, person.getWorkLocationPurposeIndex() );
            t.setTourModeChoice( chosenMode );

            workTourModeChoiceFreq[chosenMode]++;

        }

        return workTours.size();

    }



    private void setWorkTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Person person, Tour tour ) {

        String purpose = modelStructure.getDcModelIndexPurpose( person.getWorkLocationPurposeIndex() );
        mcModel.setPersonObjectForDmu ( tour, person, purpose );


        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a];
            int endHour = altEnds[a];

            workModeChoiceLogsums[a] = mcModel.getModeChoiceLogsum( person.getWorkLocationPurposeIndex(), tour.getTourDestTaz(), tour.getTourDestWalkSubzone(), startHour, endHour );

        }

        dmuObject.setModeChoiceLogsums( workModeChoiceLogsums );

    }



    private void setSchoolTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Person person, Tour tour ) {

        String purpose = modelStructure.getDcModelIndexPurpose( person.getSchoolLocationPurposeIndex() );
        mcModel.setPersonObjectForDmu ( tour, person, purpose );


        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a];
            int endHour = altEnds[a];

            schoolModeChoiceLogsums[a] = mcModel.getModeChoiceLogsum( person.getSchoolLocationPurposeIndex(), tour.getTourDestTaz(), tour.getTourDestWalkSubzone(), startHour, endHour );

        }

        dmuObject.setModeChoiceLogsums( schoolModeChoiceLogsums );

    }



    /**
     *
     * @param person object for which time choice should be made
     * @return the number of school tours this person had scheduled.
     */
    private int applyDepartueTimeChoiceForSchoolTours( Person person ) {

        // set the dmu object
        dmuObject.setPerson(person);

        ArrayList<Tour> schoolTours = person.getListOfSchoolTours();

        for ( int i=0; i < schoolTours.size(); i++ ) {

            Tour t = schoolTours.get(i);

            // dest taz was set from result of usual school location choice when tour object was created in mandatory tour frequency model.
            //TODO: if the destinationTaz value is -1, then this mandatory tour was created for a non-student (retired probably)
            //TODO: and we have to resolve this somehow - either genrate a work/school location for retired, or change activity type for person.
            //TODO: for now, we'll just skip the tour, and keep count of them.
            int destinationTaz = t.getTourDestTaz();
            if ( destinationTaz <= 0 ) {
                noUsualSchoolLocationForMandatoryActivity++;
                continue;
            }

            dmuObject.setDestinationZone( destinationTaz );

            // set the dmu object
            dmuObject.setTour( t );

            int originTaz = t.getTourOrigTaz();
            dmuObject.setOriginZone( originTaz );


            // get and set the area types for the tour origin and usual school location zones
            int tableRow = zoneTableRow[originTaz];
            dmuObject.setOriginAreaType( areaType[tableRow-1] );

            tableRow = zoneTableRow[destinationTaz];
            dmuObject.setDestinationAreaType( areaType[tableRow-1] );


            dmuObject.setFirstTour( 0 );
            dmuObject.setSubsequentTour( 0 );
            if ( schoolTours.size() > 1 && i == 0 )
                dmuObject.setFirstTour( 1 );
            else if ( schoolTours.size() > 1 && i > 0 )
                dmuObject.setSubsequentTour( 1 );

            


            // set the choice availability and sample
            boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );
            if ( departureTimeChoiceAvailability.length != schoolTourDepartureTimeChoiceSample.length ) {
                logger.error( String.format( "error in school departure time choice model for hhId=%d, persId=%d, persNum=%d, school tour %d of %d.", person.getHouseholdObject().getHhId(), person.getPersonId(), person.getPersonNum(), i, schoolTours.size() ));
                logger.error( String.format( "length of the availability array determined by the number of alternatiuves set in the person scheduler=%d", departureTimeChoiceAvailability.length ));
                logger.error( String.format( "does not equal the length of the sample array determined by the number of alternatives in the school tour UEC=%d.", schoolTourDepartureTimeChoiceSample.length ));
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
                noAvailableSchoolWindowCount++;
                departureTimeChoiceAvailability[1] = true;
                schoolTourDepartureTimeChoiceSample[1] = 1;
                departureTimeChoiceAvailability[departureTimeChoiceAvailability.length-1] = true;
                schoolTourDepartureTimeChoiceSample[schoolTourDepartureTimeChoiceSample.length-1] = 1;
            }



            // calculate and store the mode choice logsum for the usual school location for this student at the various
            // departure time and duration alternativees
            setSchoolTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( person, t );



            schoolTourChoiceModel.computeUtilities ( dmuObject, dmuObject.getIndexValues(), departureTimeChoiceAvailability, schoolTourDepartureTimeChoiceSample );


            Random hhRandom = dmuObject.getDmuHouseholdObject().getHhRandom();
            double rn = hhRandom.nextDouble();

            // if the choice model has no available alternatives, choose between the first and last alternative.
            int chosen;
            if ( schoolTourChoiceModel.getAvailabilityCount() > 0 )
                chosen = schoolTourChoiceModel.getChoiceResult( rn );
            else
                chosen = rn < 0.5 ? 1 : 190;



            // schedule the chosen alternative
            int startHour = altStarts[chosen];
            int endHour = altEnds[chosen];
            person.scheduleWindow( startHour, endHour );

            int startIndex = startHour - CtrampApplication.START_HOUR;
            int endIndex = endHour - CtrampApplication.START_HOUR;

            modelResults[1][startIndex][endIndex]++;

            t.setTourStartHour( startHour );
            t.setTourEndHour( endHour );


            // use the mcModel object already setup for computing logsums and get the mode choice, where the selected
            // school location and subzone an departure time and duration are set for this work tour.
            int chosenMode = -1;
            if ( person.getPersonIsUniversityStudent() == 1 ) {
                chosenMode = mcModel.getModeChoice ( person, t, person.getUniversityLocationPurposeIndex() );
                universityTourModeChoiceFreq[chosenMode]++;
            }
            else {
                chosenMode = mcModel.getModeChoice ( person, t, person.getUniversityLocationPurposeIndex() );
                schoolTourModeChoiceFreq[chosenMode]++;
            }

            t.setTourModeChoice( chosenMode );


        }

        return schoolTours.size();

    }


    /**
     * Logs the results of the model.
     *
     */
    public void logResults(){

        String[] typeLabels = { "work", "school" };
        int numTypes = typeLabels.length;

        String[] periodLabels = { "5 am", "6 am", "7 am", "8 am", "9 am", "10 am", "11 am", "12 pm", "1 pm", "2 pm", "3 pm", "4 pm", "5 pm", "6 pm", "7 pm", "8 pm", "9 pm", "10 pm", "11 pm" };
        int numPeriods = periodLabels.length;


        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info("Individual Mandatory Tour Departure and Duration Model Results");

        // count of model results
        logger.info(" ");


        String tableRow = String.format( "%5s %6s", "", "" );
        for ( int j=0; j < numPeriods; j++ )
            tableRow += String.format( "  %5s", periodLabels[j] );

        tableRow += String.format( "  %5s", "Total" );
        logger.info ( tableRow );
        logger.info ( "" );

        // loop over departure hours: 5-23
        int[][] periodTypeTotal = new int[numTypes][numPeriods];
        for ( int i=0; i < numPeriods; i++ ) {

            // loop over mandatory tour types: work, school
            for ( int k=0; k < numTypes; k++ ) {

                tableRow = String.format( "%5s %6s", periodLabels[i], typeLabels[k] );

                // loop over arrival hours: 5-23
                int rowTotal = 0;
                for ( int j=0; j < numPeriods; j++ ) {
                    tableRow += String.format( "  %5d", modelResults[k][i][j] );
                    periodTypeTotal[k][j] += modelResults[k][i][j];
                    rowTotal += modelResults[k][i][j];
                }

                tableRow += String.format( "  %5d", rowTotal );
                logger.info ( tableRow );
            }

            logger.info ( "" );
        }

        for ( int k=0; k < numTypes; k++ ) {

            tableRow = String.format( "%5s %6s", "Total", typeLabels[k] );

            // loop over arrival hours: 5-23
            int rowTotal = 0;
            for ( int j=0; j < numPeriods; j++ ) {
                tableRow += String.format( "  %5d", periodTypeTotal[k][j] );
                rowTotal += periodTypeTotal[k][j];
            }

            tableRow += String.format( "  %5d", rowTotal );
            logger.info ( tableRow );
        }


        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");



        // work and all school models have same set of alternatives.
        String[] tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        int workPurposeIndex = -1;
        for ( int i=0; i < tourPurposeList.length; i++ ) {
            if ( workPurposeIndex < 0 && modelStructure.getDcModelPurposeIsWorkPurpose( tourPurposeList[i] ))
                workPurposeIndex = i;
        }
        String[] workTourModeAltNames = mcModel.getModeAltNames( workPurposeIndex );

        logger.info ( "Tour Mode Choice Results" );
        logger.info ( String.format( "%-5s   %-20s   %10s   %10s   %10s", "alt", "alt name", "work", "university", "school" ) );
        int[] total = new int[3];
        for ( int i=0; i < workTourModeAltNames.length; i++ ) {
            total[0] += workTourModeChoiceFreq[i+1];
            total[1] += universityTourModeChoiceFreq[i+1];
            total[2] += schoolTourModeChoiceFreq[i+1];
            logger.info ( String.format( "%-5d   %-20s   %10d   %10d   %10d", (i+1), workTourModeAltNames[i], workTourModeChoiceFreq[i+1], universityTourModeChoiceFreq[i+1], schoolTourModeChoiceFreq[i+1] ) );
        }
        logger.info ( String.format( "%-5s   %-20s   %10d   %10d   %10d", "total", "", total[0], total[1], total[2] ) );


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
            if ( imtResultsFileName != null ) {

               imtResultsFileName = projectDirectory + imtResultsFileName;

                try {
                    writer = new FileWriter(new File(imtResultsFileName));
                }
                catch(IOException e){
                    logger.fatal( String.format( "Exception occurred opening individual mandatory results file: %s.", imtResultsFileName) );
                    throw new RuntimeException(e);
                }

                try {
                    writer.write ( "HHID,PersonID,PersonNum,PersonType,Age,CDAP,HomeTAZ,TourFrequency,");
                    writer.write ( "MT1_Purp,MT1_Dest,MT1_Subzone,MT1_Depart,MT1_Arrive,MT1_Mode,");
                    writer.write ( "MT2_Purp,MT2_Dest,MT2_Subzone,MT2_Depart,MT2_Arrive,MT2_Mode\n");
                }
                catch(IOException e){
                    logger.fatal( String.format( "Exception occurred writing header to IMTF results file" ));
                    throw new RuntimeException(e);
                }


                // all purposes have the same alternative names, so just use index=1 to get them.
                String[] tourModeAltNames = mcModel.getModeAltNames( 1 );


                // get the array of households
                Household[] householdArray = householdDataManager.getHhArray();

                for(int i=1; i < householdArray.length; ++i){

                    Household household = householdArray[i];
                    int hhId = household.getHhId();

                    Person[] personArray = household.getPersons();
                    for (int j = 1; j < personArray.length; ++j) {

                        Person person = personArray[j];

                        int personId = person.getPersonId();
                        int personNum = person.getPersonNum();
                        int personAge = person.getAge();
                        String personType = person.getPersonType();
                        String cdap = person.getCdapActivity();
                        String tourFrequency = "NA";
                        if (person.getImtfChoice() > 0)
                            tourFrequency = MANDATORY_TOUR_FREQ_ALTS_NAMES[person.getImtfChoice()];



                        ArrayList<Tour> workList = person.getListOfWorkTours();
                        ArrayList<Tour> schoolList = person.getListOfSchoolTours();

                        String purp1 = "NA";
                        String dest1 = "NA";
                        String subZone1 = "NA";
                        String depart1 = "NA";
                        String arrive1 = "NA";
                        String mode1 = "NA";
                        String purp2 = "NA";
                        String dest2 = "NA";
                        String subZone2 = "NA";
                        String depart2 = "NA";
                        String arrive2 = "NA";
                        String mode2 = "NA";

                        Tour tour = null;
                        boolean failed = true;

                        switch ( person.getImtfChoice() ) {
                            case 1:
                                if ( workList.size() == 1 && schoolList.size() == 0 ) {
                                    tour = workList.get(0);
                                    purp1 = tour.getTourPurpose();
                                    dest1 = String.format("%d", tour.getTourDestTaz());
                                    subZone1 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart1 = String.format("%d", tour.getTourStartHour());
                                    arrive1 = String.format("%d", tour.getTourEndHour());
                                    mode1 = tourModeAltNames[tour.getTourModeChoice()];
                                    failed = false;
                                }
                                break;

                            case 2:
                                if ( workList.size() == 2 && schoolList.size() == 0 ) {
                                    tour = workList.get(0);
                                    purp1 = tour.getTourPurpose();
                                    dest1 = String.format("%d", tour.getTourDestTaz());
                                    subZone1 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart1 = String.format("%d", tour.getTourStartHour());
                                    arrive1 = String.format("%d", tour.getTourEndHour());
                                    mode1 = tourModeAltNames[tour.getTourModeChoice()];

                                    tour = workList.get(1);
                                    purp2 = tour.getTourPurpose();
                                    dest2 = String.format("%d", tour.getTourDestTaz());
                                    subZone2 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart2 = String.format("%d", tour.getTourStartHour());
                                    arrive2 = String.format("%d", tour.getTourEndHour());
                                    mode2 = tourModeAltNames[tour.getTourModeChoice()];

                                    failed = false;
                                }
                                break;

                            case 3:
                                if ( schoolList.size() == 1 && workList.size() == 0 ) {
                                    tour = schoolList.get(0);
                                    purp1 = tour.getTourPurpose();
                                    dest1 = String.format("%d", tour.getTourDestTaz());
                                    subZone1 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart1 = String.format("%d", tour.getTourStartHour());
                                    arrive1 = String.format("%d", tour.getTourEndHour());
                                    mode1 = tourModeAltNames[tour.getTourModeChoice()];
                                    failed = false;
                                }
                                break;

                            case 4:
                                if ( schoolList.size() == 2 && workList.size() == 0 ) {
                                    tour = schoolList.get(0);
                                    purp1 = tour.getTourPurpose();
                                    dest1 = String.format("%d", tour.getTourDestTaz());
                                    subZone1 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart1 = String.format("%d", tour.getTourStartHour());
                                    arrive1 = String.format("%d", tour.getTourEndHour());
                                    mode1 = tourModeAltNames[tour.getTourModeChoice()];

                                    tour = schoolList.get(1);
                                    purp2 = tour.getTourPurpose();
                                    dest2 = String.format("%d", tour.getTourDestTaz());
                                    subZone2 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart2 = String.format("%d", tour.getTourStartHour());
                                    arrive2 = String.format("%d", tour.getTourEndHour());
                                    mode2 = tourModeAltNames[tour.getTourModeChoice()];

                                    failed = false;
                                }
                                break;

                            case 5:
                                if ( workList.size() == 1 && schoolList.size() == 1 ) {
                                    tour = workList.get(0);
                                    purp1 = tour.getTourPurpose();
                                    dest1 = String.format("%d", tour.getTourDestTaz());
                                    subZone1 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart1 = String.format("%d", tour.getTourStartHour());
                                    arrive1 = String.format("%d", tour.getTourEndHour());
                                    mode1 = tourModeAltNames[tour.getTourModeChoice()];

                                    tour = schoolList.get(0);
                                    purp2 = tour.getTourPurpose();
                                    dest2 = String.format("%d", tour.getTourDestTaz());
                                    subZone2 = String.format("%d", tour.getTourDestWalkSubzone());
                                    depart2 = String.format("%d", tour.getTourStartHour());
                                    arrive2 = String.format("%d", tour.getTourEndHour());
                                    mode2 = tourModeAltNames[tour.getTourModeChoice()];

                                    failed = false;
                                }
                                break;

                        }

                        if ( failed ) {
                            logger.error ( String.format("household id=%d, personNum=%d, has individual mandatory choice index=%d, but num work tours=%d and num school tours=%d.", hhId, personNum, person.getImtfChoice(), workList.size(), schoolList.size() ));
                            logger.error ( "check mandatory tour frequency model and tour creation step for this person.");
                            throw new RuntimeException();
                        }



                        try {
                            writer.write ( String.format("%d,%d,%d,%s,%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" ,
                                    hhId, personId, personNum, personType, personAge, cdap, tourFrequency,
                                    purp1, dest1, subZone1, depart1, arrive1, mode1, purp2, dest2, subZone2, depart2, arrive2, mode2));
                        }
                        catch(IOException e){
                            logger.fatal( String.format( "Exception occurred writing individual mandatory tour results file, hhId=%d, personNum=%d", hhId, personNum) );
                            throw new RuntimeException(e);
                        }

                    }

                }


                try {
                    writer.close();
                    logger.info("Individual mandatory Tour Choice Results file written.");
                }
                catch(IOException e){
                    logger.fatal( String.format( "Exception occurred closing individual mandatory tour results file: %s.", imtResultsFileName) );
                    throw new RuntimeException(e);
                }

            }

        }




}
