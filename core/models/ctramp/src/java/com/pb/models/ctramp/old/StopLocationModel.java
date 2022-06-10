package com.pb.models.ctramp.old;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Stop;
import com.pb.models.ctramp.StopDestChoiceSize;
import com.pb.models.ctramp.StopLocationDMU;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.TripModeChoiceDMU;

import java.util.*;
import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;

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
public class StopLocationModel {
    
    public Logger logger = Logger.getLogger(StopFrequencyModel.class);

    public static final String PROPERTIES_UEC_STOP_LOCATION = "UecFile.StopLocation";
    public static final String PROPERTIES_UEC_TRIP_MODE_CHOICE = "UecFile.TripModeChoice";

    private static final int HOME_TYPE_INDEX = 1;
    private static final int PRIM_DEST_TYPE_INDEX = 2;
    private static final int INT_STOP_TYPE_INDEX = 3;
    
    private static final int UEC_DATA_PAGE = 0;
    private static final int WORK_UEC_MODEL_PAGE = 1;
    private static final int ESCORT_UEC_MODEL_PAGE = 2;
    private static final int SHOPPING_UEC_MODEL_PAGE = 3;
    private static final int EAT_OUT_UEC_MODEL_PAGE = 4;
    private static final int OTH_MAINT_STUDENT_UEC_MODEL_PAGE = 5;
    private static final int SOCIAL_UEC_MODEL_PAGE = 6;
    private static final int OTH_DISCR_UEC_MODEL_PAGE = 7;

    private static final int TRIP_MC_WORK_UEC_MODEL_PAGE = 1;
    private static final int TRIP_MC_ESCORT_UEC_MODEL_PAGE = 4;
    private static final int TRIP_MC_SHOPPING_UEC_MODEL_PAGE = 4;
    private static final int TRIP_MC_EAT_OUT_UEC_MODEL_PAGE = 4;
    private static final int TRIP_MC_OTH_MAINT_STUDENT_UEC_MODEL_PAGE = 4;
    private static final int TRIP_MC_SOCIAL_UEC_MODEL_PAGE = 4;
    private static final int TRIP_MC_OTH_DISCR_UEC_MODEL_PAGE = 4;

    public static final String PROPERTIES_RESULTS_TOUR_STOP = "Results.TourStop";

    private static StopDestinationSampleOfAlternativesModel dcSoaModel = null;
    private static StopDestChoiceSize dcSizeModel = null;

    protected TazDataIf tazDataManager;
    protected ModelStructure modelStructure;
    
    protected StopLocationDMU stopLocDmuObj;
    protected TripModeChoiceDMU tripModeChoiceDmuObj;

    protected Map<String,ChoiceModelApplication> stopLocChoiceModelAppLookup;
    protected Map<String,ChoiceModelApplication> tripModeChoiceModelAppLookup;
    protected Map<String,Integer> tripModeChoicePurposeIndexLookup;

    private boolean[] tripModeChoiceAvailability;
    private int[] tripModeChoiceSample;

    private int[] altToZone;
    private int[] altToSubZone;
    
    private float[] parkRate;
    
    private int[][] tripModeChoiceResultsFreq;


    /**
     * Constructor that will be used to set up the ChoiceModelApplications for each
     * type of tour
     * @param projectDirectory - name of root level project directory
     * @param resourceBundle - properties file with paths identified
     * @param dmuObject - decision making unit for stop frequency
     * @param tazDataManager - holds information about TAZs in the model.
     * @param modelStructure - holds the model structure info
     */
    public StopLocationModel(String projectDirectory, ResourceBundle resourceBundle, StopLocationDMU dmuObject, TripModeChoiceDMU tripMcDmuObject, TazDataIf tazDataManager, ModelStructure modelStructure) {

        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;
        
        altToZone = tazDataManager.getAltToZoneArray();
        altToSubZone = tazDataManager.getAltToSubZoneArray();
        parkRate = tazDataManager.getZonalParkRate();
        
        this.stopLocDmuObj = dmuObject;
        this.tripModeChoiceDmuObj = tripMcDmuObject;

        setupStopLocationCoiceModels( projectDirectory, resourceBundle );
        setupTripModeCoiceModels( projectDirectory, resourceBundle );

    }

    
    
    private void setupStopLocationCoiceModels( String projectDirectory, ResourceBundle resourceBundle ) {
        
        // locate the UEC
        String uecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_STOP_LOCATION);
        uecFileName = projectDirectory + uecFileName;

        stopLocChoiceModelAppLookup = new HashMap<String,ChoiceModelApplication>();
        stopLocChoiceModelAppLookup.put(modelStructure.WORK_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,WORK_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.ESCORT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,ESCORT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.SHOPPING_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,SHOPPING_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.EAT_OUT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,EAT_OUT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.OTH_MAINT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,OTH_MAINT_STUDENT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.SOCIAL_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,SOCIAL_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));
        stopLocChoiceModelAppLookup.put(modelStructure.OTH_DISCR_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,OTH_DISCR_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),stopLocDmuObj.getClass()));

                
        HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap( resourceBundle );
        synchronized (this) {
            if (dcSoaModel == null) {//initialize as needed, but only if needed so that cached probabilities in the soa model can be used
                dcSizeModel = new StopDestChoiceSize(propertyMap,tazDataManager,modelStructure);
                dcSoaModel = new StopDestinationSampleOfAlternativesModel(propertyMap,tazDataManager,dcSizeModel,modelStructure);
            }
        }

    }

    

    private void setupTripModeCoiceModels( String projectDirectory, ResourceBundle resourceBundle ) {
        
        // locate the UEC
        String uecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_TRIP_MODE_CHOICE);
        uecFileName = projectDirectory + uecFileName;

        tripModeChoiceModelAppLookup = new HashMap<String,ChoiceModelApplication>();
        tripModeChoiceModelAppLookup.put(modelStructure.WORK_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_WORK_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.ESCORT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_ESCORT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.SHOPPING_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_SHOPPING_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.EAT_OUT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_EAT_OUT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.OTH_MAINT_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_OTH_MAINT_STUDENT_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.SOCIAL_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_SOCIAL_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));
        tripModeChoiceModelAppLookup.put(modelStructure.OTH_DISCR_PURPOSE_NAME, new ChoiceModelApplication(uecFileName,TRIP_MC_OTH_DISCR_UEC_MODEL_PAGE,UEC_DATA_PAGE,ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),tripModeChoiceDmuObj.getClass()));

        tripModeChoicePurposeIndexLookup = new HashMap<String,Integer>();
        tripModeChoicePurposeIndexLookup.put(modelStructure.WORK_PURPOSE_NAME, 1 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.ESCORT_PURPOSE_NAME, 2 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.SHOPPING_PURPOSE_NAME, 3 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.EAT_OUT_PURPOSE_NAME, 4 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.OTH_MAINT_PURPOSE_NAME, 5 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.SOCIAL_PURPOSE_NAME, 6 );
        tripModeChoicePurposeIndexLookup.put(modelStructure.OTH_DISCR_PURPOSE_NAME, 7 );

        int numberOfAlternatives = tripModeChoiceModelAppLookup.get(modelStructure.WORK_PURPOSE_NAME).getNumberOfAlternatives();
        tripModeChoiceResultsFreq = new int[numberOfAlternatives+1][tripModeChoiceModelAppLookup.size()+1];

        tripModeChoiceAvailability = new boolean[numberOfAlternatives+1];
        tripModeChoiceSample = new int[numberOfAlternatives+1];
        Arrays.fill(tripModeChoiceAvailability,true);
        Arrays.fill(tripModeChoiceSample,1);
    }

    

    public void applyModel(HouseholdDataManagerIf householdDataManager){

        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        // loop over the households (1-based array)
        for(int i=1;i<householdArray.length;++i){

            Household household = householdArray[i];
            
            // get this household's person array
            Person[] personArray = household.getPersons();

            // set the household id, origin taz, hh taz, and debugFlag=false in the dmus
            stopLocDmuObj.setHouseholdObject(household);
            tripModeChoiceDmuObj.setHouseholdObject(household);

            
            // apply stop location and mode choice for all tours - add joint tours to list here.
            ArrayList<Tour> tours = new ArrayList<Tour>();
            Tour[] jointTours = household.getJointTourArray();
            if ( jointTours != null )
                for ( Tour jt : jointTours )
                    tours.add( jt );
            
            // loop through the person array (1-based)
            for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];

                // set the person
                stopLocDmuObj.setPersonObject(person);
                tripModeChoiceDmuObj.setPersonObject(person);

                // individual tours for the person to the tour list
                tours.addAll( person.getListOfWorkTours() );
                tours.addAll( person.getListOfSchoolTours() );
                tours.addAll( person.getListOfIndividualNonMandatoryTours() );
                tours.addAll( person.getListOfAtWorkSubtours() );

                int tourCount=1;
                for ( Tour tour : tours ) {

                    // set the tour object
                    stopLocDmuObj.setTourObject(tour);
                    tripModeChoiceDmuObj.setTourObject(tour);

                    //loop over all inbound and outbound stops
                    boolean inbound = false;
                    for (Stop[] stops : new Stop[][]{ tour.getOutboundStops(),tour.getInboundStops() }) {
                        int stopCount = 1;
                        int origin = inbound ? tour.getTourDestTaz() : household.getHhTaz();
                        int originWalkSegment = inbound ? tour.getTourDestWalkSubzone() : household.getHhWalkSubzone();
                        int dest = inbound ? tour.getTourOrigTaz() : tour.getTourDestTaz();
                        
                        tripModeChoiceDmuObj.setOrigType( inbound ? PRIM_DEST_TYPE_INDEX : HOME_TYPE_INDEX );
                        tripModeChoiceDmuObj.setOrigParkRate( parkRate[origin] );
                        tripModeChoiceDmuObj.setDestType( inbound ? HOME_TYPE_INDEX : PRIM_DEST_TYPE_INDEX );
                        tripModeChoiceDmuObj.setPrimDestParkRate( parkRate[dest] );
                        
                        stopLocDmuObj.setInboundStop(inbound);
                        
                        if (stops == null)
                            continue;
                        
                        for (Stop stop : stops) {
                            stopLocDmuObj.setStopNumber(stopCount);
                            stopLocDmuObj.setDmuIndexValues(household.getHhId(),household.getHhTaz(),origin,dest);
                            stop.setOrig(origin);
                            stop.setOrigWalkSegment(originWalkSegment);
                            try {
                                int choice = selectDestination(stop);
                                int zone = altToZone[choice];
                                int subzone = altToSubZone[choice];
                                stop.setDest(zone);
                                stop.setDestWalkSegment(subzone);
                                tripModeChoiceDmuObj.setDestType( INT_STOP_TYPE_INDEX );
                                tripModeChoiceDmuObj.setIntStopParkRate( parkRate[zone] );
                                tripModeChoiceDmuObj.setDmuIndexValues( household.getHhId(), origin, zone );
                                tripModeChoiceDmuObj.setOrigCounty(tazDataManager.getZoneCounty(origin));
                          
                                choice = selectMode(household, tour, stop);
                                stop.setMode( choice );
                                int purposeIndex = tripModeChoicePurposeIndexLookup.get( stop.getDestPurpose( modelStructure ) );
                                tripModeChoiceResultsFreq[choice][purposeIndex]++;
                                
                                origin = zone;
                                originWalkSegment = subzone;
                                tripModeChoiceDmuObj.setOrigType( INT_STOP_TYPE_INDEX );
                                tripModeChoiceDmuObj.setOrigParkRate( parkRate[zone] );
                                stopCount++;
                            } catch ( Exception e ) {
                                logger.error ( String.format( "Exception caught processing " + (inbound ? "inbound" : "outbound") + " stop location choice model for %s type tour %s stop:  i=%d, j=%d, HHID=%d, personNum=%d, tourCount=%d, stop=%d.", ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], stop.getDestPurpose(modelStructure),i, j, household.getHhId(), person.getPersonNum(), tourCount, stopCount ) );
                                throw new RuntimeException(e);
                            }
                        }
                        inbound = true;
                    }
                    tourCount++;

                } //tour loop
            } // j (person loop)
        } // i (household loop)


        householdDataManager.setHhArray(householdArray);
        householdDataManager.setStlRandomCount();

    }

    private int selectDestination(Stop s) {
        StopDestinationSampleOfAlternativesModel.StopSoaResult result =  dcSoaModel.computeDestinationSampleOfAlternatives(s);
        int[] sample = result.getSample();
        float[] corrections = result.getCorrections();

        ChoiceModelApplication choiceModel = stopLocChoiceModelAppLookup.get(s.getDestPurpose(modelStructure));
        int altCount = choiceModel.getNumberOfAlternatives();
        boolean[] destinationAvailability = new boolean[altCount+1];
        int[] destinationSample = new int[altCount+1];
        Arrays.fill(destinationAvailability,false);
        Arrays.fill(destinationSample,0);
        for (int i = 1; i < sample.length; i++) {
            int alternative = sample[i];
            destinationAvailability[alternative] = true;
            destinationSample[alternative] = 1;
            stopLocDmuObj.setDcSoaCorrections(altToZone[alternative],altToSubZone[alternative],corrections[i]);
        }

        choiceModel.computeUtilities(stopLocDmuObj,stopLocDmuObj.getDmuIndexValues(),destinationAvailability,destinationSample);

        Random hhRandom = stopLocDmuObj.getHouseholdObject().getHhRandom();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        if ( choiceModel.getAvailabilityCount() > 0 )
            chosen = choiceModel.getChoiceResult( rn );
        else {
            logger.error (String.format( "Error for HHID=%d, PersonNum=%d, no available %s stop destination choice alternatives to choose from in choiceModelApplication.", stopLocDmuObj.getHouseholdObject().getHhId(), stopLocDmuObj.getPersonObject().getPersonNum(), s.getDestPurpose(modelStructure)));
            throw new RuntimeException();
        }

        // write choice model alternative info to log file
        if ( stopLocDmuObj.getHouseholdObject().getDebugChoiceModels() ) {
            choiceModel.logAlternativesInfo ("Stop Destination Choice", String.format("HH_%d, PERS_%d", stopLocDmuObj.getHouseholdObject().getHhId(), stopLocDmuObj.person.getPersonNum()) );
            choiceModel.logSelectionInfo ("Stop Destination Choice", String.format("HH_%d, PERS_%d", stopLocDmuObj.getHouseholdObject().getHhId(), stopLocDmuObj.person.getPersonNum()), rn, chosen );
        }
        return chosen;
    }

    
    private int selectMode ( Household household, Tour tour, Stop stop ) {

        ChoiceModelApplication choiceModel = tripModeChoiceModelAppLookup.get(stop.getDestPurpose(modelStructure));
        choiceModel.computeUtilities( tripModeChoiceDmuObj, tripModeChoiceDmuObj.getDmuIndexValues(), tripModeChoiceAvailability, tripModeChoiceSample );

        Random hhRandom = household.getHhRandom();

        // if the choice model has at least one available alternative, make choice.
        int chosen;
        if ( choiceModel.getAvailabilityCount() > 0 )
            chosen = choiceModel.getChoiceResult( hhRandom.nextDouble() );
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available %s trip mode alternatives in tourId=%d to choose from in choiceModelApplication.", household.getHhId(), ModelStructure.TOUR_CATEGORY_LABELS[tour.getTourCategoryIndex()], tour.getTourId() ) );
            throw new RuntimeException();
        }
        return chosen;

    }
    
    
    public void saveResults(HouseholdDataManagerIf householdDataManager, ResourceBundle resourceBundle) {
        File outputFile = new File(resourceBundle.getString(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY) + resourceBundle.getString(PROPERTIES_RESULTS_TOUR_STOP));
        PrintWriter writer = null;
        try {
            writer = new PrintWriter(outputFile);
            List<String> headers = new LinkedList<String>();
            headers.addAll(Arrays.asList("HHID","PersonID","PersonNum","PersonType","Age","CDAP","HomeTAZ","TourFrequency"));
            String personDataFormat = "%d,%d,%d,%s,%d,%s,%d,%d";
            //purpose origin originwz dest destwz mode
            String[] stopDataHeaders = new String[] {"Purpose","Origin","OriginSubzone","Dest","DestSubzone","Mode"};
            String stopDataFormat = ",%s,%d,%d,%d,%d,%s";
            String emptyEntry = "NA";
            String emptyStopEntry = "";
            for (int i = 0; i < stopDataHeaders.length; i++)
                emptyStopEntry += "," + emptyEntry;

            //build rest of headers
            Map<String,Integer> headerCountMap = new LinkedHashMap<String,Integer>();
            int maxMandatoryTours = 3;
            int maxNonMandatoryTours = 5;
            int maxStopCount = 3;
            headerCountMap.put("M",maxMandatoryTours);
            headerCountMap.put("NM",maxNonMandatoryTours);
            String[] directionIndicators = new String[] {"OB","IB"};
            for (String tourType : headerCountMap.keySet()) {
                for (int i = 1; i <= headerCountMap.get(tourType); i++) {
                    for (String direction : directionIndicators) {
                        for (int j = 1; j <= maxStopCount; j++) {
                            for (String column : stopDataHeaders) {
                                headers.add(tourType + i + direction + j + column);
                            }
                        }
                    }
                }
            }
            String emptyTourEntry = "";
            for (int i = 0; i < maxStopCount*directionIndicators.length; i++)
                    emptyTourEntry += emptyStopEntry;

            //write headers
            String headerFormat = "%s";
            for (int i = 1; i < headers.size(); i++)
                headerFormat += ",%s";
            String[] tempArray = headers.toArray(new String[headers.size()]);
            writer.println(String.format(headerFormat,tempArray));

            //loop through all households and write results
            Household[] householdArray = householdDataManager.getHhArray();
            for(int i=1; i < householdArray.length; ++i){

                Household household = householdArray[i];
                int hhId = household.getHhId();
                int hhTaz = household.getHhTaz();

                Person[] personArray = household.getPersons();
                for (int j = 1; j < personArray.length; ++j) {
                    StringBuilder line = new StringBuilder();

                    Person person = personArray[j];
                    int personId = person.getPersonId();
                    int personNum = person.getPersonNum();
                    int personAge = person.getAge();
                    String personType = person.getPersonType();
                    String cdap = person.getCdapActivity();
                    int tourFrequency = person.getInmtfChoice();
                    line.append(String.format(personDataFormat,hhId,personId,personNum,personType,personAge,cdap,hhTaz,tourFrequency));

                    int tourCount = 0;
                    for (Tour t : person.getListOfWorkTours()) {
                        tourCount += 1;
                        addTourStopData(t,line,maxStopCount,emptyStopEntry,stopDataFormat);
                    }
                    if (tourCount > maxMandatoryTours) {
                        System.out.println("Mand tour count: " + tourCount);
                    }
                    for (Tour t : person.getListOfSchoolTours()) {
                        tourCount += 1;
                        addTourStopData(t,line,maxStopCount,emptyStopEntry,stopDataFormat);
                    }
                    for (int k = 0; k < maxMandatoryTours - tourCount; k++)
                        line.append(emptyTourEntry);

                    tourCount = 0;
                    for (Tour t : person.getListOfIndividualNonMandatoryTours()) {
                        tourCount += 1;
                        addTourStopData(t,line,maxStopCount,emptyStopEntry,stopDataFormat);
                    }
                    for (int k = 0; k < maxNonMandatoryTours - tourCount; k++)
                        line.append(emptyTourEntry);

                    writer.println(line);
                }
             }
        } catch (IOException e) {
            logger.error("Error writing output results file for tour stops.");
        } finally {
            if (writer != null)
                writer.close();
        }
    }

    private void addTourStopData(Tour t, StringBuilder sb, int maxStopCount, String emptyStopEntry, String stopDataFormat) {
        addHalfTourStopData(t.getOutboundStops(),sb,maxStopCount,emptyStopEntry,stopDataFormat);
        addHalfTourStopData(t.getInboundStops(),sb,maxStopCount,emptyStopEntry,stopDataFormat);
    }

    private void addHalfTourStopData(Stop[] stops, StringBuilder sb, int maxStopCount, String emptyStopEntry, String stopDataFormat) {
        int stopCount = 0;
        for (Stop s : stops) {
            stopCount += 1;
            addStopData(s,sb,stopDataFormat);
        }
        for (int k = 0; k < maxStopCount - stopCount; k++)
            sb.append(emptyStopEntry);
    }

    private void addStopData(Stop s, StringBuilder sb, String stopDataFormat) {
        //"Purpose","Origin","OriginSubzone","Dest","DestSubzone","Mode"
        sb.append(String.format(stopDataFormat,s.getDestPurpose(modelStructure),s.getOrig(),s.getOrigWalkSegment(),s.getDest(),s.getDestWalkSegment(),getModeName(s.getMode())));
    }

    private String getModeName(int modeIndex) {
        return "NA";
    }


    public void logResults(){

        String[] modeAltLabels = tripModeChoiceModelAppLookup.get(modelStructure.WORK_PURPOSE_NAME).getAlternativeNames();

        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info("Trip Mode Choice Model Results");


        logger.info(" ");
        logger.info ( String.format( "%-5s   %-20s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s   %8s", "alt", "alt name", "work", "univ", "school", "escort", "shop", "eat out", "maint", "visit", "discr", "total" ) );

        
        String logString = "";

        int[] columnTotals = new int[tripModeChoicePurposeIndexLookup.size()+1];
        for ( int i=0; i < modeAltLabels.length; i++ ) {

            logString = String.format( "%-5d   %-20s", i+1, modeAltLabels[i] );

            int rowTotal = 0;
            for ( int j=1; j < columnTotals.length; j++ ) {
                columnTotals[j] += tripModeChoiceResultsFreq[i+1][j];
                rowTotal += tripModeChoiceResultsFreq[i+1][j];
                logString += String.format( "   %8d", tripModeChoiceResultsFreq[i+1][j] );
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

}