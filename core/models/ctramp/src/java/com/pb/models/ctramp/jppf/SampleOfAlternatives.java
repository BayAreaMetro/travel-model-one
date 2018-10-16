package com.pb.models.ctramp.jppf;

import com.pb.common.calculator.IndexValues;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.SoaDMU;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Random;

import org.apache.log4j.Logger;

/**
 * Created on Jul 22, 2003
 * @author Jim Hicks
 *
 */
public class SampleOfAlternatives implements java.io.Serializable {

   
    private ChoiceModelApplication cm;
    private int numAlts;
    private int numSubzones;
    private int sampleSize;

    // these will be dimensioned with the number of unique alternatives (+1) determined for the decision makers 
    HashMap<Integer,Integer> altFreqMap;
    private int[] finalSample;
    private float[] sampleCorrectionFactors;
    private int numUniqueAlts;

    
    
    public SampleOfAlternatives ( ChoiceModelApplication cm, int numSubzones, int sampleSize ) {
    //public SampleOfAlternatives ( ChoiceModelApplication cm, int numDmuSegments, Object[] objectLocks, double[][] probabilitiesCacheElement, double[][] cumProbabilitiesCacheElement ) {

        this.cm = cm;
        numAlts = cm.getUEC().getNumberOfAlternatives();
        this.numSubzones = numSubzones;
        this.sampleSize = sampleSize;
        
        altFreqMap = new HashMap<Integer,Integer>( sampleSize );
        finalSample = new int[sampleSize+1];
        sampleCorrectionFactors = new float[sampleSize+1];
        
    }

    
    
	/*
	 * apply the sample of alternatives choice model to calculate the sample, sample probabilities, and sample frequencies
	 */
	public void applySampleOfAlternativesChoiceModel ( String purposeName, SoaDMU soaDmuObject, IndexValues dmuIndex, int origTaz, boolean[] soaAvailability ) {

	    Logger soaLogger = Logger.getLogger("stopSoa");
	    
	    altFreqMap.clear();
	    
        if ( soaDmuObject.getHouseholdObject().getDebugChoiceModels () ) {
            String choiceModelDescription = String.format ( "Stop Location SOA Choice Model for: Purpose=%s", purposeName );
            String decisionMakerLabel = String.format ( "HH=%d, origTaz=%d", soaDmuObject.getHouseholdObject().getHhId(), origTaz );
            cm.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }
        
        
		cm.computeUtilities ( soaDmuObject, dmuIndex );
		double[] probabilitiesList = cm.getProbabilities();
		double[] cumProbabilitiesList = cm.getCumulativeProbabilities();
        
        // debug output
        if( soaDmuObject.getHouseholdObject().getDebugChoiceModels() ){

            // write choice model alternative info to debug log file
            String choiceModelDescription = String.format("%s Stop Location SOA Choice for origTaz=%d", purposeName, origTaz);
            String decisionMakerLabel = String.format("HHID=%d", soaDmuObject.getHouseholdObject().getHhId() );
            cm.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );

            // write UEC calculation results to separate model specific log file
            String loggingHeader = choiceModelDescription + decisionMakerLabel;
            cm.logUECResults( soaLogger, loggingHeader );
            
        }

        
        
        // loop over sampleSize, select alternatives based on probabilitiesList[dmuSegment], and count frequency of alternatives chosen.
        // may include duplicate alternative selections.
        int chosenAlt = -1;
        
        // check to see if the cumulative probability of the next to last alternative is 0.
        // if so, then no alternatives were eligable to be in the sample - probably due to the tour mode being walk
        // and no stop locations had walk available for both legs.
        // if this case hapens, let the stop location be the origin zone.
//        if ( cumProbabilitiesList[numAlts - 2] == 0.0 ) {
//            
//            // set the chosen alternative to the alternative number corresponding to the origin taz, no walk access subzone. 
//            chosenAlt = origTaz*numSubzones - 2;
//            
//            // set final sample and corrections accordingly
//            finalSample = new int[2];
//            sampleCorrectionFactors = new float[2];
//
//            finalSample[1] = chosenAlt;
//            //sampleCorrectionFactors[k+1] = (float)Math.log( (double)freq/prob ); 
//            sampleCorrectionFactors[1] = (float)Math.log( 1.0 ); 
//        }
//        else {
            
            Random hhRandom = soaDmuObject.getHouseholdObject().getHhRandom();
            int rnCount = soaDmuObject.getHouseholdObject().getHhRandomCount();
            // when household.getHhRandom() was applied, the random count was incremented, assuming a random number would be drawn right away.
            // so let's decrement by 1, then increment the count each time a random number is actually drawn in this method.
            rnCount --;
            
            for (int i=0; i < sampleSize; i++) {
                
                double rn = hhRandom.nextDouble();
                rnCount++;
                chosenAlt = cm.getChoiceIndexFromCumProbabilities( cumProbabilitiesList, rn );
                
                // write choice model alternative info to log file
                if ( soaDmuObject.getHouseholdObject().getDebugChoiceModels () ) {
                    cm.logSelectionInfo ( String.format("%s Sample Of Alternatives Choice for dmuSegment=%d", purposeName, origTaz), String.format("HHID=%d, rnCount=%d", soaDmuObject.getHouseholdObject().getHhId(), rnCount), rn, chosenAlt );
                }
                
                int freq = 0;
                if ( altFreqMap.containsKey(chosenAlt) )
                    freq = altFreqMap.get( chosenAlt );
                altFreqMap.put(chosenAlt, (freq + 1) );
                
            }

            // sampleSize random number draws were made from this Random object, so update the count in the hh's Random.
            soaDmuObject.getHouseholdObject().setHhRandomCount( rnCount );

            
            // create arrays of the unique chosen alternatives and the frequency with which those alternatives were chosen.
            numUniqueAlts = altFreqMap.size();
            Iterator<Integer> it = altFreqMap.keySet().iterator();
            int k = 0;
            while ( it.hasNext() ) {
                
                int alt = it.next();
                int freq = altFreqMap.get( alt );

                double prob = 0;
                prob = probabilitiesList[alt-1];

                finalSample[k+1] = alt;
                sampleCorrectionFactors[k+1] = (float)Math.log( (double)freq/prob ); 

                k++;
            }

//        }

	}


    
    
    public int getNumUniqueAlts() {
        return numUniqueAlts;
    }

    
	/*
	 * return array with sample of alternatives
	 */
	public int[] getSampleOfAlternatives () {
		return finalSample;
	}


	/*
	 * return array with sample of alternatives correction factors
	 */
	public float[] getSampleCorrectionFactors () {
		return sampleCorrectionFactors;
	}


    public void choiceModelUtilityTraceLoggerHeading( String choiceModelDescription, String decisionMakerLabel ) {
        cm.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
    }

}
