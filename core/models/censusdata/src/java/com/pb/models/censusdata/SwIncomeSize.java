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
package com.pb.models.censusdata;


public abstract class SwIncomeSize {
    
    protected double convertTo2000;
    
    
    public SwIncomeSize () {
    }
    
    public SwIncomeSize (double convertTo2000) {
        this.convertTo2000 = convertTo2000; 
    }
    

    // return the IncomeSize category index given the pums income and numPersons codes.
    // 
    // the definitions of the IncomeSize categories are project specific and must be
    // implemented in this method by any class that extends this abstract class.
    public abstract int getIncomeSize(int pumsIncomeCode, int hhSize);



    // return all the IncomeSize category labels.    
    public abstract String[] getIncomeSizeLabels();
    

    
	// return the number of HH income/HH size categories.    
	public abstract int getNumberIncomeSizes();



	// return the IncomeSize category index given the label.    
	public abstract int getIncomeSizeIndex(String incomeSizeLabel);



	// return the IncomeSize category label given the index.    
	public abstract String getIncomeSizeLabel(int incomeSizeIndex);

    
    
}

