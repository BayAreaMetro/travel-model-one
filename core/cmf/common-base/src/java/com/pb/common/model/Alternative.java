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

package com.pb.common.model;


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
     * Set the constant for the alternative
     * @param constant
     */
    void setConstant(double constant);
    
    /**
     * Get the constant for the alternative
     * @return double
     */
    
    double getConstant();
    
    /**
     * Set an exponentiated constant for the alternative;
     * it is taken into account when the method getFullUtility()
     * is called, after getUtility() is called.  
     * @param expConstant The constant that has already been exponentiated.
     */
    void setExpConstant(double expConstant);
    
    double getExpConstant();
    
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
    boolean isAvailable();
    /** 
    Set the availability of this alternative
    @param available True if alternative is available.
    */
    void setAvailability(boolean available);
}
