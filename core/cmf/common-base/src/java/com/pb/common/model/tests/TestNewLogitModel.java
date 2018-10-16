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
package com.pb.common.model.tests;

import java.text.NumberFormat;

import com.pb.common.newmodel.ConcreteAlternative;
import com.pb.common.newmodel.LogitModel;


import org.apache.log4j.Logger;

/**
 * Tests class and methods in the model package.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/04/2003
 */

public class TestNewLogitModel {
    public static Logger logger = Logger.getLogger("com.pb.common.model");
    protected static NumberFormat nf = NumberFormat.getInstance();


    public static void main(String[] args) {
        TestNewLogitModel.testLogitModel();
    }

     /**
     * Create a Logit Model,  set dispersion parameters of each nest, set some sample utilities, 
       calculate probabilities, select an alternative.
       
       The logit class uses the McFadden formulation, or what Koppelman refers to as the UMNL.  
       The utilities are scaled in the model strategy calculations, 
       as opposed to scaling the utilities manually for each alternative (which would require dummy nests 
       in the model if unequal nesting coefficients are used across the same level).  This is why
       Koppelman refers to the Daly formulation as the Non-Normalized Nested Logit (NNNL).  
       
       The ratio of the dispersion parameter of the nest to the dispersion parameter of the sub-alternative 
       is analogous to the nesting coefficient.  To convert the nesting parameters of a Daly model
       to the dispersion parameters required by the LogitModel strategy, assume the dispersion
       parameter for the root choice is 1.0.  The dispersion parameter for the next level (dp1) is equal
       to 1/nesting coefficient.  The dispersion parameter for the next level would be equal to 
       dp1/nesting coefficient, and so forth down levels from root to base.  
       
       Example:                        root
                      auto             transit            walk/bike       nest coeff. = 0.8  disp = 1.25 (1/0.8)
              da            sr      wlk      drv        wlk     bike      nest coeff. = 0.5  disp = 2.5  (1.25/.5)                 
              da         sr2  sr3  bus lrt   bus lrt    wlk     bike      nest coeff. = 0.3  disp = 8.33 (2.5/0.3) 
       
       
        

       Sample Structure:
                                 Root
                           /            \                     dp 1                            
             autoNest                   transitNest                   
             /      \                /               \        dp 1.4                  
   DriveAloneNext      SharedRide     walkTransit    driveTransit              
          |         /       \        /    \        /     \     dp 3.5      
        DA         2P       3+      bus  rail     bus    rail                  
                                     
     Note: in the example below, I use the ConcreteAlternative class.  This class implements
     the Alternative interface, and holds a reference to an object.  In this case, I have
     used Integers as the object, and simply numbered the base alternatives.  However, any
     object can be placed in the ConcreteAlternative class (ie TAZs, Households, etc). A different
     approach is to implement the Alternative interface in the class itself, and add it to the 
     LogitModel instead of the ConcreteAlternative.
     
     */
    public static void testLogitModel() {

        nf.setMaximumFractionDigits(8);
        nf.setMinimumFractionDigits(8);
        ConcreteAlternative[] alts = new ConcreteAlternative[7];
    	String[] altNames = {
    	   "driveAlone",
    	   "shared2",
    	   "shared3p",
    	   "walkBus",
    	   "walkRail",
    	   "driveBus",
    	   "driveRail"
    	};
    	for(int i=0;i<alts.length;++i)
    		alts[i] = new ConcreteAlternative(altNames[i],new Integer(i));
    		
        //Choice
        LogitModel root         = new LogitModel("Root",0,2);
        root.setDebug(true);

        //Level 1
        LogitModel transitNest  = new LogitModel("transitNest",1,2);
        LogitModel autoNest     = new LogitModel("autoNest",2,2);
        root.addAlternative(autoNest);
        root.addAlternative(transitNest);
        
        //Level 2
        LogitModel driveAloneNest       = new LogitModel("driveAloneNest",3,1);
        LogitModel sharedRideNest       = new LogitModel("sharedRideNest",4,2);
        LogitModel walkTransitNest      = new LogitModel("walkTransitNest",5,2);
        LogitModel driveTransitNest     = new LogitModel("driveTransitNest",6,2);
        autoNest.addAlternative(driveAloneNest);
        autoNest.addAlternative(sharedRideNest);
        
        transitNest.addAlternative(walkTransitNest);
        transitNest.addAlternative(driveTransitNest);
        autoNest.setDispersionParameter(1.4);
        transitNest.setDispersionParameter(1.4);
        
        //Level 3
        driveAloneNest.addAlternative(alts[0]);
        sharedRideNest.addAlternative(alts[1]);
        sharedRideNest.addAlternative(alts[2]);
        walkTransitNest.addAlternative(alts[3]);
        walkTransitNest.addAlternative(alts[4]);
        driveTransitNest.addAlternative(alts[5]);
        driveTransitNest.addAlternative(alts[6]);
        driveAloneNest.setDispersionParameter(3.5);
        sharedRideNest.setDispersionParameter(3.5);
        walkTransitNest.setDispersionParameter(3.5);
        driveTransitNest.setDispersionParameter(3.5);
             
        //set the base alternative utilities
        alts[0].setUtility(-1.775);
        alts[1].setUtility(  -3.7750);
        alts[2].setUtility( -4.7750);
        alts[3].setUtility(  -7.1275);
        alts[4].setUtility( -5.8150);
        alts[5].setUtility( -6.6544);
        alts[6].setUtility(-5.4325);

        
        root.setAvailability();
      
        double logsum = root.getUtility();
        
        logger.info("Logsum " +logsum);
        //calculate probabilities
        root.calculateProbabilities();
        
        logger.info("AltName             Utility   ExpUtility Probability");
        for(int i=0;i<alts.length;++i)
        	logger.info(String.format("%-20s", alts[i].getName())+"  "+nf.format(alts[i].getUtility())+ "  "+nf.format(alts[i].getExpUtility())
        			+" "+nf.format(alts[i].getProbability()));
        
        //get the chosen alternative via monte carlo simulation
        double rnum=0;
        for(int i=0;i<10;++i){
        	rnum+=0.09999;
        	ConcreteAlternative chosenAlternative = (ConcreteAlternative) root.chooseAlternative(rnum);
        	logger.info("Chose alternative "+chosenAlternative.getName()+" with random number "+rnum);
        }
        root.clear();
     
        
    }
}
