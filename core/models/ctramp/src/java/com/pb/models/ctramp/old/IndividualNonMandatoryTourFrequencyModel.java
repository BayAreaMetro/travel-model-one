package com.pb.models.ctramp.old;

import java.util.*;
import java.io.File;
import java.io.IOException;

import org.apache.log4j.Logger;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import com.pb.models.ctramp.CoordinatedDailyActivityPatternModel;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.IndividualNonMandatoryTourFrequencyDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

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
public class IndividualNonMandatoryTourFrequencyModel {

	public static Logger logger = Logger.getLogger(IndividualNonMandatoryTourFrequencyModel.class);

	public static final int UEC_DATA_PAGE     = 0;
    public static final int FT_WORKER_UEC_MODEL_PAGE = 1;
    public static final int PT_WORKER_UEC_MODEL_PAGE = 2;
    public static final int UNIVERSITY_UEC_MODEL_PAGE = 3;
    public static final int NONWORKER_UEC_MODEL_PAGE = 4;
    public static final int RETIRED_UEC_MODEL_PAGE = 5;
    public static final int DRIVING_STUDENT_UEC_MODEL_PAGE = 6;
    public static final int NON_DRIVING_STUDENT_UEC_MODEL_PAGE = 7;
    public static final int PRESCHOOL_UEC_MODEL_PAGE    = 8;
    public static int NUM_PERSON_TYPE_MODEL_PAGES = 8;

    public static final String MANDATORY_ACTIVITY = CoordinatedDailyActivityPatternModel.MANDATORY_PATTERN;
    public static final String HOME_ACTIVITY = CoordinatedDailyActivityPatternModel.HOME_PATTERN;

    public static final String PROPERTIES_TOUR_FREQUENCY_EXTENSION_PROBABILITIES_FILE = "IndividualNonMandatoryTour.FrequencyExtension.ProbabilityFile";


    //protected int[] areaType;
    //protected int[] zoneTableRow;

    protected TazDataIf tazDataManager;

    protected HashMap<String,int[]> countByPersonType;
    protected HashMap<Integer,String> purposeIndexToNameMap;

    protected IndividualNonMandatoryTourFrequencyDMU dmuObject;
	protected ChoiceModelApplication[] choiceModelApplication;
    protected TableDataSet alternativesTable;

    protected ModelStructure modelStructure;

    String[] altNames = null;

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
	public IndividualNonMandatoryTourFrequencyModel( IndividualNonMandatoryTourFrequencyDMU dmuObject, String uecFileName, ResourceBundle resourceBundle, TazDataIf tazDataManager, ModelStructure modelStructure){

        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;
        this.dmuObject = dmuObject;

        //zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        //areaType = tazDataManager.getZonalAreaType();


        // set up the model
        choiceModelApplication = new ChoiceModelApplication[NUM_PERSON_TYPE_MODEL_PAGES+1];     // one choice model for each person type that has model specified; Ones indexing for personType.
        choiceModelApplication[1] = new ChoiceModelApplication( uecFileName, FT_WORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[2] = new ChoiceModelApplication( uecFileName, PT_WORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[3] = new ChoiceModelApplication( uecFileName, UNIVERSITY_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[4] = new ChoiceModelApplication( uecFileName, NONWORKER_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[5] = new ChoiceModelApplication( uecFileName, RETIRED_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[6] = new ChoiceModelApplication( uecFileName, DRIVING_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[7] = new ChoiceModelApplication( uecFileName, NON_DRIVING_STUDENT_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );
        choiceModelApplication[8] = new ChoiceModelApplication( uecFileName, PRESCHOOL_UEC_MODEL_PAGE, UEC_DATA_PAGE, ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), dmuObject.getClass() );




        // the alternatives are the same for each person type; use the first choiceModelApplication to get its uec and from it, get the TableDataSet of alternatives
        // to use to determine which tour purposes should be generated for the chose alternative.
        alternativesTable = choiceModelApplication[1].getUEC().getAlternativeData();

        // check the field names in the alternatives table; make sure the their order is as expected.
        String[] fieldNames = alternativesTable.getColumnLabels();

        purposeIndexToNameMap = new HashMap<Integer,String>();
        purposeIndexToNameMap.put( 1, modelStructure.ESCORT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 2, modelStructure.SHOPPING_PURPOSE_NAME );
        purposeIndexToNameMap.put( 3, modelStructure.EAT_OUT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 4, modelStructure.OTH_MAINT_PURPOSE_NAME );
        purposeIndexToNameMap.put( 5, modelStructure.SOCIAL_PURPOSE_NAME );
        purposeIndexToNameMap.put( 6, modelStructure.OTH_DISCR_PURPOSE_NAME );

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
        loadIndividualNonMandatoryIncreaseModelData(resourceBundle.getString(CtrampApplication.PROPERTIES_PROJECT_DIRECTORY) +
                resourceBundle.getString(PROPERTIES_TOUR_FREQUENCY_EXTENSION_PROBABILITIES_FILE));
    }

	/**
	 * Applies the model for the array of households that are stored in the HouseholdDataManager.
	 * The results are summarized by person type.
     *
     * @param householdDataManager is the object containg the Household objects for which this model is to be applied.
	 */
	public void applyModel(HouseholdDataManagerIf householdDataManager){

        int debugCount = 0;
        int modelIndex = -1;
        int choice = -1;
        String personTypeString = "Missing";

        //this will be an array with values 1 -> tours.length being the number of non-mandatory tours in each category
        // this keeps it consistent with the way the alternatives are held in the alternatives file/arrays
        float[] tours = null;


        // prepare the results array
		countByPersonType = new HashMap<String,int[]>();
        int numPurposes = alternativesTable.getColumnLabels().length;

    	// get the array of households
    	Household[] householdArray = householdDataManager.getHhArray();

    	// loop the households (1-based array)
    	for(int i=1;i<householdArray.length;++i){

    		Household household = householdArray[i];

    		// get this household's person array
    		Person[] personArray = household.getPersons();

    		// set the household id, origin taz, hh taz, and debugFlag=false in the dmu
            dmuObject.setHouseholdObject(household);

            // set the area type for the home taz
            int urban = tazDataManager.getZoneIsUrban( household.getHhTaz() );
            dmuObject.setHomeTazIsUrban( urban );

            // loop through the person array (1-based)
    		for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];

    			// determine if this person has a mandatory daily activity
    			String activity = person.getCdapActivity();

                // count the results by person type
                personTypeString = "Missing";


                try {

                    // only apply the model if person is not PRESCHOOL and person doesn not have H daily activity pattern
                    if( person.getPersonIsPreschoolChild()==0 && !activity.equalsIgnoreCase(HOME_ACTIVITY) ) {

                        // set the person
                        dmuObject.setPersonObject(person);

                        // write debug header
                        if(household.getDebugChoiceModels()){
                            logger.info(" ");
                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info("INMTF Model: Debug Statement for Household ID: "+household.getHhId()+
                                        ", Person ID: "+person.getPersonId());
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



                        // create the sample array
                        int[] sampleArray = new int[availabilityArray.length];
                        Arrays.fill(sampleArray, 1);

                        // compute the utilities
                        dmuObject.setDmuIndexValues( household.getHhId(), household.getHhTaz(), household.getHhTaz(), -1 );


                        choiceModelApplication[modelIndex].computeUtilities(dmuObject, dmuObject.getDmuIndexValues(), availabilityArray, sampleArray);

                        // get the random number from the household
                        Random random = household.getHhRandom();
                        double randomNumber = random.nextDouble();


                        // if the choice model has at least one available alternative, make choice.
                        if ( choiceModelApplication[modelIndex].getAvailabilityCount() > 0 )
                            choice = choiceModelApplication[modelIndex].getChoiceResult( randomNumber );
                        else {
                            logger.error ( String.format( "Exception caught for i=%d, j=%d, activity=%s, HHID=%d, no Non-Mandatory Tour Frequency alternatives available to choose from in choiceModelApplication.", i, j, activity, person.getHouseholdObject().getHhId() ) );
                            throw new RuntimeException();
                        }

                        altNames = choiceModelApplication[modelIndex].getAlternativeNames();

                        // debug output
                        if(household.getDebugChoiceModels()){

                            double[] utilities     = choiceModelApplication[modelIndex].getUtilities();
                            double[] probabilities = choiceModelApplication[modelIndex].getProbabilities();

                            logger.info("Person type: "+personTypeString);
                            logger.info("Alternative                 Utility    Probability");
                            logger.info("-------------------- -------------- --------------");

                            for(int k=0; k < altNames.length; k++ ){
                                logger.info( String.format("%-20s%15.4f%15.4f", altNames[k], utilities[k], probabilities[k]) );
                            }

                            logger.info(" ");
                            logger.info( String.format("Choice: %s, with rn=%.8f", altNames[choice-1], randomNumber ) );

                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info(" ");
                        }


                        person.setInmtfChoice ( choice );

                        // create the non-mandatory tour objects for the choice made.
//                        createIndividualNonMandatoryTours ( person, choice );
                        tours = runIndividualNonMandatoryToursIncreaseModel(person,choice);
                        createIndividualNonMandatoryTours_new(person,tours);

                    }



                    // count the results by person type
                    if ( ! personTypeString.equalsIgnoreCase("Missing") ) {

                        //new way
                        // count the results
                        int[] counterArray = (countByPersonType.containsKey(personTypeString)) ?
                                countByPersonType.get(personTypeString) : new int[numPurposes];
                        for (int p=1; p < numPurposes; p++)
                            counterArray[p-1] += (int) tours[p];
                        countByPersonType.put(personTypeString, counterArray);

                    }

                }
                catch ( Exception e ) {
                    logger.error ( String.format( "Exception caught for i=%d, j=%d, activity=%s, HHID=%d", i, j, activity, person.getHouseholdObject().getHhId() ) );
                    throw new RuntimeException(e);
                }


            } // j (person loop)
    	} // i (household loop)

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setInmtfRandomCount();

    }

	/**
	 * Logs the results of the model.
	 *
	 */
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
        float[] rowValues = alternativesTable.getRowValues(choice);
        float[] copy = Arrays.copyOf(rowValues,rowValues.length); //copy to update in frequency extension loop

        int personType = person.getPersonTypeNumber();
        boolean participatedInMandatoryTour = person.getListOfWorkTours().size() > 0 || person.getListOfSchoolTours().size() > 0;
        boolean participatedInJointTour = false;
        int personNum = person.getPersonNum();
        Tour[] jointTours = person.getHouseholdObject().getJointTourArray();
        if (jointTours != null) {
            outer: for (Tour t : jointTours) {
                for (int i : t.getPersonNumArray()) {
                    if (i == personNum) {
                        participatedInJointTour = true;
                        break outer;
                    }
                }
            }
        }

        int firstCount = tourCountSum(rowValues);
        boolean notDone = firstCount < 5 && firstCount > 0; //if 0 or 5+ tours already, we are done


        while (notDone) {

            copy = Arrays.copyOf(rowValues,rowValues.length);
            for (int i = 1; i < copy.length; i++) {
                if (copy[i] < maxTourFrequencyChoiceList[i])
                    continue;
                float[] probabilities = tourFrequencyIncreaseProbabilityMap.get(
                        getTourIncreaseTableKey(i,personType,participatedInMandatoryTour,participatedInJointTour));
                double p = person.getHouseholdObject().getHhRandom().nextDouble();
                for (int j = 0; j < probabilities.length; j++) {
                    if (p <= probabilities[j]) {
                        copy[i] += j;
                        break;
                    }
                }
            }
            notDone = tourCountSum(copy) > 5;
        }

        return copy;
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
                person.createIndividualNonMandatoryTours(numTours,purposeIndexToNameMap.get(i),modelStructure);
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