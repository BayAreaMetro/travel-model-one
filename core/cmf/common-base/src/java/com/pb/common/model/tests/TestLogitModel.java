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

import com.pb.common.model.ConcreteAlternative;
import com.pb.common.model.DiscreteChoiceModelHelper;
import com.pb.common.model.LogitModel;

import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

/**
 * Tests class and methods in the model package.
 *
 * @author    Joel Freedman
 * @version   1.0, 2/04/2003
 */

public class TestLogitModel {
    public static Logger logger = Logger.getLogger("com.pb.common.model");

    public static void main(String[] args) {
        TestLogitModel.testLogitModel();
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

/*        try{
            LogFile lf= new LogFile("test.out");
        }catch(Exception e){
            System.out.println("Couldn't open test.out");
        }
  */     
        //Choice
        LogitModel root         = new LogitModel("Root");
        root.setDebug(true);

        //Level 1
        LogitModel transitNest  = new LogitModel("transitNest");
        LogitModel autoNest     = new LogitModel("autoNest");
        root.addAlternative(autoNest);
        root.addAlternative(transitNest);
        
        //Level 2
        LogitModel driveAloneNest       = new LogitModel("driveAloneNest");
        LogitModel sharedRideNest       = new LogitModel("sharedRideNest");
        LogitModel walkTransitNest      = new LogitModel("walkTransitNest");
        LogitModel driveTransitNest     = new LogitModel("driveTransitNest");
        autoNest.addAlternative(driveAloneNest);
        autoNest.addAlternative(sharedRideNest);
        
        transitNest.addAlternative(walkTransitNest);
        transitNest.addAlternative(driveTransitNest);
        autoNest.setDispersionParameter(1.4);
        transitNest.setDispersionParameter(1.4);
        
        //Level 3
        ConcreteAlternative driveAlone  = new ConcreteAlternative("driveAlone",new Integer(1));
        ConcreteAlternative shared2     = new ConcreteAlternative("shared2",new Integer(2));
        ConcreteAlternative shared3p    = new ConcreteAlternative("shared3p",new Integer(3));
        ConcreteAlternative walkBus     = new ConcreteAlternative("walkBus",new Integer(4));
        ConcreteAlternative walkRail    = new ConcreteAlternative("walkRail",new Integer(5));
        ConcreteAlternative driveBus    = new ConcreteAlternative("driveBus",new Integer(6));
        ConcreteAlternative driveRail   = new ConcreteAlternative("driveRail",new Integer(7));
        driveAloneNest.addAlternative(driveAlone);
        sharedRideNest.addAlternative(shared2);
        sharedRideNest.addAlternative(shared3p);
        walkTransitNest.addAlternative(walkBus);
        walkTransitNest.addAlternative(walkRail);
        driveTransitNest.addAlternative(driveBus);
        driveTransitNest.addAlternative(driveRail);
        driveAloneNest.setDispersionParameter(3.5);
        sharedRideNest.setDispersionParameter(3.5);
        walkTransitNest.setDispersionParameter(3.5);
        driveTransitNest.setDispersionParameter(3.5);
             
        //set the base alternative utilities
        driveAlone.setUtility(-1.775);
        shared2.setUtility(  -3.7750);
        shared3p.setUtility( -4.7750);
        walkBus.setUtility(  -7.1275);
        walkRail.setUtility( -5.8150);
        driveBus.setUtility( -6.6544);
        driveRail.setUtility(-5.4325);

//      Playing with availability settings
 /*       
         walkBus.setAvailability(false);
        walkRail.setAvailability(false);
         driveBus.setAvailability(false);
       driveRail.setAvailability(false);
   */     
       // driveRail.setUtility(-500);
        
        root.computeAvailabilities();
        root.writeAvailabilities();

        //calculate the logsum at the root level
        root.writeUtilityHeader();
        //root.expUtilities = new double[root.];
        double logsum = root.getUtility();
        
        //calculate probabilities
        root.writeProbabilityHeader();
        root.calculateProbabilities();
        
        //get the chosen alternative via monte carlo simulation
        //and multiple random number draws
        ConcreteAlternative chosenAlternative = (ConcreteAlternative) root.chooseElementalAlternative();
        
        logger.info("Root level logsum = "+logsum);
        logger.info("Chosen alternative = "+chosenAlternative.getName());
        

        //test that it works for a range of random numbers
        double rnum=0;
        for(int i=0;i<100;++i){
        	rnum+=0.009999;
        	chosenAlternative = (ConcreteAlternative) root.chooseElementalAlternative(rnum);
        	logger.info("Chose alternative "+chosenAlternative.getName()+" with random number "+rnum);
        }

        //test that it works for the method that accepts no arguments
        logger.info("\n\nMethods that accept no arguments"); 
        for(int i=0;i<100;++i){
        	chosenAlternative = (ConcreteAlternative) root.chooseElementalAlternative();
        	logger.info("Chose alternative "+chosenAlternative.getName());
        }
        
        //test that it works with the method that accepts a Random
        logger.info("\n\nAccepting a Random"); 
        Random random = new Random(); 
        for(int i=0;i<100;++i){
        	chosenAlternative = (ConcreteAlternative) root.chooseElementalAlternative(random);
        	logger.info("Chose alternative "+chosenAlternative.getName()+" with random number "+random);
        }
        
        root.clear();
     
        
        //get a Hashmap of elemental alternatives
        HashMap alternativeMap = new HashMap();
        root.getElementalAlternativeHashMap(alternativeMap);
        
        logger.info("There are "+alternativeMap.size()+" elemental alternatives under root");
        
        //get a HashMap of elemental alternatives where the object is a
        //Double() probability for each alternative
        HashMap probabilityMap = new HashMap();
        root.getElementalProbabilitiesHashMap(probabilityMap);
 
        
        //Create a helper, give the probability HashMap to the helper
        //and use to choose an alternative.
        DiscreteChoiceModelHelper dcmh = new DiscreteChoiceModelHelper();
        dcmh.setDebug(true);
        logger.info("Selected alternative: "+ dcmh.chooseAlternativeFromHashMap(probabilityMap));
    
        root.clear();
        
        //enter an auto ownership loop.  Set the 
        //constants for each loop and re-compute utility, and probability.
        // note  these constants will only 
        //be added to drive mode for simplicity but would typically
        //vary by mode.
        double[] autoConstants = {0,0.5, 1.5};
        for(int i=0;i<3;++i){
 
          
            if(i==0)
                driveAlone.setAvailability(false);
            else
                driveAlone.setAvailability(true);                

            logger.info("\n\nMarket "+i+" Constant "+autoConstants[i]);
            driveAlone.setConstant(autoConstants[i]);
            
             
            //calculate the logsum at the root level
            root.writeUtilityHeader();
            logsum = root.getUtility();
        
            //calculate probabilities
            root.writeProbabilityHeader();
            root.calculateProbabilities();
            
 //           root.allocateQuantity(1000);
            
            root.clear();
        }
    
    }

}
