package com.pb.models.ctramp.old;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Random;
import java.util.ResourceBundle;
import java.io.FileWriter;
import java.io.File;
import java.io.IOException;

import org.apache.log4j.Logger;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.common.calculator.IndexValues;
import com.pb.models.ctramp.AtWorkSubtourFrequencyDMU;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;


public class AtWorkSubtourFrequencyModel {
	
	public static Logger logger = Logger.getLogger(AtWorkSubtourFrequencyModel.class);
	
    public static final String PROPERTIES_UEC_AT_WORK_SUBTOUR_FREQ  = "UecFile.AtWorkSubtourFrequency";

    public static final int UEC_DATA_PAGE     = 0;
	public static final int UEC_MODEL_PAGE    = 1;


	// model results
	public static final int NO_SUBTOURS          = 1;
	public static final int ONE_EAT              = 2;
	public static final int ONE_BUSINESS         = 3;
	public static final int ONE_MAINT            = 4;
    public static final int TWO_BUSINESS         = 5;
    public static final int ONE_EAT_ONE_BUSINESS = 6;
	



    protected int[] areaType;
    protected int[] zoneTableRow;

    protected HashMap<String,int[]> countByPersonType;
	
	protected AtWorkSubtourFrequencyDMU dmuObject;
	protected ChoiceModelApplication choiceModelApplication;

    protected ModelStructure modelStructure;
    protected String[] alternativeNames;


    /**
	 * Constructor establishes the ChoiceModelApplication, which applies the logit model via the UEC
	 * spreadsheet.
     * @param dmuObject is the UEC dmu object for this choice model
	 * @param uecFileName is the UEC control file name
	 * @param resourceBundle is the application ResourceBundle, from which a properties file HashMap will be created for the UEC
     * @param tazDataManager is the object used to interact with the zonal data table
     * @param modelStructure is the ModelStructure object that defines segmentation and other model structure relate atributes
	 */
	public AtWorkSubtourFrequencyModel( String projectDirectory, ResourceBundle resourceBundle, AtWorkSubtourFrequencyDMU dmuObject, TazDataIf tazDataManager, ModelStructure modelStructure){

	    this.modelStructure = modelStructure;
        this.dmuObject = dmuObject;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        // locate the UEC
        String uecFileName = ResourceUtil.getProperty( resourceBundle, PROPERTIES_UEC_AT_WORK_SUBTOUR_FREQ );
        uecFileName = projectDirectory + uecFileName;
        
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
        String personTypeString = "";

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
            dmuObject.setHouseholdObject(household);

            // loop through the person array (1-based)
    		for(int j=1;j<personArray.length;++j){

                Person person = personArray[j];
    			
                // count the results by person type
                personTypeString = person.getPersonType();

                
                // loop through the work tours for this person
                ArrayList<Tour> tourList = person.getListOfWorkTours();
                if ( tourList == null )
                    continue;
                
                int workTourIndex = 1;
                for ( Tour workTour : tourList ) {
                    
                    // set the area type for the work taz
                    int tableRow = zoneTableRow[ workTour.getTourDestTaz() ];
                    dmuObject.setWorkTazAreaType( areaType[tableRow-1] );

                    
                    try {

                        // set the person and tour object
                        dmuObject.setPersonObject( person );
                        dmuObject.setTourObject( workTour );

                        // write debug header
                        if(household.getDebugChoiceModels()){
                            logger.info(" ");
                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info("AtWork Subtour Freq Model: Debug Statement for Household ID: "+household.getHhId()+
                                        ", Person ID: "+person.getPersonId() + ", Work Tour num: "+workTourIndex );
                        }


                        // set the availability array for the tour frequency model
                        alternativeNames = choiceModelApplication.getAlternativeNames();
                        int numberOfAlternatives = alternativeNames.length;
                        boolean[] availabilityArray = new boolean[numberOfAlternatives+1];
                        Arrays.fill( availabilityArray, true );

                        // create the sample array
                        int[] sampleArray = new int[availabilityArray.length];
                        Arrays.fill(sampleArray, 1);

                        
                        // compute the utilities
                        IndexValues index = dmuObject.getDmuIndexValues();
                        index.setHHIndex( household.getHhId() );
                        index.setZoneIndex( household.getHhTaz() );
                        index.setOriginZone( workTour.getTourDestTaz() );
                        index.setDebug(false);
                        choiceModelApplication.computeUtilities(dmuObject, index, availabilityArray, sampleArray);

                        
                        // get the random number from the household
                        Random random = household.getHhRandom();
                        int randomCount = household.getHhRandomCount();
                        double randomNumber = random.nextDouble();


                        // if the choice model has at least one available alternative, make choice.
                        if ( choiceModelApplication.getAvailabilityCount() > 0 )
                            choice = choiceModelApplication.getChoiceResult( randomNumber );
                        else {
                            logger.error ( String.format( "Exception caught for i=%d, j=%d, tourNum=%d, HHID=%d, no available at-work frequency alternatives to choose from in choiceModelApplication.", i, j, workTourIndex, person.getHouseholdObject().getHhId() ) );
                            throw new RuntimeException();
                        }


                        
                        // debug output
                        if(household.getDebugChoiceModels()){

                            double[] utilities     = choiceModelApplication.getUtilities();
                            double[] probabilities = choiceModelApplication.getProbabilities();

                            logger.info("Person type: "+personTypeString);
                            logger.info("Alternative                 Utility    Probability");
                            logger.info("-------------------- -------------- --------------");

                            for( int k=0; k < alternativeNames.length; k++ ) {
                                logger.info( String.format("%-20s%15.4f%15.4f",alternativeNames[k],utilities[k],probabilities[k]));
                            }

                            logger.info(" ");
                            logger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", alternativeNames[choice-1], randomNumber, randomCount ) );

                            logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
                            logger.info(" ");
                        }

                        
                        person.clearAtWorkSubtours();
                        

                        // set the person choices
                        if( choice == ONE_EAT ) {
                            int id = workTour.getSubtourIdFromIndices(workTourIndex, 0); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkEatPurposeName(), modelStructure );
                        }
                        else if( choice == ONE_BUSINESS ) {
                            int id = workTour.getSubtourIdFromIndices(workTourIndex, 0); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                        }
                        else if( choice == ONE_MAINT ) {
                            int id = workTour.getSubtourIdFromIndices(workTourIndex, 0); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkMaintPurposeName(), modelStructure );
                        }
                        else if( choice == TWO_BUSINESS ) {
                            int id = workTour.getSubtourIdFromIndices(workTourIndex, 0); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                            id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                        }
                        else if( choice == ONE_EAT_ONE_BUSINESS ) {
                            int id = workTour.getSubtourIdFromIndices(workTourIndex, 0); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkEatPurposeName(), modelStructure );
                            id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                            person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                        }


                        // count the results by person type
                        if(countByPersonType.containsKey(personTypeString)){

                            int[] counterArray = countByPersonType.get(personTypeString);
                            counterArray[choice-1]++;
                            countByPersonType.put(personTypeString, counterArray);

                        }
                        else{

                            int[] counterArray = new int[alternativeNames.length];
                            counterArray[choice-1]++;
                            countByPersonType.put(personTypeString, counterArray);

                        } // is personType in map if
                            
                    }
                    catch ( Exception e ) {                     
                        logger.error ( String.format( "Exception caught for i=%d, j=%d, tourNum=%d, HHID=%d.", i, j, workTourIndex, person.getHouseholdObject().getHhId() ) );
                        throw new RuntimeException();
                    }
                    
                    
                    workTourIndex++;
                    
                }

            } // j (person loop)

    	} // i (household loop)

    	
        householdDataManager.setHhArray(householdArray);
        householdDataManager.setAwfRandomCount();

    }
	
	/**
	 * Logs the results of the model.
	 *
	 */
	public void logResults(){
		
		logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
    	logger.info("At-Work Subtour Frequency Model Results");
    	
    	// count of model results
    	logger.info(" ");
    	String firstHeader  = "Person type                 ";
    	String secondHeader = "---------------------------     ";
    	
		for(int i=0;i<alternativeNames.length;++i){
			firstHeader  += String.format("%16s",alternativeNames[i]);
			secondHeader += "------------    ";
		}
    	
        firstHeader  += String.format("%16s","Total");
        secondHeader += "------------";

        logger.info(firstHeader);
		logger.info(secondHeader);

        int[] columnTotals = new int[alternativeNames.length];


        int lineTotal = 0;
        for(int i=0;i<Person.personTypeNameArray.length;++i){
			String personTypeString = Person.personTypeNameArray[i];
			String stringToLog  = String.format("%-28s", personTypeString);

            if(countByPersonType.containsKey(personTypeString)){
                
                lineTotal = 0;
    			int[] countArray = countByPersonType.get(personTypeString);
    			for(int j=0;j<alternativeNames.length;++j){
    				stringToLog += String.format("%16d",countArray[j]);
                    columnTotals[j] += countArray[j];
                    lineTotal += countArray[j];
                } // j

            } // if key
            else{
                
                // log zeros
                lineTotal = 0;
                for(int j=0;j<alternativeNames.length;++j){
                    stringToLog += String.format("%16d",0);
                }
            }

            stringToLog += String.format("%16d",lineTotal);

            logger.info(stringToLog);
			
		} // i
		
        String stringToLog  = String.format("%-28s", "Total");
        lineTotal = 0;
        for(int j=0;j<alternativeNames.length;++j){
            stringToLog += String.format("%16d",columnTotals[j]);
            lineTotal += columnTotals[j];
        } // j

        logger.info(secondHeader);
        stringToLog += String.format("%16d",lineTotal);
        logger.info(stringToLog);
        logger.info(" ");
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
        logger.info(" ");
        logger.info(" ");

	}

}
