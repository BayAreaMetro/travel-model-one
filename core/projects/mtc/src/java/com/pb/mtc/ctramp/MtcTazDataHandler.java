package com.pb.mtc.ctramp;

import org.apache.log4j.Logger;

import com.pb.models.ctramp.TazDataHandler;
import com.pb.common.util.CommandLine;
import com.pb.common.util.ResourceUtil;

import java.util.ResourceBundle;

import gnu.cajo.invoke.Remote;
import gnu.cajo.utils.ItemServer;

public class MtcTazDataHandler extends TazDataHandler {

    protected static Logger logger = Logger.getLogger(MtcTazDataHandler.class);

    public static final String ZONAL_DATA_SERVER_NAME = MtcTazDataHandler.class.getCanonicalName();
    public static final String ZONAL_DATA_SERVER_ADDRESS = "192.168.1.212";
    public static final int ZONAL_DATA_SERVER_PORT = 1131;

    public static final String ZONE_DATA_ZONE_FIELD_NAME = "ZONE";
    public static final String ZONE_DATA_COUNTY_FIELD_NAME = "county";
    public static final String ZONE_DATA_DISTRICT_FIELD_NAME = "district";
    
    public static final String ZONE_DATA_TOPOLOGY_FIELD_NAME = "topology";
    public static final String ZONE_DATA_HH_FIELD_NAME = "tothh";        
    public static final String ZONE_DATA_POP_FIELD_NAME = "totpop";
    public static final String ZONE_DATA_HH_POP_FIELD_NAME = "hhpop";
    public static final String ZONE_DATA_EMP_FIELD_NAME = "totemp";        
    public static final String ZONE_DATA_RESACRE_FIELD_NAME = "resacre";        
    public static final String ZONE_DATA_COMACRE_FIELD_NAME = "ciacre";
    public static final String ZONE_DATA_PEAK_HOURLY_PARKING_COST_FIELD_NAME = "prkcst";
    public static final String ZONE_DATA_OFFPEAK_HOURLY_PARKING_COST_FIELD_NAME = "oprkcst";
    public static final String ZONE_DATA_TERMINAL_TIME_FIELD_NAME = "terminal";
    
    public static final String ZONE_DATA_PERSONS_AGE_05_TO_19_FIELD_NAME = "age0519";
    public static final String ZONE_DATA_PERSONS_AGE_20_TO_44_FIELD_NAME = "age2044";
    public static final String ZONE_DATA_HIGH_SCHOOL_ENROLLMENT_FIELD_NAME = "hsenroll";
    public static final String ZONE_DATA_COLLEGE_PART_TIME_ENROLLMENT_FIELD_NAME = "collpte";
    public static final String ZONE_DATA_COLLEGE_FULL_TIME_ENROLLMENT_FIELD_NAME = "collfte";
    
    
    private static final String ZONE_DATA_AREATYPE_FIELD_NAME = "areatype";
    

    private static final String WALK_PERCENTAGE_FILE_ZONE_FIELD_NAME = "TAZ";
    private static final String WALK_PERCENTAGE_FILE_SHORT_FIELD_NAME = "SHRT";
    private static final String WALK_PERCENTAGE_FILE_LONG_FIELD_NAME = "LONG";

    //TODO Need to update these with real values
    private static final String ZONE_DATA_PARKTOT_FIELD_NAME = "ZERO";
    private static final String ZONE_DATA_PARKLNG_FIELD_NAME = "ZERO";
    private static final String ZONE_DATA_PROPFREE_FIELD_NAME = "ZERO";
    private static final String ZONE_DATA_PARKRATE_FIELD_NAME = "PrkCst";
    
    private static final String[] SUB_ZONE_NAMES = { "NONE", "SHORT", "LONG"};
    private static final String[] AREA_TYPE_NAMES = { "CBD_0", "CBD_1", "URBAN_2", "URBAN_3", "SUBURBAN_4", "RURAL_5" };

    public MtcTazDataHandler( ResourceBundle rb, String projectDirectory ){
		super( rb, projectDirectory );

        tazDataZoneFieldName = ZONE_DATA_ZONE_FIELD_NAME;
        tazDataAtFieldName = ZONE_DATA_AREATYPE_FIELD_NAME;
        tazDataDistFieldName = ZONE_DATA_DISTRICT_FIELD_NAME;

        walkPctZoneFieldName = WALK_PERCENTAGE_FILE_ZONE_FIELD_NAME;
        walkPctShortFieldName = WALK_PERCENTAGE_FILE_SHORT_FIELD_NAME;
        walkPctLongFieldName = WALK_PERCENTAGE_FILE_LONG_FIELD_NAME;

        parkTotFieldName = ZONE_DATA_PARKTOT_FIELD_NAME;
        parkLongFieldName = ZONE_DATA_PARKLNG_FIELD_NAME;
        propFreeFieldName = ZONE_DATA_PROPFREE_FIELD_NAME;
        parkRateFieldName = ZONE_DATA_PARKRATE_FIELD_NAME;
        
        subZoneNames = SUB_ZONE_NAMES;

        setupTazDataManager();
        
    }


    private static void usage( String[] args ) {
        logger.error( String.format( "improper arguments." ) );
        if (args.length == 0 ) {
            logger.error( String.format( "no properties file specified." ) );
            logger.error( String.format( "a properties file base name (without .properties extension) must be specified as the first argument." ) );
        }
        else if (args.length >= 1 ) {
            logger.error( String.format( "improper properties file specified." ) );
            logger.error( String.format( "a properties file base name (without .properties extension) must be specified as the first argument." ) );
        }
    }


    public int getZoneIsCbd( int taz ) {
        if ( getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.CBD_0.ordinal() || getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.CBD_1.ordinal() )
            return 1;
        else
            return 0;
    }
    
    public int getZoneIsUrban( int taz ) {
        if ( getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.URBAN_2.ordinal() || getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.URBAN_3.ordinal() )
            return 1;
        else
            return 0;
    }

    public int getZoneIsSuburban( int taz ) {
        if ( getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.SUBURBAN_4.ordinal() )
            return 1;
        else
            return 0;
    }

    public int getZoneIsRural( int taz ) {
        if ( getZoneTableValue ( taz, tazDataAtFieldName ) == AreaType.RURAL_5.ordinal() )
            return 1;
        else
            return 0;
    }


    public enum AreaType {
        CBD_0,
        CBD_1,
        URBAN_2,
        URBAN_3,
        SUBURBAN_4,
        RURAL_5
    }


    public static void main(String args[]) throws Exception {

        ResourceBundle rb;
        CommandLine cmdline = new CommandLine(args);


        String baseName = null;
        if ( args.length == 0 ) {
            MtcTazDataHandler.usage( args );
            return;
        }
        else if ( args.length == 1 ) {
            if ( args[0].endsWith(".properties" ) ) {
                int index = args[0].indexOf(".properties");
                baseName = args[0].substring(0, index);
            }
            else
                baseName = args[0];
        }

        if ( baseName == null ) {
            MtcTazDataHandler.usage( args );
            return;
        }
        else
            rb = ResourceBundle.getBundle( baseName );



        String projectDirectory = ResourceUtil.getProperty(rb, MtcTourBasedModel.PROPERTIES_PROJECT_DIRECTORY);

        Remote.config( ZONAL_DATA_SERVER_ADDRESS, ZONAL_DATA_SERVER_PORT, null, 0 );

        // create the tazDatahandler object
        MtcTazDataHandler tazDataHandler = new MtcTazDataHandler( rb, projectDirectory );
        tazDataHandler.setupTazDataManager();

        ItemServer.bind( tazDataHandler, ZONAL_DATA_SERVER_NAME );

        System.out.println( String.format("MtcTazDataHandler server class started on: %s:%d", ZONAL_DATA_SERVER_ADDRESS, ZONAL_DATA_SERVER_PORT ) );
    }

}