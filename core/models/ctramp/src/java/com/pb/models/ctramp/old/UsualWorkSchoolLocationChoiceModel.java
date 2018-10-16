package com.pb.models.ctramp.old;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.MissingResourceException;
import java.util.ResourceBundle;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;



public class UsualWorkSchoolLocationChoiceModel {
    
	
    public static Logger logger = Logger.getLogger(UsualWorkSchoolLocationChoiceModel.class);

    public static final String PROPERTIES_DC_SOA_SAMPLE_SIZE        = "UsualWorkAndSchoolLocationChoice.SampleOfAlternatives.SampleSize";
    public static final String PROPERTIES_UEC_USUAL_LOCATION        = "UecFile.DestinationChoice";
    public static final String PROPERTIES_UEC_USUAL_LOCATION_SOA    = "UecFile.SampleOfAlternativesChoice";
    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE      = "UecFile.TourModeChoice";

    public static final String PROPERTIES_MANDATORY_RUN_WORK = "UsualWorkAndSchoolLocationChoice.RunFlag.Work";
    public static final String PROPERTIES_MANDATORY_RUN_UNIVERSITY = "UsualWorkAndSchoolLocationChoice.RunFlag.University";
    public static final String PROPERTIES_MANDATORY_RUN_SCHOOL = "UsualWorkAndSchoolLocationChoice.RunFlag.School";

    public static final String PROPERTIES_RESULTS_WORK_SCHOOL_LOCATION_CHOICE = "Results.UsualWorkAndSchoolLocationChoice";

    public static final String PROPERTIES_WORK_SCHOOL_LOCATION_CHOICE_NUM_THREADS = "UsualWorkAndSchoolLocationChoice.NumThreads"; 
    public static final String PROPERTIES_WORK_SCHOOL_LOCATION_CHOICE_PACKET_SIZE = "UsualWorkAndSchoolLocationChoice.PacketSize";

    
    
    // TODO should this be set by user?
    public static int PACKET_SIZE = 0;
    public static int NUM_THREADS = 1;

    String wsLocResultsFileName;


    ResourceBundle resourceBundle;
    String projectDirectory;

    MatrixDataServerIf ms;
    ModelStructure modelStructure;                                         
    TazDataIf tazDataManager;
    DestChoiceModel destChoiceModel;
    DestChoiceSize dcSizeObj;
    CtrampDmuFactoryIf dmuFactory;

    String dcUecFileName;
    String soaUecFileName;
    String modeChoiceUecFileName;
    int soaSampleSize;
    int numZones;
    int numWalkSubzones;



    public UsualWorkSchoolLocationChoiceModel(ResourceBundle resourceBundle, ModelStructure modelStructure, MatrixDataServerIf ms, TazDataIf tazDataManager, DestChoiceSize dcSizeObj, CtrampDmuFactoryIf dmuFactory ){
    	
    	// set the local variables
    	this.resourceBundle = resourceBundle;
    	this.modelStructure = modelStructure;
    	this.tazDataManager = tazDataManager;
        this.dmuFactory = dmuFactory;
        this.dcSizeObj = dcSizeObj;
        this.ms = ms;

        try {
            NUM_THREADS = Integer.parseInt( resourceBundle.getString( PROPERTIES_WORK_SCHOOL_LOCATION_CHOICE_NUM_THREADS ) );
            PACKET_SIZE = Integer.parseInt( resourceBundle.getString( PROPERTIES_WORK_SCHOOL_LOCATION_CHOICE_PACKET_SIZE ) );
        }
        catch (MissingResourceException e){
            NUM_THREADS = 1;
            PACKET_SIZE = 0;
        }

        
        try {
            wsLocResultsFileName = resourceBundle.getString( PROPERTIES_RESULTS_WORK_SCHOOL_LOCATION_CHOICE );
        }
        catch (MissingResourceException e){
            wsLocResultsFileName = null;
        }


        projectDirectory = ResourceUtil.getProperty(resourceBundle, CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);

        // get the sample-of-alternatives sample size
        soaSampleSize = ResourceUtil.getIntegerProperty(resourceBundle, PROPERTIES_DC_SOA_SAMPLE_SIZE);

        // locate the UECs for destination choice, sample of alts, and mode choice
        String usualLocationUecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_USUAL_LOCATION);
        dcUecFileName = projectDirectory + usualLocationUecFileName;

        String usualLocationSoaUecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_USUAL_LOCATION_SOA);
        soaUecFileName = projectDirectory + usualLocationSoaUecFileName;

        String tourModeChoiceUecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_TOUR_MODE_CHOICE);
        modeChoiceUecFileName = projectDirectory + tourModeChoiceUecFileName;

        numZones = tazDataManager.getNumberOfZones();
        numWalkSubzones = tazDataManager.getNumberOfSubZones();

    }
    


    public void runSchoolAndLocationChoiceModel (HouseholdDataManagerIf householdDataManager) {

        runConstrainedLocationChoiceModel ( householdDataManager);

    }



    /**
     * 
     * Original multithreaded based method
     */
    private void runConstrainedLocationChoiceModel (HouseholdDataManagerIf householdDataManager) {

       // calculate the size terms
       // TODO add an option to write to file or not?
        /*
         * we might not need this.  Maybe we should write DC Size info to TazDataManager ????
         *
       DestChoiceSize dcSizeObj;
       String dcSizeDiskObjectFileName = ResourceUtil.getProperty( resourceBundle, PROPERTIES_MANDATORY_SIZE_DISKOBJECT_FILE );
       boolean readDiskObjectFile = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_MANDATORY_SIZE_DISKOBJECT_READ_FILE );

       // if a disk object file exists and the properties flag has been set to use it, read the dcSize object from the file
       if ( readDiskObjectFile && dcSizeDiskObjectFileName != null ) {
          dcSizeDiskObjectFileName = projectDirectory + dcSizeDiskObjectFileName;
          dcSizeObj = createDcSizeObjectFromSerializedObjectInFile( dcSizeDiskObjectFileName );
       }
       // otherwise create a new dcSize object
       else {
           dcSizeObj = new DestChoiceSize( modelStructure, tazDataManager);
           dcSizeObj.setupDestChoiceSize( resourceBundle, projectDirectory );
       }
         */



        // dimension an array to accumulate chosen long term model choices for use in shadow price adjustments
        String[] tourPurposeList = modelStructure.getDcModelPurposeList( ModelStructure.MANDATORY_CATEGORY );


        // create an object for calculating destination choice attraction size terms and managing shadow price calculations.
        dcSizeObj = new DestChoiceSize( modelStructure, tazDataManager );
        dcSizeObj.setupDestChoiceSize( resourceBundle, projectDirectory, ModelStructure.MANDATORY_CATEGORY );

        // calculate the size terms
        if ( ! dcSizeObj.getDcSizeCalculated() )
            dcSizeObj.calculateDcSize();



        int[][][] originLocationsByHomeZone = householdDataManager.getTourPurposePersonsByHomeZone( tourPurposeList );

        // balance the size variables
        int start = modelStructure.getDcSizeArrayCategoryIndexOffset( ModelStructure.MANDATORY_CATEGORY );
        int end = start + modelStructure.getNumDcSizeArrayCategorySegments( ModelStructure.MANDATORY_CATEGORY );
        dcSizeObj.balanceSizeVariables(originLocationsByHomeZone, tourPurposeList, start, end);
       
        
        HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle);
        
        
        double[][][] finalModeledDestChoiceLocationsByDestZone = new double[tourPurposeList.length][][];

        DestChoiceModelFactory modelFactory = DestChoiceModelFactory.getDestChoiceModelFactoryInstance( propertyMap, ms, modelStructure, ModelStructure.MANDATORY_CATEGORY, tazDataManager, dcSizeObj, dcUecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory );        

        if ( PACKET_SIZE == 0 )
            PACKET_SIZE = householdDataManager.getNumHouseholds();

        // account for possible rounding error -- make sure numPackets*PACKET_SIZE Is at least as big as num households.
        int numPackets = householdDataManager.getNumHouseholds() / PACKET_SIZE;
        if ( numPackets * PACKET_SIZE < householdDataManager.getNumHouseholds() )
            numPackets += 1;
        
        
        
        
        // shadow pricing iterations
        for( int iter=0; iter < dcSizeObj.getMaxShadowPriceIterations(); iter++ ) {
           
            ExecutorService exec = Executors.newFixedThreadPool( NUM_THREADS );
            ArrayList<Future< List<Object> >> results = new ArrayList<Future< List<Object> >>();
           

            for(int i=0;i<tourPurposeList.length;++i)
                finalModeledDestChoiceLocationsByDestZone[i] = new double[numZones+1][numWalkSubzones];

            long initTime = System.currentTimeMillis();

            
            int startIndex = 0;
            int endIndex = 0;
            while ( endIndex < householdDataManager.getNumHouseholds() ) {
                endIndex = startIndex + PACKET_SIZE - 1;
                if ( endIndex + PACKET_SIZE > householdDataManager.getNumHouseholds() )
                    endIndex = householdDataManager.getNumHouseholds();
                LocationChoiceTask task = new LocationChoiceTask( propertyMap, modelFactory, householdDataManager, startIndex, endIndex );
                results.add ( exec.submit( task ) );
                startIndex += PACKET_SIZE;
            }
            
            

            for ( Future< List<Object> > fs : results ) {
               
                try {
                    List<Object> resultBundle = fs.get();
                    double[][][] partialResults = (double[][][])resultBundle.get(0);
                    accumulateDcModelLocations( finalModeledDestChoiceLocationsByDestZone, partialResults );
                }
                catch (InterruptedException e) {
                    logger.error( "", e );
                    throw new RuntimeException();
                }
                catch (ExecutionException e) {
                    logger.error( "Exception returned in place of result object.", e );
                    throw new RuntimeException();
                }
                finally {
                    exec.shutdown();
                }

            } // future
           
            logger.info( "Usual work and school location choices computed in " + ((System.currentTimeMillis() - initTime) / 1000) + " seconds."); ;


            
            
            // apply the shadow price adjustments
            dcSizeObj.reportMaxDiff(iter, finalModeledDestChoiceLocationsByDestZone, tourPurposeList);
            dcSizeObj.updateShadowPrices(finalModeledDestChoiceLocationsByDestZone, tourPurposeList);
            dcSizeObj.updateSizeVariables(tourPurposeList, start, end);
            dcSizeObj.updateShadowPricingInfo(iter, originLocationsByHomeZone, finalModeledDestChoiceLocationsByDestZone, tourPurposeList, start, end);
           

            householdDataManager.setUwslRandomCount();

        } // iter




        /*
         * we might not need this.  Maybe we should write DC Size info to TazDataManager ????
         *

       // if the properties flag has been set to write a new disk object file, write the dcSize object to the file
       boolean writeDiskObjectFile = ResourceUtil.getBooleanProperty( resourceBundle, PROPERTIES_MANDATORY_SIZE_DISKOBJECT_Write_FILE );
       if ( writeDiskObjectFile && dcSizeDiskObjectFileName != null ) {
          createSerializedObjectInFileFromDcSizeObject( dcSizeObj, dcSizeDiskObjectFileName );
       }

         */

   }



    /**
     * Loops through the households in the HouseholdDataManager, gets the households and persons
     *  and writes a row with detail on each of these in a file.
     *
     * @param householdDataManager is the object from which the array of household objects can be retrieved.
     * @param projectDirectory is the root directory for the output file named
     */
    public void saveResults(HouseholdDataManagerIf householdDataManager, String projectDirectory){

        FileWriter writer;
        PrintWriter outStream = null;

        if ( wsLocResultsFileName != null ) {

            wsLocResultsFileName = projectDirectory + wsLocResultsFileName;

            try {
                writer = new FileWriter(new File(wsLocResultsFileName));
                outStream = new PrintWriter (new BufferedWriter( writer ) );
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred opening wsLoc results file: %s.", wsLocResultsFileName) );
                throw new RuntimeException(e);
            }

            // write header
            outStream.println( "HHID,HomeTAZ,HomeSubZone,PersonID,PersonNum,PersonType,PersonAge,EmploymentCategory,StudentCategory,WorkLocation,WorkSubZone,SchoolLocation,SchoolSubZone");

            
            // get the array of households
            Household[] householdArray = householdDataManager.getHhArray();

            for(int i=1; i < householdArray.length; ++i){


                Household household = householdArray[i];

                int hhId = household.getHhId();
                int homeTaz = household.getHhTaz();
                int homeSubzone = household.getHhWalkSubzone();

                Person[] personArray = household.getPersons();

                for (int j = 1; j < personArray.length; ++j) {

                    Person person = personArray[j];

                    int personId = person.getPersonId();
                    int personNum = person.getPersonNum();
                    String personType = person.getPersonType(); 
                    int personAge = person.getAge();
                    String employmentCategory = person.getPersonEmploymentCategory();
                    String studentCategory = person.getPersonStudentCategory();

                    int workLocation = person.getUsualWorkLocation();
                    int workSubZone = person.getPersonWorkLocationSubZone();

                    int schoolLocation = person.getUsualSchoolLocation();
                    int schoolSubZone = person.getPersonSchoolLocationSubZone();

                    // write data record
                    outStream.println( String.format("%d,%d,%d,%d,%d,%s,%d,%s,%s,%d,%d,%d,%d" , 
                                hhId, homeTaz, homeSubzone, personId, personNum, personType, personAge,
                                employmentCategory, studentCategory,
                                workLocation, workSubZone, schoolLocation, schoolSubZone));

                }

            }


            outStream.close();

        }

    }

    
    
    private void accumulateDcModelLocations( double [][][] accumulatedResults, double [][][] partialResults ) {
        
        for (int p=0; p < accumulatedResults.length; p++)
            for (int i=0; i < accumulatedResults[p].length; i++)
                for (int j=0; j < accumulatedResults[p][i].length; j++)
                    accumulatedResults[p][i][j] += partialResults[p][i][j];

    }

    private double getArrayTotal( double [][][] array ) {
        
        double total = 0.0;
        for (int p=0; p < array.length; p++)
            for (int i=0; i < array[p].length; i++)
                for (int j=0; j < array[p][i].length; j++)
                    total += array[p][i][j];

        return total;
    }

}
