package com.pb.mtc.ctramp;

import gnu.cajo.invoke.Remote;
import gnu.cajo.utils.ItemServer;

import java.net.UnknownHostException;
import java.rmi.RemoteException;
import java.util.HashMap;
import java.util.MissingResourceException;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;
import org.jppf.client.JPPFClient;

import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.util.ObjectUtil;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManager;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.HouseholdDataManagerRmi;
import com.pb.models.ctramp.HouseholdDataWriter;
import com.pb.models.ctramp.MatrixDataServer;
import com.pb.models.ctramp.MatrixDataServerRmi;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataHandler;
import com.pb.models.ctramp.jppf.CtrampApplication;
import com.pb.models.ctramp.jppf.HouseholdChoiceModelRunner;
import com.pb.models.ctramp.jppf.HouseholdIndNonManDestChoiceModel;
import com.pb.models.ctramp.jppf.HouseholdJointDestChoiceModel;
import com.pb.models.ctramp.jppf.HouseholdSubTourDestChoiceModel;
import com.pb.models.ctramp.jppf.ModeChoiceModel;
import com.pb.models.ctramp.jppf.UsualWorkSchoolLocationChoiceModel;
import com.pb.mtc.ctramp.MtcModelOutputReader.HouseholdFileAttributes;

public class MTCCreateLogsums {


//	private BuildAccessibilities                       aggAcc;
	private JPPFClient 								   jppfClient;
	private static Logger      logger                  = Logger.getLogger(MTCCreateLogsums.class);
	private HouseholdDataManagerIf householdDataManager;
	private HashMap<String,String> propertyMap;
	private ResourceBundle resourceBundle;
    // are used if no command line arguments are specified.
    private int                globalIterationNumber        = 0;
    private float              iterationSampleRate          = 0f;
    private int                sampleSeed                   = 0;
    private MtcModelStructure modelStructure;
    private MtcCtrampDmuFactory dmuFactory;
    private MatrixDataServerIf ms;
    private MtcModelOutputReader modelOutputReader;
    private TazDataHandler tazDataHandler;    

    //Joint tour
    private ModeChoiceModel jointTourMCModel = null;
	private HouseholdJointDestChoiceModel jointTourDCModel = null;
	
	//Individual non-mandatory tour setup
	private ModeChoiceModel individualNonMandatoryTourMCModel = null;
	private HouseholdIndNonManDestChoiceModel individualTourDCModel = null;
	//At-work sub-tour setup
	private ModeChoiceModel atWorkTourMCModel = null;
	private HouseholdSubTourDestChoiceModel atWorkTourDCModel = null;
    
    public static final int MATRIX_DATA_SERVER_PORT = 1171;
    public static final String PROPERTIES_REREAD_MATRIX_DATA_ON_RESTART = "RunModel.RereadMatrixDataOnRestart"; 
   /**
     * Constructor.
     * 
     * @param propertiesFile
     * @param globalIterationNumber
     * @param globalSampleRate
     * @param sampleSeed
     */
	public MTCCreateLogsums(String propertiesFile, int globalIterationNumber, float globalSampleRate, int sampleSeed){
		
		this.resourceBundle = ResourceBundle.getBundle(propertiesFile);
		propertyMap = ResourceUtil.getResourceBundleAsHashMap ( propertiesFile);
	    this.globalIterationNumber = globalIterationNumber;
	    this.iterationSampleRate = globalSampleRate;
	    this.sampleSeed = sampleSeed;
	 
	}
	
	/**
	 * Initialize data members
	 */
	public void initialize(){
		
    	startMatrixServer(propertyMap);
        String projectDirectory = ResourceUtil.getProperty( resourceBundle, CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        tazDataHandler = new MtcTazDataHandler( resourceBundle, projectDirectory );

        // create modelStructure object
        modelStructure = new MtcModelStructure();

		householdDataManager = getHouseholdDataManager();
	
		// create a factory object to pass to various model components from which
        // they can create DMU objects
        dmuFactory = new MtcCtrampDmuFactory(tazDataHandler, modelStructure);

        modelOutputReader = new MtcModelOutputReader(propertyMap,modelStructure, globalIterationNumber);
	/*
		//Joint tour setup
		jointTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.JOINT_NON_MANDATORY_CATEGORY, dmuFactory,tazDataHandler );
		jointTourDCModel = new HouseholdJointDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, jointTourMCModel );

		//Individual non-mandatory tour setup
		individualNonMandatoryTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY, dmuFactory, tazDataHandler );
		individualTourDCModel = new HouseholdIndNonManDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, individualNonMandatoryTourMCModel );

		//At-work sub-tour setup
		atWorkTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.AT_WORK_CATEGORY, dmuFactory, tazDataHandler );
		atWorkTourDCModel = new HouseholdSubTourDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, atWorkTourMCModel );
*/
	
	
	}
	
	
	/**
	 * Run all components.
	 * 
	 */
	public void run(){
		
		initialize();
		readModelOutputsAndCreateTours();
		createWorkLogsums();
		createNonWorkLogsums();
		
        HouseholdDataWriter dataWriter = new HouseholdDataWriter( resourceBundle, modelStructure, tazDataHandler, dmuFactory, 3 );
        dataWriter.writeDataToFiles(householdDataManager);
  
	}
	
	/**
	 * Read the model outputs and create tours.
	 */
	public void readModelOutputsAndCreateTours(){
		
		modelOutputReader.readHouseholdDataOutput();
		modelOutputReader.readPersonDataOutput();
		modelOutputReader.readTourDataOutput();
		
		Household[] households = householdDataManager.getHhArray();
		for(Household household : households){
			
			modelOutputReader.setHouseholdAndPersonAttributes(household);
			
			if(modelOutputReader.hasJointTourFile())
				modelOutputReader.createJointTours(household);
			
			if(modelOutputReader.hasIndividualTourFile())
				modelOutputReader.createIndividualTours(household);
		}
		householdDataManager.setHhArray(households);
	}
	
	
	
	/**
	 * Calculate and write work destination choice logsums for the synthetic population.
	 * 
	 * @param propertyMap
	 */
	public void createWorkLogsums(){
        
        jppfClient = new JPPFClient();
        // create an object for calculating destination choice attraction size terms and managing shadow price calculations.
        DestChoiceSize dcSizeObj = new DestChoiceSize( modelStructure, tazDataHandler );
     	
        // new the usual school and location choice model object
        if(ms==null){
        	logger.error("Error:Matrix server is null");
        	throw new RuntimeException();
        }
        
        
        UsualWorkSchoolLocationChoiceModel usualWorkSchoolLocationChoiceModel = new UsualWorkSchoolLocationChoiceModel(
                resourceBundle, "none", jppfClient, modelStructure, ms, tazDataHandler, dcSizeObj, dmuFactory);

        // run the model
        logger.info ( "starting usual work and school location choice.");
        usualWorkSchoolLocationChoiceModel.runSchoolAndLocationChoiceModel(householdDataManager);
        logger.info ( "finished with usual work and school location choice.");


	}
	
	public void createNonWorkLogsums(){
	/*	
		//Joint tour setup
		ModeChoiceModel jointTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.JOINT_NON_MANDATORY_CATEGORY, dmuFactory,tazDataHandler );
		HouseholdJointDestChoiceModel jointTourDCModel = new HouseholdJointDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, jointTourMCModel );

		//Individual non-mandatory tour setup
		ModeChoiceModel individualNonMandatoryTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY, dmuFactory, tazDataHandler );
		HouseholdIndNonManDestChoiceModel individualTourDCModel = new HouseholdIndNonManDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, individualNonMandatoryTourMCModel );

		//At-work sub-tour setup
		ModeChoiceModel atWorkTourMCModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.AT_WORK_CATEGORY, dmuFactory, tazDataHandler );
		HouseholdSubTourDestChoiceModel atWorkTourDCModel = new HouseholdSubTourDestChoiceModel( propertyMap, modelStructure, tazDataHandler, dmuFactory, atWorkTourMCModel );
		
        Household[] householdArray = householdDataManager.getHhArray();

        for(Household household : householdArray){
        	
        	jointTourDCModel.applyModel( household );
        	individualTourDCModel.applyModel( household );
        	atWorkTourDCModel.applyModel( household );
        	
        }
	*/	
        HouseholdChoiceModelRunner runner = new HouseholdChoiceModelRunner( propertyMap, jppfClient, "False", householdDataManager, ms, modelStructure, tazDataHandler, dmuFactory );
        runner.runHouseholdChoiceModels();

	}
	

	
	/**
	 * Create the household data manager. Based on the code in MTCTM2TourBasedModel.runTourBasedModel() 
	 * @return The household data manager interface.
	 */
	public HouseholdDataManagerIf getHouseholdDataManager( ){

		
        boolean localHandlers = false;

       String testString;
 
        HouseholdDataManagerIf householdDataManager;
        String hhHandlerAddress = "";
        int hhServerPort = 0;
        try
        {
            // get household server address. if none is specified a local server in
            // the current process will be started.
            hhHandlerAddress = resourceBundle.getString("RunModel.HouseholdServerAddress");
            try
            {
                // get household server port.
                hhServerPort = Integer.parseInt(resourceBundle.getString("RunModel.HouseholdServerPort"));
                localHandlers = false;
            } catch (MissingResourceException e)
            {
                // if no household data server address entry is found, the object
                // will be created in the local process
                localHandlers = true;
            }
        } catch (MissingResourceException e)
        {
            localHandlers = true;
        }


        try
        {

            if (localHandlers)
            {

                // create a new local instance of the household array manager
                householdDataManager = new MtcHouseholdDataManager();
                householdDataManager.setPropertyFileValues( propertyMap );

                // have the household data manager read the synthetic population files and apply its tables to objects mapping method.
                String inputHouseholdFileName = resourceBundle.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_HH );
                String inputPersonFileName = resourceBundle.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_PERS );
                householdDataManager.setHouseholdSampleRate( iterationSampleRate, sampleSeed );
                householdDataManager.setupHouseholdDataManager( modelStructure, tazDataHandler, inputHouseholdFileName, inputPersonFileName );

            } else
            {

                householdDataManager = new HouseholdDataManagerRmi( hhHandlerAddress, hhServerPort, MtcHouseholdDataManager.HH_DATA_SERVER_NAME );
                testString = householdDataManager.testRemote();
                logger.info ( "HouseholdDataManager test: " + testString );

                householdDataManager.setPropertyFileValues( propertyMap );

            }
		
            householdDataManager.setDebugHhIdsFromHashmap ();

            String inputHouseholdFileName = resourceBundle.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_HH );
            String inputPersonFileName = resourceBundle.getString( HouseholdDataManager.PROPERTIES_SYNPOP_INPUT_PERS );
            householdDataManager.setHouseholdSampleRate( iterationSampleRate, sampleSeed );
            householdDataManager.setupHouseholdDataManager( modelStructure, tazDataHandler, inputHouseholdFileName, inputPersonFileName );

        }catch (Exception e)
        {

            logger.error(String
                    .format("Exception caught setting up household data manager."), e);
            throw new RuntimeException();

        }

        return householdDataManager;
	}
	
	
	/** 
	 * Start a new matrix server connection.
	 * 
	 * @param properties
	 */
	private void startMatrixServer(HashMap<String, String> properties) {
        String matrixServerAddress = "";
        int serverPort = 0;
        try {
            // get matrix server address.  if "none" is specified, no server will be started, and matrix io will ocurr within the current process.
            matrixServerAddress = resourceBundle.getString( "RunModel.MatrixServerAddress" );
            try {
                // get matrix server port.
                serverPort = Integer.parseInt( resourceBundle.getString( "RunModel.MatrixServerPort" ) );
            }
            catch ( MissingResourceException e ) {
                // if no matrix server address entry is found, leave undefined -- it's either not needed or show could create an error.
            }
        }
        catch ( MissingResourceException e ) {
            // if no matrix server address entry is found, set to localhost, and a separate matrix io process will be started on localhost.
            matrixServerAddress = "localhost";
            serverPort = MATRIX_DATA_SERVER_PORT;
        }


        MatrixDataServer matrixServer = null;

        try {

            if ( ! matrixServerAddress.equalsIgnoreCase("none") ) {

                if ( matrixServerAddress.equalsIgnoreCase("localhost") ) {
                    matrixServer = startMatrixServerProcess( matrixServerAddress, serverPort );
                    ms = matrixServer;
                }
                else {
                    MatrixDataServerRmi mds = new MatrixDataServerRmi( matrixServerAddress, serverPort, MatrixDataServer.MATRIX_DATA_SERVER_NAME );
                    ms = mds;

                    boolean rereadMatrixDataOnRestart = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_REREAD_MATRIX_DATA_ON_RESTART, true);
                    if (rereadMatrixDataOnRestart) ms.clear();
                    //ms.start32BitMatrixIoServer( MatrixType.TPPLUS );
                    
                    MatrixDataManager mdm = MatrixDataManager.getInstance();
                    mdm.setMatrixDataServerObject( ms );
                    
                }

            }


        }
        catch ( Exception e ) {

            if ( matrixServerAddress.equalsIgnoreCase("localhost") ) {
                //matrixServer.stop32BitMatrixIoServer();
            }
            logger.error ( String.format( "exception caught running ctramp model components -- exiting." ), e );
            throw new RuntimeException();

        }
        
	}
	
    private MatrixDataServer startMatrixServerProcess( String serverAddress, int serverPort ) {

        String className = MatrixDataServer.MATRIX_DATA_SERVER_NAME;

        MatrixDataServer matrixServer = new MatrixDataServer();

        // bind this concrete object with the cajo library objects for managing RMI
        try {
            Remote.config( serverAddress, serverPort, null, 0 );
        }
        catch ( UnknownHostException e ) {
            logger.error ( String.format( "UnknownHostException. serverAddress = %s, serverPort = %d -- exiting.", serverAddress, serverPort ), e );
            //matrixServer.stop32BitMatrixIoServer();
            throw new RuntimeException();
        }

        try {
            ItemServer.bind( matrixServer, className );
        }
        catch ( RemoteException e ) {
            logger.error ( String.format( "RemoteException. serverAddress = %s, serverPort = %d -- exiting.", serverAddress, serverPort ), e );
            //matrixServer.stop32BitMatrixIoServer();
            throw new RuntimeException();
        }

        return matrixServer;

    }

	public static void main(String[] args) {
		long startTime = System.currentTimeMillis();
	    int globalIterationNumber = -1;
	    float iterationSampleRate = -1.0f;
	    int sampleSeed = -1;
	        
	    ResourceBundle rb = null;

	    logger.info( String.format( "Generating Logsums from MTC Tour Based Model using CT-RAMP version %s, 22feb2011 build %s", CtrampApplication.VERSION, 2 ) );
	        
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
	        	globalIterationNumber = 1;
	            logger.info( String.format( "no -iteration flag, default value %d used.", globalIterationNumber ) );
	        }

	        if ( iterationSampleRate < 0 ) {
	        	iterationSampleRate = 1;
	            logger.info( String.format( "no -sampleRate flag, default value %.4f used.", iterationSampleRate ) );
	        }

	        if ( sampleSeed < 0 ) {
	        	sampleSeed = 0;
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
	    MTCCreateLogsums mainObject = new MTCCreateLogsums(  args[0], globalIterationNumber, iterationSampleRate, sampleSeed );

	    // Create logsums
	    try {

	    	logger.info ("Creating logsums.");
	            mainObject.run();
	         
	        }
	        catch ( RuntimeException e ) {
	            logger.error ( "RuntimeException caught in com.pb.mtc.ctramp.MTCCreateLogsums.main() -- exiting.", e );
	            System.exit(2);
	        }


	        logger.info ("");
	        logger.info ("");
	        logger.info ("Create MTC Logsums finished in " + ((System.currentTimeMillis() - startTime) / 60000.0) + " minutes.");

	        System.exit(0);

	}

}
