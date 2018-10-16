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
/**
 *   A discrete choice model; has probabilities,
 *   but method of calculating them depends
 *   on specific model form.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
*/

package com.pb.common.model;

import com.pb.common.util.SeededRandom;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

public abstract class DiscreteChoiceModel implements CompositeAlternative {

    protected Logger logger=Logger.getLogger(DiscreteChoiceModel.class);
    protected ArrayList alternatives;
	protected double[] probabilities;
    protected ArrayList isElementalAlternative;
    protected boolean debug;
    protected ArrayList alternativeObservers;
    protected double probability = 1.0d;
    protected double startProbability =0.0d;
    
    public double getProbability() {
		return probability;
	}

	public void setProbability(double probability) {
		this.probability = probability;
	}

	public void setStartProbability(double probabilitySum) {
		this.startProbability = probabilitySum;
	}
	/**
     * Clear probabilities and set availabilities to true
     * for model and submodel nests.
     *   Exponentiated constants are not reset. 
     *   Alternative observers are not reset.  
     *   The structure is not reset.
     */
    public void clear(){
        
        for(int i=0;i<alternatives.size();++i){
            Alternative a = (Alternative)alternatives.get(i);
            a.setAvailability(true);
            
            if(probabilities!=null)
                probabilities[i]=0;
            
            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            if (elemental.equals(Boolean.FALSE))
                 ((DiscreteChoiceModel) a).clear();
        }
        
        
    }
    
    /**
     * This method doesn't do anything at DiscreteChoiceModel level.
     */
    public void setUtility(double utility){
        
    }
    /**
     * Get the arraylist of alternatives
     * @return alternatives
     */
    public ArrayList getAlternatives(){
        return alternatives;
    }

    /**
    Get the probabilities from this model.  Must call
    calculateProbabilities() prior to calling this method,
    or matrix will be null.
    @return An array containing the probabilities.
    */
    public abstract double[] getProbabilities();

    /**
    Calculate the probabilities in this model.
    */
    public abstract void calculateProbabilities();

    /**
    Get the alternative back from the possible alternatives, at the
    specified location in the list of alternatives.
    @param elementNumber   The number of the element in the list of alternatives.
    */
    public Alternative getAlternative(int elementNumber) {
        if (elementNumber > alternatives.size())
            throw new ModelException(ModelException.INVALID_ALTERNATIVE);

        return (Alternative) alternatives.get(elementNumber);
    }

    /** 
    Set debug on, all calculations reported to debugger.
    @param deb  true to turn on debugging.
    */
    public void setDebug(boolean deb) {
        debug = deb;
       for(int i=0;i<alternatives.size();++i){
            Alternative a = (Alternative)alternatives.get(i);
            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            if (elemental.equals(Boolean.FALSE))
                 ((DiscreteChoiceModel) a).setDebug(deb);
       }
    }

    /**
    Get debug status.
    @return debug  Debug status (true if on)
    */
    public boolean getDebug() {
        return debug;
    }

    /**
    Get an elemental alternative (one which is not a model nest).
    @return chosen alternative for this model.
    */
    public Alternative chooseElementalAlternative() throws ModelException {
    	double rnum = SeededRandom.getRandom();
        Alternative a = chooseAlternative(rnum);
        while (a instanceof DiscreteChoiceModel) {
            a = ((DiscreteChoiceModel) a).chooseAlternative(rnum);
        }
        return a;
    }

    /**
     * Get an elemental alternative (one which is not a model nest).
     * 
     * @return chosen alternative for this model.
     */
    public Alternative chooseElementalAlternative(Random random) throws ModelException {
    	double rnum = random.nextDouble(); 
        Alternative a = chooseAlternative(rnum);
        while (a instanceof DiscreteChoiceModel) {
            a = ((DiscreteChoiceModel) a).chooseAlternative(rnum);
        }
        return a;
    }
    
    /**
     * Get an elemental alternative (one which is not a model nest).
     * 
     * @return chosen alternative for this model.
     */
    public Alternative chooseElementalAlternative(double randomNumber) throws ModelException {
        Alternative a = chooseAlternative(randomNumber);
        while (a instanceof DiscreteChoiceModel) {
            a = ((DiscreteChoiceModel) a).chooseAlternative(randomNumber);
        }
        return a;
    }
    
    /**
     * Choose an alternative with a random number generator.
     */
    public Alternative chooseAlternative(Random random) {
    	double rnum = SeededRandom.getRandom();
        return chooseAlternative(rnum);
    }

    
    /**
     * Get an alternative (could be a subnest)
     * 
     * @return chosen alternative.
     */
    public Alternative chooseAlternative() {
        if ( probabilities.length > 1 ) {
        	double rnum = SeededRandom.getRandom();
            return chooseAlternative(rnum);            
        } else {
            return (ConcreteAlternative)alternatives.get(0);
        }
    }

    /**
     * Choose an alternative with a selector.
     */
    public Alternative chooseAlternative(double selector) throws ModelException {

        double sum = startProbability;
        Alternative a = null;
        for (int i = 0; i < probabilities.length; i++) {

            if ( probabilities[i] == 0 )
                continue;

            sum += probabilities[i]*probability;


            if ( selector <= sum && a==null) {
                a = getAlternative(i);
                if (a instanceof DiscreteChoiceModel){ 
                	((DiscreteChoiceModel) a).setProbability(probabilities[i]*probability);
                	((DiscreteChoiceModel) a).setStartProbability(sum-(probabilities[i]*probability));
                }
                return a;
            }
           

        }
       
        logger.error("Could not choose alternative for nest " + this.getName());
        logger.error("Discrete Choice model selector: " + selector);
        logger.error("Discrete Choice model cummulative probability: " + sum);
        logger.error("Discrete Choice model start probability:       " + startProbability);
        logger.error("Discrete Choice model nest probability:        " + probability);
        throw new ModelException(ModelException.INVALID_ALTERNATIVE);
    }
    
    

    /**
    Write availabilities of all nests in table to log file.
    */
    public void writeAvailabilities() {
    	if (debug)
        	writeAvailabilities(true);
    }

    protected void writeAvailabilities(boolean writeHeader) {

        if (writeHeader) {
        	logger.info("\n");
            logger.info("Availability Settings");
            logger.info("Alternative Name             Available?  ");
            logger.info("-----------------------------------------");
            logger.info(String.format("%-20s", getName()) + "\t\t\t\t" + isAvailable());
        }

        for (int i = 0; i < alternatives.size(); ++i) {
            Alternative a = (Alternative) alternatives.get(i);
            logger.info(String.format("%-20s", a.getName()) + "\t\t\t\t" + a.isAvailable());
            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            if (elemental.equals(Boolean.FALSE))
                 ((DiscreteChoiceModel) a).writeAvailabilities(false);
        }
    }

    
    /**
     * Get a HashMap of elemental Alternatives.
     * 
     * @param map  The hashmap to store the alternatives in, it sets <code>map</code>
     * to a HashMap of elemental alternatives under this model (and all
     * nests under this model) whose key values are the alternative names and
     * whose objects are the alternative objects.
     */
    public void getElementalAlternativeHashMap(HashMap map) {

        for (int i = 0; i < alternatives.size(); ++i) {
            Alternative a = (Alternative) alternatives.get(i);
            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            if (elemental.equals(Boolean.TRUE)) {
                map.put(a.getName(), a);
            } else {
                ((DiscreteChoiceModel) a).getElementalAlternativeHashMap(map);
            }
        }
    }

    /**
     * Get a HashMap of probabilities for elemental alternatives.
     * 
     * @param map  The hashmap to store the alternatives in
     */
    public void getElementalProbabilitiesHashMap(HashMap map) {

        getElementalProbabilitiesHashMap(map, 1.0);
    }

    /**
     * Get a HashMap of probabilities for elemental alternatives.
     * 
     * @param map  The hashmap to store the alternatives in
     * returns the probability of the nest over the alternative
     */
    public void getElementalProbabilitiesHashMap(HashMap map, double nestProbability) {

        for (int i = 0; i < alternatives.size(); ++i) {
            Alternative a = (Alternative) alternatives.get(i);

            Boolean elemental = (Boolean) isElementalAlternative.get(i);
            double probability = 0.0;
            if (a.isAvailable())
                probability = probabilities[i];
            if (elemental.equals(Boolean.TRUE)) {
                probability = probability * nestProbability;
                map.put(a.getName(), new Double(probability));
            } else {
                ((DiscreteChoiceModel) a).getElementalProbabilitiesHashMap(map, (probability * nestProbability));
            }
        }
    }
    
    /**
     * Get a HashMap of utilities for elemental alternatives.
     * 
     * @param map  The hashmap to store the alternatives in
     * with the utility keyed by alternative name
     */
    public void getElementalUtilitiesHashMap(HashMap map) {

        for (int i = 0; i < alternatives.size(); ++i) {

            Alternative a = (Alternative) alternatives.get(i);
            Boolean elemental = (Boolean) isElementalAlternative.get(i);

            if (elemental.equals(Boolean.TRUE))
                map.put( a.getName(), a.getUtility() );
            else
                ((DiscreteChoiceModel)a).getElementalUtilitiesHashMap(map);
        }
    }
    
    
   /** 
     * Return the alternative observers for this alternative.
     */
    public Collection getObservers(){
        
        return alternativeObservers;        
    }

    /**
     * Get a HashMap of alternative observers.  The map will contain the alternativeName and 
     * the alternative observer name, separated by a $ as the key, and the alternative
     * observer as the object.
     */ 
    public void getAlternativeObserverHashMap(HashMap map){
        
        
    }
}
