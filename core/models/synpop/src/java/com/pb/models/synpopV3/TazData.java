/*
 * Copyright  2006 PB Consult Inc.
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
package com.pb.models.synpopV3;

/**
 * Interface for classes to store and manage TAZ data.  
 * The details are likely to differ from region to region, so they 
 * are interfaced here to be more generic.  
 * 
 * @author Erhardt
 * @version 1.0 Oct 13, 2006
 *
 */
public interface TazData {
    
    /**
     * Returns the number of households in a TAZ.
     * 
     * @param tazNumber The number of the TAZ of interest. 
     * @return The number of households in that TAZ.
     */
    public int getNumberOfHouseholds(int tazNumber);
}
