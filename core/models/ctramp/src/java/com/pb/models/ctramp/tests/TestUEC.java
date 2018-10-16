package com.pb.models.ctramp.tests;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;

import com.pb.models.ctramp.TripModeChoiceDMU;
import com.pb.common.newmodel.UtilityExpressionCalculator;
import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ConcreteAlternative;
import com.pb.common.newmodel.LogitModel;

public class TestUEC {

	// get the array of alternatives for setting utilities
	private ConcreteAlternative[] alts;
	private String[] alternativeNames = null;
	private int numberOfAlternatives=0;

	private UtilityExpressionCalculator uec = null;
	private LogitModel root = null;
	private double[] probabilities;
	
	public TestUEC (String controlFileName, int modelSheet, int dataSheet, HashMap<String,String> propertyMap, Object dmuObject) {

        // create a UEC to get utilties for this choice model class
	    File uecFile = new File(controlFileName);
        uec = new UtilityExpressionCalculator( uecFile, modelSheet, dataSheet, propertyMap, (VariableTable)dmuObject );

      // get the list of concrete alternatives from this uec
      alts= new ConcreteAlternative[uec.getNumberOfAlternatives()];
      probabilities = new double[uec.getNumberOfAlternatives()];
      alternativeNames = uec.getAlternativeNames();
      numberOfAlternatives = uec.getNumberOfAlternatives();

      // create the logit model defined in cm object's uec (specified in UEC control file info passed into cm)
      createChoiceModel();
	}
	   private void createChoiceModel() {
	        
	        if ( uec.getNumberOfNestedLogitLevels() == 1 )
	            createLogitModel();
	        else
	            createNestedLogitModel(uec.getNestedLogitNestingStructure(), uec.getNestedLogitNestingCoefficients());
	    
	    }
	    
		/**
		 * create a LogitModel object for the tour mode choice model
		 */
		public void createLogitModel() {

			// create and define a new LogitModel object
			root = new LogitModel("root", 0, numberOfAlternatives);

			for(int i=0; i < numberOfAlternatives; i++) {
				alts[i]  = new ConcreteAlternative(alternativeNames[i], new Integer(i+1));
				root.addAlternative (alts[i]);
			}

		}
		
		
		/**
		 * create a LogitModel object for the tour mode choice model
		 */
		public void createNestedLogitModel(int[][] allocation, double[][] nestingCoefficients) {

	        
			// create and define a new LogitModel object
			root= new LogitModel("root", 0, numberOfAlternatives);


	        
			for(int i=0; i < numberOfAlternatives; i++)
				alts[i]  = new ConcreteAlternative(alternativeNames[i], new Integer(i+1));


			// tree structure defines nested logit model hierarchy.
			// alternatives are numbered starting at 1.
			// values in allocation[0][i] refers to elemental alternatives in nested logit model.
			// values in allocation[level][i] refers to parent branch number within level.

	        // initialize the dispersion parameters array with 1.0 and with one more row  than coefficents array
	        double[] dispersionParameters = new double[nestingCoefficients.length+1];
	        dispersionParameters[dispersionParameters.length-1] = 1.0;
	        for (int i=dispersionParameters.length-2; i >= 0; i--)
	            dispersionParameters[i] = dispersionParameters[i+1]/nestingCoefficients[i][0];
	        

	        
			int level = allocation.length - 1;
			root = buildNestedLogitModel (level, allocation, nestingCoefficients, dispersionParameters);
			
		}
		private LogitModel buildNestedLogitModel (int level, int[][] allocation, double[][] nestingCoefficients, double[] dispersionParameters) {

			int a=0;

			// level is the index number for the arrays in the allocation array for the current nesting level
			int newLevel;
			int[][] newAllocation = new int[level][];
	        double[][] newNestingCoefficients = new double[level][];
			LogitModel lm = null;
			LogitModel newLm = null;

			// find the maximum alternative number in the current nesting level
			int maxAlt = 0;
			int minAlt = 999999999;
			for (int i=0; i < allocation[level].length; i++) {
	            if (allocation[level][i] > maxAlt)
	                maxAlt = allocation[level][i];
	            if (allocation[level][i] < minAlt)
	                minAlt = allocation[level][i];
			}

			// create an array of branches for each alternative up to the altCount
			ArrayList<Integer>[] branchAlts = new ArrayList[maxAlt-minAlt+1];
			for (int i=0; i < maxAlt-minAlt+1; i++)
				branchAlts[i] = new ArrayList<Integer>();

	        
			// add alllocation[level] element numbers to the ArrayLists for each branch
			int altCount = 0;
			for (int i=0; i < allocation[level].length; i++) {
	            int index = allocation[level][i];
				if (branchAlts[index-minAlt].size() == 0)
					altCount++;
				branchAlts[index-minAlt].add( i );
			}
				
			// create a LogitModel for this level
			// with the number of unique alternatives determined from allocation[level].
			lm = new LogitModel( "level_"+level+"_alt_"+minAlt+"_to_"+maxAlt, 0, altCount );

			// dispersion parameters should always be set, even at level zero, from one nest up
			lm.setDispersionParameter(dispersionParameters[level+1]);
	        
			boolean[] altSet = new boolean[maxAlt+1];
			Arrays.fill (altSet, false);

			
			for (int i=0; i <= maxAlt-minAlt; i++) {
	            
				if (branchAlts[i].size() == 0)
					continue;
								
	            // create a logit model for each alternative with at least 2 sub-alternatives.
				if (branchAlts[i].size() >= 1 && level > 0) {

					// dispersion parameters should always be set, even at level zero
					//lm.setDispersionParameter(dispersionParameters[level]);
					
					for (int k=0; k < level; k++) {
						newAllocation[k] = new int[branchAlts[i].size()];
	                    newNestingCoefficients[k] = new double[branchAlts[i].size()];
						for (int j=0; j < branchAlts[i].size(); j++) {
							newAllocation[k][j] = allocation[k][(Integer)branchAlts[i].get(j)];
	                        newNestingCoefficients[k][j] = nestingCoefficients[k][(Integer)branchAlts[i].get(j)];
						}
					}							

			        // initialize the dispersion parameters array with value from parent
			        double[] newDispersionParameters = new double[level+1];
			        newDispersionParameters[level] = dispersionParameters[level+1] / nestingCoefficients[level][(Integer)branchAlts[i].get(0)]; 
			        for (int k=level-1; k >= 0; k--)
			            newDispersionParameters[k] = newDispersionParameters[k+1]/newNestingCoefficients[k][0];
			        
					// create the nested logit model
					newLevel = level - 1;	
					newLm = buildNestedLogitModel (newLevel, newAllocation, newNestingCoefficients, newDispersionParameters);
									
					lm.addAlternative(newLm);
				}
				else {
					a = allocation[level][(Integer)branchAlts[i].get(0)];
					if ( altSet[a] == false) {
						lm.addAlternative(alts[a]);
						altSet[a] = true;
					}
				}
			}

			return lm;
		}

	    /**
	     * Replicate the functionality in the ChoiceModelApplication computeUtilities() method.
	     */
	    public void computeUtilities ( double[] utilities ) {

	        //set utility for each alternative
	        for(int a=0; a < alts.length; a++){
	            alts[a].setAvailability( true );
	            alts[a].setUtility( utilities[a] );
	        }
	        root.setAvailability();

	        // call root.getUtility() to calculate exponentiated utilties.  The logit model logsum is returned.
	        double rootLogsum =  root.getUtility();
	        
	        // calculate logit probabilities
	        root.calculateProbabilities();
	        
	    }
	    /*
	     * apply the tour mode choice UEC to calculate the logit choice probabilities
	     * and return a chosen alternative for this household's tour mode choice
	     */
	    public int getChoiceResult( double randomNumber ) {

	        int chosenAlt = -1;

	        ConcreteAlternative chosen = (ConcreteAlternative) root.chooseAlternative( randomNumber );
	        String chosenAltName= chosen.getName();

	        // save chosen alternative in  householdChoice Array
	        for(int a=0; a < alts.length; a++) {
	            if (chosenAltName.equals(alternativeNames[a])) {
	                chosenAlt = a+1;
	                break;
	            }
	        }


	        return chosenAlt;

	    }

	    /**
	     * return the array of elemental alternative probabilities for this logit choice model
	     */
	    public double[] getProbabilities(){
	        
	         for (int i=0; i < numberOfAlternatives; i++) {
	            probabilities[i] = alts[i].getProbability();
	        }
	        
	        return probabilities;
	    
	    }
	    

	/**
	 * @param args
	 */
	public static void main(String[] args) {
		
		
		HashMap<String, String> propertyMap = new HashMap<String,String>();

		class TripModeChoiceDMU implements Serializable, VariableTable{
		    protected HashMap<String, Integer> methodIndexMap;
		    
		    public double getValueForIndex(int variableIndex, int arrayIndex) {
		    	return 1.0d;
		    }
		    public int getAssignmentIndexValue(String variableName) {
		        return 1;
		    }
		    public double getValueForIndex(int variableIndex) {
		        return 1.0d;
		    }
		    public int getIndexValue(String variableName) {
		        return 1;
		    }
		    public void setValue(String variableName, double variableValue) {
		        
		    }

		    public void setValue(int variableIndex, double variableValue) {
		        
		    }
		}
		TripModeChoiceDMU tmcd = new TripModeChoiceDMU();
		
		String uecFileName = "d:\\projects\\arc\\calibration\\2011-11-15\\a\\TripModeChoiceTest.xls";
		int modelSheet = 3;
		int dataSheet = 0;
		
		TestUEC test = new TestUEC( uecFileName, modelSheet, dataSheet, propertyMap, tmcd );

		double rnum=0;
		int result=-99;
		double[] probabilities;
		double sum=0;
		
		double[] utilities2 = { 
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00,
				 -1.297631e+00};

		for(int draw=0;draw<10;++draw){
			rnum += 0.0999999;
			test.computeUtilities(utilities2);
			result = test.getChoiceResult(rnum);
		
			System.out.println("Elemental Probabilities");
			probabilities = test.getProbabilities();
			sum=0;
			for(int i=0;i<probabilities.length;++i){
				sum+=probabilities[i];
				System.out.println("Alt "+(i+1)+" Prob "+probabilities[i]+" Cum "+sum);
			}
			System.out.println("Chose alt "+result+" with random number "+rnum);
		}
		double[] utilities = { 
				 -1.998298e+03,
				 -9.990000e+02,
				 -1.297631e+00,
				 -9.990000e+02,
				 -1.297631e+00,
				 -9.990000e+02,
				 -9.990000e+02,
				 -9.996147e+02,
				 -9.990000e+02,
				 -9.990000e+02,
				 -9.990000e+02,
				 -9.990000e+02,
				  2.818640e+00};

		rnum = 0.02058032;
		test.computeUtilities(utilities);
		result = test.getChoiceResult(rnum);
		sum=0;
		
		System.out.println("Elemental Probabilities");
		probabilities = test.getProbabilities();
		for(int i=0;i<probabilities.length;++i){
			sum+=probabilities[i];
			System.out.println("Alt "+(i+1)+" Prob "+probabilities[i]+" Cum "+sum);
		}
			System.out.println("Chose alt "+result+" with random number "+rnum);
		
		
	
		}

}
