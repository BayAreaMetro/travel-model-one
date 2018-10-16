package com.pb.models.ctramp.old;

import com.pb.common.calculator.IndexValues;
import com.pb.common.model.ChoiceModelApplication;
import com.pb.models.ctramp.SoaDMU;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Random;


/**
 * Created on Jul 22, 2003
 * @author Jim Hicks
 *
 */
public class SampleOfAlternatives implements java.io.Serializable {

    // the follow arrays are set to the array handles passed in at the time this object is created
    private double[][] probabilitiesList = null;
    private double[][] cumProbabilitiesList = null;
    
    //private static final Object objLock = new Object();
    

    ChoiceModelApplication cm;
    int numAlts;

    // these will be dimensioned with the number of unique alternatives (+1) determined for the decision makers 
    int[] finalSample;
    float[] sampleCorrectionFactors;

    
    
	public SampleOfAlternatives ( ChoiceModelApplication cm, int numDmuSegments, double[][] probabilitiesCacheElement, double[][] cumProbabilitiesCacheElement ) {

        this.cm = cm;
        numAlts = cm.getUEC().getNumberOfAlternatives();
        
        // the probabilities arrays used in this object are equal to the static probabilities cache array element passed in by the object using this one.
        probabilitiesList = probabilitiesCacheElement;
        cumProbabilitiesList = cumProbabilitiesCacheElement;

    }

    
    
	/*
	 * apply the sample of alternatives choice model to calculate the sample, sample probabilities, and sample frequencies
	 */
	public void applySampleOfAlternativesChoiceModel ( String purposeName, SoaDMU soaDmuObject, IndexValues dmuIndex, int dmuSegment, int sampleSize, boolean[] soaAvailability ) {

        // these will be dimensioned with the number of unique alternatives determined for the decision makers 
        int[] altList;
        int[] altListFreq;

        
        int[] soaSample = new int[numAlts+1];
		for (int i=0; i < soaSample.length; i++) {
		    if (soaAvailability[i])
		        soaSample[i] = 1;
		}


        // re-use sample of alternative probabilities if they've already been computed for a dmuSegment value; otherwise compute them.
   		if ( probabilitiesList[dmuSegment] == null ) {
   	        //synchronized (objLock) {
    			cm.computeUtilities ( soaDmuObject, dmuIndex, soaAvailability, soaSample );
                probabilitiesList[dmuSegment] = cm.getProbabilities();
                cumProbabilitiesList[dmuSegment] = cm.getCumulativeProbabilities();
   	        //}
   	        
            // write choice model alternative info to log file
            if ( soaDmuObject.getHouseholdObject().getDebugChoiceModels () ) {
                cm.logAlternativesInfo ( String.format("%s Sample Of Alternatives Choice for dmuSegment=%d", purposeName, dmuSegment), String.format("HHID=%d", soaDmuObject.getHouseholdObject().getHhId() ) );
            }
        }
        
        

        int rnCount = soaDmuObject.getHouseholdObject().getHhRandomCount();
        Random hhRandom = soaDmuObject.getHouseholdObject().getHhRandom();
        double rn = hhRandom.nextDouble();

		// loop over sampleSize, select alternatives based on probabilitiesList[dmuSegment], and count frequency of alternatives chosen.
		// may include duplicate alternative selections.
        HashMap<Integer,Integer> altFreqMap = new HashMap<Integer,Integer>();
		for (int i=0; i < sampleSize; i++) {
            
			int chosenAlt = cm.getChoiceIndexFromCumProbabilities( cumProbabilitiesList[dmuSegment], rn ) + 1;
            
            
            // write choice model alternative info to log file
            if ( soaDmuObject.getHouseholdObject().getDebugChoiceModels () ) {
                cm.logSelectionInfo ( String.format("%s Sample Of Alternatives Choice for dmuSegment=%d", purposeName, dmuSegment), String.format("HHID=%d", soaDmuObject.getHouseholdObject().getHhId() ), rn, chosenAlt );
            }
            

            
            int freq = 0;
			if ( altFreqMap.containsKey(chosenAlt) )
                freq = altFreqMap.get( chosenAlt );
            altFreqMap.put(chosenAlt, (freq + 1) );
            
		}

        // sampleSize random number draws were made from this Random object, so update the count in the hh's Random.
        soaDmuObject.getHouseholdObject().setHhRandomCount( rnCount + sampleSize );

        int numUniqueAlts = altFreqMap.keySet().size(); 

		
		// create arrays of the unique chosen alternatives,
		// and the frequency with which those alternatives were chosen.
        altList = new int[numUniqueAlts];
        altListFreq = new int[numUniqueAlts];
        Iterator<Integer> it = altFreqMap.keySet().iterator();
        int k = 0;
        while ( it.hasNext() ) {
            int key = (Integer)it.next();
            int value = (Integer)altFreqMap.get(key);
            altList[k] = key;
            altListFreq[k] = value;
            k++;
        }
        
		finalSample = new int[numUniqueAlts+1];
		sampleCorrectionFactors = new float[numUniqueAlts+1];

		
		// loop through the arrays, construct a finalSample[] and a sampleCorrectionFactors[],
		// and compute the slcLogsumCorrection over the set of unique alternatives in the sample.
		for (k=0; k < numUniqueAlts; k++) {
			int alt = altList[k];
			int freq = altListFreq[k];
			double prob = probabilitiesList[dmuSegment][alt-1];  

			finalSample[k+1] = alt;
			sampleCorrectionFactors[k+1] = (float)Math.log( (double)freq/prob ); 
		}

        
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
