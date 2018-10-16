/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.newmodel;

import com.pb.common.math.MathUtil;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.text.NumberFormat;

/**
 *  The LogitModel is a type of DiscreteChoiceModel
 *  with a Gumbel-distributed error term.  The LogitModel can be a multinomial
 *  model or a nest of a nested-logit model.  The method calls to getUtility() and
 *  calculateProbabilities() apply to all nests and alternatives underneath it.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
 * 
 * @revised 11/2012
 * Removed constant, probability and expUtility arrays.  Speed up implementation over old LogitModel class.
 */
public class LogitModel implements Alternative, Serializable {

    protected double dispersionParameter;
    protected static NumberFormat nf = NumberFormat.getInstance();
    protected static Logger logger = Logger.getLogger(LogitModel.class);
    
    protected String name;

    private double utility;
    private double expUtility;
    private double probability;
    private Alternative[] alternatives;
    private boolean debug;
    
	private int alternativeCounter; //track number of alternatives added
    private boolean isAvailable;
    private int alternativeNumber;

    /**
    Use this constructor if you know how many alternatives.
    @param n      The name of this model.
    @param number The number of this model.
    @param numberOfAlternatives   The number of alternatives.
    */
    public LogitModel(String n, int number, int numberOfAlternatives) {
    	
        alternatives = new Alternative[numberOfAlternatives];
        dispersionParameter = 1.0;
        setName(n);
        alternativeNumber = number;
        isAvailable=true;
        probability=1.0;
    }
    
    
    /**
     * Discover whether the LogitModel is being debugged.
     * @return  true if being debugged, else false
     */
    public boolean isDebug() {
		return debug;
	}

    /**
     * Set the logit model debug
     * @param debug  True if debug, else false
     */
	public void setDebug(boolean debug) {
		this.debug = debug;
		
		for(int i=0;i<alternatives.length;++i){
			if(alternatives[i]==null)
				continue;
			alternatives[i].setDebug(debug);
		}
	}

    /**
     * Get the number of alternatives in this logit model.
     * 
     * @return number of alternatives in logit model.
     */
    public int getNumberOfAlternatives(){
    	return alternatives.length;
    }

	/**
     * Clear probabilities and set availabilities to true
     * for model and submodel nests.
     *   The structure is not reset.
     */
    public void clear(){
        
        for(int i=0;i<alternatives.length;++i){
            alternatives[i].setAvailability(true);
            alternatives[i].setProbability(0);
            
           if (alternatives[i] instanceof LogitModel)
                 ((LogitModel) alternatives[i]).clear();
        }
    }
    
    /**
    Set availability for this model. If it is a nest and it is set to be unavailable, all
    subalternatives are also unavailable.  However, the opposite is not true; a nest can be
    available and some of its sub-alternatives may be unavailable.
    
    @param available
    */
    public void setAvailability(boolean available) {

        isAvailable = available;
        // if the model isn't available, neither are any of its alternatives.
        if(!available)
            for (int alt = 0; alt < alternatives.length; ++alt) {
                Alternative thisAlt = alternatives[alt];
                thisAlt.setAvailability(available);
            }
    }
    /**
    Get availability of this model.
    @return true if this model is available (ie has at least one available sub-alternative).
    */
    public boolean isAvailable() {
        
        return isAvailable;
    }

    /**
    Add an alternative to the collection.
    @param a the alternative to add into the choice set
    */
    public void addAlternative(Alternative a) {
        //If this alternative debug is true, then subalternatives set to true as well.
        if (debug) {
           logger.info(
                "Adding alternative "
                    + a.getName()
                    + " to LogitModel "
                    + this.getName()
                    + ".");
            //logger.debug("Adding alternative "+a.getName()+" to LogitModel "+this.getName()+".");
           a.setDebug(true); 
        }
        alternatives[alternativeCounter]=a;
        ++alternativeCounter;
    }
    /**
    Set name
    @param n Model name
    */
    public void setName(String n) {
        name = n;
    }
    /**
    Get name.
    @return Model name
    */
    public String getName() {
        return name;
    }
    /**
    Get the dispersion parameter for this model.
    @return  The dispersion parameter
    */
    public double getDispersionParameter() {
        return dispersionParameter;
    }
    /**
    Set the dispersion parameter for this model.
    @param disp  The dispersion parameter.
    */
    public void setDispersionParameter(double disp) {
        dispersionParameter = disp;
    }
    /**
    Calculates and returns the composite utility (logsum) for all available
    alternatives in this LogitModel.  This method will exponentiate the utilites,
    but the utilities must be calculated for each alternative prior to calling
    this method.
    @return The composite utility (logsum value) of all the alternatives. If
    this alternative is not available (ie no sub-alterantives are available) the
    return value is 0.
    */
    public double getUtility() {

        double sum = 0;
        double base = 0;
        for (int i = 0; i < alternatives.length; ++i) {
            if (alternatives[i].isAvailable()) {
                double utility = alternatives[i].getUtility();

                //if alternative has a very large negative utility, it isn't available
                if (utility  < -400) {
	                alternatives[i].setExpUtility(0.0);
	     			continue;
                }
                setAvailability(true);

                double expUtility = MathUtil.exp(dispersionParameter * utility);
                alternatives[i].setExpUtility(expUtility);
                sum += expUtility;
            } else {
                alternatives[i].setExpUtility(0.0);
                alternatives[i].setProbability(0.0);
            }
        }
        if (isAvailable()) {
            base = (1 / dispersionParameter) * MathUtil.log(sum);

            return base;
        }
        // if nothing available, return a bad utility
        return -999;
    }


    /**
    Writes a header to the log file for subsequent debug statements
    in the getUtility() method.  Call this method prior to calling
    getUtility().
    */
    public void writeUtilityHeader() {
        if (debug) {
        	logger.info("\n");
            logger.info(
                "Alternative Name           Utility               ExpUtility   ");
            logger.info(
                "--------------------------------------------------------------");
        }
    }

    /**
    * Calculate the probabilities based on the choice utilities.
    */
    public void calculateProbabilities() {

        if (!isAvailable()) {
            return;
        }
 
        //cycle through alternatives, compute sum(expUtilities)
        double sum = 0;
        for (int i = 0; i < alternatives.length; ++i) {
            sum += alternatives[i].getExpUtility();
        }

        //cycle through alternatives, compute expUtility/sum(expUtilities) * probability (of nest)
        for (int i = 0; i < alternatives.length; i++) {
                
        		double expUtility = alternatives[i].getExpUtility();
                if(expUtility>0 && sum > 0)
                    alternatives[i].setProbability(expUtility / sum * this.probability);
                else
                    alternatives[i].setProbability(0.0);

                if (alternatives[i] instanceof LogitModel)
                     ((LogitModel) alternatives[i]).calculateProbabilities();

        }
    
    }
    
    /**
     * get an array of all the alternatives in this logit model
     */
    public Alternative[] getAlternatives(){
    	return alternatives;
    }
    /**
     * Choose an alternative (use Math.random())
     * @return an alternative chosen according to probability distribution
     */
    public Alternative chooseAlternative(){
    	
    	double rnum = Math.random();
    	return chooseAlternative(rnum, 0.0);
    }
    
    
    /**
     * Choose an alternative with a random number
     * @return an alternative chosen according to probability distribution
     */
    public Alternative chooseAlternative(double rnum){
    	
    	return chooseAlternative(rnum, 0.0);
    }
    
    /**
     * Choose an alternative with a random number.
     */
    public Alternative chooseAlternative(double rnum, double startProbability){

        double sum = startProbability;
        Alternative a = null;
        for (int i = 0; i < alternatives.length; i++) {

        	  if ( alternatives[i].getProbability() == 0 )
                continue;

            sum += alternatives[i].getProbability();

            if ( rnum <= sum && a==null) 
                return alternatives[i].chooseAlternative(rnum, sum-alternatives[i].getProbability());
            
        }

        logger.error("Could not choose alternative.");
        logger.error("Discrete Choice model random number: " + rnum);
        logger.error("Discrete Choice model cummulative probability: " + sum);
        return null;
    }

    /**
    Set availabilities of all nests based on availability of sub-alternatives
    */
    public void setAvailability() {

    	isAvailable = false;
    	//if the logit model or elemental alternative under this alternative is available,
        //then this alternative is available.
    	for (int i = 0; i < alternatives.length; ++i) {
            if (alternatives[i].getAvailability())
                setAvailability(true);
        }
        
     }
    
	/**
	 * Get the availability of the model
	 * @return True if the model is available, else false
	 */
	public boolean getAvailability(){

		//if any alternatives under this one have a utility less than -999 or is available, return true
		for (int i = 0; i < alternatives.length; ++i) {
	        if(alternatives[i].getAvailability() || alternatives[i].getUtility()>-500)
	        	return true;
		}
		return false;
	}

	/**
     * Get the choice probabilities for underlying alternatives.
     * @return an array containing the choice probabilities.  Probabilities
     * will be 0 for non-available alternatives.
     * @param probabilities An array sized to the number of alternatives in the model
     * @return  The array filled with probabilities
     */
    public double[] getProbabilities(double[] probabilities) {
        
        for(int i=0;i<probabilities.length;++i)
        	probabilities[i]= alternatives[i].getProbability();
        return probabilities;
    }

    /*
     * Get the array of exponentiated utilities for this model.
     * Must pass method an array of doubles that is sized to the number
     * of alternatives in the model
     */
    public double[] getExponentiatedUtilities(double[] expUtilities){
        for(int i=0;i<expUtilities.length;++i)
        	expUtilities[i]= alternatives[i].getExpUtility();
        return expUtilities;
    }

    /**
     * @param logger the logger to set
     */
    public static void setLogger(Logger logger) {
        LogitModel.logger = logger;
    }

	/**
	 * Get the exponentiated utility
	 */
	public double getExpUtility() {
		return expUtility;
	}

	/**
	 * Set the exponentiated utility
	 */
	public void setExpUtility(double expUtility) {
		this.expUtility=expUtility;
		
	}

	/**
	 * Get the probability of the logit model
	 */
	public double getProbability() {
		return probability;
	}

	/**
	 * Set the probability of the logit model
	 */
	public void setProbability(double probability) {
		this.probability=probability;
		
	}
	
	/**
	 * Set the utility of the logit model.  This method should never be used.
	 */
	public void setUtility(double utility) {
		this.utility=utility;
	}
    /**
    Writes a header to the log file for subsequent debug statements
    in the calculateProbabilities() method.  Call this method prior to calling
    calculateProbabilities().
    */
    public void writeProbabilityHeader() {
        if (debug) {
            logger.info("\n");
            logger.info("Alt  Alternative Name         Probability      Cum Probability");
            logger.info("--------------------------------------------------------------");
        }
    }


	/**
	 * Get the number of this model.
	 * 
	 * @return the number of the model
	 */
	public int getNumber() {
		return alternativeNumber;
	}


	/**
	 * Set the number of this model
	 * 
	 * @number The number of the model.
	 */
	public void setNumber(int number) {
		alternativeNumber = number;
		
	}
    

}
