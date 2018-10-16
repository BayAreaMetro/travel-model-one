package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Definitions;
import com.pb.models.ctramp.Household;
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
public class HouseholdIndividualMandatoryTourFrequencyModel implements Serializable {
	
    private transient Logger logger = Logger.getLogger(HouseholdIndividualMandatoryTourFrequencyModel.class);
    private transient Logger tourFreq = Logger.getLogger("tourFreq");
		
    private static final int UEC_DATA_PAGE     = 0;
    private static final int UEC_MODEL_PAGE    = 1;

    private static final String PROPERTIES_UEC_INDIV_MANDATORY_TOUR_FREQ = "UecFile.IndividualMandatoryTourFrequency";

    private static final String MANDATORY_ACTIVITY = Definitions.MANDATORY_PATTERN;
	

	// model results
    private static final int CHOICE_ONE_WORK        = 1;
    private static final int CHOICE_TWO_WORK        = 2;
    private static final int CHOICE_ONE_SCHOOL      = 3;
    private static final int CHOICE_TWO_SCHOOL      = 4;
    public static final int CHOICE_WORK_AND_SCHOOL = 5;
	
    private static final String[] choiceResults = {"1 Work", "2 Work", "1 School", "2 School", "Wrk & Schl"};



    private int[] areaType;
    private int[] zoneTableRow;

    //protected HashMap<String,int[]> countByPersonType;
	
    private IndividualMandatoryTourFrequencyDMU imtfDmuObject;
    private ChoiceModelApplication choiceModelApplication;

    private transient Logger choiceModelLogger = Logger.getLogger("cmLogger");
    private String personChoiceModelDescription;
    private String personDecisionMakerDescription;
    private String personChoiceModelLoggingHeader;
    private String personChoiceModelSeparator;
    
    private ModelStructure modelStructure;


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
	public HouseholdIndividualMandatoryTourFrequencyModel( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) {

	    setupHouseholdIndividualMandatoryTourFrequencyModel ( propertyMap, tazDataManager, modelStructure, dmuFactory );

	}
	
	
	private void setupHouseholdIndividualMandatoryTourFrequencyModel ( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) {
	    
        logger.info( "setting up IMTF choice model." );
        
        this.modelStructure = modelStructure;

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();
        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // locate the individual mandatory tour frequency choice model UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String imtfUecFile = propertyMap.get( PROPERTIES_UEC_INDIV_MANDATORY_TOUR_FREQ );
        imtfUecFile = projectDirectory + imtfUecFile;

        // get the dmu object from the factory
        imtfDmuObject = dmuFactory.getIndividualMandatoryTourFrequencyDMU();
        
        // set up the model
        choiceModelApplication = new ChoiceModelApplication( imtfUecFile, UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)imtfDmuObject );
        
        // prepare the results array
        //countByPersonType = new HashMap<String,int[]>();
        
	}
	
	
	/**
	 * Applies the model for the array of households that are stored in the HouseholdDataManager.
	 * The results are summarized by person type.
     *
     * @param householdDataManager is the object containg the Household objects for which this model is to be applied.
	 */
	public void applyModel( Household household ){

        Logger modelLogger = tourFreq;
        if ( household.getDebugChoiceModels() )
            household.logHouseholdObject( "Pre Individual Mandatory Tour Frequency Choice HHID=" + household.getHhId() + " Object", modelLogger );
        
	    
        int choice = -1;


        // get this household's person array
		Person[] personArray = household.getPersons();
		
		// set the household id, origin taz, hh taz, and debugFlag=false in the dmu
		imtfDmuObject.setHousehold(household);

        // set the area type for the home taz
        int tableRow = zoneTableRow[household.getHhTaz()];
        imtfDmuObject.setHomeTazAreaType( areaType[tableRow-1] );

        // loop through the person array (1-based)
		for(int j=1;j<personArray.length;++j){
		    
		    Person person = personArray[j];
			
            if ( household.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
                household.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
            

			String activity = person.getCdapActivity();

            try {

                // only apply the model for those with mandatory activities and not preschool children
                if( person.getPersonIsPreschoolChild() == 0 && activity.equalsIgnoreCase(MANDATORY_ACTIVITY) ){

                    // set the person
                    imtfDmuObject.setPerson(person);

                    // write debug header
                    String separator = "";
                    String choiceModelDescription = "" ;
                    String decisionMakerLabel = "";
                    String loggingHeader = "";
                    if( household.getDebugChoiceModels() ) {

                        choiceModelDescription = String.format ( "Individual Mandatory Tour Frequency Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s.", household.getHhId(), person.getPersonNum(), person.getPersonType() );
                        
                        choiceModelApplication.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        String loggerString = "Individual Mandatory Tour Frequency Choice Model: Debug Statement for Household ID: " + household.getHhId() + ", Person Num: " + person.getPersonNum() + ", Person Type: " + person.getPersonType() + ".";
                        for (int k=0; k < loggerString.length(); k++)
                            separator += "+";
                        modelLogger.info( loggerString );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                        loggingHeader = String.format( "%s   %s", choiceModelDescription, decisionMakerLabel );
                        
                        setupPersonChoiceCalculationLogging( modelLogger, choiceModelDescription, decisionMakerLabel, loggingHeader, separator );                        
                    }
                    
                    
                    String workPurpose = modelStructure.getWorkPurposeFromIncomeInDollars( household.getIncomeInDollars() );
                    String schoolPurpose = "";


                    //TODO: do we need these?  Are they already accounted for in the UEC expressions?
                    // the availability is based on person type
                    // guojy: We should not have these purpose assignment here. 
                    //		  For ARC, the assignment is already done in ArcHouseholdDataManager and should not be over-written
                    //		  TODO: Check if needed for MTC. If not, remove.
                    if(person.getPersonIsUniversityStudent()==1){
                        schoolPurpose = ModelStructure.UNIVERSITY_PURPOSE_NAME;
                    }
                    else if(person.getPersonIsNonWorkingAdultUnder65()==1){
                        workPurpose = "";
                    }
                    else if(person.getPersonIsNonWorkingAdultOver65()==1){
                        workPurpose = "";
                        schoolPurpose = "";
                    }
                    else if(person.getPersonIsStudentDriving()==1){
                        // get the school purpose name for a driving age person
                        schoolPurpose = modelStructure.getSchoolPurpose( 17 );
                    }
                    else if(person.getPersonIsStudentNonDriving()==1){
                        // get the school purpose name for a non-driving age person
                        schoolPurpose = modelStructure.getSchoolPurpose( 10 );
                        workPurpose = "";
                    }



                    // compute the utilities
                    IndexValues index = imtfDmuObject.getIndexValues();
                    choiceModelApplication.computeUtilities( imtfDmuObject, index  );

                    
                    // get the random number from the household
                    Random random = household.getHhRandom();
                    double rn = random.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    choice = -1;
                    if ( choiceModelApplication.getAvailabilityCount() > 0 )
                        choice = choiceModelApplication.getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught for j=%d, activity=%s, HHID=%d, no available alternatives to choose from in choiceModelApplication.", j, activity, household.getHhId() ) );
                        //throw new RuntimeException();
                    }

                    
                    if ( household.getDebugChoiceModels() || choice < 0  ){
                        logPersonChoiceCalculations( household, person, choice, rn );
                    }

                    
                    if ( choice < 0 ) {
                        logger.error ( String.format( "Exception caught for j=%d, activity=%s, HHID=%d, no available alternatives to choose from in choiceModelApplication.", j, activity, household.getHhId() ) );
                        throw new RuntimeException();
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
                        person.createSchoolTours( 1, 0, schoolPurpose, modelStructure );
                    }

                } // mandatory activity if
                else if(activity.equalsIgnoreCase(MANDATORY_ACTIVITY) && person.getPersonIsPreschoolChild() == 1){
                    // pre-school child with mandatory activity type is assigned choice = 3 (1 school tour).
                    choice = 3;

                    person.setImtfChoice ( choice );

                    // get the school purpose name for a non-driving age person to use for preschool tour purpose
                    // guojy: We should not have school purpose assignment here. The arbitrary use of '10' is also not good practice.
                    //		  For ARC, the assignment is already done in ArcHouseholdDataManager and should not be over-written
                    //		  TODO: Check if needed for MTC. If not, remove.
                    String schoolPurpose = modelStructure.getSchoolPurpose( 10 );
                    person.createSchoolTours( 1, 0, schoolPurpose, modelStructure );
                }


            }
            catch ( Exception e ) {                     
                logger.error ( String.format( "Exception caught for j=%d, activity=%s, HHID=%d", j, activity, household.getHhId() ) );
                throw new RuntimeException();
            }


        } // j (person loop)

		
        household.setImtfRandomCount( household.getHhRandomCount() );
		
    }


	private void setupPersonChoiceCalculationLogging( Logger aLogger, String choiceModelDescription, String decisionMakerDescription, String loggingHeader, String aSeparator ){
	    choiceModelLogger = aLogger;
	    personChoiceModelDescription = choiceModelDescription;
	    personDecisionMakerDescription = decisionMakerDescription;
	    personChoiceModelLoggingHeader = loggingHeader;
	    personChoiceModelSeparator = aSeparator;
	}
	
	private void logPersonChoiceCalculations( Household household, Person person, int chosenAlternative, double rn ) {
	    
	    int randomCount = household.getHhRandomCount();
	    
        double[] utilities     = choiceModelApplication.getUtilities();
        double[] probabilities = choiceModelApplication.getProbabilities();

        int personNum = person.getPersonNum();
        String personTypeString = person.getPersonType();
        choiceModelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
        choiceModelLogger.info("Alternative                 Utility       Probability           CumProb");
        choiceModelLogger.info("------------------   --------------    --------------    --------------");

        double cumProb = 0.0;
        for(int k=0;k<choiceResults.length;++k){
            cumProb += probabilities[k];
            String altString = String.format( "%-3d %10s", k+1, choiceResults[k] );
            choiceModelLogger.info(String.format("%-15s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
        }

        choiceModelLogger.info(" ");
        String altString = String.format( "%-3d %10s", chosenAlternative, ( chosenAlternative < 0 ? "no choice!" : choiceResults[chosenAlternative-1] ) );
        choiceModelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

        choiceModelLogger.info( personChoiceModelSeparator );
        choiceModelLogger.info("");
        choiceModelLogger.info("");
        

        // write choice model alternative info to debug log file
        choiceModelApplication.logAlternativesInfo ( personChoiceModelDescription, personDecisionMakerDescription );
        choiceModelApplication.logSelectionInfo ( personChoiceModelDescription, personDecisionMakerDescription, rn, chosenAlternative );

        // write UEC calculation results to separate model specific log file
        choiceModelApplication.logUECResults( choiceModelLogger, personChoiceModelLoggingHeader );
            
	}
	
	/**
	 * Logs the results of the model.
	 *
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
     */

}
