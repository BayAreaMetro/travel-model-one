package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.AtWorkSubtourFrequencyDMU;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;
//

public class HouseholdAtWorkSubtourFrequencyModel implements Serializable {
	
    private transient Logger logger = Logger.getLogger(HouseholdAtWorkSubtourFrequencyModel.class);
    private transient Logger tourFreq = Logger.getLogger("tourFreq");
	
    private static final String PROPERTIES_UEC_AT_WORK_SUBTOUR_FREQ  = "UecFile.AtWorkSubtourFrequency";

    private static final int UEC_DATA_PAGE     = 0;
	private static final int UEC_MODEL_PAGE    = 1;


	// model results
	//private static final int NO_SUBTOURS          = 1;
	private static final int ONE_EAT              = 2;
	private static final int ONE_BUSINESS         = 3;
	private static final int ONE_MAINT            = 4;
    private static final int TWO_BUSINESS         = 5;
    private static final int ONE_EAT_ONE_BUSINESS = 6;
	



    private int[] areaType;
    private int[] zoneTableRow;

    //protected HashMap<String,int[]> countByPersonType;
	
	private AtWorkSubtourFrequencyDMU dmuObject;
	private ChoiceModelApplication choiceModelApplication;

	private ModelStructure modelStructure;
	private String[] alternativeNames;


    /**
	 * Constructor establishes the ChoiceModelApplication, which applies the logit model via the UEC
	 * spreadsheet.
     * @param dmuObject is the UEC dmu object for this choice model
	 * @param uecFileName is the UEC control file name
	 * @param resourceBundle is the application ResourceBundle, from which a properties file HashMap will be created for the UEC
     * @param tazDataManager is the object used to interact with the zonal data table
     * @param modelStructure is the ModelStructure object that defines segmentation and other model structure relate atributes
	 */
	public HouseholdAtWorkSubtourFrequencyModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ){

	    this.modelStructure = modelStructure;

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();

        setUpModels( propertyMap, dmuFactory );
        
	}
	
	
    private void setUpModels( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {

        logger.info( String.format( "setting up %s tour frequency choice model.", ModelStructure.AT_WORK_CATEGORY ) );
        
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String uecFileName = propertyMap.get( PROPERTIES_UEC_AT_WORK_SUBTOUR_FREQ );
        uecFileName = projectDirectory + uecFileName;

        
        dmuObject = dmuFactory.getAtWorkSubtourFrequencyDMU();
        
        // set up the model
        choiceModelApplication = new ChoiceModelApplication(uecFileName, UEC_MODEL_PAGE, UEC_DATA_PAGE, propertyMap, (VariableTable)dmuObject );
        
    }
	

    /**
	 * Applies the model for the array of households that are stored in the HouseholdDataManager.
	 * The results are summarized by person type.
     *
     * @param householdDataManager is the object containg the Household objects for which this model is to be applied.
	 */
	public void applyModel( Household household ){

        int choice = -1;
        String personTypeString = "";

        Logger modelLogger = tourFreq;
        if ( household.getDebugChoiceModels() )
            household.logHouseholdObject( "Pre AtWork Subtour Frequency Choice HHID=" + household.getHhId() + " Object", modelLogger );
        

        // prepare the results array
		//countByPersonType = new HashMap<String,int[]>();
		
        // get this household's person array
		Person[] personArray = household.getPersons();
		
		// set the household id, origin taz, hh taz, and debugFlag=false in the dmu
        dmuObject.setHouseholdObject(household);

        // loop through the person array (1-based)
		for(int j=1;j<personArray.length;++j){

            Person person = personArray[j];
			
            // count the results by person type
            personTypeString = person.getPersonType();

            if ( household.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), personTypeString );
                household.logPersonObject( decisionMakerLabel, modelLogger, person );
            }
            

            // loop through the work tours for this person
            ArrayList<Tour> tourList = person.getListOfWorkTours();
            if ( tourList == null )
                continue;
            

            
            String separator = "";
            String choiceModelDescription = "" ;
            String decisionMakerLabel = "";
            String loggingHeader = "";
            
            int workTourIndex = 0;
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

                        choiceModelDescription = String.format ( "At-work Subtour Frequency Choice Model:" );
                        decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, workTourId=%d", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType(), workTour.getTourId() );
                        choiceModelApplication.choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
                            
                        modelLogger.info(" ");
                        String loggerString = choiceModelDescription + " for " + decisionMakerLabel + ".";
                        for (int k=0; k < loggerString.length(); k++)
                            separator += "+";
                        modelLogger.info( loggerString );
                        modelLogger.info( separator );
                        modelLogger.info( "" );
                        modelLogger.info( "" );
                     
                        loggingHeader = String.format( "%s   %s", choiceModelDescription, decisionMakerLabel );

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
                    index.setOriginZone( workTour.getTourOrigTaz() );
                    index.setDestZone( workTour.getTourDestTaz() );
                    index.setDebug( household.getDebugChoiceModels() );
                    
                    
                    if( household.getDebugChoiceModels() ){
                        household.logTourObject( loggingHeader, modelLogger, person, workTour );
                    }

                    choiceModelApplication.computeUtilities(dmuObject, index, availabilityArray, sampleArray);

                    
                    // get the random number from the household
                    Random random = household.getHhRandom();
                    int randomCount = household.getHhRandomCount();
                    double rn = random.nextDouble();


                    // if the choice model has at least one available alternative, make choice.
                    if ( choiceModelApplication.getAvailabilityCount() > 0 )
                        choice = choiceModelApplication.getChoiceResult( rn );
                    else {
                        logger.error ( String.format( "Exception caught for j=%d, tourNum=%d, HHID=%d, no available at-work frequency alternatives to choose from in choiceModelApplication.", j, workTourIndex, person.getHouseholdObject().getHhId() ) );
                        throw new RuntimeException();
                    }


                    // debug output
                    if( household.getDebugChoiceModels() ){

                        double[] utilities     = choiceModelApplication.getUtilities();
                        double[] probabilities = choiceModelApplication.getProbabilities();

                        int personNum = person.getPersonNum();
                        modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
                        modelLogger.info("Alternative                    Utility       Probability           CumProb");
                        modelLogger.info("--------------------    --------------    --------------    --------------");

                        double cumProb = 0.0;
                        for( int k=0; k < alternativeNames.length; k++ ){
                            cumProb += probabilities[k];
                            String altString = String.format( "%-3d %-16s", k+1, alternativeNames[k] );
                            modelLogger.info(String.format("%-20s%18.6e%18.6e%18.6e", altString, utilities[k], probabilities[k], cumProb));
                        }

                        modelLogger.info(" ");
                        String altString = String.format( "%-3d %-16s", choice, alternativeNames[choice-1] );
                        modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

                        modelLogger.info( separator );
                        modelLogger.info("");
                        modelLogger.info("");
                        

                        // write choice model alternative info to debug log file
                        choiceModelApplication.logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
                        choiceModelApplication.logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, choice );

                        // write UEC calculation results to separate model specific log file
                        choiceModelApplication.logUECResults( modelLogger, loggingHeader );
                        
                    }


                    
                    workTour.setSubtourFreqChoice( choice );

                    
                    // set the person choices
                    if( choice == ONE_EAT ) {
                        int id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkEatPurposeName(), modelStructure );
                    }
                    else if( choice == ONE_BUSINESS ) {
                        int id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                    }
                    else if( choice == ONE_MAINT ) {
                        int id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkMaintPurposeName(), modelStructure );
                    }
                    else if( choice == TWO_BUSINESS ) {
                        int id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                        id = workTour.getSubtourIdFromIndices(workTourIndex, 2); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                    }
                    else if( choice == ONE_EAT_ONE_BUSINESS ) {
                        int id = workTour.getSubtourIdFromIndices(workTourIndex, 1); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkEatPurposeName(), modelStructure );
                        id = workTour.getSubtourIdFromIndices(workTourIndex, 2); 
                        person.createAtWorkSubtour( id, choice, workTour.getTourDestTaz(), workTour.getTourDestWalkSubzone(), modelStructure.getAtWorkBusinessPurposeName(), modelStructure );
                    }



                    // count the results by person type
//                    if(countByPersonType.containsKey(personTypeString)){
//
//                        int[] counterArray = countByPersonType.get(personTypeString);
//                        counterArray[choice-1]++;
//                        countByPersonType.put(personTypeString, counterArray);
//
//                    }
//                    else{
//
//                        int[] counterArray = new int[alternativeNames.length];
//                        counterArray[choice-1]++;
//                        countByPersonType.put(personTypeString, counterArray);
//
//                    } // is personType in map if
                        
                }
                catch ( Exception e ) {                     
                    logger.error ( String.format( "Exception caught for j=%d, tourNum=%d, HHID=%d.", j, workTourIndex, household.getHhId() ) );
                    throw new RuntimeException();
                }
                
                
                workTourIndex++;
                
            }

        } // j (person loop)

		household.setAwfRandomCount( household.getHhRandomCount() );
        
    }

	
	
}
