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

import com.pb.common.math.MathUtil;
import com.pb.common.util.SeededRandom;
import org.apache.log4j.Logger;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Set;

public class DiscreteChoiceModelHelper {

    protected boolean debug;
    protected double damp = 0.5;
    protected double minimumConstant=-150;
    protected double minimumDifference=100;
    
    public final static byte MAGIC_FORMULA=1;
    public final static byte RATIO=2;
    
    //the calculate method is the magic formula by default;
    //but it doesn't work when observed share is 1.0
    protected byte calculateMethod=1;

    protected static Logger logger = Logger.getLogger("com.pb.common.model");

    public DiscreteChoiceModelHelper() {

    }

    /**
     * Choose an alternative according to the probabilities in a HashMap of probabilities.
     * 
     * @param map  The hashmap to get the probabilities from
     * @return The name of the selected elemental alternative.
     */
    public String chooseAlternativeFromHashMap(HashMap map) {

        Set keys = map.keySet();
        Iterator it = keys.iterator();
        double selector = SeededRandom.getRandom();
        double sum = 0;
        String selected = new String("no Alternative selected");

        if (debug) {
            logger.info("\n\nAlternative Name                Probability");
            logger.info("-------------------------------------------");
        }

        while (it.hasNext()) {
            String altName = (String) it.next();
            double probability = ((Double) map.get(altName)).doubleValue();

            if (debug)
                logger.info(String.format("%-20s", altName) + "\t\t\t" + probability);

            sum += probability;

            if (selector < sum && probability > 0) {
                selected = altName;
                break;
            }
        }
        return selected;
    }

    /**
     * @return boolean
     */
    public boolean isDebug() {
        return debug;
    }

    /**
     * Sets the debug.
     * @param debug The debug to set
     */
    //	publictem.d setDebug(boolean debug) {
    public void setDebug(boolean debug) {
        this.debug = debug;
    }

    /**
     * Pass method estimated share, observed share, and an existing consant.  Calculates new
     * alternative-specific constant according to the formula:
     * 
     *  new constant =  old constant + nl(((observed*estimated)-observed)/((observed*estimated)-estimated))
     *
     * @param estimated The estimated share
     * @param observed  The observed share
     * @param existingConstant The existing alternative-specific constant
     * @return The new alternative-specfic constant
     * **/
    public double calculateConstant(
        double estimated,
        double observed,
        double existingConstant,
        String label) {

        //alternative not available if no observed share
        if (observed == (double) 0.0)
            return -999;

        if(existingConstant< this.minimumConstant)
            return existingConstant;

        double value=0;
        if(calculateMethod==MAGIC_FORMULA)
            value = existingConstant
                + damp * calculateMagic(estimated,observed);
        else
            value = existingConstant + damp * calculateRatio(estimated, observed);

        logger.info(
            String.format("%-20s", label)
                + String.format("%5.2f", estimated)
                + String.format("  %5.2f", observed)
                + String.format("  %9.4f", existingConstant)
                + String.format("  %9.4f", value));

        return value;

    }
    /**
     * Pass method estimated share, observed share, damping factor and an existing consant.  Calculates new
     * alternative-specific constant according to the formula:
     * 
     *  new constant =  old constant + damp*nl(((observed*estimated)-observed)/((observed*estimated)-estimated))
     *
     * @param estimated The estimated share
     * @param observed  The observed share
     * @param existingConstant The existing alternative-specific constant
     * @param damp A damping factor
     * @param label A label for logging
     * @return The new alternative-specfic constant
     * **/
    public double calculateConstant(
        double estimated,
        double observed,
        double existingConstant,
        String label,
        double damp) {

        //alternative not available if no observed share
        if (observed == (double) 0.0)
            return -999;

        if(existingConstant< this.minimumConstant)
            return existingConstant;

        double value=0;
        if(calculateMethod==MAGIC_FORMULA)
            value = existingConstant
                + damp * calculateMagic(estimated,observed);
        else
            value = existingConstant + damp * calculateRatio(estimated, observed);

        logger.info(
            String.format("%-20s", label)
                + String.format("%5.2f", estimated)
                + String.format("  %5.2f", observed)
                + String.format("  %9.4f", existingConstant)
                + String.format("  %9.4f", value));

        return value;
    }

    /**
     * Pass method estimated choices, observed choices, total choices and an existing consant.  Calculates new
     * alternative-specific constant according to the formula:
     * 
     *  new constant =  old constant + damp*nl(((observed*estimated)-observed)/((observed*estimated)-estimated))
     *
     * Use this method if you do not want an asc computed if the difference
     * between observed choices and estimated choices is less than minimumDifference (set
     * minimumDifference using setter first, its default is 100).
     * @param estimatedChoices The estimated number of choices
     * @param observedChoices  The observed number of choices
     * @param alternatives The total alternatives in the model
     * @param existingConstant The existing alternative-specific constant
     * @param label A label for logging
     * @return The new alternative-specfic constant
     * **/
    public double calculateConstant(
        double estimatedChoices,
        double observedChoices,
        double alternatives,
        double existingConstant,
        String label) {
            
        if(alternatives==0)
            return existingConstant;
            
        if(Math.abs(observedChoices-estimatedChoices)<this.minimumDifference)
            return existingConstant; 

        double observed = observedChoices/alternatives;
        double estimated = estimatedChoices/alternatives;
       

        //alternative not available if no observed share
        if (observed == (double) 0.0)
            return -999;

        if(existingConstant< this.minimumConstant)
            return existingConstant;

        double value=0;
        if(calculateMethod==MAGIC_FORMULA)
            value = existingConstant
                + damp * calculateMagic(estimated,observed);
        else
            value = existingConstant + damp * calculateRatio(estimated, observed);

        logger.info(
            String.format("%-20s", label)
                + String.format("%5.2f", estimated)
                + String.format("  %5.2f", observed)
                + String.format("  %9.4f", existingConstant)
                + String.format("  %9.4f", value));

        return value;
    }
    public void logConstantHeader() {
        logger.info("Constant        Estimated  Observed  Existing  New");
        logger.info("------------------------------------------");
    }
    
    private double calculateMagic(double estimated, double observed){
        double product = observed * estimated;
        double value=0;
        if((product-estimated)!=0)
            value =MathUtil.log((product - observed) / (product - estimated));
        return value;
    }
    private double calculateRatio(double estimated, double observed){
        double value=0;
        if(estimated!=0)
            value =MathUtil.log(observed / estimated);
        return value;
    }

    /**
     * Returns the damp.
     * @return double
     */
    public double getDamp() {
        return damp;
    }

    /**
     * Returns the minimumChoices.
     * @return double
     */
    public double getMinimumDifference() {
        return minimumDifference;
    }

    /**
     * Sets the damp.
     * @param damp The damp to set
     */
    public void setDamp(double damp) {
        this.damp = damp;
    }

    /**
     * Sets the minimumChoices.
     * @param minimumDifference The minimumChoices to set
     */
    public void setMinimumDifference(double minimumDifference) {
        this.minimumDifference = minimumDifference;
    }

    /**
     * Returns the minimumConstant.
     * @return double
     */
    public double getMinimumConstant() {
        return minimumConstant;
    }

    /**
     * Sets the minimumConstant.
     * @param minimumConstant The minimumConstant to set
     */
    public void setMinimumConstant(double minimumConstant) {
        this.minimumConstant = minimumConstant;
    }

    public byte getCalculateMethod() {
        return calculateMethod;
    }

    public void setCalculateMethod(byte calculateMethod) {
        this.calculateMethod = calculateMethod;
    }

}
