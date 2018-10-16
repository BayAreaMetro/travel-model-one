package com.pb.models.ctramp.jppf;

import java.util.*;
import java.io.File;
import java.io.IOException;
import java.io.Serializable;

import org.apache.log4j.Logger;

import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Definitions;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.IndividualNonMandatoryTourFrequencyDMU;

import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.newmodel.ChoiceModelApplication;

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
public class HouseholdIndividualNonMandatoryTourFrequencyModel implements Serializable {

	private transient Logger logger = Logger.getLogger(HouseholdIndividualNonMandatoryTourFrequencyModel.class);
    private transient Logger tourFreq = Logger.getLogger("tourFreq");

    
	private static final int UEC_DATA_PAGE     = 0;
    private static final int FT_WORKER_UEC_MODEL_PAGE = 1;
    private static final int PT_WORKER_UEC_MODEL_PAGE = 2;
    private static final int UNIVERSITY_UEC_MODEL_PAGE = 3;
    private static final int NONWORKER_UEC_MODEL_PAGE = 4;
    private static final int RETIRED_UEC_MODEL_PAGE = 5;
    private static final int DRIVING_STUDENT_UEC_MODEL_PAGE = 6;
    private static final int NON_DRIVING_STUDENT_UEC_MODEL_PAGE = 7;
    private static final int PRESCHOOL_UEC_MODEL_PAGE    = 8;
    private static int NUM_PERSON_TYPE_MODEL_PAGES = 8;

    private static final String HOME_ACTIVITY = Definitions.HOME_PATTERN;

    private static final String PROPERTIES_UEC_INDIV_NON_MANDATORY_TOUR_FREQ = "UecFile.IndividualNonMandatoryTourFrequency";

    private static final String PROPERTIES_TOUR_FREQUENCY_EXTENSION_PROBABILITIES_FILE = "IndividualNonMandatoryTour.FrequencyExtension.ProbabilityFile";



    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;

    //private HashMap<String,int[]> countByPersonType;
    private HashMap<Integer,String> purposeIndexToNameMap;

    private IndividualNonMandatoryTourFrequencyDMU dmuObject;
	private ChoiceModelApplication[] choiceModelApplication;
    private TableDataSet alternativesTable;


    private Map<Integer,float[]> tourFrequencyIncreaseProbabilityMap;
    private int[] maxTourFrequencyChoiceList;

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

    
    public HouseholdIndividualNonMandatoryTourFrequencyModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ){

        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;

        setUpModels( propertyMap, dmuFactory );        

    }

    
    
    public void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ){

        logger.info( String.format( "setting up %s tour frequency choice model.", ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY ) );
        
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        String uecFileName = propertyMap.get( PROPERTIES_UEC_INDIV_NON_MANDATORY_TOUR_FREQ );
        uecFileName = projectDirectory + uecFileName;

        
        dmuObject = dmuFactory.getIndividualNonMandatoryTourFrequencyDMU();
    
        // set up the model
        choiceModelApplication = new ChoiceModelApplication[NUM_PERSON_TYPE_MODEL_PAGES+1];     // one choice model for each person type that has model specified; Ones indexing for personType.
        choiceModelApplication[1] = new ChoiceModelApplication( uecFileName, FT_WORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[2] = new ChoiceModelApplication( uecFileName, PT_WORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[3] = new ChoiceModelApplication( uecFileName, UNIVERSITY_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[4] = new ChoiceModelApplication( uecFileName, NONWORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[5] = new ChoiceModelApplication( uecFileName, RETIRED_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[6] = new ChoiceModelApplication( uecFileName, DRIVING_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[7] = new ChoiceModelApplication( uecFileName, NON_DRIVING_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        choiceModelApplication[8] = new ChoiceModelApplication( uecFileName, PRESCHOOL_UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );




        // the alternatives are the same for each person type; use the first choiceModelApplication to get its uec and from it, get the TableDataSet of alternatives
        // to use to determine which tour purposes should be generated for the chose alternative.
        alternativesTable = choiceModelApplication[1].getUEC().getAlternativeData();

        // check the field names in the alternatives table; make sure the their order is as expected.
        String[] fieldNames = alternativesTable.getColumnLabels();

        purposeIndexToNameMap = new HashMap<Integer,String>();
        purposeIndexToNameMap.put( 1, modelStructure.ESCORT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 2, modelStructure.SHOPPING_PURPOSE_NAME );
        purposeIndexToNameMap.put( 3, modelStructure.OTH_MAINT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 4, modelStructure.OTH_DISCR_PURPOSE_NAME );
        purposeIndexToNameMap.put( 5, modelStructure.EAT_OUT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 6, modelStructure.SOCIAL_PURPOSE_NAME );

        if ( ! fieldNames[0].equalsIgnoreCase("a") && ! fieldNames[0].equalsIgnoreCase("alt") ) {
            logger.error ( "error while checking order of fields in IndividualNonMandatoryTourFrequencyModel alternatives file.");
            logger.error ( String.format( "first field expected to be 'a' or 'alt' (case insensitive), but %s was found instead.", fieldNames[0] ) );
            throw new RuntimeException();
        }
        else {

            for ( int i : purposeIndexToNameMap.keySet() ) {
                String name = purposeIndexToNameMap.get(i).trim();
                if ( ! fieldNames[i].equalsIgnoreCase( name ) ) {
                    logger.error ( "error while checking order of fields in IndividualNonMandatoryTourFrequencyModel alternatives file.");
                    logger.error ( String.format( "field %d expected to be '%s' (case insensitive), but %s was found instead.", i, name, fieldNames[i] ) );
                    throw new RuntimeException();
                }
            }
        }

        //load data used for tour frequency extension model
        loadIndividualNonMandatoryIncreaseModelData( projectDirectory + propertyMap.get(PROPERTIES_TOUR_FREQUENCY_EXTENSION_PROBABILITIES_FILE));

    }
    
    
    
	/**
	 * Applies the model for the array of households that are stored in the HouseholdDataManager.
	 * The results are summarized by person type.
     *
     * @param householdDataManager is the object containg the Household objects for which this model is to be applied.
	 */
	public void applyModel( Household household ){

        int modelIndex = -1;
        int choice = -1;
        String personTypeString = "Missing";

        Logger modelLogger = tourFreq;
        if ( household.getDebugChoiceModels() )
            household.logHouseholdObject( "Pre Individual Non-Mandatory Tour Frequency Choice HHID=" + household.getHhId() + " Object", modelLogger );
        

        //this will be an array with values 1 -> tours.length being the number of non-mandatory tours in each category
        // this keeps it consistent with the way the alternatives are held in the alternatives file/arrays
        float[] tours = null;


        // prepare the results array
		//countByPersonType = new HashMap<String,int[]>();
        //int numPurposes = alternativesTable.getColumnLabels().length;


        
		// get this household's person array
		Person[] personArray = household.getPersons();

		// set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        dmuObject.setHouseholdObject(household);

        // set homeTazIsUrban to 1 if area type for the home taz is urban
        int urban = 0;
        if ( tazDataManager.getZoneIsUrban( household.getHhTaz() ) == 1 )
            urban = 1;
        dmuObject.setHomeTazIsUrban( urban );

        
        String separator = "";
        String choiceModelDescription = "" ;
        String decisionMakerLabel = "";
        String loggingHeader = "";
        
        
        // loop through the person array (1-based)
		for(int j=1;j<personArray.length;++j){

            Person person = personArray[j];

			String activity = person.getCdapActivity();


            try {

                // only apply the model if person does not have H daily activity pattern
                if( !activity.equalsIgnoreCase(HOME_ACTIVITY) ) {

                    // set the person
                    dmuObject.setPersonObject(person);

                    
                    if ( household.getDebugChoiceModels() ) {
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
                        household.logPersonObject( decisionMakerLabel, modelLogger, person );
                    }
                    



                    // set the availability array for the tour frequency model
                    // same number of alternatives for each person type, so use person type 1 to get num alts.
                    int numberOfAlternatives = choiceModelApplication[1].getNumberOfAlternatives();
                    boolean[] availabilityArray = new boolean[numberOfAlternatives+1];
                    Arrays.fill(availabilityArray,true);



                    if(person.getPersonTypeIsFullTimeWorker()==1){
                        personTypeString = Person.PERSON_TYPE_FULL_TIME_WORKER_NAME;
                        modelIndex = FT_WORKER_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonTypeIsPartTimeWorker()==1){
                        personTypeString  = Person.PERSON_TYPE_PART_TIME_WORKER_NAME;
                        modelIndex = PT_WORKER_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsUniversityStudent()==1){
                        personTypeString  = Person.PERSON_TYPE_UNIVERSITY_STUDENT_NAME;
                        modelIndex = UNIVERSITY_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsNonWorkingAdultUnder65()==1){
                        personTypeString  = Person.PERSON_TYPE_NON_WORKER_NAME;
                        modelIndex = NONWORKER_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsNonWorkingAdultOver65()==1){
                        personTypeString  = Person.PERSON_TYPE_RETIRED_NAME;
                        modelIndex = RETIRED_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsStudentDriving()==1){
                        personTypeString  = Person.PERSON_TYPE_STUDENT_DRIVING_NAME;
                        modelIndex = DRIVING_STUDENT_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsStudentNonDriving()==1){
                        personTypeString  = Person.PERSON_TYPE_STUDENT_NON_DRIVING_NAME;
                        modelIndex = NON_DRIVING_STUDENT_UEC_MODEL_PAGE;
                    }
                    else if(person.getPersonIsPreschoolChild()==1){
                        personTypeString  = Person.PERSON_TYPE_PRE_SCHOOL_CHILD_NAME;
                        modelIndex = PRESCHOOL_UEC_MODEL_PAGE;
                    }


                    person.computeIdapResidualWindows();
                    

                    // create the sample array
                    int[] sampleArray = new int[availabilityArray.length];
                    Arrays.fill(sampleArray, 1);

                    // compute the utilities
                    dmuObject.setDmuIndexValues( household.getHhId(), household.getHhTaz(), household.getHhTaz(), -1 );


                    if ( household.getDebugChoiceModels() ) {
                    
                        // write debug header
                        choiceModelDescription = String.format ( "Individual Non-Mandatory Tour Frequency Orignal Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
                        choiceModelApplication[modelIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        String loggerString = choiceModelDescription + " for " + decisionMakerLabel + ".";
                        for (int k=0; k < loggerString.length(); k++)
                            separator += "+";
                        modelLogger.info( loggerString );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );

                    }
                    

                    choiceModelApplication[modelIndex].computeUtilities(dmuObject, dmuObject.getDmuIndexValues(), availabilityArray, sampleArray);

                    // get the random number from the household
                    Random random = household.getHhRandom();
                    int randomCount = household.getHhRandomCount();
                    double rn = random.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    if ( choiceModelApplication[modelIndex].getAvailabilityCount() > 0 )
                        choice = choiceModelApplication[modelIndex].getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught for j=%d, activity=%s, HHID=%d, no Non-Mandatory Tour Frequency alternatives available to choose from in choiceModelApplication.", j, activity, person.getHouseholdObject().getHhId() ) );
                        throw new RuntimeException();
                    }

                    
                    
                    // create the non-mandatory tour objects for the choice made.
//                        createIndividualNonMandatoryTours ( person, choice );
                    tours = runIndividualNonMandatoryToursIncreaseModel(person,choice);
                    createIndividualNonMandatoryTours_new(person,tours);

                    
                    // debug output
                    if( household.getDebugChoiceModels() ){

                        String[] alternativeNames     = choiceModelApplication[modelIndex].getAlternativeNames();
                        double[] utilities     = choiceModelApplication[modelIndex].getUtilities();
                        double[] probabilities = choiceModelApplication[modelIndex].getProbabilities();

                        int personNum = person.getPersonNum();
                        modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
                        modelLogger.info("Alternative                                                                        Utility       Probability           CumProb");
                        modelLogger.info("---------------------------------------------                               --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for( int k=0; k < alternativeNames.length; k++ ){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d %-66s", k+1, getAlternativeNameFromChoice(k+1) );
                            modelLogger.info(String.format("%-72s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d %s", choice, getAlternativeNameFromChoice( choice ) );
                        modelLogger.info( String.format("Original Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        altString = String.format( "%-3d %s", choice, getAlternativeNameFromModifiedChoice( tours ) );
                        modelLogger.info( String.format("Revised Choice After Increase: %s", altString ) );
                        
                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");
                        

                        // write choice model alternative info to debug log file
                        choiceModelApplication[modelIndex].logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        choiceModelApplication[modelIndex].logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, choice );

                        loggingHeader = choiceModelDescription + " for " + decisionMakerLabel;
                        
                        // write UEC calculation results to separate model specific log file
                        choiceModelApplication[modelIndex].logUECResults( modelLogger, loggingHeader );
                        
                    }

                    person.setInmtfChoice ( choice );


                }



                /* count the results by person type
                if ( ! personTypeString.equalsIgnoreCase("Missing") ) {

                    //new way
                    // count the results
                    int[] counterArray = (countByPersonType.containsKey(personTypeString)) ?
                            countByPersonType.get(personTypeString) : new int[numPurposes];
                    for (int p=1; p < numPurposes; p++)
                        counterArray[p-1] += (int) tours[p];
                    countByPersonType.put(personTypeString, counterArray);

                }
                */

            }
            catch ( Exception e ) {
                logger.error ( String.format( "Exception caught for j=%d, activity=%s, HHID=%d", j, activity, household.getHhId() ) );
                throw new RuntimeException(e);
            }

        } // j (person loop)
	
		household.setInmtfRandomCount( household.getHhRandomCount() );

	}



    private String getAlternativeNameFromChoice ( int choice ) {
        
        // use the 1s based choice value as the table row number
        float[] rowValues = alternativesTable.getRowValues( choice );
        
        String altName = "";
        
        // rowValues is a 0s based indexed array, but the first field is the alternative number,
        // and subsequent fields indicate the number of tours to be generated for the purpose corresponding to the field.
        for ( int i=1; i < rowValues.length; i++ ) {
        
            int numTours = (int)rowValues[i];
            if ( numTours == 0 )
                continue;
        
            String purposeName = purposeIndexToNameMap.get(i);
            if ( altName.length() == 0 )
                altName = String.format(", %d %s", numTours, purposeName);
            else
                altName += String.format(", %d %s", numTours, purposeName);
        }

        if ( altName.length() == 0 )
            altName = "no tours";
        
        return altName;
    }
    
    private String getAlternativeNameFromModifiedChoice ( float[] rowValues ) {
        
        String altName = "";
        
        // rowValues is a 0s based indexed array, but the first field is the alternative number,
        // and subsequent fields indicate the nuimber of tours to be generated for the purpose corresponding to the field.
        for ( int i=1; i < rowValues.length; i++ ) {
        
            int numTours = (int)rowValues[i];
            if ( numTours == 0 )
                continue;
        
            String purposeName = purposeIndexToNameMap.get(i);
            if ( altName.length() == 0 )
                altName = String.format(", %d %s", numTours, purposeName);
            else
                altName += String.format(", %d %s", numTours, purposeName);
        }

        if ( altName.length() == 0 )
            altName = "no tours";
        
        return altName;
    }
    
	/**
	 * Logs the results of the model.
	 *
	public void logResults(){

		logger.info(" ");
    	logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
    	logger.info("Individual Non-Mandatory Tour Frequency Model Results");

    	// count of model results
    	logger.info(" ");
    	String firstHeader  = "Person type                   ";
    	String secondHeader = "-----------------------------  ";



        String[] purposeNames = alternativesTable.getColumnLabels();
        int[] columnTotals = new int[purposeNames.length-1];

		for( int i=0; i < columnTotals.length; i++ ) {
			firstHeader  += String.format("%12s", purposeNames[i+1]);
			secondHeader += "----------- ";
		}

        firstHeader  += String.format("%12s","Total");
        secondHeader += "-----------";

        logger.info(firstHeader);
		logger.info(secondHeader);



        int lineTotal = 0;
        for(int i=0;i<Person.personTypeNameArray.length;++i){
			String personTypeString = Person.personTypeNameArray[i];
			String stringToLog  = String.format("%-30s", personTypeString);

			if(countByPersonType.containsKey(personTypeString)){

                lineTotal = 0;
				int[] countArray = countByPersonType.get(personTypeString);
				for(int j=0;j<columnTotals.length;++j){
					stringToLog += String.format("%12d",countArray[j]);
                    columnTotals[j] += countArray[j];
                    lineTotal += countArray[j];
                } // j
			} // if key
			else{

				// log zeros
                lineTotal = 0;
				for(int j=0;j<columnTotals.length;++j){
					stringToLog += String.format("%12d",0);
				}
			}

            stringToLog += String.format("%12d",lineTotal);

            logger.info(stringToLog);

		} // i

        String stringToLog  = String.format("%-30s", "Total");
        lineTotal = 0;
        for(int j=0;j<columnTotals.length;++j){
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

	
    private void loadIndividualNonMandatoryIncreaseModelData(String filePath) {
        //this array matches the alternative table's structure, with the first row being an alternative
        //could possibly look for the alternative with the largest sum, but this assumes the maximum tours
        //  are done across the board; then again this is hard-coded
        maxTourFrequencyChoiceList = new int[] {-1,2,1,1,1,1,1};
        tourFrequencyIncreaseProbabilityMap = new HashMap<Integer,float[]>();
        TableDataSet probabilityTable;
        try {
            probabilityTable = (new CSVFileReader().readFile(new File(filePath)));
        } catch (IOException e) {
            logger.error("Exception caught reading Individual Non-Mandatory Tour Frequency extension probability table.",e);
            throw new RuntimeException(e);
        }

        String personTypeColumnName = "person_type";
        String mandatoryTourParticipationColumnName = "mandatory_tour";
        String jointTourParticipationColumnName = "joint_tour";
        String nonMandatoryTourTypeColumn = "nonmandatory_tour_type";
        String zeroAdditionalToursColumnName = "0_tours";
        String oneAdditionalToursColumnName = "1_tours";
        String twoAdditionalToursColumnName = "2_tours";

        for (int i = 1; i <= probabilityTable.getRowCount(); i++) {
            int key = getTourIncreaseTableKey((int) probabilityTable.getValueAt(i,nonMandatoryTourTypeColumn),
                                              (int) probabilityTable.getValueAt(i,personTypeColumnName),
                                              ((int) probabilityTable.getValueAt(i,mandatoryTourParticipationColumnName)) == 1,
                                              ((int) probabilityTable.getValueAt(i,jointTourParticipationColumnName)) == 1);
            tourFrequencyIncreaseProbabilityMap.put(key,
                    new float[] {probabilityTable.getValueAt(i,zeroAdditionalToursColumnName),
                                 probabilityTable.getValueAt(i,oneAdditionalToursColumnName),
                                 probabilityTable.getValueAt(i,twoAdditionalToursColumnName)});
        }
    }

    private float[] runIndividualNonMandatoryToursIncreaseModel(Person person, int choice) {
        // use the 1s based choice value as the table row number
        // rowValues is a 0s based indexed array, but the first field is the alternative number,
        // and subsequent fields indicate the nuimber of tours to be generated for the purpose corresponding to the field.
        
        Household household = person.getHouseholdObject();
        

        int personType = person.getPersonTypeNumber();
        boolean participatedInMandatoryTour = person.getListOfWorkTours().size() > 0 || person.getListOfSchoolTours().size() > 0;

        boolean participatedInJointTour = false;
        Tour[] jointTours = person.getHouseholdObject().getJointTourArray();
        if (jointTours != null) {
            for (Tour t : jointTours) {
                if ( t.getPersonInJointTour(person)) {
                    participatedInJointTour = true;
                    break;
                }
            }
        }


        float[] rowValues = null;
        
        boolean notDone = true;
        while (notDone) {

            rowValues = alternativesTable.getRowValues(choice);

            int firstCount = tourCountSum(rowValues);
            if ( firstCount == 0 || firstCount >= 5 ) //if 0 or 5+ tours already, we are done
                break;
            
            for (int i = 1; i < rowValues.length; i++) {

                if (rowValues[i] < maxTourFrequencyChoiceList[i])
                    continue;

                int newChoice=-1;
                int key = getTourIncreaseTableKey( i, personType, participatedInMandatoryTour, participatedInJointTour );
                float[] probabilities = tourFrequencyIncreaseProbabilityMap.get( key );
                Random random = household.getHhRandom();
                int randomCount = household.getHhRandomCount();
                double rn = random.nextDouble();
                for (int j = 0; j < probabilities.length; j++) {
                    if ( rn <= probabilities[j] ) {
                        rowValues[i] += j;
                        newChoice=j;
                        break;
                    }
                }

                // debug output
                if( household.getDebugChoiceModels() ){

                    Logger modelLogger = tourFreq;
                    String[] alternativeNames  = { "no additional", "1 additional", "2 additional" };

                    modelLogger.info("Individual Non-Mandatory Tour Frequency Increase Choice for tour purposeName=" + purposeIndexToNameMap.get( i ) + ", purposeIndex=" + i );
                    modelLogger.info("Alternative                Probability           CumProb");
                    modelLogger.info("---------------         --------------    --------------");

                    double cumProb = 0.0;
                    for( int k=0; k < alternativeNames.length; k++ ){
                        cumProb += probabilities[k];
                        String altString = String.format( "%-3d %-15s", k+1, alternativeNames[k] );
                        modelLogger.info(String.format("%-20s%18.6e%18.6e", altString, probabilities[k], cumProb));
                    }

                    modelLogger.info( String.format("choice: %s, with rn=%.8f, randomCount=%d", newChoice, rn, randomCount ) );

                    modelLogger.info("");
                    modelLogger.info("");
                    
                }
            
            }
            notDone = tourCountSum(rowValues) > 5;
        }

        return rowValues;
    }

    private int tourCountSum(float[] tours) {
        //tours are located in indices 1 -> tours.length
        int sum = 0;
        for (int i = 1; i < tours.length; i++)
            sum += tours[i];
        return sum;
    }

    private int getTourIncreaseTableKey(int nonMandatoryTourType,
                                        int personType,
                                        boolean participatedInMandatoryTour,
                                        boolean participatedInJointTour) {
        return nonMandatoryTourType +
               100*personType +
               10000*(participatedInMandatoryTour ? 1 : 0) +
               100000*(participatedInJointTour ? 1 : 0);
    }

    private void createIndividualNonMandatoryTours_new(Person person, float[] tours) {
        person.clearIndividualNonMandatoryToursArray();
        
        for(int i = 1; i < tours.length; i++) {
            int numTours = (int) tours[i];
            if (numTours > 0)
                person.createIndividualNonMandatoryTours( numTours, purposeIndexToNameMap.get(i), modelStructure );
        }
    }

    
//    private void createIndividualNonMandatoryTours ( Person person, int choice ) {
//
//        // use the 1s based choice value as the table row number
//        float[] rowValues = alternativesTable.getRowValues( choice );
//
//        // rowValues is a 0s based indexed array, but the first field is the alternative number,
//        // and subsequent fields indicate the nuimber of tours to be generated for the purpose corresponding to the field.
//        for ( int i=1; i < rowValues.length; i++ ) {
//
//            int numTours = (int)rowValues[i];
//            if ( numTours == 0 )
//                continue;
//
//            String purposeName = purposeIndexToNameMap.get(i);
//
//            person.createIndividualNonMandatoryTours( numTours, i, purposeName );
//        }
//
//    }

}