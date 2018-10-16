package com.pb.common.model;

/**
 * @author Jim Hicks
 *
 * Tour mode choice model application class
 */
import com.pb.common.calculator.UtilityExpressionCalculator;
import com.pb.common.calculator.IndexValues;
import com.pb.common.util.SeededRandom;

import java.io.File;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;


public class ChoiceModelApplication implements java.io.Serializable {

	static Logger logger = Logger.getLogger(ChoiceModelApplication.class);
    protected static Logger debugLogger = Logger.getLogger("cmDebug");

	// get the array of alternatives for setting utilities
	private ConcreteAlternative[] alts;
	private String[] alternativeNames = null;
	private int numberOfAlternatives=0;

    private boolean[] defaultAltsAvailable;
    private int[] defaultAltsSample;
	
	private UtilityExpressionCalculator uec = null;
	private LogitModel root = null;
    private double[] utilities = null;
	
	// the rootLogsum is calculated when utilities are exponentiated
	private double rootLogsum = 0.0;
	private int availabilityCount = 0;

    private double randomNumber;
    private int chosenAlt ;  
    
    
    

	public ChoiceModelApplication (String controlFileName, int modelSheet, int dataSheet, HashMap<String,String> propertyMap, Class dmuClassObject) {

          // create a UEC to get utilties for this choice model class
        uec = new UtilityExpressionCalculator(new File(controlFileName), modelSheet, dataSheet, propertyMap, dmuClassObject);

        // get the list of concrete alternatives from this uec
        alts= new ConcreteAlternative[uec.getNumberOfAlternatives()];
        alternativeNames = uec.getAlternativeNames();
        numberOfAlternatives = uec.getNumberOfAlternatives();

        
        // define availabilty and sample arrays to be used by default where all alternatives are available and in the sample.
        // and specific choice model can compute utility based on a differnt set of availability and sample by overriding
        // these defaults.
        defaultAltsAvailable = new boolean[numberOfAlternatives+1];
        defaultAltsSample = new int[numberOfAlternatives+1];

        // set the defaultAltsAvailable array to true for all choice alternatives
        for (int k=1; k <= numberOfAlternatives; k++)
            defaultAltsAvailable[k] = true;

        // set the defaultAltsSample array to 1 for all choice alternatives
        for (int k=1; k <= numberOfAlternatives; k++)
            defaultAltsSample[k] = 1;

        
        // create the logit model defined in cm object's uec (specified in UEC control file info passed into cm)
        createChoiceModel();
        
	}


	
	/**
	 * @return the UEC created for this choice model
	 */
	public UtilityExpressionCalculator getUEC() {
		return uec;
	}
	
    
    /**
     * @return number of alternatives in choice model UEC. 
     */
    public int getNumberOfAlternatives() {
        return numberOfAlternatives;
    }
    
	
	/**
	 * create a LogitModel object for the tour mode choice model
	 */
	public void createLogitModel() {

		// create and define a new LogitModel object
		root = new LogitModel("root", numberOfAlternatives);

		for(int i=0; i < numberOfAlternatives; i++) {
			alts[i]  = new ConcreteAlternative(alternativeNames[i], new Integer(i+1));
			root.addAlternative (alts[i]);
		}

	}
	
	
	/**
	 * create a LogitModel object for the tour mode choice model
	 */
	public void createNestedLogitModel(int[][] allocation, double[][] nestingCoefficients) {

        
		// create and define a new LogitModel object
		root= new LogitModel("root", numberOfAlternatives);


        
		for(int i=0; i < numberOfAlternatives; i++)
			alts[i]  = new ConcreteAlternative(alternativeNames[i], new Integer(i+1));


		// tree structure defines nested logit model hierarchy.
		// alternatives are numbered starting at 1.
		// values in allocation[0][i] refers to elemental alternatives in nested logit model.
		// values in allocation[level][i] refers to parent branch number within level.

        // initialize the dispersion parameters array with 1.0 and with one more row  than coefficents array
        double[] dispersionParameters = new double[nestingCoefficients.length+1];
        dispersionParameters[dispersionParameters.length-1] = 1.0;
        for (int i=dispersionParameters.length-2; i >= 0; i--)
            dispersionParameters[i] = dispersionParameters[i+1]/nestingCoefficients[i][0];
        

        
		int level = allocation.length - 1;
		root = buildNestedLogitModel (level, allocation, nestingCoefficients, dispersionParameters);
		
	}
	

    /** 
     * create either a MNL or NL choice model of type LogitModel, depending on the number of levels defined in the UEC control file.
     */
    private void createChoiceModel() {
        
        if ( uec.getNumberOfNestedLogitLevels() == 1 )
            createLogitModel();
        else
            createNestedLogitModel(uec.getNestedLogitNestingStructure(), uec.getNestedLogitNestingCoefficients());
    
    }
    
    
	private LogitModel buildNestedLogitModel (int level, int[][] allocation, double[][] nestingCoefficients, double[] dispersionParameters) {

		int a=0;

		// level is the index number for the arrays in the allocation array for the current nesting level
		int newLevel;
		int[][] newAllocation = new int[level][];
        double[][] newNestingCoefficients = new double[level][];
		LogitModel lm = null;
		LogitModel newLm = null;

		// find the maximum alternative number in the current nesting level
		int maxAlt = 0;
		int minAlt = 999999999;
		for (int i=0; i < allocation[level].length; i++) {
            if (allocation[level][i] > maxAlt)
                maxAlt = allocation[level][i];
            if (allocation[level][i] < minAlt)
                minAlt = allocation[level][i];
		}

		// create an array of branches for each alternative up to the altCount
		ArrayList<Integer>[] branchAlts = new ArrayList[maxAlt-minAlt+1];
		for (int i=0; i < maxAlt-minAlt+1; i++)
			branchAlts[i] = new ArrayList<Integer>();

        
		// add alllocation[level] element numbers to the ArrayLists for each branch
		int altCount = 0;
		for (int i=0; i < allocation[level].length; i++) {
            int index = allocation[level][i];
			if (branchAlts[index-minAlt].size() == 0)
				altCount++;
			branchAlts[index-minAlt].add( i );
		}
			
		// create a LogitModel for this level
		// with the number of unique alternatives determined from allocation[level].
		lm = new LogitModel( "level_"+level+"_alt_"+minAlt+"_to_"+maxAlt, altCount );

		// dispersion parameters should always be set, even at level zero, from one nest up
		lm.setDispersionParameter(dispersionParameters[level+1]);
        
		boolean[] altSet = new boolean[maxAlt+1];
		Arrays.fill (altSet, false);

		
		for (int i=0; i <= maxAlt-minAlt; i++) {
            
			if (branchAlts[i].size() == 0)
				continue;
							
            // create a logit model for each alternative with at least 2 sub-alternatives.
			if (branchAlts[i].size() >= 1 && level > 0) {

				// dispersion parameters should always be set, even at level zero
				//lm.setDispersionParameter(dispersionParameters[level]);
				
				for (int k=0; k < level; k++) {
					newAllocation[k] = new int[branchAlts[i].size()];
                    newNestingCoefficients[k] = new double[branchAlts[i].size()];
					for (int j=0; j < branchAlts[i].size(); j++) {
						newAllocation[k][j] = allocation[k][(Integer)branchAlts[i].get(j)];
                        newNestingCoefficients[k][j] = nestingCoefficients[k][(Integer)branchAlts[i].get(j)];
					}
				}							

		        // initialize the dispersion parameters array with value from parent
		        double[] newDispersionParameters = new double[level+1];
		        newDispersionParameters[level] = dispersionParameters[level+1] / nestingCoefficients[level][(Integer)branchAlts[i].get(0)]; 
		        for (int k=level-1; k >= 0; k--)
		            newDispersionParameters[k] = newDispersionParameters[k+1]/newNestingCoefficients[k][0];
		        
				// create the nested logit model
				newLevel = level - 1;	
				newLm = buildNestedLogitModel (newLevel, newAllocation, newNestingCoefficients, newDispersionParameters);
								
				lm.addAlternative(newLm);
			}
			else {
				a = allocation[level][(Integer)branchAlts[i].get(0)];
				if ( altSet[a] == false) {
					lm.addAlternative(alts[a]);
					altSet[a] = true;
				}
			}
		}

		return lm;
	}


	
    /*
     * calculate utilities and update utilities and availabilities in the logit model passed in
     * using the deafults - all alternatives initially available and in the sample
     */
    public void computeUtilities ( Object dmuObject, IndexValues index ) {

        int[] sample = defaultAltsSample;
        boolean[] availability = defaultAltsAvailable;

        // get utilities for each alternative for this household
        utilities = uec.solve( index, dmuObject, sample );
        
        
        //set utility for each alternative
        availabilityCount = 0;
        for(int a=0; a < alts.length; a++){
            alts[a].setAvailability( availability[a+1] );
            if (sample[a+1] == 1 && availability[a+1])
                alts[a].setAvailability( (utilities[a] > -99.0) );
            alts[a].setUtility( utilities[a] );
            if (sample[a+1] == 1 && availability[a+1] && utilities[a] > -99.0)
                availabilityCount++;
        }
        
        
        
        root.computeAvailabilities();

        // call root.getUtility() to calculate exponentiated utilties.  The logit model logsum is returned.
        rootLogsum =  root.getUtility();
        
        // calculate logit probabilities
        root.calculateProbabilities();
        
    }
    
    
    /*
	 * calculate utilities and update utilities and availabilities in the logit model passed in
	 */
	public void computeUtilities (Object dmuObject, IndexValues index, boolean[] availability, int[] sample) {

        for ( int i=0; i < availability.length; i++ )
            if ( ! availability[i] )
                sample[i] = 0;

        
        // get utilities for each alternative for this household
		utilities = uec.solve( index, dmuObject, sample );


		//set utility for each alternative
		availabilityCount = 0;
		for(int a=0; a < alts.length; a++){
			alts[a].setAvailability( availability[a+1] );
			if (sample[a+1] == 1 && availability[a+1])
				alts[a].setAvailability( (utilities[a] > -99.0) );
			alts[a].setUtility( utilities[a] );
			if (sample[a+1] == 1 && availability[a+1] && utilities[a] > -99.0)
				availabilityCount++;
		}
		
		
		
		root.computeAvailabilities();

		// call root.getUtility() to calculate exponentiated utilties.  The logit model logsum is returned.
		rootLogsum =  root.getUtility();
		
		// calculate logit probabilities
		root.calculateProbabilities();
		
	}


    public LogitModel getRootLogitModel() {
        return root;
    }
    
	/*
	 * apply the logit choice UEC to calculate the logsum for this household's choice model
	 */
	public double getLogsum() {
		return rootLogsum;
	}
	
	
    public String[] getAlternativeNames() {
        return alternativeNames;
    }
    
    public ConcreteAlternative[] getAlternatives() {
    	return alts; 
    }

    
    /**
     * @return the double[modelEntries][numAlternatives] of answers determined by the UEC
     */
    public double[][] getUecAnswers() {
        return uec.getAnswersArray();
    }
    
    
    /**
     * return the array of elemental alternative utilities for this logit choice model
     */
    public double[] getUtilities() {

        HashMap<String,Double> elementalUtilMap = new HashMap<String,Double>();
        root.getElementalUtilitiesHashMap(elementalUtilMap);
        
        double[] elementalUtils = new double[numberOfAlternatives];
        
        for (int i=0; i < numberOfAlternatives; i++) {
            double util = (Double)elementalUtilMap.get(alternativeNames[i]);
            elementalUtils[i] = util;
        }
        
        return elementalUtils;

    }

    
    
    /**
     * return the array of elemental alternative probabilities for this logit choice model
     */
    public double[] getProbabilities(){
        
        HashMap<String,Double> elementalProbMap = new HashMap<String,Double>();
        root.getElementalProbabilitiesHashMap(elementalProbMap);
        
        double[] elementalProbs = new double[numberOfAlternatives];
        
        for (int i=0; i < numberOfAlternatives; i++) {
            double prob = (Double)elementalProbMap.get(alternativeNames[i]);
            elementalProbs[i] = prob;
        }
        
        return elementalProbs;
    
    }
    
    
    
	public int getAvailabilityCount () {
		return availabilityCount;
	}



	/*
	 * apply the tour mode choice UEC to calculate the logit choice probabilities
	 * and return a chosen alternative for this household's tour mode choice
	 */
	public int getChoiceResult() {

		int chosenAlt = 0;

        ConcreteAlternative chosen = (ConcreteAlternative) root.chooseElementalAlternative();
		String chosenAltName= chosen.getName();

		// save chosen alternative in  householdChoice Array
		for(int a=0; a < alts.length; a++) {
			if (chosenAltName.equals(alternativeNames[a])) {
				chosenAlt = a+1;
				break;
			}
		}

		return chosenAlt;

	}

    
	
    /*
     * apply the tour mode choice UEC to calculate the logit choice probabilities
     * and return a chosen alternative for this household's tour mode choice
     */
    public int getChoiceResult( Random randomObject ) {

        chosenAlt = -1;

        randomNumber = randomObject.nextDouble();
        ConcreteAlternative chosen = (ConcreteAlternative) root.chooseElementalAlternative( randomNumber );
        String chosenAltName= chosen.getName();

        // save chosen alternative in  householdChoice Array
        for(int a=0; a < alts.length; a++) {
            if (chosenAltName.equals(alternativeNames[a])) {
                chosenAlt = a+1;
                break;
            }
        }


        return chosenAlt;

    }



    /*
     * apply the tour mode choice UEC to calculate the logit choice probabilities
     * and return a chosen alternative for this household's tour mode choice
     */
    public int getChoiceResult( double randomNumber ) {

        this.randomNumber = randomNumber;
        chosenAlt = -1;

        ConcreteAlternative chosen = (ConcreteAlternative) root.chooseElementalAlternative( randomNumber );
        String chosenAltName= chosen.getName();

        // save chosen alternative in  householdChoice Array
        for(int a=0; a < alts.length; a++) {
            if (chosenAltName.equals(alternativeNames[a])) {
                chosenAlt = a+1;
                break;
            }
        }


        return chosenAlt;

    }



    public static int getMonteCarloSelection (double[] probabilities) {

        double randomNumber = SeededRandom.getRandom();
        int returnValue = 0;

        double sum = probabilities[0];
        for (int i=0; i < probabilities.length-1; i++) {
            if (randomNumber <= sum) {
                returnValue = i;
                break;
            }
            else {
                sum += probabilities[i+1];
                returnValue = i+1;
            }
        }

        return returnValue;

    }

    public static int getMonteCarloSelection (double[] probabilities, double randomNumber) {

        int returnValue = 0;

        double sum = probabilities[0];
        for (int i=0; i < probabilities.length-1; i++) {
            if (randomNumber <= sum) {
                returnValue = i;
                break;
            }
            else {
                sum += probabilities[i+1];
                returnValue = i+1;
            }
        }

        return returnValue;

    }

    public int getMonteCarloSelection (double[] probabilities, Random randomObject) {

        randomNumber = randomObject.nextDouble();
        int returnValue = 0;

        double sum = probabilities[0];
        for (int i=0; i < probabilities.length-1; i++) {
            if (randomNumber <= sum) {
                returnValue = i;
                break;
            }
            else {
                sum += probabilities[i+1];
                returnValue = i+1;
            }
        }

        return returnValue;

    }

    /**
     * return the array of cumulative probabilities for this logit choice model
     */
    public double[] getCumulativeProbabilities(){
        
        HashMap<String,Double> elementalProbMap = new HashMap<String,Double>();
        root.getElementalProbabilitiesHashMap(elementalProbMap);
        
        double[] cumProbs = new double[numberOfAlternatives];
        
        cumProbs[0] = (Double)elementalProbMap.get(alternativeNames[0]);
        for (int i=1; i < numberOfAlternatives; i++) {
            double prob = (Double)elementalProbMap.get(alternativeNames[i]);
            cumProbs[i] = cumProbs[i-1] + prob;
        }
        cumProbs[numberOfAlternatives-1] = 1.0;
        
        return cumProbs;
    
    }
    
    
    public int getChoiceIndexFromCumProbabilities (double[] cumProbabilities, Random randomObject ) {
        randomNumber = randomObject.nextDouble();
        int chosenIndex = binarySearchDouble (cumProbabilities, randomNumber);
        chosenAlt = chosenIndex + 1;
        return chosenIndex;
    }
    
    
    
    public int getChoiceIndexFromCumProbabilities (double[] cumProbabilities, Double randomNum ) {
        randomNumber = randomNum;
        int chosenIndex = binarySearchDouble (cumProbabilities, randomNumber);
        chosenAlt = chosenIndex + 1;
        return chosenIndex;
    }
    
    
    
    public void logAlternativesInfo ( String choiceModelLabel, String decisionMakerLabel ) {
                
        double[] utils = getUtilities();
        double[] probs = getProbabilities();
        double[] cumProbs = getCumulativeProbabilities();

        
        debugLogger.debug( String.format ( "HH DEBUG:  %s Alternatives Info for %s", choiceModelLabel, decisionMakerLabel ) );
        debugLogger.debug( String.format ( "HH DEBUG:  %-6s  %-12s  %16s  %16s  %16s  %12s", "alt", "name", "utility", "probability", "cumProb", "availability" ) );
        
        for(int a=0; a < alts.length; a++) {
            int altIndex = a+1;
            String altName = alternativeNames[a];
            double altUtil = utils[a];
            double altProb = probs[a];
            double altCumProb = cumProbs[a];
            boolean altAvail = alts[a].isAvailable();

            if ( altAvail )
                debugLogger.debug( String.format ( "HH DEBUG:  %-6d  %-12s  %16.8e  %16.8e  %16.8e  %12s", altIndex, altName, altUtil, altProb, altCumProb, Boolean.toString(altAvail) ) );
        }

    }
    
    
    
    public void logSelectionInfo ( String choiceModelLabel, String decisionMakerLabel ) {
        debugLogger.debug( String.format ( "HH DEBUG:  %s result chosen for %s is %d with rn %.8f", choiceModelLabel, decisionMakerLabel, chosenAlt, randomNumber ) );
    }
    

    public void logSelectionInfo ( String choiceModelLabel, String decisionMakerLabel, double randomNumber, int chosenAlt ) {
        debugLogger.debug( String.format ( "HH DEBUG:  %s result chosen for %s is %d with rn %.8f", choiceModelLabel, decisionMakerLabel, chosenAlt, randomNumber ) );
    }
    
    /**
     * For each nest within the logit model, prints out the utilities,
     * probabilities, and logsum.  
     * 
     * @param choiceModelLabel
     * @param decisionMakerLabel
     */
    public void logLogitCalculations ( String choiceModelLabel, String decisionMakerLabel ) {
        debugLogger.debug( "****************************************************************************************************************" );
        debugLogger.debug( String.format ( "HH DEBUG:  %s Logit Calcuations for %s", choiceModelLabel, decisionMakerLabel ) );
        debugLogger.debug( "****************************************************************************************************************" );

        logLogitCalculations(root); 
    }
    
    public void logUECResults ( Logger localLogger, String uecName ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName);                
    }
    
    public void logUECResults ( Logger localLogger, String uecName, int maxAltsToLog ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName, maxAltsToLog );                
    }
    
    public void logUECResults ( Logger localLogger, String uecName, int[] specificAltsToLog ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName, specificAltsToLog );                
    }
    
    /**
     * For each nest within the logit model, prints out the utilities,
     * probabilities, and logsum.  
     * 
     * @param nest
     */
    private void logLogitCalculations(LogitModel nest) {

    	debugLogger.info("Nest Name = " + nest.getName() 
    			+ "   NestingCoefficient = " + String.format("%.8f", 1/nest.getDispersionParameter())
    			+ "   Logsum = " + String.format("%.8f",nest.getUtility()));
    	
    	String altNameList = "Alternatives    = "; 
    	String utilList    = "  Utilities     = "; 
    	String probList    = "  Probabilities = ";
    	
    	ArrayList nestAlts = nest.getAlternatives();
    	double[] probs = nest.getProbabilities();
    	for (int i=0; i<nestAlts.size(); i++) {
    		Alternative alt = (Alternative) nestAlts.get(i);
    		altNameList += String.format("%24s", alt.getName());
    		utilList    += String.format("%24.8f", alt.getUtility()); 
    		probList    += String.format("%24.8f", probs[i]); 
    	}
    	debugLogger.info(altNameList); 
    	debugLogger.info(utilList); 
    	debugLogger.info(probList); 
    	    	
    	for (int i=0; i<nestAlts.size(); i++) {
    		Alternative alt = (Alternative) nestAlts.get(i);
    		if (alt.getClass().equals(LogitModel.class)) {
    			LogitModel subNest = (LogitModel) alt; 
    			logLogitCalculations(subNest); 
    		}
    	}
    }
    
    /**
     * 
     * @param cumProbabilities cumulative probabilities array
     * @param entry target to search for in array
     * @return the array index i where cumProbabilities[i] < entry and cumProbabilities[i-1] <= entry.  
     */
    private int binarySearchDouble (double[] cumProbabilities, double entry) {
        
        // lookup index for 0 <= entry < 1.0 in cumProbabilities
        // cumProbabilities values are assumed to be in range: [0,1], and
        // cumProbabilities[cumProbabilities.length-1] must equal 1.0


        // if entry is outside the allowed range, return -1
        if ( entry < 0 || entry >= 1.0 ) {
            logger.error ( "entry = " + entry + " is outside of allowable range for cumulative distribution [0,...,1.0)" );
            return -1;
        }

        // if cumProbabilities[cumProbabilities.length-1] is not equal to 1.0, return -1
        if ( cumProbabilities[cumProbabilities.length-1] != 1.0 ) {
            logger.error ( "cumProbabilities[cumProbabilities.length-1] = " + cumProbabilities[cumProbabilities.length-1] + " must equal 1.0" );
            return -1;
        }
        
        
        int hi = cumProbabilities.length;
        int lo = 0;
        int mid = (hi -lo)/2;
        
        int safetyCount = 0;
        

        // if mid is 0, 
        if ( mid == 0 ) {
            if ( entry < cumProbabilities[0] )
                return 0;
            else
                return 1;
        }
        else if ( entry < cumProbabilities[mid] && entry >= cumProbabilities[mid-1] ) {
            return mid;
        }

        
        while (true) {
        
            if ( entry < cumProbabilities[mid] ) {
                hi = mid;
                mid = (hi + lo)/2;
            }
            else {
                lo = mid;
                mid = (hi + lo)/2;
            }

            
            // if mid is 0, 
            if ( mid == 0 ) {
                if ( entry < cumProbabilities[0] )
                    return 0;
                else
                    return 1;
            }
            else if ( entry < cumProbabilities[mid] && entry >= cumProbabilities[mid-1] ) {
                return mid;
            }
        
            
            if ( safetyCount++ > cumProbabilities.length ) {
                logger.error ( "binary search stuck in the while loop" );
                throw new RuntimeException( "binary search stuck in the while loop" );
            }
                
        }
        
    }
    
    
    public void choiceModelUtilityTraceLoggerHeading( String choiceModelDescription, String decisionMakerLabel ) {
        
        // get the trace logger for the UEC and log header information for this specific choice model and decision maker prior to computing utilities
        Logger traceLogger = uec.getTraceLogger();
        
        int numSideStars = 3;
        
        int maxStringLength = Math.max( choiceModelDescription.length(), decisionMakerLabel.length() );
        int numTopStars = maxStringLength + numSideStars*4;
        
        String sideStars = "";
        for ( int i=0; i < numSideStars; i++ )
            sideStars += "*";
                
        String topStars = "";
        for ( int i=0; i < numTopStars; i++ )
            topStars += "*";
                
        // make a format statement to use to print the two header lines
        String myFormat = String.format( "%%-%ds%%-%ds%%%ds", (numSideStars*2), maxStringLength, (numSideStars*2) );
        
        String firstLine = String.format( myFormat, sideStars, choiceModelDescription, sideStars );
        String secondLine = String.format( myFormat, sideStars, decisionMakerLabel, sideStars );

        traceLogger.debug( "" );
        traceLogger.debug( topStars );
        traceLogger.debug( firstLine );
        traceLogger.debug( secondLine );
        traceLogger.debug( topStars );

    }
    
}
