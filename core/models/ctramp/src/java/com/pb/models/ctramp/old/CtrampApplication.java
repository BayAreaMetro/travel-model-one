package com.pb.models.ctramp.old;

import gnu.cajo.invoke.Remote;
import gnu.cajo.utils.ItemServer;

import java.rmi.RemoteException;
import java.util.HashMap;
import java.util.MissingResourceException;
import java.util.ResourceBundle;
import java.io.NotSerializableException;
import java.io.IOException;
import java.net.UnknownHostException;

import org.apache.log4j.Logger;

import com.pb.common.matrix.MatrixType;
import com.pb.common.util.ResourceUtil;
import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.datafile.DataWriter;
import com.pb.common.datafile.DataFile;
import com.pb.common.datafile.DataReader;
import com.pb.models.ctramp.CoordinatedDailyActivityPatternModel;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.JointTourFrequencyModel;
import com.pb.models.ctramp.MatrixDataServer;
import com.pb.models.ctramp.MatrixDataServerRmi;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;
//import com.pb.models.ctramp.jppf.UsualWorkSchoolLocationChoiceModel;
import com.pb.models.synpopV3.PopulationSynthesizer;

 public class CtrampApplication {

     protected transient Logger logger = Logger.getLogger(CtrampApplication.class);

     public static final String PROGRAM_VERSION = "XXMar2008";


     public static final int MATRIX_DATA_SERVER_PORT = 1171;

     public static final boolean UWSL_DEBUG_FILE = false;
     public static final boolean AO_DEBUG_FILE = true;
     public static final boolean CDAP_DEBUG_FILE = false;
     public static final boolean IMTF_DEBUG_FILE = false;
     public static final boolean MTDAD_DEBUG_FILE = false;


     public static final String ALT_FIELD_NAME = "a";
     public static final String START_FIELD_NAME = "start";
     public static final String END_FIELD_NAME = "end";
     public static final int START_HOUR = 5;
     public static final int LAST_HOUR = 23;

     public static final String PROPERTIES_BASE_NAME = "ctramp";
     public static final String PROPERTIES_PROJECT_DIRECTORY = "Project.Directory";

     public static final String SQLITE_DATABASE_FILENAME = "Sqlite.DatabaseFileName";

     public static final String PROPERTIES_RUN_POPSYN                                     = "RunModel.PopulationSynthesizer";
     public static final String PROPERTIES_RUN_WORKSCHOOL_CHOICE                          = "RunModel.UsualWorkAndSchoolLocationChoice";
     public static final String PROPERTIES_RUN_AUTO_OWNERSHIP                             = "RunModel.AutoOwnership";
     public static final String PROPERTIES_RUN_DAILY_ACTIVITY_PATTERN                     = "RunModel.CoordinatedDailyActivityPattern";
     public static final String PROPERTIES_RUN_INDIV_MANDATORY_TOUR_FREQ                  = "RunModel.IndividualMandatoryTourFrequency";
     public static final String PROPERTIES_RUN_MAND_TOUR_DEP_TIME_AND_DUR                 = "RunModel.MandatoryTourDepartureTimeAndDuration";
     public static final String PROPERTIES_RUN_AT_WORK_SUBTOUR_FREQ                       = "RunModel.AtWorkSubTourFrequency";
     public static final String PROPERTIES_RUN_AT_WORK_SUBTOUR_LOCATION_CHOICE            = "RunModel.AtWorkSubTourLocationChoice";
     public static final String PROPERTIES_RUN_AT_WORK_SUBTOUR_DEP_TIME_AND_DUR           = "RunModel.AtWorkSubTourDepartureTimeAndDuration";
     public static final String PROPERTIES_RUN_JOINT_TOUR_FREQ                            = "RunModel.JointTourFrequency";
     public static final String PROPERTIES_RUN_JOINT_LOCATION_CHOICE                      = "RunModel.JointTourLocationChoice";
     public static final String PROPERTIES_RUN_JOINT_TOUR_DEP_TIME_AND_DUR                = "RunModel.JointTourDepartureTimeAndDuration";
     public static final String PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_FREQ              = "RunModel.IndividualNonMandatoryTourFrequency";
     public static final String PROPERTIES_RUN_INDIV_NON_MANDATORY_LOCATION_CHOICE        = "RunModel.IndividualNonMandatoryTourLocationChoice";
     public static final String PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_DEP_TIME_AND_DUR  = "RunModel.IndividualNonMandatoryTourDepartureTimeAndDuration";
     public static final String PROPERTIES_RUN_STOP_FREQUENCY                             = "RunModel.StopFrequency";
     public static final String PROPERTIES_RUN_STOP_LOCATION                              = "RunModel.StopLocation";


     public static final String PROPERTIES_UEC_AUTO_OWNERSHIP                = "UecFile.AutoOwnership";
     public static final String PROPERTIES_UEC_DAILY_ACTIVITY_PATTERN        = "UecFile.CoordinatedDailyActivityPattern";
     public static final String PROPERTIES_UEC_INDIV_MANDATORY_TOUR_FREQ     = "UecFile.IndividualMandatoryTourFrequency";
     public static final String PROPERTIES_UEC_MAND_TOUR_DEP_TIME_AND_DUR    = "UecFile.TourDepartureTimeAndDuration";
     public static final String PROPERTIES_UEC_INDIV_NON_MANDATORY_TOUR_FREQ = "UecFile.IndividualNonMandatoryTourFrequency";

     // TODO eventually move to model-specific structure object
     public static final int TOUR_MODE_CHOICE_WORK_MODEL_UEC_PAGE         = 1;
     public static final int TOUR_MODE_CHOICE_UNIVERSITY_MODEL_UEC_PAGE   = 2;
     public static final int TOUR_MODE_CHOICE_HIGH_SCHOOL_MODEL_UEC_PAGE  = 3;
     public static final int TOUR_MODE_CHOICE_GRADE_SCHOOL_MODEL_UEC_PAGE = 4;

     // TODO eventually move to model-specific model structure object
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_WORK_MODEL_UEC_PAGE     = 1;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_WORK_DEPARTURE_UEC_PAGE = 2;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_WORK_DURATION_UEC_PAGE  = 3;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_WORK_ARRIVAL_UEC_PAGE   = 4;

     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_SCHOOL_MODEL_UEC_PAGE     = 5;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_SCHOOL_DEPARTURE_UEC_PAGE = 6;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_SCHOOL_DURATION_UEC_PAGE  = 7;
     public static final int MANDATORY_TOUR_DEP_TIME_AND_DUR_SCHOOL_ARRIVAL_UEC_PAGE   = 8;

     public static final String PROPERTIES_SCHEDULING_NUMBER_OF_TIME_PERIODS = "Scheduling.NumberOfTimePeriods";
     public static final String PROPERTIES_SCHEDULING_FIRST_TIME_PERIOD = "Scheduling.FirstTimePeriod";


     static final String PROPERTIES_HOUSEHOLD_DISK_OBJECT_FILE_NAME = "Households.disk.object.base.name";
     static final String PROPERTIES_HOUSEHOLD_DISK_OBJECT_KEY = "Read.HouseholdDiskObjectFile";
     static final String PROPERTIES_TAZ_DISK_OBJECT_FILE_NAME = "TAZ.disk.object.base.name";
     static final String PROPERTIES_TAZ_DISK_OBJECT_KEY = "Read.TAZDiskObjectFile";

     public static final String PROPERTIES_OUTPUT_WRITE_SWITCH = "CTRAMP.Output.WriteToDiskSwitch";
     public static final String PROPERTIES_OUTPUT_HOUSEHOLD_FILE = "CTRAMP.Output.HouseholdFile";
     public static final String PROPERTIES_OUTPUT_PERSON_FILE = "CTRAMP.Output.PersonFile";

     public static final String PROPERTIES_WRITE_DATA_TO_FILE = "Results.WriteDataToFiles";
     public static final String PROPERTIES_WRITE_DATA_TO_DATABASE = "Results.WriteDataToDatabase";

     private ResourceBundle resourceBundle;

     private MatrixDataServerIf ms;

     private ModelStructure modelStructure;
     private TazDataIf tazDataManager;
     protected String projectDirectory;
     protected String hhDiskObjectFile;
     protected String hhDiskObjectKey;
     protected String tazDiskObjectFile;
     protected String tazDiskObjectKey;


     public CtrampApplication( ResourceBundle rb ){
         resourceBundle = rb;
         projectDirectory = ResourceUtil.getProperty(resourceBundle, PROPERTIES_PROJECT_DIRECTORY);
     }



     public void setupModels( ModelStructure modelStructure, TazDataIf tazDataManager ){

         this.modelStructure = modelStructure;
         this.tazDataManager = tazDataManager;

         hhDiskObjectFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_HOUSEHOLD_DISK_OBJECT_FILE_NAME);
         if ( hhDiskObjectFile != null )
             hhDiskObjectFile = projectDirectory + hhDiskObjectFile;
         hhDiskObjectKey = ResourceUtil.getProperty(resourceBundle, PROPERTIES_HOUSEHOLD_DISK_OBJECT_KEY);

         tazDiskObjectFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_TAZ_DISK_OBJECT_FILE_NAME);
         if ( tazDiskObjectFile != null )
             tazDiskObjectFile = projectDirectory + tazDiskObjectFile;
         tazDiskObjectKey = ResourceUtil.getProperty(resourceBundle, PROPERTIES_TAZ_DISK_OBJECT_KEY);

     }

     
     public void runPopulationSynthesizer( PopulationSynthesizer populationSynthesizer ){

         // run population synthesizer
         boolean runModelPopulationSynthesizer = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_POPSYN);
         if(runModelPopulationSynthesizer){
             populationSynthesizer.runPopulationSynthesizer();
         }

     }


     public void runModels( HouseholdDataManagerIf householdDataManager, CtrampDmuFactoryIf dmuFactory ){


         
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
                 // if no matrix server address entry is found, leave undefined -- it's eithe not needed or show could create an error.
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
                     MatrixDataServerRmi mds = new MatrixDataServerRmi( matrixServerAddress, serverPort, matrixServerAddress );
                     ms = mds;
                     //MatrixDataManager mdm = MatrixDataManager.getInstance();
                     //mdm.setMatrixDataServerObject( mds );
                 }

             }


         }
         catch ( Exception e ) {

             if ( matrixServerAddress.equalsIgnoreCase("localhost") ) {
                 matrixServer.stop32BitMatrixIoServer();
             }
             logger.error ( String.format( "exception caught running ctramp model components -- exiting." ), e );
             throw new RuntimeException();

         }
         
         
         
         HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle);
         
         
         // run usual workplace/school location model if requested
         boolean runUsualWorkSchoolChoiceModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_WORKSCHOOL_CHOICE);
         if(runUsualWorkSchoolChoiceModel){

             // create an object for calculating destination choice attraction size terms and managing shadow price calculations.
             DestChoiceSize dcSizeObj = new DestChoiceSize( modelStructure, tazDataManager );
             
             // new the usual school and location choice model object
             UsualWorkSchoolLocationChoiceModel usualWorkSchoolLocationChoiceModel = new UsualWorkSchoolLocationChoiceModel(resourceBundle, modelStructure, ms, tazDataManager, dcSizeObj, dmuFactory );

             //householdDataManager.logPersonSummary();            

             // run the model
             logger.info ( "starting usual work and school location choice.");
             usualWorkSchoolLocationChoiceModel.runSchoolAndLocationChoiceModel(householdDataManager);
             logger.info ( "finished with usual work and school location choice.");

             usualWorkSchoolLocationChoiceModel.saveResults(householdDataManager, projectDirectory);

             // write a disk object fle for the householdDataManager, in case we want to restart from the next step.
             if ( hhDiskObjectFile != null ) {
                 String hhFileName = hhDiskObjectFile + "_ao";
                 createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "ao" );
             }
             if ( tazDiskObjectFile != null ) {
                 String tazFileName = tazDiskObjectFile + "_ao";
                 createSerializedObjectInFileFromObject( tazDataManager, tazFileName, "ao" );
             }
             
         } // usual work and school location choice


         if ( tazDiskObjectKey.equalsIgnoreCase("ao") ) {
             String doFileName = tazDiskObjectFile + "_ao";
             tazDataManager = (TazDataIf) createObjectFromSerializedObjectInFile( tazDataManager, doFileName, "ao" );
         }

         // run the auto ownership model if requested
         boolean runAutoOwnershipModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AUTO_OWNERSHIP);
         if(runAutoOwnershipModel){

             if ( hhDiskObjectKey.equalsIgnoreCase("ao") ) {
                 String doFileName = hhDiskObjectFile + "_ao";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "ao" );
                 householdDataManager.resetAoRandom();
             }


             // locate the UEC
             String autoOwnershipUecFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_AUTO_OWNERSHIP);
             autoOwnershipUecFile = projectDirectory + autoOwnershipUecFile;

             // create the model
             AutoOwnershipChoiceModel autoOwnershipModel = new AutoOwnershipChoiceModel( autoOwnershipUecFile, resourceBundle, modelStructure);

             // apply the model
             autoOwnershipModel.applyModel(householdDataManager);

             // log the results
             autoOwnershipModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             autoOwnershipModel.logResults();

             // write a disk object fle for the householdDataManager, in case we want to restart from the next step.
             String hhFileName = hhDiskObjectFile + "_cdap";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "cdap" );

         }

         // TODO auto ownership task?

         // TODO cdap here
         // TODO cdap task?

         // run the coordinated daily acitivity pattern model if requested
         boolean runCoordinatedDailyActivityPatternModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_DAILY_ACTIVITY_PATTERN);
         if(runCoordinatedDailyActivityPatternModel){


             if ( hhDiskObjectKey.equalsIgnoreCase("cdap") ) {
                 String doFileName = hhDiskObjectFile + "_cdap";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "cdap" );
                 householdDataManager.resetCdapRandom();
             }


             // locate the UEC
             String cdapUecFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_DAILY_ACTIVITY_PATTERN);
             cdapUecFile = projectDirectory + cdapUecFile;

             // create the model
             CoordinatedDailyActivityPatternModel cdapModel = new CoordinatedDailyActivityPatternModel(cdapUecFile, resourceBundle);

             // apply the model
             cdapModel.applyModel(householdDataManager);

             // log the results
             cdapModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             cdapModel.logResults();

             // write a disk object fle for the householdDataManager, in case we want to restart from the next step.
             String hhFileName = hhDiskObjectFile + "_imtf";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "imtf" );
         }




         // Individual Mandatory Tour Frequency Model
         boolean runIndividualMandatoryTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_MANDATORY_TOUR_FREQ);
         if(runIndividualMandatoryTourFrequencyModel){


             //TODO: results of CDAP model should be already populated in Household objects
             //TODO: we need some consistency checking and error handling that's part of an overall restore/restart and result handling strategy

             // check that Coordinated Daily Activity Pattern data is in the household data manager
//             if(!householdDataManager.isThisFieldStoredInHouseholdTable(HouseholdDataManager.MODELED_CDAP_ACTIVITY_PATTERN_FIELD_NAME)){
//
//                 logger.fatal("Coordinated Daily Activity Pattern model must be executed before the ");
//                 logger.fatal("Individual Mandatory Tour Frequency model.");
//                 throw new RuntimeException();
//             }


             if ( hhDiskObjectKey.equalsIgnoreCase("imtf") ) {
                 String doFileName = hhDiskObjectFile + "_imtf";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "imtf" );
                 householdDataManager.resetImtfRandom();
             }


             // feedback
             logger.info("Applying Individual Mandatory Tour Frequency Model");

             // locate the UEC
             String uecFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_INDIV_MANDATORY_TOUR_FREQ);
             uecFile = projectDirectory + uecFile;

             // create the model
             IndividualMandatoryTourFrequencyModel model = new IndividualMandatoryTourFrequencyModel( dmuFactory.getIndividualMandatoryTourFrequencyDMU(), uecFile, resourceBundle, tazDataManager, modelStructure );

             // apply the model
             model.applyModel(householdDataManager);

             // log the results
             model.logResults();

             // write a disk object fle for the householdDataManager, in case we want to restart from the next step.
             String hhFileName = hhDiskObjectFile + "_imtod";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "imtod" );

         }



         // Mandatory Tour Departure Time, Duration and Mode Model,
         boolean runMandatoryTourDepartureTimeAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_MAND_TOUR_DEP_TIME_AND_DUR);
         if(runMandatoryTourDepartureTimeAndDurationModel){

             if ( hhDiskObjectKey.equalsIgnoreCase("imtod") ) {
                 String doFileName = hhDiskObjectFile + "_imtod";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "imtod" );
                 householdDataManager.resetImtodRandom();
             }


             // create the model
             IndividualMandatoryTourDepartureAndDurationTime mtdadModel = new IndividualMandatoryTourDepartureAndDurationTime( projectDirectory, dmuFactory.getTourDepartureTimeAndDurationDMU(), dmuFactory.getModeChoiceDMU(), modelStructure, tazDataManager );

             // setup model object
             mtdadModel.setUpModels( propertyMap, projectDirectory, ModelStructure.MANDATORY_CATEGORY );

             // apply the model
             mtdadModel.applyModel( householdDataManager );

             // save the results
             mtdadModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             mtdadModel.logResults();

             String hhFileName = hhDiskObjectFile + "_awf";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "awf" );
         }



         // At-work subtour frequency, to be applied for work tours
         boolean runAtWorkSubTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_FREQ);
         if(runAtWorkSubTourFrequencyModel){

             if ( hhDiskObjectKey.equalsIgnoreCase("awf") ) {
                 String doFileName = hhDiskObjectFile + "_awf";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "awf" );
                 householdDataManager.resetAwfRandom();
             }


             // create the model
             AtWorkSubtourFrequencyModel awfModel = new AtWorkSubtourFrequencyModel( projectDirectory, resourceBundle, dmuFactory.getAtWorkSubtourFrequencyDMU(), tazDataManager, modelStructure );

             // apply the model
             awfModel.applyModel( householdDataManager );

             // log the results
             awfModel.logResults();

             String hhFileName = hhDiskObjectFile + "_awl";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "awl" );
         }



         // run at-work subtour location choice model if requested
         boolean runAtWorkSubtourLocationChoiceModel = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_LOCATION_CHOICE );
         if( runAtWorkSubtourLocationChoiceModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("awl") ) {
                 String doFileName = hhDiskObjectFile + "_awl";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "awl" );
                 householdDataManager.resetAwlRandom();
             }


             // new the usual school and location choice model object
             AtWorkSubtourLocationChoiceModel atWorkSubtourLocationChoiceModel = new AtWorkSubtourLocationChoiceModel(resourceBundle, ms, modelStructure, tazDataManager, dmuFactory );

             // run the model
             atWorkSubtourLocationChoiceModel.runAtWorkSubtourLocationChoiceModel(householdDataManager);

             String hhFileName = hhDiskObjectFile + "_awtod";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "awtod" );
         }



         // At-work subtour Departure Time, Duration and Mode Choice Model
         boolean runAtWorkSubtourDepartureTimeAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_DEP_TIME_AND_DUR);
         if( runAtWorkSubtourDepartureTimeAndDurationModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("awtod") ) {
                 String doFileName = hhDiskObjectFile + "_awtod";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "awtod" );
                 householdDataManager.resetAwtodRandom();
             }


             // create the model
             AtWorkSubtourDepartureAndDurationTime awtodModel = new AtWorkSubtourDepartureAndDurationTime( projectDirectory, dmuFactory.getTourDepartureTimeAndDurationDMU(), dmuFactory.getModeChoiceDMU(), modelStructure, tazDataManager );

             // setup model object
             awtodModel.setUpModels( propertyMap, projectDirectory, ModelStructure.AT_WORK_CATEGORY );

             // apply the model
             awtodModel.applyModel( householdDataManager );

             // write out the results
             awtodModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             awtodModel.logResults();

             String hhFileName = hhDiskObjectFile + "_jtf";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "jtf" );
         }




         // Joint Tour Frequency Model
         boolean runJointTourFrequencyModel = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_RUN_JOINT_TOUR_FREQ );
         if( runJointTourFrequencyModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("jtf") ) {
                 String doFileName = hhDiskObjectFile + "_jtf";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "jtf" );
                 householdDataManager.resetJtfRandom();
             }


             // create the model
             JointTourFrequencyModel jtfModel = new JointTourFrequencyModel( projectDirectory, dmuFactory.getJointTourFrequencyDMU(), modelStructure, tazDataManager );

             // setup model object
             jtfModel.setUpModels( resourceBundle, projectDirectory );

             // apply the model
             jtfModel.applyModel( householdDataManager );

             // log the results
             jtfModel.logResults();

             // write a disk object fle for the householdDataManager, in case we want to restart from the next step.
             String hhFileName = hhDiskObjectFile + "_jtl";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "jtl" );
         }



         // run joint tour location choice model if requested
         boolean runJointTourLocationChoiceModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_JOINT_LOCATION_CHOICE);
         if( runJointTourLocationChoiceModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("jtl") ) {
                 String doFileName = hhDiskObjectFile + "_jtl";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "jtl" );
                 householdDataManager.resetJtlRandom();
             }


             // new the usual school and location choice model object
             JointTourLocationChoiceModel jointTourLocationChoiceModel = new JointTourLocationChoiceModel(resourceBundle, ms, modelStructure, tazDataManager, dmuFactory );

             // run the model
             jointTourLocationChoiceModel.runJointTourLocationChoiceModel(householdDataManager);

             String hhFileName = hhDiskObjectFile + "_jtod";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "jtod" );
         } // joint tour location choice



         // Joint Tour Departure Time, Duration and Mode Model
         boolean runJointTourDepartureTimeAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_JOINT_TOUR_DEP_TIME_AND_DUR);
         if( runJointTourDepartureTimeAndDurationModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("jtod") ) {
                 String doFileName = hhDiskObjectFile + "_jtod";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "jtod" );
                 householdDataManager.resetJtodRandom();
             }


             // create the model
             JointTourDepartureAndDurationTime jtdadModel = new JointTourDepartureAndDurationTime( projectDirectory, dmuFactory.getTourDepartureTimeAndDurationDMU(), dmuFactory.getModeChoiceDMU(), modelStructure, tazDataManager );

             // setup model object
             jtdadModel.setUpModels( propertyMap, projectDirectory, ModelStructure.JOINT_NON_MANDATORY_CATEGORY );

             // apply the model
             jtdadModel.applyModel( householdDataManager );

             // write out the results
             jtdadModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             jtdadModel.logResults();

             String hhFileName = hhDiskObjectFile + "_inmtf";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "inmtf" );
         }



         // Individual Non-Mandatory Tour Frequency Model
         boolean runIndividualNonMandatoryTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_FREQ);
         if(runIndividualNonMandatoryTourFrequencyModel){

             if ( hhDiskObjectKey.equalsIgnoreCase("inmtf") ) {
                 String doFileName = hhDiskObjectFile + "_inmtf";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "inmtf" );
                 householdDataManager.resetInmtfRandom();
             }


             // feedback
             logger.info("Applying Individual Non-Mandatory Tour Frequency Model");

             // locate the UEC
             String uecFile = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_INDIV_NON_MANDATORY_TOUR_FREQ);
             uecFile = projectDirectory + uecFile;

             // create the model
             IndividualNonMandatoryTourFrequencyModel model = new IndividualNonMandatoryTourFrequencyModel( dmuFactory.getIndividualNonMandatoryTourFrequencyDMU(), uecFile, resourceBundle, tazDataManager, modelStructure );

             // apply the model
             model.applyModel(householdDataManager);

             // log the results
             model.logResults();

             String hhFileName = hhDiskObjectFile + "_inmtl";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "inmtl" );
         }



         // run individual non-mandatory tour location choice model if requested
         boolean runIndividualNonMandatoryTourLocationChoiceModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_LOCATION_CHOICE);
         if( runIndividualNonMandatoryTourLocationChoiceModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("inmtl") ) {
                 String doFileName = hhDiskObjectFile + "_inmtl";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "inmtl" );
                 householdDataManager.resetInmtlRandom();
             }


             // new the usual school and location choice model object
             IndividualNonMandatoryTourLocationChoiceModel indivNonMandatoryTourLocationChoiceModel = new IndividualNonMandatoryTourLocationChoiceModel(resourceBundle, ms, modelStructure, tazDataManager, dmuFactory );

             // run the model
             indivNonMandatoryTourLocationChoiceModel.runIndivNonMandatoryTourLocationChoiceModel(householdDataManager);

             String hhFileName = hhDiskObjectFile + "_inmtod";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "inmtod" );
         } // individual non-mandatory tour location choice




         // individual non-mandatory Tour Departure Time, Duration and Mode Model
         boolean runIndividualNonMandatoyTourDepartureTimeAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_DEP_TIME_AND_DUR);
         if( runIndividualNonMandatoyTourDepartureTimeAndDurationModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("inmtod") ) {
                 String doFileName = hhDiskObjectFile + "_inmtod";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "inmtod" );
                 householdDataManager.resetInmtodRandom();
             }


             // create the model
             IndividualNonMandatoryTourDepartureAndDurationTime itdadModel = new IndividualNonMandatoryTourDepartureAndDurationTime( projectDirectory, dmuFactory.getTourDepartureTimeAndDurationDMU(), dmuFactory.getModeChoiceDMU(), modelStructure, tazDataManager );

             // setup model object
             itdadModel.setUpModels( propertyMap, projectDirectory, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY );

             // apply the model
             itdadModel.applyModel( householdDataManager );

             // write out the results
             itdadModel.saveResults(householdDataManager, projectDirectory);

             // log the results
             itdadModel.logResults();

             String hhFileName = hhDiskObjectFile + "_stf";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "stf" );
         }




         // Stop Frequency Model
         boolean runStopFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_STOP_FREQUENCY);
         if( runStopFrequencyModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("stf") ) {
                 String doFileName = hhDiskObjectFile + "_stf";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "stf" );
                 householdDataManager.resetStfRandom();
             }


             // create the model
             StopFrequencyModel stfModel = new StopFrequencyModel( projectDirectory, resourceBundle, dmuFactory.getStopFrequencyDMU(), tazDataManager, modelStructure );

             // apply the model
             stfModel.applyModel( householdDataManager );

             // log the results
             stfModel.logResults();

             String hhFileName = hhDiskObjectFile + "_stl";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "stl" );
         }



         // Stop Location Model
         boolean runStopLocationModel = false;
         try {
             runStopLocationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_STOP_LOCATION);
         }
         catch ( Exception e ) {
             // if exception is caught while getting property file value, then boolean flag remains false
         }
         if( runStopLocationModel ){

             if ( hhDiskObjectKey.equalsIgnoreCase("stl") ) {
                 String doFileName = hhDiskObjectFile + "_stl";
                 householdDataManager = (HouseholdDataManagerIf) createObjectFromSerializedObjectInFile( householdDataManager, doFileName, "stl" );
                 householdDataManager.resetStlRandom();
                 householdDataManager.setDebugHhIdsFromHashmap();
                 householdDataManager.setTraceHouseholdSet();
             }


             // create the model
             StopLocationModel stlModel = new StopLocationModel( projectDirectory, resourceBundle, dmuFactory.getStopLocationDMU(), dmuFactory.getTripModeChoiceDMU(), tazDataManager , modelStructure);

             // apply the model
             stlModel.applyModel( householdDataManager );

             // write out the results
             stlModel.saveResults(householdDataManager, resourceBundle);

             // log the results
             stlModel.logResults();

             String hhFileName = hhDiskObjectFile + "_end";
             createSerializedObjectInFileFromObject( householdDataManager, hhFileName, "end" );
         }



         /*
         
         boolean writeTextFileFlag = false;
         boolean writeSqliteFlag = false;
         try {
             writeTextFileFlag = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_WRITE_DATA_TO_FILE);
         }
         catch ( MissingResourceException e ) {
             // if exception is caught while getting property file value, then boolean flag remains false
         }
         try {
             writeSqliteFlag = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_WRITE_DATA_TO_FILE);
         }
         catch ( MissingResourceException e ) {
             // if exception is caught while getting property file value, then boolean flag remains false
         }

         HouseholdDataWriter dataWriter = null;
         if ( writeTextFileFlag || writeSqliteFlag ) {
             dataWriter = new HouseholdDataWriter(resourceBundle,modelStructure,dmuFactory);

             if ( writeTextFileFlag )
                dataWriter.writeDataToFiles(householdDataManager);
             if ( writeSqliteFlag ) {
                 String dbFilename = "";
                 try {
                     dbFilename = resourceBundle.getString(SQLITE_DATABASE_FILENAME);
                     dataWriter.writeDataToDatabase(householdDataManager, dbFilename);
                 }
                 catch ( MissingResourceException e ) {
                     // if exception is caught while getting property file value, then boolean flag remains false
                 }
             }
         }
         
         */
         

         
         // if a separate process for running matrix data mnager was started, we're done with it, so close it. 
         if ( matrixServerAddress.equalsIgnoreCase("localhost") ) {
             matrixServer.stop32BitMatrixIoServer();
         }


         
     }



     public String getProjectDirectoryName() {
        return projectDirectory;
     }


     public void restartModels ( HouseholdDataManagerIf householdDataManager ) {

         boolean runUsualWorkSchoolChoiceModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_WORKSCHOOL_CHOICE);
         if ( runUsualWorkSchoolChoiceModel ) {
             householdDataManager.resetUwslRandom();
         }
         else {
             boolean runAutoOwnershipModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AUTO_OWNERSHIP);
             if ( runAutoOwnershipModel ) {
                householdDataManager.resetAoRandom();
             }
             else {
                boolean runCoordinatedDailyActivityPatternModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_DAILY_ACTIVITY_PATTERN);
                if ( runCoordinatedDailyActivityPatternModel  ) {
                    householdDataManager.resetCdapRandom();
                }
                else {
                    boolean runIndividualMandatoryTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_MANDATORY_TOUR_FREQ);
                    if ( runIndividualMandatoryTourFrequencyModel  ) {
                        householdDataManager.resetImtfRandom();
                    }
                    else {
                        boolean runIndividualMandatoryTourDepartureAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_MAND_TOUR_DEP_TIME_AND_DUR);
                        if ( runIndividualMandatoryTourDepartureAndDurationModel  ) {
                            householdDataManager.resetImtodRandom();
                        }
                        else {
                            boolean runAtWorkSubTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_FREQ);
                            if ( runAtWorkSubTourFrequencyModel  ) {
                                householdDataManager.resetAwfRandom();
                            }
                            else {
                                boolean runAtWorkSubtourLocationChoiceModel = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_LOCATION_CHOICE );
                                if ( runAtWorkSubtourLocationChoiceModel  ) {
                                    householdDataManager.resetAwlRandom();
                                }
                                else {
                                    boolean runAtWorkSubtourDepartureTimeAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_AT_WORK_SUBTOUR_DEP_TIME_AND_DUR);
                                    if ( runAtWorkSubtourDepartureTimeAndDurationModel  ) {
                                        householdDataManager.resetAwtodRandom();
                                    }
                                    else {
                                        boolean runJointTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_JOINT_TOUR_FREQ);
                                        if ( runJointTourFrequencyModel  ) {
                                            householdDataManager.resetJtfRandom();
                                        }
                                        else {
                                            boolean runJointTourLocationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_JOINT_LOCATION_CHOICE);
                                            if ( runJointTourLocationModel  ) {
                                                householdDataManager.resetJtlRandom();
                                            }
                                            else {
                                                boolean runJointTourDepartureAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_JOINT_TOUR_DEP_TIME_AND_DUR);
                                                if ( runJointTourDepartureAndDurationModel  ) {
                                                    householdDataManager.resetJtodRandom();
                                                }
                                                else {
                                                    boolean runIndividualNonMandatoryTourFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_FREQ);
                                                    if ( runIndividualNonMandatoryTourFrequencyModel  ) {
                                                        householdDataManager.resetInmtfRandom();
                                                    }
                                                    else {
                                                        boolean runIndividualNonMandatoryTourLocationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_LOCATION_CHOICE);
                                                        if ( runIndividualNonMandatoryTourLocationModel  ) {
                                                            householdDataManager.resetInmtlRandom();
                                                        }
                                                        else {
                                                            boolean runIndividualNonMandatoryTourDepartureAndDurationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_DEP_TIME_AND_DUR);
                                                            if ( runIndividualNonMandatoryTourDepartureAndDurationModel  ) {
                                                                householdDataManager.resetInmtodRandom();
                                                            }
                                                            else {
                                                                boolean runStopFrequencyModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_STOP_FREQUENCY);
                                                                if ( runStopFrequencyModel  ) {
                                                                    householdDataManager.resetStfRandom();
                                                                }
                                                                else {
                                                                    boolean runStopLocationModel = ResourceUtil.getBooleanProperty(resourceBundle, PROPERTIES_RUN_STOP_LOCATION);
                                                                    if ( runStopLocationModel  ) {
                                                                        householdDataManager.resetStlRandom();
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                 }
             }
         }
     }



     private void createSerializedObjectInFileFromObject( Object objectToSerialize, String serializedObjectFileName, String serializedObjectKey ){
         try{
             DataFile dataFile = new DataFile( serializedObjectFileName, 1 );
             DataWriter dw = new DataWriter( serializedObjectKey );
             dw.writeObject( objectToSerialize );
             dataFile.insertRecord( dw );
             dataFile.close();
         }
         catch(NotSerializableException e) {
             logger.error( String.format("NotSerializableException for %s.  Trying to create serialized object with key=%s, in filename=%s.", objectToSerialize.getClass().getName(), serializedObjectKey, serializedObjectFileName ), e );
             throw new RuntimeException();
         }
         catch(IOException e) {
             logger.error( String.format("IOException trying to write disk object file=%s, with key=%s for writing.", serializedObjectFileName, serializedObjectKey ), e );
             throw new RuntimeException();
         }
     }


     private Object createObjectFromSerializedObjectInFile( Object newObject, String serializedObjectFileName, String serializedObjectKey ){
         try{
             DataFile dataFile = new DataFile( serializedObjectFileName, "r" );
             DataReader dr = dataFile.readRecord( serializedObjectKey );
             newObject = dr.readObject();
             dataFile.close();
             return newObject;
         }
         catch(IOException e) {
             logger.error( String.format("IOException trying to read disk object file=%s, with key=%s.", serializedObjectFileName, serializedObjectKey ), e );
             throw new RuntimeException();
         }
         catch(ClassNotFoundException e) {
             logger.error( String.format("could not instantiate %s object, with key=%s from filename=%s.", newObject.getClass().getName(), serializedObjectFileName, serializedObjectKey ), e );
             throw new RuntimeException();
         }
     }


     private MatrixDataServer startMatrixServerProcess( String serverAddress, int serverPort ) {

         String className = MatrixDataServer.MATRIX_DATA_SERVER_NAME;

         MatrixDataServer matrixServer = new MatrixDataServer();

         try {

             // create the concrete data server object
             matrixServer.start32BitMatrixIoServer( MatrixType.TPPLUS );

         }
         catch ( RuntimeException e ) {
             matrixServer.stop32BitMatrixIoServer();
             logger.error ( "RuntimeException caught in com.pb.models.ctramp.MatrixDataServer.main() -- exiting.", e );
         }

         // bind this concrete object with the cajo library objects for managing RMI
         try {
             Remote.config( serverAddress, serverPort, null, 0 );
         }
         catch ( UnknownHostException e ) {
             logger.error ( String.format( "UnknownHostException. serverAddress = %s, serverPort = %d -- exiting.", serverAddress, serverPort ), e );
             matrixServer.stop32BitMatrixIoServer();
             throw new RuntimeException();
         }

         try {
             ItemServer.bind( matrixServer, className );
         }
         catch ( RemoteException e ) {
             logger.error ( String.format( "RemoteException. serverAddress = %s, serverPort = %d -- exiting.", serverAddress, serverPort ), e );
             matrixServer.stop32BitMatrixIoServer();
             throw new RuntimeException();
         }

         return matrixServer;

     }


}
