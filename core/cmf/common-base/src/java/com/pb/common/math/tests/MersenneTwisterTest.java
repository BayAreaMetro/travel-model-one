package com.pb.common.math.tests;

import java.util.Arrays;
import java.util.Random;

import com.pb.common.math.MersenneTwister;


public class MersenneTwisterTest {

    private Random javaRandom;
    private MersenneTwister mtRandom;
	
    
    public MersenneTwisterTest(){
    	javaRandom = new Random();
    	mtRandom = new MersenneTwister();
    }
    
    /**
     * Test the java random number generator.
     * 
     * @param seed  Seed for the random number generator.
     * @param probabilities  An array of probabilities
     * @param draws  Number of draws
     */
	public void testJavaRandom(long seed, double[] probabilities, int draws){
		
		javaRandom.setSeed(seed);
		int[] results = new int[probabilities.length];
        long createTime = -System.currentTimeMillis();
		
		for(int i=0;i<draws;++i){
			
			double rnum = javaRandom.nextDouble();
			int chosenAlternative = chooseAlternative(probabilities,rnum);
			++results[chosenAlternative];
		}
	    createTime += System.currentTimeMillis();
		
		System.out.println("Results of testing java rng seeded using "+seed);
		System.out.println("Time "+createTime);
		for(int i =0;i<results.length;++i){
			System.out.println("Alternative "+i+" chosen "+results[i]+" times");
		}
	
	}
	
    /**
     * Test the mersenne twister random number generator.
     * 
     * @param seed  Seed for the random number generator.
     * @param probabilities  An array of probabilities
     * @param draws  Number of draws
     */
	public void testMTRandom(long seed, double[] probabilities, int draws){
		
		mtRandom.setSeed(seed);
		int[] results = new int[probabilities.length];
        long createTime = -System.currentTimeMillis();
		
		for(int i=0;i<draws;++i){
			
			double rnum = mtRandom.nextDouble();
			int chosenAlternative = chooseAlternative(probabilities,rnum);
			++results[chosenAlternative];
		}
	
	    createTime += System.currentTimeMillis();
		
		System.out.println("Results of testing mersenne twister rng seeded using "+seed);
		System.out.println("Time "+createTime);
		for(int i =0;i<results.length;++i){
			System.out.println("Alternative "+i+" chosen "+results[i]+" times");
		}
	}
	
	/**
	 * Return the index of the alternative corresponding to the random number.
	 * 
	 * @param probabilities  An array of probabilities
	 * @param rnum A random number
	 * @return Index of the chosen alternative
	 */
	public int chooseAlternative(double[] probabilities, double rnum){
		
		double cProb=0;
		for(int i=0;i<probabilities.length;++i){
			cProb += probabilities[i];			
			if(cProb>=rnum && probabilities[i]>0)
				return i;

			
		}	
		
		System.out.println("Error with random number "+rnum);
		return -9999;
	}	
	
	
	/**
	 * @param args
	 */
	public static void main(String[] args) {
		
		double[] probabilities = {
				0.000000e+00,
				0.000000e+00,
				9.701843e-03,
				0.000000e+00,
				9.701843e-03,
				0.000000e+00,
				7.263600e-02,
				0.000000e+00,
				0.000000e+00,
				0.000000e+00,
				0.000000e+00,
				0.000000e+00,
				9.079603e-01 };
	
		MersenneTwisterTest mtt = new MersenneTwisterTest();
		
		long seed = 828730;
		int draws = 100;
		
		for(int i=1;i<10;++i){
			mtt.testJavaRandom(seed, probabilities, draws);
			mtt.testMTRandom(seed, probabilities, draws);
			++seed;
		}
		seed = 1000;
		draws = 1000;
		mtt.testJavaRandom(seed, probabilities, draws);
		mtt.testMTRandom(seed, probabilities, draws);
		
		seed = 1000;
		draws = 100000;
		mtt.testJavaRandom(seed, probabilities, draws);
		mtt.testMTRandom(seed, probabilities, draws);

		seed = 1000;
		draws = 1000000;
		mtt.testJavaRandom(seed, probabilities, draws);
		mtt.testMTRandom(seed, probabilities, draws);
		
		
		//time seeding
		int householdModels=3;  // auto ownership, transponder ownership, CDAP
		int personModels = 4;   // mandatory location choice, mandatory generation, non-mandatory generation, participation
		int tourModels = 4;     // destination, time-of-day, mode, stop frequency 
		int stopModels = 2;     // location, timing
		int tripModels = 1;     // mode
		
		int[] householdModelOffsets = { 1121, 1122, 1123};
		int[] personModelOffsets = { 2121, 2122, 2123, 2124};
		int[] tourModelOffsets = { 3121, 3122, 3123, 3124};
		int[] stopModelOffsets = { 41210, 41220};
		int[] tripModelOffsets = { 51210};
		
		int households = 1000000;
		//int households = 1000;
		int personsPerHousehold = 3;
		int toursPerPerson = 2;
		int stopsPerTour = 2;
		int tripsPerTour = stopsPerTour+2;
		
		int totalPersons = households * personsPerHousehold;
		int totalTours = totalPersons * toursPerPerson;
		int totalStops = totalTours * stopsPerTour;
		int totalTrips = totalTours * tripsPerTour;
		
		int totalModels = households * householdModels + totalTours * tourModels + totalStops * stopModels + totalTrips * tripModels;
		
		int numberOfCycles = 0;
		
		// test mersenne twister with setting seed based on ids and model offsets
		MersenneTwister mt = mtt.mtRandom;
	    long createTime = -System.currentTimeMillis();
		
	    double[] seedProbabilities = new double[100];
	    long[] chosen = new long[100];
	    Arrays.fill(seedProbabilities, 0.01);
	    
		for(int household = 0; household < households; ++household){
			
			for(int householdModel = 0; householdModel < householdModels; ++householdModel){
				long testSeed = ((long)household + 1) + (long)householdModelOffsets[householdModel];
				mt.setSeed(testSeed);
				mtt.advanceRNG(mt,numberOfCycles);
				int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
				++chosen[a];
			}
			for(int person = 0; person < personsPerHousehold; ++person){
				
				for(int personModel = 0; personModel < personModels; ++personModel){
					long testSeed = ((long)household + 1) + (long)(person + 1 ) * 10000000 + (long)personModelOffsets[personModel];
					mt.setSeed(testSeed);
					mtt.advanceRNG(mt,numberOfCycles);
					int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
					++chosen[a];
				}

				for(int tour = 0; tour < toursPerPerson; ++tour){
				
					for(int tourModel = 0; tourModel < tourModels; ++tourModel){
						long testSeed = ((long)household + 1) + (long) (person + 1 ) * 10000000 
								+ (long) (tour + 1) * 100000000
								+ (long) tourModelOffsets[tourModel];
						mt.setSeed(testSeed);
						mtt.advanceRNG(mt,numberOfCycles);
						int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
						++chosen[a];
					}

					for(int stop = 0; stop < stopsPerTour; ++stop){
						for(int stopModel = 0; stopModel < stopModels; ++stopModel){
							long testSeed = ((long)household + 1) + (long) (person + 1 ) * 10000000 
									+ (long) (tour + 1) * 100000000
									+ (long) (stop + 1)
									+ (long) stopModelOffsets[stopModel];
							mt.setSeed(testSeed);
							mtt.advanceRNG(mt,numberOfCycles);
							int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
							++chosen[a];
						}
				
					}
					
					for(int trip = 0; trip < tripsPerTour; ++trip){
						for(int tripModel = 0; tripModel < tripModels; ++tripModel){
							long testSeed = ((long)household + 1) + (long) (person + 1 ) * 10000000 
									+ (long) (tour + 1) * 100000000
									+ (long) (trip + 1)
									+ (long) tripModelOffsets[tripModel];
							mt.setSeed(testSeed);
							mtt.advanceRNG(mt,numberOfCycles);
							int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
							++chosen[a];
						}
						
					}
					
					
				}
				
			}	
		}
	    createTime += System.currentTimeMillis();
		System.out.println("Results of testing mersenne twister rng seeding over "+totalModels+" models");
		System.out.println("Time "+createTime);
		
		for(int a = 0; a< chosen.length;++a)
			System.out.println("Alternative "+a+" chosen "+chosen[a]+" times");

		// test mersenne twister with setting seed once
		mt.setSeed(4347);
		Arrays.fill(chosen, 0);
	    createTime = -System.currentTimeMillis();
		
		for(int household = 0; household < households; ++household){
			
			for(int householdModel = 0; householdModel < householdModels; ++householdModel){
				int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
				++chosen[a];
			}
			for(int person = 0; person < personsPerHousehold; ++person){
				
				for(int personModel = 0; personModel < personModels; ++personModel){
					int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
					++chosen[a];
				}

				for(int tour = 0; tour < toursPerPerson; ++tour){
				
					for(int tourModel = 0; tourModel < tourModels; ++tourModel){
						int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
						++chosen[a];
					}

					for(int stop = 0; stop < stopsPerTour; ++stop){
						for(int stopModel = 0; stopModel < stopModels; ++stopModel){
							int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
							++chosen[a];
						}
				
					}
					
					for(int trip = 0; trip < tripsPerTour; ++trip){
						for(int tripModel = 0; tripModel < tripModels; ++tripModel){
							int a = mtt.chooseAlternative(seedProbabilities,mt.nextDouble());
							++chosen[a];
						}
						
					}
					
					
				}
				
			}	
		}
	    createTime += System.currentTimeMillis();
		System.out.println("Results of testing mersenne twister rng seeding once");
		System.out.println("Time "+createTime);
		
		for(int a = 0; a< chosen.length;++a)
			System.out.println("Alternative "+a+" chosen "+chosen[a]+" times");

	}
	
	public void advanceRNG(MersenneTwister mt, int numberOfCycles){
		
		for(int i =0;i<numberOfCycles;++i)
			mt.nextDouble();
	}

	
}
