package com.pb.models.ctramp;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Random;
import java.util.ResourceBundle;
import java.util.Set;

import org.apache.log4j.Logger;

import com.pb.common.calculator.UtilityExpressionCalculator;
import com.pb.common.calculator.IndexValues;
import com.pb.common.model.Alternative;
import com.pb.common.model.ConcreteAlternative;
import com.pb.common.model.LogitModel;
import com.pb.common.model.ModelException;

/**
 * Implements a coordinated daily activity pattern model, which is a joint choice of activity
 * types of each member of a household. The class builds and applies separate choice models for 
 * households of sizes 1, 2, 3, 4, and 5. For households larger than 5, the persons in the household
 * are ordered such that the first 5 members include up to 2 workers and 3 children (youngest to
 * oldest), the 5-person model is applied for these 5 household members, than a separate, simple
 * cross-sectional distribution is looked up for the remaining household members.
 * 
 * The utilities are computed using four separate UEC spreadsheets. The first computes the activity
 * utility for each person individually; the second computes the activity utility for each
 * person when paired with each other person; the third computes the activity utility for each 
 * person when paired with each group of two other people in the household; and the fourth computes
 * the activity utility considering all the members of the household. These utilities are then
 * aggregated to represent each possible activity pattern for the household, and the choice is made.
 * For households larger than 5, a second model is applied after the first, which selects a pattern
 * for the 5+ household members from a predefined distribution.  
 * 
 * @author D. Ory
 *
 */
public class CoordinatedDailyActivityPatternModel {
	
	public static Logger logger = Logger.getLogger(CoordinatedDailyActivityPatternModel.class);


    public static final String PROPERTIES_RESULTS_DAILY_ACTIVITY_PATTERN = "Results.CoordinatedDailyActivityPattern";


    public static final int UEC_DATA_PAGE    = 0;
	public static final int UEC_ONE_PERSON   = 1;
	public static final int UEC_TWO_PERSON   = 2;
	public static final int UEC_THREE_PERSON = 3;
	public static final int UEC_ALL_PERSON   = 4;
	
	public static final String MANDATORY_PATTERN    = "M";
	public static final String NONMANDATORY_PATTERN = "N";
	public static final String HOME_PATTERN         = "H";
	
	public static final String[] activityNameArray = {MANDATORY_PATTERN,NONMANDATORY_PATTERN,HOME_PATTERN};

	public static final int MAX_MODEL_HH_SIZE = 5;
	
	// collection of logit models - one for each household size
	protected ArrayList<LogitModel> logitModelList;
	
	// DMU for the UEC
	protected CoordinatedDailyActivityPatternDMU dmuObject;

    protected String cdapResultsFileName;

    // re-ordered collection of households
	protected Person[] cdapPersonArray;
	
	// Four separate UECs to compute segments of the utility
	protected UtilityExpressionCalculator onePersonUec, twoPeopleUec, threePeopleUec, allMemberInteractionUec;
	
	// summary collections
	protected HashMap<Integer,HashMap<String,Integer>> countByHhSizeAndPattern;
	protected HashMap<String,HashMap<String,Integer>> countByPersonTypeAndActivity;
	


    /**
	 * Constructor sets up a logit model for each of the 5 possible household sizes and reads in
	 * each of the four UEC model tabs.
	 * 
	 * @param uecFileName - should contain a tab for each of the four utility segments, as well
	 * as one for the data
	 * @param resourceBundle - should contain any references made in the UEC file (not used for anything
	 * other than the UEC call)
	 */
	public CoordinatedDailyActivityPatternModel(String uecFileName, ResourceBundle resourceBundle){
		
		createLogitModels();
		setUpModel(uecFileName, resourceBundle);
		
	}
	


    /**
     * Loops through the households in the HouseholdDataManager, gets the coordinated daily
     * activity pattern for each person in the household, and writes a text file with hhid,
     * personid, persnum, and activity pattern.
     *
     * @param householdDataManager
     */
    public void saveResults(HouseholdDataManagerIf householdDataManager, String projectDirectory){

        FileWriter writer;
        if ( cdapResultsFileName != null ) {

            cdapResultsFileName = projectDirectory + cdapResultsFileName;

            try {
                writer = new FileWriter(new File(cdapResultsFileName));
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred opening CDAP results file: %s.", cdapResultsFileName ) );
                throw new RuntimeException(e);
            }

            try {
                writer.write ( "HHID,PersonID,PersonNum,ActivityString\n" );
            }
            catch(IOException e){
                logger.fatal( "Exception occurred writing CDAP header in results file." ) ;
                throw new RuntimeException(e);
            }



            // get the array of households
            Household[] householdArray = householdDataManager.getHhArray();

            for(int i=1; i < householdArray.length; ++i){

                Household household = householdArray[i];
                int hhid = household.getHhId();

                // get the pattern for each person
                Person[] personArray = household.getPersons();
                for( int j=1; j < personArray.length; j++ ) {

                    int persId = personArray[j].getPersonId();
                    int persNum = personArray[j].getPersonNum();
                    String activityString = personArray[j].getCdapActivity();

                    try {
                        writer.write ( String.format("%d,%d,%d,%s\n", hhid, persId, persNum, activityString ));
                    }
                    catch(IOException e){
                        logger.fatal( String.format( "Exception occurred writing CDAP results file, hhid=%d, persId=%d, persNum=%d", hhid, persId, persNum ) );
                        throw new RuntimeException(e);
                    }

                } // j (person loop)

            }


            try {
                writer.close();
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred closing CDAP results file: %s.", cdapResultsFileName ) );
                throw new RuntimeException(e);
            }

        }

    }



    /**
     * Loops through the households in the HouseholdDataManager, applies the coordinated daily
     * activity pattern model, sets the pattern for the selected household (which, in turn, sets
     * the activity for each person), and summarizes the results by household size and pattern, as
     * well as by person type and activity.
     *
     * @param householdDataManager
     */
    public void applyModel(HouseholdDataManagerIf householdDataManager){

        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();

        // initialize the results maps/lists
        countByHhSizeAndPattern      = new HashMap<Integer,HashMap<String,Integer>>();
        countByPersonTypeAndActivity = new HashMap<String,HashMap<String,Integer>>();

        //TODO: check the indexing - 1 based or 0-based?
        // loop through households (1-based array)
        for(int i=1; i < householdArray.length; ++i){

            Household household = householdArray[i];

            // give some feedback
            if(i%500000==0) logger.info("... Processing household ID: "+household.getHhId());

            // get the activity pattern choice
            String pattern = getCoordinatedDailyActivityPatternChoice(household);

            // set the pattern for the household
            household.setCoordinatedDailyActivityPatternResult( pattern );

            // set the pattern for each person and count by person type
            Person[] personArray = household.getPersons();
            for(int j=1;j<personArray.length;++j){
                String activityString = pattern.substring(j-1,j);
                personArray[j].setDailyActivityResult(activityString);

                // set the person type for the results counting
                String personTypeString = "";

                if(personArray[j].getPersonTypeIsFullTimeWorker()==1){
                    personTypeString = Person.PERSON_TYPE_FULL_TIME_WORKER_NAME;
                }

                else if(personArray[j].getPersonTypeIsPartTimeWorker()==1){
                    personTypeString = Person.PERSON_TYPE_PART_TIME_WORKER_NAME;
                }

                else if(personArray[j].getPersonIsUniversityStudent()==1){
                    personTypeString = Person.PERSON_TYPE_UNIVERSITY_STUDENT_NAME;
                }

                else if(personArray[j].getPersonIsNonWorkingAdultUnder65()==1){
                    personTypeString = Person.PERSON_TYPE_NON_WORKER_NAME;
                }

                else if(personArray[j].getPersonIsNonWorkingAdultOver65()==1){
                    personTypeString = Person.PERSON_TYPE_RETIRED_NAME;
                }

                else if(personArray[j].getPersonIsStudentDriving()==1){
                    personTypeString = Person.PERSON_TYPE_STUDENT_DRIVING_NAME;
                }

                else if(personArray[j].getPersonIsStudentNonDriving()==1){
                    personTypeString = Person.PERSON_TYPE_STUDENT_NON_DRIVING_NAME;
                }

                else if(personArray[j].getPersonIsPreschoolChild()==1){
                    personTypeString = Person.PERSON_TYPE_PRE_SCHOOL_CHILD_NAME;
                }

                // check if the person type is in the map
                if(countByPersonTypeAndActivity.containsKey(personTypeString)){

                    HashMap<String,Integer> activityCountMap = countByPersonTypeAndActivity.get(personTypeString);

                    // check if the activity is in the activity map
                    if(activityCountMap.containsKey(activityString)){
                        int currentCount = activityCountMap.get(activityString);
                        currentCount++;
                        activityCountMap.put(activityString, currentCount);
                        countByPersonTypeAndActivity.put(personTypeString, activityCountMap);
                    }
                    else{
                        activityCountMap.put(activityString, 1);
                        countByPersonTypeAndActivity.put(personTypeString, activityCountMap);
                    }


                }
                else{
                    HashMap<String,Integer> activityCountMap = new HashMap<String,Integer>();
                    activityCountMap.put(activityString, 1);
                    countByPersonTypeAndActivity.put(personTypeString, activityCountMap);

                } // is personType in map if

            } // j (person loop)


            // count each type of pattern string by hhSize
            if(countByHhSizeAndPattern.containsKey(pattern.length())){
                HashMap<String,Integer> patternCountMap = countByHhSizeAndPattern.get(pattern.length());
                if(patternCountMap.containsKey(pattern)){
                    int currentCount = patternCountMap.get(pattern);
                    currentCount++;
                    patternCountMap.put(pattern, currentCount);
                }
                else{
                    patternCountMap.put(pattern, 1);
                    countByHhSizeAndPattern.put(pattern.length(), patternCountMap);
                }
            }
            else{
                HashMap<String,Integer> patternCountMap = new HashMap<String,Integer>();
                patternCountMap.put(pattern, 1);
                countByHhSizeAndPattern.put(pattern.length(), patternCountMap);

            } // is personType in map if

            // log results for debug households
            if(household.getDebugChoiceModels()){

                logger.info(" ");
                logger.info("CDAP Chosen Pattern by Person Type");
                logger.info("CDAP # FT W PT W UNIV NONW RETR SCHD SCHN PRES");
                logger.info("------ ---- ---- ---- ---- ---- ---- ---- ----");

                String bString = "";
                for(int j=1;j<personArray.length;++j){

                    String pString = pattern.substring(j-1, j);
                    String stringToLog = "";

                    if(personArray[j].getPersonTypeIsFullTimeWorker()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,pString,bString,bString,bString,bString,bString,bString,bString);
                    }

                    else if(personArray[j].getPersonTypeIsPartTimeWorker()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,pString,bString,bString,bString,bString,bString,bString);
                    }

                    else if(personArray[j].getPersonIsUniversityStudent()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,pString,bString,bString,bString,bString,bString);
                    }

                    else if(personArray[j].getPersonIsNonWorkingAdultUnder65()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,bString,pString,bString,bString,bString,bString);
                    }

                    else if(personArray[j].getPersonIsNonWorkingAdultOver65()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,bString,bString,pString,bString,bString,bString);
                    }

                    else if(personArray[j].getPersonIsStudentDriving()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,bString,bString,bString,pString,bString,bString);
                    }

                    else if(personArray[j].getPersonIsStudentNonDriving()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,bString,bString,bString,bString,pString,bString);
                    }

                    else if(personArray[j].getPersonIsPreschoolChild()==1){
                        stringToLog = String.format("%6d%5s%5s%5s%5s%5s%5s%5s%5s",
                                j,bString,bString,bString,bString,bString,bString,bString,pString);
                    }

                    logger.info(stringToLog);

                } // j (person loop)

                logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                logger.info(" ");

            } // if traceMe

        }

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setCdapRandomCount();



    }



    /**
     * Records the coordinated daily activity pattern model results to the logger. A household-level
     * summary simply records each pattern type and a person-level summary summarizes the activity
     * choice by person type (full-time worker, university student, etc). 
     *
     */
    public void logResults(){
    	
    	logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
    	logger.info("Coordinated Daily Activity Pattern Model Results");
    	
    	// count of activities by person type
    	logger.info(" ");
    	logger.info("CDAP Results: Count of activities by person type");
    	String firstHeader  = "Person type                    ";
    	String secondHeader = "-----------------------------  ";
		for(int i=0;i<activityNameArray.length;++i){
			firstHeader  += "        " + activityNameArray[i] + " ";
			secondHeader += "--------- ";
		}

        firstHeader  += "    Total";
        secondHeader += "---------";

        logger.info(firstHeader);
		logger.info(secondHeader);

        int[] columnTotals = new int[activityNameArray.length];

        for(int i=0;i<Person.personTypeNameArray.length;++i){
			String personType = Person.personTypeNameArray[i];
			String stringToLog  = String.format("%-30s", personType);
            int lineTotal = 0;

            if(countByPersonTypeAndActivity.containsKey(personType)){
				
				for(int j=0;j<activityNameArray.length;++j){
					int count = 0;
					if(countByPersonTypeAndActivity.get(personType).containsKey(activityNameArray[j])){
						count = countByPersonTypeAndActivity.get(personType).get(activityNameArray[j]);
					}
					stringToLog += String.format("%10d",count);

                    lineTotal += count;
                    columnTotals[j] += count;
                } // j
				
			} // if key
			
            stringToLog += String.format("%10d",lineTotal);
			logger.info(stringToLog);
			
		} // i

        logger.info(secondHeader);

        String stringToLog  = String.format("%-30s", "Total");
        int lineTotal = 0;
        for(int j=0;j<activityNameArray.length;++j){
            stringToLog += String.format("%10d",columnTotals[j]);
            lineTotal += columnTotals[j];
        } // j

        stringToLog += String.format("%10d",lineTotal);
        logger.info(stringToLog);


        // count of patterns
        logger.info(" ");
        logger.info(" ");
    	logger.info("CDAP Results: Count of patterns");
    	logger.info("Pattern                Count");
    	logger.info("------------------ ---------");
    	
    	// sort the map by hh size first
    	Set<Integer> hhSizeKeySet = countByHhSizeAndPattern.keySet();
    	Integer[] hhSizeKeyArray = new Integer[hhSizeKeySet.size()];
    	hhSizeKeySet.toArray(hhSizeKeyArray);
    	Arrays.sort(hhSizeKeyArray);

        int total = 0;
        for(int i=0;i<hhSizeKeyArray.length;++i){
    		
    		// sort the patterns alphabetically
    		HashMap<String,Integer> patternMap = countByHhSizeAndPattern.get(hhSizeKeyArray[i]);
    		Set<String> patternKeySet = patternMap.keySet();
    		String[] patternKeyArray = new String[patternKeySet.size()];
    		patternKeySet.toArray(patternKeyArray);
    		Arrays.sort(patternKeyArray);
    		for(int j=0;j<patternKeyArray.length;++j){
    			int count = patternMap.get(patternKeyArray[j]);
                total += count;
                logger.info(String.format("%-18s%10d",patternKeyArray[j],count));
    		}
    		
    	}
        
        logger.info("------------------ ---------");
        logger.info(String.format("%-18s%10d","Total",total));
        logger.info(" ");

    	logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");
        
    }
	
    /**
     * Selects the coordinated daily activity pattern choice for the passed in Household. The
     * method works for households of all sizes, though two separate models are applied for 
     * households with more than 5 members. 
     * 
     * @param householdObject
     * @return a string of length household size, where each character in the string represents
     * the activity pattern for that person, in order (see Household.reOrderPersonsForCdap method).
     */
	public String getCoordinatedDailyActivityPatternChoice( Household householdObject ){
		
		// set all household level dmu variables
		dmuObject.setHousehold(householdObject);
		
		// set the hh size (cap modeled size at MAX_MODEL_HH_SIZE)
		int actualHhSize = householdObject.getSize();
		int modelHhSize  = Math.min(MAX_MODEL_HH_SIZE, actualHhSize);
		
		// reorder persons for large households if need be
		reOrderPersonsForCdap(householdObject);
		
		// get the logit model we need and clear it of any lingering probilities
		LogitModel workingLogitModel = logitModelList.get(modelHhSize-1);
		workingLogitModel.clear();
		
		// get the alternatives and reset the utilities to zero
		ArrayList alternativeList = workingLogitModel.getAlternatives();
		for(int i=0;i<alternativeList.size();++i){
			Alternative tempAlt = (Alternative)alternativeList.get(i);
			tempAlt.setUtility(0.0);
		}
		
		// write the debug header if we have a trace household
		if(householdObject.getDebugChoiceModels()){
			
			logger.info(" ");
			logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
			logger.info("CDAP Model: Debug Statement for Household ID: "+householdObject.getHhId());
			String firstHeader  = "Utility Segment                 PersonA  PersonB  PersonC";
			String secondHeader = "------------------------------ -------- -------- --------";
			for(int j=0;j<activityNameArray.length;++j){
				firstHeader  += "    " + activityNameArray[j] + " util";
				secondHeader += " ---------"; 
			}
			
			logger.info(firstHeader);
			logger.info(secondHeader);
			
		}
		
		
		// all the alternatives are available for all households (1-based, ignore 0 index and set other three to 1.)
		int[] availability = {-1,1,1,1};
		
		// loop through each person
		for(int i=0;i<modelHhSize;++i){
			
			// get personA
			Person personA = getCdapPerson(i+1);
			
			// set the person level dmu variables
			dmuObject.setPersonA(personA);
			
			// compute the single person utilities
			double[] firstPersonUtilities = onePersonUec.solve(dmuObject.getIndexValues(), dmuObject, availability);
			
			// log these utilities for trace households
			if(householdObject.getDebugChoiceModels()){
				
				String stringToLog  = String.format("%-30s%9d%9s%9s", "OnePerson",(i+1),"--","--");

    			for(int j=0;j<activityNameArray.length;++j){
    				stringToLog  += String.format("%10.4f", firstPersonUtilities[j]);
    			}
    			logger.info(stringToLog);
	
			} // debug trace
			
			
			// align the one person utilities with the alternatives for person i
			for(int j=0;j<alternativeList.size();++j){
				
				// get the name of the alternative
				Alternative tempAlt = (Alternative)alternativeList.get(j);
				String altName = tempAlt.getName();
				
				// get the name of the activity for this person in the alternative string
				String altNameForPersonA = altName.substring(i, i+1);
				
				// align the utility results with this activity 
				for(int k=0;k<activityNameArray.length;++k){
			
					if(altNameForPersonA.equalsIgnoreCase(activityNameArray[k])){
						double currentUtility = tempAlt.getUtility();
						tempAlt.setUtility(currentUtility + firstPersonUtilities[k]);		
					}
				} // k
				
			} // j
			
			// loop through all possible person Bs
			for(int j=0;j<modelHhSize;++j){
				
				// skip if same as person A
				if(i==j) continue;
				
				// skip if i>j because if we have 1,2 for person 1, we don't also want 2,1; that's the
				// same combination of two people
				if(i>j) continue;
				
				Person personB = getCdapPerson(j+1);
				
				// set the two person level dmu variables
				dmuObject.setPersonB(personB);
				
				// compute the two people utilities
				double[] twoPersonUtilities = twoPeopleUec.solve(dmuObject.getIndexValues(),dmuObject,availability);
				
				// log these utilities for trace households
				if(householdObject.getDebugChoiceModels()){
					
					String stringToLog  = String.format("%-30s%9d%9d%9s", "TwoPeople",(i+1),(j+1),"--");

	    			for(int k=0;k<activityNameArray.length;++k){
	    				stringToLog  += String.format("%10.4f", twoPersonUtilities[k]);
	    			}
	    			logger.info(stringToLog);
		
				} // debug trace
				
				// align the two person utilities with the alternatives for person i
				for(int k=0;k<alternativeList.size();++k){
					Alternative tempAlt = (Alternative)alternativeList.get(k);
					String altName = tempAlt.getName();
					
                    // get the name of the activity for this person in the alternative string
                    String altNameForPersonA = altName.substring(i, i+1);
                    String altNameForPersonB = altName.substring(j, j+1);
                    
                    for(int l=0;l<activityNameArray.length;++l){
                        if(altNameForPersonA.equalsIgnoreCase(activityNameArray[l])
                                && altNameForPersonB.equalsIgnoreCase(activityNameArray[l])){
                            double currentUtility = tempAlt.getUtility();
                            tempAlt.setUtility(currentUtility + twoPersonUtilities[l]);     
                        }
                    } // l
				} // k 
				
				// loop through all possible person Cs
				for(int k=0;k<modelHhSize;++k){
					
					// skip if same as person A
					if(i==k) continue;
					
					// skip if same as person B
					if(j==k) continue;
					
					// skip if j>k because if we have 1,2,3 for person 1, we don't also want 1,3,2; that's the
					// same combination of three people
					if(j>k) continue;
					
					Person personC = getCdapPerson(k+1);
					
					// set the three level dmu variables
					dmuObject.setPersonC(personC);
					
					// compute the three person utilities
					double[] threePersonUtilities = threePeopleUec.solve(dmuObject.getIndexValues(),dmuObject,availability);
					
					// log these utilities for trace households
					if(householdObject.getDebugChoiceModels()){
						
						String stringToLog  = String.format("%-30s%9d%9d%9d", "ThreePeople",(i+1),(j+1),(k+1));

		    			for(int l=0;l<activityNameArray.length;++l){
		    				stringToLog  += String.format("%10.4f", threePersonUtilities[l]);
		    			}
		    			logger.info(stringToLog);
						
			
					} // debug trace
					
					// align the three person utilities with the alternatives for person i
					for(int l=0;l<alternativeList.size();++l){
						Alternative tempAlt = (Alternative)alternativeList.get(l);
						String altName = tempAlt.getName();
						
                        // get the name of the activity for this person in the alternative string
                        String altNameForPersonA = altName.substring(i, i+1);
                        String altNameForPersonB = altName.substring(j, j+1);
                        String altNameForPersonC = altName.substring(k, k+1);
                        
                        for(int m=0;m<activityNameArray.length;++m){
                            if(altNameForPersonA.equalsIgnoreCase(activityNameArray[m]) &&
                                    altNameForPersonB.equalsIgnoreCase(activityNameArray[m]) &&
                                    altNameForPersonC.equalsIgnoreCase(activityNameArray[m])){
                                double currentUtility = tempAlt.getUtility();
                                tempAlt.setUtility(currentUtility + threePersonUtilities[m]);       
                            }
                        } // m
					} // l 
					
				} // k (person C loop)
					
			} // j (person B loop)
			
		} // i (person A loop)
		
	    // compute the interaction utilities
		double[] allMemberInteractionUtilities = allMemberInteractionUec.solve(dmuObject.getIndexValues(), dmuObject, availability);
		
		// log these utilities for trace households
		if(householdObject.getDebugChoiceModels()){
			
			String stringToLog  = String.format("%-30s%9s%9s%9s", "AllMembers","--","--","--");

			for(int i=0;i<activityNameArray.length;++i){
				stringToLog  += String.format("%10.4f", allMemberInteractionUtilities[i]);
			}
			logger.info(stringToLog);
			
		} // debug trace
		
		// align the utilities with the proper alternatives
		for(int i=0;i<alternativeList.size();++i){
			Alternative tempAlt = (Alternative)alternativeList.get(i);
			String altName = tempAlt.getName();
			
			for(int j=0;j<activityNameArray.length;++j){
				
				boolean samePattern = true;
				for(int k=0;k<modelHhSize;++k){
					
					// alternative should have pattern j for each member k
					String altNameForThisPerson = altName.substring(k, k+1);
					if(altNameForThisPerson.equalsIgnoreCase(activityNameArray[j])) continue;
					else{
						samePattern = false;
						break;
					}
				} // k
				
				// if all have the same pattern, add the new utilities
				if(samePattern){
					double currentUtility = tempAlt.getUtility();
					tempAlt.setUtility(currentUtility + allMemberInteractionUtilities[j]);	
				}
			} // j
			
		} // i


        //TODO: check this out - use computeAvailabilty() checks that an alternative is available
        // all utilities are set - compute probabilities
		//workingLogitModel.setAvailability(true);
        workingLogitModel.computeAvailabilities();

        // compute the exponentiated utility, logging debug if need be
		if(householdObject.getDebugChoiceModels()){
			workingLogitModel.setDebug(true);
			workingLogitModel.writeUtilityHeader();
		}
		workingLogitModel.getUtility();
		
		// compute the probabilities, logging debug if need be
		if(householdObject.getDebugChoiceModels()){
			workingLogitModel.writeProbabilityHeader();
		}
		workingLogitModel.calculateProbabilities();
		
		// turn debug off for the next guy
		workingLogitModel.setDebug(false);
		
		// make a choice for the first five
		Random hhRandom = householdObject.getHhRandom();
		
		double randomNumber = hhRandom.nextDouble();


        String firstFiveChosenName = "";
        try {
            ConcreteAlternative chosenAlternative = (ConcreteAlternative) workingLogitModel.chooseElementalAlternative(randomNumber);
            firstFiveChosenName = chosenAlternative.getName();
        }
        catch ( ModelException e ) {
            logger.error ( String.format( "Exception caught for HHID=%d, no available CDAP alternatives to choose.", householdObject.getHhId() ), e );
            throw new RuntimeException();
        }

		// make a choice for additional hh members if need be
		if(actualHhSize>MAX_MODEL_HH_SIZE){
			
			String allMembersChosenPattern = applyModelForExtraHhMembers(householdObject,firstFiveChosenName);

            // re-order the activities by the original order of persons
            String finalHhPattern = "";
            String[] finalHhPatternActivities = new String[cdapPersonArray.length];
            for ( int i=1; i < cdapPersonArray.length; i++ ) {
                int k = cdapPersonArray[i].getPersonNum();
                finalHhPatternActivities[k] = allMembersChosenPattern.substring( i-1, i );
            }

            for ( int i=1; i < cdapPersonArray.length; i++ )
                finalHhPattern += finalHhPatternActivities[i];

            return finalHhPattern;

		}



        // no need to re-order the activities - hhsize <= MAX_MODEL_HH_SIZE have original order of persons
        return firstFiveChosenName;
		
		
	}
	/**
	 * Applies a simple, segmented fixed-distribution model for members of households with more than
	 * 5 people who are not included in the CDAP model. The choices of the additional household
	 * members are independent of each other, but dependent on the pattern choice for the 5 
	 * modeled household members. 
	 * 
	 * @param householdObject
	 * @param patternStringForOtherHhMembers
	 * @return the pattern for the entire household, including the 5-member pattern chosen by the 
	 * logit model and the additional members chosen by the fixed-distribution model. 
	 * 
	 */
	private String applyModelForExtraHhMembers(Household householdObject, String patternStringForOtherHhMembers){
		
		String allMembersPattern = patternStringForOtherHhMembers;
		
		// get the persons not yet modeled
		Person[] personArray = getPersonsNotModeledByCdap(MAX_MODEL_HH_SIZE);
		
		// person array is 1-based to be consistent with other person arrays
		for(int i=1;i<personArray.length;++i){
			
			// five variables for which the model is applied
			boolean worker  = false;
			boolean student = false;
			boolean other   = false;
			
			boolean mandatoryPatternInHh            = false;
			boolean preschoolChildAtHomeWithNoAdult = false;
			
			// check for each of the five variables
			if(personArray[i].getPersonIsWorker()==1){
				
				worker = true;

				// is there a mandatory pattern in the string
				if(patternStringForOtherHhMembers.indexOf(MANDATORY_PATTERN)!=-1) 
					mandatoryPatternInHh = true;
					
			}
			else if(personArray[i].getPersonIsStudentDriving()==1 || 
					personArray[i].getPersonIsStudentNonDriving()==1){
				student = true;
			}
			else{
				other = true;
			}
			
			if(personArray[i].getPersonIsAdult()==1){
				
				// see if we have a preschool child at home and/or an adult at home
				boolean preschoolChildAtHome = false;
				boolean adultAtHome = false;
				
				for(int j=0;j<patternStringForOtherHhMembers.length();++j){
					String patternType = patternStringForOtherHhMembers.substring(j, j+1);
					if(patternType.equalsIgnoreCase(HOME_PATTERN)){
						
						if( isThisCdapPersonPreschoolChild(j+1) ){
							preschoolChildAtHome = true;
							if(adultAtHome) break;
						}
						
						if( isThisCdapPersonAnAdult(j+1) ){
							adultAtHome = true;
							if(preschoolChildAtHome) break;
						}
						
					}
				} // j (loop through pattern string)
				
				// do we have a preschool child at home without an adult?
				if(preschoolChildAtHome && !adultAtHome) preschoolChildAtHomeWithNoAdult = true; 
				
				
			}
			
			// TODO now apply model
			// for now append non mandatory for every person
			allMembersPattern += NONMANDATORY_PATTERN;
			
			
			
		}
		
		return allMembersPattern;
		
	}
	
	/**
	 * Establishes the four UECs, which are used to compute four segments of the
	 * joint utility. 
	 * 
	 * @param uecFileName
	 * @param resourceBundle
	 */
	private void setUpModel(String uecFileName, ResourceBundle resourceBundle){

        cdapResultsFileName = resourceBundle.getString( PROPERTIES_RESULTS_DAILY_ACTIVITY_PATTERN );

        // create the dmu object
		dmuObject = new CoordinatedDailyActivityPatternDMU();
		
		// create the uecs
		onePersonUec = new UtilityExpressionCalculator(new File(uecFileName),UEC_ONE_PERSON,UEC_DATA_PAGE,
				resourceBundle,dmuObject.getClass());
		
		twoPeopleUec = new UtilityExpressionCalculator(new File(uecFileName),UEC_TWO_PERSON,UEC_DATA_PAGE,
				resourceBundle,CoordinatedDailyActivityPatternDMU.class);
		
		threePeopleUec = new UtilityExpressionCalculator(new File(uecFileName),UEC_THREE_PERSON,UEC_DATA_PAGE,
				resourceBundle,CoordinatedDailyActivityPatternDMU.class);
		
		allMemberInteractionUec = new UtilityExpressionCalculator(new File(uecFileName),UEC_ALL_PERSON,UEC_DATA_PAGE,
				resourceBundle,CoordinatedDailyActivityPatternDMU.class);
		
	}
	
	/**
	 * Prepares a separate logit model for households of size 1, 2, 3, 4, and 5. Each model
	 * has 3^n alternatives, where n is the household size. The models are cleared and re-used
	 * for each household of the specified size. 
	 *
	 */
	private void createLogitModels(){
		
		// new the collection of logit models
		logitModelList = new ArrayList<LogitModel>(MAX_MODEL_HH_SIZE);
		
		// build a model for each HH size
		for(int i=0;i<MAX_MODEL_HH_SIZE;++i){
		
			int hhSize = i + 1;
			
			// create the working model
			LogitModel workingLogitModel = new LogitModel( hhSize + " Person HH" );
			
			// compute the number of alternatives
			int numberOfAlternatives = 1;
			for(int j=0;j<hhSize;++j) numberOfAlternatives *= activityNameArray.length;
			
			// create a counter for each of the people in the hh
			int[] counterForEachPerson = new int[hhSize];
			Arrays.fill(counterForEachPerson,0);
			
			// create the alternatives and add them to the logit model
			int numberOfAltsCounter = 0;
			while(numberOfAltsCounter<numberOfAlternatives){
				
				// set the string for the alternative
				String alternativeName = "";
				for(int j=0;j<hhSize;++j) alternativeName += activityNameArray[counterForEachPerson[j]];
				
				// create the alternative and add it to the model
				ConcreteAlternative tempAlt = new ConcreteAlternative(alternativeName,numberOfAltsCounter);
				workingLogitModel.addAlternative(tempAlt);
				numberOfAltsCounter++;
				
				// check increment the counters
				for(int j=0;j<hhSize;++j){
					counterForEachPerson[j]++;
					if(counterForEachPerson[j]==activityNameArray.length) counterForEachPerson[j] = 0;
					else break;
				}
				
			}
			
			// add the model to the array list
			logitModelList.add(i, workingLogitModel);
			
		} // for i max hh size
				
		
	}
	
    /**
     * Method reorders the persons in the household for use with the CDAP model, which only
     * explicitly models the interaction of five persons in a HH. Priority in the reordering is first
     * given to full time workers (up to two), then to part time workers (up to two workers, of any type),
     * then to children (youngest to oldest, up to three). If the method is called for a household with
     * less than 5 people, the cdapPersonArray is the same as the person array.
     *
     */
    public void reOrderPersonsForCdap(Household household){
    	
    	// set the person array
    	Person[] persons = household.getPersons();
    	
    	// if hh is not too big, set cdap equal to persons and return
    	int hhSize = household.getSize();
    	if(hhSize<=MAX_MODEL_HH_SIZE){
    		cdapPersonArray = persons;
    		return;
    	}



        // create the end game array
    	cdapPersonArray = new Person[persons.length];
    	
    	// keep track of which persons you count
    	boolean[] iCountedYou = new boolean[persons.length];
    	Arrays.fill(iCountedYou, false);
    	
    	// define the persons we want to find among the five
    	int firstWorkerIndex         = -99;
    	int secondWorkerIndex        = -99;
    	
    	int youngestChildIndex       = -99;
    	int secondYoungestChildIndex = -99;
    	int thirdYoungestChildIndex  = -99;
    	
    	int youngestChildAge = 99;
    	int secondYoungestChildAge = 99;
    	int thirdYoungestChildAge  = 99;
    	
    	// first: full-time workers (persons is 1-based array)
    	for(int i=1;i<persons.length;++i){
    		
    		if(iCountedYou[i]) continue;
    		
    		// is the person a full-time worker
    		if(persons[i].getPersonIsFullTimeWorker()==1){
    			
    			// check our indices
    			if(firstWorkerIndex==-99){
    				firstWorkerIndex = i;
    				iCountedYou[i] = true;
    			}
    			else if(secondWorkerIndex==-99){
    				secondWorkerIndex = i;
    				iCountedYou[i] = true;
    			}
    		}
    		
    	} // i (full time workers)
    	
    	// second: part-time workers (only if we don't have two workers)
    	if(firstWorkerIndex==-99 || secondWorkerIndex==-99){
    		
    		for(int i=1;i<persons.length;++i){
    			
    			if(iCountedYou[i]) continue;
    			
    			// is the person part-time worker
    			if(persons[i].getPersonIsPartTimeWorker()==1){

    				// check our indices
        			if(firstWorkerIndex==-99){
        				firstWorkerIndex = i;
        				iCountedYou[i] = true;
        			}
        			else if(secondWorkerIndex==-99){
        				secondWorkerIndex = i;
        				iCountedYou[i] = true;
        			}
    				
    			} 
    			
    		} // i (part-time workers)
    	}
    	
    	// third: youngest child loop
    	for(int i=1;i<persons.length;++i){
    		
    		if(iCountedYou[i]) continue;
    		
    		if(persons[i].getPersonIsPreschoolChild()==1 ||
    				persons[i].getPersonIsStudentNonDriving()==1 ||
    				persons[i].getPersonIsStudentDriving()==1){
    			
    			// check our indices
    			if(youngestChildIndex==-99){
    				youngestChildIndex = i;
    				youngestChildAge = persons[i].getAge();
    				iCountedYou[i] = true;
    			}
    			else{
    				
    				// see if this child is younger than the one on record
    				int age = persons[i].getAge();
    				if(age<youngestChildAge){
    					
    					// reset iCountedYou for previous child
    					iCountedYou[youngestChildIndex] = false;
    					
    					// set variables for this child
    					youngestChildIndex = i;
        				youngestChildAge = age;
        				iCountedYou[i] = true;
    					
    				}
    			}
    			
    		} // if person is child
    		
    	} // i (youngest child loop)

    	// fourth: second youngest child loop (skip if youngest child is not filled)
    	if(youngestChildIndex!=-99){
    		
    		for(int i=1;i<persons.length;++i){
        		
        		if(iCountedYou[i]) continue;
        		
        		if(persons[i].getPersonIsPreschoolChild()==1 ||
        				persons[i].getPersonIsStudentNonDriving()==1 ||
        				persons[i].getPersonIsStudentDriving()==1){
        			
        			// check our indices
        			if(secondYoungestChildIndex==-99){
        				secondYoungestChildIndex = i;
        				secondYoungestChildAge = persons[i].getAge();
        				iCountedYou[i] = true;
        			}
        			else{
        				
        				// see if this child is younger than the one on record
        				int age = persons[i].getAge();
        				if(age<secondYoungestChildAge){
        					
        					// reset iCountedYou for previous child
        					iCountedYou[secondYoungestChildIndex] = false;
        					
        					// set variables for this child
        					secondYoungestChildIndex = i;
        					secondYoungestChildAge = age;
            				iCountedYou[i] = true;
        					
        				}
        			}
        			
        		} // if person is child
        		
        	} // i (second youngest child loop)
    	}
    	
    	
    	// fifth: third youngest child loop (skip if second kid not included)
    	if(secondYoungestChildIndex!=-99){
    		
    		for(int i=1;i<persons.length;++i){
        		
        		if(iCountedYou[i]) continue;
        		
        		if(persons[i].getPersonIsPreschoolChild()==1 ||
        				persons[i].getPersonIsStudentNonDriving()==1 ||
        				persons[i].getPersonIsStudentDriving()==1){
        			
        			// check our indices
        			if(thirdYoungestChildIndex==-99){
        				thirdYoungestChildIndex = i;
        				thirdYoungestChildAge = persons[i].getAge();
        				iCountedYou[i] = true;
        			}
        			else{
        				
        				// see if this child is younger than the one on record
        				int age = persons[i].getAge();
        				if(age<thirdYoungestChildAge){
        					
        					// reset iCountedYou for previous child
        					iCountedYou[thirdYoungestChildIndex] = false;
        					
        					// set variables for this child
        					thirdYoungestChildIndex = i;
        					thirdYoungestChildAge = age;
            				iCountedYou[i] = true;
        					
        				}
        			}
        			
        		} // if person is child
        		
        	} // i (third youngest child loop)
    	}
    	
    	
    	// assign any missing spots among the top 5 to random members
    	int cdapPersonIndex;


        Random hhRandom = household.getHhRandom();

        int randomCount = household.getHhRandomCount();
        // when household.getHhRandom() was applied, the random count was incremented, assuming a random number would be drawn right away.
        // so let's decrement by 1, then increment the count each time a random number is actually drawn in this method.
        randomCount --;


        // first worker
    	cdapPersonIndex = 1; // persons and cdapPersonArray are 1-based
    	if(firstWorkerIndex==-99){
    		

    		int randomIndex = (int)( hhRandom.nextDouble() * hhSize );
            randomCount++;
            while(iCountedYou[randomIndex] || randomIndex==0) {
                randomIndex = (int)( hhRandom.nextDouble() * hhSize );
                randomCount++;
            }
    		
    		cdapPersonArray[cdapPersonIndex] = persons[randomIndex];
    		iCountedYou[randomIndex] = true;
    		
    	}
    	else{
    		cdapPersonArray[cdapPersonIndex] = persons[firstWorkerIndex];
    	}
    	
    	// second worker
    	cdapPersonIndex = 2;
    	if(secondWorkerIndex==-99){
    		
            int randomIndex = (int)( hhRandom.nextDouble() * hhSize );
            randomCount++;
            while(iCountedYou[randomIndex] || randomIndex==0){
                randomIndex = (int)( hhRandom.nextDouble() * hhSize );
                randomCount++;
            }
    		
    		cdapPersonArray[cdapPersonIndex] = persons[randomIndex];
    		iCountedYou[randomIndex] = true;
    		
    	}
    	else{
    		cdapPersonArray[cdapPersonIndex] = persons[secondWorkerIndex];
    	}
    	
    	// youngest child
    	cdapPersonIndex = 3;
    	if(youngestChildIndex==-99){
    		
            int randomIndex = (int)( hhRandom.nextDouble() * hhSize );
            randomCount++;
    		while(iCountedYou[randomIndex] || randomIndex==0){
                randomIndex = (int)( hhRandom.nextDouble() * hhSize );
                randomCount++;
            }
    		
    		cdapPersonArray[cdapPersonIndex] = persons[randomIndex];
    		iCountedYou[randomIndex] = true;
    		
    	}
    	else{
    		cdapPersonArray[cdapPersonIndex] = persons[youngestChildIndex];
    	}
    	
    	// second youngest child
    	cdapPersonIndex = 4;
    	if(secondYoungestChildIndex==-99){
    		
            int randomIndex = (int)( hhRandom.nextDouble() * hhSize );
            randomCount++;
    		while(iCountedYou[randomIndex] || randomIndex==0){
                randomIndex = (int)( hhRandom.nextDouble() * hhSize );
                randomCount++;
            }
    		
    		cdapPersonArray[cdapPersonIndex] = persons[randomIndex];
    		iCountedYou[randomIndex] = true;
    		
    	}
    	else{
    		cdapPersonArray[cdapPersonIndex] = persons[secondYoungestChildIndex];
    	}
    	
    	// third youngest child
    	cdapPersonIndex = 5;
    	if(thirdYoungestChildIndex==-99){
    		
    		int randomIndex = (int)( hhRandom.nextDouble() * hhSize );
            randomCount++;
    		while(iCountedYou[randomIndex] || randomIndex==0){
                randomIndex = (int)( hhRandom.nextDouble() * hhSize );
                randomCount++;
            }
    		
    		cdapPersonArray[cdapPersonIndex] = persons[randomIndex];
    		iCountedYou[randomIndex] = true;
    		
    	}
    	else{
    		cdapPersonArray[cdapPersonIndex] = persons[thirdYoungestChildIndex];
    	}
    	
    	// fill spots outside the top 5
    	cdapPersonIndex = 6;
    	for(int i=1;i<persons.length;++i){
    		
    		if(iCountedYou[i]) continue;
    		
    		cdapPersonArray[cdapPersonIndex] = persons[i];
    		cdapPersonIndex++;
    	}


        household.setHhRandomCount( randomCount );

    }
    
	

    protected Person getCdapPerson(int persNum){
    	if ( persNum < 1 || persNum > cdapPersonArray.length - 1  ) {
            logger.fatal( String.format("persNum value = %d is out of range for hhSize = %d", persNum, cdapPersonArray.length - 1) );
            throw new RuntimeException();
        }

        return cdapPersonArray[persNum];
    }

    /**
     * Method returns an array of persons not modeled by the CDAP model (i.e. persons 6 to X, when
     * ordered by the reOrderPersonsForCdap method
     * @param personsModeledByCdap
     * @return
     */
    public Person[] getPersonsNotModeledByCdap(int personsModeledByCdap){

    	// create a 1-based person array to be consistent
    	Person[] personArray = new Person[cdapPersonArray.length - personsModeledByCdap];

    	for(int i=1;i<personArray.length;++i){
    		personArray[i] = cdapPersonArray[personsModeledByCdap+i];
    	}

    	return personArray;

    }

    /**
     * Returns true if this CDAP person number (meaning the numbering of persons for the purposes
     * of the CDAP model) is a preschool child; false if not.
     * @param cdapPersonNumber
     * @return
     */
    public boolean isThisCdapPersonPreschoolChild(int cdapPersonNumber){

    	if(cdapPersonArray[cdapPersonNumber].getPersonIsPreschoolChild()==1) return true;
    	return false;
    }

    /**
     * Returns true if this CDAP person number (meaning the number of persons for the purposes
     * of the CDAP model) is an adult; false if not.
     * @param cdapPersonNumber
     * @return
     */
    public boolean isThisCdapPersonAnAdult(int cdapPersonNumber){

    	if(cdapPersonArray[cdapPersonNumber].getPersonIsAdult()==1) return true;
    	return false;
    }



}
