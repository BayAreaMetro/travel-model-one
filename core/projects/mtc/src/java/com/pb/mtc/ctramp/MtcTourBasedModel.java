package com.pb.mtc.ctramp;


import java.util.HashMap;
import java.util.MissingResourceException;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.HouseholdDataManager;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.HouseholdDataManagerRmi;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.jppf.CtrampApplication;
import com.pb.mtc.synpop.MTCPopulationSynthesizer;


public class MtcTourBasedModel {

    public static Logger logger = Logger.getLogger(MtcTourBasedModel.class);

    public static final String PROPERTIES_PROJECT_DIRECTORY = "Project.Directory";
    
    private static final int DEFAULT_ITERATION_NUMBER = 1;
    private static final float DEFAULT_SAMPLE_RATE = 1.0f;
    private static final int DEFAULT_SAMPLE_SEED = 0;
    
    public static final int DEBUG_CHOICE_MODEL_HHID = 740151;

    private ResourceBundle rb;
    private String propertiesFileBaseName;

    // values for these variables are set as command line arguments, or default vaues are used if no command line arguments are specified.
    private int globalIterationNumber = 0;
    private float iterationSampleRate = 0f;
    private int sampleSeed = 0;

    /**
     *
     * @param rb, java.util.ResourceBundle containing environment settings from a properties file specified on the command line
     * @param baseName, String containing basename (without .properites) from which ResourceBundle was created.
     * @param globalIterationNumber, int iteration number for which the model is run, set by another process controlling a model stream with feedback.
     * @param iterationSampleRate, float percentage [0.0, 1.0] inicating the portion of all households to be modeled.
     *
     * This object defines the implementation of the MTC tour based, activity based travel demand model.
     */
    public MtcTourBasedModel( ResourceBundle rb, String baseName, int globalIterationNumber, float iterationSampleRate, int sampleSeed ) {
        this.rb = rb;
        propertiesFileBaseName = baseName;
        this.globalIterationNumber = globalIterationNumber;
        this.iterationSampleRate = iterationSampleRate;
        this.sampleSeed = sampleSeed;
    }



    private void runTourBasedModel() {


        // new a ctramp application object
        MtcCtrampApplication ctrampApplication = new MtcCtrampApplication( rb );
        String projectDirectory = ctrampApplication.getProjectDirectoryName();

        // create modelStructure object
        MtcModelStructure modelStructure = new MtcModelStructure();


        
        boolean localHandlers = false;
        
        String hhHandlerAddress = "";
        int hhServerPort = 0;
        try {
            // get household server address.  if none is specified a local server in the current process will be started.
            hhHandlerAddress = rb.getString( "RunModel.HouseholdServerAddress" );
            try {
                // get household server port.
                hhServerPort = Integer.parseInt( rb.getString( "RunModel.HouseholdServerPort" ) );
                localHandlers = false;
            }
            catch ( MissingResourceException e ) {
                // if no household data server address entry is found, the object will be created in the local process
                localHandlers = true;
            }
        }
        catch ( MissingResourceException e ) {
            localHandlers = true;
        }

        
        
        
        TazDataIf tazDataHandler;
        String testString;
//        if ( localHandlers ) {
            tazDataHandler = new MtcTazDataHandler(rb, projectDirectory);
//        }
//        else {
//            tazDataHandler = new TazDataHandlerRmi( MtcTazDataHandler.ZONAL_DATA_SERVER_ADDRESS, MtcTazDataHandler.ZONAL_DATA_SERVER_PORT, MtcTazDataHandler.ZONAL_DATA_SERVER_NAME );
//            testString = tazDataHandler.testRemote();
//            logger.info ( "TazDataHandler test: " + testString );
//        }


        // setup the ctramp application
        ctrampApplication.setupModels( modelStructure, tazDataHandler );

        // generate the synthetic population
        MTCPopulationSynthesizer populationSynthesizer = new MTCPopulationSynthesizer( propertiesFileBaseName );
        ctrampApplication.runPopulationSynthesizer( populationSynthesizer );


        HouseholdDataManagerIf householdDataManager;
        
        HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(rb);
        
        try {

            if ( localHandlers ) {

                // create a new local instance of the household array manager
                householdDataManager = new MtcHouseholdDataManager();
                householdDataManager.setPropertyFileValues( propertyMap );

                // have the household data manager read the synthetic population files and apply its tables to objects mapping method.
                String inputHouseholdFileName = rb.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_HH );
                String inputPersonFileName = rb.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_PERS );
                householdDataManager.setHouseholdSampleRate( iterationSampleRate, sampleSeed );
                householdDataManager.setupHouseholdDataManager( modelStructure, tazDataHandler, inputHouseholdFileName, inputPersonFileName );
                 
            }
            else {

                householdDataManager = new HouseholdDataManagerRmi( hhHandlerAddress, hhServerPort, MtcHouseholdDataManager.HH_DATA_SERVER_NAME );
                testString = householdDataManager.testRemote();
                logger.info ( "HouseholdDataManager test: " + testString );

                householdDataManager.setPropertyFileValues( propertyMap );


                // have the household data manager read the synthetic population files and apply its tables to objects mapping method.
                boolean restartHhServer = false;
                try {
                    // possible values for the following can be none, ao, cdap, imtf, imtod, awf, awl, awtod, jtf, jtl, jtod, inmtf, inmtl, inmtod, stf, stl
                    String restartModel = rb.getString( "RunModel.RestartWithHhServer" );
                    if ( restartModel.equalsIgnoreCase("none") )
                        restartHhServer = true;
                    else if ( restartModel.equalsIgnoreCase("uwsl") || restartModel.equalsIgnoreCase("ao") ||
                        restartModel.equalsIgnoreCase("fp") || restartModel.equalsIgnoreCase("cdap") || restartModel.equalsIgnoreCase("imtf") ||
                        restartModel.equalsIgnoreCase("imtod") || restartModel.equalsIgnoreCase("awf") || restartModel.equalsIgnoreCase("awl") ||
                        restartModel.equalsIgnoreCase("awtod") || restartModel.equalsIgnoreCase("jtf") || restartModel.equalsIgnoreCase("jtl") ||
                        restartModel.equalsIgnoreCase("jtod") || restartModel.equalsIgnoreCase("inmtf") || restartModel.equalsIgnoreCase("inmtl") ||
                        restartModel.equalsIgnoreCase("inmtod") || restartModel.equalsIgnoreCase("stf") || restartModel.equalsIgnoreCase("stl") )
                            restartHhServer = false;
                }
                catch ( MissingResourceException e ) {
                    restartHhServer = true;
                }
                
                
                
                if ( restartHhServer ) {

                    householdDataManager.setDebugHhIdsFromHashmap ();

                    String inputHouseholdFileName = rb.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_HH );
                    String inputPersonFileName = rb.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_PERS );
                    householdDataManager.setHouseholdSampleRate( iterationSampleRate, sampleSeed );
                    householdDataManager.setupHouseholdDataManager( modelStructure, tazDataHandler, inputHouseholdFileName, inputPersonFileName );
                } else {

                    // if the restart is from a disk object file, the ctrampApplication.runModels() method will take care of readig the file
                    // and the debug households already set will be used.
                    if ( ctrampApplication.restartFromDiskObjectFile() == false ) {
                        householdDataManager.setHouseholdSampleRate( iterationSampleRate, sampleSeed );
                        householdDataManager.setDebugHhIdsFromHashmap ();
                        householdDataManager.setTraceHouseholdSet();

                        // set the random number sequence for household objects accordingly based on which model components are
                        // assumed to have already run and are stored in the remote HouseholdDataManager object.
                        ctrampApplication.restartModels( householdDataManager );
                    }

                }
                

            }



            // create a factory object to pass to various model components from which they can create DMU objects
            MtcCtrampDmuFactory dmuFactory = new MtcCtrampDmuFactory( tazDataHandler, modelStructure );

            // run the models
            ctrampApplication.runModels( householdDataManager, dmuFactory, globalIterationNumber, iterationSampleRate );
            

        }
        catch ( Exception e ) {

            logger.error ( String.format( "exception caught running ctramp model components -- exiting." ), e );
            throw new RuntimeException();

        }
        
    }



    public static void main(String[] args) {

        long startTime = System.currentTimeMillis();
        int globalIterationNumber = -1;
        float iterationSampleRate = -1.0f;
        int sampleSeed = -1;
        
        ResourceBundle rb = null;

        logger.info( String.format( "MTC Tour Based Model using CT-RAMP version %s, 21Oct2024 build", CtrampApplication.VERSION) );
        
        if ( args.length == 0 ) {
            logger.error( String.format( "no properties file base name (without .properties extension) was specified as an argument." ) );
            return;
        }
        else {
            rb = ResourceBundle.getBundle( args[0] );

            // optional arguments
            for (int i=1; i < args.length; i++) {

                if (args[i].equalsIgnoreCase("-iteration")) {
                    globalIterationNumber = Integer.parseInt( args[i+1] );
                    logger.info( String.format( "-iteration %d.", globalIterationNumber ) );
                }

                if (args[i].equalsIgnoreCase("-sampleRate")) {
                    iterationSampleRate = Float.parseFloat( args[i+1] );
                    logger.info( String.format( "-sampleRate %.4f.", iterationSampleRate ) );
                }

                if (args[i].equalsIgnoreCase("-sampleSeed")) {
                    sampleSeed = Integer.parseInt( args[i+1] );
                    logger.info( String.format( "-sampleSeed %d.", sampleSeed ) );
                }

            }
                
            if ( globalIterationNumber < 0 ) {
                globalIterationNumber = DEFAULT_ITERATION_NUMBER;
                logger.info( String.format( "no -iteration flag, default value %d used.", globalIterationNumber ) );
            }

            if ( iterationSampleRate < 0 ) {
                iterationSampleRate = DEFAULT_SAMPLE_RATE;
                logger.info( String.format( "no -sampleRate flag, default value %.4f used.", iterationSampleRate ) );
            }

            if ( sampleSeed < 0 ) {
                sampleSeed = DEFAULT_SAMPLE_SEED;
                logger.info( String.format( "no -sampleSeed flag, default value %d used.", sampleSeed ) );
            }

        }


        String baseName;
        if ( args[0].endsWith(".properties") ) {
            int index = args[0].indexOf(".properties");
            baseName = args[0].substring(0, index);
        }
        else {
            baseName = args[0];
        }


        // create an instance of this class for main() to use.
        MtcTourBasedModel mainObject = new MtcTourBasedModel( rb, baseName, globalIterationNumber, iterationSampleRate, sampleSeed );

        // run tour based models
        try {

            logger.info ("starting tour based model.");
            mainObject.runTourBasedModel();

        }
        catch ( RuntimeException e ) {
            logger.error ( "RuntimeException caught in com.pb.mtc.ctramp.TourBasedModel.main() -- exiting.", e );
            System.exit(2);
        }


        logger.info ("");
        logger.info ("");
        logger.info ("MTC Tour Based Model finished in " + ((System.currentTimeMillis() - startTime) / 60000.0) + " minutes.");

        System.exit(0);
    }
}
