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
public class HouseholdIndividualMandatoryTourDepartureAndDurationTime implements Serializable {


    private transient Logger logger = Logger.getLogger( HouseholdIndividualMandatoryTourDepartureAndDurationTime.class );
    private transient Logger todLogger = Logger.getLogger( "todLogger" );
    private transient Logger tourMCManLogger = Logger.getLogger( "tourMcMan" );

    private static final String PROPERTIES_UEC_MAND_TOUR_DEP_TIME_AND_DUR = "UecFile.TourDepartureTimeAndDuration";


    // all the other page numbers are passed in
    private static final int UEC_DATA_PAGE = 0;
    private static final int UEC_WORK_MODEL_PAGE    = 2;
    private static final int UEC_SCHOOL_MODEL_PAGE    = 3;


    private int[] areaType;
    private int[] zoneTableRow;

    private int[] workTourDepartureTimeChoiceSample;
    private int[] schoolTourDepartureTimeChoiceSample;


    // DMU for the UEC
    private TourDepartureTimeAndDurationDMU imtodDmuObject;
    private ModeChoiceDMU mcDmuObject;
    
    // model structure to compare the .properties time of day with the UECs
    private ModelStructure modelStructure;
    private String tourCategory = ModelStructure.MANDATORY_CATEGORY;

    private ChoiceModelApplication workTourChoiceModel;
    private ChoiceModelApplication schoolTourChoiceModel;
    private ModeChoiceModel mcModel;


    private boolean[] needToComputeLogsum;
    private double[] workModeChoiceLogsums;
    private double[] schoolModeChoiceLogsums;

    private int[] altStarts;
    private int[] altEnds;
    
    private int noAvailableWorkWindowCount = 0;
    private int noAvailableSchoolWindowCount = 0;

    private int noUsualWorkLocationForMandatoryActivity = 0;
    private int noUsualSchoolLocationForMandatoryActivity = 0;




    public HouseholdIndividualMandatoryTourDepartureAndDurationTime( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory, ModeChoiceModel mcModel ){

        setupHouseholdIndividualMandatoryTourDepartureAndDurationTime ( propertyMap, tazDataManager, modelStructure, dmuFactory, mcModel );

    }


    private void setupHouseholdIndividualMandatoryTourDepartureAndDurationTime( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory, ModeChoiceModel mcModel ){

        logger.info( String.format( "setting up %s time-of-day choice model.", tourCategory ) );
        
        // set the model structure
        this.modelStructure = modelStructure;
        this.mcModel = mcModel;
        

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        
        // locate the individual mandatory tour frequency choice model UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String imtodUecFile = propertyMap.get( PROPERTIES_UEC_MAND_TOUR_DEP_TIME_AND_DUR );
        imtodUecFile = projectDirectory + imtodUecFile;

        // get the dmu objects from the factory
        imtodDmuObject = dmuFactory.getTourDepartureTimeAndDurationDMU();
        mcDmuObject = dmuFactory.getModeChoiceDMU();
        

        // set up the models
        workTourChoiceModel = new ChoiceModelApplication( imtodUecFile, UEC_WORK_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)imtodDmuObject );
        schoolTourChoiceModel = new ChoiceModelApplication( imtodUecFile, UEC_SCHOOL_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)imtodDmuObject );

        // get the alternatives table from the work tod UEC.
        TableDataSet altsTable = workTourChoiceModel.getUEC().getAlternativeData();
        altStarts = altsTable.getColumnAsInt( CtrampApplication.START_FIELD_NAME );
        altEnds = altsTable.getColumnAsInt( CtrampApplication.END_FIELD_NAME );
        altsTable = null;

        imtodDmuObject.setTodAlts(altStarts, altEnds);
        
        
        int numWorkDepartureTimeChoiceAlternatives = workTourChoiceModel.getNumberOfAlternatives();
        workTourDepartureTimeChoiceSample = new int[numWorkDepartureTimeChoiceAlternatives+1];
        Arrays.fill(workTourDepartureTimeChoiceSample, 1);

        int numSchoolDepartureTimeChoiceAlternatives = schoolTourChoiceModel.getNumberOfAlternatives();
        schoolTourDepartureTimeChoiceSample = new int[numSchoolDepartureTimeChoiceAlternatives+1];
        Arrays.fill(schoolTourDepartureTimeChoiceSample, 1);

        
        
        int numLogsumIndices = modelStructure.getSkimPeriodCombinationIndices().length;
        needToComputeLogsum = new boolean[numLogsumIndices];
        
        workModeChoiceLogsums = new double[numLogsumIndices];
        schoolModeChoiceLogsums = new double[numLogsumIndices];
        
        
        //modelResults = new int[2][numWorkDepartureTimeChoiceAlternatives][numWorkDepartureTimeChoiceAlternatives];
        

    
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

    }


    public void applyModel( Household household ){

        Logger modelLogger = todLogger;
        if ( household.getDebugChoiceModels() ) {
            household.logHouseholdObject( "Pre Individual Mandatory Departure Time Choice Model HHID=" + household.getHhId(), modelLogger );
            household.logHouseholdObject( "Pre Individual Mandatory Tour Mode Choice Model HHID=" + household.getHhId(), tourMCManLogger );
        }
        
        // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        imtodDmuObject.setHousehold(household);



        // get the array of persons for this household
        Person[] personArray = household.getPersons();

        // loop through the persons (1-based array)
        for(int j=1;j<personArray.length;++j){

            Person person = personArray[j];

            if ( household.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
                household.logPersonObject( decisionMakerLabel, modelLogger, person );
                household.logPersonObject( decisionMakerLabel, tourMCManLogger, person );
            }
            

            // mandatory tour departure time and dureation choice models for each worker/student require a specific order:
            // 1. Work tours made by workers, school/university tours made by students.
            // 2. Work tours made by students, school/university tours made by workers.
            //TODO: check consistency of these definitions -
            //TODO: workers can also be students (school-age and university)?, non-driving students can be workers?,
            //TODO: cannot be school-age student and university? etc...

            try {

                if ( person.getPersonIsWorker() == 1 ) {
                    applyDepartureTimeChoiceForWorkTours( person );
                    if ( person.getListOfSchoolTours().size() > 0 )
                        applyDepartureTimeChoiceForSchoolTours( person );
                }
                else if ( person.getPersonIsStudent() == 1 || person.getPersonIsPreschoolChild() == 1 ) {
                    applyDepartureTimeChoiceForSchoolTours( person );
                    if ( person.getListOfWorkTours().size() > 0 )
                        applyDepartureTimeChoiceForWorkTours( person );
                }
                else {
                    if ( person.getListOfWorkTours().size() > 0 || person.getListOfSchoolTours().size() > 0 ) {
                        logger.error( String.format( "error mandatory departure time choice model for j=%d, hhId=%d, persNum=%d, personType=%s.", j, person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() ));
                        logger.error( String.format( "person with type other than worker or student has %d work tours and %d school tours.", person.getListOfWorkTours().size(), person.getListOfSchoolTours().size() ) );
                        throw new RuntimeException();
                    }
                }

            }
            catch ( Exception e ) {
                logger.error( String.format( "error mandatory departure time choice model for j=%d, hhId=%d, persId=%d, persNum=%d, personType=%s.", j, person.getHouseholdObject().getHhId(), person.getPersonId(), person.getPersonNum(), person.getPersonType() ));
                throw new RuntimeException();
            }

        }

        
        
        // given the schedules just set, update time window availability variables used in joint tour frequency
        // and participation models.  Can skip if single person household as no joint tour frequency model will be run.
        try {
            if ( personArray.length > 2  )
                household.updateTimeWindows();                
        }
        catch ( Exception e ) {
            logger.error ( String.format("exception thrown updating time windows in mandatory departure time, duration, and tour mode choice for household id = %d.", household.getHhId() ), e );
            throw new RuntimeException();
        }
        
        
        household.setImtodRandomCount( household.getHhRandomCount() );

        
    }


    /**
     *
     * @param person object for which time choice should be made
     * @return the number of work tours this person had scheduled.
     */
    private int applyDepartureTimeChoiceForWorkTours( Person person ) {

        Logger modelLogger = todLogger;
        
        // set the dmu object
        imtodDmuObject.setPerson(person);

        Household household = person.getHouseholdObject();
        
        
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

            
            
            // write debug header
            String separator = "";
            String choiceModelDescription = "" ;
            String decisionMakerLabel = "";
            String loggingHeader = "";
            if( household.getDebugChoiceModels() ) {

                choiceModelDescription = String.format ( "Individual Mandatory Work Tour Departure Time Choice Model for: Purpose=%s", t.getTourPurpose() );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d", household.getHhId(), person.getPersonNum(), person.getPersonType(), t.getTourId(), workTours.size() );
                
                workTourChoiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                    
                modelLogger.info(" ");
                String loggerString = "Individual Mandatory Work Tour Departure Time Choice Model: Debug Statement for Household ID: " + household.getHhId() + ", Person Num: " + person.getPersonNum() + ", Person Type: " + person.getPersonType() + ", Work Tour Id: " + t.getTourId() + " of " + workTours.size() + " work tours.";
                for (int k=0; k < loggerString.length(); k++)
                    separator += "+";
                modelLogger.info( loggerString );
                modelLogger.info( separator );
                modelLogger.info( "" );
                modelLogger.info( "" );
             
                loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
                
            }


            
            
            imtodDmuObject.setDestinationZone( destinationTaz );

            // set the dmu object
            imtodDmuObject.setTour( t );


            int originTaz = t.getTourOrigTaz();
            imtodDmuObject.setOriginZone( originTaz );


            // get and set the area types for the tour origin and usual work location zones
            int tableRow = zoneTableRow[originTaz];
            imtodDmuObject.setOriginAreaType( areaType[tableRow-1] );

            tableRow = zoneTableRow[destinationTaz];
            imtodDmuObject.setDestinationAreaType( areaType[tableRow-1] );

            
            // check for multiple tours for this person
            // set the first or second switch if multiple tours for person
            if ( workTours.size() == 1 && person.getListOfSchoolTours().size() == 0 ) {
                // not a multiple tour pattern
                imtodDmuObject.setFirstTour( 0 );
                imtodDmuObject.setSubsequentTour( 0 );
                imtodDmuObject.setTourNumber( 1 );
                imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
            }
            else if ( workTours.size() > 1 && person.getListOfSchoolTours().size() == 0 ) {
                // Two work tour multiple tour pattern
                if ( i == 0 ) {
                    // first of 2 work tours
                    imtodDmuObject.setFirstTour( 1 );
                    imtodDmuObject.setSubsequentTour( 0 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
                }
                else {
                    // second of 2 work tours
                    imtodDmuObject.setFirstTour( 0 );
                    imtodDmuObject.setSubsequentTour( 1 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    int otherTourEndHour = workTours.get(0).getTourEndHour();
                    imtodDmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                }
            }
            else if ( workTours.size() == 1 && person.getListOfSchoolTours().size() == 1 ) {
                // One work tour, one school tour multiple tour pattern
                if ( person.getPersonIsWorker() == 1 ) {
                    // worker, so work tour is first scheduled, school tour comes later.
                    imtodDmuObject.setFirstTour( 1 );
                    imtodDmuObject.setSubsequentTour( 0 );
                    imtodDmuObject.setTourNumber( 1 );
                    imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
                }
                else {
                    // student, so school tour was already scheduled, this work tour is the second.
                    imtodDmuObject.setFirstTour( 0 );
                    imtodDmuObject.setSubsequentTour( 1 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    int otherTourEndHour = person.getListOfSchoolTours().get(0).getTourEndHour();
                    imtodDmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                }
            }

            

            
            // set the choice availability and initialize sample array - choicemodelapplication will change sample[] according to availability[]
            boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );
            Arrays.fill(workTourDepartureTimeChoiceSample, 1);

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
                departureTimeChoiceAvailability[departureTimeChoiceAvailability.length-1] = true;
            }


            // calculate and store the mode choice logsum for the usual work location for this worker at the various
            // departure time and duration alternativees
            setWorkTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( person, t );


            if( household.getDebugChoiceModels() ){
                household.logTourObject( loggingHeader, modelLogger, person, t );
            }


            workTourChoiceModel.computeUtilities ( imtodDmuObject, imtodDmuObject.getIndexValues(), departureTimeChoiceAvailability, workTourDepartureTimeChoiceSample );


            Random hhRandom = imtodDmuObject.getDmuHouseholdObject().getHhRandom();
            int randomCount = household.getHhRandomCount();
            double rn = hhRandom.nextDouble();


            // if the choice model has no available alternatives, choose between the first and last alternative.
            int chosen;
            if ( workTourChoiceModel.getAvailabilityCount() > 0 )
                chosen = workTourChoiceModel.getChoiceResult( rn );
            else
                chosen = rn < 0.5 ? 1 : 190;



            // schedule the chosen alternative
            int startHour = altStarts[chosen-1];
            int endHour = altEnds[chosen-1];
            person.scheduleWindow( startHour, endHour );

            household.updateTimeWindows();
            
            //int startIndex = startHour - CtrampApplication.START_HOUR;
            //int endIndex = endHour - CtrampApplication.START_HOUR;

            t.setTourStartHour( startHour );
            t.setTourEndHour( endHour );

            
            //modelResults[0][startIndex][endIndex]++;

            
            // debug output
            if( household.getDebugChoiceModels() ){

                double[] utilities     = workTourChoiceModel.getUtilities();
                double[] probabilities = workTourChoiceModel.getProbabilities();
                boolean[] availabilities = workTourChoiceModel.getAvailabilities();

                String personTypeString = person.getPersonType();
                int personNum = person.getPersonNum();
                modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString + ", Tour Id: " + t.getTourId() );
                modelLogger.info("Alternative            Availability           Utility       Probability           CumProb");
                modelLogger.info("--------------------   ------------    --------------    --------------    --------------");

                double cumProb = 0.0;
                for(int k=0; k < workTourChoiceModel.getNumberOfAlternatives(); k++){
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
                workTourChoiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                workTourChoiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                // write UEC calculation results to separate model specific log file
                loggingHeader = String.format("%s  %s", choiceModelDescription, decisionMakerLabel );
                workTourChoiceModel.logUECResults( modelLogger, loggingHeader );
                
            }
        }

        if ( household.getDebugChoiceModels() ) {
            String decisionMakerLabel = String.format ( "Final Work Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
            household.logPersonObject( decisionMakerLabel, modelLogger, person );
        }
        
        return workTours.size();

    }



    private void setWorkTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Person person, Tour tour ) {

        Household household = person.getHouseholdObject();
        
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject( household );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setDmuIndexValues( household.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

        
        Arrays.fill( needToComputeLogsum, true );
        Arrays.fill( workModeChoiceLogsums, Double.NaN );
        

        Logger modelLogger = todLogger;
        String choiceModelDescription = String.format ( "Work Tour Mode Choice Logsum calculation for %s Departure Time Choice", tour.getTourPurpose() );
        String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourId(), person.getListOfWorkTours().size() );
        String loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
        
        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a-1];
            int endHour = altEnds[a-1];

            int index = modelStructure.getSkimPeriodCombinationIndex(startHour, endHour);
            if ( needToComputeLogsum[index] ) {

                String periodString = modelStructure.getSkimMatrixPeriodString( startHour ) + " to " + modelStructure.getSkimMatrixPeriodString( endHour );
                
                mcDmuObject.setTourStartHour( startHour );
                mcDmuObject.setTourEndHour( endHour );
    
                if ( household.getDebugChoiceModels() )
                    household.logTourObject( loggingHeader + ", " + periodString, modelLogger, person, mcDmuObject.getTourObject() );
                
                workModeChoiceLogsums[index] = mcModel.getModeChoiceLogsum( mcDmuObject, tour.getTourPurpose(), modelLogger, choiceModelDescription, decisionMakerLabel + ", " + periodString );
                
                needToComputeLogsum[index] = false;
            }

        }

        imtodDmuObject.setModeChoiceLogsums( workModeChoiceLogsums );

        mcDmuObject.setTourStartHour( 0 );
        mcDmuObject.setTourEndHour( 0 );
    }


    
    private void setSchoolTourModeChoiceLogsumsForDepartureTimeAndDurationAlternatives( Person person, Tour tour ) {

        Household household = person.getHouseholdObject();
        
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject( household );
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setDmuIndexValues( household.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

        
        Arrays.fill( needToComputeLogsum, true );
        Arrays.fill( schoolModeChoiceLogsums, Double.NaN );

        
        Logger modelLogger = todLogger;
        String choiceModelDescription = String.format ( "School Tour Mode Choice Logsum calculation for %s Departure Time Choice", tour.getTourPurpose() );
        String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourId(), person.getListOfSchoolTours().size() );
        String loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
        
        
        
        for (int a=1; a <= altStarts.length; a++) {

            int startHour = altStarts[a-1];
            int endHour = altEnds[a-1];

            int index = modelStructure.getSkimPeriodCombinationIndex(startHour, endHour);
            if ( needToComputeLogsum[index] ) {

                String periodString = modelStructure.getSkimMatrixPeriodString( startHour ) + " to " + modelStructure.getSkimMatrixPeriodString( endHour );
                
                mcDmuObject.setTourStartHour( startHour );
                mcDmuObject.setTourEndHour( endHour );
    
                if ( household.getDebugChoiceModels() )
                    household.logTourObject( loggingHeader + ", " + periodString, modelLogger, person, mcDmuObject.getTourObject() );
                
                schoolModeChoiceLogsums[index] = mcModel.getModeChoiceLogsum( mcDmuObject, tour.getTourPurpose(), modelLogger, choiceModelDescription, decisionMakerLabel + ", " + periodString );

                needToComputeLogsum[index] = false;
            }
            
        }

        imtodDmuObject.setModeChoiceLogsums( schoolModeChoiceLogsums );

    }



    /**
     *
     * @param person object for which time choice should be made
     * @return the number of school tours this person had scheduled.
     */
    private int applyDepartureTimeChoiceForSchoolTours( Person person ) {

        Logger modelLogger = todLogger;
        
        // set the dmu object
        imtodDmuObject.setPerson(person);


        Household household = person.getHouseholdObject();
        
        
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

            
            
            // write debug header
            String separator = "";
            String choiceModelDescription = "" ;
            String decisionMakerLabel = "";
            String loggingHeader = "";
            if( household.getDebugChoiceModels() ) {

                choiceModelDescription = String.format ( "Individual Mandatory School Tour Departure Time Choice Model for: Purpose=%s", t.getTourPurpose() );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, tourId=%d of %d", household.getHhId(), person.getPersonNum(), person.getPersonType(), t.getTourId(), schoolTours.size() );
                
                schoolTourChoiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                    
                modelLogger.info(" ");
                String loggerString = "Individual Mandatory School Tour Departure Time Choice Model: Debug Statement for Household ID: " + household.getHhId() + ", Person Num: " + person.getPersonNum() + ", Person Type: " + person.getPersonType() + ", Tour Id: " + t.getTourId() + " of " + schoolTours.size() + " school tours.";
                for (int k=0; k < loggerString.length(); k++)
                    separator += "+";
                modelLogger.info( loggerString );
                modelLogger.info( separator );
                modelLogger.info( "" );
                modelLogger.info( "" );

            }
            

            
            imtodDmuObject.setDestinationZone( destinationTaz );

            // set the dmu object
            imtodDmuObject.setTour( t );

            int originTaz = t.getTourOrigTaz();
            imtodDmuObject.setOriginZone( originTaz );


            // get and set the area types for the tour origin and usual school location zones
            int tableRow = zoneTableRow[originTaz];
            imtodDmuObject.setOriginAreaType( areaType[tableRow-1] );

            tableRow = zoneTableRow[destinationTaz];
            imtodDmuObject.setDestinationAreaType( areaType[tableRow-1] );


            // check for multiple tours for this person
            // set the first or second switch if multiple tours for person
            if ( schoolTours.size() == 1 && person.getListOfWorkTours().size() == 0 ) {
                // not a multiple tour pattern
                imtodDmuObject.setFirstTour( 0 );
                imtodDmuObject.setSubsequentTour( 0 );
                imtodDmuObject.setTourNumber( 1 );
                imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
            }
            else if ( schoolTours.size() > 1 && person.getListOfWorkTours().size() == 0 ) {
                // Two school tour multiple tour pattern
                if ( i == 0 ) {
                    // first of 2 school tours
                    imtodDmuObject.setFirstTour( 1 );
                    imtodDmuObject.setSubsequentTour( 0 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
                }
                else {
                    // second of 2 school tours
                    imtodDmuObject.setFirstTour( 0 );
                    imtodDmuObject.setSubsequentTour( 1 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    int otherTourEndHour = schoolTours.get(0).getTourEndHour();
                    imtodDmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                }
            }
            else if ( schoolTours.size() == 1 && person.getListOfWorkTours().size() == 1 ) {
                // One school tour, one work tour multiple tour pattern
                if ( person.getPersonIsStudent() == 1 ) {
                    // student, so school tour is first scheduled, work comes later.
                    imtodDmuObject.setFirstTour( 1 );
                    imtodDmuObject.setSubsequentTour( 0 );
                    imtodDmuObject.setTourNumber( 1 );
                    imtodDmuObject.setEndOfPreviousScheduledTour( 0 );
                }
                else {
                    // worker, so work tour was already scheduled, this school tour is the second.
                    imtodDmuObject.setFirstTour( 0 );
                    imtodDmuObject.setSubsequentTour( 1 );
                    imtodDmuObject.setTourNumber( i + 1 );
                    int otherTourEndHour = person.getListOfWorkTours().get(0).getTourEndHour();
                    imtodDmuObject.setEndOfPreviousScheduledTour( otherTourEndHour );
                }
            }

            

            
            // set the choice availability and sample
            boolean[] departureTimeChoiceAvailability = person.getAvailableTimeWindows( altStarts, altEnds );
            Arrays.fill(schoolTourDepartureTimeChoiceSample, 1);
            
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


            if( household.getDebugChoiceModels() ) {
                household.logTourObject( loggingHeader, modelLogger, person, t );
            }


            schoolTourChoiceModel.computeUtilities ( imtodDmuObject, imtodDmuObject.getIndexValues(), departureTimeChoiceAvailability, schoolTourDepartureTimeChoiceSample );


            Random hhRandom = imtodDmuObject.getDmuHouseholdObject().getHhRandom();
            int randomCount = household.getHhRandomCount();
            double rn = hhRandom.nextDouble();

            // if the choice model has no available alternatives, choose between the first and last alternative.
            int chosen;
            if ( schoolTourChoiceModel.getAvailabilityCount() > 0 )
                chosen = schoolTourChoiceModel.getChoiceResult( rn );
            else
                chosen = rn < 0.5 ? 1 : 190;



            // schedule the chosen alternative
            int startHour = altStarts[chosen-1];
            int endHour = altEnds[chosen-1];
            person.scheduleWindow( startHour, endHour );

            household.updateTimeWindows();

            //int startIndex = startHour - CtrampApplication.START_HOUR;
            //int endIndex = endHour - CtrampApplication.START_HOUR;

            //modelResults[1][startIndex][endIndex]++;

            t.setTourStartHour( startHour );
            t.setTourEndHour( endHour );

            

            
            // debug output
            if( household.getDebugChoiceModels() ){

                double[] utilities     = schoolTourChoiceModel.getUtilities();
                double[] probabilities = schoolTourChoiceModel.getProbabilities();
                boolean[] availabilities = schoolTourChoiceModel.getAvailabilities();

                String personTypeString = person.getPersonType();
                int personNum = person.getPersonNum();
                modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString + ", Tour Id: " + t.getTourId() );
                modelLogger.info("Alternative            Availability           Utility       Probability           CumProb");
                modelLogger.info("--------------------   ------------    --------------    --------------    --------------");

                double cumProb = 0.0;
                for(int k=0; k < schoolTourChoiceModel.getNumberOfAlternatives(); k++){
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
                schoolTourChoiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                schoolTourChoiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

                // write UEC calculation results to separate model specific log file
                loggingHeader = String.format("%s  %s", choiceModelDescription, decisionMakerLabel );
                schoolTourChoiceModel.logUECResults( modelLogger, loggingHeader );
                
            }

            
        }

        if ( household.getDebugChoiceModels() ) {
            String decisionMakerLabel = String.format ( "Final School Departure Time Person Object: HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
            household.logPersonObject( decisionMakerLabel, modelLogger, person );
        }
        
        return schoolTours.size();

    }

}
