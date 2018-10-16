package com.pb.models.ctramp.old;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Random;
import java.util.ResourceBundle;

import org.apache.log4j.Logger;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.common.calculator.IndexValues;
import com.pb.models.ctramp.CoordinatedDailyActivityPatternModel;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.IndividualMandatoryTourFrequencyDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;

/**
 * Implements an invidual mandatory tour frequency model, which selects the number of work, school,
 * or work and school tours for each person who selects a mandatory activity. There are essentially
 * seven separate models, one for each person type (full-time worker, part-time worker, university student,
 * non working adults, retired, driving students, and non-driving students), except pre-school students. 
 * The choices are one work tour, two work tours, one school tour, two school tours, and one
 * work and school tour. Availability arrays are defined for each person type.  
 * 
 * The UEC for the model has two additional matrix calcuation tabs, which computes the one-way walk distance
 * and the round-trip auto time to work and/or school for the model. This allows us to compute the work and/or
 * school time, by setting the DMU destination index, just using the UEC. 
 * 
 * @author D. Ory
 *
 */
public class IndividualMandatoryTourFrequencyModel {
	
	public static Logger logger = Logger.getLogger(IndividualMandatoryTourFrequencyModel.class);
	
	public static final int UEC_DATA_PAGE     = 0;
	public static final int UEC_MODEL_PAGE    = 1;

	public static final String MANDATORY_ACTIVITY = CoordinatedDailyActivityPatternModel.MANDATORY_PATTERN;
	

	// model results
	public static final int CHOICE_ONE_WORK        = 1;
	public static final int CHOICE_TWO_WORK        = 2;
	public static final int CHOICE_ONE_SCHOOL      = 3;
	public static final int CHOICE_TWO_SCHOOL      = 4;
	public static final int CHOICE_WORK_AND_SCHOOL = 5;
	
	public static final String[] choiceResults = {"1 Work", "2 Work", "1 School", "2 School", "Wrk & Schl"};



    protected int[] areaType;
    protected int[] zoneTableRow;

    protected HashMap<String,int[]> countByPersonType;
	
	protected IndividualMandatoryTourFrequencyDMU dmuObject;
	protected ChoiceModelApplication choiceModelApplication;

    protected ModelStructure modelStructure;


    /**
	 * Constructor establishes the ChoiceModelApplication, which applies the logit model via the UEC
	 * spreadsheet, and it also establishes the UECs used to compute the one-way walk distance to work
	 * and/or school and the round-trip auto time to work and/or school. The model must be the first UEC
	 * tab, the one-way distance calculations must be the second UEC tab, round-trip time must be 
	 * the third UEC tab.
     * @param dmuObject is the UEC dmu object for this choice model
	 * @param uecFileName is the UEC control file name
	 * @param resourceBundle is the application ResourceBundle, from which a properties file HashMap will be created for the UEC
     * @param tazDataManager is the object used to interact with the zonal data table
     * @param modelStructure is the ModelStructure object that defines segmentation and other model structure relate atributes
	 */
	public IndividualMandatoryTourFrequencyModel( IndividualMandatoryTourFrequencyDMU dmuObject, String uecFileName, ResourceBundle resourceBundle, TazDataIf tazDataManager, ModelStructure modelStructure){

        this.modelStructure = modelStructure;
        this.dmuObject = dmuObject;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        // set up the model
		choiceModelApplication = new ChoiceModelApplication(uecFileName, UEC_MODEL_PAGE, UEC_DATA_PAGE, 
				ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle),dmuObject.getClass());
		
	}
	
	/**
	 * Applies the model for the array of households that are stored in the HouseholdDataManager.
	 * The results are summarized by person type.
     *
     * @param householdDataManager is the object containg the Household objects for which this model is to be applied.
	 */
	public void applyModel(HouseholdDataManagerIf householdDataManager){

        int choice = -1;
        String personTypeString = "Missing";

        // prepare the results array
		countByPersonType = new HashMap<String,int[]>();
		
    	// get the array of households
    	Household[] householdArray = householdDataManager.getHhArray();
    	
    	// loop the households (1-based array)
    	for(int i=1;i<householdArray.length;++i){
    		
    		Household household = householdArray[i];

            // get this household's person array
    		Person[] personArray = household.getPersons();
    		
    		// set the household id, origin taz, hh taz, and debugFlag=false in the dmu
            dmuObject.setHousehold(household);

            // set the area type for the home taz
            int tableRow = zoneTableRow[household.getHhTaz()];
            dmuObject.setHomeTazAreaType( areaType[tableRow-1] );

            // loop through the person array (1-based)
    		for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];
    			
    			// determine if this person has a mandatory daily activity
    			String activity = person.getCdapActivity();

                // count the results by person type
                personTypeString = "Missing";


                try {

                    // only apply the model for those with mandatory activities and not preschool children
                    if(activity.equalsIgnoreCase(MANDATORY_ACTIVITY) && person.getPersonIsPreschoolChild()==0){

                        // set the person
                        dmuObject.setPerson(person);

                        // write debug header
                        if(household.getDebugChoiceModels()){
                            logger.info(" ");
                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info("IMTF Model: Debug Statement for Household ID: "+household.getHhId()+
                                        ", Person ID: "+person.getPersonId());
                        }


                        // set the availability array for the tour frequency model
                        int numberOfAlternatives = choiceModelApplication.getNumberOfAlternatives();
                        boolean[] availabilityArray = new boolean[numberOfAlternatives+1];
                        Arrays.fill( availabilityArray, true );


                        String workPurpose = modelStructure.WORK_PURPOSE_NAME;
                        String schoolPurpose = "";


                        //TODO: do we need these?  Are they already accounted for in the UEC expressions?
                        // the availability is based on person type
                        if(person.getPersonTypeIsFullTimeWorker()==1){
                            personTypeString = Person.PERSON_TYPE_FULL_TIME_WORKER_NAME;
                        }
                        else if(person.getPersonTypeIsPartTimeWorker()==1){
                            personTypeString  = Person.PERSON_TYPE_PART_TIME_WORKER_NAME;
                        }
                        else if(person.getPersonIsUniversityStudent()==1){
                            personTypeString  = Person.PERSON_TYPE_UNIVERSITY_STUDENT_NAME;
                            schoolPurpose = modelStructure.UNIVERSITY_PURPOSE_NAME;
                        }
                        else if(person.getPersonIsNonWorkingAdultUnder65()==1){
                            personTypeString  = Person.PERSON_TYPE_NON_WORKER_NAME;
                            workPurpose = "";
                        }
                        else if(person.getPersonIsNonWorkingAdultOver65()==1){
                            personTypeString  = Person.PERSON_TYPE_RETIRED_NAME;
                            workPurpose = "";
                            schoolPurpose = "";
                        }
                        else if(person.getPersonIsStudentDriving()==1){
                            personTypeString  = Person.PERSON_TYPE_STUDENT_DRIVING_NAME;
                            schoolPurpose = modelStructure.SCHOOL_PURPOSE_NAME;
                        }
                        else if(person.getPersonIsStudentNonDriving()==1){
                            personTypeString  = Person.PERSON_TYPE_STUDENT_NON_DRIVING_NAME;
                            schoolPurpose = modelStructure.SCHOOL_PURPOSE_NAME;
                            workPurpose = "";
                        }



                        // create the sample array
                        int[] sampleArray = new int[availabilityArray.length];
                        Arrays.fill(sampleArray, 1);

                        // compute the utilities
                        IndexValues index = dmuObject.getIndexValues();
                        index.setDebug(false);


                        choiceModelApplication.computeUtilities(dmuObject, index,
                                availabilityArray, sampleArray);

                        // get the random number from the household
                        Random random = household.getHhRandom();
                        int randomCount = household.getHhRandomCount();
                        double randomNumber = random.nextDouble();


                        // if the choice model has at least one available alternative, make choice.
                        if ( choiceModelApplication.getAvailabilityCount() > 0 )
                            choice = choiceModelApplication.getChoiceResult( randomNumber );
                        else {
                            logger.error ( String.format( "Exception caught for i=%d, j=%d, activity=%s, HHID=%d, no available alternatives to choose from in choiceModelApplication.", i, j, activity, person.getHouseholdObject().getHhId() ) );
                            throw new RuntimeException();
                        }


                        // debug output
                        if(household.getDebugChoiceModels()){

                            double[] utilities     = choiceModelApplication.getUtilities();
                            double[] probabilities = choiceModelApplication.getProbabilities();

                            logger.info("Person type: "+personTypeString);
                            logger.info("Alternative                 Utility    Probability");
                            logger.info("-------------------- -------------- --------------");

                            for(int k=0;k<choiceResults.length;++k){
                                logger.info(String.format("%-20s%15.4f%15.4f",choiceResults[k],utilities[k],probabilities[k]));
                            }

                            logger.info(" ");
                            logger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", choiceResults[choice-1], randomNumber, randomCount ) );

                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info(" ");
                        }


                        person.setImtfChoice ( choice );

                        // set the person choices
                        if(choice==CHOICE_ONE_WORK){
                            person.createWorkTours( 1, 0, workPurpose, modelStructure );
                        }
                        else if(choice==CHOICE_TWO_WORK){
                            person.createWorkTours( 2, 0, workPurpose, modelStructure );
                        }
                        else if(choice==CHOICE_ONE_SCHOOL){
                            person.createSchoolTours( 1, 0, schoolPurpose, modelStructure );
                        }
                        else if(choice==CHOICE_TWO_SCHOOL){
                            person.createSchoolTours( 2, 0, schoolPurpose, modelStructure );
                        }
                        else if(choice==CHOICE_WORK_AND_SCHOOL){
                            person.createWorkTours( 1, 0, workPurpose, modelStructure );
                            person.createSchoolTours( 1, 1, schoolPurpose, modelStructure );
                        }

                    } // mandatory activity if
                    else if(activity.equalsIgnoreCase(MANDATORY_ACTIVITY) && person.getPersonIsPreschoolChild() == 1){
                        // pre-school child with mandatory activity type is assigned choice = 3 (1 school tour).
                        choice = 3;

                        person.setImtfChoice ( choice );

                        personTypeString = Person.PERSON_TYPE_PRE_SCHOOL_CHILD_NAME;
                        person.createSchoolTours( 1, 0, modelStructure.SCHOOL_PURPOSE_NAME, modelStructure );
                    }


                    // count the results by person type
                    if ( ! personTypeString.equalsIgnoreCase("Missing") ) {

                        // count the results
                        if(countByPersonType.containsKey(personTypeString)){

                            int[] counterArray = countByPersonType.get(personTypeString);
                            counterArray[choice-1]++;
                            countByPersonType.put(personTypeString, counterArray);

                        }
                        else{

                            int[] counterArray = new int[choiceResults.length];
                            counterArray[choice-1]++;
                            countByPersonType.put(personTypeString, counterArray);

                        } // is personType in map if

                    }

                }
                catch ( Exception e ) {                     
                    logger.error ( String.format( "Exception caught for i=%d, j=%d, activity=%s, HHID=%d", i, j, activity, person.getHouseholdObject().getHhId() ) );
                    throw new RuntimeException();
                }


            } // j (person loop)
    	} // i (household loop)

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setImtfRandomCount();

    }
	
	/**
	 * Logs the results of the model.
	 *
	 */
	public void logResults(){
		
		logger.info(" ");
    	logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
    	logger.info("Individual Mandatory Tour Frequency Model Results");
    	
    	// count of model results
    	logger.info(" ");
    	String firstHeader  = "Person type                   ";
    	String secondHeader = "-----------------------------  ";
    	
		for(int i=0;i<choiceResults.length;++i){
			firstHeader  += String.format("%12s",choiceResults[i]);
			secondHeader += "----------- ";
		}
    	
        firstHeader  += String.format("%12s","Total");
        secondHeader += "-----------";

        logger.info(firstHeader);
		logger.info(secondHeader);

        int[] columnTotals = new int[choiceResults.length];


        int lineTotal = 0;
        for(int i=0;i<Person.personTypeNameArray.length;++i){
			String personTypeString = Person.personTypeNameArray[i];
			String stringToLog  = String.format("%-30s", personTypeString);

			if(countByPersonType.containsKey(personTypeString)){
				
                lineTotal = 0;
				int[] countArray = countByPersonType.get(personTypeString);
				for(int j=0;j<choiceResults.length;++j){
					stringToLog += String.format("%12d",countArray[j]);
                    columnTotals[j] += countArray[j];
                    lineTotal += countArray[j];
                } // j
			} // if key
			else{
				
				// log zeros
                lineTotal = 0;
				for(int j=0;j<choiceResults.length;++j){
					stringToLog += String.format("%12d",0);
				}
			}

            stringToLog += String.format("%12d",lineTotal);

            logger.info(stringToLog);
			
		} // i
		
        String stringToLog  = String.format("%-30s", "Total");
        lineTotal = 0;
        for(int j=0;j<choiceResults.length;++j){
            stringToLog += String.format("%12d",columnTotals[j]);
            lineTotal += columnTotals[j];
        } // j

        logger.info(secondHeader);
        stringToLog += String.format("%12d",lineTotal);
        logger.info(stringToLog);
        logger.info(" ");
    	logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");

	}

}
