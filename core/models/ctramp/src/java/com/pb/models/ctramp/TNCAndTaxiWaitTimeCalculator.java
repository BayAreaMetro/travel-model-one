package com.pb.models.ctramp;

import java.util.HashMap;

import org.apache.log4j.Logger;

import umontreal.iro.lecuyer.probdist.LognormalDist;



public class TNCAndTaxiWaitTimeCalculator {

    private static Logger           logger   = Logger.getLogger(TNCAndTaxiWaitTimeCalculator.class);

	private float[] startPopEmpPerSqMi;
	
	private LognormalDist[] TNCSingleWaitTimeDistribution;
	private LognormalDist[] TNCSharedWaitTimeDistribution;
	private LognormalDist[] TaxiWaitTimeDistribution;
	float[] meanTNCSingleWaitTime ;
	float[] meanTNCSharedWaitTime ;
	float[] meanTaxiWaitTime ;
	
    /**
     * Constructor; doesn't do anything (call @createTimeDistributions method next)
     */
    public TNCAndTaxiWaitTimeCalculator(){
    	
    }
    
	/**
	 *  Reads the propertyMap and finds values for property arrays
	 *    TNC.waitTime.mean, Taxi.waitTime.mean,
	 *    TNC.waitTime.sd, and Taxi.waitTime.sd - containing arrays
	 *    of wait time and standard deviations for TNCs and Taxis by area type,
	 *    plus an array of end ranges for area type (pop+emp)/sq miles
	 *    with an implied start value of 0. 
	 *    Creates and stores umontreal.iro.lecuyer.probdist.LognormalDist 
	 *    TNCWaitTimeDistribution[] and TaxiWaitTimeDistribution[] where 
	 *    each element of the distribution corresponds to the areatype range. 
	 * @param propertyMap
	 */

	public void createWaitTimeDistributions(HashMap<String, String> propertyMap){
		
		//read properties
		meanTNCSingleWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "TNC.single.waitTime.mean");
		float[] sdTNCSingleWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "TNC.single.waitTime.sd");

		meanTNCSharedWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "TNC.shared.waitTime.mean");
		float[] sdTNCSharedWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "TNC.shared.waitTime.sd");

		meanTaxiWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "Taxi.waitTime.mean");
		float[] sdTaxiWaitTime = Util.getFloatArrayFromPropertyMap(propertyMap, "Taxi.waitTime.sd");

		startPopEmpPerSqMi = Util.getFloatArrayFromPropertyMap(propertyMap, "WaitTimeDistribution.EndPopEmpPerSqMi");
		
		// create the distribution arrays
		TNCSingleWaitTimeDistribution = new LognormalDist[startPopEmpPerSqMi.length];
		TNCSharedWaitTimeDistribution = new LognormalDist[startPopEmpPerSqMi.length];
		TaxiWaitTimeDistribution = new LognormalDist[startPopEmpPerSqMi.length];

		//iterate through area types
		for(int i = 0; i< startPopEmpPerSqMi.length;++i){
			
			// calculate the location and scale parameters from the mean and standard deviations
			double locationTNCSingleWaitTime = calculateLocation(meanTNCSingleWaitTime[i], sdTNCSingleWaitTime[i]);
			double scaleTNCSingleWaitTime = calculateScale(meanTNCSingleWaitTime[i], sdTNCSingleWaitTime[i]);


			double locationTNCSharedWaitTime = calculateLocation(meanTNCSharedWaitTime[i], sdTNCSharedWaitTime[i]);
			double scaleTNCSharedWaitTime = calculateScale(meanTNCSharedWaitTime[i], sdTNCSharedWaitTime[i]);

			// create the TNC wait time distribution for this area type
			TNCSingleWaitTimeDistribution[i] = new LognormalDist(locationTNCSingleWaitTime, scaleTNCSingleWaitTime); 
			TNCSharedWaitTimeDistribution[i] = new LognormalDist(locationTNCSharedWaitTime, scaleTNCSharedWaitTime); 
			
			double locationTaxiWaitTime = calculateLocation(meanTaxiWaitTime[i], sdTaxiWaitTime[i]);
			double scaleTaxiWaitTime = calculateScale(meanTaxiWaitTime[i], sdTaxiWaitTime[i]);

			TaxiWaitTimeDistribution[i] = new LognormalDist(locationTaxiWaitTime, scaleTaxiWaitTime); 
						
		}
	}
	
	/**
	 * Calculate the lognormal distribution location given 
	 * the mean and standard deviation of the distribution 
	 * according to the formula:
	 * 
	 *  location = ln(mean/sqrt(1 + variance/mean^2))
	 * 
	 * @param mean 
	 * @param standardDeviation
	 * @return Location variable (u)
	 */
	public double calculateLocation(double mean, double standardDeviation){
		
		double variance = standardDeviation * standardDeviation;
		double meanSquared = mean  * mean;
		double denom = Math.sqrt(1.0 + (variance/meanSquared));
		double location = mean/denom;
		if(location<=0){
			logger.error("Error: Trying to calculation location for mean "+mean
					+" and standard deviation "+standardDeviation);
			throw new RuntimeException();
		}
		
		return Math.log(location);
		
	}

	/**
	 * Calculate the lognormal distribution scale given 
	 * the mean and standard deviation of the distribution 
	 * according to the formula:
	 *  
	 *  scale = sqrt(ln(1 + variance/mean^2));
	 * 
	 * @param mean 
	 * @param standardDeviation
	 * @return Scale variable (sigma)
	 */
	public double calculateScale(double mean, double standardDeviation){
		
		double variance = standardDeviation * standardDeviation;
		double meanSquared = mean  * mean;
		return Math.sqrt(Math.log(1 + variance/meanSquared));
	}

	/**
	 * Sample from the Single TNC wait time distribution and return the wait time.
	 * @param rnum A unit-distributed random number.
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The sampled TNC wait time.
	 */
	public double sampleFromSingleTNCWaitTimeDistribution(double rnum, double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return TNCSingleWaitTimeDistribution[i].inverseF(rnum);
			}
		}
		
		logger.error("Error: Attempting to find Single TNC wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getSingleTNCWaitTime method");
		throw new RuntimeException();
		
	}
	
	/**
	 * Sample from the Shared TNC wait time distribution and return the wait time.
	 * @param rnum A unit-distributed random number.
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The sampled TNC wait time.
	 */
	public double sampleFromSharedTNCWaitTimeDistribution(double rnum, double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return TNCSharedWaitTimeDistribution[i].inverseF(rnum);
			}
		}
		
		logger.error("Error: Attempting to find Shared TNC wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getSharedTNCWaitTime method");
		throw new RuntimeException();
		
	}
	

	/**
	 * Sample from the Taxi wait time distribution and return the wait time.
	 * @param rnum A unit-distributed random number.
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The sampled Taxi wait time.
	 */
	public double sampleFromTaxiWaitTimeDistribution(double rnum, double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return TaxiWaitTimeDistribution[i].inverseF(rnum);
			}
		}
		
		logger.error("Error: Attempting to find Taxi wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getTaxiWaitTime method");
		throw new RuntimeException();
		
	}
	
	/**
	 * Get the mean Taxi wait time for the density. This method would be used in the case that
	 * there is no household or person object to use for a random number draw.
	 * 
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The mean Taxi wait time.
	 */
	public double getMeanTaxiWaitTime( double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return meanTaxiWaitTime[i];
			}
		}
		
		logger.error("Error: Attempting to find mean Taxi wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getMeanTaxiWaitTime method");
		throw new RuntimeException();
		
	}
	
	/**
	 * Get the mean Single TNC wait time for the density. This method would be used in the case that
	 * there is no household or person object to use for a random number draw.
	 * 
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The mean TNC wait time.
	 */
	public double getMeanSingleTNCWaitTime( double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return meanTNCSingleWaitTime[i];
			}
		}
		
		logger.error("Error: Attempting to find mean Single TNC wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime method");
		throw new RuntimeException();
		
	}
	
	/**
	 * Get the mean Shared TNC wait time for the density. This method would be used in the case that
	 * there is no household or person object to use for a random number draw.
	 * 
	 * @param popEmpPerSqMi The population plus employment divided by square miles
	 * @return The mean TNC wait time.
	 */
	public double getMeanSharedTNCWaitTime( double popEmpPerSqMi){
		
		for(int i = 0; i < startPopEmpPerSqMi.length;++i){
			
			if(popEmpPerSqMi <startPopEmpPerSqMi[i]){
				return meanTNCSharedWaitTime[i];
			}
		}
		
		logger.error("Error: Attempting to find mean Shared TNC wait time for out-of-range population and employment density"+ popEmpPerSqMi);
		logger.error("Error: Throwing runtime exception from TNCAndTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime method");
		throw new RuntimeException();
		
	}


	
}
