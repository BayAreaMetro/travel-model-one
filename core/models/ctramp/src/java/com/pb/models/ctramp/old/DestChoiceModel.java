package com.pb.models.ctramp.old;

import java.util.MissingResourceException;
import java.util.Random;
import java.util.ArrayList;
import java.util.HashMap;

import com.pb.common.model.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.DestChoiceDMU;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;


import org.apache.log4j.Logger;

public class DestChoiceModel {

    public static Logger logger = Logger.getLogger(DestChoiceModel.class);
    protected static Logger traceLogger =  Logger.getLogger("trace");

    // TODO eventually remove this target
    String dcControlFileTarget = "dcUEC.file";
    static final int DC_DATA_SHEET = 0;

    // The following arrays are static so that only one instance of them exists that multiple threads share.
    
    // These arrays are used as sample of alternatives probabilities and cumulative probabilities caches.
    // The DC alternative probabilities are computed and stored by purpose, segment, and origin zone, by whichever thread
    // needs them first, then used/re-used by any thread that needs them thereafter.  The cache is flushed
    // prior to each shadow price iteration so that new sample of alternatives probabilities get computed
    // each iteration.
    private static double[][][] probabilitiesCache = null;
    private static double[][][] cumProbabilitiesCache = null;

    static final int DEFAULT_AM_HOUR = 8;
    static final int DEFAULT_PM_HOUR = 16;
    

    String tourCategory;
    ModelStructure modelStructure;
    String[] tourPurposeList;
    HashMap<String,Integer> tourPurposeIndexMap;
    
    ModeChoiceModel mcModel;
    DestinationSampleOfAlternativesModel dcSoaModel;

    // A MyChoiceModelApplication object and modeAltsAvailable[] is needed for each purpose
    ChoiceModelApplication dcModel[];
    DcSoaDMU dcSoaDmuObject;
    DestChoiceDMU dcDmuObject;
    ModeChoiceDMU mcDmuObject;

    private boolean runWorkTours;
    private boolean runUnivTours;
    private boolean runSchoolTours;
    
    boolean[][] destAltsAvailable;
    int[][] destAltsSample;

    private int numberOfSubzones;
    private int numberOfZones;

    double[][][] modeledDestinationLocationsByDestZone;



    public DestChoiceModel( HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj,
            String destChoiceUecFileName, String soaUecFile, int soaSampleSize, String modeChoiceUecFile, CtrampDmuFactoryIf dmuFactory ){

    	// set the model structure and the tour purpose list
    	this.modelStructure = modelStructure;
        this.tourCategory = tourCategory;

        dcDmuObject = dmuFactory.getDestChoiceDMU();
        mcDmuObject = dmuFactory.getModeChoiceDMU();
        dcDmuObject.setDestChoiceSize( dcSizeObj );

        tourPurposeList = modelStructure.getDcModelPurposeList( this.tourCategory );
        tourPurposeIndexMap = new HashMap<String,Integer>();

        numberOfZones = tazDataManager.getNumberOfZones();
        numberOfSubzones = tazDataManager.getNumberOfSubZones();

        // create an array of MyChoiceModelApplication objects for each choice purpose
    	setupChoiceModelApplicationArray( destChoiceUecFileName, propertyMap );
    	
    	// create the destination sample of alternatives model
    	dcSoaModel = new DestinationSampleOfAlternativesModel( soaUecFile, soaSampleSize, propertyMap,
    			modelStructure, tourCategory, tazDataManager, probabilitiesCache, cumProbabilitiesCache, dcSizeObj, dmuFactory );
    	
    	// create the mode choice model
    	mcModel = new ModeChoiceModel( modeChoiceUecFile, propertyMap, modelStructure,  mcDmuObject, tourCategory );
    	

    	// these flags are useful in calibration to limit the number of usual work and school location choices made
    	// to speed up calibration model runs.
        if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) ) {
            try {
                runWorkTours = propertyMap.get( UsualWorkSchoolLocationChoiceModel.PROPERTIES_MANDATORY_RUN_WORK ).equalsIgnoreCase("true");
            }
            catch (MissingResourceException e){
                runWorkTours = false;
            }

            try {
                runUnivTours = propertyMap.get( UsualWorkSchoolLocationChoiceModel.PROPERTIES_MANDATORY_RUN_UNIVERSITY ).equalsIgnoreCase("true");
            }
            catch (MissingResourceException e){
                runUnivTours = false;
            }

            try {
                runSchoolTours = propertyMap.get( UsualWorkSchoolLocationChoiceModel.PROPERTIES_MANDATORY_RUN_SCHOOL ).equalsIgnoreCase("true");
            }
            catch (MissingResourceException e){
                runSchoolTours = false;
            }

        }    	
    }



    // same as above method with tazDataManager
    private void setupChoiceModelApplicationArray( String destChoiceUecFileName, HashMap<String, String>propertyMap ) {

        // get the number of purposes and declare the array dimension to be this size.
        int numPurposes = tourPurposeList.length;
        dcModel = new ChoiceModelApplication[numPurposes];

        // declare dimensions for the array of choice alternative availability by purpose and
        // set elements to true.
        destAltsAvailable = new boolean[numPurposes][];
        destAltsSample = new int[numPurposes][];

        // declare dimensions for the arrays of destination choice sample of alternative probabilities by purpose.
        probabilitiesCache = new double[numPurposes][][];
        cumProbabilitiesCache = new double[numPurposes][][];
        
        
        // for each purpose, create the MyChoiceModelApplication object and the availabilty array
        for (int p=0;p<tourPurposeList.length;++p) {

            // map the purpose strings for this tourCategory to indices used to reference choice models and results arrays
            tourPurposeIndexMap.put( tourPurposeList[p], p);

            // get the uec worksheet index
        	int uecWorkSheetIndex = modelStructure.getDcUecIndexForPurpose( tourPurposeList[p] );
        	
            dcModel[p] = new ChoiceModelApplication ( destChoiceUecFileName, uecWorkSheetIndex, DC_DATA_SHEET, propertyMap, dcDmuObject.getClass() );

            int numAlts = dcModel[p].getNumberOfAlternatives();
            destAltsAvailable[p] = new boolean[numAlts+1];
            destAltsSample[p] = new int[numAlts+1];
            
            // declare dimensions for the arrays of destination choice sample of alternative probabilities by purpose and segment.
            probabilitiesCache[p] = new double[numberOfZones+1][];
            cumProbabilitiesCache[p] = new double[numberOfZones+1][];
            
        }

        // dimension an array in which to accumulate chosen long term model choices for use in shadow price adjustments
        modeledDestinationLocationsByDestZone = new double[tourPurposeList.length][][];
        for (int p=0;p<tourPurposeList.length;++p)
            modeledDestinationLocationsByDestZone[p] = new double[numberOfZones+1][numberOfSubzones];


     
    }


    public void applyDestinationChoiceForHousehold ( Household hh ) {
        
        // declare these variables here so their values can be logged if a RuntimeException occurs.
        int i = -1;
        int hhId = -1;
        int purposeIndex = -1;
        String purposeName = "";


        try {
            
            hhId = hh.getHhId();

            
            if ( tourCategory.equalsIgnoreCase( ModelStructure.MANDATORY_CATEGORY ) ) {

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



                    int choiceNum = 0;
                    for ( String dcPurposeName : dcPurposeList ) {

                        purposeName = dcPurposeName;
                        purposeIndex = modelStructure.getDcModelPurposeIndex( purposeName );

                        int chosen = selectDestinationAlternative( p, purposeName, purposeIndex, ++choiceNum );

                        // get zone, subzone from DC alternative
                        int chosenDestAlt = (chosen-1)/numberOfSubzones + 1;
                        int chosenShrtWlk = chosen - (chosenDestAlt-1)*numberOfSubzones - 1;

//                        int dummy = 0;
//                        if ( purposeIndex > 6 ) {
//                            System.out.println( String.format("hhid=%d, persNum=%d, purposeIndex=%d, purposeName=%s, chosen=%d", hh.getHhId(), p.getPersonNum(), purposeIndex, purposeName, chosen) );
//                        }
                        
                        // save selected zone, subzone by purpose, segment for later use in shadow pricing adjustments
                        modeledDestinationLocationsByDestZone[purposeIndex][chosenDestAlt][chosenShrtWlk]++;

                        // set chosen values in tour object
                        if ( modelStructure.getDcModelPurposeIsWorkPurpose( purposeName ) ) {
                            p.setWorkLoc( chosenDestAlt );
                            p.setWorkLocSubzone( chosenShrtWlk );
                        }
                        else {
                            p.setSchoolLoc( chosenDestAlt );
                            p.setSchoolLocSubzone( chosenShrtWlk );
                        }

                    }

                }

            }
            else if ( tourCategory.equalsIgnoreCase( ModelStructure.JOINT_NON_MANDATORY_CATEGORY ) ) {

                Tour[] jt = hh.getJointTourArray();
                if ( jt == null )
                    return;

                int choiceNum = 0;
                for ( i=0; i < jt.length; i++ ) {

                    Tour t = jt[i];

                    purposeName = t.getTourPurpose();
                    purposeIndex = tourPurposeIndexMap.get( purposeName );

                    byte[] personsInTour = t.getPersonNumArray();
                    int personNum = personsInTour[0];
                    Person p = hh.getPersons()[personNum];

                    int chosen = selectDestinationAlternative( t, p, purposeName, purposeIndex, ++choiceNum );

                    // get zone, subzone from DC alternative
                    int chosenDestAlt = (chosen-1)/numberOfSubzones + 1;
                    int chosenShrtWlk = chosen - (chosenDestAlt-1)*numberOfSubzones - 1;

                    // save selected zone, subzone by purpose, segment for later use in shadow pricing adjustments
                    modeledDestinationLocationsByDestZone[purposeIndex][chosenDestAlt][chosenShrtWlk]++;

                    t.setTourDestTaz( chosenDestAlt );
                    t.setTourDestWalkSubzone( chosenShrtWlk );

                }

            }
            else if ( tourCategory.equalsIgnoreCase( ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY ) ) {

                Person[] persons = hh.getPersons();

                for ( i=1; i < persons.length; i++ ) {

                    Person p = persons[i];

                    // get the individual non-mandatory tours for this person and choose a destination for each.
                    int choiceNum = 0;
                    ArrayList<Tour> tourList = p.getListOfIndividualNonMandatoryTours();
                    for ( Tour tour : tourList ) {

                        purposeName = tour.getTourPurpose();
                        purposeIndex = tour.getTourPurposeIndex();

                        int chosen = selectDestinationAlternative( tour, p, purposeName, purposeIndex, ++choiceNum );

                        // get zone, subzone from DC alternative
                        int chosenDestAlt = (chosen-1)/numberOfSubzones + 1;
                        int chosenShrtWlk = chosen - (chosenDestAlt-1)*numberOfSubzones - 1;

                        // save selected zone, subzone by purpose, segment for later use in shadow pricing adjustments
                        modeledDestinationLocationsByDestZone[purposeIndex][chosenDestAlt][chosenShrtWlk]++;

                        // set chosen values in tour object
                        tour.setTourDestTaz( chosenDestAlt );
                        tour.setTourDestWalkSubzone( chosenShrtWlk );

                    }

                }

            }
            else if ( tourCategory.equalsIgnoreCase( ModelStructure.AT_WORK_CATEGORY ) ) {

                Person[] persons = hh.getPersons();

                for ( i=1; i < persons.length; i++ ) {

                    Person p = persons[i];

                    // get the individual non-mandatory tours for this person and choose a destination for each.
                    int choiceNum = 0;
                    ArrayList<Tour> tourList = p.getListOfAtWorkSubtours();
                    for ( Tour tour : tourList ) {

                        purposeName = tour.getTourPurpose();
                        purposeIndex = tour.getTourPurposeIndex();
                        
                        //at-work tour category purposes are stored as 1,2,3, so subtract 1 as the model array indices are 0 based.
                        purposeIndex --;

                        int chosen = selectDestinationAlternative( tour, p, purposeName, purposeIndex, ++choiceNum );

                        // get zone, subzone from DC alternative
                        int chosenDestAlt = (chosen-1)/numberOfSubzones + 1;
                        int chosenShrtWlk = chosen - (chosenDestAlt-1)*numberOfSubzones - 1;

                        // save selected zone, subzone by purpose, segment for later use in shadow pricing adjustments
                        modeledDestinationLocationsByDestZone[purposeIndex][chosenDestAlt][chosenShrtWlk]++;

                        // set chosen values in tour object
                        tour.setTourDestTaz( chosenDestAlt );
                        tour.setTourDestWalkSubzone( chosenShrtWlk );

                    }

                }

            }


        
        }
        catch (RuntimeException e) {
            logger.fatal( String.format("exception caught for hh.hhid=%d, person i=%d, in %s choice, purposeIndex=%d, purposeName=%s", hhId, i, tourCategory, purposeIndex, purposeName ) );
            throw e;
        }

    }


    /**
     * This method is used for usual work and school location choice, when no tour object has yet been created.
     * @param person
     * @param purposeName
     * @param purposeIndex
     * @return DC alternative chosen
     */
    private int selectDestinationAlternative( Person person, String purposeName, int purposeIndex, int choiceNum ) {

        // update the MC and DC dmuObjects in those respective models for this person
        mcModel.setPersonObjectForDmu ( person, purposeName );
        setPersonObjectForDmu ( null, person );

        // compute the sample of alternatives set for the person
        dcSoaModel.computeDestinationSampleOfAlternatives( null, person, purposeName, purposeIndex );

        // get sample of locations and correction factors for sample
        int[] sample = dcSoaModel.getSampleOfAlternatives();
        float[] corrections = dcSoaModel.getSampleOfAlternativesCorrections();


        // get the work location alternative chosen from the sample
        return selectLocationFromSampleOfAlternatives( null, person, sample, corrections, purposeName, purposeIndex, choiceNum );

    }



    /**
     * This method is used for non-mandatory location choice(joint, individual, and work-based subtours), when tour objects have been created.
     * @param person
     * @param purposeName
     * @param purposeIndex
     * @return DC alternative chosen
     */
    public int selectDestinationAlternative( Tour tour, Person person, String purposeName, int purposeIndex, int choiceNum ) {

        // update the MC and DC dmuObjects in those respective models for this person
        mcModel.setPersonObjectForDmu ( tour, person, purposeName );
        setPersonObjectForDmu ( tour, person );

        // compute the sample of alternatives set for the person
        dcSoaModel.computeDestinationSampleOfAlternatives( tour, person, purposeName, purposeIndex );

        // get sample of locations and correction factors for sample
        int[] sample = dcSoaModel.getSampleOfAlternatives();
        float[] corrections = dcSoaModel.getSampleOfAlternativesCorrections();


        // get the work location alternative chosen from the sample
        return selectLocationFromSampleOfAlternatives( tour, person, sample, corrections, purposeName, purposeIndex, choiceNum );

    }



    private int selectLocationFromSampleOfAlternatives( Tour tour, Person person, int[] finalSample, float[] sampleCorrectionFactors, String purposeName, int purposeIndex, int choiceNum ) {
        
        int numAlts = dcModel[purposeIndex].getNumberOfAlternatives();

        // set the destAltsAvailable array to true for all destination choice alternatives for each purpose
        for (int k=1; k <= numAlts; k++)
                destAltsAvailable[purposeIndex][k] = false;

        // set the destAltsSample array to 1 for all destination choice alternatives for each purpose
        for (int k=1; k <= numAlts; k++)
                destAltsSample[purposeIndex][k] = 0;

        
        int logsumIndex = modelStructure.getSkimPeriodCombinationIndex( DEFAULT_AM_HOUR, DEFAULT_PM_HOUR );
        
        // for the destinations and sub-zones in the sample, compute mc logsums and save in DC dmuObject.
        // also save correction factor and set availability and sample value for the sample alternative to true. 1, respectively.
        for (int i=1; i < finalSample.length; i++) {

            int d = (finalSample[i]-1)/numberOfSubzones + 1;
            int w = finalSample[i] - (d-1)*numberOfSubzones - 1;
            
            // get the mode choice logsum for the destination choice sample alternative
            double logsum = mcModel.getModeChoiceLogsum( purposeIndex, d, w, DEFAULT_AM_HOUR, DEFAULT_PM_HOUR );
            
            // set logsum value in DC dmuObject for the sampled zone and subzone - for this long term choice model, set the AmPm logsum value.
            dcDmuObject.setMcLogsum ( logsumIndex, d, w, logsum );
        
            // set sample of alternatives correction factor used in destination choice utility for the sampled alternative.
            setDcSoaCorrections( d, w, sampleCorrectionFactors[i] );

            // set availaibility and sample values for the purpose, dcAlt.
            setAvailability( purposeIndex, finalSample[i] );

        }


        // apply choice model to get selected DC alternative.
        return getDestinationAlternative( tour, person, purposeName, purposeIndex, choiceNum );

    }
    

    

    public void setPersonObjectForDmu ( Tour tour, Person person ) {

        Household hhObj = person.getHouseholdObject();

        // update the MC and DC dmuObjects for this person
        dcDmuObject.setHouseholdObject( hhObj );
        dcDmuObject.setPersonObject( person );
        dcDmuObject.setTourObject(tour);
        
        int origTaz = -1;
        int homeTaz = hhObj.getHhTaz();
        if ( tour == null )
            origTaz = homeTaz;
        else
            origTaz = tour.getTourOrigTaz();
        
        dcDmuObject.setDmuIndexValues( hhObj.getHhId(), homeTaz, origTaz, 0 );

    }



    // sample of alternatibes correction factors used in destination choice utility
    public void setDcSoaCorrections( int dest, int subZone, double correction ) {
        dcDmuObject.setDcSoaCorrections( dest, subZone, correction );
    }

    public void setAvailability( int purpose, int dcAlt ) {
        destAltsAvailable[purpose][dcAlt] = true;
        destAltsSample[purpose][dcAlt] = 1;
    }

    private int getDestinationAlternative( Tour tour, Person person, String purposeName, int purposeIndex, int choiceNum ) {

        // log headers to traceLogger if the person making the destination choice is from a household requesting trace information
        if ( person.getHouseholdObject().getDebugChoiceModels() ) {
            String choiceModelDescription = "";
            String decisionMakerLabel = "";

            if ( tour == null ) {
                // null tour means the DC is a mandatory usual location choice
                choiceModelDescription = String.format ( "Usual Location Choice Model for: Category=%s, Purpose=%s, PersonChoiceNum=%d", tourCategory, purposeName, choiceNum );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            else {
                choiceModelDescription = String.format ( "Destination Choice Model for: Category=%s, Purpose=%s, TourId=%d", tourCategory, purposeName, tour.getTourId() );
                decisionMakerLabel = String.format ( "HH=%d, PersonNum=%d, PersonType=%s", person.getHouseholdObject().getHhId(), person.getPersonNum(), person.getPersonType() );
            }
            
            dcModel[purposeIndex].choiceModelUtilityTraceLoggerHeading( choiceModelDescription, decisionMakerLabel );
        }

        
        // compute destination choice proportions and choose alternative
        dcModel[purposeIndex].computeUtilities ( dcDmuObject, dcDmuObject.getDmuIndexValues(), destAltsAvailable[purposeIndex], destAltsSample[purposeIndex] );
        
        Random hhRandom = dcDmuObject.getHouseholdObject().getHhRandom();
        double rn = hhRandom.nextDouble();
        
        // if the choice model has at least one available alternative, make choice.
        int chosen = -1;
        if ( dcModel[purposeIndex].getAvailabilityCount() > 0 )
            chosen = dcModel[purposeIndex].getChoiceResult( rn );
        else {
            logger.error ( String.format( "Exception caught for HHID=%d, PersonNum=%d, no available %s destination choice alternatives to choose from in choiceModelApplication.", dcDmuObject.getHouseholdObject().getHhId(), dcDmuObject.getPersonObject().getPersonNum(), purposeName ) );
            throw new RuntimeException();
        }
        
        
        // write choice model alternative info to log file
        if ( dcDmuObject.getHouseholdObject().getDebugChoiceModels() ) {
            dcModel[purposeIndex].logAlternativesInfo ( "Destination Choice", String.format("HH_%d, PERS_%d", dcDmuObject.getHouseholdObject().getHhId(), dcDmuObject.person.getPersonNum()) );
            dcModel[purposeIndex].logSelectionInfo ( "Destination Choice", String.format("HH_%d, PERS_%d", dcDmuObject.getHouseholdObject().getHhId(), dcDmuObject.person.getPersonNum()), rn, chosen );
        }
        

        return chosen;

    }


    
    
    /** 
     * get array dimensioned to purpose, numZones, numSubZones of the number of locations chosen for the segment.
     * @return modeledDestinationLocationsByDestZone, number of destination choice alternatives chosen by purpose, segment
     */
    public double[][][] getModeledDestinationLocationsByDestZone() {
        return modeledDestinationLocationsByDestZone;
    }


    /**
     * zero out the array used by this DestChoiceModel instance to accumulate choices made by households
     * applied in this instance.
     * 
     */
    public void zeroModeledDestinationLocationsByDestZoneArray() {
        
        int sum = 0;
        for (int p=0; p < modeledDestinationLocationsByDestZone.length; p++) {
            for (int i=0; i < modeledDestinationLocationsByDestZone[p].length; i++) {
                for (int j=0; j < modeledDestinationLocationsByDestZone[p][i].length; j++) {
                    sum += modeledDestinationLocationsByDestZone[p][i][j];
                    modeledDestinationLocationsByDestZone[p][i][j] = 0.0;
                }
            }
        }
        
    }


}