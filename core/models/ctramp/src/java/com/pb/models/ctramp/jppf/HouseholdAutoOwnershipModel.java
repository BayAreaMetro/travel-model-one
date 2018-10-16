package com.pb.models.ctramp.jppf;

import java.io.File;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Random;

import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.newmodel.UtilityExpressionCalculator;
import com.pb.models.ctramp.AutoOwnershipChoiceDMU;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TimeDMU;

import org.apache.log4j.Logger;


public class HouseholdAutoOwnershipModel implements Serializable {
    
    private transient Logger logger = Logger.getLogger(HouseholdAutoOwnershipModel.class);
    private transient Logger aoLogger = Logger.getLogger("ao");
    

    private static final String AO_CONTROL_FILE_TARGET = "UecFile.AutoOwnership";
    private static final int AO_DATA_SHEET = 0;
    private static final int AO_MODEL_SHEET = 1;
    private static final int AUTO_MODEL_SHEET = 2;
    private static final int TRANSIT_MODEL_SHEET = 3;
    private static final int WALK_MODEL_SHEET = 4;


    ChoiceModelApplication aoModel;
    AutoOwnershipChoiceDMU aoDmuObject;

    UtilityExpressionCalculator[] timeUec;



    public HouseholdAutoOwnershipModel( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {

        // setup the auto ownership choice model objects
        setupAutoOwnershipChoiceModelApplication( propertyMap, dmuFactory );
    	
    }


    private void setupAutoOwnershipChoiceModelApplication( HashMap<String, String> propertyMap, CtrampDmuFactoryIf dmuFactory ) {
        
        logger.info( "setting up AO choice model." );

        // locate the auto ownership UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String autoOwnershipUecFile = propertyMap.get( AO_CONTROL_FILE_TARGET);
        autoOwnershipUecFile = projectDirectory + autoOwnershipUecFile;

        // create the auto ownership choice model DMU object.
        aoDmuObject = dmuFactory.getAutoOwnershipDMU();
        
        
        // create the auto ownership choice model object
        aoModel = new ChoiceModelApplication( autoOwnershipUecFile, AO_MODEL_SHEET, AO_DATA_SHEET, propertyMap, (VariableTable)aoDmuObject );

        
        TimeDMU timeDmu = new TimeDMU();
        
        // create a set of UEC objects to use to get OD times for the selected long term location
        timeUec = new UtilityExpressionCalculator[3];
        timeUec[0] = new UtilityExpressionCalculator(new File(autoOwnershipUecFile), AUTO_MODEL_SHEET, AO_DATA_SHEET, propertyMap, (VariableTable)timeDmu );
        timeUec[1] = new UtilityExpressionCalculator(new File(autoOwnershipUecFile), TRANSIT_MODEL_SHEET, AO_DATA_SHEET, propertyMap, (VariableTable)timeDmu );
        timeUec[2] = new UtilityExpressionCalculator(new File(autoOwnershipUecFile), WALK_MODEL_SHEET, AO_DATA_SHEET, propertyMap, (VariableTable)timeDmu );

    }

    
    public void applyModel( Household hhObject ){

        if ( hhObject.getDebugChoiceModels() )
            hhObject.logHouseholdObject( "Pre AO Household " + hhObject.getHhId() + " Object", aoLogger );
        
        int chosen = getAutoOwnershipChoice( hhObject );
        hhObject.setAutoOwnershipModelResult((short)chosen);

    }
    
    
    private int getAutoOwnershipChoice ( Household hhObj ) {

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
        int randomCount = hhObj.getHhRandomCount();
        double rn = hhRandom.nextDouble();

        

        // if the choice model has at least one available alternative, make choice.
        int chosenAlt;
        if ( aoModel.getAvailabilityCount() > 0 ) {
            chosenAlt = aoModel.getChoiceResult( rn );
        }
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available auto ownership alternatives to choose from in choiceModelApplication.", hhObj.getHhId() ) );
            throw new RuntimeException();
        }


        // write choice model alternative info to log file
        if ( hhObj.getDebugChoiceModels() ) {

            double[] utilities     = aoModel.getUtilities();
            double[] probabilities = aoModel.getProbabilities();

            aoLogger.info("Alternative                    Utility       Probability           CumProb");
            aoLogger.info("--------------------   ---------------      ------------      ------------");

            double cumProb = 0.0;
            for( int k=0; k < aoModel.getNumberOfAlternatives(); k++ ) {
                cumProb += probabilities[k];
                aoLogger.info(String.format("%-20s%18.6e%18.6e%18.6e", k + " autos", utilities[k], probabilities[k], cumProb ) );
            }

            aoLogger.info(" ");
            aoLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", chosenAlt, rn, randomCount ) );

            aoLogger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
            aoLogger.info("");
            aoLogger.info("");

        
            // write choice model alternative info to debug log file
            aoModel.logAlternativesInfo ( "Household Auto Ownership Choice", String.format("HH_%d", hhObj.getHhId() ) );
            aoModel.logSelectionInfo ( "Household Auto Ownership Choice", String.format("HH_%d", hhObj.getHhId() ), rn, chosenAlt );

            // write UEC calculation results to separate model specific log file
            aoModel.logUECResults( aoLogger, String.format("Household Auto Ownership Choice, HH_%d", hhObj.getHhId() ) );
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
        Person[] personArray = hhObj.getPersons();
        for ( int i=1; i < personArray.length; i++ ) {

            Person person = personArray[i];
            
            // if person is not a worker, skip to next person.
            if ( person.getPersonIsWorker() == 0 )
                continue;

            
            // use a time UEC to get the od times for this person's location choice
            boolean debugFlag = false;
            if ( hhObj.getDebugChoiceModels() )
            	debugFlag = hhObj.getDebugChoiceModels();
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

            if ( debugFlag ) {
            	aoLogger.info( "Debug for hhid=" + hhObj.getHhId() + ", personNum=" + i );
            	aoLogger.info( "auto=" + auto + ", transit=" + transit + ", walk=" + walk );
            	aoLogger.info( "auto=" + auto + ", transit=" + transit + ", walk=" + walk );
            	aoLogger.info( "minWalkTransit=" + minWalkTransit + ", autoSavings=" + autoSavings + ", autoSavingsRatio=" + autoSavingsRatio + ", totalAutoSavingsRatio=" + totalAutoSavingsRatio );
            }
            
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
        Person[] personArray = hhObj.getPersons();
        for ( int i=1; i < personArray.length; i++ ) {

            Person person = personArray[i];
            

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
        Person[] personArray = hhObj.getPersons();
        for ( int i=1; i < personArray.length; i++ ) {

            Person person = personArray[i];
            

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
