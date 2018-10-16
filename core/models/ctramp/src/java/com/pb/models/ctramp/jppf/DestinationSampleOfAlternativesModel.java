package com.pb.models.ctramp.jppf;

import com.pb.common.calculator.VariableTable;
import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;
import com.pb.common.newmodel.ChoiceModelApplication;

import java.io.Serializable;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Random;

import org.apache.log4j.Logger;


public class DestinationSampleOfAlternativesModel implements Serializable {

    private transient Logger logger = Logger.getLogger(DestinationSampleOfAlternativesModel.class);

    // set to false to store probabilities in cache for re-use; true to disable probabilities cache.
    private static final boolean ALWAYS_COMPUTE_PROBABILITIES = false;
    
    private static final int DC_SOA_DATA_SHEET = 0;
    private String dcSoaUecFileName;
    private int sampleSize;


    private int currentOrigTaz;
    private double[][] probabilitiesCache;
    private double[][] cumProbabilitiesCache;
    private int currentWorkTaz;
    private double[][] subtourProbabilitiesCache;
    private double[][] subtourCumProbabilitiesCache;

    
    // destsSample[] and destsAvailable[] are indexed by purpose and alternative
    private boolean[][] destsAvailable;
    private int[][] destsSample;

    // these will be used to keep the unique alternatives determined for the decision makers 
    HashMap<Integer,Integer> altFreqMap;
    private int[] sample;
    private float[] corrections;
    private int numUniqueAlts;

    private ChoiceModelApplication[] choiceModel;
    
    private String tourCategory;
    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;

    private int soaProbabilitiesCalculationCount = 0;

    
    public DestinationSampleOfAlternativesModel( String soaUecFile, int sampleSize, HashMap<String,String> propertyMap, ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj, DcSoaDMU dcSoaDmuObject ){

    	this.sampleSize       = sampleSize;
    	this.dcSoaUecFileName = soaUecFile;
    	this.tourCategory = tourCategory;
        this.modelStructure   = modelStructure;
        this.tazDataManager = tazDataManager;
        
        // create an array of sample of alternative ChoiceModelApplication objects for each purpose
    	setupSampleOfAlternativesChoiceModelArrays( propertyMap, dcSizeObj, dcSoaDmuObject );

    }
    


    
    private void setupSampleOfAlternativesChoiceModelArrays( HashMap<String,String> propertyMap, DestChoiceSize dcSizeObj, DcSoaDMU dcSoaDmuObject ) {

        String[] soaModelPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        
        int minPurposeIndex = 99;
        int maxPurposeIndex = 0;
        for ( String purp : soaModelPurposeList ) {
            int index = modelStructure.getDcModelPurposeIndex( purp );
            if ( index < minPurposeIndex )
                minPurposeIndex = index;
            if ( index > maxPurposeIndex )
                maxPurposeIndex = index;
        }
            
        choiceModel = new ChoiceModelApplication[maxPurposeIndex+1];
        probabilitiesCache = new double[maxPurposeIndex+1][];
        cumProbabilitiesCache = new double[maxPurposeIndex+1][];
        subtourProbabilitiesCache = new double[maxPurposeIndex+1][];
        subtourCumProbabilitiesCache = new double[maxPurposeIndex+1][];
        
        
        // for each purpose, get the number of segments
        for ( String purp : soaModelPurposeList ) {

            int purposeIndex = modelStructure.getDcModelPurposeIndex( purp );

            try {
                int uecIndex = modelStructure.getSoaUecIndexForPurpose( purp );
                choiceModel[purposeIndex] = new ChoiceModelApplication ( dcSoaUecFileName, uecIndex, DC_SOA_DATA_SHEET, propertyMap, (VariableTable)dcSoaDmuObject );
            }
            catch (RuntimeException e) {
                logger.error ( String.format("exception caught setting up DC SOA ChoiceModelApplication[%d] for purpose=%s", purposeIndex, purp) );
                logger.fatal( "Exception caught:", e );
                logger.fatal( "Throwing new RuntimeException() to terminate." );
                throw new RuntimeException();
            }

        }


        setDcSizeForSampleOfAlternatives ( soaModelPurposeList, dcSizeObj );
        
        altFreqMap = new HashMap<Integer,Integer>( sampleSize );
        sample = new int[sampleSize+1];
        corrections = new float[sampleSize+1];
    }
    


    /**
     *  This method is called initially when the SOA choice models array is created.
     *  It would be called subsequently if a shadow pricing methodology is applied to reset the scaled size terms
     *  and corresponding availabilities and sample arrays.
     */
    public void setDcSizeForSampleOfAlternatives ( String[] soaModelPurposeList, DestChoiceSize dcSizeObj ) {

        int numberOfZones = tazDataManager.getNumberOfZones();
        int numberOfSubzones = tazDataManager.getNumberOfSubZones();
        int numDcAlts = numberOfZones*numberOfSubzones;

        int[] altToZone = tazDataManager.getAltToZoneArray();
        int[] altToSubZone = tazDataManager.getAltToSubZoneArray();


        
        // declare dimensions for the alternative availability array by purpose and number of alternaives
        // set elements to true if size[purpose][alternative] > 0.  Alternatives are numbered 1,...,ZONES*SUBZONES.
        // set the destsSample to 1 if destsAvailable true - it is used in the UEC as a filter - if destsSample[purpose][k] == 0, the utility calculation is completely skipped.
        int maxPurposeIndex = 0;
        for ( String purp : soaModelPurposeList ) {
            int index = modelStructure.getDcModelPurposeIndex( purp );
            if ( index > maxPurposeIndex )
                maxPurposeIndex = index;
        }
            
        destsAvailable = new boolean[maxPurposeIndex+1][];
        destsSample = new int[maxPurposeIndex+1][];

        for ( String purposeString : soaModelPurposeList ) {
            
            int p = modelStructure.getDcModelPurposeIndex( purposeString );

            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex( p );

            destsAvailable[p] = new boolean[numDcAlts+1];
            destsSample[p] = new int[numDcAlts+1];

            int k=0;
            try {
                for (k=1; k <= numDcAlts; k++) {
                    int zone = altToZone[k];
                    int subzone = altToSubZone[k];
                    double size = dcSizeObj.getDcSize( dcSizeArrayIndex, zone, subzone );
                    if ( size > 0.0 ) {
                        destsAvailable[p][k] = true;
                        destsSample[p][k] = 1;
                    }
                } // k
            }
            catch (RuntimeException e){
                logger.error ( String.format( "caught exception getting DC Size - p=%d, purposeString=%s, k=%d", p, purposeString, k));
                logger.fatal( "Exception caught:", e );
                logger.fatal( "Throwing new RuntimeException() to terminate." );
                throw new RuntimeException();
            }
            
        } // p

    }
    
    

    public void computeDestinationSampleOfAlternatives( DcSoaDMU dcSoaDmuObject, Tour tour, Person person, String purposeName, int purposeIndex ) {

        // clear the HashMap used to store the alternatives selected and the count of each time an alternative was included
        altFreqMap.clear();
        
        
        // get the origin taz for the person or tour
        Household hhObj = person.getHouseholdObject();
        
        int homeTaz = hhObj.getHhTaz();
        int origTaz = homeTaz;
        if ( tour != null )
            origTaz = tour.getTourOrigTaz();

        // if the flag is set to compute sample of alternative probabilities for every work/school location choice,
        // or the tour's origin taz is different from the currentOrigTaz, reset the currentOrigTaz and clear the stored probabilities.
        if ( tour != null && tour.getTourCategoryIsAtWork() ) {
                
            if ( ALWAYS_COMPUTE_PROBABILITIES || origTaz != currentWorkTaz ) {
                
                // clear the probabilities store for the current origin taz, for each purpose 
                for ( int i=0; i < subtourProbabilitiesCache.length; i++ ) {
                    subtourProbabilitiesCache[i] = null;  
                    subtourCumProbabilitiesCache[i] = null; 
                }
                currentWorkTaz = origTaz;

            }
            
            // If the sample of alternatives choice probabilities have not been computed for the current origin taz
            // and purpose specified, compute them.
            if ( subtourProbabilitiesCache[purposeIndex] == null ) {
                computeSampleOfAlternativesChoiceProbabilities( choiceModel[purposeIndex], dcSoaDmuObject, tour, person, purposeName, purposeIndex, origTaz );
                soaProbabilitiesCalculationCount++;
            }

        }
        else {
            
            if ( ALWAYS_COMPUTE_PROBABILITIES || origTaz != currentOrigTaz ) {
                
                // clear the probabilities store for the current origin taz, for each purpose 
                for ( int i=0; i < probabilitiesCache.length; i++ ) {
                    probabilitiesCache[i] = null;  
                    cumProbabilitiesCache[i] = null; 
                }
                currentOrigTaz = origTaz;
                
            }
            
            // If the sample of alternatives choice probabilities have not been computed for the current origin taz
            // and purpose specified, compute them.
            if ( probabilitiesCache[purposeIndex] == null ) {
                computeSampleOfAlternativesChoiceProbabilities( choiceModel[purposeIndex], dcSoaDmuObject, tour, person, purposeName, purposeIndex, origTaz );
                soaProbabilitiesCalculationCount++;
            }

        }
        
        
        

        
        Random hhRandom = hhObj.getHhRandom();
        int rnCount = hhObj.getHhRandomCount();
        // when household.getHhRandom() was applied, the random count was incremented, assuming a random number would be drawn right away.
        // so let's decrement by 1, then increment the count each time a random number is actually drawn in this method.
        rnCount --;
        
        // select sampleSize alternatives based on probabilitiesList[origTaz], and count frequency of alternatives chosen.
        // final sample may include duplicate alternative selections.
        for (int i=0; i < sampleSize; i++) {
            
            double rn = hhRandom.nextDouble();
            rnCount++;

            int chosenAlt = -1;
            if ( tour != null && tour.getTourCategoryIsAtWork() )
                chosenAlt = choiceModel[purposeIndex].getChoiceIndexFromCumProbabilities( subtourCumProbabilitiesCache[purposeIndex], rn );
            else
                chosenAlt = choiceModel[purposeIndex].getChoiceIndexFromCumProbabilities( cumProbabilitiesCache[purposeIndex], rn );
            
            // write choice model alternative info to log file
            if ( hhObj.getDebugChoiceModels () ) {
                choiceModel[purposeIndex].logSelectionInfo ( String.format("%s Sample Of Alternatives Choice for dmuSegment=%d", purposeName, origTaz), String.format("HHID=%d, rn=%.8f, rnCount=%d", hhObj.getHhId(), rn, (rnCount+i) ), rn, chosenAlt );
            }
            
            
            int freq = 0;
            if ( altFreqMap.containsKey(chosenAlt) )
                freq = altFreqMap.get( chosenAlt );
            altFreqMap.put(chosenAlt, (freq + 1) );
            
        }

        // sampleSize random number draws were made from the Random object for the current household,
        // so update the count in the hh's Random.
        hhObj.setHhRandomCount( rnCount );


        
        // create arrays of the unique chosen alternatives and the frequency with which those alternatives were chosen.
        numUniqueAlts = altFreqMap.size();
        Iterator<Integer> it = altFreqMap.keySet().iterator();
        int k = 0;
        while ( it.hasNext() ) {
            
            int alt = it.next();
            int freq = altFreqMap.get( alt );

            double prob = 0;
            if ( tour != null && tour.getTourCategoryIsAtWork() )
                prob = subtourProbabilitiesCache[purposeIndex][alt-1];
            else
                prob = probabilitiesCache[purposeIndex][alt-1];

            sample[k+1] = alt;
            corrections[k+1] = (float)Math.log( (double)freq/prob ); 

            k++;
        }
        
    }
    
    

    /**
     * @param choiceModel the ChoiceModelApplication object for the purpose
     * @param tour the tour object for whic destination choice is required, or null if a usual work/school location is being chosen 
     * @param person the person object for whom the choice is being made
     * @param purposeName the name of the purpose the choice is being made for - for logging
     * @param purposeindex the index associated with the purpose
     */
    private void computeSampleOfAlternativesChoiceProbabilities( ChoiceModelApplication choiceModel, DcSoaDMU dcSoaDmuObject, Tour tour, Person person, String purposeName, int purposeIndex, int origTaz ) {
        
        Household hhObj = person.getHouseholdObject();
        
        // set the hh object for this DMU object
        dcSoaDmuObject.setHouseholdObject ( hhObj );
        
        // set sample of alternatives choice DMU attributes
        dcSoaDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhTaz(), origTaz, 0 );

        
        // If the person making the choice is from a household requesting trace information,
        // create a trace logger header and write prior to the choiceModel computing utilities
        if ( hhObj.getDebugChoiceModels () ) {

            // prepare a trace log header that the choiceModel object will write prior to UEC trace logging
            String choiceModelDescription = "";
            String decisionMakerLabel = "";

            if ( tour == null ) {
                // null tour means the SOA choice is for a mandatory usual location choice
                choiceModelDescription = String.format ( "Usual Location Sample of Alternatives Choice Model for: Category=%s, Purpose=%s", tourCategory, purposeName );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            else {
                choiceModelDescription = String.format ( "Destination Choice Model for: Category=%s, Purpose=%s, TourId=%d", tourCategory, purposeName, tour.getTourId() );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            
            // log headers to traceLogger if the person making the choice is from a household requesting trace information
            choiceModel.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );

        }


    
        choiceModel.computeUtilities ( dcSoaDmuObject, dcSoaDmuObject.getDmuIndexValues(), destsAvailable[purposeIndex], destsSample[purposeIndex] );


        // the following order of assignment is important in mult-threaded context.
        // probabilitiesCache[][] is a trigger variable - if it is not null for any thread, the cumProbabilitiesCache[][] values
        // are used immediately, so the cumProbabilitiesCache values must be assigned before the probabilitiesCache
        // are assigned, which indicates cumProbabilitiesCache[][] values are ready to be used.
        if ( tour != null && tour.getTourCategoryIsAtWork() ) {
           	double[] cumProb = choiceModel.getCumulativeProbabilities();
        	double[] prob = choiceModel.getProbabilities(); 
        	subtourCumProbabilitiesCache[purposeIndex] = Arrays.copyOf(cumProb, cumProb.length);
        	subtourProbabilitiesCache[purposeIndex] = Arrays.copyOf(prob, prob.length); 
       }
        else {
          	double[] cumProb = choiceModel.getCumulativeProbabilities();
        	double[] prob = choiceModel.getProbabilities(); 
            cumProbabilitiesCache[purposeIndex] = Arrays.copyOf(cumProb, cumProb.length);
            probabilitiesCache[purposeIndex] = Arrays.copyOf(prob, prob.length); 
        }


        
        // If the person making the choice is from a household requesting trace information,
        // write choice model alternative info to the debug log file
        if ( hhObj.getDebugChoiceModels () ) {
            choiceModel.logAlternativesInfo ( String.format("%s Sample Of Alternatives Choice for origTaz=%d", purposeName, origTaz), String.format("HHID=%d", hhObj.getHhId()) );
        }

    }


    
    public int getSoaProbabilitiesCalculationCount() {
        return soaProbabilitiesCalculationCount;
    }
    
    public int getNumUniqueAlts() {
        return numUniqueAlts;
    }

    public int[] getSampleOfAlternatives() {
        return sample;
    }

    public float[] getSampleOfAlternativesCorrections() {
        return corrections;
    }
    
    public int getCurrentOrigTaz() {
        return currentOrigTaz;
    }
    
}