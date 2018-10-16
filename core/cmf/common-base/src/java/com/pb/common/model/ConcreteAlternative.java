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

package com.pb.common.model;
import java.util.ArrayList;
import java.io.Serializable;

public class ConcreteAlternative implements Alternative, Serializable{

    double utility;
    String name;
    boolean isAvailable;
    Object alternative;
    ArrayList alternativeObservers;
    double constant;
    double expConstant;
    
    /**
    Constructor takes reference to actual alternative.
    @param n Name of alternative.
    @param alt Alternative to hold reference to.
    */
    public ConcreteAlternative(String n, Object alt){
        
        name=n;
        alternative=alt;
        isAvailable=true;
    }
    
    /**
    Get the utility of the alternative.
    @return Utility value.
    */
    public double getUtility(){
        return utility;
    }
    
    public void setConstant(double constant){
        this.constant = constant;
    }
    
    public double getConstant(){
        return constant;
    }
    public void setExpConstant(double expConstant){
        this.expConstant =expConstant;
    }
    public double getExpConstant(){
         return expConstant;
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
    @param alt Actual alternative.
    */
    public void setAlternative(String n, Object alt){
        name=n;
        alternative=alt;
    }
    /**
    Get the actual alternative.
    @return Actual alternative.
    */
    public Object getAlternative(){
        return alternative;
    }

    /**
     * Sets the alternative.
     * @param alternative The alternative to set
     */
    public void setAlternativeObject(Object alternative) {
        this.alternative = alternative;
    }
    /**
     * Gets the alternative.
     * 
     */
    public Object getAlternativeObject() {
        return alternative;
    }

}
