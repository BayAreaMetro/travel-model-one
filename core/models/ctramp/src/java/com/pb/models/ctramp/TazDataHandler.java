package com.pb.models.ctramp;

import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.util.Arrays;
import java.util.HashMap;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.ResourceUtil;


/**
 * This class provides methods defined in the TazDataIf interface for accessing zonal data stored in
 * its TazDataManager object.
 *
 * A CT-RAMP tour based model application could create an instance of a subclass of this class, where additional
 * project specific varaible definitions and methods are defined and pass that instance to its model
 * component objects.
 *
 * Alternatively, an application could use TazDataHandlerRmi as the base class instead and create a "remoteable" subclass.
 * The TazDataHandlerRmi class implements the same interface, so the model component classes can be unaware of whether the
 * taz data handler object accesses zonal data from its member object or remotely from a server.  Those methods in the
 * rmi class access zonal data from a TazDataManager object contained in a "taz data server" object which must exist in
 * a separate JVM on the same machine or on another addressable machine over the network.
 *
 * The flexibility provided by this design is intended to allow the "local" instance to be declared and passed within a single JVM
 * to model components for possibly greater performance (yet to be tested and proven) at production run time.
 * The "rmi" instance however allows the model components to access zonal data from a "long-running process" (the server
 * class may execute for weeks or months).  This approach aids in model development as during development, model
 * applications can be written to skip startup procedures for reading zonal data, and access them directly from the
 * server that is already running.
 *
 * A similar approach is planned for managing objects such as Household objects and ModelResults objects so that model
 * components, for example individual non-mandatory tour related models which occur well into the tour based model stream,
 * can be run in a "hot-start" fasion, where the model component of interest is executed immediately where all the
 * preliminary data and prior model results it requires are stored in long-running server objects.  Testing and debugging
 * of these model components can occur without the time required to run through all preliminary steps.
 *
 *
 */

public class TazDataHandler implements TazDataIf, Serializable {

    protected transient Logger logger = Logger.getLogger(TazDataHandler.class);

    public static final String PROPERTIES_TAZ_DATA          = "TazData.File";
    public static final String PROPERTIES_WALK_SHARES_DATA  = "TazWalkShares.File";
    public static final String PROPERTIES_ZONAL_ACCESSIBILITIESS_DATA  = "ZonalAccessibilities.file";


    // default values - can be overridden by subclass setter methods
    private static final String ZONE_DATA_ZONE_FIELD_NAME = "zone";
    private static final String ZONE_DATA_AREATYPE_FIELD_NAME = "at";
    private static final String ZONE_DATA_DISTRICT_FIELD_NAME = "dist";
    private static final String ZONE_DATA_COUNTY_FIELD_NAME = "county";
    private static final String ZONE_DATA_CORDON_FIELD_NAME = "cordon";
    private static final String ZONE_DATA_CORDON_COST_FIELD_NAME = "cordonCost";

    private static final String ZONE_DATA_PARKTOT_FIELD_NAME = "parkTot";
    private static final String ZONE_DATA_PARKLNG_FIELD_NAME = "parkLong";
    private static final String ZONE_DATA_PROPFREE_FIELD_NAME = "PropFree";
    private static final String ZONE_DATA_PARKRATE_FIELD_NAME = "ParkRate";
    
    
    private static final String ZONE_DATA_TOTPOP_FIELD_NAME = "TOTPOP";
    private static final String ZONE_DATA_TOTEMP_FIELD_NAME = "TOTEMP";
    private static final String ZONE_DATA_TOTACRES_FIELD_NAME = "TOTACRE";
    

    private static final String ACCESSIBILITIES_FILE_ZONE_FIELD_NAME = "taz";
    private static final String ACCESSIBILITIES_PEAK_AUTO_RETAIL_FIELD_NAME = "autoPeakRetail";
    private static final String ACCESSIBILITIES_PEAK_AUTO_TOTAL_FIELD_NAME = "autoPeakTotal";
    private static final String ACCESSIBILITIES_PEAK_TRANSIT_RETAIL_FIELD_NAME = "transitPeakRetail";
    private static final String ACCESSIBILITIES_PEAK_TRANSIT_TOTAL_FIELD_NAME = "transitPeakTotal";
    private static final String ACCESSIBILITIES_OFF_PEAK_AUTO_RETAIL_FIELD_NAME = "autoOffPeakRetail";
    private static final String ACCESSIBILITIES_OFF_PEAK_AUTO_TOTAL_FIELD_NAME = "autoOffPeakTotal";
    private static final String ACCESSIBILITIES_OFF_PEAK_TRANSIT_RETAIL_FIELD_NAME = "transitOffPeakRetail";
    private static final String ACCESSIBILITIES_OFF_PEAK_TRANSIT_TOTAL_FIELD_NAME = "transitOffPeakTotal";
    private static final String ACCESSIBILITIES_NON_MOTORIZED_RETAIL_FIELD_NAME = "nonMotorizedRetail";
    private static final String ACCESSIBILITIES_NON_MOTORIZED_TOTAL_FIELD_NAME = "nonMotorizedTotal";

    private static final String WALK_PERCENTAGE_FILE_ZONE_FIELD_NAME = "zone";
    private static final String WALK_PERCENTAGE_FILE_SHORT_FIELD_NAME = "short";
    private static final String WALK_PERCENTAGE_FILE_LONG_FIELD_NAME = "long";

    // do not change the ordering of these segment names  
    private static final String[] SUB_ZONE_NAMES = { "none", "short", "long"};	

    protected String projectDirectory;

    protected String tazDataFileName;
    protected String walkPercentFileName;

    protected int cbdAreaTypesArrayIndex;
    protected int urbanAreaTypesArrayIndex;
    protected int suburbanAreaTypesArrayIndex;
    protected int ruralAreaTypesArrayIndex;
    protected int[][] areaTypes;

    private int NUM_ZONES;
    private int NUM_SUBZONES;

    private float[] pkAutoRetail;
    private float[] pkAutoTotal;
    private float[] opAutoRetail;
    private float[] opAutoTotal;
    private float[] pkTransitRetail;
    private float[] pkTransitTotal;
    private float[] opTransitRetail;
    private float[] opTransitTotal;
    private float[] nonMotorizedRetail;
    private float[] nonMotorizedTotal;
    
    private float[] popEmpSqMile;

    protected String tazDataZoneFieldName = "";
    protected String tazDataDistFieldName= "";
    protected String tazDataCountyFieldName= "";
    protected String tazDataAtFieldName= "";
    protected String walkPctZoneFieldName= "";
    protected String walkPctShortFieldName= "";
    protected String walkPctLongFieldName= "";
    protected String parkTotFieldName= "";
    protected String parkLongFieldName= "";
    protected String propFreeFieldName= "";
    protected String parkRateFieldName= "";

    protected String zonalAccessibilityFileName;

    protected TableDataSet zoneDataTable;


    // zoneTableRow is a correspondence between zone number (i,e, origin taz or dest taz) and the TableDataSet row
    // in which those zonal attributes are stored.
    protected int[] zoneTableRow;

    // indexToZone is a correspondence between 1-based zone index values (1,...,numZones) and the zone values.
    protected int[] indexToZone;

    // altToZone is a correspondence between DC alternative number (1,...,numZones*numSubzones) and 1-based zone index (1,...,numZones)
    protected int[] altToZone;

    // altToSubZone is a correspondence between DC alternative number (1,...,numZones*numSubzones) and 0-based subzone index (0,...,numSubZones-1)
    protected int[] altToSubZone;



    // 1st dimension is indexed by zone number, 2nd dimension is walk segments - e.g. 0: no walk %, 1: shrt %, 2: long %.
    protected float[][] zonalWalkPctArray;

    protected String[] subZoneNames;



    //TODO: need to apply consistent zone number/zone table row/o & d zonal index/ correspondence defined in this class
    //TODO: and make sure that proper indexing is applied in all models that use zone table data.


    public TazDataHandler( ResourceBundle rb, String projectDirectory ){

        this.projectDirectory = projectDirectory;

        tazDataZoneFieldName = ZONE_DATA_ZONE_FIELD_NAME;
        tazDataAtFieldName = ZONE_DATA_AREATYPE_FIELD_NAME;
        tazDataDistFieldName = ZONE_DATA_DISTRICT_FIELD_NAME;
        tazDataCountyFieldName = ZONE_DATA_COUNTY_FIELD_NAME;
        walkPctZoneFieldName = WALK_PERCENTAGE_FILE_ZONE_FIELD_NAME;
        walkPctShortFieldName = WALK_PERCENTAGE_FILE_SHORT_FIELD_NAME;
        walkPctLongFieldName = WALK_PERCENTAGE_FILE_LONG_FIELD_NAME;
        parkTotFieldName = ZONE_DATA_PARKTOT_FIELD_NAME;
        parkLongFieldName = ZONE_DATA_PARKLNG_FIELD_NAME;
        propFreeFieldName = ZONE_DATA_PROPFREE_FIELD_NAME;
        parkRateFieldName = ZONE_DATA_PARKRATE_FIELD_NAME;

        subZoneNames = SUB_ZONE_NAMES;

        // locate the taz data from the .properties file
        tazDataFileName = projectDirectory + ResourceUtil.getProperty(rb, PROPERTIES_TAZ_DATA);

        // locate the walk percentages data from the .properties file
        walkPercentFileName = projectDirectory + ResourceUtil.getProperty(rb, PROPERTIES_WALK_SHARES_DATA);

        // locate the walk percentages data from the .properties file
        zonalAccessibilityFileName = projectDirectory + ResourceUtil.getProperty(rb, PROPERTIES_ZONAL_ACCESSIBILITIESS_DATA);

    }



    public void setupTazDataManager() {

		// create the zonal data table
		zoneDataTable = readZonalData(tazDataFileName);

        // compute the number of destination choice alternatives
	    NUM_SUBZONES = subZoneNames.length;

        // prepare the zonal walk percent array
		zonalWalkPctArray = new float[NUM_SUBZONES][NUM_ZONES + 1];


        // if walk-based market segmentation is implemented, read walk percentages file; otherwise, walk is 100% 
		if (NUM_SUBZONES == 1) 
			Arrays.fill(zonalWalkPctArray[0], 1);
		else
			readWalkPercentagesFile(walkPercentFileName);

        // dimension the correspondence arrays that will contain the zone and subzone, respectively, given the DC alternative index (1,...,numAlts)
        altToZone = new int[NUM_ZONES*NUM_SUBZONES + 1];
        altToSubZone = new int[NUM_ZONES*NUM_SUBZONES + 1];

        for (int i=1; i <= NUM_ZONES*NUM_SUBZONES; i++) {
            altToZone[i] = getZoneFromAlt(i);
            altToSubZone[i] = getWalkSubzoneFromAlt(i);
        }


        readZonalAccessibilitiesFile (zonalAccessibilityFileName);
        
        //for TNC/Taxi wait times
        calculatePopEmpSqMi();
    }



    private TableDataSet readZonalData(String zoneDataFileName) {

        int numZones = 0;
        int maxZone = 0;
        int zoneCol;
        TableDataSet zoneTable;

        try{

            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            reader.setDelimSet( "," + reader.getDelimSet() );
            zoneTable = reader.readFile(new File( zoneDataFileName ));

            // set global max zone and num zones values, and make sure there are no duplicates.
            zoneCol = zoneTable.getColumnPosition( tazDataZoneFieldName );
            HashMap<Integer,Integer> zoneValues = new HashMap<Integer,Integer>();

            for (int i=1; i <= zoneTable.getRowCount(); i++) {
                int zone = (int)zoneTable.getValueAt(i, zoneCol);
                if ( zoneValues.containsKey( zone ) ) {
                    logger.fatal( String.format("zone employment table read from %s has duplicate value for ZONE=%d in column %d at record number %d", zoneDataFileName, zone, zoneCol, (i+1)) );
                    throw new RuntimeException();
                }
                else {
                    zoneValues.put(zone, i);
                    numZones++;
                    if ( zone > maxZone )
                        maxZone = zone;
                }

            }

        }
        catch(IOException e){
            logger.error( String.format( "Exception occurred reading zonal employment data file: %s into TableDataSet object.", zoneDataFileName ) );
            throw new RuntimeException();
        }

        NUM_ZONES = numZones;

        // store the row numbers for each zone so that zonal attributes can be retrieved later using given a zone number
        indexToZone = new int[numZones+1];
        zoneTableRow = new int[maxZone+1];
        for (int i=1; i <= zoneTable.getRowCount(); i++) {
            int zone = (int)zoneTable.getValueAt(i, zoneCol);
            zoneTableRow[zone] = i;
            indexToZone[i] = zone;
        }

        return zoneTable;

    }


    private void readWalkPercentagesFile (String fileName) {

        int taz;
        float[] shrtArray = new float[NUM_ZONES + 1];
        float[] longArray = new float[NUM_ZONES + 1];
        zonalWalkPctArray = new float[NUM_SUBZONES][NUM_ZONES + 1];
        Arrays.fill(zonalWalkPctArray[0], 1.0f);
        Arrays.fill(zonalWalkPctArray[1], 0.0f);
        Arrays.fill(zonalWalkPctArray[2], 0.0f);

        if (fileName != null) {

            try {
                OLD_CSVFileReader reader = new OLD_CSVFileReader();
                reader.setDelimSet( " " + reader.getDelimSet() );
                TableDataSet wa = reader.readFile(new File(fileName));

                int tazPosition = wa.getColumnPosition( walkPctZoneFieldName );
                if (tazPosition <= 0) {
                    logger.fatal( String.format("expected zone field name=%s was not a field in the walk access file: %s.", WALK_PERCENTAGE_FILE_ZONE_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int shrtPosition = wa.getColumnPosition( walkPctShortFieldName );
                if (shrtPosition <= 0) {
                    logger.fatal( String.format("expected short field name=%s was not a field in the walk access file: %s.", WALK_PERCENTAGE_FILE_SHORT_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int longPosition = wa.getColumnPosition( walkPctLongFieldName );
                if (longPosition <= 0) {
                    logger.fatal( String.format("expected long field name=%s was not a field in the walk access file: %s.", WALK_PERCENTAGE_FILE_LONG_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                for (int j = 1; j <= wa.getRowCount(); j++) {
                    taz = (int) wa.getValueAt(j, tazPosition);
                    shrtArray[taz] = wa.getValueAt(j, shrtPosition);
                    longArray[taz] = wa.getValueAt(j, longPosition);
                    zonalWalkPctArray[1][taz] = shrtArray[taz];										// segment "short"
                    zonalWalkPctArray[2][taz] = longArray[taz];										// segment "long"
                    zonalWalkPctArray[0][taz] = (float) ( 1.0 - (shrtArray[taz] + longArray[taz]) );// segment "none"
                }

            }
            catch (IOException e) {
                logger.fatal( String.format("exception caught reading walk access file: %s", fileName), e);
            }

        } else {

            logger.fatal( "no zonal walk access data file was named in properties file with target: 'WalkPercentages.file ='." );
            throw new RuntimeException();

        }

    }


    private void readZonalAccessibilitiesFile (String fileName) {

        int taz;
        pkAutoRetail = new float[NUM_ZONES + 1];
        pkAutoTotal = new float[NUM_ZONES + 1];
        opAutoRetail = new float[NUM_ZONES + 1];
        opAutoTotal = new float[NUM_ZONES + 1];
        pkTransitRetail = new float[NUM_ZONES + 1];
        pkTransitTotal = new float[NUM_ZONES + 1];
        opTransitRetail = new float[NUM_ZONES + 1];
        opTransitTotal = new float[NUM_ZONES + 1];
        nonMotorizedRetail = new float[NUM_ZONES + 1];
        nonMotorizedTotal = new float[NUM_ZONES + 1];


        if (fileName != null) {

            try {
                OLD_CSVFileReader reader = new OLD_CSVFileReader();
                reader.setDelimSet( " " + reader.getDelimSet() );
                TableDataSet acc = reader.readFile(new File(fileName));

                int tazPosition = acc.getColumnPosition( ACCESSIBILITIES_FILE_ZONE_FIELD_NAME );
                if (tazPosition <= 0) {
                    logger.fatal( String.format("expected zone field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_FILE_ZONE_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int pkAutoRetailPosition = acc.getColumnPosition( ACCESSIBILITIES_PEAK_AUTO_RETAIL_FIELD_NAME );
                if (pkAutoRetailPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_PEAK_AUTO_RETAIL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int pkAutoTotalPosition = acc.getColumnPosition( ACCESSIBILITIES_PEAK_AUTO_TOTAL_FIELD_NAME );
                if (pkAutoTotalPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_PEAK_AUTO_TOTAL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int pkTransitRetailPosition = acc.getColumnPosition( ACCESSIBILITIES_PEAK_TRANSIT_RETAIL_FIELD_NAME );
                if (pkTransitRetailPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_PEAK_TRANSIT_RETAIL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int pkTransitTotalPosition = acc.getColumnPosition( ACCESSIBILITIES_PEAK_TRANSIT_TOTAL_FIELD_NAME );
                if (pkTransitTotalPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_PEAK_TRANSIT_TOTAL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int opAutoRetailPosition = acc.getColumnPosition( ACCESSIBILITIES_OFF_PEAK_AUTO_RETAIL_FIELD_NAME );
                if (opAutoRetailPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_OFF_PEAK_AUTO_RETAIL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int opAutoTotalPosition = acc.getColumnPosition( ACCESSIBILITIES_OFF_PEAK_AUTO_TOTAL_FIELD_NAME );
                if (opAutoTotalPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_OFF_PEAK_AUTO_TOTAL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int opTransitRetailPosition = acc.getColumnPosition( ACCESSIBILITIES_OFF_PEAK_TRANSIT_RETAIL_FIELD_NAME );
                if (opTransitRetailPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_OFF_PEAK_TRANSIT_RETAIL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int opTransitTotalPosition = acc.getColumnPosition( ACCESSIBILITIES_OFF_PEAK_TRANSIT_TOTAL_FIELD_NAME );
                if (opTransitTotalPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_OFF_PEAK_TRANSIT_TOTAL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int nonMotorizedRetailPosition = acc.getColumnPosition( ACCESSIBILITIES_NON_MOTORIZED_RETAIL_FIELD_NAME );
                if (nonMotorizedRetailPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_NON_MOTORIZED_RETAIL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }

                int nonMotorizedTotalPosition = acc.getColumnPosition( ACCESSIBILITIES_NON_MOTORIZED_TOTAL_FIELD_NAME );
                if (nonMotorizedTotalPosition <= 0) {
                    logger.fatal( String.format("expected field name=%s was not a field in the zonal accessibilities file: %s.", ACCESSIBILITIES_NON_MOTORIZED_TOTAL_FIELD_NAME, fileName));
                    throw new RuntimeException();
                }


                for (int i=1; i <= acc.getRowCount(); i++) {
                    taz = (int) acc.getValueAt(i, tazPosition);
                    pkAutoRetail[taz] = acc.getValueAt(i, pkAutoRetailPosition);
                    pkAutoTotal[taz] = acc.getValueAt(i, pkAutoTotalPosition);
                    pkTransitRetail[taz] = acc.getValueAt(i, pkTransitRetailPosition);
                    pkTransitTotal[taz] = acc.getValueAt(i, pkTransitTotalPosition);
                    opAutoRetail[taz] = acc.getValueAt(i, opAutoRetailPosition);
                    opAutoTotal[taz] = acc.getValueAt(i, opAutoTotalPosition);
                    opTransitRetail[taz] = acc.getValueAt(i, opTransitRetailPosition);
                    opTransitTotal[taz] = acc.getValueAt(i, opTransitTotalPosition);
                    nonMotorizedRetail[taz] = acc.getValueAt(i, nonMotorizedRetailPosition);
                    nonMotorizedTotal[taz] = acc.getValueAt(i, nonMotorizedTotalPosition);
                }

            }
            catch (IOException e) {
                logger.fatal( String.format("exception caught reading accessibilities file: %s", fileName), e);
            }

        } else {

            logger.fatal( "no zonal accessibilities data file was named in properties file with target: " + fileName );
            throw new RuntimeException();

        }

    }


    /**
     * @param alt is the DC alternaive number
     * @return zone number for the DC alt.
     */
    private int getZoneFromAlt ( int alt ) {
        int zone = (int)((alt-1)/NUM_SUBZONES) + 1;
        if ( zone < 1 || zone > NUM_ZONES ) {
            logger.fatal( String.format("invalid value for zone index = %d, determined for alt = %d.", zone, alt) );
            logger.fatal( String.format("NUM_ZONES = %d, NUM_SUBZONES = %d.", NUM_ZONES, NUM_SUBZONES) );
            throw new RuntimeException();
        }
        return zone;
    }

    /**
     * @param alt is the DC alternaive number
     * @return walk subzone index for the DC alt.
     */
    private int getWalkSubzoneFromAlt ( int alt ) {
        int zone = getZoneFromAlt ( alt );
        int subzone = alt - (zone-1)*NUM_SUBZONES - 1;
        if ( subzone < 0 || subzone >= NUM_SUBZONES ) {
            logger.fatal( String.format("invalid value for walk subzone index = %d, zone = %d, determined for alt = %d.", subzone, zone, alt) );
            logger.fatal( String.format("NUM_ZONES = %d, NUM_SUBZONES = %d.", NUM_ZONES, NUM_SUBZONES) );
            throw new RuntimeException();
        }
        return subzone;
    }






    public String testRemote() {
        return String.format("testRemote() method in %s called.", this.getClass().getCanonicalName() );
    }

    public int[] getAltToZoneArray () {
        return altToZone;
    }

    public int[] getAltToSubZoneArray () {
        return altToSubZone;
    }

    public int[] getIndexToZoneArray () {
        return indexToZone;
    }

    public int[] getZoneTableRowArray () {
        return zoneTableRow;
    }


    /**
     *
     * @param field is the field name to be checked against the column names in the zone data table.
     * @return true if field matches one of the zone data table column names, otherwise false.
     */
    public boolean isValidZoneTableField(String field){
        return zoneDataTable.getColumnPosition(field) >= 0;
    }


    public String[] getZoneDataTableColumnLabels() {
        return zoneDataTable.getColumnLabels();
    }

    public int getNumberOfZones(){
        return NUM_ZONES;
    }

    public int getNumberOfSubZones(){
        return NUM_SUBZONES;
    }

    public String[] getSubZoneNames() {
        return subZoneNames;
    }

    public double[] getZonalWalkPercentagesForTaz( int taz ) {
        double[] percentages = new double[NUM_SUBZONES];
        for (int i=0; i < NUM_SUBZONES; i++)
            percentages[i] = zonalWalkPctArray[i][taz];
        return percentages;
    }

    public float getZoneTableValue ( int taz, String fieldName ) {
        // get the table row number for the TAZ passed in
        int rowIndex = zoneTableRow[taz];

        // get the table value from the rowIndex and fieldname passed in
        return zoneDataTable.getValueAt( rowIndex, fieldName );
    }

    // get the table column from the fieldname passed in
    public int[] getZoneTableIntColumn ( String fieldName ) {
        return zoneDataTable.getColumnAsInt( fieldName );
    }

    // get the table column from the fieldname passed in
    public float[] getZoneTableFloatColumn ( String fieldName ) {
        return zoneDataTable.getColumnAsFloat( fieldName );
    }

    /**
     * @param tableRowNumber is the zone table row number
     * @return zone number for the table row.
     */
    public int getTazNumber ( int tableRowNumber ) {
        return (int) zoneDataTable.getValueAt( tableRowNumber, tazDataZoneFieldName );
    }

    /**
     * @return area type array from the zone data table.
     */
    public int[] getZonalAreaType () {
        int atFieldPosition = zoneDataTable.getColumnPosition( tazDataAtFieldName );
        if ( atFieldPosition < 0 ) {
            logger.error ( String.format("The area type field name = %s defined in %s is not found as a field name in the zone data table.", tazDataAtFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsInt( atFieldPosition );
    }

    /**
     * @return district array from the zone data table.
     */
    public int[] getZonalDistrict () {
        int districtFieldPosition = zoneDataTable.getColumnPosition( tazDataDistFieldName );
        if ( districtFieldPosition < 0 ) {
            logger.error ( String.format("The district field name = %s defined in %s is not found as a field name in the zone data table.", tazDataDistFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsInt( districtFieldPosition );
    }

    /**
     * @return county array from the zone data table.
     */
    public int[] getZonalCounty () {
        int countyFieldPosition = zoneDataTable.getColumnPosition( tazDataCountyFieldName );
        if ( countyFieldPosition < 0 ) {
            logger.error ( String.format("The county field name = %s defined in %s is not found as a field name in the zone data table.", tazDataCountyFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsInt( countyFieldPosition );
    }

    public int getZoneCordon( int taz ) {
        // handle if the cordon column doesn't exist
        return (int)getZoneTableValue(taz, ZONE_DATA_CORDON_FIELD_NAME );
    }

    public int getZoneCordonCost( int taz ) {
        // handle if the cordon column doesn't exist
        return (int)getZoneTableValue(taz, ZONE_DATA_CORDON_COST_FIELD_NAME );
    }

    public int getZoneIsCbd( int taz ) {
        return getZoneIsInAreaType( taz, areaTypes[cbdAreaTypesArrayIndex] );
    }

    public int getZoneIsUrban( int taz ) {
        return getZoneIsInAreaType( taz, areaTypes[urbanAreaTypesArrayIndex] );
    }

    public int getZoneIsSuburban( int taz ) {
        return getZoneIsInAreaType( taz, areaTypes[suburbanAreaTypesArrayIndex] );
    }

    public int getZoneIsRural( int taz ) {
        return getZoneIsInAreaType( taz, areaTypes[ruralAreaTypesArrayIndex] );
    }

    public int getZoneCounty( int taz ) {
        return (int)getZoneTableValue ( taz, tazDataCountyFieldName );
    }

    private int getZoneIsInAreaType( int taz, int[] areaTypes  ) {
        int returnValue = 0;
        int tazAreaType = (int)getZoneTableValue ( taz, tazDataAtFieldName );
        for ( int atIndex : areaTypes ) {
            if ( tazAreaType == atIndex ) {
                returnValue = 1;
                break;
            }
        }
        return returnValue;
    }

    
    /**
     * @return parkTot field name used in the zone data table.
     */
    public String getZonalParkTotFieldName () {
        return parkTotFieldName;
    }
    
    
    /**
     * @return parkRate field name used in the zone data table.
     */
    public String getZonalParkRateFieldName () {
        return parkRateFieldName;
    }
    
    
    /**
     * @return parkTot array from the zone data table.
     */
    public int[] getZonalParkTot () {
        int parkTotFieldPosition = zoneDataTable.getColumnPosition( parkTotFieldName );
        if ( parkTotFieldPosition < 0 ) {
            logger.error ( String.format("The parkTot field name = %s defined in %s is not found as a field name in the zone data table.", parkTotFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsInt( parkTotFieldPosition );
    }

    /**
     * @return parkLong array from the zone data table.
     */
    public int[] getZonalParkLong () {
        int parkLongFieldPosition = zoneDataTable.getColumnPosition( parkLongFieldName );
        if ( parkLongFieldPosition < 0 ) {
            logger.error ( String.format("The parkLong field name = %s defined in %s is not found as a field name in the zone data table.", parkLongFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsInt( parkLongFieldPosition );
    }

    /**
     * @return propFree array from the zone data table.
     */
    public float[] getZonalPropFree () {
        int propFreeFieldPosition = zoneDataTable.getColumnPosition( propFreeFieldName );
        if ( propFreeFieldPosition < 0 ) {
            logger.error ( String.format("The propFree field name = %s defined in %s is not found as a field name in the zone data table.", propFreeFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsFloat( propFreeFieldPosition );
    }

    /**
     * @return parkRate array from the zone data table.
     */
    public float[] getZonalParkRate () {
        int parkRateFieldPosition = zoneDataTable.getColumnPosition( parkRateFieldName );
        if ( parkRateFieldPosition < 0 ) {
            logger.error ( String.format("The parkRate field name = %s defined in %s is not found as a field name in the zone data table.", parkRateFieldName, this.getClass().getName() ));
            throw new RuntimeException();
        }
        return zoneDataTable.getColumnAsFloat( parkRateFieldPosition );
    }

    


    public float[] getPkAutoRetailAccessibity() {
        return pkAutoRetail;
    }

    public float[] getPkAutoTotalAccessibity() {
        return pkAutoTotal;
    }

    public float[] getPkTransitRetailAccessibity() {
        return pkTransitRetail;
    }

    public float[] getPkTransitTotalAccessibity() {
        return pkTransitTotal;
    }

    public float[] getOpAutoRetailAccessibity() {
        return opAutoRetail;
    }

    public float[] getOpAutoTotalAccessibity() {
        return opAutoTotal;
    }

    public float[] getOpTransitRetailAccessibity() {
        return opTransitRetail;
    }

    public float[] getOpTransitTotalAccessibity() {
        return opTransitTotal;
    }

    public float[] getNonMotorizedRetailAccessibity() {
        return nonMotorizedRetail;
    }

    public float[] getNonMotorizedTotalAccessibity() {
        return nonMotorizedTotal;
    }

    /**
     * Get a new array of zones.
     * 
     */
    public int[] getTazs(){
    	
    	int[] tazs = new int[this.getNumberOfZones()];
    	
    	for(int i = 0; i < tazs.length; ++ i)
    		tazs[i] = this.getTazNumber(i+1);
    	
    	return tazs;
    	
    }
    
    /**
     * Get a new array of zones, indexed from 1
     */
    public int[] getTazsOneBased(){
    	
    	int[] tazs = new int[this.getNumberOfZones()+1];
    	
    	for(int i = 0; i < tazs.length; ++ i)
    		tazs[i+1] = this.getTazNumber(i+1);
    	
    	return tazs;
    	
    }
    
    /**
     * For TAXI/TNC wait times; currently calculated based on pop,emp,acre fields in TAZ file. Does not
     * use a floating zone calculation, which is probably OK for now, since TM1 is zone-based.
     * 
     */
    private void calculatePopEmpSqMi(){
    	
    	popEmpSqMile = new float[NUM_ZONES+1];
        
    	for (int i=1; i <= zoneDataTable.getRowCount(); i++) {
            int taz = (int) zoneDataTable.getValueAt(i, ZONE_DATA_ZONE_FIELD_NAME);
            double pop = zoneDataTable.getValueAt(i, ZONE_DATA_TOTPOP_FIELD_NAME);
            double emp = zoneDataTable.getValueAt(i, ZONE_DATA_TOTEMP_FIELD_NAME);
            double acres = zoneDataTable.getValueAt(i, ZONE_DATA_TOTACRES_FIELD_NAME);
            
            //factor to convert acres to sq. miles = 0.0015625
            popEmpSqMile[taz] = (float) ((pop+emp)/(acres * 0.0015625));
        }
    	
    }
    
    /**
     * Get population + employment per square mile for TAZ.
     * 
     * @param taz
     * @return
     */
    public float getPopEmpPerSqMi(int taz){

    	return popEmpSqMile[taz];
    }
   
    

    public enum AreaType {
        CBD,
        URBAN,
        SUBURBAN,
        RURAL
    }

}