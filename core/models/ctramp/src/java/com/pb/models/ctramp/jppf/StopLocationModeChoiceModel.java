package com.pb.models.ctramp.jppf;

import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.util.IndexSort;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.ParkingChoiceDMU;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Stop;
import com.pb.models.ctramp.StopDestChoiceSize;
import com.pb.models.ctramp.StopLocationDMU;
import com.pb.models.ctramp.TNCAndTaxiWaitTimeCalculator;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.TripModeChoiceDMU;

import java.io.File;
import java.io.IOException;
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
public class StopLocationModeChoiceModel implements Serializable {
    
    private transient Logger logger = Logger.getLogger(StopLocationModeChoiceModel.class);
    private transient Logger slcLogger = Logger.getLogger("slcLogger");
    private transient Logger tripDepartLogger = Logger.getLogger("tripDepartLog");
    private transient Logger tripMcLogger = Logger.getLogger("tripMcLog");
    private transient Logger parkLocLogger = Logger.getLogger("parkLocLog");

    private static final int HOME_TYPE_INDEX = 1;
    private static final int PRIM_DEST_TYPE_INDEX = 2;
    private static final int INT_STOP_TYPE_INDEX = 3;
    
    private static final String PROPERTIES_UEC_STOP_LOCATION = "UecFile.StopLocation";
    public static final String PROPERTIES_UEC_TRIP_MODE_CHOICE = "UecFile.TripModeChoice";
    private static final String PROPERTIES_UEC_PARKING_LOCATION_CHOICE = "UecFile.ParkingLocationChoice";
    
    private static final String PROPERTIES_UEC_PARKING_LOCATION_ALTERNATIVES_FILE = "CBDParkingAlternatives.file";
    
    private static final String PROPERTIES_TRIP_DEPART_TIME_LOOKUP_FILE = "TripDepartTime.Proportions";
    
    public static final int UEC_DATA_PAGE = 0;
    private static final int MAND_FREE_PAGE = 1;
    private static final int MAND_PAID_PAGE = 2;
    private static final int NON_MAND_PAGE = 3;

    private static int PARK_TAZ_COLUMN = 2;
    
    // define names used in trip depart time lookup file
    private static final String TOUR_PRIMARY_PURPOSE_COLUMN_HEADING = "TourPurp";
    private static final String HALF_TOUR_DIRECTION_COLUMN_HEADING =  "IsInbound";
    private static final String TOUR_HOUR_COLUMN_HEADING =            "TourHour";
    private static final String TRIP_INDEX_COLUMN_HEADING =           "TripIndex";
    
    private StopDestinationSampleOfAlternativesModel dcSoaModel = null;
    private StopDestChoiceSize dcSizeModel = null;

    private int[] sampleValues;
    private boolean[] destinationAvailability;
    private int[] destinationSample;

    private TazDataIf tazDataManager;
    private ModelStructure modelStructure;
    
    private StopLocationDMU stopLocDmuObj;
    private TripModeChoiceDMU tripModeChoiceDmuObj;
    private ParkingChoiceDMU parkingChoiceDmuObj;

    private ChoiceModelApplication[] slChoiceModelApplication;
    private ChoiceModelApplication[] mcChoiceModelApplication;
    private ChoiceModelApplication mandatoryFreePc;
    private ChoiceModelApplication mandatoryPaidPc;
    private ChoiceModelApplication nonMandatoryPc;
    
    private TableDataSet cbdAltsTable;
    
    private int[] altToZone;
    private int[] altToSubZone;
    
    private float[] parkRate;
   
    private HashMap<String,double[]> tripDepartTimeOutboundMap;
    private HashMap<String,double[]> tripDepartTimeInboundMap;
    private String appender = "_";

    private long[] soaTime = new long[2];
    private long[] slsTime = new long[2];
    private long[] slcTime = new long[2];
    private long[] todTime = new long[2];
    private long[] mcTime  = new long[2];
    private long[] plcTime = new long[2];
    private long[][] hhTimes = new long[7][2];
    
    private TNCAndTaxiWaitTimeCalculator tncTaxiWaitTimeCalculator;
    
    /**
     * Constructor that will be used to set up the ChoiceModelApplications for each
     * type of tour
     * @param projectDirectory - name of root level project directory
     * @param resourceBundle - properties file with paths identified
     * @param dmuObject - decision making unit for stop frequency
     * @param tazDataManager - holds information about TAZs in the model.
     * @param modelStructure - holds the model structure info
     */
    public StopLocationModeChoiceModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ) {
        
        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;

        setupStopLocationChoiceModels( propertyMap, dmuFactory );
        setupTripDepartTimeModel(propertyMap, dmuFactory);
        setupTripModeChoiceModels( propertyMap, dmuFactory );
        setupParkingLocationModel( propertyMap, dmuFactory );
    
    }


    
    
    private void setupStopLocationChoiceModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {
        
        logger.info( String.format( "setting up stop location choice models." ) );
        
        altToZone = tazDataManager.getAltToZoneArray();
        altToSubZone = tazDataManager.getAltToSubZoneArray();
        parkRate = tazDataManager.getZonalParkRate();

        stopLocDmuObj = dmuFactory.getStopLocationDMU();

        
        // locate the UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        // locate the UEC
        String uecFileName = propertyMap.get( PROPERTIES_UEC_STOP_LOCATION );
        uecFileName = projectDirectory + uecFileName;


        // set up the stop location choice model array
        Collection<Integer> modelSheets = modelStructure.getStopLocModelSheetIndices();
        slChoiceModelApplication = new ChoiceModelApplication[modelSheets.size()+1];     // one choice model for each model sheet specified
        for ( int i : modelSheets ) {
            if ( slChoiceModelApplication[i] == null )
                slChoiceModelApplication[i] = new ChoiceModelApplication( uecFileName, i, UEC_DATA_PAGE, propertyMap, (VariableTable)stopLocDmuObj );
        }

        
        dcSizeModel = new StopDestChoiceSize(propertyMap,tazDataManager,modelStructure);
        dcSoaModel = new StopDestinationSampleOfAlternativesModel(propertyMap,tazDataManager,dcSizeModel,modelStructure,dmuFactory);
        // dcSoaModel = new StopDestinationSampleOfAlternativesModelGeneric(propertyMap,tazDataManager,dcSizeModel,modelStructure,dmuFactory);

        sampleValues = new int[dcSoaModel.getSampleOfAlternativesSampleSize()];
        
        int altCount = tazDataManager.getNumberOfZones()*tazDataManager.getNumberOfSubZones();
        destinationAvailability = new boolean[altCount+1];
        destinationSample = new int[altCount+1];
    }

    

    private void setupTripModeChoiceModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {
        
        logger.info( String.format( "setting up trip mode choice models." ) );
        
        // locate the UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        // locate the UEC
        String uecFileName = propertyMap.get( PROPERTIES_UEC_TRIP_MODE_CHOICE );
        uecFileName = projectDirectory + uecFileName;

        tripModeChoiceDmuObj = dmuFactory.getTripModeChoiceDMU();

        // keep a set of unique model sheet numbers so that we can create ChoiceModelApplication objects once for each model sheet used
        TreeSet<Integer> modelIndexSet = new TreeSet<Integer>();

        Collection<Integer> modelSheets = modelStructure.getTripModeChoiceModelSheetIndices();
        
        int maxUecIndex = 0;
        for ( int i : modelSheets ) {
            modelIndexSet.add( i );
            if ( i > maxUecIndex )
                maxUecIndex = i;
        }
        
        // set up the trip mode choice model array
        mcChoiceModelApplication = new ChoiceModelApplication[maxUecIndex+1];     // one choice model for each model sheet specified

        // for each unique model index, create the ChoiceModelApplication object and the availabilty array
        Iterator<Integer> it = modelIndexSet.iterator();
        int i = -1;
        while ( it.hasNext() ) {
            i = it.next();
            mcChoiceModelApplication[i] = new ChoiceModelApplication( uecFileName, i, UEC_DATA_PAGE, propertyMap, (VariableTable)tripModeChoiceDmuObj );
        }
        
        tncTaxiWaitTimeCalculator = new TNCAndTaxiWaitTimeCalculator();
        tncTaxiWaitTimeCalculator.createWaitTimeDistributions(propertyMap);

    }

    

    private void setupParkingLocationModel( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {
        
        logger.info ("setting up parking location choice models.");
        
        // locate the UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        // locate the UEC
        String uecFileName = propertyMap.get( PROPERTIES_UEC_PARKING_LOCATION_CHOICE );
        uecFileName = projectDirectory + uecFileName;

        parkingChoiceDmuObj = dmuFactory.getParkingChoiceDMU();

        mandatoryFreePc =  new ChoiceModelApplication( uecFileName, MAND_FREE_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)parkingChoiceDmuObj );
        mandatoryPaidPc =  new ChoiceModelApplication( uecFileName, MAND_PAID_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)parkingChoiceDmuObj );
        nonMandatoryPc =  new ChoiceModelApplication( uecFileName, NON_MAND_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)parkingChoiceDmuObj );


        

        // read the parking choice alternatives data file to get alternatives names
        String cbdFile = projectDirectory + (String)propertyMap.get( PROPERTIES_UEC_PARKING_LOCATION_ALTERNATIVES_FILE );

        try {
            CSVFileReader reader = new CSVFileReader();
            cbdAltsTable = reader.readFile(new File(cbdFile));
        }
        catch (IOException e) {
            logger.error ("problem reading table of cbd zones for parking location choice model.", e);
            System.exit(1);
        }

        int[] parkTazs = cbdAltsTable.getColumnAsInt( PARK_TAZ_COLUMN );
        parkingChoiceDmuObj.setParkTazArray ( parkTazs );
    }
    
    private void setupTripDepartTimeModel( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {
          	
    	logger.info( String.format( "setting up trip depart time choice model." ) );

        //get project directory
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        // read the trip depart time lookup table data and populate the maps used to assign results
        String tripDepartTimeLookupFileName = projectDirectory + propertyMap.get(PROPERTIES_TRIP_DEPART_TIME_LOOKUP_FILE);
        readTripDepartTimeLookupProportionsTable( tripDepartTimeLookupFileName );
        
        //create dmu
        tripModeChoiceDmuObj = dmuFactory.getTripModeChoiceDMU();

    }
    
    
    public void applyModel( Household household ) {

        soaTime[0] = 0;
        soaTime[1] = 0;
        slsTime[0] = 0;
        slsTime[1] = 0;
        slcTime[0] = 0;
        slcTime[1] = 0;
        todTime[0] = 0;
        todTime[1] = 0;
        mcTime[0] = 0;
        mcTime[1] = 0;
        plcTime[0] = 0;
        plcTime[1] = 0;
        hhTimes[6][0] = 0;
        hhTimes[6][1] = 0;

        // get this household's person array
        Person[] personArray = household.getPersons();

        // set the household id, origin taz, hh taz, and debugFlag=false in the dmus
        stopLocDmuObj.setHouseholdObject(household);
        tripModeChoiceDmuObj.setHouseholdObject(household);

        
        // loop through the person array (1-based)
        for(int j=1;j<personArray.length;++j){

            ArrayList<Tour> tours = new ArrayList<Tour>();

            Person person = personArray[j];

            // set the person
            stopLocDmuObj.setPersonObject(person);
            tripModeChoiceDmuObj.setPersonObject(person);

            
            
            // apply stop location and mode choice for all individual tours.
            tours.addAll( person.getListOfWorkTours() );
            tours.addAll( person.getListOfSchoolTours() );
            tours.addAll( person.getListOfIndividualNonMandatoryTours() );
            tours.addAll( person.getListOfAtWorkSubtours() );

            for ( Tour tour : tours ) {

                // set the tour object
                stopLocDmuObj.setTourObject(tour);
                tripModeChoiceDmuObj.setTourObject(tour);

                
                applyForOutboundStops( tour, person, household );
                
                applyForInboundStops( tour, person, household );

            } //tour loop

        } // j (person loop)

        
        
        // apply stop location and mode choice for all joint tours.
        Tour[] jointTours = household.getJointTourArray();
        if ( jointTours != null ) {
        
            for ( Tour tour : jointTours ) {

                // set the tour object
                stopLocDmuObj.setTourObject(tour);
                tripModeChoiceDmuObj.setTourObject(tour);

                // no person objects for joint tours
                applyForOutboundStops( tour, null, household );
                
                applyForInboundStops( tour, null, household );


            } //tour loop

        }

        
        household.setStlRandomCount( household.getHhRandomCount() );
        
    
    }

    
    private void applyForOutboundStops( Tour tour, Person person, Household household ) {
        
        Stop[] stops = tour.getOutboundStops();
        
        int origin = tour.getTourOrigTaz();
        int originWalkSegment = tour.getTourOrigWalkSubzone();
        int dest = tour.getTourDestTaz();
        int destWalkSegment = tour.getTourDestWalkSubzone();
        stopLocDmuObj.setInboundStop( false );
            
        tripModeChoiceDmuObj.setOrigType( HOME_TYPE_INDEX );
        tripModeChoiceDmuObj.setOrigParkRate( 0.0f );
        tripModeChoiceDmuObj.setDestType( PRIM_DEST_TYPE_INDEX );
        tripModeChoiceDmuObj.setPrimDestParkRate( parkRate[dest-1] );
        
        applyTripChoiceModels ( household, person, tour, stops, origin, originWalkSegment, dest, destWalkSegment );

    }
    
    
    private void applyForInboundStops( Tour tour, Person person, Household household ) {
        
        Stop[] stops = tour.getInboundStops();
        
        int origin = tour.getTourDestTaz();
        int originWalkSegment = tour.getTourDestWalkSubzone();
        int dest = tour.getTourOrigTaz();
        int destWalkSegment = tour.getTourOrigWalkSubzone();
        stopLocDmuObj.setInboundStop( true );
            
        tripModeChoiceDmuObj.setOrigType( PRIM_DEST_TYPE_INDEX );
        tripModeChoiceDmuObj.setOrigParkRate( parkRate[origin-1] );
        tripModeChoiceDmuObj.setDestType( HOME_TYPE_INDEX );
        tripModeChoiceDmuObj.setPrimDestParkRate( parkRate[origin-1] );
        
        applyTripChoiceModels ( household, person, tour, stops, origin, originWalkSegment, dest, destWalkSegment );

    }

    
    private void applyTripChoiceModels ( Household household, Person person, Tour tour, Stop[] stops, int origin, int originWalkSegment, int dest, int destWalkSegment ) {
        
        // if there are stops on this half-tour, determine their destinations, depart hours, trip modes, and parking tazs.
        if (stops != null) {

            long check2 = System.nanoTime();
            
            for ( int i=0; i < stops.length; i++ ) {
                
                Stop stop = stops[i];
                stop.setOrig(origin);
                stop.setOrigWalkSegment(originWalkSegment);
                
                stopLocDmuObj.setStopObject( stop );
                
                stopLocDmuObj.setStopNumber( i + 1 );
                stopLocDmuObj.setDmuIndexValues( household.getHhId(), household.getHhTaz(), origin, dest );

                tripModeChoiceDmuObj.setStopObject( stop );
                tripModeChoiceDmuObj.setStopObjectIsFirst( i == 0 ? 1 : 0 );
                tripModeChoiceDmuObj.setStopObjectIsLast( i == stops.length - 1 ? 1 : 0 );
                tripModeChoiceDmuObj.setIntStopParkRate( 0 );
                
                float popEmpDenOrig = (float) tazDataManager.getPopEmpPerSqMi(origin);
                float waitTimeSingleTNC=0;
                float waitTimeSharedTNC=0;
                float waitTimeTaxi=0;
                
                if(household!=null){
                    Random hhRandom = household.getHhRandom();
                    double rnum = hhRandom.nextDouble();
                    waitTimeSingleTNC = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenOrig);
                    waitTimeSharedTNC = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenOrig);
                    waitTimeTaxi = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenOrig);
                   }else{
                	waitTimeSingleTNC = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenOrig);
                	waitTimeSharedTNC = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenOrig);
                	waitTimeTaxi = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime( popEmpDenOrig);
                }

                tripModeChoiceDmuObj.setWaitTimeSingleTNC(waitTimeSingleTNC);
                tripModeChoiceDmuObj.setWaitTimeSharedTNC(waitTimeSharedTNC);
                tripModeChoiceDmuObj.setWaitTimeTaxi(waitTimeTaxi);
                  
                stop.setOrigTaxiWait(waitTimeTaxi);
                stop.setOrigSingleTNCWait(waitTimeSingleTNC);
                stop.setOrigSharedTNCWait(waitTimeSharedTNC);
                
                int zone = -1;
                int subzone = -1;
                int choice = -1;
                // if not the last stop object, make a destination choice
                if ( i < stops.length - 1 ) {

                    tripModeChoiceDmuObj.setDestType( INT_STOP_TYPE_INDEX );

                    try {
                        long check = System.nanoTime();
                        choice = selectDestination(stop);
                        slcTime[0] += ( System.nanoTime() - check );
                    }
                    catch ( Exception e ) {
                        logger.error ( String.format( "Exception caught processing %s stop location choice model for %s type tour %s stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), (i+1) ) );
                        throw new RuntimeException(e);
                    }

                    zone = altToZone[choice];
                    subzone = altToSubZone[choice];
                    tripModeChoiceDmuObj.setIntStopParkRate( parkRate[zone-1] );
                }
                else {
                    zone = dest;
                    subzone = destWalkSegment;
                    if ( stopLocDmuObj.getInboundStop() == 1 ) {
                        tripModeChoiceDmuObj.setDestType( HOME_TYPE_INDEX );
                    }
                    else {
                        tripModeChoiceDmuObj.setDestType( PRIM_DEST_TYPE_INDEX );
                    }
                }
                
                stop.setDest(zone);
                stop.setDestWalkSegment(subzone);
                tripModeChoiceDmuObj.setDmuIndexValues( household.getHhId(), origin, zone );
                tripModeChoiceDmuObj.setOrigCounty(tazDataManager.getZoneCounty(origin));

                long check = System.nanoTime();
                //select trip depart hour
            	int choosenHour = -1;
                try {
                	choosenHour = selectTripDepartTime (household, tour, stop);
                } catch ( Exception e ) {
                        logger.error ( String.format( "Exception caught processing %s trip depart time %s type tour %s intermediate stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), (i+1) ) );
                        e.printStackTrace();
                        System.exit(-1);
//                            throw new RuntimeException(e);
                }
                stop.setDepartHour(choosenHour);
                todTime[0] += ( System.nanoTime() - check );

                
                //select mode
                check = System.nanoTime();
                choice = -1;
                try {
                    choice = selectMode( household, tour, stop );
                }
                catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught processing %s trip mode choice model for %s type tour %s intermediate stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), (i+1) ) );
                    e.printStackTrace();
                    System.exit(-1);
//                    throw new RuntimeException(e);
                }
                stop.setMode( choice );
                mcTime[0] += ( System.nanoTime() - check );

                
                
                // set the next segment's origin temporarily - it might change if a parking zone is selected
                int tempOrigin = zone;
                
                float parkTot = tazDataManager.getZoneTableValue( zone, tazDataManager.getZonalParkTotFieldName() );
                
                check = System.nanoTime();
                // if the stop location is in the CBD and the mode is drive (SOV or HOV), determine the parking location zone.
                if ( modelStructure.getTripModeIsSovOrHov( choice ) && parkTot > 0 && tazDataManager.getZoneIsCbd( zone ) == 1 ) {
                    parkingChoiceDmuObj.setDmuState( household, origin, zone );
                    choice = -1;
                    try {
                        choice = selectParkingLocation ( household, tour, stop );
                    }
                    catch ( Exception e ) {
                        logger.error ( String.format( "Exception caught processing %s stop parking location choice model for %s type tour %s intermediate stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), (i+1) ) );
                        throw new RuntimeException(e);
                    }
                    stop.setParkTaz( choice );
                    tempOrigin = choice;
                }
                plcTime[0] += ( System.nanoTime() - check );
                
                origin = tempOrigin;
                originWalkSegment = subzone;

                tripModeChoiceDmuObj.setOrigType( INT_STOP_TYPE_INDEX );
                tripModeChoiceDmuObj.setOrigParkRate( parkRate[origin-1] );

            }

            hhTimes[6][0] += ( System.nanoTime() - check2 );
            
        }
        // if no stops on the half-tour, determine trip mode choice, then parking location choice at the primary destination.
        else {

            long check2 = System.nanoTime();

            long check = System.nanoTime();
            // create a Stop object for use in applying trip mode choice for this half tour without stops
            String origStopPurpose = "";
            String destStopPurpose = "";
            if ( stopLocDmuObj.getInboundStop() == 0 ) {
                origStopPurpose = tour.getTourCategoryIsAtWork() ? "Work" : "Home";
                destStopPurpose = tour.getTourPrimaryPurpose();
            }
            else {
                origStopPurpose = tour.getTourPrimaryPurpose();
                destStopPurpose = tour.getTourCategoryIsAtWork() ? "Work" : "Home";
            }

            Stop stop = null;
            try {
                stop = tour.createStop( modelStructure, origStopPurpose, destStopPurpose, stopLocDmuObj.getInboundStop() == 1, tour.getTourCategoryIsAtWork() );            
            }
            catch ( Exception e ){
                logger.info( "exception creating stop." );
            }
            
            stop.setOrig(origin);
            stop.setOrigWalkSegment(originWalkSegment);
            
            stopLocDmuObj.setStopObject( stop );
            tripModeChoiceDmuObj.setStopObjectIsFirst( 1);
            tripModeChoiceDmuObj.setStopObjectIsLast( 1);
            tripModeChoiceDmuObj.setIntStopParkRate( 0 );
                       
            stopLocDmuObj.setStopNumber( 1 );
            stopLocDmuObj.setDmuIndexValues( household.getHhId(), household.getHhTaz(), origin, dest );
            tripModeChoiceDmuObj.setOrigCounty(tazDataManager.getZoneCounty(origin));

            int zone = dest;
            int subzone = destWalkSegment;
            if ( stopLocDmuObj.getInboundStop() == 1 ) {
                tripModeChoiceDmuObj.setDestType( HOME_TYPE_INDEX );
            }
            else {
                tripModeChoiceDmuObj.setDestType( PRIM_DEST_TYPE_INDEX );
            }

            stop.setDest(zone);
            stop.setDestWalkSegment(subzone);

            slcTime[1] += ( System.nanoTime() - check );
            check = System.nanoTime();
            
            
            tripModeChoiceDmuObj.setStopObject( stop );
            tripModeChoiceDmuObj.setDmuIndexValues( household.getHhId(), origin, zone );
            float popEmpDenOrig = (float) tazDataManager.getPopEmpPerSqMi(origin);
            float waitTimeSingleTNC=0;
            float waitTimeSharedTNC=0;
            float waitTimeTaxi=0;
            
            if(household!=null){
                Random hhRandom = household.getHhRandom();
                double rnum = hhRandom.nextDouble();
                waitTimeSingleTNC = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenOrig);
                waitTimeSharedTNC = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenOrig);
                waitTimeTaxi = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenOrig);
               }else{
            	waitTimeSingleTNC = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenOrig);
            	waitTimeSharedTNC = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenOrig);
            	waitTimeTaxi = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime( popEmpDenOrig);
            }

            tripModeChoiceDmuObj.setWaitTimeSingleTNC(waitTimeSingleTNC);
            tripModeChoiceDmuObj.setWaitTimeSharedTNC(waitTimeSharedTNC);
            tripModeChoiceDmuObj.setWaitTimeTaxi(waitTimeTaxi);
                         
            stop.setOrigTaxiWait(waitTimeTaxi);
            stop.setOrigSingleTNCWait(waitTimeSingleTNC);
            stop.setOrigSharedTNCWait(waitTimeSharedTNC);

            
            //select trip depart hour
            int choosenHour = -1;
            try {
            	choosenHour = selectTripDepartTime (household, tour, stop);
            } catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught processing %s trip depart time %s type tour %s intermediate stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), 1 ) );
                    e.printStackTrace();
                    System.exit(-1);
//                    throw new RuntimeException(e);
            }
            stop.setDepartHour(choosenHour);
            todTime[1] += ( System.nanoTime() - check );
            check = System.nanoTime();
            
            //select mode
            int choice = -1;
            try {
                choice = selectMode( household, tour, stop );
            }
            catch ( Exception e ) {
                logger.error ( String.format( "Exception caught processing %s trip mode choice model for %s type half-tour %s stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), 1 ) );
                e.printStackTrace();
                System.exit(-1);
//                throw new RuntimeException(e);
            }
            stop.setMode( choice );
            mcTime[1] += ( System.nanoTime() - check );
            check = System.nanoTime();
            
            
            float parkTot = tazDataManager.getZoneTableValue( zone, tazDataManager.getZonalParkTotFieldName() );
            
            // if the stop location is in the CBD and the mode is drive (SOV or HOV), determine the parking location zone.
            if ( modelStructure.getTripModeIsSovOrHov( choice ) && parkTot > 0 && tazDataManager.getZoneIsCbd( zone ) == 1 ) {
                parkingChoiceDmuObj.setDmuState( household, origin, zone );
                choice = -1;
                try {
                    choice = selectParkingLocation ( household, tour, stop );
                }
                catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught processing %s stop parking location choice model for %s type half-tour %s stop:  HHID=%d, personNum=%s, stop=%d.", ( stopLocDmuObj.getInboundStop() == 1 ? "inbound" : "outbound"), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourPurpose(), household.getHhId(), ( person == null ? "N/A" : Integer.toString(person.getPersonNum()) ), 1 ) );
                    throw new RuntimeException(e);
                }
                stop.setParkTaz( choice );
            }
            plcTime[1] += ( System.nanoTime() - check );
             
            hhTimes[6][1] += ( System.nanoTime() - check2 );
                
        }            
            
    }

    
    private int selectDestination(Stop s) {

        Logger modelLogger = slcLogger;
        
        Household household = s.getTour().getPersonObject().getHouseholdObject();
        Tour tour = s.getTour();
        Person person = tour.getPersonObject();
        
        if ( household.getDebugChoiceModels() ) {
            if ( s == null ) {
                household.logHouseholdObject( "Pre Stop Location Choice for tour primary destination: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId(), modelLogger );
                household.logPersonObject( "Pre Stop Location Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Stop Location Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
            }
            else {
                household.logHouseholdObject( "Pre Stop Location Choice for trip: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId() + ", Tour Purpose_" + tour.getTourPurpose() + ", Stop_" + s.getStopId(), modelLogger );
                household.logPersonObject( "Pre Stop Location Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Stop Location Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
                household.logStopObject("Pre Stop Location Choice for stop " + s.getStopId(), modelLogger, s, modelStructure );
            }
        }
        

        long check = System.nanoTime();
        StopDestinationSampleOfAlternativesModel.StopSoaResult result =  dcSoaModel.computeDestinationSampleOfAlternatives(s);
        soaTime[0] += ( System.nanoTime() - check );

        check = System.nanoTime();
        int numAltsInSample = result.getNumUniqueAltsInSample();
        int[] sample = result.getSample();
        float[] corrections = result.getCorrections();
        double[] stopLocSize = result.getStopLocationSize();	//is 1-based
        
		// write out size terms 
        if ( household.getDebugChoiceModels () ) {
            logger.info("****************************************************************************************************************");
        	logger.info(String.format( "Log of size terms in StopLocationModeChoiceModel "));
            logger.info(String.format("%-6s  %-16s", "alt", "size term"));

        	for(int i=1; i<stopLocSize.length; i++) 
        		logger.info(String.format("%-6d  %16.8e", i, stopLocSize[i]));
        }       

        //The model (through UERC page) is selected based on tour purpose because the LOS (logsum) measures are based on tour  
        // even though the size terms were determined based on stop purpose
        int modelIndex = modelStructure.getStopLocationModelIndex( s.getTour().getTourPrimaryPurpose() );
        ChoiceModelApplication choiceModel = slChoiceModelApplication[modelIndex];

        
        String choiceModelDescription = "";
        String decisionMakerLabel = "";
        String loggingHeader = "";
        String separator = "";
        String logsumLoggingHeader = "";
        
        if ( household.getDebugChoiceModels() ) {

            choiceModelDescription = "Stop Location Choice";
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourPurpose=%s, TourId=%d, StopDestPurpose=%s, StopId=%d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourPurpose(), tour.getTourId(), s.getDestPurpose(modelStructure), s.getStopId() );
            loggingHeader = String.format( "%s for %s", choiceModelDescription, decisionMakerLabel );
        
            modelLogger.info(" ");
            for (int k=0; k < loggingHeader.length(); k++)
                separator += "+";
            modelLogger.info( loggingHeader );
            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
        
        }


        stopLocDmuObj.setLogSizeTerms(stopLocSize);
        
        Arrays.fill(destinationAvailability,false);
        Arrays.fill(destinationSample,0);
        for (int i=1; i <= numAltsInSample; i++) {
            int alternative = sample[i];
            destinationAvailability[alternative] = true;
            destinationSample[alternative] = 1;

            stopLocDmuObj.setDcSoaCorrections(altToZone[alternative],altToSubZone[alternative],corrections[i]);
            
            // calculate the logsum for the stop origin to the stop destination alternative
            // stop origin has already been set; stop destionation is the stop alternative being considered for the ik logsum
            s.setDest( altToZone[alternative] );
            s.setDestWalkSegment( altToSubZone[alternative] );

            if ( household.getDebugChoiceModels() ) {
                logsumLoggingHeader = "ik mode choice logsum for slc soa sample=" + i + ", alt=" + alternative + ", taz=" + altToZone[alternative] + ", subzone=" + altToSubZone[alternative];
            }
        
            
            check = System.nanoTime();
            double ikLogsum = calculateTripModeChoiceLogsum( household, person, tour, s, modelLogger, logsumLoggingHeader );
            stopLocDmuObj.setTripMcLogsumIk( altToZone[alternative], altToSubZone[alternative], ikLogsum );
            slsTime[0] += ( System.nanoTime() - check );
            

            
            // calculate the logsum for the stop destination alternative to the tour primary destination
            // stop destination is the tour origin or the tour primary destination, depending on whether this half-tour is inbound or outbound
            s.setDest( s.isInboundStop() ? tour.getTourOrigTaz() : tour.getTourDestTaz() );
            s.setDestWalkSegment( s.isInboundStop() ? tour.getTourOrigWalkSubzone() : tour.getTourDestWalkSubzone() );
            // stop dest attributes will be reset after stop location is made; but stop origin attributes need to be reset after logsum calculation
            int tempOrig = s.getOrig();
            int tempOrigWalkSegment = s.getOrigWalkSegment();
            // stop origin should be the stop alternative being considered for the jk logsum.
            s.setOrig( altToZone[alternative] );
            s.setOrigWalkSegment( altToSubZone[alternative] );
            
            if ( household.getDebugChoiceModels() ) {
                logsumLoggingHeader = "kj mode choice logsum for slc soa sample=" + i + ", alt=" + alternative + ", taz=" + altToZone[alternative] + ", subzone=" + altToSubZone[alternative];
            }

            
            check = System.nanoTime();
            double kjLogsum = calculateTripModeChoiceLogsum( household, person, tour, s, modelLogger, logsumLoggingHeader );
            s.setOrig( tempOrig );
            s.setOrigWalkSegment( tempOrigWalkSegment );
            stopLocDmuObj.setTripMcLogsumKj( altToZone[alternative], altToSubZone[alternative], kjLogsum );
            slsTime[0] += ( System.nanoTime() - check );

        }

        choiceModel.computeUtilities(stopLocDmuObj,stopLocDmuObj.getDmuIndexValues(),destinationAvailability,destinationSample);

        // write choice model alternative info to log file
        if ( household.getDebugChoiceModels() ) {
            
            double[] utilities     = choiceModel.getUtilities();
            double[] probabilities = choiceModel.getProbabilities();
            boolean[] availabilities = choiceModel.getAvailabilities();
           
            String personTypeString = person.getPersonType();
            int personNum = person.getPersonNum();

            modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
            modelLogger.info("Alternative             Availability           Utility       Probability           CumProb");
            modelLogger.info("---------------------   ------------       -----------    --------------    --------------");

            int numberOfSubzones = tazDataManager.getNumberOfSubZones();
            
            // copy the values of the sample to an array that can be sorted for logging purposes
            for (int i=1; i <= numAltsInSample; i++)
                sampleValues[i-1] = sample[i];
            for (int i=numAltsInSample; i < sampleValues.length; i++)
                sampleValues[i] = Integer.MAX_VALUE;
            int[] sortedSampleValueIndices = IndexSort.indexSort( sampleValues );
            
            double cumProb = 0.0;
            for(int j=1; j <= numAltsInSample; j++){

                int k =  sortedSampleValueIndices[j-1];
                int alt = sample[k+1];

                int d = ( alt-1) / numberOfSubzones + 1;
                int w = alt - (d-1)*numberOfSubzones - 1;
                cumProb += probabilities[alt-1];
                String altString = String.format( "%-3d %5d %5d %5d", j, alt, d, w );
                modelLogger.info(String.format("%-21s%15s%18.6e%18.6e%18.6e", altString, availabilities[alt], utilities[alt-1], probabilities[alt-1], cumProb));
            }
            
//            choiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            // write UEC calculation results to separate model specific log file
            choiceModel.logUECResults( modelLogger, loggingHeader );

        }

        Random hhRandom = household.getHhRandom();
        int randomCount = household.getHhRandomCount();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        if ( choiceModel.getAvailabilityCount() > 0 )
            chosen = choiceModel.getChoiceResult( rn );
        else {
            logger.error (String.format( "Error for HHID=%d, PersonNum=%d, no available %s stop destination choice alternatives to choose from in choiceModelApplication.", stopLocDmuObj.getHouseholdObject().getHhId(), stopLocDmuObj.getPersonObject().getPersonNum(), tour.getTourPurpose()));
            throw new RuntimeException();
        }
                    
        
        // write choice model alternative info to log file
        if ( household.getDebugChoiceModels() || chosen < 0 ) {
            
            double[] utilities     = choiceModel.getUtilities();
            double[] probabilities = choiceModel.getProbabilities();
            boolean[] availabilities = choiceModel.getAvailabilities();
           
            // copy the values of the sample to an array that can be sorted for logging purposes
            for (int i=1; i <= numAltsInSample; i++)
                sampleValues[i-1] = sample[i];
            for (int i=numAltsInSample; i < sampleValues.length; i++)
                sampleValues[i] = Integer.MAX_VALUE;
            int[] sortedSampleValueIndices = IndexSort.indexSort( sampleValues );
            
            int selectedIndex = -1;
            for(int j=1; j <= numAltsInSample; j++){

                int k =  sortedSampleValueIndices[j-1];
                int alt = sample[k+1];

                if ( alt == chosen )
                    selectedIndex = j;
            }

            modelLogger.info(" ");
            int numberOfSubzones = tazDataManager.getNumberOfSubZones();
            int d = (chosen-1)/numberOfSubzones + 1;
            int w = chosen - (d-1)*numberOfSubzones - 1;
            String altString = String.format( "%-3d %5d %5d %5d", selectedIndex, chosen, d, w );
            modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
                    
            choiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            choiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );
            
            // write UEC calculation results to separate model specific log file
            choiceModel.logUECResults( modelLogger, loggingHeader );
        }

        return chosen;
    }

    
    private int selectMode ( Household household, Tour tour, Stop stop ) {

        Logger modelLogger = tripMcLogger;
        
        
        if ( household.getDebugChoiceModels() ) {
            if ( stop == null ) {
                household.logHouseholdObject( "Pre Trip Mode Choice: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId(), tripMcLogger );
                household.logPersonObject( "Pre Trip Mode Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Trip Mode Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
            }
            else {
                household.logHouseholdObject( "Pre Trip Mode Choice: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId() + ", Tour Purpose_" + tour.getTourPurpose() + ", Stop_" + stop.getStopId(), tripMcLogger );
                household.logPersonObject( "Pre Trip Mode Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Trip Mode Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
                household.logStopObject("Pre Trip Mode Choice for stop " + stop.getStopId(), modelLogger, stop, modelStructure );
            }
        }
        

        
        int modelIndex = modelStructure.getTripModeChoiceModelIndex( tour.getTourPrimaryPurpose().toLowerCase() );
        ChoiceModelApplication choiceModel = mcChoiceModelApplication[modelIndex];

        
        Person person = tour.getPersonObject();
        
        String choiceModelDescription = "";
        String separator = "";
        String loggerString = "";
        String decisionMakerLabel = "";

        if ( household.getDebugChoiceModels() ) {
            
            choiceModelDescription = "Trip Mode Choice Model";
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourPurpose=%s, TourId=%d, StopDestPurpose=%s, StopId=%d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourPurpose(), tour.getTourId(), stop.getDestPurpose(modelStructure), stop.getStopId() );


            modelLogger.info(" ");
            loggerString = choiceModelDescription + " for " + decisionMakerLabel + ".";
            for (int k=0; k < loggerString.length(); k++)
                separator += "+";
            modelLogger.info( loggerString );
            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
         
            choiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        
        }

        
        
        choiceModel.computeUtilities( tripModeChoiceDmuObj, tripModeChoiceDmuObj.getDmuIndexValues() );

        Random hhRandom = household.getHhRandom();
        int randomCount = household.getHhRandomCount();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        if ( choiceModel.getAvailabilityCount() > 0 )
            chosen = choiceModel.getChoiceResult( rn );

        
        
        // write choice model alternative info to log file
        if ( household.getDebugChoiceModels() || chosen < 0 ) {
            
            double[] utilities     = choiceModel.getUtilities();
            double[] probabilities = choiceModel.getProbabilities();

            String[] altNames = choiceModel.getAlternativeNames();
            
            String personTypeString = person.getPersonType();
            int personNum = person.getPersonNum();

            modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
            modelLogger.info("Alternative               Utility       Probability           CumProb");
            modelLogger.info("---------------    --------------    --------------    --------------");

            double cumProb = 0.0;

            for(int k=0; k < altNames.length; k++){
                cumProb += probabilities[k];
                String altString = String.format( "%-3d  %25s", k+1, altNames[k] );
                modelLogger.info(String.format("%-30s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
            }

            
            modelLogger.info(" ");
            if ( chosen < 0 ) {
                String altString = "No alternatives available to choose from";
                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );
                
                if ( stop == null ) {
                    household.logHouseholdObject( "Pre Trip Mode Choice: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId(), tripMcLogger );
                    household.logPersonObject( "Pre Trip Mode Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                    household.logTourObject("Pre Trip Mode Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
                }
                else {
                    household.logHouseholdObject( "Pre Trip Mode Choice: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId() + ", Tour Purpose_" + tour.getTourPurpose() + ", Stop_" + stop.getStopId(), tripMcLogger );
                    household.logPersonObject( "Pre Trip Mode Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                    household.logTourObject("Pre Trip Mode Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
                    household.logStopObject("Pre Trip Mode Choice for stop " + stop.getStopId(), modelLogger, stop, modelStructure );
                }
                
            }
            else {
                String altString = String.format( "%-3d  %s", chosen, altNames[chosen-1] );
                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );
            }

            
            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
        
            
            choiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            choiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

            
            // write UEC calculation results to separate model specific log file
            choiceModel.logUECResults( modelLogger, loggerString );

        }

        
        
        if ( chosen > 0 )
            return chosen;
        else {
            logger.error ( String.format( "HHID=%d, no available %s trip mode alternatives in tourId=%d to choose from in choiceModelApplication.", household.getHhId(), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourId() ) );
            throw new RuntimeException();
        }

    }
    
    
    
    // determine the trip mode choice logsum for the intermediate stop alternative either as an origin or a destination
    private double calculateTripModeChoiceLogsum( Household household, Person person, Tour tour, Stop stop, Logger modelLogger, String loggerHeader ){
        
        //determine the trip mode choice logsum for the sampled dest alt and store in stop location dmu
        tripModeChoiceDmuObj.setDmuIndexValues( household.getHhId(), stop.getOrig(), stop.getDest() );
        tripModeChoiceDmuObj.setOrigCounty(tazDataManager.getZoneCounty(stop.getOrig()));

        tripModeChoiceDmuObj.setIntStopParkRate( parkRate[stop.getDest()-1] );
        
        int mcModelIndex = modelStructure.getTripModeChoiceModelIndex( tour.getTourPrimaryPurpose().toLowerCase() );
        mcChoiceModelApplication[mcModelIndex].computeUtilities( tripModeChoiceDmuObj, tripModeChoiceDmuObj.getDmuIndexValues() );
        double logsum = mcChoiceModelApplication[mcModelIndex].getLogsum();

        if ( household.getDebugChoiceModels() ) {
            household.logStopObject(loggerHeader, modelLogger, stop, modelStructure );
            mcChoiceModelApplication[mcModelIndex].logUECResults( modelLogger, loggerHeader );
            modelLogger.info( "" );
            modelLogger.info( "calculated mc logsum: " + logsum );
        }
        
        return logsum;
        
    }
 
    
    // this method is called to determine parking location if stop location is in the CBD and chosen mode is sov or hov.
    private int selectParkingLocation ( Household household, Tour tour, Stop stop ) {

        Logger modelLogger = parkLocLogger;
                
        if ( household.getDebugChoiceModels() ) {
            if ( stop == null ) {
                household.logHouseholdObject( "Pre Parking Location Choice for tour primary destination: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId(), modelLogger );
                household.logPersonObject( "Pre Parking Location Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Parking Location Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
            }
            else {
                household.logHouseholdObject( "Pre Parking Location Choice for trip: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId() + ", Tour Purpose_" + tour.getTourPurpose() + ", Stop_" + stop.getStopId(), modelLogger );
                household.logPersonObject( "Pre Parking Location Choice for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
                household.logTourObject("Pre Parking Location Choice for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
                household.logStopObject("Pre Parking Location Choice for stop " + stop.getStopId(), modelLogger, stop, modelStructure );
            }
        }
                
        ChoiceModelApplication choiceModel;
        if ( tour.getTourCategoryIsMandatory() ) {
            Person person = tour.getPersonObject(); 
            switch ( person.getFreeParkingAvailableResult() ) {
                case 1:
                    choiceModel = mandatoryFreePc;
                    break;
                case 2:
                    choiceModel = mandatoryPaidPc;
                    break;
                    
                default:
                    logger.error( String.format("Free parking availability choice for hh=%d was %d, but should have been 1 or 2.", household.getHhId(), person.getFreeParkingAvailableResult()) );
                    throw new RuntimeException();
            }
        }
        else {
            choiceModel = nonMandatoryPc;
        }
        
        parkingChoiceDmuObj.setTourObject(tour);
        
        Person person = tour.getPersonObject();
        
        String choiceModelDescription = "";
        String separator = "";
        String loggerString = "";
        String decisionMakerLabel = "";

        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( household.getDebugChoiceModels() ) {
            
            if ( stop == null ) {
                choiceModelDescription = "Parking Location Choice Model for tour primary destination";
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourPurpose=%s, TourId=%d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourPurpose(), tour.getTourId() );
            }
            else {
                choiceModelDescription = "Parking Location Choice Model for trip";
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourPurpose=%s, TourId=%d, StopDestPurpose=%s, StopId=%d", household.getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourPurpose(), tour.getTourId(), stop.getDestPurpose(modelStructure), stop.getStopId() );
            }

            modelLogger.info(" ");
            loggerString = choiceModelDescription + " for " + decisionMakerLabel + ".";
            for (int k=0; k < loggerString.length(); k++)
                separator += "+";
            modelLogger.info( loggerString );
            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
         
            choiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        
        }

        
        
        choiceModel.computeUtilities ( parkingChoiceDmuObj, parkingChoiceDmuObj.getDmuIndexValues() );

        Random hhRandom = household.getHhRandom();
        int randomCount = household.getHhRandomCount();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        int parkTaz = 0;
        if ( choiceModel.getAvailabilityCount() > 0 ) {
            chosen = choiceModel.getChoiceResult( rn );
            
            // get the zone number associated with the chosen alternative
            parkTaz = (int)cbdAltsTable.getValueAt( chosen, PARK_TAZ_COLUMN );
        }


        
        // write choice model alternative info to log file
        if ( household.getDebugChoiceModels() || chosen < 0 ) {
            
            double[] utilities     = choiceModel.getUtilities();
            double[] probabilities = choiceModel.getProbabilities();

            int[] altTazs = cbdAltsTable.getColumnAsInt( PARK_TAZ_COLUMN );
            
            String personTypeString = person.getPersonType();
            int personNum = person.getPersonNum();

            modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
            modelLogger.info("Alternative               Utility       Probability           CumProb");
            modelLogger.info("---------------    --------------    --------------    --------------");

            double cumProb = 0.0;

            for(int k=0; k < altTazs.length; k++){
                int alt = altTazs[k];
                cumProb += probabilities[k];
                String altString = String.format( "%-3d  %5d", k+1, alt );
                modelLogger.info(String.format("%-15s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
            }

            modelLogger.info(" ");
            if ( chosen < 0 ) {
                modelLogger.info( String.format("No Alternatives Available For Choice !!!" ) );
            }
            else {
                String altString = String.format( "%-3d  %5d", chosen, altTazs[chosen-1] );
                modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );
            }

            modelLogger.info( separator );
            modelLogger.info( "" );
            modelLogger.info( "" );
        
            
            choiceModel.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            choiceModel.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

            
            // write UEC calculation results to separate model specific log file
            choiceModel.logUECResults( modelLogger, loggerString );

        }

        
        if ( chosen > 0 )
            return parkTaz;
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available %s parking location alternatives in tourId=%d to choose from in choiceModelApplication.", household.getHhId(), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourId() ) );
            throw new RuntimeException();
        }

    }
    
    

    public void cleanUp() {
        dcSoaModel.cleanUp();
    }
    
    private void readTripDepartTimeLookupProportionsTable( String tripDepartTimeLookupFileName ) {

        // read the trip depart time proportions into a TableDataSet
        TableDataSet departTimeLookupTable = null;
        try{
            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            departTimeLookupTable =  reader.readFile(new File( tripDepartTimeLookupFileName ));
        }
        catch(Exception e){
            logger.error( String.format( "Exception occurred reading trip depart time lookup proportions file: %s.", tripDepartTimeLookupFileName ),e);
            throw new RuntimeException();
        }
        
        
        // create a mapping between names used in lookup file and purpose names used in model
        // at work tour use tour hours
        HashMap<String,String> primaryPurposeMap = new HashMap<String,String>();
        primaryPurposeMap.put( "" + ModelStructure.WORK_PURPOSE_INDEX, ModelStructure.WORK_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.UNIVERSITY_PURPOSE_INDEX, ModelStructure.UNIVERSITY_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.SCHOOL_PURPOSE_INDEX, ModelStructure.SCHOOL_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.ESCORT_PURPOSE_INDEX, ModelStructure.ESCORT_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.SHOPPING_PURPOSE_INDEX, ModelStructure.SHOPPING_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.EAT_OUT_PURPOSE_INDEX, ModelStructure.EAT_OUT_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.OTH_MAINT_PURPOSE_INDEX, ModelStructure.OTH_MAINT_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.SOCIAL_PURPOSE_INDEX, ModelStructure.SOCIAL_PURPOSE_NAME );
        primaryPurposeMap.put( "" + ModelStructure.OTH_DISCR_PURPOSE_INDEX, ModelStructure.OTH_DISCR_PURPOSE_NAME );
        
        // fields in lookup file are:
        // TourPurp, IsInbound, TourHour, TripIndex, HR5, HR6,..., HR23
        
        // create hash table with four keys appended together with "_"
        // The tour purpose code is replaced with the model tour purpose name/label 
        tripDepartTimeInboundMap = new HashMap<String,double[]>();
        tripDepartTimeOutboundMap = new HashMap<String,double[]>();

        // loop over rows in the TableDataSet
        int numDepartHours = CtrampApplication.LAST_HOUR - CtrampApplication.START_HOUR + 1;
        for ( int i=0; i < departTimeLookupTable.getRowCount(); i++ ) {

            // get the tour primary purpose
            String tourPrimPurp = departTimeLookupTable.getStringValueAt( i+1, TOUR_PRIMARY_PURPOSE_COLUMN_HEADING );
            
            // get the half tour direction
            String direction = departTimeLookupTable.getStringValueAt( i+1, HALF_TOUR_DIRECTION_COLUMN_HEADING );
            
            // get the tour hour (depart hour for outbound and return hour for inbound)
            int tourHour = (int)departTimeLookupTable.getValueAt( i+1, TOUR_HOUR_COLUMN_HEADING );
            
            // get the trip index (the index of the trip on the tour (with 1 equal to the 1st trip on the tour)
            int tripIndex = (int)departTimeLookupTable.getValueAt( i+1, TRIP_INDEX_COLUMN_HEADING );
            
            // read the proportions for all hours and create the array of proportions for this table record.
            // reverse the inbound array so the cumulative monte carlo selection works
            int startHoursColumn = departTimeLookupTable.getColumnCount() - numDepartHours + 1;
            String key = primaryPurposeMap.get(tourPrimPurp) + appender + direction + appender + tourHour + appender + tripIndex;
            double[] props = new double[numDepartHours];
            
            for ( int j=0; j < numDepartHours; j++ ) {
            		if(direction.equals("1")) {
           				props[(numDepartHours-1)-j] = departTimeLookupTable.getValueAt( i+1, startHoursColumn + j);
            		} else {
            			props[j] = departTimeLookupTable.getValueAt( i+1, startHoursColumn + j);
            		}
            }
            
    		if(direction.equals("1")) {
   				tripDepartTimeInboundMap.put(key, props);
    		} else {
    			tripDepartTimeOutboundMap.put(key, props);
    		}
            
        }
        
    }

  
    private int selectTripDepartTime ( Household household, Tour tour, Stop stop) {
        
    	//log context
        Logger modelLogger = tripDepartLogger;
        if ( household.getDebugChoiceModels() ) {
            household.logHouseholdObject( "Trip Depart Time Model for trip: HH_" + household.getHhId() + ", Pers_" + tour.getPersonObject().getPersonNum() + ", Tour Purpose_" + tour.getTourPurpose() + ", Tour_" + tour.getTourId() + ", Tour Purpose_" + tour.getTourPurpose() + ", Stop_" + stop.getStopId(), modelLogger );
            household.logPersonObject( "Trip Depart Time Model for person " + tour.getPersonObject().getPersonNum(), modelLogger, tour.getPersonObject() );
            household.logTourObject("Trip Depart Time Model for tour " + tour.getTourId(), modelLogger, tour.getPersonObject(), tour );
            household.logStopObject("Trip Depart Time Model for stop " + stop.getStopId(), modelLogger, stop, modelStructure );
        }
        
        //exit if at work tour and use default 
        if(tour.getTourCategoryIsAtWork()) {
        	if ( household.getDebugChoiceModels() ) {
        		modelLogger.info("Trip Depart Time Model Not Run for At-Work Trips; Tour Start and End Hour Used Instead");
        	}
        	return stop.getDepartHour();
        } 
        
        //exit if tour start and end hour equal
        if(tour.getTourEndHour() == tour.getTourStartHour()) {
        	if ( household.getDebugChoiceModels() ) {
        		modelLogger.info("Trip Depart Time Model Not Run Since Tour Start and End Hour Equal; Tour Start and End Hour Used Instead");
        	}
        	return stop.getDepartHour();
        }
        
        //exit if first trip or last trip on half tour and use tour hour
        if(stop.isInboundStop()) {
        	if(stop.getStopId() == tour.getNumInboundStops()) {
        		if ( household.getDebugChoiceModels() ) {
        			modelLogger.info("Trip Depart Time Model Not Run Since First or Last Trip on Tour; Tour Start and End Hour Used Instead");
        		}
        		return stop.getDepartHour();
        	}
    	} else {
    		if(stop.getStopId() == 0) {
    			if ( household.getDebugChoiceModels() ) {
    				modelLogger.info("Trip Depart Time Model Not Run Since First or Last Trip on Tour; Tour Start and End Hour Used Instead");
    			}
    			return stop.getDepartHour();
    		}
    	}
    		
    	//exit if no stops on tour
    	if(stop.getStopId() == -1) {
    		if ( household.getDebugChoiceModels() ) {
    			modelLogger.info("Trip Depart Time Model Not Run Since No Stops on Tour; Tour Start and End Hour Used Instead");
    		}
        	return stop.getDepartHour();
    	}
    	        
        //get context information to create lookup key
        String tourPurpose = tour.getTourPrimaryPurpose();
        int halfTourDirection = stop.isInboundStop() ? 1 : 0;
        int tourHour = stop.isInboundStop() ? tour.getTourEndHour() : tour.getTourStartHour() ;
        int tripIndex = -1;
        
        //determine tripIndex on half tour
        //stop ids start at zero (except no stop tours which have stops with id=-1)
        //stops store trip depart time to stop (not from stop)
        if(stop.isInboundStop()) {
    		tripIndex = tour.getNumInboundStops() - stop.getStopId() + 1; 
    	} else {
    		tripIndex = stop.getStopId() + 1;
    	}
        String key = tourPurpose + appender + halfTourDirection + appender + tourHour + appender + tripIndex;
        
        //get choices 
        double[] probs;
        if(stop.isInboundStop()) {
        	probs = tripDepartTimeInboundMap.get(key);	
        } else {
        	probs = tripDepartTimeOutboundMap.get(key);
        }
        
        //log choices
        if ( household.getDebugChoiceModels() ) {
            modelLogger.info(String.format("Trip Depart Time Model Lookup Key (tourPurpose_halfTourDirection_tourHour_tripIndex): %-15s", key));
            modelLogger.info(String.format("Tour Start Hour: %s, Tour End Hour: %s", tour.getTourStartHour(), tour.getTourEndHour()));
            modelLogger.info("Alternative        Probability");
            modelLogger.info("---------------    -----------");
            for(int k=0; k < probs.length; k++) {
                String altString = String.format( "%-3d", k);
                modelLogger.info(String.format("%-15s%18.6e", altString, probs[k]));
            }
        }
        
        
        //choose
        int stopId = stop.getStopId();
        int choosenHour = -1;
        int choice = -1;
        double rn;
        boolean valid = false;
        int maxDraws = 100;
        int counter = 0;
        do {
        
            rn = household.getHhRandom().nextDouble();
            choice = getMonteCarloSelection(probs, rn );
            if(stop.isInboundStop()) {
            	choosenHour = CtrampApplication.LAST_HOUR - choice; 
            } else {
            	choosenHour = choice + CtrampApplication.START_HOUR;
            }
            
            //ensure stop within tour time window and stop depart hours are in order for the tour
            //if cannot make a random choice them take next/prev stop hour
            if(choosenHour >= tour.getTourStartHour() && choosenHour <= tour.getTourEndHour()) {
            	
            	if(stop.isInboundStop()) {
            		if(stopId > 0) {
            			//last trip on half tour is only constrained by start of inbound half tour, but that has not been allocated yet
            			if(stopId == tour.getNumInboundStops()) {
            				valid = true;
            			} else {
            				Stop nextStop = tour.getInboundStops()[stopId+1];
            				Stop prevStop = tour.getInboundStops()[stopId-1];
                        	if(choosenHour >= prevStop.getDepartHour() && choosenHour <= nextStop.getDepartHour()) {
            					valid = true;
                			} else if(maxDraws == counter) {
                				choosenHour = nextStop.getDepartHour();
                			}
            			}
            		} else {
            			//first stop on inbound half tour must be greater than the last stop on outbound tour
            			Stop prevStop = tour.getOutboundStops()[tour.getNumOutboundStops()];
            			if(choosenHour >= prevStop.getDepartHour()) {
            				valid = true;
            			} else if(maxDraws == counter) {
            				choosenHour = prevStop.getDepartHour();
            			}
            		}
                } else {
                	Stop prevStop = tour.getOutboundStops()[stopId-1];
                	if(choosenHour >= prevStop.getDepartHour()) {
                		valid = true;
                	} else if(maxDraws == counter) {
                		choosenHour = prevStop.getDepartHour();
                	}
                }            
            } else {
                //if an hour is drawn outside the tour window repeatedly (and for the final time)
                if(stop.isInboundStop()) {
                	if(stopId > 0) {
                		choosenHour = stop.getDepartHour();	
                	} else {
                		Stop prevStop = tour.getOutboundStops()[tour.getNumOutboundStops()];
                		choosenHour = prevStop.getDepartHour();	
                	}
                } else {
                	if(stopId > 0) {
                		Stop prevStop = tour.getOutboundStops()[stopId-1];	
                		choosenHour = prevStop.getDepartHour();
                	} else {
                		choosenHour = stop.getDepartHour();
                	}
                }
            }
            counter++;
            
            //if(counter==(maxDraws-1)) {
            //	modelLogger.info("Redrawing Trip Depart Time Model for: HH_" + household.getHhId() + " Lookup Key: " + key);
            //}
        	
        } while(!valid && counter <= maxDraws);

        //log choice made
        if ( household.getDebugChoiceModels() ) {
	        modelLogger.info(" ");
	        if ( choice < 0 ) {
	            modelLogger.info( String.format("No Alternatives Available For Choice !!!" ) );
	        }
	        else {
	            modelLogger.info( String.format("Choice: %-3d (HR %s), with rn=%.8f", choice, choosenHour, rn) );
	        }
	        modelLogger.info( "" );
        }
        
        //return choice
        return choosenHour;
        
    }

    private int getMonteCarloSelection (double[] probabilities, double randomNumber) {

        int returnValue = 0;
        double sum = probabilities[0];
        for (int i=0; i < probabilities.length-1; i++) {
            if (randomNumber <= sum) {
                returnValue = i;
                break;
            }
            else {
                sum += probabilities[i+1];
                returnValue = i+1;
            }
        }
        return returnValue;
    }
 
    public long[][] getHhTimes() {
        hhTimes[0] = soaTime;
        hhTimes[1] = slsTime;
        hhTimes[2] = slcTime;
        hhTimes[3] = todTime;
        hhTimes[4] = mcTime;
        hhTimes[5] = plcTime;
        return hhTimes;
    }
    
}