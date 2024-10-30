package com.pb.models.ctramp;

import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.util.ObjectUtil;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.jppf.CtrampApplication;
import com.pb.models.ctramp.jppf.StopLocationModeChoiceModel;
import com.pb.models.ctramp.sqlite.ConnectionHelper;

import java.util.*;
import java.io.PrintWriter;
import java.io.File;
import java.io.IOException;
import java.sql.SQLException;
import java.sql.Connection;
import java.sql.Statement;
import java.sql.PreparedStatement;

import org.apache.log4j.Logger;

/**
 * @author crf <br/>
 *         Started: Dec 31, 2008 11:46:36 AM
 */
public class HouseholdDataWriter {
    
    private transient Logger logger = Logger.getLogger(HouseholdDataWriter.class);
    
    private static final String PROPERTIES_HOUSEHOLD_DATA_FILE    = "Results.HouseholdDataFile";
    private static final String PROPERTIES_PERSON_DATA_FILE       = "Results.PersonDataFile";
    private static final String PROPERTIES_INDIV_TOUR_DATA_FILE   = "Results.IndivTourDataFile";
    private static final String PROPERTIES_JOINT_TOUR_DATA_FILE   = "Results.JointTourDataFile";
    private static final String PROPERTIES_INDIV_TRIP_DATA_FILE   = "Results.IndivTripDataFile";
    private static final String PROPERTIES_JOINT_TRIP_DATA_FILE   = "Results.JointTripDataFile";
    private static final String PROPERTIES_TRIP_DATA_FILE         = "Results.TripDataFile";
    private static final String PROPERTIES_TRAVEL_TIME_DATA_FILE  = "Results.TravelTimeDataFile";
    private static final String PROPERTIES_TRAVEL_TIME_FORMAT     = "Results.TravelTimeFormat";

    private static final String PROPERTIES_HOUSEHOLD_TABLE  = "Results.HouseholdTable";
    private static final String PROPERTIES_PERSON_TABLE     = "Results.PersonTable";
    private static final String PROPERTIES_INDIV_TOUR_TABLE = "Results.IndivTourTable";
    private static final String PROPERTIES_JOINT_TOUR_TABLE = "Results.JointTourTable";
    private static final String PROPERTIES_INDIV_TRIP_TABLE = "Results.IndivTripTable";
    private static final String PROPERTIES_JOINT_TRIP_TABLE = "Results.JointTripTable";

    private static final int NUM_WRITE_PACKETS = 2000;

    private final String intFormat = "%d";
    private final String floatFormat = "%f";
    private final String doubleFormat = "%f";
    private final String fileStringFormat = "%s";
    private final String databaseStringFormat = "'%s'";
    private String stringFormat = fileStringFormat;

    private boolean saveUtilsProbsFlag = false;
    
    private ResourceBundle resourceBundle;
    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;
    private int iteration;
    private TravelTimeModel travelTimeModel;
    private CtrampDmuFactoryIf dmuFactory;

    private Map<String,Map<Integer,String>> tourModeAltLabels; //purpose -> mode id -> mode name
    private Map<Integer,Map<Integer,String>> tripModeAltLabels; //trip mode choice purpose index -> mode id -> mode name;

    
    
    public HouseholdDataWriter( ResourceBundle resourceBundle, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory, int iteration ) {

        logger.info("Writing data structures to files.");
        this.resourceBundle = resourceBundle;
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;
        this.dmuFactory = dmuFactory;
        this.iteration = iteration;

        // default is to not save the tour mode choice utils and probs for each tour
        String saveUtilsProbsString = resourceBundle.getString( CtrampApplication.PROPERTIES_SAVE_TOUR_MODE_CHOICE_UTILS );
        if ( saveUtilsProbsString != null ) {
            if ( saveUtilsProbsString.equalsIgnoreCase( "true" ) )
                saveUtilsProbsFlag = true;
        }

    }

    //NOTE - this method should not be called simultaneously with the file one one as the string format is changed
    public void writeDataToDatabase(HouseholdDataManagerIf householdData, String dbFileName) {
        logger.info("Writing data structures to database.");
        long t = System.currentTimeMillis();
        stringFormat = databaseStringFormat;
        writeData(householdData,new DatabaseDataWriter(dbFileName));
        float delta = ((Long) (System.currentTimeMillis() - t)).floatValue() / 60000.0f;
        logger.info("Finished writing data structures to database (" + delta + " minutes).");
    }
    //NOTE - this method should not be called simultaneously with the database one one as the string format is changed
    public void writeDataToFiles(HouseholdDataManagerIf householdData) {
        stringFormat = fileStringFormat;
        FileDataWriter fdw = new FileDataWriter();
        writeData(householdData,fdw);
    }
    

    private void writeData(HouseholdDataManagerIf householdDataManager, DataWriter writer) {
        int hhid=0;
        int persNum = 0;
        int tourid = 0;

        boolean fileWriter = writer instanceof FileDataWriter; //only write trips if writing to file

        if (writer.getWriteTripFileFlag()) {
            loadTourModes(resourceBundle,dmuFactory);
            loadTripModes(resourceBundle,dmuFactory);
        }
        
        if (writer.getWriteTravelTimesFileFlag() || writer.getWriteTripFileFlag()) {
            travelTimeModel = new TravelTimeModel(ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle));
        }

        try {

            ArrayList<int[]> startEndTaskIndicesList = getWriteHouseholdRanges( householdDataManager.getNumHouseholds() );

            long maxSize = 0;
            for ( int[] startEndIndices : startEndTaskIndicesList ) {
            
                int startIndex = startEndIndices[0];
                int endIndex = startEndIndices[1];

            
                // get the array of households
                Household[] householdArray = householdDataManager.getHhArray( startIndex, endIndex );
            
                for (Household hh : householdArray) {
                    if (hh == null) continue;
                    hhid = hh.getHhId();
                    
                    long size = 0;
                    try{
                        size = ObjectUtil.checkObjectSize( hh );                        
                    }
                    catch ( Exception e ){
                    }
                    if ( size > maxSize )
                        maxSize = size;

                    
                    writer.writeHouseholdData(formHouseholdDataEntry(hh));
                    for (Person p : hh.getPersons()) {
                        if (p == null) continue;
                        persNum = p.getPersonNum(); 
                        
                        writer.writePersonData(formPersonDataEntry(p));
                        for (Tour t : p.getListOfWorkTours())
                            writeIndivTourData(t,writer);
                        for (Tour t : p.getListOfSchoolTours())
                            writeIndivTourData(t,writer);
                        for (Tour t : p.getListOfIndividualNonMandatoryTours())
                            writeIndivTourData(t,writer);
                        for (Tour t : p.getListOfAtWorkSubtours())
                            writeIndivTourData(t,writer);
                    }
                    Tour[] jointTours = hh.getJointTourArray();
                    if (jointTours != null) {
                        for (Tour t : jointTours)  {
                            if (t == null) continue;
                            writeJointTourData(t,writer);
                        }
                    }

                    if (fileWriter && writer.getWriteTripFileFlag()) {
                        writer.writeTripData(createVizTripRecords(hh));
                    }
                }
            }
            
            logger.info( "max size for all Household objects after writing output files is " + maxSize + " bytes." );

            if (fileWriter && writer.getWriteTravelTimesFileFlag()) {
                logger.info("Writing travel time table");
                int[] tazs = tazDataManager.getIndexToZoneArray();
                writer.writeTravelTimeData(Arrays.copyOfRange(tazs,1,tazs.length));
            }

        } catch ( RuntimeException e ) {
            logger.error( String.format( "error writing hh=%d, persNum=%d, tourId=%d", hhid, persNum, tourid ), e);
            throw new RuntimeException();
        } finally {
            writer.finishActions();
        }
    }
    
   
    

    private void writeIndivTourData(Tour t, DataWriter writer) {
        writer.writeIndivTourData(formIndivTourDataEntry(t));
        
        Stop[] outboundStops = t.getOutboundStops();
        if ( outboundStops != null ) {
            for ( int i=0; i < outboundStops.length; i++ ) {
                writer.writeIndivTripData(formIndivTripDataEntry(outboundStops[i]));
            }
        }
        else {
            writer.writeIndivTripData(formTourAsIndivTripDataEntry(t, false));
        }
        
        Stop[] inboundStops = t.getInboundStops();
        if ( inboundStops != null ) {
            for ( Stop s : inboundStops )
                writer.writeIndivTripData(formIndivTripDataEntry(s));
        }
        else {
            writer.writeIndivTripData(formTourAsIndivTripDataEntry(t, true));
        }
        
    }


    private void writeJointTourData(Tour t, DataWriter writer) {
        writer.writeJointTourData(formJointTourDataEntry(t));
        
        Stop[] outboundStops = t.getOutboundStops();
        if ( outboundStops != null ) {
            for ( Stop s : outboundStops )
                writer.writeJointTripData(formJointTripDataEntry(s));
        }
        else {
            writer.writeJointTripData(formTourAsJointTripDataEntry(t, false));
        }
        
        Stop[] inboundStops = t.getInboundStops();
        if ( inboundStops != null ) {
            for ( Stop s : inboundStops )
                writer.writeJointTripData(formJointTripDataEntry(s));
        }
        else {
            writer.writeJointTripData(formTourAsJointTripDataEntry(t, true));
        }
        
    }


    private String string(int value) {
        return String.format(intFormat,value);
    }

    private String string(float value) {
        return String.format(floatFormat,value);
    }

    private String string(double value) {
        return String.format(doubleFormat,value);
    }

    private String string(String value) {
        return String.format(stringFormat,value);
    }

   private List<String> formHouseholdColumnNames() {
        List<String> data = new LinkedList<String>();
        data.add("hh_id");
        data.add("taz");
        data.add("walk_subzone");
        data.add("income");
        data.add("autos");
        data.add("cdap_pattern");
        data.add("jtf_choice");
        data.add("jtf_pattern");
        data.add("size");
        data.add("workers");
        data.add("auto_suff");
        data.add("ao_rn");
        data.add("fp_rn");
        data.add("cdap_rn");
        data.add("imtf_rn");
        data.add("imtod_rn");
        data.add("immc_rn");
        data.add("jtf_rn");
        data.add("jtl_rn");
        data.add("jtod_rn");
        data.add("jmc_rn");
        data.add("inmtf_rn");
        data.add("inmtl_rn");
        data.add("inmtod_rn");
        data.add("inmmc_rn");
        data.add("awf_rn");
        data.add("awl_rn");
        data.add("awtod_rn");
        data.add("awmc_rn");
        data.add("stf_rn");
        data.add("stl_rn");
        data.add("humanVehicles");
        data.add("autonomousVehicles");
        data.add("sampleRate");


        return data;
    }
   

   private List<SqliteDataTypes> formHouseholdColumnTypes() {
        List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.REAL);
        
        return data;
    }

    private List<String> formHouseholdDataEntry(Household hh) {
    	
    	int diff = hh.getAutoOwnershipModelResult() - hh.getWorkers();
        String suff = diff < 0 ? "cars<wkrs" : diff >= 0 ? "cars>=wkrs" : "nocars";
    	
        List<String> data = new LinkedList<String>();
        data.add(string(hh.getHhId()));
        data.add(string(hh.getHhTaz()));
        data.add(string(hh.getHhWalkSubzone()));
        data.add(string(hh.getIncomeInDollars()));
        data.add(string(hh.getAutoOwnershipModelResult()));
        data.add(hh.getCoordinatedDailyActivityPattern());
        data.add(string(hh.getJointTourFreqChosenAlt()));
        data.add(hh.getJointTourFreqChosenAltName());
        data.add(string(hh.getSize()));
        data.add(string(hh.getWorkers()));
        data.add(suff);
        data.add(string(hh.getAoRandomCount()));
        data.add(string(hh.getFpRandomCount()));
        data.add(string(hh.getCdapRandomCount()));
        data.add(string(hh.getImtfRandomCount()));
        data.add(string(hh.getImtodRandomCount()));
        data.add(string(hh.getImmcRandomCount()));
        data.add(string(hh.getJtfRandomCount()));
        data.add(string(hh.getJtlRandomCount()));
        data.add(string(hh.getJtodRandomCount()));
        data.add(string(hh.getJmcRandomCount()));
        data.add(string(hh.getInmtfRandomCount()));
        data.add(string(hh.getInmtlRandomCount()));
        data.add(string(hh.getInmtodRandomCount()));
        data.add(string(hh.getInmmcRandomCount()));
        data.add(string(hh.getAwfRandomCount()));
        data.add(string(hh.getAwlRandomCount()));
        data.add(string(hh.getAwtodRandomCount()));
        data.add(string(hh.getAwmcRandomCount()));
        data.add(string(hh.getStfRandomCount()));
        data.add(string(hh.getStlRandomCount()));
        data.add(string(hh.getHumanVehicles()));
        data.add(string(hh.getAutonomousVehicles()));
        data.add(string(hh.getSampleRate()));
        return data;
    }

   private List<String> formPersonColumnNames() {
        List<String> data = new LinkedList<String>();
        data.add("hh_id");
        data.add("person_id");
        data.add("person_num");
        data.add("age");
        data.add("gender");
        data.add("type");
        data.add("value_of_time"); 
        data.add("fp_choice");
        data.add("activity_pattern");
        data.add("imf_choice");
        data.add("inmf_choice");
        data.add("workDCLogsum");
        data.add("schoolDCLogsum");
        data.add("sampleRate");
        data.add("wfh_choice");
        data.add("industry");
        return data;
    }

   private List<SqliteDataTypes> formPersonColumnTypes() {
        List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.REAL); 
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.REAL); 
        data.add(SqliteDataTypes.REAL); 
        data.add(SqliteDataTypes.REAL); 
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        return data;
    }

   private List<String> formPersonDataEntry(Person p) {
        List<String> data = new LinkedList<String>();
        data.add(string(p.getHouseholdObject().getHhId()));
        data.add(string(p.getPersonId()));
        data.add(string(p.getPersonNum()));
        data.add(string(p.getAge()));
        data.add(string(p.getPersonIsMale() == 1 ? "m" : "f"));
        data.add(string(p.getPersonType()));
        data.add(string(p.getValueOfTime())); 
        data.add(string(p.getFreeParkingAvailableResult()));
        data.add(string(p.getCdapActivity()));
        data.add(string(p.getImtfChoice()));
        data.add(string(p.getInmtfChoice()));
        data.add(string(p.getWorkLocationLogsum()));
        data.add(string(p.getSchoolLocationLogsum()));
        float sampleRate = p.getSampleRate();
        data.add(string(sampleRate));
        data.add(string(p.getPersonWorksFromHome()));
        data.add(p.getPersonIndustry());
        return data;
    }

   private List<String> formIndivTourColumnNames() {
       List<String> data = new LinkedList<String>();
       data.add("hh_id");
       data.add("person_id");
       data.add("person_num");
       data.add("person_type");
       data.add("tour_id");
       data.add("tour_category");                     
       data.add("tour_purpose");
       data.add("orig_taz");
       data.add("orig_walk_segment");
       data.add("dest_taz");
       data.add("dest_walk_segment");
       data.add("start_hour");
       data.add("end_hour");
       data.add("tour_mode");
       data.add("atWork_freq");
       data.add("num_ob_stops");
       data.add("num_ib_stops");
       data.add("avAvailable");
       data.add("dcLogsum");
       data.add("sampleRate");
       data.add("origTaxiWait");
       data.add("destTaxiWait");
       data.add("origSingleTNCWait");
       data.add("destSingleTNCWait");
       data.add("origSharedTNCWait");
       data.add("destSharedTNCWait");
       
       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           for ( int i=1; i <= numModeAlts; i++ ) {
               String colName = String.format( "util_%d", i );
               data.add( colName );
           }
           
           for ( int i=1; i <= numModeAlts; i++ ) {
               String colName = String.format( "prob_%d", i );
               data.add( colName );
           }
       }
       
       return data;
   }

   private List<String> formJointTourColumnNames() {
       List<String> data = new LinkedList<String>();
       data.add("hh_id");
       data.add("tour_id");
       data.add("tour_category");                     
       data.add("tour_purpose");
       data.add("tour_composition");
       data.add("tour_participants");
       data.add("orig_taz");
       data.add("orig_walk_segment");
       data.add("dest_taz");
       data.add("dest_walk_segment");
       data.add("start_hour");
       data.add("end_hour");
       data.add("tour_mode");
       data.add("num_ob_stops");
       data.add("num_ib_stops");
       data.add("avAvailable");
       data.add("dcLogsum");
       data.add("sampleRate");
       data.add("origTaxiWait");
       data.add("destTaxiWait");
       data.add("origSingleTNCWait");
       data.add("destSingleTNCWait");
       data.add("origSharedTNCWait");
       data.add("destSharedTNCWait");
       
       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           for ( int i=1; i <= numModeAlts; i++ ) {
               String colName = String.format( "util_%d", i );
               data.add( colName );
           }
           
           for ( int i=1; i <= numModeAlts; i++ ) {
               String colName = String.format( "prob_%d", i );
               data.add( colName );
           }
       }
       
       return data;
   }

   private List<SqliteDataTypes> formIndivTourColumnTypes() {
       List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.TEXT);
       data.add(SqliteDataTypes.TEXT);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
             
       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           for ( int i=1; i <= numModeAlts; i++ ) {
               data.add( SqliteDataTypes.REAL );
           }
           
           for ( int i=1; i <= numModeAlts; i++ ) {
               data.add( SqliteDataTypes.REAL );
           }
       }
       
       return data;
   }

   private List<SqliteDataTypes> formJointTourColumnTypes() {
       List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.TEXT);
       data.add(SqliteDataTypes.TEXT);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.INTEGER);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);
       data.add(SqliteDataTypes.REAL);

       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           for ( int i=1; i <= numModeAlts; i++ ) {
               data.add( SqliteDataTypes.REAL );
           }
           
           for ( int i=1; i <= numModeAlts; i++ ) {
               data.add( SqliteDataTypes.REAL );
           }
       }
       
       return data;
   }

   private List<String> formIndivTourDataEntry(Tour t) {
       
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getPersonObject().getPersonId()));
       data.add(string(t.getPersonObject().getPersonNum()));
       data.add(string(t.getPersonObject().getPersonTypeNumber()));
       data.add(string(t.getTourId()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string(t.getTourPurpose()));
       data.add(string(t.getTourOrigTaz()));
       data.add(string(t.getTourOrigWalkSubzone()));
       data.add(string(t.getTourDestTaz()));
       data.add(string(t.getTourDestWalkSubzone()));
       data.add(string(t.getTourStartHour()));
       data.add(string(t.getTourEndHour()));
       data.add(string(t.getTourModeChoice()));
       data.add(string(t.getSubtourFreqChoice()));
       data.add(string( t.getNumOutboundStops() == 0 ? 0 : t.getNumOutboundStops()) );
       data.add(string( t.getNumInboundStops() == 0 ? 0 : t.getNumInboundStops()) );
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(t.getDestinationChoiceLogsum()));
       float sampleRate = t.getSampleRate();
       data.add(string(sampleRate));
       data.add(string(t.getOrigTaxiWait()));
       data.add(string(t.getDestTaxiWait()));
       data.add(string(t.getOrigTNCSingleWait()));
       data.add(string(t.getDestTNCSingleWait()));
       data.add(string(t.getOrigTNCSharedWait()));
       data.add(string(t.getDestTNCSharedWait()));
       
       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           float[] utils = t.getTourModalUtilities();
           for ( int i=0; i < utils.length; i++ )
               data.add(string(utils[i]));
           for ( int i=utils.length; i < numModeAlts; i++ )
               data.add( "-999" );
           
           float[] probs = t.getTourModalProbabilities();
           for ( int i=0; i < probs.length; i++ )
               data.add(string(probs[i]));
           for ( int i=probs.length; i < numModeAlts; i++ )
               data.add( "0.0" );
       }
       
       return data;
   }

   private List<String> formJointTourDataEntry(Tour t) {
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getTourId()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string(t.getTourPurpose()));
       data.add(string(t.getJointTourComposition()));
       data.add(string(formTourParticipationEntry(t)));
       data.add(string(t.getTourOrigTaz()));
       data.add(string(t.getTourOrigWalkSubzone()));
       data.add(string(t.getTourDestTaz()));
       data.add(string(t.getTourDestWalkSubzone()));
       data.add(string(t.getTourStartHour()));
       data.add(string(t.getTourEndHour()));
       data.add(string(t.getTourModeChoice()));
       data.add(string( t.getNumOutboundStops() == 0 ? 0 : t.getNumOutboundStops()) );
       data.add(string( t.getNumInboundStops() == 0 ? 0 : t.getNumInboundStops()) );
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(t.getDestinationChoiceLogsum()));
       float sampleRate = t.getSampleRate();
       data.add(string(sampleRate));
       data.add(string(t.getOrigTaxiWait()));
       data.add(string(t.getDestTaxiWait()));
       data.add(string(t.getOrigTNCSingleWait()));
       data.add(string(t.getDestTNCSingleWait()));
       data.add(string(t.getOrigTNCSharedWait()));
       data.add(string(t.getDestTNCSharedWait()));

       if ( saveUtilsProbsFlag ) {
           int numModeAlts = modelStructure.getMaxTourModeIndex();
           float[] utils = t.getTourModalUtilities();
           for ( int i=0; i < utils.length; i++ )
               data.add(string(utils[i]));
           for ( int i=utils.length; i < numModeAlts; i++ )
               data.add( "-999" );
           
           float[] probs = t.getTourModalProbabilities();
           for ( int i=0; i < probs.length; i++ )
               data.add(string(probs[i]));
           for ( int i=probs.length; i < numModeAlts; i++ )
               data.add( "0.0" );
       }
       
       return data;
   }

    private String formTourParticipationEntry(Tour t) {
        byte[] persons = t.getPersonNumArray();
        if (persons == null)
            throw new RuntimeException("null Person[] object for joint tour, hhid=" + t.getHhId());
        if (persons.length == 1)
            throw new RuntimeException("Person[] object has length=1 for joint tour, hhid=" + t.getHhId());
        String participation = Integer.toString( persons[0] );
        for (int i=1; i < persons.length; i++ ) {
            participation += " ";
            participation += persons[i];
        }
        return participation;
    }

    /*
    private int getBitMask(int number) {
        switch (number) {
            case 1 : return 1;
            case 2 : return 2;
            case 3 : return 4;
            case 4 : return 8;
            case 5 : return 16;
            case 6 : return 32;
            case 7 : return 64;
            case 8 : return 128;
            case 9 : return 256;
            case 10 : return 512;
            case 11 : return 1024;
            case 12 : return 2048;
            case 13 : return 4096;
            case 14 : return 8192;
            case 15 : return 16384;
            case 16 : return 32768;
            case 17 : return 65536;
            case 18 : return 131072;
            case 19 : return 262144;
            case 20 : return 524288;
            case 21 : return 1048576;
            case 22 : return 2097152;
            case 23 : return 4194304;
            case 24 : return 8388608;
            case 25 : return 16777216;
            case 26 : return 33554432;
            case 27 : return 67108864;
            case 28 : return 134217728;
            case 29 : return 268435456;
            case 30 : return 536870912;
            default : throw new RuntimeException("Participation array value unknown: " + number);
        }
    }
     */
    
    
    private List<String> formIndivTripColumnNames() {
        List<String> data = new LinkedList<String>();
        data.add("hh_id");
        data.add("person_id");
        data.add("person_num");
        data.add("tour_id");
        data.add("stop_id");
        data.add("inbound");
        data.add("tour_purpose");
        data.add("orig_purpose");
        data.add("dest_purpose");
        data.add("orig_taz");
        data.add("orig_walk_segment");
        data.add("dest_taz");
        data.add("dest_walk_segment");
        data.add("parking_taz");
        data.add("depart_hour");
        data.add("trip_mode");
        data.add("tour_mode");
        data.add("tour_category");
        data.add("avAvailable");
        data.add("sampleRate");
        data.add("taxiWait");
        data.add("singleTNCWait");
        data.add("sharedTNCWait");
        return data;
    }

    private List<String> formJointTripColumnNames() {
        List<String> data = new LinkedList<String>();
        data.add("hh_id");
        data.add("tour_id");
        data.add("stop_id");
        data.add("inbound");
        data.add("tour_purpose");
        data.add("orig_purpose");
        data.add("dest_purpose");
        data.add("orig_taz");
        data.add("orig_walk_segment");
        data.add("dest_taz");
        data.add("dest_walk_segment");
        data.add("parking_taz");
        data.add("depart_hour");
        data.add("trip_mode");
        data.add("num_participants");
        data.add("tour_mode");
        data.add("tour_category");
        data.add("avAvailable");
        data.add("sampleRate");
        data.add("taxiWait");
        data.add("singleTNCWait");
        data.add("sharedTNCWait");
        return data;
    }

    private String formTripTableColumnHeader() {
        return new StringBuilder()
            .append("hh_id").append(",")
            .append("person_id").append(",")
            .append("person_num").append(",")
            .append("tour_id").append(",")
            .append("stop_id").append(",")
            .append("inbound").append(",")
            .append("tour_category").append(",")
            .append("tour_purpose").append(",")
            .append("orig_purpose").append(",")
            .append("dest_purpose").append(",")
            .append("orig_taz").append(",")
            .append("dest_taz").append(",")
            .append("orig_walk_segment").append(",")
            .append("dest_walk_segment").append(",")
            .append("parking_taz").append(",")
            .append("depart_hour").append(",")
            .append("trip_mode").append(",")
            .append("tour_mode").append(",")
            .append("num_participants").append(",")
            .append("tour_participants").append(",")
            .append("tour_start_hour").append(",")
            .append("tour_id_uniq").append(",")
            .append("trip_id").append(",")
            .append("orig_purpose_start_hour").append(",")
            .append("home_taz").append(",")
            .append("hh_income").append(",")
            .append("hh_autos").append(",")
            .append("hh_fp_choice").append(",")
            .append("hh_inc_bin").append(",")
            .append("hh_size").append(",")
            .append("hh_wkrs").append(",")
            .append("hh_auto_suff").append(",")
            .append("age").append(",")
            .append("gender").append(",")
            .append("person_type").append(",")
            .append("activity_pattern").append(",")
            .append("tour_mode_name").append(",")
            .append("trip_mode_name").append(",")
            .append("travel_time").append(",")
        	.append("distance").append(",")
        	.append("sampleRate").append(",")
        	.append("taxiWait").append(",")
        	.append("singleTNCWait").append(",")
        	.append("sharedTNCWait").toString();

    }

    private String formTravelTimeTableColumnHeader() {
        return new StringBuilder()
            .append("orig_taz").append(",")
            .append("dest_taz").append(",")
            .append("time_of_day").append(",")
            .append("mode_name").append(",")
            .append("travel_time").append(",")
            .append("distance").toString();
    }

    private List<SqliteDataTypes> formIndivTripColumnTypes() {
        List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        return data;
    }

    private List<SqliteDataTypes> formJointTripColumnTypes() {
        List<SqliteDataTypes> data = new LinkedList<SqliteDataTypes>();
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.TEXT);
        data.add(SqliteDataTypes.INTEGER);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        data.add(SqliteDataTypes.REAL);
        return data;
    }

   private List<String> formIndivTripDataEntry(Stop s) {
       Tour t = s.getTour();
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getPersonObject().getPersonId()));
       data.add(string(t.getPersonObject().getPersonNum()));
       data.add(string(t.getTourId()));
       data.add(string(s.getStopId()));
       data.add(string(s.isInboundStop() ? 1 : 0));
       data.add(string(t.getTourPurpose()));
       
       if ( s.getStopId() == 0 ) {
           if ( s.isInboundStop() ) {
               // first trip on inbound half-tour with stops
               data.add( s.getOrigPurpose(modelStructure) );
               data.add( s.getDestPurpose(modelStructure) );
           }
           else {
               // first trip on outbound half-tour with stops
               if ( t.getTourCategoryIsAtWork() ) {
                   data.add("Work"); 
                   data.add( s.getDestPurpose(modelStructure) );
               }
               else {
                   data.add("Home"); 
                   data.add( s.getDestPurpose(modelStructure) );
               }
           }
       }
       else if ( s.isInboundStop() && s.getStopId() == t.getNumInboundStops() ) {
           // last trip on inbound half-tour with stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add("Work"); 
           }
           else {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add("Home"); 
           }
       }
       else if ( ! s.isInboundStop() && s.getStopId() == t.getNumOutboundStops() ) {
           // last trip on outbound half-tour with stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add(t.getTourPrimaryPurpose()); 
           }
           else {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add(t.getTourPrimaryPurpose());
           }
       }
       else {
           data.add( s.getOrigPurpose(modelStructure) );
           data.add( s.getDestPurpose(modelStructure) );
       }
       
       data.add(string(s.getOrig()));
       data.add(string(s.getOrigWalkSegment()));
       data.add(string(s.getDest()));
       data.add(string(s.getDestWalkSegment()));
       data.add(string(s.getParkTaz()));
       data.add(string(s.getDepartHour() ));
       data.add(string(s.getMode()));
       data.add(string(t.getTourModeChoice()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(s.getSampleRate()));
       data.add(string(s.getOrigTaxiWait()));
       data.add(string(s.getOrigSingleTNCWait()));
       data.add(string(s.getOrigSharedTNCWait()));
       
       return data;
   }


   private List<String> formJointTripDataEntry(Stop s) {
       Tour t = s.getTour();
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getTourId()));
       data.add(string(s.getStopId()));
       data.add(string(s.isInboundStop() ? 1 : 0));
       data.add(string(t.getTourPurpose()));

       if ( s.getStopId() == 0 ) {
           if ( s.isInboundStop() ) {
               // first trip on inbound half-tour with stops
               data.add( s.getOrigPurpose(modelStructure) );
               data.add( s.getDestPurpose(modelStructure) );
           }
           else {
               // first trip on outbound half-tour with stops
               if ( t.getTourCategoryIsAtWork() ) {
                   data.add("Work"); 
                   data.add( s.getDestPurpose(modelStructure) );
               }
               else {
                   data.add("Home"); 
                   data.add( s.getDestPurpose(modelStructure) );
               }
           }
       }
       else if ( s.isInboundStop() && s.getStopId() == t.getNumInboundStops() ) {
           // last trip on inbound half-tour with stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add("Work"); 
           }
           else {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add("Home"); 
           }
       }
       else if ( ! s.isInboundStop() && s.getStopId() == t.getNumOutboundStops() ) {
           // last trip on outbound half-tour with stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add(t.getTourPrimaryPurpose()); 
           }
           else {
               data.add( s.getOrigPurpose(modelStructure) );
               data.add(t.getTourPrimaryPurpose());
           }
       }
       else {
           data.add( s.getOrigPurpose(modelStructure) );
           data.add( s.getDestPurpose(modelStructure) );
       }

       data.add(string(s.getOrig()));
       data.add(string(s.getOrigWalkSegment()));
       data.add(string(s.getDest()));
       data.add(string(s.getDestWalkSegment()));
       data.add(string(s.getParkTaz()));
       data.add(string(s.getDepartHour() ));
       data.add(string(s.getMode()));
       
       byte[] participants = t.getPersonNumArray();
       if ( participants == null ) {
           logger.error ( "tour participants array is null, hhid=" + t.getHhId() + "." );
           throw new RuntimeException();
       }
       if ( participants.length  < 2 ) {
           logger.error ( "length of tour participants array is not null, but is < 2; should be >= 2 for joint tour, hhid=" + t.getHhId() + "." );
           throw new RuntimeException();
       }

       data.add(string(participants.length));
       data.add(string(t.getTourModeChoice()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(s.getSampleRate()));
       data.add(string(s.getOrigTaxiWait()));
       data.add(string(s.getOrigSingleTNCWait()));
       data.add(string(s.getOrigSharedTNCWait()));

      
       return data;
   }


   private List<String> formTourAsIndivTripDataEntry(Tour t, boolean inbound) {
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getPersonObject().getPersonId()));
       data.add(string(t.getPersonObject().getPersonNum()));
       data.add(string(t.getTourId()));
       data.add(string( -1 ));
       data.add(string((inbound ? 1 : 0)));
       data.add(string(t.getTourPurpose()));

       if ( inbound ) {
           // inbound trip on half-tour with no stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add(t.getTourPrimaryPurpose());
               data.add("Work");
           }
           else {
               data.add(t.getTourPrimaryPurpose());
               data.add("Home"); 
           }
       }
       else {
           // outbound trip on half-tour with no stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add("Work");
               data.add(t.getTourPrimaryPurpose());
           }
           else {
               data.add("Home");
               data.add(t.getTourPrimaryPurpose());
           }
       }

       data.add(string((inbound ? t.getTourDestTaz() : t.getTourOrigTaz())));
       data.add(string((inbound ? t.getTourDestWalkSubzone() : t.getTourOrigWalkSubzone())));
       data.add(string((inbound ? t.getTourOrigTaz() : t.getTourDestTaz())));
       data.add(string((inbound ? t.getTourOrigWalkSubzone() : t.getTourDestWalkSubzone())));
       data.add(string(t.getTourParkTaz()));
       data.add(string(inbound ? t.getTourEndHour() : t.getTourStartHour() ));
       data.add(string(t.getTourModeChoice()));
       data.add(string(t.getTourModeChoice()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(t.getSampleRate()));
       data.add(string((inbound ? t.getDestTaxiWait() : t.getOrigTaxiWait())));
       data.add(string((inbound ? t.getDestTNCSingleWait() : t.getOrigTNCSingleWait())));
       data.add(string((inbound ? t.getDestTNCSharedWait() : t.getOrigTNCSharedWait())));
       
       
       return data;
   }

   private List<String> formTourAsJointTripDataEntry(Tour t, boolean inbound) {
       List<String> data = new LinkedList<String>();
       data.add(string(t.getHhId()));
       data.add(string(t.getTourId()));
       data.add(string( -1 ));
       data.add(string((inbound ? 1 : 0)));
       data.add(string(t.getTourPurpose()));

       if ( inbound ) {
           // inbound trip on half-tour with no stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add(t.getTourPrimaryPurpose());
               data.add("Work");
           }
           else {
               data.add(t.getTourPrimaryPurpose());
               data.add("Home"); 
           }
       }
       else {
           // outbound trip on half-tour with no stops
           if ( t.getTourCategoryIsAtWork() ) {
               data.add("Work");
               data.add(t.getTourPrimaryPurpose());
           }
           else {
               data.add("Home");
               data.add(t.getTourPrimaryPurpose());
           }
       }

       data.add(string((inbound ? t.getTourDestTaz() : t.getTourOrigTaz())));
       data.add(string((inbound ? t.getTourDestWalkSubzone() : t.getTourOrigWalkSubzone())));
       data.add(string((inbound ? t.getTourOrigTaz() : t.getTourDestTaz())));
       data.add(string((inbound ? t.getTourOrigWalkSubzone() : t.getTourDestWalkSubzone())));
       data.add(string(t.getTourParkTaz()));
       data.add(string(inbound ? t.getTourEndHour() : t.getTourStartHour() ));
       data.add(string(t.getTourModeChoice()));
       
       byte[] participants = t.getPersonNumArray();
       if ( participants == null ) {
           logger.error ( "tour participants array is null, hhid=" + t.getHhId() + "." );
           throw new RuntimeException();
       }
       if ( participants.length  < 2 ) {
           logger.error ( "length of tour participants array is not null, but is < 2; should be >= 2 for joint tour, hhid=" + t.getHhId() + "." );
           throw new RuntimeException();
       }

       data.add(string(participants.length));
       data.add(string(t.getTourModeChoice()));
       data.add(string(ModelStructure.TOUR_CATEGORY_LABELS[t.getTourCategoryIndex()]));
       data.add(string( t.getUseOwnedAV() ? 1 : 0) );
       data.add(string(t.getSampleRate()));
       data.add(string((inbound ? t.getDestTaxiWait() : t.getOrigTaxiWait())));
       data.add(string((inbound ? t.getDestTNCSingleWait() : t.getOrigTNCSingleWait())));
       data.add(string((inbound ? t.getDestTNCSharedWait() : t.getOrigTNCSharedWait())));

       return data;
   }


    private static enum SqliteDataTypes {
        INTEGER,
        TEXT,
        REAL
    }

    private interface DataWriter {
        void writeHouseholdData(List<String> data);
        void writePersonData(List<String> data);
        void writeIndivTourData(List<String> data);
        void writeJointTourData(List<String> data);
        void writeIndivTripData(List<String> data);
        void writeJointTripData(List<String> data);
        void writeTripData(List<String> entries);
        void writeTravelTimeData(int[] zoneList);
        void finishActions();
        Boolean getWriteTripFileFlag();
        Boolean getWriteTravelTimesFileFlag();
    }

    private class DatabaseDataWriter implements DataWriter {
        private final String householdTable = resourceBundle.getString(PROPERTIES_HOUSEHOLD_TABLE);
        private final String personTable = resourceBundle.getString(PROPERTIES_PERSON_TABLE);
        private final String indivTourTable = resourceBundle.getString(PROPERTIES_INDIV_TOUR_TABLE);
        private final String jointTourTable = resourceBundle.getString(PROPERTIES_JOINT_TOUR_TABLE);
        private final String indivTripTable = resourceBundle.getString(PROPERTIES_INDIV_TRIP_TABLE);
        private final String jointTripTable = resourceBundle.getString(PROPERTIES_JOINT_TRIP_TABLE);
        private Connection connection = null;
		private PreparedStatement hhPreparedStatement = null;
        private PreparedStatement personPreparedStatement = null;
        private PreparedStatement indivTourPreparedStatement = null;
        private PreparedStatement jointTourPreparedStatement = null;
        private PreparedStatement indivTripPreparedStatement = null;
        private PreparedStatement jointTripPreparedStatement = null;
        
        private Boolean writeTripFileFlag = false;
        private Boolean writeTravelTimesFileFlag = false;

        public DatabaseDataWriter( String dbFileName ) {
            initializeTables(dbFileName);
        }

        private void initializeTables( String dbFileName ) {
            Statement s = null;
            try {
                connection = ConnectionHelper.getConnection(dbFileName);
                s = connection.createStatement();
                s.addBatch(getTableInitializationString(householdTable,formHouseholdColumnNames(),formHouseholdColumnTypes()));
                s.addBatch(getTableInitializationString(personTable,formPersonColumnNames(),formPersonColumnTypes()));
                s.addBatch(getTableInitializationString(indivTourTable,formIndivTourColumnNames(),formIndivTourColumnTypes()));
                s.addBatch(getTableInitializationString(jointTourTable,formJointTourColumnNames(),formJointTourColumnTypes()));
                s.addBatch(getTableInitializationString(indivTripTable,formIndivTripColumnNames(),formIndivTripColumnTypes()));
                s.addBatch(getTableInitializationString(jointTripTable,formJointTripColumnNames(),formJointTripColumnTypes()));
                s.addBatch(getClearTableString(householdTable));
                s.addBatch(getClearTableString(personTable));
                s.addBatch(getClearTableString(indivTourTable));
                s.addBatch(getClearTableString(jointTourTable));
                s.addBatch(getClearTableString(indivTripTable));
                s.addBatch(getClearTableString(jointTripTable));
                s.executeBatch();
            } catch (SQLException e) {
                    try {
                        if (connection != null)
                            connection.close();
                    } catch (SQLException ee) {
                        //swallow
                    }
                    throw new RuntimeException(e);
            } finally {
                closeStatement(s);
            }
            setupPreparedStatements();
        }

        private void setupPreparedStatements() {
            String psStart = "INSERT INTO ";
            String psMiddle = " VALUES (?";
            StringBuilder hhp = new StringBuilder(psStart);
            hhp.append(householdTable).append(psMiddle);
            for (int i = 1; i < formHouseholdColumnNames().size(); i++)
                hhp.append(",?");
            hhp.append(");");
            StringBuilder pp = new StringBuilder(psStart);
            pp.append(personTable).append(psMiddle);
            for (int i = 1; i < formPersonColumnNames().size(); i++)
                pp.append(",?");
            pp.append(");");
            StringBuilder itp = new StringBuilder(psStart);
            itp.append(indivTourTable).append(psMiddle);
            for (int i = 1; i < formIndivTourColumnNames().size(); i++)
                itp.append(",?");
            itp.append(");");
            StringBuilder jtp = new StringBuilder(psStart);
            jtp.append(jointTourTable).append(psMiddle);
            for (int i = 1; i < formJointTourColumnNames().size(); i++)
                jtp.append(",?");
            jtp.append(");");
            StringBuilder itp2 = new StringBuilder(psStart);
            itp2.append(indivTripTable).append(psMiddle);
            for (int i = 1; i < formIndivTripColumnNames().size(); i++)
                itp2.append(",?");
            itp2.append(");");
            StringBuilder jtp2 = new StringBuilder(psStart);
            jtp2.append(jointTripTable).append(psMiddle);
            for (int i = 1; i < formJointTripColumnNames().size(); i++)
                jtp2.append(",?");
            jtp2.append(");");
            try {
                hhPreparedStatement = connection.prepareStatement(hhp.toString());
                personPreparedStatement = connection.prepareStatement(pp.toString());
                indivTourPreparedStatement = connection.prepareStatement(itp.toString());
                jointTourPreparedStatement = connection.prepareStatement(jtp.toString());
                indivTripPreparedStatement = connection.prepareStatement(itp2.toString());
                jointTripPreparedStatement = connection.prepareStatement(jtp2.toString());
                connection.setAutoCommit(false);
            } catch (SQLException e) {
                throw new RuntimeException(e);
            }
        }

        private String getTableInitializationString(String table, List<String> columns, List<SqliteDataTypes> types) {
            StringBuilder sb = new StringBuilder("CREATE TABLE IF NOT EXISTS ");
            sb.append(table).append(" (");
            Iterator<String> cols = columns.iterator();
            Iterator<SqliteDataTypes> tps = types.iterator();
            sb.append(cols.next()).append(" ").append(tps.next().name());
            while (cols.hasNext())
                sb.append(",").append(cols.next()).append(" ").append(tps.next().name());
            sb.append(");");
            return sb.toString();
        }

        private String getClearTableString(String table) {
            return "DELETE FROM " + table + ";";
        }

        private void writeToTable(PreparedStatement ps, List<String> values) {
            try {
                int counter = 1;
                for (String value : values)
                    ps.setString(counter++,value);
                ps.executeUpdate();
            } catch (SQLException e) {
                throw new RuntimeException(e);
            }
        }
//        private void writeToTable(String table, List<String> values) {
//            StringBuilder sb = new StringBuilder("INSERT INTO");
//            sb.append(" ").append(table).append(" VALUES(");
//            Iterator<String> vls = values.iterator();
//            sb.append(vls.next());
//            while (vls.hasNext())
//                sb.append(",").append(vls.next());
//            sb.append(");");
//            try {
//                s.addBatch(sb.toString());
//            } catch (SQLException e) {
//                try {
//                    throw new RuntimeException(e);
//                } finally {
//                    try {
//                        if (s != null)
//                            s.close();
//                    } catch (SQLException ee) {
//                        //swallow
//                    }
//                    try {
//                        if (connection != null)
//                            connection.close();
//                    } catch (SQLException ee) {
//                        //swallow
//                    }
//                }
//            }
//        }

        public void writeHouseholdData(List<String> data) {
            writeToTable(hhPreparedStatement,data);
        }

        public void writePersonData(List<String> data) {
            writeToTable(personPreparedStatement,data);
        }

        public void writeIndivTourData(List<String> data) {
            writeToTable(indivTourPreparedStatement,data);
        }

        public void writeJointTourData(List<String> data) {
            writeToTable(jointTourPreparedStatement,data);
        }

        public void writeIndivTripData(List<String> data) {
            writeToTable(indivTripPreparedStatement,data);
        }

        public void writeJointTripData(List<String> data) {
            writeToTable(jointTripPreparedStatement,data);
        }

        public void writeTripData(List<String> entries) {
            throw new UnsupportedOperationException("Database writer does not support writing trip table.");
        }

        public void writeTravelTimeData(int[] zoneList) {
            throw new UnsupportedOperationException("Database writer does not support writing travel time table");
        }

        public void finishActions() {

            try {
                connection.commit();
            } catch (SQLException e) {
                throw new RuntimeException(e);
            } finally {
                closeStatement(hhPreparedStatement);
                closeStatement(personPreparedStatement);
                closeStatement(indivTourPreparedStatement);
                closeStatement(jointTourPreparedStatement);
                closeStatement(indivTripPreparedStatement);
                closeStatement(jointTripPreparedStatement);
                try {
                    if (connection != null)
                        connection.close();
                } catch (SQLException ee) {
                    //swallow
                }
            }
        }

        private void closeStatement(Statement s) {
            try {
                if (s != null)
                    s.close();
            } catch (SQLException e) {
                //swallow
            }
        }
        
        public Boolean getWriteTripFileFlag() {
        	return(writeTripFileFlag);
        }
        
        public Boolean getWriteTravelTimesFileFlag() {
        	return(writeTravelTimesFileFlag);
        }
    }

    private void loadTourModes(ResourceBundle properties, CtrampDmuFactoryIf dmuFactory) {
        tourModeAltLabels = new HashMap<String,Map<Integer,String>>();
        String mcUecFile = properties.getString(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY) +
                           properties.getString(com.pb.models.ctramp.jppf.ModeChoiceModel.PROPERTIES_UEC_TOUR_MODE_CHOICE);

        String[] categories = {ModelStructure.MANDATORY_CATEGORY,ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY,
                               ModelStructure.JOINT_NON_MANDATORY_CATEGORY,ModelStructure.AT_WORK_CATEGORY};
        VariableTable vt = dmuFactory.getModeChoiceDMU();
        @SuppressWarnings("unchecked") //this will return a HashMap<String,String> - signature of method is missing generic declaration
        HashMap<String,String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle);

        for (String tourCategory : categories) {
            // create a HashMap to map purposeName to model index
            Map<String,Integer> purposeModelIndexMap = new HashMap<String,Integer>();

            // keep a set of unique model sheet numbers so that we can create ChoiceModelApplication objects once for each model sheet used
            TreeSet<Integer> modelIndexSet = new TreeSet<Integer>();

            for ( String purposeName : modelStructure.getDcModelPurposeList( tourCategory ) ) {
                int uecIndex = modelStructure.getTourModeChoiceUecIndexForPurpose(purposeName);
                purposeModelIndexMap.put(purposeName,uecIndex);
                modelIndexSet.add( uecIndex );
            }

            for (int m : modelIndexSet) {
                String[] altNames = new ChoiceModelApplication(mcUecFile, m,com.pb.models.ctramp.jppf.ModeChoiceModel.MC_DATA_SHEET,propertyMap,vt).getAlternativeNames();
                //save mode names by purpose
                Map<Integer,String> modeNameMap = new HashMap<Integer,String>();
                for (int i = 0; i < altNames.length; i++)
                    modeNameMap.put(i+1,altNames[i]); //mode indices are indexed by 1
                for (String p : purposeModelIndexMap.keySet()) {//more than one purpose may use same index map
                    if (purposeModelIndexMap.get(p) == m) {
                        if (!tourModeAltLabels.containsKey(p))
                            tourModeAltLabels.put(p,new HashMap<Integer,String>());
                        tourModeAltLabels.get(p).putAll(modeNameMap);
                    }
                }
            }
        }
    }

    private void loadTripModes(ResourceBundle properties, CtrampDmuFactoryIf dmuFactory) {
        tripModeAltLabels = new HashMap<Integer,Map<Integer,String>>();
        String uecFileName = properties.getString(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY) +
                             properties.getString(StopLocationModeChoiceModel.PROPERTIES_UEC_TRIP_MODE_CHOICE);

        VariableTable vt = dmuFactory.getTripModeChoiceDMU();
        @SuppressWarnings("unchecked") //this will return a HashMap<String,String> - signature of method is missing generic declaration
        HashMap<String,String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle);

        for (int i : modelStructure.getTripModeChoiceModelSheetIndices()) {
            //get mode names
            Map<Integer,String> modeNameMap = new HashMap<Integer,String>();
            int counter = 1; //trip modes are indexed by 1
            for (String name : new ChoiceModelApplication(uecFileName,i,StopLocationModeChoiceModel.UEC_DATA_PAGE,propertyMap,vt).getAlternativeNames())
                modeNameMap.put(counter++,name);
            if (!tripModeAltLabels.containsKey(i))
                tripModeAltLabels.put(i,new HashMap<Integer,String>());
            tripModeAltLabels.get(i).putAll(modeNameMap);
        }
    }

    private class FileDataWriter implements DataWriter{
    	
        private final PrintWriter hhWriter;
        private final PrintWriter personWriter;
        private final PrintWriter indivTourWriter;
        private final PrintWriter jointTourWriter;
        private final PrintWriter indivTripWriter;
        private final PrintWriter jointTripWriter;
        private PrintWriter tripWriter;
        private PrintWriter travelTimeWriter;
        
        private Boolean writeTripFileFlag = false;
        private Boolean writeTravelTimesFileFlag = false;

        public FileDataWriter() {
            String baseDir = ResourceUtil.getProperty(resourceBundle,CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);

            String hhFile = formFileName( resourceBundle.getString(PROPERTIES_HOUSEHOLD_DATA_FILE), iteration );
            String personFile = formFileName( resourceBundle.getString(PROPERTIES_PERSON_DATA_FILE), iteration );
            String indivTourFile = formFileName( resourceBundle.getString(PROPERTIES_INDIV_TOUR_DATA_FILE), iteration );
            String jointTourFile = formFileName( resourceBundle.getString(PROPERTIES_JOINT_TOUR_DATA_FILE), iteration );
            String indivTripFile = formFileName( resourceBundle.getString(PROPERTIES_INDIV_TRIP_DATA_FILE), iteration );
            String jointTripFile = formFileName( resourceBundle.getString(PROPERTIES_JOINT_TRIP_DATA_FILE), iteration );

            //write trip file and travel times file
            String tripFile = "";
            String travelTimeFile = "";
            if ( resourceBundle.containsKey(PROPERTIES_TRIP_DATA_FILE) ) {
            	tripFile = formFileName(resourceBundle.getString(PROPERTIES_TRIP_DATA_FILE), iteration );
            	writeTripFileFlag = true; 
            }
            if ( resourceBundle.containsKey(PROPERTIES_TRAVEL_TIME_DATA_FILE) ) { 
            	travelTimeFile = formFileName(resourceBundle.getString(PROPERTIES_TRAVEL_TIME_DATA_FILE), iteration );
            	writeTravelTimesFileFlag = true; 
            }
            
            try {
                hhWriter = new PrintWriter(new File(baseDir + hhFile));
                personWriter = new PrintWriter(new File(baseDir + personFile));
                indivTourWriter = new PrintWriter(new File(baseDir + indivTourFile));
                jointTourWriter = new PrintWriter(new File(baseDir + jointTourFile));
                indivTripWriter = new PrintWriter(new File(baseDir + indivTripFile));
                jointTripWriter = new PrintWriter(new File(baseDir + jointTripFile));
                if(writeTripFileFlag) {
                	tripWriter = new PrintWriter(new File(baseDir + tripFile));
                }
                if(writeTravelTimesFileFlag) {
                	travelTimeWriter = new PrintWriter(new File(baseDir + travelTimeFile));
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }

            writeHouseholdData(formHouseholdColumnNames());
            writePersonData(formPersonColumnNames());
            writeIndivTourData(formIndivTourColumnNames());
            writeJointTourData(formJointTourColumnNames());
            writeIndivTripData(formIndivTripColumnNames());
            writeJointTripData(formJointTripColumnNames());
            if(writeTripFileFlag) {
            	tripWriter.println(formTripTableColumnHeader());
            }
            if(writeTravelTimesFileFlag) {
            	travelTimeWriter.println(formTravelTimeTableColumnHeader());
            }
            
        }

        private String formFileName( String originalFileName, int iteration ) {
            int lastDot = originalFileName.lastIndexOf('.');
            
            String returnString = "";
            if ( lastDot > 0 ) {
                String base = originalFileName.substring( 0, lastDot );
                String ext = originalFileName.substring( lastDot );
                returnString = String.format( "%s_%d%s", base, iteration, ext );
            }
            else {
                returnString = String.format( "%s_%d.csv", originalFileName, iteration );
            }
            
            logger.info( "writing household csv file to " + returnString );
            
            return returnString;
        }
        
        public void writeHouseholdData(List<String> data) {
            writeEntryToCsv(hhWriter,data);
        }

        public void writePersonData(List<String> data) {
            writeEntryToCsv(personWriter,data);
        }

        public void writeIndivTourData(List<String> data) {
            writeEntryToCsv(indivTourWriter,data);
        }

        public void writeJointTourData(List<String> data) {
            writeEntryToCsv(jointTourWriter,data);
        }

        public void writeIndivTripData(List<String> data) {
            writeEntryToCsv(indivTripWriter,data);
        }

        public void writeJointTripData(List<String> data) {
            writeEntryToCsv(jointTripWriter,data);
        }

        public void writeTripData(List<String> entries) {
            for (String entry : entries)
                tripWriter.println(entry);
        }

        public void writeTravelTimeData(int[] zoneList) {
            for (int origin : zoneList)
                for (int dest : zoneList)
                    for (String line : getTravelTimeTableEntries(origin,dest))
                        travelTimeWriter.println(line);
        }

        private void writeEntryToCsv(PrintWriter pw, List<String> data) {
            pw.println(formCsvString(data));
        }

       private String formCsvString(List<String> data) {
            char delimiter = ',';
            Iterator<String> it = data.iterator();
            StringBuilder sb = new StringBuilder(it.next());
            while (it.hasNext())
                sb.append(delimiter).append(it.next());
            return sb.toString();
        }

        public void finishActions() {
            try {
                hhWriter.flush();
                personWriter.flush();
                indivTourWriter.flush();
                jointTourWriter.flush();
                indivTripWriter.flush();
                jointTripWriter.flush();
                if(writeTripFileFlag) {
                	tripWriter.flush();
                }
                if(writeTravelTimesFileFlag) {
                	travelTimeWriter.flush();
                }
            } finally {
                hhWriter.close();
                personWriter.close();
                indivTourWriter.close();
                jointTourWriter.close();
                indivTripWriter.close();
                jointTripWriter.close();
                if(writeTripFileFlag) {
                	tripWriter.close();
                }
                if(writeTravelTimesFileFlag) {
                	travelTimeWriter.close();	
                }
            }
        }
        
        public Boolean getWriteTripFileFlag() {
        	return(writeTripFileFlag);
        }
        
        public Boolean getWriteTravelTimesFileFlag() {
        	return(writeTravelTimesFileFlag);
        }
    }

    private List<String> getTravelTimeTableEntries(int origin, int dest) {
        String travelTimeFormat = resourceBundle.getString(PROPERTIES_TRAVEL_TIME_FORMAT);
        List<String> entries = new LinkedList<String>();
        for (String period : travelTimeModel.getTimePeriods()) {
            String[] alts = travelTimeModel.getTimeAlternatives(period);
            double[] times = travelTimeModel.getTravelTimes(period,origin,dest); 
            double[] distances = travelTimeModel.getTravelDistances(period,origin,dest); 
            for (int i = 0; i < alts.length; i++) {
                entries.add(new StringBuilder()
                    .append(origin).append(",")
                    .append(dest).append(",")
                    .append(period).append(",")
                    .append(alts[i]).append(",")
                    .append(String.format(travelTimeFormat,times[i])).append(",")
                    .append(distances[i]).toString());
            }
        }
        return entries;
    }

    private List<String> createVizTripRecords(Household hh) {
        Person[] persons = hh.getPersons();
        List<Map<Integer,List<StringBuilder[]>>> personRecords = new ArrayList<Map<Integer,List<StringBuilder[]>>>();
        for (Person p : hh.getPersons()) {
            if (p == null) { //deal with 1-based arrays
                personRecords.add(null);
                continue;
            }
            Map<Integer,List<StringBuilder[]>> recordMap = new TreeMap<Integer,List<StringBuilder[]>>();  //orders by departure time
            personRecords.add(recordMap);
            for (Tour t : p.getListOfWorkTours())
                addTripsFromTour(p,t,recordMap);
            for (Tour t : p.getListOfIndividualNonMandatoryTours())
                addTripsFromTour(p,t,recordMap);
            for (Tour t : p.getListOfSchoolTours())
                addTripsFromTour(p,t,recordMap);
            for (Tour t : p.getListOfAtWorkSubtours())
                addTripsFromTour(p,t,recordMap);
        }

        Tour[] jointTours = hh.getJointTourArray();
        if (jointTours != null)
            for (Tour t : jointTours)
                for (byte p : t.getPersonNumArray())
                    addTripsFromTour(persons[p],t,personRecords.get(p));

        List<String> tours = new LinkedList<String>();
        for (Map<Integer,List<StringBuilder[]>> personRecord : personRecords) {
            if (personRecord == null)
                continue;
            int startTime = 5; //todo: don't hard code this
            int tripId = 1;
            for (Integer departTime : personRecord.keySet()) {
                for (StringBuilder[] sb : personRecord.get(departTime)) {
                    tours.add(sb[0].append(tripId++).append(",").append(startTime).append(sb[2]).toString()); //tripId is across persons, not just within tours
                    startTime = departTime; //last activity ended at same time (except first, which is taken care of)
                }
            }
        }
        return tours;
    }

    private void addTripsFromTour(Person p, Tour t, Map<Integer,List<StringBuilder[]>> tourList) {
        Stop[] stops = t.getOutboundStops();
        if (stops != null) {
            for (Stop s : stops) {
                int h = s.getDepartHour();
                if (!tourList.containsKey(h))
                    tourList.put(h,new LinkedList<StringBuilder[]>());
                tourList.get(h).add(getVizTripString(p,s));
            }
        } else {
            int h = t.getTourStartHour();
            if (!tourList.containsKey(h))
                tourList.put(h,new LinkedList<StringBuilder[]>());
            tourList.get(h).add(getVizTripString(p,t,false));
        }
        stops = t.getInboundStops();
        if (stops != null) {
            for (Stop s : stops) {
                int h = s.getDepartHour();
                if (!tourList.containsKey(h))
                    tourList.put(h,new LinkedList<StringBuilder[]>());
                tourList.get(h).add(getVizTripString(p,s));
            }
        } else {
            int h = t.getTourEndHour();
            if (!tourList.containsKey(h))
                tourList.put(h,new LinkedList<StringBuilder[]>());
            tourList.get(h).add(getVizTripString(p,t,false));
        }
    }

    private StringBuilder[] getVizTripString(Person p, Tour t, boolean returnTrip) {
        Household hh = p.getHouseholdObject();
        byte[] persons = t.getPersonNumArray();
        StringBuilder personsSb = new StringBuilder();
        if (persons == null) {
            personsSb.append(p.getPersonNum());
        } else {
            personsSb.append(persons[0]);
            for (int i = 1; i < persons.length; i++)
                personsSb.append(" ").append(persons[i]);
        }
        String suff = "nocars";
        if(hh.getAutoOwnershipModelResult() > 0) {
        	int diff = hh.getAutoOwnershipModelResult() - hh.getWorkers();
        	suff = diff < 0 ? "cars<wkrs" : "cars>=wkrs";
        }
        String tourCategory;
        if (t.getTourCategoryIsMandatory())
            tourCategory = ModelStructure.MANDATORY_CATEGORY;
        else if (t.getTourCategoryIsIndivNonMandatory())
            tourCategory = ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY;
        else if (t.getTourCategoryIsJointNonMandatory())
            tourCategory = ModelStructure.JOINT_NON_MANDATORY_CATEGORY;
        else
            tourCategory = ModelStructure.AT_WORK_CATEGORY;
        String tripMode = tourModeAltLabels.get(t.getTourPurpose().toLowerCase()).get(t.getTourModeChoice());
        int departHour = returnTrip ? t.getTourEndHour() : t.getTourStartHour();
        int origin = returnTrip ? t.getTourDestTaz() : t.getTourOrigTaz();
        int dest = returnTrip ? t.getTourOrigTaz() : t.getTourDestTaz();

        StringBuilder[] record = new StringBuilder[3];
        record[0] = new StringBuilder()
                .append(hh.getHhId()).append(",")
                .append(p.getPersonId()).append(",")
                .append(p.getPersonNum()).append(",")
                .append(t.getTourId()).append(",")
                .append(-1).append(",")
                .append(returnTrip ? 0 : 1).append(",")
                .append(tourCategory).append(",")
                .append(t.getTourPurpose()).append(",")
                .append(returnTrip ? t.getTourPurpose() : t.getTourCategoryIsAtWork() ? "work" : "home").append(",")
                .append(returnTrip ? (t.getTourCategoryIsAtWork() ? "work" : "home") : t.getTourPurpose()).append(",")
                .append(origin).append(",")
                .append(dest).append(",")
                .append(returnTrip ? t.getTourDestWalkSubzone() : t.getTourOrigWalkSubzone()).append(",")
                .append(returnTrip ? t.getTourOrigWalkSubzone() : t.getTourDestWalkSubzone()).append(",")
                .append(returnTrip ? 0 : t.getTourParkTaz()).append(",")
                .append(departHour).append(",")
                .append(t.getTourModeChoice()).append(",")
                .append(t.getTourModeChoice()).append(",")
                .append(persons == null ? 1 : persons.length).append(",")
                .append(personsSb).append(",")
                .append(t.getTourStartHour()).append(",")
                .append(tourCategory).append("_").append(t.getTourId()).append("_").append(t.getTourPurpose()).append(","); //unique id
        record[2] = new StringBuilder()
                .append(",")
                .append(hh.getHhTaz()).append(",")
                .append(hh.getIncomeInDollars()).append(",")
                .append(hh.getAutoOwnershipModelResult()).append(",")
                .append(p.getFreeParkingAvailableResult()).append(",")
                .append(hh.getIncomeSegment()).append(",")
                .append(hh.getHhSize()).append(",")
                .append(hh.getWorkers()).append(",")
                .append(suff).append(",")
                .append(p.getAge()).append(",")
                .append(p.getGender() == 2 ? "Female" : "Male").append(",")
                .append(p.getPersonType()).append(",")
                .append(p.getCdapActivity()).append(",")
                .append(tourModeAltLabels.get(t.getTourPurpose().toLowerCase()).get(t.getTourModeChoice())).append(",") //trip mode name
                .append(tripMode).append(",") //tour mode name
                .append(tripMode == null ? -1 : travelTimeModel.getTravelTime(tripMode,departHour,origin,dest)).append(",")
        		.append(tripMode == null ? -1 : travelTimeModel.getTravelDistance(tripMode,departHour,origin,dest));
        if (tripMode == null)
            logger.info("Null trip mode: " + t.getTourPrimaryPurpose().toLowerCase()+ " " + t.getTourModeChoice());
        return record;
    }

    private StringBuilder[] getVizTripString(Person p, Stop s) {
        Household hh = p.getHouseholdObject();
        Tour t = s.getTour();
        byte[] persons = t.getPersonNumArray();
        StringBuilder personsSb = new StringBuilder();
        if (persons == null) {
            personsSb.append(p.getPersonNum());
        } else {
            personsSb.append(persons[0]);
            for (int i = 1; i < persons.length; i++)
                personsSb.append(" ").append(persons[i]);
        }
        String suff = "nocars";
        if(hh.getAutoOwnershipModelResult() > 0) {
        	int diff = hh.getAutoOwnershipModelResult() - hh.getWorkers();
        	suff = diff < 0 ? "cars<wkrs" : "cars>=wkrs";
        }
        String tourCategory;
        if (t.getTourCategoryIsMandatory())
            tourCategory = ModelStructure.MANDATORY_CATEGORY;
        else if (t.getTourCategoryIsIndivNonMandatory())
            tourCategory = ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY;
        else if (t.getTourCategoryIsJointNonMandatory())
            tourCategory = ModelStructure.JOINT_NON_MANDATORY_CATEGORY;
        else
            tourCategory = ModelStructure.AT_WORK_CATEGORY;
        String tripMode = tripModeAltLabels.get(modelStructure.getTripModeChoiceModelIndex(t.getTourPrimaryPurpose().toLowerCase())).get(s.getMode());

        StringBuilder[] record = new StringBuilder[3];
        record[0] = new StringBuilder()
                .append(hh.getHhId()).append(",")
                .append(p.getPersonId()).append(",")
                .append(p.getPersonNum()).append(",")
                .append(t.getTourId()).append(",")
                .append(s.getStopId()).append(",")
                .append(s.isInboundStop() ? 1 : 0).append(",")
                .append(tourCategory).append(",")
                .append(t.getTourPurpose()).append(",")
                .append(s.getOrigPurpose(modelStructure)).append(",")
                .append(s.getDestPurpose(modelStructure)).append(",")
                .append(s.getOrig()).append(",")
                .append(s.getDest()).append(",")
                .append(s.getOrigWalkSegment()).append(",")
                .append(s.getDestWalkSegment()).append(",")
                .append(s.getParkTaz()).append(",")
                .append(s.getDepartHour()).append(",")
                .append(s.getMode()).append(",")
                .append(t.getTourModeChoice()).append(",")
                .append(persons == null ? 1 : persons.length).append(",")
                .append(personsSb).append(",")
                .append(t.getTourStartHour()).append(",")
                .append(tourCategory).append("_").append(t.getTourId()).append("_").append(t.getTourPurpose()).append(","); //unique id
        record[2] = new StringBuilder()
                .append(",")
                .append(hh.getHhTaz()).append(",")
                .append(hh.getIncomeInDollars()).append(",")
                .append(hh.getAutoOwnershipModelResult()).append(",")
                .append(p.getFreeParkingAvailableResult()).append(",")
                .append(hh.getIncomeSegment()).append(",")
                .append(hh.getHhSize()).append(",")
                .append(hh.getWorkers()).append(",")
                .append(suff).append(",")
                .append(p.getAge()).append(",")
                .append(p.getGender() == 2 ? "Female" : "Male").append(",")
                .append(p.getPersonType()).append(",")
                .append(p.getCdapActivity()).append(",")
                .append(tourModeAltLabels.get(t.getTourPurpose().toLowerCase()).get(t.getTourModeChoice())).append(",") //trip mode name
                .append(tripMode).append(",") //tour mode name
                .append(tripMode == null ? -1 : travelTimeModel.getTravelTime(tripMode,s.getDepartHour(),s.getOrig(),s.getDest())).append(",")
        		.append(tripMode == null ? -1 : travelTimeModel.getTravelDistance(tripMode,s.getDepartHour(),s.getOrig(),s.getDest()));
        if (tripMode == null)
            logger.info("Null trip mode: " + t.getTourPrimaryPurpose().toLowerCase()+ " " + s.getMode());
        return record;
    }
    
    
    private ArrayList<int[]> getWriteHouseholdRanges( int numberOfHouseholds ) {
        
        ArrayList<int[]> startEndIndexList = new ArrayList<int[]>(); 

        int startIndex = 0;
        int endIndex = 0;
        
        while ( endIndex < numberOfHouseholds - 1 ) {
            endIndex = startIndex + NUM_WRITE_PACKETS - 1;
            if ( endIndex + NUM_WRITE_PACKETS > numberOfHouseholds )
                endIndex = numberOfHouseholds - 1;
        
            int[] startEndIndices = new int[2];
            startEndIndices[0] = startIndex; 
            startEndIndices[1] = endIndex;
            startEndIndexList.add( startEndIndices );
            
            startIndex += NUM_WRITE_PACKETS;
        }

        
        return startEndIndexList;
        
    }


}
