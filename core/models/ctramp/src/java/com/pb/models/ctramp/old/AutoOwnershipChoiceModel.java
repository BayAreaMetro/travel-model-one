package com.pb.models.ctramp.old;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Random;
import java.util.ResourceBundle;

import com.pb.common.calculator.UtilityExpressionCalculator;
import com.pb.common.model.ChoiceModelApplication;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.AutoOwnershipChoiceDMU;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TimeDMU;

import org.apache.log4j.Logger;

public class AutoOwnershipChoiceModel {
    
    public static Logger logger = Logger.getLogger(AutoOwnershipChoiceModel.class);
    


    public static final String PROPERTIES_RESULTS_AUTO_OWNERSHIP = "Results.AutoOwnership";


    static final String AO_CONTROL_FILE_TARGET = "aoUEC.file";
    static final int AO_DATA_SHEET = 0;
    static final int AO_MODEL_SHEET = 1;

    static final String TIME_CONTROL_FILE_TARGET = "aoUEC.file";
    static final int TIME_DATA_SHEET = 0;
    static final int AUTO_MODEL_SHEET = 2;
    static final int TRANSIT_MODEL_SHEET = 3;
    static final int WALK_MODEL_SHEET = 4;


    // A ChoiceModelApplication object and altsAvailable[] is needed for each purpose
    ChoiceModelApplication aoModel;
    AutoOwnershipChoiceDMU aoDmuObject;
    boolean[] aoAltsAvailable;
    int[] aoAltsSample;

    String aoResultsFileName;

    ModelStructure modelStructure;

    UtilityExpressionCalculator[] timeUec;
    int[] hhsByAutoOwnership;

    int numAlts;


    public AutoOwnershipChoiceModel(String uecFileName, ResourceBundle resourceBundle, ModelStructure modelStructure){

        this.modelStructure = modelStructure;

        // create the my choice model application
    	setupChoiceModelApplication( uecFileName, resourceBundle );
    	
    	
    }


    private void setupChoiceModelApplication(String uecFileName, ResourceBundle resourceBundle ) {
    	
        aoResultsFileName = resourceBundle.getString( PROPERTIES_RESULTS_AUTO_OWNERSHIP );


        // create the mode choice model DMU object.
        aoDmuObject = new AutoOwnershipChoiceDMU();
        
        // create the my choice model
        aoModel = new ChoiceModelApplication( uecFileName, AO_MODEL_SHEET, AO_DATA_SHEET, 
        		ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), AutoOwnershipChoiceDMU.class);

        numAlts = aoModel.getNumberOfAlternatives();
        aoAltsAvailable = new boolean[numAlts+1];
        aoAltsSample = new int[numAlts+1];

        // set the modeAltsAvailable array to true for all mode choice alternatives for each purpose
        for (int k=1; k <= numAlts; k++)
            aoAltsAvailable[k] = true;

        // set the modeAltsSample array to 1 for all mode choice alternatives for each purpose
        for (int k=1; k <= numAlts; k++)
            aoAltsSample[k] = 1;

    
        // create a set of UEC objects to use to get OD times for the selected long term location
        timeUec = new UtilityExpressionCalculator[3];
        timeUec[0] = new UtilityExpressionCalculator(new File(uecFileName), AUTO_MODEL_SHEET, TIME_DATA_SHEET, 
        		ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), TimeDMU.class );
        timeUec[1] = new UtilityExpressionCalculator(new File(uecFileName), TRANSIT_MODEL_SHEET, TIME_DATA_SHEET, 
        		ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), TimeDMU.class );
        timeUec[2] = new UtilityExpressionCalculator(new File(uecFileName), WALK_MODEL_SHEET, TIME_DATA_SHEET, 
        		ResourceUtil.changeResourceBundleIntoHashMap(resourceBundle), TimeDMU.class );

    }
    
    public void applyModel(HouseholdDataManagerIf householdDataManager){


        // get the array of households
        Household[] householdArray = householdDataManager.getHhArray();



        // create an array for storing the results
    	hhsByAutoOwnership = new int[aoModel.getNumberOfAlternatives()+1];
    	
    	// loop through the households
    	for(int i=1; i < householdArray.length; i++){

            Household household = householdArray[i];
            short chosen = getAutoOwnershipChoice(household);

            household.setAutoOwnershipModelResult(chosen);

            // track the results
            hhsByAutoOwnership[chosen]++;

        }
    	

        householdDataManager.setHhArray(householdArray);
        householdDataManager.setAoRandomCount();


    }
    


    /**
     * Loops through the households in the HouseholdDataManager, gets the auto ownership
     * result for each household, and writes a text file with hhid and auto ownership.
     *
     * @param householdDataManager is the object from which the array of household objects can be retrieved.
     * @param projectDirectory is the root directory for the output file named
     */
    public void saveResults(HouseholdDataManagerIf householdDataManager, String projectDirectory){

        FileWriter writer;
        if ( aoResultsFileName != null ) {

            aoResultsFileName = projectDirectory + aoResultsFileName;

            try {
                writer = new FileWriter(new File(aoResultsFileName));
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred opening AO results file: %s.", aoResultsFileName ) );
                throw new RuntimeException(e);
            }

            try {
                writer.write ( "HHID,AO\n" );
            }
            catch(IOException e){
                logger.fatal( "Exception occurred writing AO header in results file." );
                throw new RuntimeException(e);
            }

            // get the array of households
            Household[] householdArray = householdDataManager.getHhArray();

            for(int i=1; i < householdArray.length; ++i){

                Household household = householdArray[i];
                int hhid = household.getHhId();
                int ao = household.getAutoOwnershipModelResult();

                try {
                    writer.write ( String.format("%d,%d\n", hhid, ao ));
                }
                catch(IOException e){
                    logger.fatal( String.format( "Exception occurred writing AO results file, hhid=%d", hhid ) );
                    throw new RuntimeException(e);
                }

            }


            try {
                writer.close();
            }
            catch(IOException e){
                logger.fatal( String.format( "Exception occurred closing AO results file: %s.", aoResultsFileName ) );
                throw new RuntimeException(e);
            }

        }

    }



    public void logResults(){
    	
        String[] aoCategoryLabel = { "0 autos", "1 auto", "2 autos", "3 autos", "4 or more autos" };
        
        logger.info( "" );
        logger.info( "" );
        logger.info( "Auto Ownership Model Results" );
        logger.info( String.format("%-16s  %10s", "Category", "Num HHs" ));
        
        int total = 0;
        for (int i=1; i < hhsByAutoOwnership.length; i++) {
            logger.info( String.format("%-16s  %10d", aoCategoryLabel[(i-1)], hhsByAutoOwnership[i] ));
            total += hhsByAutoOwnership[i];
        }
        logger.info( String.format("%-16s  %10d", "Total", total ));
        
    }


    public int getNumAoAlternatives() {
        return numAlts;
    }
    

    private short getAutoOwnershipChoice ( Household hhObj ) {

        // update the AO dmuObject for this hh
        aoDmuObject.setHouseholdObject( hhObj );
        aoDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhTaz(), hhObj.getHhTaz(), 0 );


        // set the travel times from home to chosen work and school locations
        double workTimeSavings = getWorkTourAutoTimeSavings( hhObj );        
        double schoolDriveTimeSavings = getSchoolDriveTourAutoTimeSavings( hhObj );        
        double schoolNonDriveTimeSavings = getSchoolNonDriveTourAutoTimeSavings( hhObj );        
        
        aoDmuObject.setWorkTourAutoTimeSavings( workTimeSavings );
        aoDmuObject.setSchoolDriveTourAutoTimeSavings( schoolDriveTimeSavings );
        aoDmuObject.setSchoolNonDriveTourAutoTimeSavings( schoolNonDriveTimeSavings );


        // compute utilities and choose auto ownership alternative.
        aoModel.computeUtilities ( aoDmuObject, aoDmuObject.getDmuIndexValues() );
        
        Random hhRandom = hhObj.getHhRandom();
        double randomNumber = hhRandom.nextDouble();


        // if the choice model has at least one available alternative, make choice.
        short chosenAlt;
        if ( aoModel.getAvailabilityCount() > 0 ) {
            chosenAlt = (short)aoModel.getChoiceResult( randomNumber );
        }
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available auto ownership alternatives to choose from in choiceModelApplication.", hhObj.getHhId() ) );
            throw new RuntimeException();
        }


        // write choice model alternative info to log file
        if ( hhObj.getDebugChoiceModels() ) {
            aoModel.logAlternativesInfo ( "Auto Ownership Choice", String.format("HH_%d", aoDmuObject.getHouseholdObject().getHhId()) );
            aoModel.logSelectionInfo ( "Auto Ownership Choice", String.format("HH_%d", aoDmuObject.getHouseholdObject().getHhId()), randomNumber, chosenAlt );
        }

        hhObj.setAoRandomCount( hhObj.getHhRandomCount() );
        

        return chosenAlt;

    }

    
    private double getWorkTourAutoTimeSavings( Household hhObj ) {

        double totalAutoSavingsRatio = 0.0;
        
        TimeDMU timeDmuObject = new TimeDMU ();
        int[] availability = new int[2];
        availability[1] = 1;

        // determine the travel time savings from home to chosen work and school locations
        // for workers ans sr=tudents by student category
        for ( Person person : hhObj.getPersons() ) {

            // if person is not a worker, skip to next person.
            if ( person.getPersonIsWorker() == 0 )
                continue;

            
            // use a time UEC to get the od times for this person's location choice
            boolean debugFlag = hhObj.getDebugChoiceModels();
            timeDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhTaz(), hhObj.getHhTaz(), person.getUsualWorkLocation(), debugFlag );

            double auto[]    = timeUec[0].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double transit[] = timeUec[1].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double walk[]    = timeUec[2].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            
            // set the minimum of walk and transit time to walk time if no transit access,
            // otherwise to the minimum of walk and transit time.
            double minWalkTransit = walk[0];
            if ( transit[0] > 0 && transit[0] < walk[0] ) {
                minWalkTransit = transit[0];
            }
            
            // set auto savings to be minimum of walk and transit time minus auto time
            double autoSavings = minWalkTransit - auto[0];
            double autoSavingsRatio = ( autoSavings < 120 ? autoSavings/120.0 : 1.0 );

            totalAutoSavingsRatio += autoSavingsRatio;

        }
    
        return totalAutoSavingsRatio;

    }
    

    private double getSchoolDriveTourAutoTimeSavings( Household hhObj ) {

        double totalAutoSavingsRatio = 0.0;
        
        TimeDMU timeDmuObject = new TimeDMU ();
        int[] availability = new int[2];
        availability[1] = 1;

        // determine the travel time savings from home to chosen work and school locations
        // for workers ans sr=tudents by student category
        for ( Person person : hhObj.getPersons() ) {

            // if person is not a worker, skip to next person.
            if ( person.getPersonIsStudentDriving() == 0 )
                continue;

            
            // use a time UEC to get the od times for this person's location choice
            boolean debugFlag = hhObj.getDebugChoiceModels();
            timeDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhTaz(), hhObj.getHhTaz(), person.getUsualSchoolLocation(), debugFlag );

            double auto[]    = timeUec[0].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double transit[] = timeUec[1].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double walk[]    = timeUec[2].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            
            // set the minimum of walk and transit time to walk time if no transit access,
            // otherwise to the minimum of walk and transit time.
            double minWalkTransit = walk[0];
            if ( transit[0] > 0 && transit[0] < walk[0] ) {
                minWalkTransit = transit[0];
            }
            
            // set auto savings to be minimum of walk and transit time minus auto time
            double autoSavings = minWalkTransit - auto[0];
            double autoSavingsRatio = ( autoSavings < 120 ? autoSavings/120.0 : 1.0 );

            totalAutoSavingsRatio += autoSavingsRatio;

        }
    
        return totalAutoSavingsRatio;

    }
    

    private double getSchoolNonDriveTourAutoTimeSavings( Household hhObj ) {

        double totalAutoSavingsRatio = 0.0;
        
        TimeDMU timeDmuObject = new TimeDMU ();
        int[] availability = new int[2];
        availability[1] = 1;

        // determine the travel time savings from home to chosen work and school locations
        // for workers ans sr=tudents by student category
        for ( Person person : hhObj.getPersons() ) {

            // if person is not a worker, skip to next person.
            if ( person.getPersonIsStudentNonDriving() == 0 )
                continue;

            
            // use a time UEC to get the od times for this person's location choice
            boolean debugFlag = hhObj.getDebugChoiceModels();
            timeDmuObject.setDmuIndexValues( hhObj.getHhId(), hhObj.getHhTaz(), hhObj.getHhTaz(), person.getUsualSchoolLocation(), debugFlag );

            double auto[]    = timeUec[0].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double transit[] = timeUec[1].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            double walk[]    = timeUec[2].solve( timeDmuObject.getDmuIndexValues(), timeDmuObject, availability );
            
            // set the minimum of walk and transit time to walk time if no transit access,
            // otherwise to the minimum of walk and transit time.
            double minWalkTransit = walk[0];
            if ( transit[0] > 0 && transit[0] < walk[0] ) {
                minWalkTransit = transit[0];
            }
            
            // set auto savings to be minimum of walk and transit time minus auto time
            double autoSavings = minWalkTransit - auto[0];
            double autoSavingsRatio = ( autoSavings < 120 ? autoSavings/120.0 : 1.0 );

            totalAutoSavingsRatio += autoSavingsRatio;

        }
    
        return totalAutoSavingsRatio;

    }

}
