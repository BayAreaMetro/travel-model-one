package com.pb.models.ctramp.jppf;

import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.StopFrequencyDMU;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

import java.io.File;
import java.io.Serializable;
import java.util.*;

import org.apache.log4j.Logger;

/**
 * This class will be used for determining the number of stops
 * on individual mandatory, individual non-mandatory and joint
 * tours.
 *
 * @author Christi Willison
 * @version Nov 4, 2008
 *          <p/>
 *          Created by IntelliJ IDEA.
 */
public class StopFrequencyModel implements Serializable {
    
    private transient Logger logger = Logger.getLogger(StopFrequencyModel.class);
    private transient Logger stopFreqLogger = Logger.getLogger("stopFreqLog");

    private static final String PROPERTIES_UEC_STOP_FREQ = "UecFile.StopFrequency";
    private static final String PROPERTIES_STOP_PURPOSE_LOOKUP_FILE = "StopPurposeLookup.Proportions";
    
    

    private static final int UEC_DATA_PAGE = 0;

    // define names used in lookup file
    private static final String TOUR_PRIMARY_PURPOSE_COLUMN_HEADING = "PrimPurp";
    private static final String HALF_TOUR_DIRECTION_COLUMN_HEADING = "Direction";
    private static final String TOUR_DEPARTURE_START_RANGE_COLUMN_HEADING = "DepartRangeStart";
    private static final String TOUR_DEPARTURE_END_RANGE_COLUMN_HEADING = "DepartRangeEnd";
    private static final String PERSON_TYPE_COLUMN_HEADING = "Ptype";
    
    private static final String OUTBOUND_DIRECTION_NAME = "Outbound";    
    private static final String INBOUND_DIRECTION_NAME = "Inbound";    
    
    private static final String WORK_PURPOSE_NAME_IN_FILE = "Work";
    private static final String UNIVERSITY_PURPOSE_NAME_IN_FILE = "University";
    private static final String SCHOOL_PURPOSE_NAME_IN_FILE = "School";
    private static final String ESCORT_PURPOSE_NAME_IN_FILE = "Escort";
    private static final String SHOP_PURPOSE_NAME_IN_FILE = "Shop";
    private static final String OTH_MAINT_PURPOSE_NAME_IN_FILE = "Maintenance";
    private static final String EAT_OUT_PURPOSE_NAME_IN_FILE = "Eating Out";
    private static final String SOCIAL_PURPOSE_NAME_IN_FILE = "Visiting";
    private static final String OTH_DISCR_PURPOSE_NAME_IN_FILE = "Discretionary";
    private static final String AT_WORK_PURPOSE_NAME_IN_FILE = "Work-Based";
    
    
    private static final String FT_WORKER_PERSON_TYPE_NAME = "FT Worker";
    private static final String PT_WORKER_PERSON_TYPE_NAME = "PT Worker";
    private static final String UNIVERSITY_PERSON_TYPE_NAME = "University Student";
    private static final String NONWORKER_PERSON_TYPE_NAME = "Homemaker";
    private static final String RETIRED_PERSON_TYPE_NAME = "Retired";
    private static final String DRIVING_STUDENT_PERSON_TYPE_NAME = "Driving-age Child";
    private static final String NONDRIVING_STUDENT_PERSON_TYPE_NAME = "Pre-Driving Child";
    private static final String PRESCHOOL_PERSON_TYPE_NAME = "Preschool";
    private static final String ALL_PERSON_TYPE_NAME = "All";

    
    
    private TazDataIf tazDataManager;
    private ModelStructure modelStructure;

    private StopFrequencyDMU dmuObject;
	private ChoiceModelApplication[] choiceModelApplication;

    private HashMap<String,double[]>[] outProportionsMaps;
    private HashMap<String,double[]>[] inProportionsMaps;

    private int[] zoneTableRow;
    private int[] areaType;

    



    /**
     * Constructor that will be used to set up the ChoiceModelApplications for each
     * type of tour
     * @param projectDirectory - name of root level project directory
     * @param resourceBundle - properties file with paths identified
     * @param dmuObject - decision making unit for stop frequency
     * @param tazDataManager - holds information about TAZs in the model.
     */
    public StopFrequencyModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ) { 
        
        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;

        setupModels( propertyMap, dmuFactory );
       
    }



    private void setupModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) { 
        
        logger.info( String.format( "setting up stop frequency choice models." ) );
        
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        // locate the UEC
        String uecFileName = propertyMap.get( PROPERTIES_UEC_STOP_FREQ );
        uecFileName = projectDirectory + uecFileName;

        
        dmuObject = dmuFactory.getStopFrequencyDMU();

        
        float[] pkTransitRetail = tazDataManager.getPkTransitRetailAccessibity();
        float[] opTransitRetail = tazDataManager.getOpTransitRetailAccessibity();
        float[] nonMotorizedRetail = tazDataManager.getNonMotorizedRetailAccessibity();
        
        dmuObject.setZonalAccessibilities( pkTransitRetail, opTransitRetail, nonMotorizedRetail );

        
        // get the zone table row correspondence array for TAZs
        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();


        // set up the model array
        TreeSet<Integer> modelSheets = modelStructure.getStopFreqModelSheetIndices();
        choiceModelApplication = new ChoiceModelApplication[modelSheets.size()+1];     // one choice model for each model sheet specified
        for ( int i : modelSheets ) {
            if ( choiceModelApplication[i] == null )
                choiceModelApplication[i] = new ChoiceModelApplication( uecFileName, i, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        }

        
        String purposeLookupFileName = projectDirectory + propertyMap.get(PROPERTIES_STOP_PURPOSE_LOOKUP_FILE);
        
        // read the stop purpose lookup table data and populate the maps used to assign stop purposes
        readPurposeLookupProportionsTable( purposeLookupFileName );
        
    }



    public void applyModel( Household household ){

        int totalStops = 0;
        int totalTours = 0;

        Logger modelLogger = stopFreqLogger;
        if ( household.getDebugChoiceModels() )
            household.logHouseholdObject( "Pre Stop Frequency Choice: HH=" + household.getHhId(), stopFreqLogger );


        // get this household's person array
        Person[] personArray = household.getPersons();

        
        // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        dmuObject.setHouseholdObject(household);

        // process the joint tours for the household first
        Tour[] jt = household.getJointTourArray();
        if ( jt != null ) {

            List<Tour> tourList = new ArrayList<Tour>();
            
            for ( Tour t : jt )
                tourList.add( t );
            
            int tourCount = 0;
            for ( Tour tour : tourList ) {

                try {

                    int modelIndex = modelStructure.getStopFrequencyModelIndex( tour.getTourPurpose().toLowerCase() );

                    
                    // write debug header
                    String separator = "";
                    String choiceModelDescription = "" ;
                    String decisionMakerLabel = "";
                    String loggingHeader = "";
                    if( household.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "Joint Tour Stop Frequency Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, TourType=%s, TourId=%d, TourPurpose=%s.", household.getHhId(), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourId(), tour.getTourPurpose() );
                        
                        choiceModelApplication[modelIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        loggingHeader = choiceModelDescription + " for " + decisionMakerLabel;
                        for (int k=0; k < loggingHeader.length(); k++)
                            separator += "+";
                        modelLogger.info( loggingHeader );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                    }
                    
                     
                    
                    // set the tour object
                    dmuObject.setTourObject(tour);

                    // set the area type for the origin taz
                    int tableRow = zoneTableRow[tour.getTourOrigTaz()];
                    dmuObject.setOriginTazAreaType( areaType[tableRow-1] );

                    // set the area type for the primary destination taz
                    tableRow = zoneTableRow[tour.getTourDestTaz()];
                    dmuObject.setDestTazAreaType( areaType[tableRow-1] );

                    // compute the utilities
                    dmuObject.setDmuIndexValues( household.getHhId(), household.getHhTaz(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

                    choiceModelApplication[modelIndex].computeUtilities(dmuObject, dmuObject.getDmuIndexValues() );

                    // get the random number from the household
                    Random random = household.getHhRandom();
                    int randomCount = household.getHhRandomCount();
                    double rn = random.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    int choice = -1;
                    if ( choiceModelApplication[modelIndex].getAvailabilityCount() > 0 )
                        choice = choiceModelApplication[modelIndex].getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught applying joint tour stop frequency choice model for %s type tour: HHID=%d, tourCount=%d, randomCount=%f -- no avaialable stop frequency alternative to choose.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], household.getHhId(), tourCount, randomCount ) );
                        throw new RuntimeException();
                    }


                    // debug output
                    if( household.getDebugChoiceModels() ){

                        double[] utilities     = choiceModelApplication[modelIndex].getUtilities();
                        double[] probabilities = choiceModelApplication[modelIndex].getProbabilities();
                        String[] altNames = choiceModelApplication[modelIndex].getAlternativeNames();        // 0s-indexing

                        modelLogger.info( decisionMakerLabel );
                        modelLogger.info("Alternative                 Utility       Probability           CumProb");
                        modelLogger.info("------------------   --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for(int k=0;k<altNames.length;++k){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d %15s", k+1, altNames[k] );
                            modelLogger.info(String.format("%-20s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d  %s", choice, altNames[choice-1] );
                        modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");
                        

                        // write choice model alternative info to debug log file
                        choiceModelApplication[modelIndex].logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        choiceModelApplication[modelIndex].logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, choice );

                        // write UEC calculation results to separate model specific log file
                        choiceModelApplication[modelIndex].logUECResults( modelLogger, loggingHeader );
                        
                    }


                    
                    //choiceResultsFreq[choice][modelIndex]++;


                    // save the chosen alternative and create and populate the arrays of inbound/outbound stops in the tour object
                    totalStops += setStopFreqChoice ( tour, choice );
                    totalTours++;

                    tourCount++;

                }
                catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught processing joint tour stop frequency choice model for %s type tour:  HHID=%d, tourCount=%d.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], household.getHhId(), tourCount ) );
                    throw new RuntimeException(e);
                }

            }
            
            
        }

        
        
        
        
        
        // now loop through the person array (1-based), and process all tours for each person
        for(int j=1;j<personArray.length;++j){

            Person person = personArray[j];

            if ( household.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
                household.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
            
            // set the person
            dmuObject.setPersonObject(person);

            List<Tour> tourList = new ArrayList<Tour>();
            
            // apply stop frequency for all person tours
            tourList.addAll( person.getListOfWorkTours() );
            tourList.addAll( person.getListOfSchoolTours() );
            tourList.addAll( person.getListOfIndividualNonMandatoryTours() );
            tourList.addAll( person.getListOfAtWorkSubtours() );

            int tourCount = 0;
            for ( Tour tour : tourList ) {

                int modelIndex = -1;
                try {

                    modelIndex = modelStructure.getStopFrequencyModelIndex( tour.getTourPurpose().toLowerCase() );

                    
                    // write debug header
                    String separator = "";
                    String choiceModelDescription = "" ;
                    String decisionMakerLabel = "";
                    String loggingHeader = "";
                    if( household.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "Individual Tour Stop Frequency Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourType=%s, TourId=%d, TourPurpose=%s.", household.getHhId(), person.getPersonNum(), person.getPersonType(), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourId(), tour.getTourPurpose() );
                        
                        choiceModelApplication[modelIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        loggingHeader = choiceModelDescription + " for " + decisionMakerLabel;
                        for (int k=0; k < loggingHeader.length(); k++)
                            separator += "+";
                        modelLogger.info( loggingHeader );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                    }
                    
                     
                    
                    // set the tour object
                    dmuObject.setTourObject(tour);

                    // set the area type for the origin taz
                    int tableRow = zoneTableRow[tour.getTourOrigTaz()];
                    dmuObject.setOriginTazAreaType( areaType[tableRow-1] );

                    // set the area type for the primary destination taz
                    tableRow = zoneTableRow[tour.getTourDestTaz()];
                    dmuObject.setDestTazAreaType( areaType[tableRow-1] );

                    // compute the utilities
                    dmuObject.setDmuIndexValues( household.getHhId(), household.getHhTaz(), tour.getTourOrigTaz(), tour.getTourDestTaz() );

                    choiceModelApplication[modelIndex].computeUtilities(dmuObject, dmuObject.getDmuIndexValues() );

                    // get the random number from the household
                    Random random = household.getHhRandom();
                    int randomCount = household.getHhRandomCount();
                    double rn = random.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    int choice = -1;
                    if ( choiceModelApplication[modelIndex].getAvailabilityCount() > 0 )
                        choice = choiceModelApplication[modelIndex].getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught applying Individual Tour stop frequency choice model for %s type tour: j=%d, HHID=%d, personNum=%d, tourCount=%d, randomCount=%f -- no avaialable stop frequency alternative to choose.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], j, household.getHhId(), person.getPersonNum(), tourCount, randomCount ) );
                        throw new RuntimeException();
                    }



                    // debug output
                    if( household.getDebugChoiceModels() ){

                        double[] utilities     = choiceModelApplication[modelIndex].getUtilities();
                        double[] probabilities = choiceModelApplication[modelIndex].getProbabilities();
                        String[] altNames = choiceModelApplication[modelIndex].getAlternativeNames();        // 0s-indexing

                        modelLogger.info( decisionMakerLabel );
                        modelLogger.info("Alternative                 Utility       Probability           CumProb");
                        modelLogger.info("------------------   --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for(int k=0;k<altNames.length;++k){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d %15s", k+1, altNames[k] );
                            modelLogger.info(String.format("%-20s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d  %s", choice, altNames[choice-1] );
                        modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");
                        

                        // write choice model alternative info to debug log file
                        choiceModelApplication[modelIndex].logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        choiceModelApplication[modelIndex].logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, choice );

                        // write UEC calculation results to separate model specific log file
                        choiceModelApplication[modelIndex].logUECResults( modelLogger, loggingHeader );
                        
                    }


                    
                    //choiceResultsFreq[choice][modelIndex]++;


                    // save the chosen alternative and create and populate the arrays of inbound/outbound stops in the tour object
                    totalStops += setStopFreqChoice ( tour, choice );
                    totalTours++;

                    tourCount++;

                }
                catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught processing Individual Tour stop frequency choice model for %s type tour, tourPurpose=%s, modelINdex=%d:  j=%d, HHID=%d, personNum=%d, tourCount=%d.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), modelIndex, j, household.getHhId(), person.getPersonNum(), tourCount ) );
                    throw new RuntimeException(e);
                }

            }


        } // j (person loop)

        household.setStfRandomCount( household.getHhRandomCount() );
        
    }



    private int setStopFreqChoice ( Tour tour, int stopFreqChoice ) {

        tour.setStopFreqChoice ( stopFreqChoice );


        // set argument values for method call to get stop purpose
        Household hh = tour.getPersonObject().getHouseholdObject();
        int tourDepartHour = tour.getTourStartHour();
        String tourPrimaryPurpose = tour.getTourPrimaryPurpose();
        String personType = tour.getPersonObject().getPersonType();
        
        
        int numObStops = dmuObject.getNumObStopsAlt(stopFreqChoice);
        if ( numObStops > 0 ) {
            // get a stop purpose for each outbound stop generated, plus the stop at the primary destination
            String[] obStopOrigPurposes = new String[numObStops+1];
            String[] obStopDestPurposes = new String[numObStops+1];
            obStopOrigPurposes[0] = tour.getTourCategoryIsAtWork() ? "Work" : "Home";
            // the last stop record is for the trip from stop to destination
            for ( int i=0; i < numObStops; i++ ) {
                if ( i > 0 )
                    obStopOrigPurposes[i] = obStopDestPurposes[i-1];
                obStopDestPurposes[i] = getStopPurpose ( hh, OUTBOUND_DIRECTION_NAME, tourDepartHour, tourPrimaryPurpose, personType );
            }
            obStopOrigPurposes[numObStops] = obStopDestPurposes[numObStops-1];
            obStopDestPurposes[numObStops] = tourPrimaryPurpose;
            
            tour.createOutboundStops( modelStructure, obStopOrigPurposes, obStopDestPurposes );
        }
        
        
        int numIbStops = dmuObject.getNumIbStopsAlt(stopFreqChoice);
        if ( numIbStops > 0 ) {
            // get a stop purpose for each inbound stop generated
            String[] ibStopOrigPurposes = new String[numIbStops+1];
            String[] ibStopDestPurposes = new String[numIbStops+1];
            ibStopOrigPurposes[0] = tourPrimaryPurpose;
            // the last stop record is for the trip from stop to home or work
            for ( int i=0; i < numIbStops; i++ ) {
                if ( i > 0 )
                    ibStopOrigPurposes[i] = ibStopDestPurposes[i-1];
                ibStopDestPurposes[i] = getStopPurpose ( hh, INBOUND_DIRECTION_NAME, tourDepartHour, tourPrimaryPurpose, personType );
            }
            ibStopOrigPurposes[numIbStops] = ibStopDestPurposes[numIbStops-1];
            ibStopDestPurposes[numIbStops] = tour.getTourCategoryIsAtWork() ? "Work" : "Home";

            tour.createInboundStops( modelStructure, ibStopOrigPurposes, ibStopDestPurposes );
        }

        
        return numObStops + numIbStops;

    }

    private void readPurposeLookupProportionsTable( String purposeLookupFilename ) {

        // read the stop purpose proportions into a TableDataSet
        TableDataSet purposeLookupTable = null;
        String fileName = "";
        try{
            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            purposeLookupTable =  reader.readFile(
                    new File( purposeLookupFilename )
            );
        }
        catch(Exception e){
            logger.error( String.format( "Exception occurred reading stop purpose lookup proportions file: %s.", fileName ),e);
            throw new RuntimeException();
        }
        
        
        // allocate a HashMap array for each direction, dimensioned to maximum departure hour, to map keys determined by combination of categories to proportions arrays.
        int numDepartHours = CtrampApplication.LAST_HOUR + 1;
        outProportionsMaps = new HashMap[numDepartHours];
        inProportionsMaps = new HashMap[numDepartHours];
        for ( int i=CtrampApplication.START_HOUR; i < numDepartHours; i++ ) {
            outProportionsMaps[i] = new HashMap<String,double[]>();
            inProportionsMaps[i] = new HashMap<String,double[]>();
        }
        

        // create a mapping between names used in lookup file and purpose names used in model
        HashMap<String,String> primaryPurposeMap = new HashMap<String,String>();
        primaryPurposeMap.put( WORK_PURPOSE_NAME_IN_FILE, ModelStructure.WORK_PURPOSE_NAME );
        primaryPurposeMap.put( UNIVERSITY_PURPOSE_NAME_IN_FILE, ModelStructure.UNIVERSITY_PURPOSE_NAME );
        primaryPurposeMap.put( SCHOOL_PURPOSE_NAME_IN_FILE, ModelStructure.SCHOOL_PURPOSE_NAME );
        primaryPurposeMap.put( ESCORT_PURPOSE_NAME_IN_FILE, ModelStructure.ESCORT_PURPOSE_NAME );
        primaryPurposeMap.put( SHOP_PURPOSE_NAME_IN_FILE, ModelStructure.SHOPPING_PURPOSE_NAME );
        primaryPurposeMap.put( EAT_OUT_PURPOSE_NAME_IN_FILE, ModelStructure.EAT_OUT_PURPOSE_NAME );
        primaryPurposeMap.put( OTH_MAINT_PURPOSE_NAME_IN_FILE, ModelStructure.OTH_MAINT_PURPOSE_NAME );
        primaryPurposeMap.put( SOCIAL_PURPOSE_NAME_IN_FILE, ModelStructure.SOCIAL_PURPOSE_NAME );
        primaryPurposeMap.put( OTH_DISCR_PURPOSE_NAME_IN_FILE, ModelStructure.OTH_DISCR_PURPOSE_NAME );
        primaryPurposeMap.put( AT_WORK_PURPOSE_NAME_IN_FILE, ModelStructure.AT_WORK_PURPOSE_NAME );
        
        
        // create a mapping between names used in lookup file and person type names used in model
        HashMap<String,String> personTypeMap = new HashMap<String,String>();
        personTypeMap.put( FT_WORKER_PERSON_TYPE_NAME, Person.PERSON_TYPE_FULL_TIME_WORKER_NAME );
        personTypeMap.put( PT_WORKER_PERSON_TYPE_NAME, Person.PERSON_TYPE_PART_TIME_WORKER_NAME );
        personTypeMap.put( UNIVERSITY_PERSON_TYPE_NAME, Person.PERSON_TYPE_UNIVERSITY_STUDENT_NAME );
        personTypeMap.put( NONWORKER_PERSON_TYPE_NAME, Person.PERSON_TYPE_NON_WORKER_NAME );
        personTypeMap.put( RETIRED_PERSON_TYPE_NAME, Person.PERSON_TYPE_RETIRED_NAME );
        personTypeMap.put( DRIVING_STUDENT_PERSON_TYPE_NAME, Person.PERSON_TYPE_STUDENT_DRIVING_NAME );
        personTypeMap.put( NONDRIVING_STUDENT_PERSON_TYPE_NAME, Person.PERSON_TYPE_STUDENT_NON_DRIVING_NAME );
        personTypeMap.put( PRESCHOOL_PERSON_TYPE_NAME, Person.PERSON_TYPE_PRE_SCHOOL_CHILD_NAME );
        personTypeMap.put( ALL_PERSON_TYPE_NAME, ALL_PERSON_TYPE_NAME );


        
        
        // fields in lookup file are:
        // PrimPurp    Direction   DepartRangeStart    DepartRangeEnd  Ptype   Work    University  School  Escort  Shop    Maintenance Eating Out  Visiting    Discretionary
        
        // populate the outProportionsMaps and inProportionsMaps arrays of maps from data in the TableDataSet.
        // when stops are generated, they can lookup the proportions for stop purpose selection from a map determined
        // by tour purpose, person type, outbound/inbound direction and tour departure time.  From these proportions,
        // a stop purpose can be drawn.
        
        
        // loop over rows in the TableDataSet
        for ( int i=0; i < purposeLookupTable.getRowCount(); i++ ) {

            // get the tour primary purpose
            String tourPrimPurp = primaryPurposeMap.get( purposeLookupTable.getStringValueAt( i+1, TOUR_PRIMARY_PURPOSE_COLUMN_HEADING ) );
            
            // get the half tour direction
            String direction = purposeLookupTable.getStringValueAt( i+1, HALF_TOUR_DIRECTION_COLUMN_HEADING );
            
            // get the beginning of the range of departure hours
            int startRange = (int)purposeLookupTable.getValueAt( i+1, TOUR_DEPARTURE_START_RANGE_COLUMN_HEADING );
            
            // get the end of the range of departure hours
            int endRange = (int)purposeLookupTable.getValueAt( i+1, TOUR_DEPARTURE_END_RANGE_COLUMN_HEADING );
                        
            
            // get the person type
            String personType = personTypeMap.get( purposeLookupTable.getStringValueAt( i+1, PERSON_TYPE_COLUMN_HEADING ) );

            
            // columns following person type are proportions by stop purpose.  Get the index of the first stop purpose proportion.
            int firstPropColumn = purposeLookupTable.getColumnPosition( PERSON_TYPE_COLUMN_HEADING ) + 1;

            // starting at this column, read the proportions for all stop purposes.
            // Create the array of proportions for this table record.  Dimensions is size of map-1 (no atwork stop purpose).
            // since indexing starts at 1, would normally add 1, but no need to add 1 to dimension (because we don't need the at-work purpose)
            double[] props = new double[primaryPurposeMap.size()];
            for ( int j=1; j < props.length; j++ ) {
                props[j] = purposeLookupTable.getValueAt( i+1, firstPropColumn + j - 1 );
            }
            
            
            // get a HashMap for the direction and each hour in the start/end range, and store the proportions in that map for the key.
            // the key to use for any of these HashMaps is created consisting of "TourPrimPurp_PersonType"
            // if the person type for the record is "All", a key is defined for each person type, and the proportions stored for each key.
            if ( personType.equalsIgnoreCase( ALL_PERSON_TYPE_NAME ) ) {
                for ( String ptype : personTypeMap.values() ) {
                    String key = tourPrimPurp + "_" + ptype;
                    if ( direction.equalsIgnoreCase( OUTBOUND_DIRECTION_NAME ) ) {
                        for ( int k=startRange; k <= endRange; k++ )
                            outProportionsMaps[k].put(key, props);
                    }
                    else if ( direction.equalsIgnoreCase( INBOUND_DIRECTION_NAME ) ) {
                        for ( int k=startRange; k <= endRange; k++ )
                            inProportionsMaps[k].put(key, props);                
                    }
                }
            }
            else {
                String key = tourPrimPurp + "_" + personType;
                if ( direction.equalsIgnoreCase( OUTBOUND_DIRECTION_NAME ) ) {
                    for ( int k=startRange; k <= endRange; k++ )
                        outProportionsMaps[k].put(key, props);
                }
                else if ( direction.equalsIgnoreCase( INBOUND_DIRECTION_NAME ) ) {
                    for ( int k=startRange; k <= endRange; k++ )
                        inProportionsMaps[k].put(key, props);                
                }
            }
            
        }
        
    }

    
    
    private String getStopPurpose ( Household household, String halfTourDirection, int tourDepartHour, String tourPrimaryPurpose, String personType ) {
        
        double[] props = null;
        String key = tourPrimaryPurpose + "_" + personType;
        if ( halfTourDirection.equalsIgnoreCase( OUTBOUND_DIRECTION_NAME ) )
            props = outProportionsMaps[tourDepartHour].get(key);
        else if ( halfTourDirection.equalsIgnoreCase( INBOUND_DIRECTION_NAME ) )
            props = inProportionsMaps[tourDepartHour].get(key);

        double rn = household.getHhRandom().nextDouble();
        int choice = ChoiceModelApplication.getMonteCarloSelection( props, rn );
        
        return modelStructure.getPrimaryPurposeForIndex( choice );
        
    }
    
}
