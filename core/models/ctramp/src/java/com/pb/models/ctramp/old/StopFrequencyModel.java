package com.pb.models.ctramp.old;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.StopFrequencyDMU;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

import java.io.File;
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
public class StopFrequencyModel {
    public static Logger logger = Logger.getLogger(StopFrequencyModel.class);

    public static final String PROPERTIES_UEC_STOP_FREQ = "UecFile.StopFrequency";
    public static final String PROPERTIES_STOP_PURPOSE_LOOKUP_FILE = "StopPurposeLookup.Proportions";
    
    

    private static final int UEC_DATA_PAGE = 0;
    private static final int WORK_UEC_MODEL_PAGE = 1;
    private static final int UNIVERSITY_UEC_MODEL_PAGE = 2;
    private static final int SCHOOL_UEC_MODEL_PAGE = 3;
    private static final int ESCORT_UEC_MODEL_PAGE = 4;
    private static final int SHOPPING_UEC_MODEL_PAGE = 5;
    private static final int EAT_OUT_UEC_MODEL_PAGE = 7;
    private static final int OTH_MAINT_STUDENT_UEC_MODEL_PAGE = 6;
    private static final int SOCIAL_STUDENT_UEC_MODEL_PAGE = 7;
    private static final int OTH_DISCR_UEC_MODEL_PAGE = 8;
    private static final int AT_WORK_UEC_MODEL_PAGE = 9;
    private static final int NUM_PURPOSE_MODEL_PAGES = 10;

    // define names used in lookup file
    private static final String TOUR_PRIMARY_PURPOSE_COLUMN_HEADING = "PrimPurp";
    private static final String HALF_TOUR_DIRECTION_COLUMN_HEADING = "Direction";
    private static final String TOUR_DEPARTURE_START_RANGE_COLUMN_HEADING = "DepartRangeStart";
    private static final String TOUR_DEPARTURE_END_RANGE_COLUMN_HEADING = "DepartRangeEnd";
    private static final String PERSON_TYPE_COLUMN_HEADING = "Ptype";
    
    private static final String OUTBOUND_DIRECTION_NAME = "Outbound";    
    private static final String INBOUND_DIRECTION_NAME = "Inbound";    
    
    private static final String WORK_PRIMARY_PURPOSE_NAME = "Work";
    private static final String UNIVERSITY_PRIMARY_PURPOSE_NAME = "University";
    private static final String SCHOOL_PRIMARY_PURPOSE_NAME = "School";
    private static final String ESCORT_PRIMARY_PURPOSE_NAME = "Escort";
    private static final String SHOP_PRIMARY_PURPOSE_NAME = "Shop";
    private static final String OTH_MAINT_PRIMARY_PURPOSE_NAME = "Maintenance";
    private static final String EAT_OUT_PRIMARY_PURPOSE_NAME = "Eating Out";
    private static final String SOCIAL_PRIMARY_PURPOSE_NAME = "Visiting";
    private static final String OTH_DISCR_PRIMARY_PURPOSE_NAME = "Discretionary";
    private static final String AT_WORK_PRIMARY_PURPOSE_NAME = "Work-Based";
    
    private static final String FT_WORKER_PERSON_TYPE_NAME = "FT Worker";
    private static final String PT_WORKER_PERSON_TYPE_NAME = "PT Worker";
    private static final String UNIVERSITY_PERSON_TYPE_NAME = "University Student";
    private static final String NONWORKER_PERSON_TYPE_NAME = "Homemaker";
    private static final String RETIRED_PERSON_TYPE_NAME = "Retired";
    private static final String DRIVING_STUDENT_PERSON_TYPE_NAME = "Driving-age Child";
    private static final String NONDRIVING_STUDENT_PERSON_TYPE_NAME = "Pre-Driving Child";
    private static final String PRESCHOOL_PERSON_TYPE_NAME = "Preschool";
    private static final String ALL_PERSON_TYPE_NAME = "All";

    private static final int FIRST_DEPART_HOUR = 5;
    private static final int LAST_DEPART_HOUR = 23;
    
    
    
    protected TazDataIf tazDataManager;
    protected ModelStructure modelStructure;

    protected StopFrequencyDMU dmuObject;
	protected ChoiceModelApplication[] choiceModelApplication;

    protected HashMap<String, Integer> tourPurposeMap;

    protected HashMap<Integer,String> indexPurposeMap;
    protected HashMap<String,double[]>[] outProportionsMaps;
    protected HashMap<String,double[]>[] inProportionsMaps;

    protected int[] zoneTableRow;
    protected int[] areaType;

    
    protected int[][] choiceResultsFreq;



    /**
     * Constructor that will be used to set up the ChoiceModelApplications for each
     * type of tour
     * @param projectDirectory - name of root level project directory
     * @param resourceBundle - properties file with paths identified
     * @param dmuObject - decision making unit for stop frequency
     * @param tazDataManager - holds information about TAZs in the model.
     */
    public StopFrequencyModel( String projectDirectory, ResourceBundle resourceBundle, StopFrequencyDMU dmuObject, TazDataIf tazDataManager, ModelStructure modelStructure ) {

        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;
        this.dmuObject = dmuObject;

        // get the zone table row correspondence array for TAZs
        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        // locate the UEC
        String uecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_STOP_FREQ);
        uecFileName = projectDirectory + uecFileName;

        tourPurposeMap = new HashMap<String, Integer>();
        tourPurposeMap.put( modelStructure.WORK_PURPOSE_NAME, 1 );
        tourPurposeMap.put( modelStructure.UNIVERSITY_PURPOSE_NAME, 2 );
        tourPurposeMap.put( modelStructure.SCHOOL_PURPOSE_NAME, 3 );
        tourPurposeMap.put( modelStructure.ESCORT_PURPOSE_NAME, 4 );
        tourPurposeMap.put( modelStructure.SHOPPING_PURPOSE_NAME, 5 );
        tourPurposeMap.put( modelStructure.EAT_OUT_PURPOSE_NAME, 6 );
        tourPurposeMap.put( modelStructure.OTH_MAINT_PURPOSE_NAME, 7 );
        tourPurposeMap.put( modelStructure.SOCIAL_PURPOSE_NAME, 8 );
        tourPurposeMap.put( modelStructure.OTH_DISCR_PURPOSE_NAME, 9 );
        tourPurposeMap.put( modelStructure.AT_WORK_PURPOSE_NAME, 10 );

        // set up the model
        choiceModelApplication = new ChoiceModelApplication[NUM_PURPOSE_MODEL_PAGES+1];     // one choice model for each person type that has model specified; Ones indexing for personType.
        choiceModelApplication[1] = new ChoiceModelApplication( uecFileName, WORK_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[2] = new ChoiceModelApplication( uecFileName, UNIVERSITY_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[3] = new ChoiceModelApplication( uecFileName, SCHOOL_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[4] = new ChoiceModelApplication( uecFileName, ESCORT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[5] = new ChoiceModelApplication( uecFileName, SHOPPING_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[6] = new ChoiceModelApplication( uecFileName, EAT_OUT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[7] = new ChoiceModelApplication( uecFileName, OTH_MAINT_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[8] = new ChoiceModelApplication( uecFileName, SOCIAL_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[9] = new ChoiceModelApplication( uecFileName, OTH_DISCR_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[10] = new ChoiceModelApplication( uecFileName, AT_WORK_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );

        int numberOfAlternatives = choiceModelApplication[1].getNumberOfAlternatives();
        choiceResultsFreq = new int[numberOfAlternatives+1][NUM_PURPOSE_MODEL_PAGES+1];

        
        // read the stop purpose lookup table data and populate the maps used to assign stop purposes
        readPurposeLookupProportionsTable( projectDirectory, resourceBundle );
        
    }



    public void applyModel(HouseholdDataManagerIf householdDataManager){

        // set the availability array for the tour frequency model
        // same number of alternatives for each person type, so use person type 1 to get num alts.
        int numberOfAlternatives = choiceModelApplication[1].getNumberOfAlternatives();
        boolean[] availabilityArray = new boolean[numberOfAlternatives+1];
        Arrays.fill(availabilityArray,true);

        // create the sample array
        int[] sampleArray = new int[availabilityArray.length];
        Arrays.fill(sampleArray, 1);


        float[] pkTransitRetail = tazDataManager.getPkTransitRetailAccessibity();
        float[] opTransitRetail = tazDataManager.getOpTransitRetailAccessibity();
        float[] nonMotorizedRetail = tazDataManager.getNonMotorizedRetailAccessibity();
        
        dmuObject.setZonalAccessibilities( pkTransitRetail, opTransitRetail, nonMotorizedRetail );

        int totalStops = 0;
        int totalTours = 0;

        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();


        // loop the households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];

            // get this household's person array
            Person[] personArray = household.getPersons();

            // set the household id, origin taz, hh taz, and debugFlag=false in the dmu
            dmuObject.setHouseholdObject(household);

            // add the joint tours for the household
            List<Tour> tourList = new ArrayList<Tour>();
            Tour[] jt = household.getJointTourArray();
            if ( jt != null ) {
                for ( Tour t : jt )
                    tourList.add( t );
            }
            
            // loop through the person array (1-based)
            for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];

                // set the person
                dmuObject.setPersonObject(person);

                // apply stop frequency for all person tours
                tourList.addAll( person.getListOfWorkTours() );
                tourList.addAll( person.getListOfSchoolTours() );
                tourList.addAll( person.getListOfIndividualNonMandatoryTours() );
                tourList.addAll( person.getListOfAtWorkSubtours() );

                int tourCount = 0;
                for ( Tour tour : tourList ) {

                    try {

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

                        int modelIndex = getModelIndexForTourPurpose ( tour.getTourPurpose() );
                        choiceModelApplication[modelIndex].computeUtilities(dmuObject, dmuObject.getDmuIndexValues(), availabilityArray, sampleArray);

                        // get the random number from the household
                        Random random = household.getHhRandom();
                        double randomNumber = random.nextDouble();


                        // if the choice model has at least one available alternative, make choice.
                        int choice = -1;
                        if ( choiceModelApplication[modelIndex].getAvailabilityCount() > 0 )
                            choice = choiceModelApplication[modelIndex].getChoiceResult( randomNumber );
                        else {
                            logger.error ( String.format( "Exception caught applying stop frequency choice model for %s type tour:  i=%d, j=%d, HHID=%d, personNum=%d, tourCount=%d -- no avaialable stop frequency alternative to choose.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], i, j, household.getHhId(), person.getPersonNum(), tourCount ) );
                            throw new RuntimeException();
                        }


                        choiceResultsFreq[choice][modelIndex]++;


                        // save the chosen alternative and create and populate the arrays of inbound/outbound stops in the tour object
                        totalStops += setStopFreqChoice ( tour, choice );
                        totalTours++;

                        tourCount++;

                    }
                    catch ( Exception e ) {
                        logger.error ( String.format( "Exception caught processing stop frequency choice model for %s type tour:  i=%d, j=%d, HHID=%d, personNum=%d, tourCount=%d.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], i, j, household.getHhId(), person.getPersonNum(), tourCount ) );
                        throw new RuntimeException(e);
                    }

                }


            } // j (person loop)

        } // i (household loop)

        logger.info ( "" );
        logger.info ( "" );
        logger.info ( String.format ( "Stop Frequency Model applied on %d tours, creating %d stops.", totalTours, totalStops ) );

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setStfRandomCount();

    }


    /**
     * Logs the results of the model.
     *
     */
    public void logResults(){

        String[] altLabels = choiceModelApplication[1].getAlternativeNames();

        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info("Stops On Tour Frequency Model Results");


        logger.info(" ");
        logger.info ( String.format( "%-5s   %-20s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s", "alt", "alt name", "work", "univ", "school", "escort", "shop", "eat out", "maint", "visit", "discr", "total" ) );


        String logString = "";

        int[] columnTotals = new int[NUM_PURPOSE_MODEL_PAGES+1];
        for ( int i=0; i < altLabels.length; i++ ) {

            logString = String.format( "%-5d   %-20s", i+1, altLabels[i] );

            int rowTotal = 0;
            for ( int j=1; j < columnTotals.length; j++ ) {
                columnTotals[j] += choiceResultsFreq[i+1][j];
                rowTotal += choiceResultsFreq[i+1][j];
                logString += String.format( "   %8d", choiceResultsFreq[i+1][j] );
            }

            logString += String.format( "   %8d", rowTotal );
            logger.info ( logString );

        }

        int rowTotal = 0;
        logString = String.format( "%-5s   %-20s", "total", "" );
        for ( int j=1; j < columnTotals.length; j++ ) {
            rowTotal += columnTotals[j];
            logString += String.format( "   %8d", columnTotals[j] );
        }

        logString += String.format( "   %8d", rowTotal );
        logger.info ( logString );

        logger.info(" ");
        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");

    }



    private int getModelIndexForTourPurpose ( String tourPurpose ) {
       return tourPurposeMap.get( tourPurpose);
    }



    private int setStopFreqChoice ( Tour tour, int stopFreqChoice ) {

        tour.setStopFreqChoice ( stopFreqChoice );


        // set argument values for method call to get stop purpose
        Household hh = tour.getPersonObject().getHouseholdObject();
        int tourDepartHour = tour.getTourStartHour();
        String tourPrimaryPurpose = tour.getTourPurpose();
        String personType = tour.getPersonObject().getPersonType();
        
        int numObStops = dmuObject.getNumObStopsAlt(stopFreqChoice);

        // get a stop purpose for each outbound stop generated
        String[] obStopOrigPurposes = new String[numObStops];
        String[] obStopDestPurposes = new String[numObStops];
        obStopOrigPurposes[0] = "Home";
        for ( int i=0; i < numObStops; i++ ) {
            if ( i > 0 )
                obStopOrigPurposes[i] = obStopDestPurposes[i-1];
            obStopDestPurposes[i] = getStopPurpose ( hh, OUTBOUND_DIRECTION_NAME, tourDepartHour, tourPrimaryPurpose, personType );
        }
        
        // pass in the array of stop purposes; length of array dtermines number of outbound stop objects created.
        tour.createOutboundStops( modelStructure, obStopOrigPurposes, obStopDestPurposes );

        
        
        int numIbStops = dmuObject.getNumIbStopsAlt(stopFreqChoice);

        // get a stop purpose for each inbound stop generated
        String[] ibStopOrigPurposes = new String[numIbStops];
        String[] ibStopDestPurposes = new String[numIbStops];
        ibStopOrigPurposes[0] = tour.getTourPurpose();
        for ( int i=0; i < numIbStops; i++ ) {
            if ( i > 0 )
                ibStopOrigPurposes[i] = ibStopDestPurposes[i-1];
            ibStopDestPurposes[i] = getStopPurpose ( hh, INBOUND_DIRECTION_NAME, tourDepartHour, tourPrimaryPurpose, personType );
        }
        
        // pass in the array of stop purposes; length of array dtermines number of outbound stop objects created.
        tour.createInboundStops( modelStructure, ibStopOrigPurposes, ibStopDestPurposes );

        
        
        return numObStops + numIbStops;

    }

    private void readPurposeLookupProportionsTable( String projectDirectory, ResourceBundle resourceBundle ) {

        // read the stop purpose proportions into a TableDataSet
        TableDataSet purposeLookupTable = null;
        String fileName = "";
        try{
            CSVFileReader reader = new CSVFileReader();
            fileName = projectDirectory + resourceBundle.getString(PROPERTIES_STOP_PURPOSE_LOOKUP_FILE);
            purposeLookupTable =  reader.readFile(
                    new File( fileName )
            );
        }
        catch(Exception e){
            logger.error( String.format( "Exception occurred reading stop purpose lookup proportions file: %s.", fileName ),e);
            throw new RuntimeException();
        }
        
        
        // allocate a HashMap array for each direction, dimensioned to maximum departure hour, to map keys determined by combination of categories to proportions arrays.
        int numDepartHours = LAST_DEPART_HOUR + 1;
        outProportionsMaps = new HashMap[numDepartHours];
        inProportionsMaps = new HashMap[numDepartHours];
        for ( int i=FIRST_DEPART_HOUR; i < numDepartHours; i++ ) {
            outProportionsMaps[i] = new HashMap<String,double[]>();
            inProportionsMaps[i] = new HashMap<String,double[]>();
        }
        

        // create a mapping between names used in lookup file and purpose names used in model
        HashMap<String,String> primaryPurposeMap = new HashMap<String,String>();
        primaryPurposeMap.put( WORK_PRIMARY_PURPOSE_NAME, modelStructure.WORK_PURPOSE_NAME );
        primaryPurposeMap.put( UNIVERSITY_PRIMARY_PURPOSE_NAME, modelStructure.UNIVERSITY_PURPOSE_NAME );
        primaryPurposeMap.put( SCHOOL_PRIMARY_PURPOSE_NAME, modelStructure.SCHOOL_PURPOSE_NAME );
        primaryPurposeMap.put( ESCORT_PRIMARY_PURPOSE_NAME, modelStructure.ESCORT_PURPOSE_NAME );
        primaryPurposeMap.put( SHOP_PRIMARY_PURPOSE_NAME, modelStructure.SHOPPING_PURPOSE_NAME );
        primaryPurposeMap.put( EAT_OUT_PRIMARY_PURPOSE_NAME, modelStructure.EAT_OUT_PURPOSE_NAME );
        primaryPurposeMap.put( OTH_MAINT_PRIMARY_PURPOSE_NAME, modelStructure.OTH_MAINT_PURPOSE_NAME );
        primaryPurposeMap.put( SOCIAL_PRIMARY_PURPOSE_NAME, modelStructure.SOCIAL_PURPOSE_NAME );
        primaryPurposeMap.put( OTH_DISCR_PRIMARY_PURPOSE_NAME, modelStructure.OTH_DISCR_PURPOSE_NAME );
        primaryPurposeMap.put( AT_WORK_PRIMARY_PURPOSE_NAME, modelStructure.AT_WORK_PURPOSE_NAME );
        
        // create a mapping between stop purpose alternative indices selected from monte carlo process and primary purpose names used in model
        // the indices are the order of the proportions columns in the table
        indexPurposeMap = new HashMap<Integer,String>();
        indexPurposeMap.put( 1, modelStructure.WORK_PURPOSE_NAME );
        indexPurposeMap.put( 2, modelStructure.UNIVERSITY_PURPOSE_NAME );
        indexPurposeMap.put( 3, modelStructure.SCHOOL_PURPOSE_NAME );
        indexPurposeMap.put( 4, modelStructure.ESCORT_PURPOSE_NAME );
        indexPurposeMap.put( 5, modelStructure.SHOPPING_PURPOSE_NAME );
        indexPurposeMap.put( 6, modelStructure.OTH_MAINT_PURPOSE_NAME );
        indexPurposeMap.put( 7, modelStructure.EAT_OUT_PURPOSE_NAME );
        indexPurposeMap.put( 8, modelStructure.SOCIAL_PURPOSE_NAME );
        indexPurposeMap.put( 9, modelStructure.OTH_DISCR_PURPOSE_NAME );
        
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
            // Create the array of proportions for this table record.
            double[] props = new double[indexPurposeMap.size()+1];
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
        
        return indexPurposeMap.get( choice );
        
    }
    
}
