package com.pb.models.ctramp.jppf;

import java.io.IOException;
import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.util.ObjectUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;



public class HouseholdChoiceModels implements Serializable {
    
    private transient Logger logger = Logger.getLogger("HouseholdChoiceModels");

    private boolean runAutoOwnershipModel;
    private boolean runFreeParkingAvailableModel;
    private boolean runCoordinatedDailyActivityPatternModel;
    private boolean runIndividualMandatoryTourFrequencyModel;
    private boolean runMandatoryTourModeChoiceModel;
    private boolean runMandatoryTourDepartureTimeAndDurationModel;
    private boolean runAtWorkSubtourFrequencyModel;
    private boolean runAtWorkSubtourLocationChoiceModel;
    private boolean runAtWorkSubtourModeChoiceModel;
    private boolean runAtWorkSubtourDepartureTimeAndDurationModel;
    private boolean runJointTourFrequencyModel;
    private boolean runJointTourLocationChoiceModel;
    private boolean runJointTourDepartureTimeAndDurationModel;
    private boolean runJointTourModeChoiceModel;
    private boolean runIndividualNonMandatoryTourFrequencyModel;
    private boolean runIndividualNonMandatoryTourLocationChoiceModel;
    private boolean runIndividualNonMandatoryTourModeChoiceModel;
    private boolean runIndividualNonMandatoryTourDepartureTimeAndDurationModel;
    private boolean runStopFrequencyModel;
    private boolean runStopLocationModel;
    
    private String restartModelString;
    
    private HouseholdAutoOwnershipModel aoModel;
    private HouseholdFreeParkingModel fpModel;
    private HouseholdCoordinatedDailyActivityPatternModel cdapModel;
    private HouseholdIndividualMandatoryTourFrequencyModel imtfModel;
    private TourVehicleTypeChoiceModel tvtcModel;
    private ModeChoiceModel immcModel;
    private HouseholdIndividualMandatoryTourDepartureAndDurationTime imtodModel;
    private JointTourModels jtfModel;
    private HouseholdJointDestChoiceModel jlcModel;
    private JointTourDepartureAndDurationTime jtodModel;
    private ModeChoiceModel jmcModel;
    private HouseholdIndividualNonMandatoryTourFrequencyModel inmtfModel;
    private ModeChoiceModel inmmcModel;
    private HouseholdIndNonManDestChoiceModel inmlcModel;
    private HouseholdIndividualNonMandatoryTourDepartureAndDurationTime inmtodModel;
    private HouseholdAtWorkSubtourFrequencyModel awfModel;
    private ModeChoiceModel awmcModel;
    private HouseholdSubTourDestChoiceModel awlcModel;
    private HouseholdAtWorkSubtourDepartureAndDurationTime awtodModel;
    private StopFrequencyModel stfModel;
    private StopLocationModeChoiceModel stlmcModel;
    
    private long aoTime;
    private long fpTime;
    private long cdapTime;
    private long imtfTime;
    private long imtodTime;
    private long imtmcTime;
    private long jtfTime;
    private long jtdcTime;
    private long jtodTime;
    private long jtmcTime;
    private long inmtfTime;
    private long inmtdcTime;
    private long inmtodTime;
    private long inmtmcTime;
    private long awtfTime;
    private long awtdcTime;
    private long awtodTime;
    private long awtmcTime;
    private long stfTime;
    private long stdtmTime;

    private long[][] hhTimes = new long[7][2];
    
    private int modelIndex;
    

    
    
    public HouseholdChoiceModels( int modelIndex, String restartModelString, HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) {
        this.modelIndex = modelIndex;
        this.restartModelString = restartModelString;
        
        
        try {
            setupModels( propertyMap, tazDataManager, modelStructure, dmuFactory );
        } catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

    
    private void setupModels( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) throws IOException {

        runAutoOwnershipModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_AUTO_OWNERSHIP ) );
        runFreeParkingAvailableModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_FREE_PARKING_AVAILABLE ) );
        runCoordinatedDailyActivityPatternModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_DAILY_ACTIVITY_PATTERN ) );
        
        runIndividualMandatoryTourFrequencyModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_INDIV_MANDATORY_TOUR_FREQ ) );
        runMandatoryTourDepartureTimeAndDurationModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_MAND_TOUR_DEP_TIME_AND_DUR ) );
        runMandatoryTourModeChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_MAND_TOUR_MODE_CHOICE ) );
        
        runAtWorkSubtourFrequencyModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_AT_WORK_SUBTOUR_FREQ ) );
        runAtWorkSubtourLocationChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_AT_WORK_SUBTOUR_LOCATION_CHOICE ) );
        runAtWorkSubtourDepartureTimeAndDurationModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_AT_WORK_SUBTOUR_DEP_TIME_AND_DUR ) );
        runAtWorkSubtourModeChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_AT_WORK_SUBTOUR_MODE_CHOICE ) );
        
        runJointTourFrequencyModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_JOINT_TOUR_FREQ ) );
        runJointTourLocationChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_JOINT_LOCATION_CHOICE ) );
        runJointTourDepartureTimeAndDurationModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_JOINT_TOUR_DEP_TIME_AND_DUR ) );
        runJointTourModeChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_JOINT_TOUR_MODE_CHOICE ) );
        
        runIndividualNonMandatoryTourFrequencyModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_FREQ ) );
        runIndividualNonMandatoryTourLocationChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_INDIV_NON_MANDATORY_LOCATION_CHOICE ) );
        runIndividualNonMandatoryTourDepartureTimeAndDurationModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_DEP_TIME_AND_DUR ) );
        runIndividualNonMandatoryTourModeChoiceModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_INDIV_NON_MANDATORY_TOUR_MODE_CHOICE ) );
         
        runStopFrequencyModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_STOP_FREQUENCY ) );
        runStopLocationModel = Boolean.parseBoolean( propertyMap.get( CtrampApplication.PROPERTIES_RUN_STOP_LOCATION ) );
        
        checkModelRunFlags(); 
        
        boolean measureObjectSizes = false;
        
        try {
            
            // create the auto ownership choice model application object
            if ( runAutoOwnershipModel ) {
                aoModel = new HouseholdAutoOwnershipModel( propertyMap, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "AO size:     " + ObjectUtil.checkObjectSize( aoModel ) );
            }
            
            if ( runFreeParkingAvailableModel ) {
                fpModel = new HouseholdFreeParkingModel( propertyMap, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "FP size:     " + ObjectUtil.checkObjectSize( fpModel ) );
            }
            
            if ( runCoordinatedDailyActivityPatternModel ) {
                cdapModel = new HouseholdCoordinatedDailyActivityPatternModel( propertyMap, modelStructure, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "CDAP size:   " + ObjectUtil.checkObjectSize( cdapModel ) );
            }
            
            
            if ( runIndividualMandatoryTourFrequencyModel ) {
                imtfModel = new HouseholdIndividualMandatoryTourFrequencyModel( propertyMap, tazDataManager, modelStructure, dmuFactory );
                tvtcModel = new TourVehicleTypeChoiceModel(propertyMap);
                if ( measureObjectSizes ) logger.info ( "IMTF and TVTC size:   " + (ObjectUtil.checkObjectSize( imtfModel )+ ObjectUtil.checkObjectSize( tvtcModel )) );
            }
                
            if ( runMandatoryTourModeChoiceModel || runMandatoryTourDepartureTimeAndDurationModel ){
                immcModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.MANDATORY_CATEGORY, dmuFactory, tazDataManager );
                if ( measureObjectSizes ) logger.info ( "IMMC size:   " + ObjectUtil.checkObjectSize( immcModel ) );
            }
                
            if ( runMandatoryTourDepartureTimeAndDurationModel ){
                imtodModel = new HouseholdIndividualMandatoryTourDepartureAndDurationTime( propertyMap, tazDataManager, modelStructure, dmuFactory, immcModel );
                if ( measureObjectSizes ) logger.info ( "IMTOD size:  " + ObjectUtil.checkObjectSize( imtodModel ) );
            }
            
            
            if ( runJointTourFrequencyModel ){
                jtfModel = new JointTourModels( propertyMap, modelStructure, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "JTF size:    " + ObjectUtil.checkObjectSize( jtfModel ) );
            }
                
            if ( runJointTourModeChoiceModel || runJointTourLocationChoiceModel || runJointTourDepartureTimeAndDurationModel ){
                jmcModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.JOINT_NON_MANDATORY_CATEGORY, dmuFactory,tazDataManager );
                if ( measureObjectSizes ) logger.info ( "JMC size:    " + ObjectUtil.checkObjectSize( jmcModel ) );
            }
            if ( runJointTourLocationChoiceModel ){
                //jlcModel = new HouseholdJointDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, jmcModel, jointProbabilitiesCache, jointCumProbabilitiesCache );
                jlcModel = new HouseholdJointDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, jmcModel );
                if ( measureObjectSizes ) logger.info ( "JLC size:    " + ObjectUtil.checkObjectSize( jlcModel ) );
            }
            if ( runJointTourDepartureTimeAndDurationModel ){
                jtodModel = new JointTourDepartureAndDurationTime( propertyMap, modelStructure, tazDataManager, dmuFactory, jmcModel );        
                if ( measureObjectSizes ) logger.info ( "JTOD size:   " + ObjectUtil.checkObjectSize( jtodModel ) );
            }
            
            
            if ( runIndividualNonMandatoryTourFrequencyModel ){
                inmtfModel = new HouseholdIndividualNonMandatoryTourFrequencyModel( propertyMap, modelStructure, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "INMTF size:  " + ObjectUtil.checkObjectSize( inmtfModel ) );
            }
            if ( runIndividualNonMandatoryTourModeChoiceModel || runIndividualNonMandatoryTourLocationChoiceModel || runIndividualNonMandatoryTourDepartureTimeAndDurationModel){
                inmmcModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY, dmuFactory, tazDataManager );
                if ( measureObjectSizes ) logger.info ( "INMMC size:  " + ObjectUtil.checkObjectSize( inmmcModel ) );
            }
            if ( runIndividualNonMandatoryTourLocationChoiceModel ){
                //inmlcModel = new HouseholdIndNonManDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, inmmcModel, indivNonManProbabilitiesCache, indivNonManCumProbabilitiesCache );
                inmlcModel = new HouseholdIndNonManDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, inmmcModel );
                if ( measureObjectSizes ) logger.info ( "INMLC size:  " + ObjectUtil.checkObjectSize( inmlcModel ) );
            }
            if ( runIndividualNonMandatoryTourDepartureTimeAndDurationModel ){
                inmtodModel = new HouseholdIndividualNonMandatoryTourDepartureAndDurationTime( propertyMap, modelStructure, tazDataManager, dmuFactory, inmmcModel );
                if ( measureObjectSizes ) logger.info ( "INMTOD size: " + ObjectUtil.checkObjectSize( inmtodModel ) );
            }

            
            if ( runAtWorkSubtourFrequencyModel ){
                awfModel = new HouseholdAtWorkSubtourFrequencyModel( propertyMap, modelStructure, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "AWF size:    " + ObjectUtil.checkObjectSize( awfModel ) );
            }
            if ( runAtWorkSubtourModeChoiceModel ||  runAtWorkSubtourLocationChoiceModel ||  runAtWorkSubtourDepartureTimeAndDurationModel ){
                awmcModel = new ModeChoiceModel( propertyMap, modelStructure, ModelStructure.AT_WORK_CATEGORY, dmuFactory, tazDataManager );
                if ( measureObjectSizes ) logger.info ( "AWMC size:   " + ObjectUtil.checkObjectSize( awmcModel ) );
            }
            if ( runAtWorkSubtourLocationChoiceModel ){
                //awlcModel = new HouseholdSubTourDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, awmcModel, atWorkProbabilitiesCache, atWorkCumProbabilitiesCache );
                awlcModel = new HouseholdSubTourDestChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory, awmcModel );
                if ( measureObjectSizes ) logger.info ( "AWLC size:   " + ObjectUtil.checkObjectSize( awlcModel ) );
            }
            if ( runAtWorkSubtourDepartureTimeAndDurationModel ){
                awtodModel = new HouseholdAtWorkSubtourDepartureAndDurationTime( propertyMap, modelStructure, tazDataManager, dmuFactory, awmcModel );
                if ( measureObjectSizes ) logger.info ( "AWTOD size:  " + ObjectUtil.checkObjectSize( awtodModel ) );
            }

            
            if ( runStopFrequencyModel ){
                stfModel = new StopFrequencyModel( propertyMap, modelStructure, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "STF size:    " + ObjectUtil.checkObjectSize( stfModel ) );
            }
            
            if ( runStopLocationModel ){
                stlmcModel = new StopLocationModeChoiceModel( propertyMap, modelStructure, tazDataManager, dmuFactory );
                if ( measureObjectSizes ) logger.info ( "STLMC size:  " + ObjectUtil.checkObjectSize( stlmcModel ) );
            }

        }
        catch ( RuntimeException e ) {
            
            String lastModel = "";
            if ( runAutoOwnershipModel && aoModel != null )
                lastModel += " ao";
            
            if ( runFreeParkingAvailableModel && fpModel != null )
                lastModel += " fp";
            
            if ( runCoordinatedDailyActivityPatternModel && cdapModel != null )
                lastModel += " cdap";

            if ( runIndividualMandatoryTourFrequencyModel && imtfModel != null )
                lastModel += " imtf";

            if ( runMandatoryTourDepartureTimeAndDurationModel && imtodModel != null )
                lastModel += " imtod";

            if ( runMandatoryTourModeChoiceModel && immcModel != null )
                lastModel += " immc";
                        
            if ( runJointTourFrequencyModel && jtfModel != null )
                lastModel += " jtf";

            if ( runJointTourLocationChoiceModel && jlcModel != null )
                lastModel += " jlc";

            if ( runJointTourDepartureTimeAndDurationModel && jtodModel != null )
                lastModel += " jtod";

            if ( runJointTourModeChoiceModel && jmcModel != null )
                lastModel += " jmc";
            
            if ( runIndividualNonMandatoryTourFrequencyModel && inmtfModel != null )
                lastModel += " inmtf";

            if ( runIndividualNonMandatoryTourLocationChoiceModel && inmlcModel != null )
                lastModel += " inmlc";

            if ( runIndividualNonMandatoryTourDepartureTimeAndDurationModel && inmtodModel != null )
                lastModel += " inmtod";

            if ( runIndividualNonMandatoryTourModeChoiceModel && inmmcModel != null )
                lastModel += " inmmc";
            
            if ( runAtWorkSubtourFrequencyModel && awfModel != null )
                lastModel += " awf";

            if ( runAtWorkSubtourLocationChoiceModel && awlcModel != null )
                lastModel += " awlc";

            if ( runAtWorkSubtourDepartureTimeAndDurationModel && awtodModel != null )
                lastModel += " awtod";

            if ( runAtWorkSubtourModeChoiceModel && awmcModel != null )
                lastModel += " awmc";
            
            if ( runStopFrequencyModel && stfModel != null )
                lastModel += " stf";

            if ( runStopLocationModel && stlmcModel != null )
                lastModel += " stlmc";

            logger.error( "RuntimeException setting up HouseholdChoiceModels." );
            logger.error( "Models setup = " + lastModel );
            logger.error( "", e );

            StackTraceElement[] s = e.getStackTrace();
            for(StackTraceElement ste : s){
                logger.error("\tat " + ste);
            }
            throw e;
        }
        

    }


    public void cleanUp() {
        
        if ( stlmcModel != null )
            stlmcModel.cleanUp();
    }

    
    public void zeroTimes() {
        aoTime = 0;
        fpTime = 0;
        cdapTime = 0;
        imtfTime = 0;
        imtodTime = 0;
        imtmcTime = 0;
        jtfTime = 0;
        jtdcTime = 0;
        jtodTime = 0;
        jtmcTime = 0;
        inmtfTime = 0;
        inmtdcTime = 0;
        inmtodTime = 0;
        inmtmcTime = 0;
        awtfTime = 0;
        awtdcTime = 0;
        awtodTime = 0;
        awtmcTime = 0;
        stfTime = 0;
        stdtmTime = 0;

        for (int i=0; i < hhTimes.length; i++)
            for (int j=0; j < hhTimes[i].length; j++)
                hhTimes[i][j] = 0;
    }
    
    
    public long[][] getPartialTimes() {
        return hhTimes;
    }
    
    public long[] getTimes() {
        long[] returnTimes = new long[20];
        returnTimes[0] = aoTime;
        returnTimes[1] = fpTime;
        returnTimes[2] = cdapTime;
        returnTimes[3] = imtfTime;
        returnTimes[4] = imtodTime;
        returnTimes[5] = imtmcTime;
        returnTimes[6] = jtfTime;
        returnTimes[7] = jtdcTime;
        returnTimes[8] = jtodTime;
        returnTimes[9] = jtmcTime;
        returnTimes[10] = inmtfTime;
        returnTimes[11] = inmtdcTime;
        returnTimes[12] = inmtodTime;
        returnTimes[13] = inmtmcTime;
        returnTimes[14] = awtfTime;
        returnTimes[15] = awtdcTime;
        returnTimes[16] = awtodTime;
        returnTimes[17] = awtmcTime;
        returnTimes[18] = stfTime;
        returnTimes[19] = stdtmTime;
        return returnTimes;
    }
    
    
    public void runModels( Household hhObject ) {
        
        
        // check to see if restartModel was set and reset random number sequence appropriately if so.
        checkRestartModel( hhObject );
      
        if ( runAutoOwnershipModel )
            aoModel.applyModel( hhObject );
        
        if ( runFreeParkingAvailableModel )
            fpModel.applyModel( hhObject );
        
        if ( runCoordinatedDailyActivityPatternModel )
            cdapModel.applyModel( hhObject );
        
        if ( runIndividualMandatoryTourFrequencyModel ){
            imtfModel.applyModel( hhObject );
            tvtcModel.applyModelToMandatoryTours(hhObject);
        }
        
        if ( runMandatoryTourDepartureTimeAndDurationModel )
            imtodModel.applyModel( hhObject );

        if ( runMandatoryTourModeChoiceModel )
            immcModel.applyModel( hhObject );
        
        if ( runJointTourFrequencyModel ){
            jtfModel.applyModel( hhObject );
            tvtcModel.applyModelToJointTours(hhObject);
        }
        
        if ( runJointTourLocationChoiceModel )
            jlcModel.applyModel( hhObject );
        
        if ( runJointTourDepartureTimeAndDurationModel )
            jtodModel.applyModel( hhObject );

        if ( runJointTourModeChoiceModel )
            jmcModel.applyModel( hhObject );
        
        if ( runIndividualNonMandatoryTourFrequencyModel ){
            inmtfModel.applyModel( hhObject );
            tvtcModel.applyModelToNonMandatoryTours(hhObject);
        }
        
        if ( runIndividualNonMandatoryTourLocationChoiceModel )
            inmlcModel.applyModel( hhObject );
        
        if ( runIndividualNonMandatoryTourDepartureTimeAndDurationModel )
            inmtodModel.applyModel( hhObject );

        if ( runIndividualNonMandatoryTourModeChoiceModel )
            inmmcModel.applyModel( hhObject );
        
        if ( runAtWorkSubtourFrequencyModel ){
            awfModel.applyModel( hhObject );
            tvtcModel.applyModelToAtWorkSubTours(hhObject);
        }
        
        if ( runAtWorkSubtourLocationChoiceModel )
            awlcModel.applyModel( hhObject );
        
        if ( runAtWorkSubtourDepartureTimeAndDurationModel )
            awtodModel.applyModel( hhObject );

        if ( runAtWorkSubtourModeChoiceModel )
            awmcModel.applyModel( hhObject );
        
        if ( runStopFrequencyModel )
            stfModel.applyModel( hhObject );
        
        if ( runStopLocationModel )
            stlmcModel.applyModel( hhObject );

        
        //}        
        
    }


    public void runModelsWithTiming( Household hhObject ) {
        
        
        // check to see if restartModel was set and reset random number sequence appropriately if so.
        checkRestartModel( hhObject );
      
        if ( runAutoOwnershipModel ) {
            long check = System.nanoTime();
            aoModel.applyModel( hhObject );
            aoTime += ( System.nanoTime() - check );
        }
        
        if ( runFreeParkingAvailableModel ) {
            long check = System.nanoTime();
            fpModel.applyModel( hhObject );
            fpTime += ( System.nanoTime() - check );
        }
        
        if ( runCoordinatedDailyActivityPatternModel ) {
            long check = System.nanoTime();
            cdapModel.applyModel( hhObject );
            cdapTime += ( System.nanoTime() - check );
        }
        
        if ( runIndividualMandatoryTourFrequencyModel ) {
            long check = System.nanoTime();
            imtfModel.applyModel( hhObject );
            tvtcModel.applyModelToMandatoryTours(hhObject);
            imtfTime += ( System.nanoTime() - check );
        }
        
        if ( runMandatoryTourDepartureTimeAndDurationModel ) {
            long check = System.nanoTime();
            imtodModel.applyModel( hhObject );
            imtodTime += ( System.nanoTime() - check );
        }

        if ( runMandatoryTourModeChoiceModel ) {
            long check = System.nanoTime();
            immcModel.applyModel( hhObject );
            imtmcTime += ( System.nanoTime() - check );
        }
        
        if ( runJointTourFrequencyModel ) {
            long check = System.nanoTime();
            jtfModel.applyModel( hhObject );
            tvtcModel.applyModelToJointTours(hhObject);
            jtfTime += ( System.nanoTime() - check );
        }
        
        if ( runJointTourLocationChoiceModel ) {
            long check = System.nanoTime();
            jlcModel.applyModel( hhObject );
            jtdcTime += ( System.nanoTime() - check );
        }
        
        if ( runJointTourDepartureTimeAndDurationModel ) {
            long check = System.nanoTime();
            jtodModel.applyModel( hhObject );
            jtodTime += ( System.nanoTime() - check );
        }

        if ( runJointTourModeChoiceModel ) {
            long check = System.nanoTime();
            jmcModel.applyModel( hhObject );
            jtmcTime += ( System.nanoTime() - check );
        }
        
        if ( runIndividualNonMandatoryTourFrequencyModel ) {
            long check = System.nanoTime();
            inmtfModel.applyModel( hhObject );
            tvtcModel.applyModelToNonMandatoryTours(hhObject);
            inmtfTime += ( System.nanoTime() - check );
        }
        
        if ( runIndividualNonMandatoryTourLocationChoiceModel ) {
            long check = System.nanoTime();
            inmlcModel.applyModel( hhObject );
            inmtdcTime += ( System.nanoTime() - check );
        }
        
        if ( runIndividualNonMandatoryTourDepartureTimeAndDurationModel ) {
            long check = System.nanoTime();
            inmtodModel.applyModel( hhObject );
            inmtodTime += ( System.nanoTime() - check );
        }

        if ( runIndividualNonMandatoryTourModeChoiceModel ) {
            long check = System.nanoTime();
            inmmcModel.applyModel( hhObject );
            inmtmcTime += ( System.nanoTime() - check );
        }
        
        if ( runAtWorkSubtourFrequencyModel ) {
            long check = System.nanoTime();
            awfModel.applyModel( hhObject );
            tvtcModel.applyModelToAtWorkSubTours(hhObject);
            awtfTime += ( System.nanoTime() - check );
        }
        
        if ( runAtWorkSubtourLocationChoiceModel ) {
            long check = System.nanoTime();
            awlcModel.applyModel( hhObject );
            awtdcTime += ( System.nanoTime() - check );
        }
        
        if ( runAtWorkSubtourDepartureTimeAndDurationModel ) {
            long check = System.nanoTime();
            awtodModel.applyModel( hhObject );
            awtodTime += ( System.nanoTime() - check );
        }

        if ( runAtWorkSubtourModeChoiceModel ) {
            long check = System.nanoTime();
            awmcModel.applyModel( hhObject );
            awtmcTime += ( System.nanoTime() - check );
        }
        
        if ( runStopFrequencyModel ) {
            long check = System.nanoTime();
            stfModel.applyModel( hhObject );
            stfTime += ( System.nanoTime() - check );
        }
        
        if ( runStopLocationModel ) {
            long check = System.nanoTime();
            stlmcModel.applyModel( hhObject );
            long[][] partialTimes = stlmcModel.getHhTimes();
            for (int i=0; i < partialTimes.length; i++)
                for (int j=0; j < partialTimes[i].length; j++)
                    hhTimes[i][j] += partialTimes[i][j];
            stdtmTime += ( System.nanoTime() - check );
        }

        
        //}        
        
    }


    private void checkRestartModel( Household hhObject ) {
        
        // version 1.0.8.22 - changed model restart options - possible values for restart are now: none, ao, imtf, immc, jtf, jmc, inmtf, inmmc, awf, awmc, stf
        
        
        // if restartModel was specified, reset the random number sequence
        // based on the cumulative count of random numbers drawn by the component preceding the one specified.
        if ( restartModelString.equalsIgnoreCase("") || restartModelString.equalsIgnoreCase("none") )
            return;
        else if ( restartModelString.equalsIgnoreCase("ao")) {
            hhObject.initializeForAoRestart();
        }
        else if ( restartModelString.equalsIgnoreCase("imtf")) {
            hhObject.initializeForImtfRestart();
        }
        else if ( restartModelString.equalsIgnoreCase("immc")) {
            hhObject.initializeForImmcRestart(runJointTourFrequencyModel, runIndividualNonMandatoryTourFrequencyModel, runAtWorkSubtourFrequencyModel); 
        }
        else if ( restartModelString.equalsIgnoreCase("jtf")) {
            hhObject.initializeForJtfRestart();
        }
        else if ( restartModelString.equalsIgnoreCase("jmc")) {
            hhObject.initializeForJmcRestart(runIndividualNonMandatoryTourFrequencyModel, runAtWorkSubtourFrequencyModel); 
        }
        else if ( restartModelString.equalsIgnoreCase("inmtf")) {
            hhObject.initializeForInmtfRestart();
        }
        else if ( restartModelString.equalsIgnoreCase("inmmc")) {
            hhObject.initializeForInmmcRestart(runAtWorkSubtourFrequencyModel); 
        }
        else if ( restartModelString.equalsIgnoreCase("awf")) {
            hhObject.initializeForAwfRestart();
        }
        else if ( restartModelString.equalsIgnoreCase("awmc")) {
            hhObject.initializeForAwmcRestart(); 
        }
        else if ( restartModelString.equalsIgnoreCase("stf")) {
            hhObject.initializeForStfRestart();
        }
        else {
        	throw new RuntimeException("Cannot restart model from " + restartModelString + ".  Must be one of: none, ao, imtf, jtf, inmtf, awf, stf."); 
        }
    
    }

    private void checkModelRunFlags() {
        
    	if (runMandatoryTourDepartureTimeAndDurationModel) {
    		if (!runIndividualMandatoryTourFrequencyModel) {
    			throw new RuntimeException("If running runMandatoryTourDepartureTimeAndDurationModel, runIndividualMandatoryTourFrequencyModel must also be true."); 
    		}
    	}

    	if (runJointTourDepartureTimeAndDurationModel) {
    		if (!runJointTourFrequencyModel) {
    			throw new RuntimeException("If running jointTourDepartureTimeAndDurationModel, jointTourFrequencyModel must also be true."); 
    		}
    		if (!runJointTourLocationChoiceModel) {
    			throw new RuntimeException("If running jointTourDepartureTimeAndDurationModel, jointTourLocationModel must also be true."); 
    		}
    	}

    	if (runJointTourLocationChoiceModel) {
    		if (!runJointTourFrequencyModel) {
    			throw new RuntimeException("If running jointTourLocationChoiceModel, jointTourFrequencyModel must also be true."); 
    		}
    	}
    	
    	if (runIndividualNonMandatoryTourDepartureTimeAndDurationModel) {
    		if (!runIndividualNonMandatoryTourFrequencyModel) {
    			throw new RuntimeException("If running individualNonMandatoryTourDepartureTimeAndDurationModel, individualNonMandatoryTourFrequencyModel must also be true."); 
    		}
    		if (!runIndividualNonMandatoryTourLocationChoiceModel) {
    			throw new RuntimeException("If running individualNonMandatoryTourDepartureTimeAndDurationModel, individualNonMandatoryTourLocationModel must also be true."); 
    		}
    	}

    	if (runIndividualNonMandatoryTourLocationChoiceModel) {
    		if (!runIndividualNonMandatoryTourFrequencyModel) {
    			throw new RuntimeException("If running individualNonMandatoryLocationChoiceModel, individualNonMandatoryTourFrequencyModel must also be true."); 
    		}
     	}

    	if (runAtWorkSubtourDepartureTimeAndDurationModel) {
    		if (!runAtWorkSubtourFrequencyModel) {
    			throw new RuntimeException("If running atWorkSubtourDepartureTimeAndDurationModel, atWorkSubtourFrequencyModel must also be true."); 
    		}
    		if (!runAtWorkSubtourLocationChoiceModel) {
    			throw new RuntimeException("If running atWorkSubtourDepartureTimeAndDurationModel, atWorkSubtourLocationModel must also be true."); 
    		}
    	}

    	if (runAtWorkSubtourLocationChoiceModel) {
    		if (!runAtWorkSubtourFrequencyModel) {
    			throw new RuntimeException("If running atWorkSubtourLocationChoiceModel, atWorkSubtourFrequencyModel must also be true."); 
    		}
    	}
    }
    
    public int getModelIndex(){
        return modelIndex;
    }

}
