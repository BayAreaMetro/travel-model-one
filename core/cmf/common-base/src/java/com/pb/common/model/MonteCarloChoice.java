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
 *  Uses monte carlo selection simulation to select a choice among alternatives
 *  in a DiscreteChoiceModel.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/02/2003
 */

package com.pb.common.model;

import com.pb.common.util.SeededRandom;

public class MonteCarloChoice implements ChoiceStrategy {

    DiscreteChoiceModel dcm;
    
    public void setModelReference(DiscreteChoiceModel model){
        dcm=model;
    }
    
    public void calculateChoice(){
    }    

    public Alternative chooseElementalAlternative() throws ModelException {
        Alternative a = chooseAlternative();
        while (a instanceof DiscreteChoiceModel) {
            a = chooseAlternative();
        }
        return a;
    }

    public Alternative chooseAlternative() throws ModelException{
        double selector = SeededRandom.getRandom();
        double sum = 0;
        double[] probabilities = dcm.getProbabilities();
        for (int i = 0; i < probabilities.length; i++) {
            sum += probabilities[i];
            if (selector <= sum) 
                return dcm.getAlternative(i);
        }
        throw new ModelException(ModelException.INVALID_ALTERNATIVE);
    }
    
 
}