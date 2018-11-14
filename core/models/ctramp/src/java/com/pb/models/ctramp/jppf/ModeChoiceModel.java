package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.*;

import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.common.util.ObjectUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TNCAndTaxiWaitTimeCalculator;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;




//
import org.apache.log4j.Logger;

public class ModeChoiceModel implements Serializable {
    
    private transient Logger logger = Logger.getLogger(ModeChoiceModel.class);
    private transient Logger tourMCManLogger = Logger.getLogger( "tourMcMan" );
    private transient Logger tourMCNonManLogger = Logger.getLogger( "tourMcNonMan" );
    

    public static final int MC_DATA_SHEET = 0;
    public static final String PROPERTIES_UEC_TOUR_MODE_CHOICE = "UecFile.TourModeChoice";

    
    // A MyChoiceModelApplication object and modeAltsAvailable[] is needed for each purpose
    private ChoiceModelApplication mcModel[];
    private ModeChoiceDMU mcDmuObject;

    private String tourCategory;
    private String[] tourPurposeList;

    private HashMap<String, Integer> purposeModelIndexMap;

    private String[][] modeAltNames;

    private boolean saveUtilsProbsFlag=false;
    
//    private long[][] filterCount = null;
//    private long[][] expressionCount = null;
//    private long[][] coeffCount = null;
    private long cmUecTime;
    private long cmOtherTime;
    private long mcLsTotalTime;
    //added for TNC and Taxi modes
    TNCAndTaxiWaitTimeCalculator tncTaxiWaitTimeCalculator = null;
    protected TazDataIf tazDataManager;


    public ModeChoiceModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory, CtrampDmuFactoryIf dmuFactory, TazDataIf tazDataManager ){

        this.tourCategory =  tourCategory;
        mcDmuObject = dmuFactory.getModeChoiceDMU();
        setupModeChoiceModelApplicationArray( propertyMap, modelStructure, tourCategory );
        
        tncTaxiWaitTimeCalculator = new TNCAndTaxiWaitTimeCalculator();
        tncTaxiWaitTimeCalculator.createWaitTimeDistributions(propertyMap);
        this.tazDataManager = tazDataManager;
    }

    public ModeChoiceModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory, ModeChoiceDMU mcDmuObject, TazDataIf tazDataManager ){

        this.tourCategory =  tourCategory;
        this.mcDmuObject = mcDmuObject;
        setupModeChoiceModelApplicationArray( propertyMap, modelStructure, tourCategory );
        tncTaxiWaitTimeCalculator = new TNCAndTaxiWaitTimeCalculator();
        tncTaxiWaitTimeCalculator.createWaitTimeDistributions(propertyMap);
        this.tazDataManager = tazDataManager;
    }



    private void setupModeChoiceModelApplicationArray( HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory ) {

        logger.info( String.format( "setting up %s tour mode choice model.", tourCategory ) );

        // locate the individual mandatory tour mode choice model UEC
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String mcUecFile = propertyMap.get( PROPERTIES_UEC_TOUR_MODE_CHOICE );
        mcUecFile = projectDirectory + mcUecFile;

        // default is to not save the tour mode choice utils and probs for each tour
        String saveUtilsProbsString = propertyMap.get( CtrampApplication.PROPERTIES_SAVE_TOUR_MODE_CHOICE_UTILS );
        if ( saveUtilsProbsString != null ) {
            if ( saveUtilsProbsString.equalsIgnoreCase( "true" ) )
                saveUtilsProbsFlag = true;
        }

        
        // get the number of purposes and declare the array dimension to be this size.
        tourPurposeList = modelStructure.getDcModelPurposeList( tourCategory );
        
        // create a HashMap to map purposeName to model index
        purposeModelIndexMap = new HashMap<String, Integer>();

        // keep a set of unique model sheet numbers so that we can create ChoiceModelApplication objects once for each model sheet used
        TreeSet<Integer> modelIndexSet = new TreeSet<Integer>();
        
        int maxUecIndex = 0;
        for ( String purposeName : tourPurposeList ) {
            int uecIndex = modelStructure.getTourModeChoiceUecIndexForPurpose( purposeName );
            purposeModelIndexMap.put( purposeName, uecIndex );
            modelIndexSet.add( uecIndex );
            if ( uecIndex > maxUecIndex )
                maxUecIndex = uecIndex;
        }
        
        mcModel = new ChoiceModelApplication[maxUecIndex+1];

        // declare dimensions for the array of choice alternative availability by purpose
        modeAltNames = new String[maxUecIndex+1][];

        // for each unique model index, create the ChoiceModelApplication object and the availabilty array
        Iterator<Integer> it = modelIndexSet.iterator();
        while ( it.hasNext() ) {
            int m = it.next();
            mcModel[m] = new ChoiceModelApplication ( mcUecFile, m, MC_DATA_SHEET, propertyMap, (VariableTable)mcDmuObject );
            modeAltNames[m] = mcModel[m].getAlternativeNames();

//            if (filterCount == null){
//                filterCount = new long[mcModel[m].getFilterCount().length][mcModel[m].getFilterCount()[0].length];
//                expressionCount = new long[mcModel[m].getExpressionCount().length][mcModel[m].getExpressionCount()[0].length];
//                coeffCount = new long[mcModel[m].getCoeffCount().length][mcModel[m].getCoeffCount()[0].length];
//            }

            
//            try{
//                logger.info ( "mcModel[" + m + "] size:   " + ObjectUtil.checkObjectSize(mcModel[m]) );
//            }catch(Exception e){
//                throw(new RuntimeException(e));
//            }
        }
        
    }



    /**
     * Calculate and return the tour mode choice logsum for the DMU object.
     * @param mcDmuObject is the tour mode choice model DMU object
     * @return logsum of the tour mode choice alternatives
     */
    public double getModeChoiceLogsum ( ModeChoiceDMU mcDmuObject, String purposeName, Logger modelLogger, String choiceModelDescription, String decisionMakerLabel ) {

        long check1 = System.nanoTime();
        
        int modelIndex = purposeModelIndexMap.get( purposeName );

        Household household = mcDmuObject.getHouseholdObject();
        float SingleTNCWaitTimeOrig = 0;
        float SingleTNCWaitTimeDest = 0;
        float SharedTNCWaitTimeOrig = 0;
        float SharedTNCWaitTimeDest = 0;
        float TaxiWaitTimeOrig = 0;
        float TaxiWaitTimeDest = 0;
        int oTaz = mcDmuObject.dmuIndex.getOriginZone();
        int dTaz = mcDmuObject.dmuIndex.getDestZone();
        float popEmpDenOrig = tazDataManager.getPopEmpPerSqMi(oTaz);
        float popEmpDenDest = tazDataManager.getPopEmpPerSqMi(dTaz);
        
        if(household!=null){
            Random hhRandom = household.getHhRandom();
            double rnum = hhRandom.nextDouble();
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenDest);
        }else{
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime( popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime(popEmpDenDest);
        }

        mcDmuObject.setOrigTaxiWaitTime(TaxiWaitTimeOrig);
        mcDmuObject.setDestTaxiWaitTime(TaxiWaitTimeDest);
        mcDmuObject.setOrigSingleTNCWaitTime(SingleTNCWaitTimeOrig);
        mcDmuObject.setDestSingleTNCWaitTime(SingleTNCWaitTimeDest);
        mcDmuObject.setOrigSharedTNCWaitTime(SharedTNCWaitTimeOrig);
        mcDmuObject.setDestSharedTNCWaitTime(SharedTNCWaitTimeDest);
        
        // log headers to traceLogger
        if ( household.getDebugChoiceModels() ) {
        	mcModel[modelIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }
        
        
        mcModel[modelIndex].computeUtilities( mcDmuObject, mcDmuObject.getDmuIndexValues() );
        cmUecTime = mcModel[modelIndex].getTotalCount();
        cmOtherTime = mcModel[modelIndex].getOtherCount();
//        long[][] counts = mcModel[modelIndex].getFilterCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                filterCount[j][k] = counts[j][k];
//        counts = mcModel[modelIndex].getExpressionCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                expressionCount[j][k] = counts[j][k];
//        counts = mcModel[modelIndex].getCoeffCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                coeffCount[j][k] = counts[j][k];
        
        double logsum = mcModel[modelIndex].getLogsum();

        
        // write UEC calculation results to separate model specific log file
        if( household.getDebugChoiceModels() ){
        	if (modelLogger.isDebugEnabled()) {
        		String loggingHeader = String.format( "%s   %s", choiceModelDescription, decisionMakerLabel );
        		mcModel[modelIndex].logUECResults( modelLogger, loggingHeader );
        	}
            modelLogger.info( choiceModelDescription + " Logsum value: " + logsum );
            modelLogger.info( "" );
            modelLogger.info( "" );
        }

        
        mcLsTotalTime = System.nanoTime() - check1;

        return logsum;

    }


    
    public double getModeChoiceLogsum ( ModeChoiceDMU mcDmuObject, String purposeName ) {

        long check1 = System.nanoTime();
        
        int modelIndex = purposeModelIndexMap.get( purposeName );

        Household household = mcDmuObject.getHouseholdObject();
        float SingleTNCWaitTimeOrig = 0;
        float SingleTNCWaitTimeDest = 0;
        float SharedTNCWaitTimeOrig = 0;
        float SharedTNCWaitTimeDest = 0;
        float TaxiWaitTimeOrig = 0;
        float TaxiWaitTimeDest = 0;
        int oTaz = mcDmuObject.dmuIndex.getOriginZone();
        int dTaz = mcDmuObject.dmuIndex.getDestZone();
        float popEmpDenOrig = tazDataManager.getPopEmpPerSqMi(oTaz);
        float popEmpDenDest = tazDataManager.getPopEmpPerSqMi(dTaz);
        
        if(household!=null){
            Random hhRandom = household.getHhRandom();
            double rnum = hhRandom.nextDouble();
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenDest);
        }else{
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime( popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime(popEmpDenDest);
        }

        mcDmuObject.setOrigTaxiWaitTime(TaxiWaitTimeOrig);
        mcDmuObject.setDestTaxiWaitTime(TaxiWaitTimeDest);
        mcDmuObject.setOrigSingleTNCWaitTime(SingleTNCWaitTimeOrig);
        mcDmuObject.setDestSingleTNCWaitTime(SingleTNCWaitTimeDest);
        mcDmuObject.setOrigSharedTNCWaitTime(SharedTNCWaitTimeOrig);
        mcDmuObject.setDestSharedTNCWaitTime(SharedTNCWaitTimeDest);        
        // log headers to traceLogger
        if ( household.getDebugChoiceModels() ) {
            mcModel[modelIndex].choiceModelUtilityTraceLoggerHeading( "", "" );
        }
        
        
        mcModel[modelIndex].computeUtilities( mcDmuObject, mcDmuObject.getDmuIndexValues() );
        cmUecTime = mcModel[modelIndex].getTotalCount();
        cmOtherTime = mcModel[modelIndex].getOtherCount();
//        long[][] counts = mcModel[modelIndex].getFilterCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                filterCount[j][k] = counts[j][k];
//        counts = mcModel[modelIndex].getExpressionCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                expressionCount[j][k] = counts[j][k];
//        counts = mcModel[modelIndex].getCoeffCount();
//        for ( int j=0; j < counts.length; j++ )
//            for ( int k=0; k < counts[j].length; k++ )
//                coeffCount[j][k] = counts[j][k];
        
        double logsum = mcModel[modelIndex].getLogsum();

        
        // write UEC calculation results to separate model specific log file
        if( household.getDebugChoiceModels() ){
        	if (tourMCNonManLogger.isDebugEnabled()) {
        		String loggingHeader = String.format( "%s    %s", "", "" );
        		mcModel[modelIndex].logUECResults( tourMCNonManLogger, loggingHeader );
        	}
        }
        
        mcLsTotalTime = System.nanoTime() - check1;

        return logsum;

    }


    private int getModeChoice ( ModeChoiceDMU mcDmuObject, String purposeName ) {

        int modelIndex = purposeModelIndexMap.get( purposeName );

        Household household = mcDmuObject.getHouseholdObject();

        Logger modelLogger = null;
        if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) )
            modelLogger = tourMCManLogger;
        else
            modelLogger = tourMCNonManLogger;
            
        String choiceModelDescription = "";
        String decisionMakerLabel = "";
        String loggingHeader = "";
        String separator = "";

        
        Tour tour = mcDmuObject.getTourObject();
        
        if ( household.getDebugChoiceModels() ) {

            Person person = mcDmuObject.getPersonObject();    	 
            
            choiceModelDescription = String.format ( "%s Tour Mode Choice Model for: Purpose=%s, Orig=%d, OrigSubZ=%d, Dest=%d, DestSubZ=%d", tourCategory, purposeName, household.getHhTaz(), household.getHhWalkSubzone(), tour.getTourDestTaz(), tour.getTourDestWalkSubzone() );
            decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s, TourId=%d", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType(), tour.getTourId() );
            loggingHeader = String.format( "%s    %s", choiceModelDescription, decisionMakerLabel );
            
            household.logHouseholdObject( "Pre " + tourCategory + " Tour Mode Choice Model HHID=" + household.getHhId(), tourMCManLogger );               
            household.logPersonObject( decisionMakerLabel, tourMCManLogger, person );            
            
            mcModel[modelIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );


            modelLogger.info(" ");
            for (int k=0; k < loggingHeader.length(); k++)
                separator += "+";
            modelLogger.info( loggingHeader );
            modelLogger.info( separator );
         
            household.logTourObject( loggingHeader, modelLogger, person, tour );
            
        }

        mcModel[modelIndex].computeUtilities( mcDmuObject, mcDmuObject.getDmuIndexValues() );

        Random hhRandom = household.getHhRandom();
        int randomCount = household.getHhRandomCount();
        double rn = hhRandom.nextDouble();

        // if the choice model has at least one available alternative, make choice.
        int chosen;
        if ( mcModel[modelIndex].getAvailabilityCount() > 0 )
            chosen = mcModel[modelIndex].getChoiceResult( rn );
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, no available %s tour mode alternatives to choose from in choiceModelApplication.", household.getHhId(), tourCategory ) );
            throw new RuntimeException();
        }
        
        
        // debug output
        if( household.getDebugChoiceModels() ){

            double[] utilities     = mcModel[modelIndex].getUtilities();          // 0s-indexing
            double[] probabilities = mcModel[modelIndex].getProbabilities();      // 0s-indexing
            boolean[] availabilities = mcModel[modelIndex].getAvailabilities();   // 1s-indexing
            String[] altNames = mcModel[modelIndex].getAlternativeNames();        // 0s-indexing

            Person person = mcDmuObject.getPersonObject();
            String personTypeString = person.getPersonType();
            int personNum = person.getPersonNum();
            
            modelLogger.info("Person num: " + personNum  + ", Person type: " + personTypeString + ", Tour Id: " + tour.getTourId() );
            modelLogger.info("Alternative                    Utility       Probability           CumProb");
            modelLogger.info("--------------------    --------------    --------------    --------------");

            double cumProb = 0.0;
            for(int k=0; k < mcModel[modelIndex].getNumberOfAlternatives(); k++){
                cumProb += probabilities[k];
                String altString = String.format( "%-3d  %s", k+1, altNames[k] );
                modelLogger.info( String.format( "%-20s%15s%18.6e%18.6e%18.6e", altString, availabilities[k+1], utilities[k], probabilities[k], cumProb ) );
            }

            modelLogger.info(" ");
            String altString = String.format( "%-3d  %s", chosen, altNames[chosen-1] );
            modelLogger.info( String.format("Choice: %s, with rn=%.8f, randomCount=%d", altString, rn, randomCount ) );

            modelLogger.info( separator );
            modelLogger.info("");
            modelLogger.info("");
            
            
            // write choice model alternative info to log file
            mcModel[modelIndex].logAlternativesInfo ( choiceModelDescription, decisionMakerLabel );
            mcModel[modelIndex].logSelectionInfo ( choiceModelDescription, decisionMakerLabel, rn, chosen );
            mcModel[modelIndex].logLogitCalculations ( choiceModelDescription, decisionMakerLabel );

            
            // write UEC calculation results to separate model specific log file
            mcModel[modelIndex].logUECResults( modelLogger, loggingHeader );
        }

        
        
        if ( saveUtilsProbsFlag ) {
            
            // get the utilities and probabilities arrays for the tour mode choice model for this tour and save them to the tour object 
            double[] dUtils     = mcModel[modelIndex].getUtilities();
            double[] dProbs = mcModel[modelIndex].getProbabilities();
            
            float[] utils = new float[dUtils.length];
            float[] probs = new float[dUtils.length];
            for ( int k=0; k < dUtils.length; k++ ) {
                utils[k] = (float)dUtils[k];
                probs[k] = (float)dProbs[k];
            }
            
            tour.setTourModalUtilities(utils);
            tour.setTourModalProbabilities(probs);
            
        }

        
        return chosen;

    }

    public void applyModel( Household household ){

        try {
	        if (tourCategory.equalsIgnoreCase(ModelStructure.JOINT_NON_MANDATORY_CATEGORY)) {
	            Tour[] jointTours = household.getJointTourArray();
	            if (jointTours!=null) {
	            	for ( int i=0; i < jointTours.length; i++ ) {
	            		Tour tour = jointTours[i];  
	            		applyJointModel(household, tour); 
	            	}
	            	household.setJmcRandomCount(household.getHhRandomCount());
	            }
	        }
        } catch ( Exception e ) {
            logger.error( String.format( "error in joint tour mode choice model model for hhId=%d.", household.getHhId()));
            throw new RuntimeException(e);
        }
        // get the array of persons for this household
        Person[] personArray = household.getPersons();

        // loop through the persons (1-based array)
        for(int j=1;j<personArray.length;++j){

            Tour tour = null;
            Person person = personArray[j];
            
            try {
	            if (tourCategory.equalsIgnoreCase(ModelStructure.MANDATORY_CATEGORY)) {
	            	ArrayList<Tour> workTours = person.getListOfWorkTours();
	            	for ( int i=0; i < workTours.size(); i++ ) {
	            		tour = workTours.get(i); 
	            		applyIndividualModel(household, person, tour); 
	            	}
	            	ArrayList<Tour> schoolTours = person.getListOfSchoolTours();
	            	for (int i=0; i < schoolTours.size(); i++) {
	            		tour = schoolTours.get(i); 
	            		applyIndividualModel(household, person, tour); 
	            	}                    
	            	household.setImmcRandomCount(household.getHhRandomCount());
	            }
	            else if (tourCategory.equalsIgnoreCase(ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY)) {
	            	ArrayList<Tour> tours = person.getListOfIndividualNonMandatoryTours();
	            	for ( int i=0; i < tours.size(); i++ ) {
	            		tour = tours.get(i); 
	            		applyIndividualModel(household, person, tour); 
	            	}            	
	            	household.setInmmcRandomCount(household.getHhRandomCount());
	            }
	            else if (tourCategory.equalsIgnoreCase(ModelStructure.AT_WORK_CATEGORY)) {
	            	ArrayList<Tour> tours = person.getListOfAtWorkSubtours(); 
	            	for ( int i=0; i < tours.size(); i++ ) {
	            		tour = tours.get(i); 
	            		applyIndividualModel(household, person, tour); 
	            	}            	
	            	household.setAwmcRandomCount(household.getHhRandomCount());
	            }
            }
            catch ( Exception e ) {
                logger.error( String.format( "error in individual tour mode choice model model for hhId=%d, persId=%d, persNum=%d, personType=%s.", household.getHhId(), person.getPersonId(), person.getPersonNum(), person.getPersonType() ));
                logger.error( String.format( "tour id=%d, tour orig=%d, tour dest=%d, tour purpose=%s, tour purpose index=%d.", tour.getTourId(), tour.getTourOrigTaz(), tour.getTourDestTaz(), tour.getTourPurpose(), tour.getTourPurposeIndex() ));
                throw new RuntimeException(e);
            }
        }
    	
    }
    

    private void applyJointModel(Household household, Tour tour) {
    	Person person = tour.getPersonObject(); 
    	applyIndividualModel(household, person, tour); 
    }
    
    private void applyIndividualModel(Household household, Person person, Tour tour) {
        
        // update the MC dmuObjects for this person
        mcDmuObject.setHouseholdObject(household);
        mcDmuObject.setPersonObject( person );
        mcDmuObject.setTourObject( tour );
        mcDmuObject.setDmuIndexValues( household.getHhId(), tour.getTourOrigTaz(), tour.getTourDestTaz() );
        mcDmuObject.setTourStartHour( tour.getTourStartHour() );
        mcDmuObject.setTourEndHour( tour.getTourEndHour() );
        
        float SingleTNCWaitTimeOrig = 0;
        float SingleTNCWaitTimeDest = 0;
        float SharedTNCWaitTimeOrig = 0;
        float SharedTNCWaitTimeDest = 0;
        float TaxiWaitTimeOrig = 0;
        float TaxiWaitTimeDest = 0;
        int oTaz = mcDmuObject.dmuIndex.getOriginZone();
        int dTaz = mcDmuObject.dmuIndex.getDestZone();
        float popEmpDenOrig = tazDataManager.getPopEmpPerSqMi(oTaz);
        float popEmpDenDest = tazDataManager.getPopEmpPerSqMi(dTaz);
        
        if(household!=null){
            Random hhRandom = household.getHhRandom();
            double rnum = hhRandom.nextDouble();
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSingleTNCWaitTimeDistribution(rnum, popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromSharedTNCWaitTimeDistribution(rnum, popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.sampleFromTaxiWaitTimeDistribution(rnum, popEmpDenDest);
        }else{
            SingleTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenOrig);
            SingleTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSingleTNCWaitTime( popEmpDenDest);
            SharedTNCWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenOrig);
            SharedTNCWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanSharedTNCWaitTime( popEmpDenDest);
            TaxiWaitTimeOrig = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime( popEmpDenOrig);
            TaxiWaitTimeDest = (float) tncTaxiWaitTimeCalculator.getMeanTaxiWaitTime(popEmpDenDest);
        }

        mcDmuObject.setOrigTaxiWaitTime(TaxiWaitTimeOrig);
        mcDmuObject.setDestTaxiWaitTime(TaxiWaitTimeDest);
        mcDmuObject.setOrigSingleTNCWaitTime(SingleTNCWaitTimeOrig);
        mcDmuObject.setDestSingleTNCWaitTime(SingleTNCWaitTimeDest);
        mcDmuObject.setOrigSharedTNCWaitTime(SharedTNCWaitTimeOrig);
        mcDmuObject.setDestSharedTNCWaitTime(SharedTNCWaitTimeDest);
        
        if (tourCategory.equalsIgnoreCase(ModelStructure.AT_WORK_CATEGORY)) {
        	ArrayList<Tour> workTourList = person.getListOfWorkTours();
            int workTourIndex = tour.getWorkTourIndexFromSubtourId( tour.getTourId() );
            Tour workTour = workTourList.get( workTourIndex );            
        	mcDmuObject.setWorkTourObject(workTour); 
        }

        // use the mcModel object already setup for computing logsums and get the mode choice, where the selected
        // worklocation and subzone an departure time and duration are set for this work tour.
        int chosenMode = getModeChoice ( mcDmuObject, tour.getTourPurpose() );
        tour.setTourModeChoice( chosenMode );

        if ( household.getDebugChoiceModels() ) {
        	Logger modelLogger = null; 
            if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) )
                modelLogger = tourMCManLogger;
            else
                modelLogger = tourMCNonManLogger;
            
            modelLogger.info("Chosen mode = " + chosenMode); 
            String decisionMakerLabel = String.format ( "Final Mode Choice Person Object: HH=%d, PersonNum=%d, PersonType=%s", household.getHhId(), person.getPersonNum(), person.getPersonType() );
            household.logPersonObject( decisionMakerLabel, modelLogger, person );
        }
        
    }

    public String[] getModeAltNames( int purposeIndex ) {
        int modelIndex = purposeModelIndexMap.get( tourPurposeList[purposeIndex] );
        return modeAltNames[modelIndex];
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
    return mcLsTotalTime;
    }
}

