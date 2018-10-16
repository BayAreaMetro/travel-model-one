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
package com.pb.common.model;

import com.pb.common.math.MathUtil;
import org.apache.log4j.Logger;

import java.io.Serializable;
import java.text.NumberFormat;
import java.util.ArrayList;

/**
 *  The LogitModel is a type of DiscreteChoiceModel
 *  with a Gumbel-distributed error term.  The LogitModel can be a multinomial
 *  model or a nest of a nested-logit model.  The method calls to getUtility() and
 *  calculateProbabilities() apply to all nests and alternatives underneath it.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
 */
public class LogitModel extends DiscreteChoiceModel implements Serializable {

    protected double dispersionParameter;
	protected double[] expUtilities;
    protected static NumberFormat nf = NumberFormat.getInstance();
    protected double constant;
    protected double expConstant;
    protected static Logger logger = Logger.getLogger(LogitModel.class);
    
    protected String name;

    //LogitModels are not available unless the getUtility
    //method has been called and at least one alternative
    //under the model is available
    protected boolean isAvailable = false;
    /**
    Default constructor.
    @param n      The name of this model.
    */
    public LogitModel(String n) {
        alternatives = new ArrayList();
        isElementalAlternative = new ArrayList();
        dispersionParameter = 1.0;
        setName(n);
    }

    /**
    Use this constructor if you know how many alternatives.
    @param n      The name of this model.
    @param numberOfAlternatives   The number of alternatives.
    */
    public LogitModel(String n, int numberOfAlternatives) {
        alternatives = new ArrayList(numberOfAlternatives);
        isElementalAlternative = new ArrayList(numberOfAlternatives);
        dispersionParameter = 1.0;
        setName(n);
        
            this.expUtilities = new double[numberOfAlternatives];
        
            this.probabilities = new double[numberOfAlternatives];
        
    }

    public void setConstant(double constant) {
        this.constant = constant;
    }

    public double getConstant() {
        return constant;
    }

    public void setExpConstant(double expConstant) {
        this.expConstant = expConstant;
    }
    public double getExpConstant() {
        return expConstant;
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
            for (int alt = 0; alt < alternatives.size(); ++alt) {
                Alternative thisAlt = (Alternative) alternatives.get(alt);
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
            if (a instanceof DiscreteChoiceModel)
                 ((DiscreteChoiceModel) a).setDebug(true);
        }
        alternatives.add(a);
        if (a instanceof DiscreteChoiceModel)
            isElementalAlternative.add(new Boolean(false));
        else
            isElementalAlternative.add(new Boolean(true));

        if(expUtilities == null)
            expUtilities = new double[alternatives.size()]; 
        
        if(probabilities == null)
            probabilities = new double[alternatives.size()]; 
           
        if(alternatives.size()>expUtilities.length)
            expUtilities = new double[alternatives.size()];

        if(alternatives.size()>probabilities.length)
            probabilities = new double[alternatives.size()];
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
    public double getUtility() throws ModelException {

        double sum = 0;
        double base = 0;

        int i = 0;
        nf.setMaximumFractionDigits(8);
        nf.setMinimumFractionDigits(8);
        for (int alt = 0; alt < alternatives.size(); ++alt) {
            Alternative thisAlt = (Alternative) alternatives.get(alt);
            if (thisAlt.isAvailable()) {
                double utility = thisAlt.getUtility();
                double constant = thisAlt.getConstant();

                //if alternative has a very large negative utility, it isn't available
                if (utility + constant < -400) {
	                expUtilities[i] = 0.0;
	     			++i;           
                    continue;
                }
                setAvailability(true);

                expUtilities[i] = MathUtil.exp(dispersionParameter * (utility + constant));
                sum += expUtilities[i];
                Boolean elemental = (Boolean) isElementalAlternative.get(i);
                if (elemental.equals(Boolean.TRUE) && debug)
                    logger.info(
                        String.format("%-20s", thisAlt.getName())
                            + "\t\t"
                            + nf.format(utility)
                            + "\t\t\t"
                            + nf.format(constant)
                            + "\t\t\t"
                            + nf.format(expUtilities[i]));
            } else
                expUtilities[i] = 0.0;
            ++i;
        }
        if (isAvailable()) {
            base = (1 / dispersionParameter) * MathUtil.log(sum);

            if (Double.isNaN(base))
                throw new ModelException(ModelException.INVALID_UTILITY);

            if (debug)
                logger.info(String.format("%-20s", getName() + " logsum:" ) + "\t\t" + nf.format(base));
            //
            return base;
        }
        // if nothing avaiable, return a bad utilty
        return -999;
    }

    /**
     * Use this method when the alternatives have exponentiated
     * constants associated with them; Use the getUtility method first,
     * then getFullUtility to multiply the base alternatives by the
     * exponentiated constants (set by the setExpConstant() method),
     * and bring them up to the root level.
     * Note that nests can also have exponentiated constants.
     */
    public double getFullUtility() {

        double sum = 0;
        double base = 0;
        int i = 0;
        nf.setMaximumFractionDigits(8);
        nf.setMinimumFractionDigits(8);
        for (int alt = 0; alt < alternatives.size(); ++alt) {
            Alternative thisAlt = (Alternative) alternatives.get(alt);
            if (thisAlt.isAvailable()) {

                Boolean elemental = (Boolean) isElementalAlternative.get(alt);

                //if it is an elemental alternative, use the exponentiated
                //utility instead of calculating it again, and multiply it
                //by the exponentiated constant
                if (elemental.equals(Boolean.TRUE)) {
                    expUtilities[alt] = expUtilities[alt] * thisAlt.getExpConstant();

                } else {
                    double utility = thisAlt.getUtility();
                    double constant = thisAlt.getConstant();
                    expUtilities[i] =
                        MathUtil.exp(dispersionParameter * (utility + constant))
                            * thisAlt.getExpConstant();
                }
                sum += expUtilities[i];
            } else
                expUtilities[i] = 0.0;
            ++i;
        }
        if (isAvailable()) {
            base = (1 / dispersionParameter) * MathUtil.log(sum);

            if (Double.isNaN(base))
                throw new ModelException(ModelException.INVALID_UTILITY);

            if (debug)
                logger.info(String.format("%-20s", getName()) + "\t\t" + nf.format(base));
            //
            return base;
        }
        return 0.0;

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
                "Alternative Name           Utility              Constant              ExpUtility   ");
            logger.info(
                "-----------------------------------------------------------------------------------------");
        }
    }

    /**
    Calculate the probabilities based on the choice utilities.
    */
    public void calculateProbabilities() {

        if (!isAvailable())
            return;
        nf.setMaximumFractionDigits(8);
        nf.setMinimumFractionDigits(8);
 
        double sum = 0;
        for (int i = 0; i < alternatives.size(); ++i) {
            if (Double.isNaN(expUtilities[i])) {
                throw new ModelException(ModelException.INVALID_EXPUTILITY);
            }
            sum += expUtilities[i];
        }
        double cumProb = 0.0;
         for (int i = 0; i < alternatives.size(); i++) {
                
                if(expUtilities[i]>0 && sum > 0)
                    probabilities[i] = expUtilities[i] / sum;
                else
                    probabilities[i] = 0;

                cumProb += probabilities[i];

                Alternative a = getAlternative(i);
                if (debug && a.isAvailable()) {
                    logger.info(
                        String.format( "%-4d %-20s %15.8f %20.8f", (i+1), a.getName(), probabilities[i], cumProb ) );
                }
                Boolean elemental = (Boolean) isElementalAlternative.get(i);
                if (elemental.equals(Boolean.FALSE))
                     ((DiscreteChoiceModel) a).calculateProbabilities();

        }
    
        if (debug ) logger.info("\n");

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
    Get the choice probabilities.
    @return an array containing the choice probabilities.  Probabilities
    will be 0 for non-available alternatives.
    */
    public double[] getProbabilities() {
        return probabilities;
    }

    /**
    Set availabilities of all nests based on availability of sub-alternatives
    */
    public void computeAvailabilities() {
        int availableAlternatives=0;
        for (int i = 0; i < alternatives.size(); ++i) {
            Alternative a = (Alternative) alternatives.get(i);
            
            //if this alternative is a logit model, check its availability
            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            
            if (elemental.equals(Boolean.FALSE))
                 ((LogitModel) a).computeAvailabilities();
            
            //elemental alternatives aren't available if their utility is very small
            // (don't check the utility if the element is not availible)
            if(elemental.equals(Boolean.TRUE))
                if (!a.isAvailable() || a.getUtility()<-999)
                    continue;
            
            //if the logit model or elemental alternative under this alternative is available,
            //then this alternative is available.
            if (a.isAvailable()) {
                if(debug)
                    logger.info("Alternative "+a.getName()+" is available, setting "+getName()+" available");
                setAvailability(true);
                ++availableAlternatives;
            }
        }
        
        //if no lower alternatives are available, then this alternative isn't available.
        if(availableAlternatives==0)
            setAvailability(false);
    }
    
    /*
     * Get the array of exponentiated utilities for this model.
     */
    public double[] getExponentiatedUtilities(){
        return expUtilities;

    }

    /**
     * @param logger the logger to set
     */
    public static void setLogger(Logger logger) {
        LogitModel.logger = logger;
    }

}
