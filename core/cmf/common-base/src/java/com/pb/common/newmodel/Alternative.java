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
 *   Alternative interface
 *   Implement to allow an object to be an alternative in a model 
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
*/

package com.pb.common.newmodel;


public interface Alternative {

	/** 
    Get the utility of this alternative
    @return utility
    */
    double getUtility();
    /** 
    Set the utility of this alternative
    @param utility The utility of the alternative
    */
    void setUtility(double utility);
    
	/** 
    Get the exponentiated utility of this alternative
    @return exponentiated utility
    */
    double getExpUtility();
    /** 
    Set the exponentiated utility of this alternative
    @param expUtility The exponentiated utility of the alternative
    */
    void setExpUtility(double expUtility);

    /**
     * Set the debug for this alternative.
     * @param debug  True if debug, else false
     */
    void setDebug(boolean debug);

    /**
     * Set the probability of this alternative
     * @param probability
     */
    void setProbability(double probability);
    
    /**
     * Get the probability of the alternative
     * @return probability
     */
    double getProbability();
    
    
    
    /** 
    Get the name of this alternative
    @return name
    */
    String getName();
    /** 
    Set the name of this alternative
    @param name Name of alternative.
    */
    void setName(String name);
    /** 
    Get the availability of this alternative
    @return true if alternative is available.
    */
    
    /**
     * Get the number of this alternative
     * @return number
     */
    int getNumber();
    
    /**
     * Set the number of this alternative
     * @param number
     */
    void setNumber(int number);
    
    boolean isAvailable();
    
    /** 
    Set the availability of this alternative
    @param available True if alternative is available.
    */
    void setAvailability(boolean available);
    
    /**
     * Check whether this alternative is available
     * @return   True if available, else false
     */
    boolean getAvailability();
    
    /**
     * Get an alternative (returns this if elemental alternative)
     * @param rnum
     */
    Alternative chooseAlternative(double rnum, double startProbability);
}
