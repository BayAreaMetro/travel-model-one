/*
 * Created on 21-Oct-2005
 *
 * Copyright  2005 JE Abraham, PB Consult, and others
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

/** @author John Abraham
 * 
 */

package com.pb.common.model;

import java.util.ArrayList;

/**
 * @author jabraham
 * This class just uses the expConstant of its alternatives to calculate the relative weights
 * and hence the choice probabilities.
 *
 */
public class ObservedChoiceProbabilities extends DiscreteChoiceModel {
    
    String name;
    
    public ObservedChoiceProbabilities(String name) {
        this.name = name;
        alternatives = new ArrayList();
    }

    @Override
    public String toString() {
        return "ObservedChoiceProbabilities("+name+")";
    }

    @Override
    public double[] getProbabilities() {
        return probabilities;
    }

    public void setProbabilities(double[] probabilities) {
        this.probabilities = probabilities;
        
    }
    
    @Override
    public void calculateProbabilities() {
        probabilities = new double[alternatives.size()];
        double sum = 0;
        for (int i =0;i<probabilities.length;i++) {
            probabilities[i] = ((Alternative) alternatives.get(i)).getExpConstant();
            sum+= probabilities[i];
        }
        for (int i =0;i<probabilities.length;i++) {
            probabilities[i] /= sum;
        }

    }

    public void addAlternative(Alternative a) {
        probabilities = null;
        alternatives.add(a);
    }

    public double getUtility() {
        throw new RuntimeException("Observed distribution models cannot calculate expected maximum utilities");
    }

    public void setConstant(double constant) {
        // nothing to do here.
    }

    public double getConstant() {
        return 0;
    }

    public void setExpConstant(double expConstant) {
        // nothing to do here.

    }

    public double getExpConstant() {
        return 1;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;

    }

    public boolean isAvailable() {
        // TODO Auto-generated method stub
        return false;
    }

    public void setAvailability(boolean available) {
        // TODO Auto-generated method stub

    }

}
