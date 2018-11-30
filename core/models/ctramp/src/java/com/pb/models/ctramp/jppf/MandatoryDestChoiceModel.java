package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Random;
import java.util.ArrayList;
import java.util.HashMap;

import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.util.IndexSort;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.DestChoiceDMU;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.Tour;
import com.pb.models.ctramp.jppf.DestinationSampleOfAlternativesModel;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.jppf.ModeChoiceModel;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;

import org.apache.log4j.Logger;

public class MandatoryDestChoiceModel implements Serializable {

    private transient Logger logger = Logger.getLogger(MandatoryDestChoiceModel.class);
    private transient Logger dcManLogger =  Logger.getLogger("tourDcMan");

    
    private static final String PROPERTIES_MANDATORY_RUN_WORK = "UsualWorkAndSchoolLocationChoice.RunFlag.Work";
    private static final String PROPERTIES_MANDATORY_RUN_UNIVERSITY = "UsualWorkAndSchoolLocationChoice.RunFlag.University";
    private static final String PROPERTIES_MANDATORY_RUN_SCHOOL = "UsualWorkAndSchoolLocationChoice.RunFlag.School";

    private static final int DC_DATA_SHEET = 0;


    private String tourCategory;
    private ModelStructure modelStructure;

    private String[] tourPurposeList;
    private HashMap<String, Integer> purposeModelIndexMap;

    private ModeChoiceDMU mcDmuObject;
    private DestChoiceDMU dcDmuObject;
    private DcSoaDMU dcSoaDmuObject;
    
    private ModeChoiceModel mcModel;
    private DestinationSampleOfAlternativesModel dcSoaModel;

    // A ChoiceModelApplication object and modeAltsAvailable[] is needed for each purpose
    private ChoiceModelApplication dcModel[];

    private int[] sampleValues;
    
    private boolean runWorkTours;
    private boolean runUnivTours;
    private boolean runSchoolTours;
    
    private int numberOfSubzones;

    private int modelIndex;
    private int shadowPricingIteration;

    private long lsTime = 0;
    private long soaTime = 0;
    private long totTime = 0;
    
//    private long[][] filterCount = null;
//    private long[][] expressionCount = null;
//    private long[][] coeffCount = null;
    private long cmUecTime;
    private long cmOtherTime;
    private long lsTotalTime;
    
    

    public MandatoryDestChoiceModel( int index, HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj, String dcUecFileName, String soaUecFile, int soaSampleSize, String modeChoiceUecFile, CtrampDmuFactoryIf dmuFactory ){

    	// set the model structure and the tour purpose list
    	this.modelStructure = modelStructure;
        this.tourCategory = tourCategory;

        modelIndex = index;

        mcDmuObject = dmuFactory.getModeChoiceDMU();

        dcDmuObject = dmuFactory.getDestChoiceDMU();        
        
        dcSoaDmuObject = dmuFactory.getDcSoaDMU();

        dcDmuObject.setDestChoiceSize(dcSizeObj);
        dcSoaDmuObject.setDestChoiceSizeObject(dcSizeObj);
        
        
        // create an array of ChoiceModelApplication objects for each choice purpose
        setupDestChoiceModelArrays( propertyMap, dcUecFileName, modeChoiceUecFile, soaUecFile, soaSampleSize, dcSizeObj, tazDataManager );
    	
        shadowPricingIteration = 0;
        
    }


    
    private void setupDestChoiceModelArrays( HashMap<String, String> propertyMap, String dcUecFileName, String modeChoiceUecFile, String soaUecFile, int soaSampleSize, DestChoiceSize dcSizeObj, TazDataIf tazDataManager ) {
        
        tourPurposeList = modelStructure.getDcModelPurposeList( this.tourCategory );

        numberOfSubzones = tazDataManager.getNumberOfSubZones();

        
        // create the mode choice model
        mcModel = new ModeChoiceModel( propertyMap, modelStructure, tourCategory, mcDmuObject, tazDataManager );
//        filterCount = new long[mcModel.getFilterCount().length][mcModel.getFilterCount()[0].length];
//        expressionCount = new long[mcModel.getExpressionCount().length][mcModel.getExpressionCount()[0].length];
//        coeffCount = new long[mcModel.getCoeffCount().length][mcModel.getCoeffCount()[0].length];
        
        // these flags are useful in calibration to limit the number of usual work and school location choices made
        // to speed up calibration model runs.
        if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) ) {

            String propertyValue = "";
            
            runWorkTours = false;
            propertyValue = propertyMap.get( PROPERTIES_MANDATORY_RUN_WORK );
            if ( propertyValue != null )
                runWorkTours = propertyValue.equalsIgnoreCase("true");
            
            runUnivTours = false;
            propertyValue = propertyMap.get( PROPERTIES_MANDATORY_RUN_UNIVERSITY );
            if ( propertyValue != null )
                runUnivTours = propertyValue.equalsIgnoreCase("true");
            
            runSchoolTours = false;
            propertyValue = propertyMap.get( PROPERTIES_MANDATORY_RUN_SCHOOL );
            if ( propertyValue != null )
                runSchoolTours = propertyValue.equalsIgnoreCase("true");
            
        }
        

        // create a sample of alternatives choice model object for use in selecting a sample
        // of all possible destination choice alternatives.
        dcSoaModel = new DestinationSampleOfAlternativesModel( soaUecFile, soaSampleSize, propertyMap, modelStructure, tourCategory, tazDataManager, dcSizeObj, dcSoaDmuObject );        
    
    
        // get the number of purposes and declare the array dimension to be this size.
        // create a HashMap to map purposeName to model index
        purposeModelIndexMap = new HashMap<String, Integer>();

        int maxUecIndex = 0;
        for ( String purposeName : tourPurposeList ) {
            int uecIndex = modelStructure.getDcUecIndexForPurpose( purposeName );
            purposeModelIndexMap.put( purposeName, uecIndex );
            if ( uecIndex > maxUecIndex )
                maxUecIndex = uecIndex;
        }
        
        dcModel = new ChoiceModelApplication[maxUecIndex+1];

        // for each unique model index, create the ChoiceModelApplication object and the availabilty array
        for ( int m : purposeModelIndexMap.values() ) {
            dcModel[m] = new ChoiceModelApplication ( dcUecFileName, m, DC_DATA_SHEET, propertyMap, (VariableTable)dcDmuObject );
        }

        sampleValues = new int[soaSampleSize];
        
    }
    
    
    /**
     *  This method is called if a shadow pricing methodology is applied to reset the scaled size terms in objects that reference them.
     */
    public void setDcSize ( DestChoiceSize dcSizeObj, int currentShadowPriceIteration ) {
        
        // if a dcModel object is being recycled by multiple tasks, only need to reset size object once per iteration.
        if ( currentShadowPriceIteration > shadowPricingIteration ) {
        
            dcDmuObject.setDestChoiceSize(dcSizeObj);
            dcSoaDmuObject.setDestChoiceSizeObject(dcSizeObj);
            
            dcSoaModel.setDcSizeForSampleOfAlternatives( tourPurposeList, dcSizeObj );
            shadowPricingIteration++;
        
        }
        
    }


    
    public void applyWorkSchoolLocationChoice( Household hh ) {
        
        lsTime = 0;
        soaTime = 0;
        totTime = 0;

        cmUecTime = 0;
        cmOtherTime = 0;
        lsTotalTime = 0;
//        for (int i=0; i < filterCount.length; i++ ){
//            Arrays.fill(filterCount[i], 0);
//            Arrays.fill(expressionCount[i], 0);
//            Arrays.fill(coeffCount[i], 0);
//        }

        long totCheck = System.nanoTime();
        
        if ( hh.getDebugChoiceModels() ) {
            String label = String.format( "Pre Work/School Location Choice HHId=%d Object", hh.getHhId() );
            hh.logHouseholdObject( label, dcManLogger );
        }

        
        // declare these variables here so their values can be logged if a RuntimeException occurs.
        int i = -1;
        int purposeIndex = -1;
        String purposeName = "";


        Person[] persons = hh.getPersons();

        for ( i=1; i < persons.length; i++ ) {

            ArrayList<String> dcPurposeList = new ArrayList<String>();

            Person p = persons[i];

            // get a list of DC purpose names for this person based on the standard person types that make mandatory tours:
            if ( p.getPersonIsPreschoolChild() == 1 || p.getPersonIsStudentNonDriving() == 1 || p.getPersonIsStudentDriving() == 1 ) {
                if ( runSchoolTours )
                    dcPurposeList.add( modelStructure.getSchoolPurpose( p.getAge() ) );
                if ( runWorkTours && p.getPersonIsStudentDriving() == 1 && p.getPersonIsWorker() == 1 )
                    dcPurposeList.add( modelStructure.getWorkPurposeFromIncomeInDollars( p.getPersonIsPartTimeWorker()==1, hh.getIncomeInDollars() ) );
            }
            else if ( p.getPersonIsUniversityStudent() == 1 ) {
                if ( runUnivTours )
                    dcPurposeList.add( modelStructure.getUniversityPurpose() );
                if ( runWorkTours && p.getPersonIsWorker() == 1 )
                    dcPurposeList.add( modelStructure.getWorkPurposeFromIncomeInDollars( p.getPersonIsPartTimeWorker()==1, hh.getIncomeInDollars() ) );
            }
            else if ( ( p.getPersonIsPartTimeWorker() == 1 || p.getPersonIsFullTimeWorker() == 1 ) ) {
                if ( runWorkTours )
                    dcPurposeList.add( modelStructure.getWorkPurposeFromIncomeInDollars( p.getPersonIsPartTimeWorker()==1, hh.getIncomeInDollars() ) );
            }


            if ( hh.getDebugChoiceModels() ) {
                String decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", p.getHouseholdObject().getHhId(), p.getPersonNum(), p.getPersonType() );
    
                Logger modelLogger = null;
                modelLogger = dcManLogger;
    
                hh.logPersonObject( decisionMakerLabel, modelLogger, p );
            }
            

            int choiceNum = 0;
            for ( String dcPurposeName : dcPurposeList ) {

                purposeName = dcPurposeName;
                purposeIndex = modelStructure.getDcModelPurposeIndex( purposeName );

                int chosen = -1; 
                try {

                    int homeTaz = hh.getHhTaz();
                    int origTaz = homeTaz;

                    // update the MC dmuObject for this person
                    mcDmuObject.setHouseholdObject( hh );
                    mcDmuObject.setPersonObject( p );
                    mcDmuObject.setTourObject( new Tour( p, purposeName ) ); // make a Tour object for use by the MC DMU for work/school location choice MC logsum
                    mcDmuObject.setDmuIndexValues( hh.getHhId(), origTaz, 0 );

                    // update the DC dmuObject for this person
                    dcDmuObject.setHouseholdObject( hh );
                    dcDmuObject.setPersonObject( p );
                    dcDmuObject.setDmuIndexValues( hh.getHhId(), homeTaz, origTaz, 0 );

                    // get the work location alternative chosen from the sample
                    chosen =  selectLocationFromSampleOfAlternatives( dcDmuObject, dcSoaDmuObject, mcDmuObject, null, p, purposeName, purposeIndex, ++choiceNum );
                    
                }
                catch (RuntimeException e) {
                    logger.fatal( String.format("Exception caught in dcModel selecting work or school location for i=%d, hh.hhid=%d, person i=%d, in %s choice, purposeIndex=%d, purposeName=%s", i, hh.getHhId(), i, tourCategory, purposeIndex, purposeName ) );
                    logger.fatal( "Exception caught:", e );
                    logger.fatal( "Throwing new RuntimeException() to terminate." );
                    throw new RuntimeException();
                }

                // get zone, subzone from DC alternative
                int chosenDestAlt = (chosen-1)/numberOfSubzones + 1;
                int chosenShrtWlk = chosen - (chosenDestAlt-1)*numberOfSubzones - 1;

                
                
                // set chosen values in person object - university and school are saved as school locations
                if ( modelStructure.getDcModelPurposeIsWorkPurpose( purposeName ) ) {
                    p.setWorkLoc( chosenDestAlt );
                    p.setWorkLocSubzone( chosenShrtWlk );
                }
                else if ( modelStructure.getDcModelPurposeIsSchoolPurpose( purposeName ) ) {
                    p.setSchoolLoc( chosenDestAlt );
                    p.setSchoolLocSubzone( chosenShrtWlk );
                }
                else if ( modelStructure.getDcModelPurposeIsUniversityPurpose( purposeName ) ) {
                    p.setSchoolLoc( chosenDestAlt );
                    p.setSchoolLocSubzone( chosenShrtWlk );
                }

            }

        }
        
        totTime += (System.nanoTime() - totCheck);
    }


    


    private int selectLocationFromSampleOfAlternatives( DestChoiceDMU dcDmuObject, DcSoaDMU dcSoaDmuObject, ModeChoiceDMU mcDmuObject, Tour tour, Person person, String purposeName, int purposeIndex, int choiceNum ) {

        int uecIndex = modelStructure.getDcUecIndexForPurpose( purposeName );
        
        Household household = dcDmuObject.getHouseholdObject();
        
        long soaCheck = System.nanoTime();
        
        // compute the sample of alternatives set for the person
        dcSoaModel.computeDestinationSampleOfAlternatives( dcSoaDmuObject, null, person, purposeName, purposeIndex );

        soaTime += (System.nanoTime() - soaCheck);
        
        // get sample of locations and correction factors for sample
        int numUniqueAltsInSample = dcSoaModel.getNumUniqueAlts();
        int[] finalSample = dcSoaModel.getSampleOfAlternatives();
        float[] sampleCorrectionFactors = dcSoaModel.getSampleOfAlternativesCorrections();

        
        

        int numAlts = dcModel[uecIndex].getNumberOfAlternatives();

        boolean[] destAltsAvailable = new boolean[numAlts+1];
        int[] destAltsSample = new int[numAlts+1];

        // set the destAltsAvailable array to true for all destination choice alternatives for each purpose
        for (int k=0; k <= numAlts; k++)
                destAltsAvailable[k] = false;

        // set the destAltsSample array to 1 for all destination choice alternatives for each purpose
        for (int k=0; k <= numAlts; k++)
                destAltsSample[k] = 0;

        

        String tourPrimaryPurpose = "";
        int index = purposeName.indexOf('_');
        if ( index < 0 )
            tourPrimaryPurpose = purposeName;
        else
            tourPrimaryPurpose = purposeName.substring(0,index);
        
        
        // set tour origin taz/subzone and start/end times for calculating mode choice logsum
        int origTaz = -1;
        int origSubz = -1;
        int tourDepart = -1; 
        int tourEnd = -1; 
        Logger modelLogger = null;
        if ( tourPrimaryPurpose.equalsIgnoreCase( ModelStructure.WORK_PURPOSE_NAME ) ) {
            tourDepart = modelStructure.getDefaultAmHour();
            tourEnd = modelStructure.getDefaultPmHour();
            origTaz = household.getHhTaz();
            origSubz = household.getHhWalkSubzone();
            modelLogger = dcManLogger;
        }
        else if ( tourPrimaryPurpose.equalsIgnoreCase( ModelStructure.UNIVERSITY_PURPOSE_NAME ) ) {
            tourDepart = modelStructure.getDefaultAmHour();
            tourEnd = modelStructure.getDefaultPmHour();
            origTaz = household.getHhTaz();
            origSubz = household.getHhWalkSubzone();
            modelLogger = dcManLogger;
        }
        else if ( tourPrimaryPurpose.equalsIgnoreCase( ModelStructure.SCHOOL_PURPOSE_NAME ) ) {
            tourDepart = modelStructure.getDefaultAmHour();
            tourEnd = modelStructure.getDefaultMdHour();
            origTaz = household.getHhTaz();
            origSubz = household.getHhWalkSubzone();
            modelLogger = dcManLogger;
        }
        

        // determine the logsum array index into which the computed values will be stored
        int logsumIndex = modelStructure.getSkimPeriodCombinationIndex( tourDepart, tourEnd );

        
        String choiceModelDescription = "";
        String decisionMakerLabel = "";
        String loggingHeader = "";
        if ( household.getDebugChoiceModels() ) {
            choiceModelDescription = String.format ( "Tour Mode Choice Logsum calculation for %s Location Choice", purposeName );
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
            loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
        }        
        
        
        // for the destinations and sub-zones in the sample, compute mc logsums and save in DC dmuObject.
        // also save correction factor and set availability and sample value for the sample alternative to true. 1, respectively.
        for (int i=1; i <= numUniqueAltsInSample; i++) {

            int d = (finalSample[i]-1)/numberOfSubzones + 1;
            int w = finalSample[i] - (d-1)*numberOfSubzones - 1;
            
            
            // set the zone, walk subzone, start and end time values for the mcDmuObject and calculate the logsum.
            mcDmuObject.setTourOrigTaz( origTaz );
            mcDmuObject.setTourOrigWalkSubzone( origSubz );
            mcDmuObject.setTourDestTaz( d );
            mcDmuObject.setTourDestWalkSubzone( w );
            mcDmuObject.setTourStartHour( tourDepart );
            mcDmuObject.setTourEndHour( tourEnd );
            mcDmuObject.setDmuIndexValues( household.getHhId(), origTaz, d );

            
            if ( household.getDebugChoiceModels() ) {
                household.logTourObject( loggingHeader, modelLogger, person, mcDmuObject.getTourObject() );
            }
            
            long lsCheck = System.nanoTime();

            // get the mode choice logsum for the destination choice sample alternative
            double logsum = mcModel.getModeChoiceLogsum( mcDmuObject, purposeName, modelLogger, choiceModelDescription, decisionMakerLabel );

            lsTime += (System.nanoTime() - lsCheck);
            
            cmUecTime += mcModel.getCmUecTime();
            cmOtherTime += mcModel.getCmOtherTime();
            lsTotalTime += mcModel.getLsTotalTime();
//            long[][] counts = mcModel.getFilterCount();
//            for ( int j=0; j < counts.length; j++ )
//                for ( int k=0; k < counts[j].length; k++ )
//                    filterCount[j][k] += counts[j][k];
//            counts = mcModel.getExpressionCount();
//            for ( int j=0; j < counts.length; j++ )
//                for ( int k=0; k < counts[j].length; k++ )
//                    expressionCount[j][k] += counts[j][k];
//            counts = mcModel.getCoeffCount();
//            for ( int j=0; j < counts.length; j++ )
//                for ( int k=0; k < counts[j].length; k++ )
//                    coeffCount[j][k] += counts[j][k];
            
            // set logsum value in DC dmuObject for the logsum index, sampled zone and subzone.
            dcDmuObject.setMcLogsum ( logsumIndex, d, w, logsum );

            // set sample of alternatives correction factor used in destination choice utility for the sampled alternative.
            dcDmuObject.setDcSoaCorrections( d, w, sampleCorrectionFactors[i] );

            // set availaibility and sample values for the purpose, dcAlt.
            destAltsAvailable[finalSample[i]] = true;
            destAltsSample[finalSample[i]] = 1;

        }

        

        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( household.getDebugChoiceModels() ) {
            
            // null tour means the DC is a mandatory usual location choice
            choiceModelDescription = String.format ( "Usual Location Choice Model for: Purpose=%s", purposeName );
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourNum=%d", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType(), choiceNum );

            modelLogger.info(" ");
            modelLogger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
            modelLogger.info( "Usual Location Choice Model for: Purpose=" + purposeName +
                    ", Person Num: "+person.getPersonNum() + ", Person Type: "+person.getPersonType() + ", TourNum=" + choiceNum );
            
            loggingHeader = String.format( "%s for %s", choiceModelDescription, decisionMakerLabel );
                        
            dcModel[uecIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        
        }

        
        
        // compute destination choice proportions and choose alternative
        dcModel[uecIndex].computeUtilities ( dcDmuObject, dcDmuObject.getDmuIndexValues(), destAltsAvailable, destAltsSample );
        
        Random hhRandom = household.getHhRandom();
        int randomCount = household.getHhRandomCount();
        double rn = hhRandom.nextDouble();
        
        
        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        if ( dcModel[uecIndex].getAvailabilityCount() > 0 ) {
            chosen = dcModel[uecIndex].getChoiceResult( rn );
        }
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, PersonNum=%d, no available %s destination choice alternatives to choose from in choiceModelApplication.", dcDmuObject.getHouseholdObject().getHhId(), dcDmuObject.getPersonObject().getPersonNum(), purposeName ) );
            throw new RuntimeException();
        }
        
        
        // write choice model alternative info to log file
        if ( household.getDebugChoiceModels() ) {
            
            double[] utilities     = dcModel[uecIndex].getUtilities();
            double[] probabilities = dcModel[uecIndex].getProbabilities();
            boolean[] availabilities = dcModel[uecIndex].getAvailabilities();

            String personTypeString = person.getPersonType();
            int personNum = person.getPersonNum();

            modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString );
            modelLogger.info("Alternative             Availability           Utility       Probability           CumProb");
            modelLogger.info("--------------------- --------------    --------------    --------------    --------------");

            // copy the values of the sample to an array that can be sorted for logging purposes
            for (int i=1; i <= numUniqueAltsInSample; i++)
                sampleValues[i-1] = finalSample[i];
            for (int i=numUniqueAltsInSample; i < sampleValues.length; i++)
                sampleValues[i] = Integer.MAX_VALUE;
            int[] sortedSampleValueIndices = IndexSort.indexSort( sampleValues );
                        
            double cumProb = 0.0;
            int selectedIndex = -1;
            for(int j=1; j <= numUniqueAltsInSample; j++){

                int k =  sortedSampleValueIndices[j-1];
                int alt = finalSample[k+1];

                if ( alt == chosen )
                    selectedIndex = j;
                
                int d = ( alt-1) / numberOfSubzones + 1;
                int w = alt - (d-1)*numberOfSubzones - 1;
                cumProb += probabilities[alt-1];
                String altString = String.format( "%-3d %5d %5d %5d", j, alt, d, w );
                modelLogger.info(String.format("%-21s%15s%18.6e%18.6e%18.6e", altString, availabilities[alt], utilities[alt-1], probabilities[alt-1], cumProb));
            }

            modelLogger.info(" ");
            int d = (chosen-1)/numberOfSubzones + 1;
            int w = chosen - (d-1)*numberOfSubzones - 1;
            String altString = String.format( "%-3d %5d %5d %5d", selectedIndex, chosen, d, w );
            modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

            modelLogger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++");
            modelLogger.info(" ");

        
            
            dcModel[uecIndex].logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            dcModel[uecIndex].logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );

            
            // write UEC calculation results to separate model specific log file
            dcModel[uecIndex].logUECResults( modelLogger, loggingHeader );
                

        }

        return chosen;

    }
    
    /**
     * @return total milliseconds accumulated computing MC Logsums for destination choice
     */
    public long getLogsumTime() {
        return lsTime;
    }
 
    /**
     * @return total milliseconds accumulated computing SOA probabilities for destination choice
     */
    public long getSoaTime() {
        return soaTime;
    }
 
    /**
     * @return total milliseconds accumulated computing destination choice
     */
    public long getTotTime() {
        return totTime;
    }
 
    public int getProbCalcs() {
        return dcSoaModel.getSoaProbabilitiesCalculationCount();
    }
    
    public int getModelIndex(){
        return modelIndex;
    }
   
    public int getCurrentOrigTaz() {
        return dcSoaModel.getCurrentOrigTaz();
    }


//    public long[][] getFilterCount() {
//        return filterCount;
//    }
//    public long[][] getExpressionCount() {
//        return expressionCount;
//    }
//    public long[][] getCoeffCount() {
//        return coeffCount;
//    }
    public long getCmUecTime() {
        return cmUecTime;
    }
    public long getCmOtherTime() {
        return cmOtherTime;
    }
    public long getLsTotalTime() {
        return lsTotalTime;
    }

}