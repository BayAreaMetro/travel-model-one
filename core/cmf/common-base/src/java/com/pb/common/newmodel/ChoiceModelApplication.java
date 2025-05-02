package com.pb.common.newmodel;

/**
 * @author Jim Hicks
 *
 * Tour mode choice model application class
 */
import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

import java.io.File;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.HashMap;
import org.apache.log4j.Logger;


public class ChoiceModelApplication implements java.io.Serializable {

	private transient Logger logger = Logger.getLogger(ChoiceModelApplication.class);

	private transient Logger debugLogger = Logger.getLogger("cmDebug");

    private String description = "No description set";
    
	// get the array of alternatives for setting utilities
	private ConcreteAlternative[] alts;
	private String[] alternativeNames = null;
	private int numberOfAlternatives=0;

    private boolean[] defaultAltsAvailable;
    private int[] defaultAltsSample;
	
    private boolean[]                   altsAvailable;
    private int[]                       altsSample;

	private UtilityExpressionCalculator uec = null;
	private LogitModel root = null;

    // the rootLogsum is calculated when utilities are exponentiated
    private double                      rootLogsum           = 0.0;
    private int                         availabilityCount    = 0;
    private double[] cumProbs;
    private double[] elementalUtils;
    private double[] elementalProbs;    

    private long totalCount;
    private long otherCount;

	public ChoiceModelApplication (String controlFileName, int modelSheet, int dataSheet, HashMap<String,String> propertyMap, Object dmuClassObject, Logger logger) {
        // call the original constructor
        this(controlFileName, modelSheet, dataSheet, propertyMap, dmuClassObject);
        
        if (logger != null) {
            debugLogger = logger;
        }
    }

	public ChoiceModelApplication (String controlFileName, int modelSheet, int dataSheet, HashMap<String,String> propertyMap, Object dmuObject) {

        // create a UEC to get utilties for this choice model class
        File uecFile = new File(controlFileName);
        uec = new UtilityExpressionCalculator(uecFile, modelSheet, dataSheet, propertyMap,
                (VariableTable) dmuObject);

        // get the list of concrete alternatives from this uec
        alts = new ConcreteAlternative[uec.getNumberOfAlternatives()];
        alternativeNames = uec.getAlternativeNames();
        numberOfAlternatives = uec.getNumberOfAlternatives();
        
        // define availabilty and sample arrays to be used by default where all
        // alternatives are available and in the sample.
        // and specific choice model can compute utility based on a differnt set of
        // availability and sample by overriding
        // these defaults.
        defaultAltsAvailable = new boolean[numberOfAlternatives + 1];
        defaultAltsSample = new int[numberOfAlternatives + 1];

        // set the defaultAltsAvailable array to true for all choice alternatives
        for (int k = 1; k <= numberOfAlternatives; k++)
            defaultAltsAvailable[k] = true;

        // set the defaultAltsSample array to 1 for all choice alternatives
        for (int k = 1; k <= numberOfAlternatives; k++)
            defaultAltsSample[k] = 1;

        altsAvailable = defaultAltsAvailable;
        altsSample = defaultAltsSample;

        elementalUtils = new double[numberOfAlternatives];
        elementalProbs = new double[numberOfAlternatives];
        cumProbs = new double[numberOfAlternatives];

        // create the logit model defined in cm object's uec (specified in UEC
        // control file info passed into cm)
        createChoiceModel();
        
	}


    /**
	 * @return the logger
	 */
	public Logger getLogger() {
		return logger;
	}



	/**
	 * @param logger the logger to set
	 */
	public void setLogger(Logger logger) {
		this.logger = logger;
	}
	
    /**
	 * @return the debugLogger
	 */
	public Logger getDebugLogger() {
		return debugLogger;
	}


	/**
	 * @param debugLogger the debugLogger to set
	 */
	public void setDebugLogger(Logger debugLogger) {
		this.debugLogger = debugLogger;
	}


	/**
     * @return the UEC created for this choice model
     */
    public UtilityExpressionCalculator getUEC()
    {
        return uec;
    }

    /**
     * @return number of alternatives in choice model UEC.
     */
    public int getNumberOfAlternatives()
    {
        return numberOfAlternatives;
    }

    /**
     * create a MyLogit object for the tour mode choice model
     */
    public void createLogitModel()
    {

        // create and define a new LogitModel object
        root = new LogitModel("root", 0, numberOfAlternatives);

        for (int i = 0; i < numberOfAlternatives; i++)
        {
            alts[i] = new ConcreteAlternative(alternativeNames[i], new Integer(i + 1));
            root.addAlternative(alts[i]);
        }

    }

    /**
     * create a MyLogit object for the tour mode choice model
     */
    public void createNestedLogitModel(int[][] allocation, double[][] nestingCoefficients)
    {

        // create and define a new MyLogit object
        root = new LogitModel("root", 0, numberOfAlternatives);

        for (int i = 0; i < numberOfAlternatives; i++)
            alts[i] = new ConcreteAlternative(alternativeNames[i], new Integer(i + 1));

        // tree structure defines nested logit model hierarchy.
        // alternatives are numbered starting at 1.
        // values in allocation[0][i] refers to elemental alternatives in nested
        // logit model.
        // values in allocation[level][i] refers to parent branch number within
        // level.

        // initialize the dispersion parameters array with 1.0 and with one more row
        // than coefficents array
        double[] dispersionParameters = new double[nestingCoefficients.length + 1];
        dispersionParameters[dispersionParameters.length - 1] = 1.0;
        for (int i = dispersionParameters.length - 2; i >= 0; i--)
            dispersionParameters[i] = dispersionParameters[i + 1] / nestingCoefficients[i][0];

        int level = allocation.length - 1;
        root = buildNestedLogitModel(level, allocation, nestingCoefficients, dispersionParameters);

    }
	
    /**
     * create either a MNL or NL choice model of type MyLogit, depending on the
     * number of levels defined in the UEC control file.
     */
    private void createChoiceModel()
    {

        if (uec.getNumberOfNestedLogitLevels() == 1) createLogitModel();
        else createNestedLogitModel(uec.getNestedLogitNestingStructure(), uec
                .getNestedLogitNestingCoefficients());

    }

    private LogitModel buildNestedLogitModel(int level, int[][] allocation,
            double[][] nestingCoefficients, double[] dispersionParameters)
    {

        int a = 0;

        // level is the index number for the arrays in the allocation array for the
        // current nesting level
        int newLevel;
        int[][] newAllocation = new int[level][];
        double[][] newNestingCoefficients = new double[level][];
        LogitModel lm = null;
        LogitModel newLm = null;

        // find the maximum alternative number in the current nesting level
        int maxAlt = 0;
        int minAlt = 999999999;
        for (int i = 0; i < allocation[level].length; i++)
        {
            if (allocation[level][i] > maxAlt) maxAlt = allocation[level][i];
            if (allocation[level][i] < minAlt) minAlt = allocation[level][i];
        }

        // create an array of branches for each alternative up to the altCount
        ArrayList<Integer>[] branchAlts = new ArrayList[maxAlt - minAlt + 1];
        for (int i = 0; i < maxAlt - minAlt + 1; i++)
            branchAlts[i] = new ArrayList<Integer>();

        // add alllocation[level] element numbers to the ArrayLists for each branch
        int altCount = 0;
        for (int i = 0; i < allocation[level].length; i++)
        {
            int index = allocation[level][i];
            if (branchAlts[index - minAlt].size() == 0) altCount++;
            branchAlts[index - minAlt].add(i);
        }

        // create a MyLogit for this level
        // with the number of unique alternatives determined from allocation[level].
        lm = new LogitModel("level_" + level + "_alt_" + minAlt + "_to_" + maxAlt, 0, altCount);

        // dispersion parameters should always be set, even at level zero, from one
        // nest up
        lm.setDispersionParameter(dispersionParameters[level + 1]);

        boolean[] altSet = new boolean[maxAlt + 1];
        Arrays.fill(altSet, false);

        for (int i = 0; i <= maxAlt - minAlt; i++)
        {

            if (branchAlts[i].size() == 0) continue;

            // create a logit model for each alternative with at least 2
            // sub-alternatives.
            if (branchAlts[i].size() >= 1 && level > 0)
            {

                // dispersion parameters should always be set, even at level zero
                // lm.setDispersionParameter(dispersionParameters[level]);

                for (int k = 0; k < level; k++)
                {
                    newAllocation[k] = new int[branchAlts[i].size()];
                    newNestingCoefficients[k] = new double[branchAlts[i].size()];
                    for (int j = 0; j < branchAlts[i].size(); j++)
                    {
                        newAllocation[k][j] = allocation[k][(Integer) branchAlts[i].get(j)];
                        newNestingCoefficients[k][j] = nestingCoefficients[k][(Integer) branchAlts[i]
                                .get(j)];
                    }
                }

                // initialize the dispersion parameters array with value from parent
                double[] newDispersionParameters = new double[level + 1];
                newDispersionParameters[level] = dispersionParameters[level + 1]
                        / nestingCoefficients[level][(Integer) branchAlts[i].get(0)];
                for (int k = level - 1; k >= 0; k--)
                    newDispersionParameters[k] = newDispersionParameters[k + 1]
                            / newNestingCoefficients[k][0];

                // create the nested logit model
                newLevel = level - 1;
                newLm = buildNestedLogitModel(newLevel, newAllocation, newNestingCoefficients,
                        newDispersionParameters);

                lm.addAlternative(newLm);
            } else
            {
                a = allocation[level][(Integer) branchAlts[i].get(0)];
                if (altSet[a] == false)
                {
                    lm.addAlternative(alts[a]);
                    altSet[a] = true;
                }
            }
        }

        return lm;
    }

    /**
     * 
     * Calculate utilities and update utilities and availabilities in the logit model
     * passed in using the deafults - all alternatives initially available and in the
     * sample
     * 
     * @return The logsum
     */
    public double computeUtilities(Object dmuObject, IndexValues index)
    {

        double[] utilities = null;
        
        // get utilities for each alternative for this household
        long check1 = System.nanoTime();
        try {
            utilities = uec.solve(index, dmuObject, altsSample);
        }
        catch (Exception e) {
            logger.error("exception caught solving UEC", e);
            throw new RuntimeException();
        }
        long check2 = System.nanoTime();
        totalCount = check2 - check1;

        // set utility for each alternative
        availabilityCount = 0;
        for (int a = 0; a < alts.length; a++)
        {
            alts[a].setAvailability(altsAvailable[a + 1]);
            if (altsSample[a + 1] == 1 && altsAvailable[a + 1])
                alts[a].setAvailability((utilities[a] > -299.0));
            alts[a].setUtility(utilities[a]);
            if (altsSample[a + 1] == 1 && altsAvailable[a + 1] && utilities[a] > -299.0)
                availabilityCount++;
        }

        root.setAvailability();

        // call root.getUtility() to calculate exponentiated utilties. The logit
        // model logsum is returned.
        rootLogsum = root.getUtility();

        // calculate logit probabilities
        root.calculateProbabilities();

        otherCount = System.nanoTime() - check2;
        
        return rootLogsum;
    }

    /*
     * calculate utilities and update utilities and availabilities in the logit model
     * passed in
     */
    public void computeUtilities(Object dmuObject, IndexValues index, boolean[] availability,
            int[] sample)
    {

        double[] utilities = null;
        
        altsAvailable = availability;
        altsSample = sample;

        for (int i = 0; i < altsAvailable.length; i++)
            if (!altsAvailable[i]) altsSample[i] = 0;

        // get utilities for each alternative for this household
        long check1 = System.nanoTime();
        try {
            utilities = uec.solve(index, dmuObject, altsSample);
        }
        catch (Exception e) {
            logger.error("exception caught solving UEC", e);
            throw new RuntimeException();
        }
        long check2 = System.nanoTime();
        totalCount = check2 - check1;

        // set utility for each alternative
        availabilityCount = 0;
        for (int a = 0; a < alts.length; a++)
        {
            alts[a].setAvailability(altsAvailable[a + 1]);
            if (altsSample[a + 1] == 1 && altsAvailable[a + 1])
                alts[a].setAvailability((utilities[a] > -299.0));
            alts[a].setUtility(utilities[a]);
            if (altsSample[a + 1] == 1 && altsAvailable[a + 1] && utilities[a] > -299.0)
                availabilityCount++;
        }

        root.setAvailability();

        // call root.getUtility() to calculate exponentiated utilties. The logit
        // model logsum is returned.
        rootLogsum = root.getUtility();

        // calculate logit probabilities
        root.calculateProbabilities();

    }

    public LogitModel getRootLogitModel()
    {
        return root;
    }

    /*
     * apply the logit choice UEC to calculate the logsum for this household's choice
     * model
     */
    public double getLogsum()
    {
        return rootLogsum;
    }

    public String[] getAlternativeNames()
    {
        return alternativeNames;
    }

    public ConcreteAlternative[] getAlternatives()
    {
        return alts;
    }

    /**
     * @return the double[modelEntries][numAlternatives] of answers determined by the
     *         UEC
     */
    public double[][] getUecAnswers()
    {
        return uec.getAnswersArray();
    }

    /**
     * return the array of elemental alternative utilities for this logit choice
     * model
     */
    public double[] getUtilities()
    {

        for (int i = 0; i < numberOfAlternatives; i++)
            elementalUtils[i] = alts[i].getUtility();
 
        return elementalUtils;

    }

    /**
     * return the array of elemental alternative probabilities for this logit choice
     * model
     */
    /**
     * return the array of elemental alternative probabilities for this logit choice model
     */
    public double[] getProbabilities(){
        
        for (int i=0; i < numberOfAlternatives; i++) {
            elementalProbs[i] = alts[i].getProbability();
        }
        
        return elementalProbs;
    
    }

    public int getAvailabilityCount()
    {
        return availabilityCount;
    }

    public boolean[] getAvailabilities()
    {
        return altsAvailable;
    }

    /*
     * apply the tour mode choice UEC to calculate the logit choice probabilities
     * and return a chosen alternative for this household's tour mode choice.  The 
     * number of the alternative is 1-based.
     */
    public int getChoiceResult( double randomNumber ) {

        ConcreteAlternative chosen = (ConcreteAlternative) root.chooseAlternative( randomNumber );
        int alternativeNumber = chosen.getNumber();
        
        return alternativeNumber;

    }

    public static int getMonteCarloSelection(double[] probabilities, double randomNumber)
    {

        int returnValue = 0;

        double sum = probabilities[0];
        for (int i = 0; i < probabilities.length - 1; i++)
        {
            if (randomNumber <= sum)
            {
                returnValue = i;
                break;
            } else
            {
                sum += probabilities[i + 1];
                returnValue = i + 1;
            }
        }

        return returnValue;

    }

    /**
     * return the array of cumulative probabilities for this logit choice model
     */
    public double[] getCumulativeProbabilities(){
        

    	double[] probabilities = getProbabilities();
        cumProbs[0] = probabilities[0];
        for (int i=1; i < numberOfAlternatives; i++) 
            cumProbs[i] = cumProbs[i-1] + probabilities[i];
        
        cumProbs[numberOfAlternatives-1] = 1.0;
        
        return cumProbs;
    
    }

    public int getChoiceIndexFromCumProbabilities (double[] cumProbabilities, double randomNum ) {
        int chosenIndex = binarySearchDouble ( cumProbabilities, randomNum );
        return chosenIndex + 1;
    }
    
    
    public void logAlternativesInfo(String choiceModelLabel, String decisionMakerLabel,
            Logger myLogger)
    {
        logInfo(choiceModelLabel, decisionMakerLabel, myLogger);
    }

    public void logAlternativesInfo(String choiceModelLabel, String decisionMakerLabel)
    {
        logInfo(choiceModelLabel, decisionMakerLabel, debugLogger);
    }

    private void logInfo(String choiceModelLabel, String decisionMakerLabel, Logger myLogger)
    {

        double[] utils = getUtilities();
        double[] probs = getProbabilities();
        double[] cumProbs = getCumulativeProbabilities();

        myLogger.debug("****************************************************************************************************************");
        myLogger.debug(String.format("HH DEBUG:  %s Alternatives Info for %s", choiceModelLabel, decisionMakerLabel));
        myLogger.debug("****************************************************************************************************************");
        myLogger.debug(String.format("HH DEBUG:  %-6s  %-12s  %16s  %16s  %16s  %12s", "alt", "name", "utility", "probability", "cumProb", "availability"));

        for (int a = 0; a < alts.length; a++)
        {
            int altIndex = a + 1;
            String altName = alternativeNames[a];
            double altUtil = utils[a];
            double altProb = probs[a];
            double altCumProb = cumProbs[a];
            boolean altAvail = alts[a].isAvailable();

            if (altAvail)
                myLogger.debug(String.format(
                        "HH DEBUG:  %-6d  %-12s  %16.8e  %16.8e  %16.8e  %12s", altIndex, altName,
                        altUtil, altProb, altCumProb, Boolean.toString(altAvail)));
        }

    }

    public void logSelectionInfo(String choiceModelLabel, String decisionMakerLabel,
            double randomNumber, int chosenAlt)
    {
        debugLogger.debug(String.format("HH DEBUG:  %s result chosen for %s is %d with rn %.8f",
                choiceModelLabel, decisionMakerLabel, chosenAlt, randomNumber));
    }

    /**
     * For each nest within the logit model, prints out the utilities, probabilities,
     * and logsum.
     * 
     * @param choiceModelLabel
     * @param decisionMakerLabel
     */
    public void logLogitCalculations(String choiceModelLabel, String decisionMakerLabel)
    {
        debugLogger
                .debug("****************************************************************************************************************");
        debugLogger.debug(String.format("HH DEBUG:  %s Logit Calculations for %s", choiceModelLabel,
                decisionMakerLabel));
        debugLogger
                .debug("****************************************************************************************************************");

        logLogitCalculations(root);
    }

    /**
     * For each nest within the logit model, prints out the utilities, probabilities,
     * and logsum.
     * 
     * @param nest
     */
    private void logLogitCalculations(LogitModel nest)
    {

        debugLogger.info("Nest Name = " + nest.getName() + "   NestingCoefficient = "
                + String.format("%.8f", 1 / nest.getDispersionParameter()) + "   Logsum = "
                + String.format("%.8f", nest.getUtility()));

        String altNameList = "Alternatives    = ";
        String utilList = "  Utilities     = ";
        String probList = "  Probabilities = ";

    	Alternative[] nestAlts = nest.getAlternatives();
       	for (int i=0; i<nestAlts.length; i++) {
    		Alternative alt =  nestAlts[i];
    		altNameList += String.format("%24s", alt.getName());
    		utilList    += String.format("%24.8f", alt.getUtility()); 
    		probList    += String.format("%24.8f", alt.getProbability()); 
    	}
        debugLogger.info(altNameList);
        debugLogger.info(utilList);
        debugLogger.info(probList);

       	for (int i=0; i<nestAlts.length; i++) {
    		Alternative alt = nestAlts[i];
    		if (alt instanceof LogitModel) {
    			LogitModel subNest = (LogitModel) alt; 
    			logLogitCalculations(subNest); 
    		}
    	}
    }
    
    public void logDataValues(Logger localLogger, int origTaz, int destTaz) {
        uec.logDataValues(localLogger, origTaz, destTaz, 0);
    }

    public void logUECResults ( Logger localLogger ){
        logUECResults( localLogger, description );
    }
    
    public void logUECResults ( Logger localLogger, String uecName ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName);                
    }
    
    public void logUECResults ( Logger localLogger, String uecName, int maxAltsToLog ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName, maxAltsToLog );                
    }
    
    public void logUECResultsSpecificAlts ( Logger localLogger, String uecName, int[] altsToLog ){
        // write UEC calculation results to separate model specific log file
        uec.logAnswersArray( localLogger, uecName, altsToLog );                
    }
    
    public void choiceModelUtilityTraceLoggerHeading(String choiceModelDescription,
            String decisionMakerLabel)
    {

        // get the trace logger for the UEC and log header information for this
        // specific choice model and decision maker prior to computing utilities
        Logger traceLogger = uec.getTraceLogger();

        int numSideStars = 3;

        int maxStringLength = Math.max(choiceModelDescription.length(), decisionMakerLabel.length());
        int numTopStars = maxStringLength + numSideStars * 4;

        String sideStars = "";
        for (int i = 0; i < numSideStars; i++)
            sideStars += "*";

        String topStars = "";
        for (int i = 0; i < numTopStars; i++)
            topStars += "*";

        // make a format statement to use to print the two header lines
        String myFormat = String.format("%%-%ds%%-%ds%%%ds", (numSideStars * 2), maxStringLength, (numSideStars * 2));

        String firstLine = String.format(myFormat, sideStars, choiceModelDescription, sideStars);
        String secondLine = String.format(myFormat, sideStars, decisionMakerLabel, sideStars);

        traceLogger.debug("");
        traceLogger.debug(topStars);
        traceLogger.debug(firstLine);
        traceLogger.debug(secondLine);
        traceLogger.debug(topStars);

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
        
    public long getTotalCount() {
        return totalCount;
    }
    public long getOtherCount() {
        return otherCount;
    }

    /**
     * Set a description of this ChoiceModelApplication object which could be used for debug logging
     * @param descr Description of the expressions being solved
     */
    public void setDescription( String descr ) {
        description = descr;
    }
    
}
