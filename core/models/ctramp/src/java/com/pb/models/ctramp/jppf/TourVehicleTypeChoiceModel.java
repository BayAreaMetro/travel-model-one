package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Random;

import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.Util;

import org.apache.log4j.Logger;

public class TourVehicleTypeChoiceModel
        implements Serializable
{

    private transient Logger                   logger                 = Logger.getLogger(TourVehicleTypeChoiceModel.class);
    float probabilityBoostAutosLTDrivers = 0;
    float probabilityBoostAutosGEDrivers = 0;
    
    private transient Logger tourFreq = Logger.getLogger("tourFreq");

    public TourVehicleTypeChoiceModel(HashMap<String, String> rbMap)
    {

        logger.info("setting up tour vehicle type choice model.");
        probabilityBoostAutosLTDrivers = Util.getFloatValueFromPropertyMap(rbMap,"Mobility.AV.ProbabilityBoost.AutosLTDrivers");
        probabilityBoostAutosGEDrivers = Util.getFloatValueFromPropertyMap(rbMap,"Mobility.AV.ProbabilityBoost.AutosGEDrivers");

     
    }

    /**
     * Calculate the probability of the tour using the AV in the household. If AVs owned =0, returns 0, else
     * returns a probability equal to the share of AVs in the household, boosted by the parameters in the properties file.
     * The parameters are named Mobility.AV.ProbabilityBoost.AutosLTDrivers and Mobility.AV.ProbabilityBoost.AutosGEDrivers
     * and are read in the object constructor.
     * 
     * @param hhObj
     * @return The probability of using one of the household AVs for the tour.
     */
    public double calculateProbability(Household hhObj){
    	
    	float numberOfAVs = (float) hhObj.getAutonomousVehicles();
    	
    	if(numberOfAVs==0)
    		return 0;
    	
    	float numberOfCVs = (float) hhObj.getHumanVehicles();
    	float numberOfDrivers = (float) hhObj.getDrivers();
    	float totalVehicles = numberOfAVs + numberOfCVs;
    	float origProbability = numberOfAVs/totalVehicles;
    	float probability=0;
    	float probabilityBoost=(float)1.0;
    	if(totalVehicles<numberOfDrivers)
    		probabilityBoost =  probabilityBoostAutosLTDrivers;
    	else
    		probabilityBoost =  probabilityBoostAutosGEDrivers;

    	probability = origProbability * probabilityBoost;
    	
        // write info to log file
        if ( hhObj.getDebugChoiceModels() ) {

       	 	tourFreq.info("Number of AVs:     "+numberOfAVs);
       	 	tourFreq.info("Number of HVs:     "+numberOfCVs);
       	 	tourFreq.info("Number of Drivers: "+numberOfDrivers);
      	 	tourFreq.info("Total Vehicles:    "+totalVehicles);
      	 	tourFreq.info("Orig Probability:  "+origProbability);
      	 	tourFreq.info("Probabilty Boost:  "+probabilityBoost);
      	 	tourFreq.info("Final Probability: "+probability);

        }
    	
    	return probability;
    }
    
    /**
     * Iterate through all persons and mandatory tours in the household and choose a vehicle type for each
     * 
     * @param hhObj for which to apply the model
     */

    public void applyModelToMandatoryTours(Household hhObj)
    {
        // write info to log file
        if ( hhObj.getDebugChoiceModels() ) {
        	tourFreq.info("");
        	tourFreq.info("***************************************************************");
       	 	tourFreq.info("Calculating probability for AV availability for mandatory tours");
           	tourFreq.info("*********");
        }
    	double probability  = calculateProbability(hhObj);
    	
        // write info to log file
        if ( hhObj.getDebugChoiceModels() ) {
        	tourFreq.info("");
           	tourFreq.info("***************************************************************");
        }
  	
    	
    	
    	for(Person p : hhObj.getPersons()){
    		
    		if(p==null)
    			continue;
    		
    		if(p.getListOfWorkTours()!=null){
    			//work tours
    			for(Tour t : p.getListOfWorkTours()){
    			
    				Random hhRandom = hhObj.getHhRandom();
    				int randomCount = hhObj.getHhRandomCount();
    				double rn = hhRandom.nextDouble();
    				if(rn<probability)
    					t.setUseOwnedAV(true);
    				else
    					t.setUseOwnedAV(false);
    			}
    		}
    		
    		//school tours
    		if(p.getListOfSchoolTours()!=null){
    			for(Tour t : p.getListOfSchoolTours()){
    		
    			
    				Random hhRandom = hhObj.getHhRandom();
    				int randomCount = hhObj.getHhRandomCount();
    				double rn = hhRandom.nextDouble();
    				if(rn<probability)
    					t.setUseOwnedAV(true);
    				else
    					t.setUseOwnedAV(false);
    			}
    		}
    	}
    		
    }
    /**
    * Iterate through all persons and non-mandatory tours in the household and choose a vehicle type for each
    * 
    * @param hhObj for which to apply the model
    */

    public void applyModelToNonMandatoryTours(Household hhObj)
    {
        	
     	double probability  = calculateProbability(hhObj);
       		
       	for(Person p : hhObj.getPersons()){    		//individual non-mandatory tours
    
       		if(p==null)
    			continue;

       		if(p.getListOfIndividualNonMandatoryTours()!=null){
       			for(Tour t : p.getListOfIndividualNonMandatoryTours()){
    			
       				Random hhRandom = hhObj.getHhRandom();
       				int randomCount = hhObj.getHhRandomCount();
       				double rn = hhRandom.nextDouble();
       				if(rn<probability)
       					t.setUseOwnedAV(true);
       				else
       					t.setUseOwnedAV(false);
       			}
       		}
       	}
    }
    
    /**
    * Iterate through all persons and fully joint tours in the household and choose a vehicle type for each
    * 
    * @param hhObj for which to apply the model
    */

    public void applyModelToJointTours(Household hhObj)
    {
        	
     	double probability  = calculateProbability(hhObj);
      		
     	if(hhObj.getJointTourArray()!=null){
     		for(Tour t : hhObj.getJointTourArray()){
    			
     			Random hhRandom = hhObj.getHhRandom();
     			int randomCount = hhObj.getHhRandomCount();
     			double rn = hhRandom.nextDouble();
     			if(rn<probability)
   			  		t.setUseOwnedAV(true);
     			else
     				t.setUseOwnedAV(false);
     		}
     	}
    }
    /**
     * Iterate through all persons and at-work sub-tours in the household and choose a vehicle type for each
     * 
     * @param hhObj for which to apply the model
     */

     public void applyModelToAtWorkSubTours(Household hhObj)
     {

       	for(Person p : hhObj.getPersons()){    		//individual at-work sub-tours
    
       		if(p==null)
    			continue;

       		//At-work sub-tours; set to parent work tour availability
    		if(p.getListOfAtWorkSubtours()!=null){
    			for(Tour t : p.getListOfAtWorkSubtours()){
    		
    				int workTourIndex = t.getWorkTourIndexFromSubtourId(t.getTourId());
    				Tour workTour = p.getListOfWorkTours().get( workTourIndex );
    				boolean usedAV = workTour.getUseOwnedAV();
    				t.setUseOwnedAV(usedAV);
    			
    			}
    		}

       	}
     }

}
