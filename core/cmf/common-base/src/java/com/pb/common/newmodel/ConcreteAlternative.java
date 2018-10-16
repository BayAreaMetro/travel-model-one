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
 *   Implements Alternative interface
 *   Use to hold alternative in a model; holds reference to actual alternative. 
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
*/

package com.pb.common.newmodel;
import java.io.Serializable;

public class ConcreteAlternative implements Alternative, Serializable{

    double utility;
    double expUtility;
    double probability;
    String name;
    boolean isAvailable;
    boolean isDebug;
    int alternativeNumber;
    
    /**
    Constructor takes reference to actual alternative.
    @param n Name of alternative.
    @param alt Alternative to hold reference to.
    */
    public ConcreteAlternative(String n, int number){
        
        name=n;
        alternativeNumber=number;
        isAvailable=true;
    }
    
    /**
    Get the utility of the alternative.
    @return Utility value.
    */
    public double getUtility(){
        return utility;
    }
    /**
    Set the utility of the alternative.
    @param util  Utility value.
    */
    public void setUtility(double util){
        utility=util;
    }    /**

    /** 
    Get the name of this alternative.
    @return The name of the alternative
    */
    public String getName(){
        return name;
    }
    /** 
    Set the name of this alternative.
    @param name The name of the alternative
    */
    public void setName(String name){
        this.name=name;
    }
    /** 
    Get the availability of this alternative.
    @return True if alternative is available
    */
    public boolean isAvailable(){
        return isAvailable;
    }
    /** 
    Set the availability of this alternative.
    @param available True if alternative is available
    */
    public void setAvailability(boolean available){
        isAvailable=available;
    }
    
    /**
    Set reference to actual alternative.
    @param n Name of alternative
    @param alt Number of alternative.
    */
    public void setAlternative(String n, int number){
        name=n;
        alternativeNumber=number;
    }
    /**
    Get the alternative.
    @return The alternative.
    */
    public Alternative chooseAlternative(){
        return this;
    }

    /**
    Get the alternative.
    @return Actual alternative.
    */
    public Alternative chooseAlternative(double rnum, double startProbability){
        return this;
    }

    /**
     * Sets the alternative.
     * @param alternative The alternative to set
     */
    public void setNumber(int number) {
        alternativeNumber = number;
    }
    /**
     * Gets the alternative number.
     * 
     */
    public int getNumber() {
        return alternativeNumber;
    }

	/**
	 * Get availability of alternative
	 */
	public boolean getAvailability() {
		return isAvailable;
	}

	
	/**
	 * Get exponentiated utility 
	 */
	public double getExpUtility() {
		return expUtility;
	}

	/**
	 * Get probability
	 */
	public double getProbability() {
		return probability;
	}

	/**
	 * Set debug
	 */
	public void setDebug(boolean debug) {
		isDebug = debug;
	}

	/**
	 * Set exponentiated utility
	 */
	public void setExpUtility(double expUtility) {
		this.expUtility=expUtility;
		
	}

	/**
	 * Set probability
	 */
	public void setProbability(double probability) {
		this.probability = probability;
		
	}

}
