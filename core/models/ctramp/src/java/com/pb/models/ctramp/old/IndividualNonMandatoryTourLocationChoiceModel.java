package com.pb.models.ctramp.old;

import java.util.ArrayList;
import java.util.List;
import java.util.ResourceBundle;
import java.util.HashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;

public class IndividualNonMandatoryTourLocationChoiceModel {

    public static Logger logger = Logger.getLogger(IndividualNonMandatoryTourLocationChoiceModel.class);

    public static final String PROPERTIES_DC_SOA_SAMPLE_SIZE        = "IndividualNonMandatoryTourLocationChoice.SampleOfAlternatives.SampleSize";
    public static final String PROPERTIES_DC_UEC                    = "UecFile.DestinationChoice";
    public static final String PROPERTIES_DC_SOA_UEC                = "UecFile.SampleOfAlternativesChoice";
    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE      = "UecFile.TourModeChoice";


    // TODO should this be set by user?
    public static int NUM_PARTITIONS = 1;
    private int[] partitions = new int[NUM_PARTITIONS];



    ResourceBundle resourceBundle;
    String projectDirectory;

    private MatrixDataServerIf ms;
    ModelStructure modelStructure;
    TazDataIf tazDataManager;
    DestChoiceModel destChoiceModel;
    CtrampDmuFactoryIf dmuFactory;

    protected HashMap<Integer,String> purposeIndexToNameMap;

    String uecFileName, soaUecFileName, modeChoiceUecFileName;
    int soaSampleSize;
    int numZones, numWalkSubzones;



    public IndividualNonMandatoryTourLocationChoiceModel(ResourceBundle resourceBundle, MatrixDataServerIf ms, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ){

    	// set the local variables
    	this.resourceBundle = resourceBundle;
    	this.modelStructure = modelStructure;
    	this.tazDataManager = tazDataManager;
        this.dmuFactory = dmuFactory;
        this.ms = ms;

        projectDirectory = ResourceUtil.getProperty(resourceBundle, CtrampApplication.PROPERTIES_PROJECT_DIRECTORY);

        // get the sample-of-alternatives sample size
        soaSampleSize = ResourceUtil.getIntegerProperty(resourceBundle, PROPERTIES_DC_SOA_SAMPLE_SIZE);

        // locate the UECs for destination choice, sample of alts, and mode choice
        String dcUecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_DC_UEC);
        uecFileName = projectDirectory + dcUecFileName;

        String soaFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_DC_SOA_UEC);
        soaUecFileName = projectDirectory + soaFileName;

        String tourModeChoiceUecFileName = ResourceUtil.getProperty(resourceBundle, PROPERTIES_UEC_TOUR_MODE_CHOICE);
        modeChoiceUecFileName = projectDirectory + tourModeChoiceUecFileName;

        numZones = tazDataManager.getNumberOfZones();
        numWalkSubzones = tazDataManager.getNumberOfSubZones();


        purposeIndexToNameMap = new HashMap<Integer,String>();

        int i = 0;
        String[] names = modelStructure.getEscortSegmentNames();
        if ( names.length > 0 ) {
            for ( i=0; i < names.length; i++ ) {
                String tempName = String.format( "%s_%s", modelStructure.ESCORT_PURPOSE_NAME, names[i] );
                purposeIndexToNameMap.put( i+1, tempName );
            }
        }
        else {
            purposeIndexToNameMap.put( i+1, modelStructure.ESCORT_PURPOSE_NAME );
        }
        purposeIndexToNameMap.put( i+1, modelStructure.SHOPPING_PURPOSE_NAME );
        purposeIndexToNameMap.put( i+2, modelStructure.EAT_OUT_PURPOSE_NAME );
        purposeIndexToNameMap.put( i+3, modelStructure.OTH_MAINT_PURPOSE_NAME );
        purposeIndexToNameMap.put( i+4, modelStructure.SOCIAL_PURPOSE_NAME );
        purposeIndexToNameMap.put( i+5, modelStructure.OTH_DISCR_PURPOSE_NAME );


    }



    public void runIndivNonMandatoryTourLocationChoiceModel (HouseholdDataManagerIf householdDataManager) {

        runUnConstrainedLocationChoiceModel ( householdDataManager);

    }



    private void runUnConstrainedLocationChoiceModel (HouseholdDataManagerIf householdDataManager) {

        // get the list of purpose names to use for this location choice model
        String[] tourPurposeList = new String[purposeIndexToNameMap.size()];
        for ( int i=0; i < tourPurposeList.length; i++ )
            tourPurposeList[i] = purposeIndexToNameMap.get(i+1);



        double[][][] finalModeledDestChoiceLocationsByDestZone = new double[tourPurposeList.length][][];
        for( int i=0; i < tourPurposeList.length; i++ ) {
      		finalModeledDestChoiceLocationsByDestZone[i] = new double [numZones+1][numWalkSubzones];
        } // i (tourPurpose)



        // create an object for calculating destination choice attraction size terms and managing shadow price calculations.
        DestChoiceSize dcSizeObj = new DestChoiceSize( modelStructure, tazDataManager );
        dcSizeObj.setupDestChoiceSize( resourceBundle, projectDirectory, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY );


        // calculate the size terms
        // TODO add an option to write to file or not?
        dcSizeObj.calculateDcSize();


	    // partition the household array
	    partitionHouseholdArray( householdDataManager.getNumHouseholds() );


	    int[][][] originLocationsByHomeZone = new int[tourPurposeList.length][][];

	    // loop through the purposes and extract out subjects
	    for(int i=0;i<tourPurposeList.length;++i){
		    String purposeString = tourPurposeList[i];
		    originLocationsByHomeZone[i] = householdDataManager.getIndividualNonMandatoryToursByHomeZoneSubZone( purposeString );
	    }

	    // balance the size variables
        int start = modelStructure.getDcSizeArrayCategoryIndexOffset( ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY );
        int end = start + modelStructure.getNumDcSizeArrayCategorySegments( ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY );
	    dcSizeObj.balanceSizeVariables(originLocationsByHomeZone, tourPurposeList, start, end);

	    
        HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle);
        DestChoiceModelFactory modelFactory = DestChoiceModelFactory.getDestChoiceModelFactoryInstance( propertyMap, ms, modelStructure, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY, tazDataManager, dcSizeObj, uecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory );         

        
        ExecutorService exec = Executors.newFixedThreadPool(NUM_PARTITIONS);
        ArrayList<Future< List<Object> >> results = new ArrayList<Future< List<Object> >>();

        int firstHh = 1;
        for ( int partition=0; partition < NUM_PARTITIONS; partition++ ) {

            int lastHh = partitions[partition];

            // call the task
            LocationChoiceTask task = new LocationChoiceTask( propertyMap, modelFactory, householdDataManager, firstHh, lastHh );            
            results.add ( exec.submit( task ) );

            firstHh = partitions[partition];
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

        // apply the shadow price adjustments
        dcSizeObj.reportMaxDiff( -1, finalModeledDestChoiceLocationsByDestZone, tourPurposeList );
        dcSizeObj.updateSizeVariables( tourPurposeList, start, end );


        householdDataManager.setInmtlRandomCount();

   }


   private void partitionHouseholdArray( int totalHhs ) {

       int partitionSize = totalHhs / NUM_PARTITIONS;

       // set the ending hhArray index for each partition
       partitions[0] = partitionSize;
       for ( int i=1 ; i < NUM_PARTITIONS; i++ )
           partitions[i] = partitions[i-1] + partitionSize;

       partitions[NUM_PARTITIONS-1] = totalHhs;

   }

   private void accumulateDcModelLocations( double [][][] accumulatedResults, double [][][] partialResults ) {
       
       for (int p=0; p < partialResults.length; p++)
           for (int i=0; i < partialResults[p].length; i++)
               for (int j=0; j < partialResults[p][i].length; j++)
                   accumulatedResults[p][i][j] += partialResults[p][i][j];

   }

}