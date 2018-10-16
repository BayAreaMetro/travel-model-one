package com.pb.models.ctramp.old;

import java.util.HashMap;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

import org.apache.log4j.Logger;


public class DestinationSampleOfAlternativesModel {

    static final int DC_SOA_DATA_SHEET = 0;
    
    private String dcSoaUecFileName;
    

    // A SampleOfAlternatives object and destsAvailable[] is needed for each purpose, segment
    private SampleOfAlternatives[] soa;
    private boolean[][] destsAvailable;

    private int sampleSize;
    private int[] sample;
    private float[] corrections;

    private  int[] altToZone;
    private  int[] altToSubZone;

    private int numDcAlts;
    private int numZones;

    private String tourCategory;
    
    private DcSoaDMU dcSoaDmuObject;
    
    private ModelStructure modelStructure;

    
    

    public DestinationSampleOfAlternativesModel( String soaUecFile, int sampleSize, HashMap<String, String> propertyMap,
    			ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, double[][][] probabilitiesCache,
                double[][][] cumProbabilitiesCache, DestChoiceSize dcSizeObj, CtrampDmuFactoryIf dmuFactory ){

    	this.modelStructure   = modelStructure;
    	this.sampleSize       = sampleSize;
    	this.dcSoaUecFileName = soaUecFile;
    	this.tourCategory = tourCategory;
    	
        dcSoaDmuObject = dmuFactory.getDcSoaDMU();

        dcSoaDmuObject.setDestChoiceSizeObject( dcSizeObj );

        numDcAlts = tazDataManager.getNumberOfZones()*tazDataManager.getNumberOfSubZones();
        numZones = tazDataManager.getNumberOfZones();

        altToZone = tazDataManager.getAltToZoneArray();
        altToSubZone = tazDataManager.getAltToSubZoneArray();

        // create an array of sample of alternative objects for each purpose
    	setupSampleOfAlternativesArrays( propertyMap, probabilitiesCache, cumProbabilitiesCache, dcSizeObj );
    }
    


    
    // updated to work with CtrampApplication (dto)
    private void setupSampleOfAlternativesArrays( HashMap<String, String> propertyMap, double[][][] probabilitiesCache, double[][][] cumProbabilitiesCache, DestChoiceSize dcSizeObj ) {

        Logger logger = Logger.getLogger(DestinationSampleOfAlternativesModel.class);

        // get the number of purposes and declare the first dimension to be this size.
        String[] soaModelPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        int numPurposes = soaModelPurposeList.length;
        soa = new SampleOfAlternatives[numPurposes];

        // for each purpose, get the number of segments
        for ( int p=0; p < numPurposes; p++ ) {

            // get the array of segments for this purpose
        	String purposeString = soaModelPurposeList[p];

            // create a new SampleOfAlternatives object for each array element
            ChoiceModelApplication choiceModel = null;

            try {
                int uecIndex = modelStructure.getSoaUecIndexForPurpose(purposeString);
                choiceModel = new ChoiceModelApplication (dcSoaUecFileName, uecIndex, DC_SOA_DATA_SHEET, propertyMap, dcSoaDmuObject.getClass() );
            }
            catch (RuntimeException e) {
                logger.error ( String.format("exception caught setting up DC SOA UEC model index for purpose[%d]: %s", p, soaModelPurposeList[p]), e );
                throw e;
            }

            // pass the probabilities cache element (i.e. a double[][]) for the purpose, segment, to be used locally by the SampleOfAlternatives object.
            soa[p] = new SampleOfAlternatives( choiceModel, numZones, probabilitiesCache[p], cumProbabilitiesCache[p] );

        }

        // declare dimensions for the array of choice alternative availability by purpose, segment and
        // set elements to true if size[purpose][alternative] > 0.  Alternatives are numbered 1,...,ZONES*SUBZONES
        destsAvailable = new boolean[numPurposes][];
        for ( int p=0; p < soaModelPurposeList.length; p++ ) {
        	String purposeString = soaModelPurposeList[p];
        	int purposeIndex = modelStructure.getDcModelPurposeIndex(purposeString);
        	int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex( purposeIndex );

            destsAvailable[p] = new boolean[numDcAlts+1];

            int k=0;
            try {
                for (k=1; k <= numDcAlts; k++) {
                    int zone = altToZone[k];
                    int subzone = altToSubZone[k];
                    double size = dcSizeObj.getDcSize( dcSizeArrayIndex, zone, subzone );
                    if ( size > 0.0 )
                        destsAvailable[p][k] = true;
                } // k
            }
            catch (RuntimeException e){
                logger.error ( String.format( "caught exception - p=%d, purposeString=%s, purposeIndex=%d, k=%d", p, purposeString, purposeIndex, k));
                throw new RuntimeException();
            }
        } // p
        
    }
    



    public void computeDestinationSampleOfAlternatives( Tour tour, Person person, String purposeName, int purposeIndex ) {

        Household hhObj = person.getHouseholdObject();
        
        // set the hh object for this DMU object
        dcSoaDmuObject.setHouseholdObject ( hhObj );
        
        int homeTaz = hhObj.getHhTaz();
        int origTaz = homeTaz;
        if ( tour != null )
            origTaz = tour.getTourOrigTaz();
        
        // set sample of alternatives choice DMU attributes
        dcSoaDmuObject.setDmuIndexValues( hhObj.getHhId(), homeTaz, origTaz, 0 );

        // apply sample of alternatives model for the work segment to which this worker belongs.
        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( person.getHouseholdObject().getDebugChoiceModels() ) {
            String choiceModelDescription = "";
            String decisionMakerLabel = "";

            if ( tour == null ) {
                // null tour means the DC is a mandatory usual location choice
                choiceModelDescription = String.format ( "Usual Location Sample of Alternatives Choice Model for: Category=%s, Purpose=%s", tourCategory, purposeName );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            else {
                choiceModelDescription = String.format ( "Destination Choice Model for: Category=%s, Purpose=%s, TourId=%d", tourCategory, purposeName, tour.getTourId() );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            
            soa[purposeIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }

        
        soa[purposeIndex].applySampleOfAlternativesChoiceModel ( purposeName, dcSoaDmuObject, dcSoaDmuObject.getDmuIndexValues(), origTaz, sampleSize, destsAvailable[purposeIndex] );

        // get sample of locations and correction factors for sample
        sample = soa[purposeIndex].getSampleOfAlternatives();
        corrections = soa[purposeIndex].getSampleCorrectionFactors();

    }


    public int[] getSampleOfAlternatives() {
        return sample;
    }


    public float[] getSampleOfAlternativesCorrections() {
        return corrections;
    }
    

}