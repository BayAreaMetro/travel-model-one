/**
 * 
 */
package com.pb.models.ctramp.jppf;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Random;

import org.apache.log4j.Logger;

import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.matrix.Matrix;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.newmodel.ConcreteAlternative;
import com.pb.common.newmodel.UtilityExpressionCalculator;
import com.pb.common.util.PropertyMap;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Stop;
import com.pb.models.ctramp.StopDestChoiceSize;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.jppf.StopDestinationSampleOfAlternativesModel.StopSoaResult;

/**
 * This class extends the StopDestinationSampleOfAlternativesModel to allow for a computationally more efficient 
 * option for creating the stop destination choice sample. The computationally more efficient option involves applying 
 * a simplified utility specification that includes only distance measures and size terms:
 * 		U(o,s,d) = beta * Dist(o,s) + beta * Dist(s,d) + logSizeTerm 
 * Furthermore, the same beta value is assumed for all stop purposes. These simplifications make it possible to pre-compute
 * EXP(beta*Dist(i,j)) once for all zone pairs i-j. When the destination choice sample is to be generated for a given stop, 
 * the exponentiated utilities are calculated by looking up the appropriate cells in exponentiated distance matrix. This approach
 * cuts back the number of exponentiation operations in the computation. 
 * 
 * Note that this generic approach is suitable mainly for highway modes because the simplifying assumptions may not apply to 
 * other modes such as transit, walk and bike. The choice between using the generic model versus the standard model is specified 
 * at runtime in the properties file for each mode. 
 *    
 * @author guojy
 *
 */
public class StopDestinationSampleOfAlternativesModelGeneric extends
		StopDestinationSampleOfAlternativesModel {

    private transient Logger 	logger = Logger.getLogger(StopDestinationSampleOfAlternativesModelGeneric.class);
    private static final int 	SOA_GENERIC_UEC_MODEL_PAGE = 11;	//the page for distance calculation is added to the end 
    private static final String PROPERTIES_USE_GENERIC_SOA_MODEL  = "StopLocationSoa.useGenericSOAModel";
    
    private boolean[] useGenericSOAModel;	//indexed by mode to indicate if the generic model is to be applied to a given mode
    ChoiceModelApplication genericSOAModel;
	private Matrix exponentiatedDistanceMatrix;    //by origin TAZ, destination TAZ 

	StopDestChoiceSize sizeModel;
	
	/**
	 * @param propertyMap
	 * @param tazDataManager
	 * @param sizeModel
	 * @param modelStructure
	 * @param dmuFactory
	 */
	public StopDestinationSampleOfAlternativesModelGeneric( HashMap<String, String> propertyMap, TazDataIf tazDataManager,
			StopDestChoiceSize sizeModel, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory) {
		// call the superclass' constructor
		super(propertyMap, tazDataManager, sizeModel, modelStructure, dmuFactory);
				
		this.sizeModel = sizeModel;
		
        //an array of booleans by mode, indexed from 0!
        useGenericSOAModel = PropertyMap.getBooleanArrayFromPropertyMap(propertyMap, PROPERTIES_USE_GENERIC_SOA_MODEL);

        // create UEC for generic model 
     	genericSOAModel = new ChoiceModelApplication(stopSoaUecFileName, SOA_GENERIC_UEC_MODEL_PAGE, 
     												 STOP_SOA_DATA_SHEET, propertyMap, (VariableTable) stopSoaDmu);
        genericSOAModel.setLogger(this.logger);
        genericSOAModel.setDebugLogger(this.logger);

    	calculateExponentiatedDistanceMatrix(tazDataManager);
	}
	

	/**
	 * This method initializes and calculates the exponentiatedDistanceMatrix array. 
	 * 
	 */
	private void calculateExponentiatedDistanceMatrix(TazDataIf tazDataManager){
		
	    logger.info("Calculating stop destination soa model intermediate stop exponentiated distance matrix");
		
        // Retrieve the array of TAZ numbers and determine the size of the exponentiated distance matrix
        int[] tazs = tazDataManager.getTazs();
        int maxTaz = tazs[0];
        for (int i = 1; i<tazs.length; i++)
        	if (tazs[i]>maxTaz)
        		maxTaz = tazs[i];      
        
     	// Initialize exponentiated distance matrix
     	exponentiatedDistanceMatrix = new Matrix("Exp_Dist_Matrix","Exponentiated Distance Matrix",maxTaz+1,maxTaz+1);
    	exponentiatedDistanceMatrix.setExternalNumbersZeroBased(tazs);

    	// Reference to Alternatives
        TableDataSet altData = genericSOAModel.getUEC().getAlternativeData();
        
    	//iterate through origin zones, solve the UEC and store the results in the matrix
    	for(int i=0; i<tazs.length; i++){
        	
        	int originTaz = (int) tazs[i]; 
        		
        	//set origin taz in dmu (destination set in UEC by alternative)
        	//stopSoaDmu.setDmuState(originTaz, originTaz, originTaz, null,null,false,false,null);
        	stopSoaDmu.setDmuState(originTaz);

        	//Calculate utilities & probabilities
        	genericSOAModel.computeUtilities(stopSoaDmu, stopSoaDmu.getDmuIndexValues());

        	if (originTaz==186)
        		genericSOAModel.logUECResults( logger, "calculate weighted distance");

        	//Store exponentiated distance utilities, where U_ij = beta*D_ij
            double[] distanceUtilities = genericSOAModel.getUtilities();
            	
            for(int j=0; j<distanceUtilities.length; j++){
            		
            	double expUtility = Math.exp(distanceUtilities[j]);
            	// map alternative number to destination taz number
            	int destTaz = (int) altData.getValueAt(j+1,"dtaz");
            	exponentiatedDistanceMatrix.setValueAt(originTaz, destTaz, (float)expUtility);
            		  
     		}
     	}
    	logger.info("Finished calculating stop location soa model exponentiated distance matrix");
	}
    

    public StopSoaResult computeDestinationSampleOfAlternatives( Stop s ) {
    	
    	// determine dmu state parameters
        boolean inbound = s.isInboundStop();
        int stopOrig = s.getOrig();
        boolean hasKids = false;
        Tour t = s.getTour();
        int tourDest = inbound ? t.getTourOrigTaz() : t.getTourDestTaz();
        String tourPurpose = t.getTourPrimaryPurpose();      
        Household hh = t.getPersonObject().getHouseholdObject();
        
        // compute index for looking up size terms
        int lookupIndex;
        String stopPurpose = modelStructure.getPrimaryPurposeForIndex( s.getDestPurposeIndex() );
        if ( stopPurpose.equals(ModelStructure.ESCORT_PURPOSE_NAME) ) {
            hasKids = hh.getNumChildrenUnder19() > 0;
            lookupIndex = getPurposeLookupIndex( ModelStructure.ESCORT_PURPOSE_NAME, inbound, hasKids );
        } else {
            lookupIndex = getPurposeLookupIndex( stopPurpose, inbound );
        }
        double[] stopLocSize = logSizeTerms.get(lookupIndex);

        // set DMU state, including size terms
        stopSoaDmu.setDmuState( hh.getHhTaz(), stopOrig, tourDest, hh, t, inbound, hasKids, stopLocSize );

        // apply the appropriate choice model depending on the mode and the useGenericSOAModel property values
    	int mode = s.getTour().getTourModeChoice();
    	if (useGenericSOAModel[mode - 1])
    		// apply the generic model, store results in soaResult
    		sampleFromGenericUtilities(s,lookupIndex);
    	else { 
    		// apply the purpose-specific model through the DMU
            int uecPage = uecPageMap.get( tourPurpose );
            SampleOfAlternatives soaModel = soa.get( uecPage );            
            soaModel.applySampleOfAlternativesChoiceModel ( tourPurpose, stopSoaDmu, stopSoaDmu.getDmuIndexValues(), stopOrig, destinationAvailability.get(lookupIndex) );
            // store results 
            soaResult.setSample( soaModel.getSampleOfAlternatives() );
            soaResult.setCorrections( soaModel.getSampleCorrectionFactors() );
            soaResult.setNumUniqueAltsInSample( soaModel.getNumUniqueAlts() );
    	}
        soaResult.setStopLocationSize( stopLocSize );

        return soaResult;
    }

    /**
     * This method is modified from com.pb.models.ctramp.jppf.SampleOfAlternatives.applySampleOfAlternativesChoiceModel and
     * com.pb.ompo.visitormodel.VisitorStopLocationChoiceModel.chooseSample 
     * 
     * @param s
     * @param purposeLookupIndex 
     */
	private void sampleFromGenericUtilities(Stop s, int purposeLookupIndex) {
	    
		// log alternative info if applicable
        if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) {
            String choiceModelDescription = String.format ( "Stop Location SOA (Generic) Choice Model for: Purpose=%s", modelStructure.getPrimaryPurposeForIndex(s.getDestPurposeIndex()) );
            String decisionMakerLabel = String.format ( "HH=%d, orig=%d", stopSoaDmu.getHouseholdObject().getHhId(), s.getOrig() );
            logger.info("****************************************************************************************************************");
            logger.info(String.format("HH DEBUG:  %s Alternatives Info for %s", choiceModelDescription, decisionMakerLabel));
        }       

    	// initialize arrays of choice probabilities and cumulative probabilities for stop sampling
    	int numAlternatives = genericSOAModel.getUEC().getNumberOfAlternatives();
        double[] prob = new double[numAlternatives+1];
        double[] cumProb = new double[numAlternatives+1];
        Arrays.fill(prob, 0);
        Arrays.fill(cumProb, 0);
				
        // compute choice probabilities using the generic model
        computeChoiceProbabilities(purposeLookupIndex, prob, cumProb);
		
        Random hhRandom = stopSoaDmu.getHouseholdObject().getHhRandom();
        int rnCount = stopSoaDmu.getHouseholdObject().getHhRandomCount();
        // when household.getHhRandom() was applied, the random count was incremented, assuming a random number would be drawn right away.
        // so let's decrement by 1, then increment the count each time a random number is actually drawn in this method.
        rnCount --;
            
        // loop over sampleSize, select alternatives based on cumProb[] computed earlier, and count frequency of alternatives chosen.
        // may include duplicate alternative selections.
        HashMap<Integer,Integer> altFreqMap = new HashMap<Integer,Integer>( sampleSize );
        int chosenAlt = -1;
       
        for (int i=0; i < sampleSize; i++) {
                
        	double rn = hhRandom.nextDouble();
        	rnCount++;
        	
        	// make a choice based on random number
    		for(int j=1; j<=numAlternatives; j++){
    			if(rn<cumProb[j]){
    				chosenAlt = j;
    				break;
    			}
    		}

    		if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) 
				logger.info(String.format("HH DEBUG:  Chose alt %d with rn %.8f", chosenAlt, rn));
               
    		// update frequency count of the chosen alternative having been chosen
        	int freq = 0;
    	   	if ( altFreqMap.containsKey(chosenAlt) )
    	   		freq = altFreqMap.get( chosenAlt );
    	   	altFreqMap.put(chosenAlt, (freq + 1) );                
        }

        // sampleSize random number draws were made from this Random object, so update the count in the hh's Random.
        stopSoaDmu.getHouseholdObject().setHhRandomCount( rnCount );

        // create arrays of the unique chosen alternatives and the frequency with which those alternatives were chosen.
        float[] sampleCorrectionFactors = new float[sampleSize+1];
        int[] finalSample = new int[sampleSize+1];
        Iterator<Integer> it = altFreqMap.keySet().iterator();
        int k = 0;
        while ( it.hasNext() ) {              
        	int alt = it.next();
        	int freq = altFreqMap.get( alt );
        	
            double probability = prob[alt];
            
            k++;
        	finalSample[k] = alt;
        	sampleCorrectionFactors[k] = (float)Math.log( (double)freq/probability ); 
        }
       
        soaResult.setSample( finalSample );
        soaResult.setCorrections( sampleCorrectionFactors );
        soaResult.setNumUniqueAltsInSample( k );

	}

	private double[] computeChoiceProbabilities(int purposeLookupIndex, double[] prob, double[] cumProb) {
		
    	int numAlternatives = genericSOAModel.getUEC().getNumberOfAlternatives();
    	int[] altToZone = tazDataManager.getAltToZoneArray();
    	int[] altToSubZone = tazDataManager.getAltToSubZoneArray();
    	
    	// initialize an array of exponentiated utilities for stop sampling
        double[] expUtilities = new double[numAlternatives+1];
    	Arrays.fill(expUtilities, 0);

		//calculate exponentiated utilities for all stop alternatives
    	int originTaz = stopSoaDmu.getDmuIndexValues().getOriginZone();
    	int destinationTaz = stopSoaDmu.getDmuIndexValues().getDestZone();
		double sumExp = 0;

		// log alternative info if applicable
        if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) {
            logger.info("****************************************************************************************************************");
            logger.info("Calculating exponentiated utilities:");            
            logger.info(String.format("%-6s  %-6s  %16s  %16s  %16s  %16s", "alt", "zone", "size term", "osExpUtility", "sdExpUtility", "expUtilities"));
        }       

		for(int i=1; i<=numAlternatives; i++){
			
			// look up the unlogged size term to avoid having to exponentiate
			int stopTaz = altToZone[i];			//1-based array
			int subzone = altToSubZone[i];		//1-based array
			String[] purposeSegments = getMainAndSubPurposeFromLookupIndex(purposeLookupIndex);
			double size = sizeModel.getDcSize(purposeSegments[0].toLowerCase(), purposeSegments[1].toLowerCase(), stopTaz, subzone );
			size = size + 1; 	//plus 1 to ensure equivalence with how size terms are incorporated in the mode-specific model
								//particularly important when size==0
			
            // look up the exponentiated weighted distance terms
			float osExpUtility = exponentiatedDistanceMatrix.getValueAt(originTaz, stopTaz);
			float sdExpUtility = exponentiatedDistanceMatrix.getValueAt(stopTaz, destinationTaz);
		
			// calculate exponentiated utility
			expUtilities[i] = osExpUtility * sdExpUtility * size;
			sumExp +=expUtilities[i];
			
	        if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) {
	        	logger.info( String.format ("%-6d  %-6d %-6d  %-6d  %16.8e  %16.8e  %16.8e  %16.8e", 
	            		originTaz, destinationTaz, i, stopTaz, size, osExpUtility, sdExpUtility, expUtilities[i]));
	        }
		}
		
		// log alternative info if applicable
        if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) {
            logger.info("****************************************************************************************************************");
            logger.info(String.format("HH DEBUG:  %-6s  %-12s  %16s  %16s  %16s", "alt", "zone", "exp_util", "probability", "cum. probability"));
        }       

		// calculate choice probabilities and cumulative probabilities
    	for(int i=1; i<=numAlternatives; i++) {
			prob[i] = expUtilities[i]/sumExp;
			cumProb[i] = cumProb[i-1]+prob[i];

	        if ( stopSoaDmu.getHouseholdObject().getDebugChoiceModels () ) {
                logger.info(String.format("HH DEBUG:  %-6d  %-12s  %16.8e  %16.8e  %16.8e", 
                						i, altToZone[i],expUtilities[i], prob[i], cumProb[i]));
	        }
    	}
    	
    	return prob;
     }   
 
}
