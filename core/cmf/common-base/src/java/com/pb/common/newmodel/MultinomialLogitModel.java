package com.pb.common.newmodel;

import com.pb.common.math.MathUtil;
import com.pb.common.newmodel.Alternative;
import com.pb.common.newmodel.LogitModel;

public class MultinomialLogitModel
{

    private static final int MAX_EXP_ARGUMENT = 400;

    private double[]         utilities;
    private double[]         expUtilities;
    private double[]         probabilities;
    private double[]  		 cumProbabilities;
    private double[]         util;
    double sumExpUtility;
    private String[]         altName;

    /**
     * Create a new multinomial logit model with numberOfAlternatives alternatives.
     *  
     * @param numberOfAlternatives  Number of alternatives.
     */
    public MultinomialLogitModel(int numberOfAlternatives)
    {

        utilities = new double[numberOfAlternatives];
        expUtilities = new double[numberOfAlternatives];
        probabilities = new double[numberOfAlternatives];
        cumProbabilities = new double[numberOfAlternatives];
        util = new double[numberOfAlternatives];
        altName = new String[numberOfAlternatives];
        for(int i=0;i<altName.length;++i){
        	altName[i]=new Integer(i+1).toString();
        }
        	
    }

    /**
     * Calculate and return the model logsum.
     * 
     * @return The composite utility (logsum value) of all the alternatives.
     */
    public double getUtility()
    {

        sumExpUtility = 0;
        double base = 0;

        // exponentiate the utilities array and save result in expUtilities.
        MathUtil.expArray( utilities, expUtilities );

        // sum the exponentiated utilities
        for (int i = 0; i < expUtilities.length; i++){
        	sumExpUtility += expUtilities[i];
        
        }
        if (sumExpUtility>0)
        {
            base = MathUtil.log(sumExpUtility);

            return base;
        }

        // if nothing available, return a bad utility
        return -999;
    }
    
    
    /**
     * Calculate probabilities
     * 
     * @return the probabilities array
     */
    public double[] calculateProbabilities(){
    	
    	double sumProbabilities = 0;
    	
    	for(int i=0;i<expUtilities.length;++i){
    		
    		if(utilities[i]>-MAX_EXP_ARGUMENT){
    			probabilities[i] = expUtilities[i]/sumExpUtility;
    			sumProbabilities += probabilities[i];
    			cumProbabilities[i] = sumProbabilities;
    		}else{
    			probabilities[i]=0;
    		}
    	}
    
    	return probabilities;
    }
    
    /**
     * Choose an alternative and return its number.  Note: Numbers are 0-based!
     * 
     * @param rnum  A random number between 0 and 1.0
     * @return  The number of the chosen alternative (zero-based).
     */
    public int chooseAlternative(double rnum){
    	
    	int chosenAlt = -1;
    	for(int i=0;i<cumProbabilities.length;++i){
    		if(rnum<=cumProbabilities[i]){
    			chosenAlt=i;
    			break;
    		}
    	}
    	return chosenAlt;
    }
    
    /**
	 * @return the utilities
	 */
	public double[] getUtilities() {
		return utilities;
	}

	/**
	 * @param utilities the utilities to set
	 */
	public void setUtilities(double[] utilities) {
		this.utilities = utilities;
	}

	/**
	 * @return the expUtilities
	 */
	public double[] getExpUtilities() {
		return expUtilities;
	}

	/**
	 * @param expUtilities the expUtilities to set
	 */
	public void setExpUtilities(double[] expUtilities) {
		this.expUtilities = expUtilities;
	}

	/**
	 * @return the altName
	 */
	public String[] getAltName() {
		return altName;
	}

	/**
	 * @param altName the altName to set
	 */
	public void setAltName(String[] altName) {
		this.altName = altName;
	}

}
