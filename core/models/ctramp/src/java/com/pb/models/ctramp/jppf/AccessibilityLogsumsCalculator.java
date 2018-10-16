package com.pb.models.ctramp.jppf;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.apache.log4j.Logger;
import org.jppf.JPPFException;
import org.jppf.client.JPPFClient;
import org.jppf.client.JPPFJob;
import org.jppf.server.protocol.JPPFTask;
import org.jppf.task.storage.DataProvider;
import org.jppf.task.storage.MemoryMapDataProvider;
import com.pb.common.newmodel.UtilityExpressionCalculator;
import com.pb.common.calculator.IndexValues;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.Tracer;
import com.pb.models.ctramp.AccConstantsDMU;
import com.pb.models.ctramp.AccessibilityDMU;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Util;


public class AccessibilityLogsumsCalculator implements Callable<List<Object>>, Serializable
{

    private static transient Logger logger = Logger.getLogger(AccessibilityLogsumsCalculator.class);

    private static String PROJECT_UEC_FOLDER_PROPERTY_KEY = "uec.folder";

    private static final String ACC_NUM_THREADS = "num.acc.threads";
    private static final String ACC_JPPF_PACKET_SIZE = "num.acc.tazs.in.jppf.packets";
    
    private static final String ACC_UEC_FILE_CONSTANTS_PROPERTY_KEY =                                   "acc.uec.constants.file";
    private static final String ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_WORK_PAGE_PROPERTY_KEY =        "acc.uec.work.constants.utility.page";
    private static final String ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_OTHMAINT_PAGE_PROPERTY_KEY =    "acc.uec.othMaint.constants.utility.page";
    private static final String ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_DATA_PAGE_PROPERTY_KEY =        "acc.uec.constants.data.page";

    private static final String ACC_UEC_FILE_KEY =                                                      "acc.uec.utility.file";

    private static final String ACC_UEC_FILE_MANDATORY_DATA_PAGE_PROPERTY_KEY =                         "acc.uec.mandatory.data.page";
    private static final String ACC_UEC_FILE_MANDATORY_ACCESSIBILITIES_UTILITY_PAGE_PROPERTY_KEY =      "acc.uec.mandatory.utility.page";
    private static final String ACC_UEC_FILE_SOV_PK_UTILITY_PAGE_PROPERTY_KEY =                         "acc.sov.peak.page";
    private static final String ACC_UEC_FILE_HOV_PK_UTILITY_PAGE_PROPERTY_KEY =                         "acc.hov.peak.page";
    private static final String ACC_UEC_FILE_WALK_TRANSIT_PK_UTILITY_PAGE_PROPERTY_KEY =                "acc.wt.peak.page";
    private static final String ACC_UEC_FILE_DRIVE_TRANSIT_PK_UTILITY_PAGE_PROPERTY_KEY =               "acc.dt.peak.page";

    private static final String ACC_UEC_FILE_NON_MANDATORY_DATA_PAGE_PROPERTY_KEY =                     "acc.uec.nonmandatory.data.page";
    private static final String ACC_UEC_FILE_NON_MANDATORY_ACCESSIBILITIES_UTILITY_PAGE_PROPERTY_KEY =  "acc.uec.nonmandatory.utility.page";
    private static final String ACC_UEC_FILE_NON_MOTOR_OP_UTILITY_PAGE_PROPERTY_KEY =                   "acc.nm.offpeak.page";
    private static final String ACC_UEC_FILE_SOV_OP_UTILITY_PAGE_PROPERTY_KEY =                         "acc.sov.offpeak.page";
    private static final String ACC_UEC_FILE_HOV_OP_UTILITY_PAGE_PROPERTY_KEY =                         "acc.hov.offpeak.page";
    private static final String ACC_UEC_FILE_WALK_TRANSIT_OP_UTILITY_PAGE_PROPERTY_KEY =                "acc.wt.offpeak.page";
    private static final String ACC_UEC_FILE_DRIVE_TRANSIT_OP_UTILITY_PAGE_PROPERTY_KEY =               "acc.dt.offpeak.page";

    private static final String ACC_UEC_VALUE_OF_TIME_LOW = "acc.low.value.of.time";
    private static final String ACC_UEC_VALUE_OF_TIME_MED = "acc.med.value.of.time";
    private static final String ACC_UEC_VALUE_OF_TIME_HIGH = "acc.high.value.of.time";
    private static final String ACC_UEC_VALUE_OF_TIME_VERYHIGH = "acc.veryhigh.value.of.time";

    private static final String ACC_TRACE_OD_UTILITY_PROPERTY_KEY = "acc.trace.flag";
    private static final String ACC_TRACE_OD_UTILITY_ORIG_PROPERTY_KEY = "acc.trace.orig";
    private static final String ACC_TRACE_OD_UTILITY_DEST_PROPERTY_KEY = "acc.trace.dest";

    public static final String OFF_PEAK_PERIOD_STRING = "peak";
    public static final String PEAK_PERIOD_STRING = "offpeak";
    
    private static final int NUM_PERIODS = 2;
    private static final int PEAK_INDEX = 0;
    private static final int OFF_PEAK_INDEX = 1;

    private static final int LOGSUM_0_AUTO = 0;
    private static final int LOGSUM_AUTOS_LT_WORKERS = 1;
    private static final int LOGSUM_AUTOS_GE_WORKERS = 2;
    
    private double[] incomeSegmentVOTs;
        

//    private int testAlts = -1;
    
    private int maxTaz;
    private int numDcAlts;
    private int numberOfSubzones;    
    
    private boolean trace;
    private int[] traceOtaz;
    private int[] traceDtaz;
    private Tracer tracer;

    private transient DestChoiceSize[] dcSizeObj;
    
    private CtrampDmuFactoryIf dmuFactory;
    private TazDataIf tazDataHandler;
    
    private String[] incomeSegments;
    private String[] autoSufficiencySegments;
    
    private int numAccessibilityThreads;
    private int numOrigsPerJppfTask;
    private boolean useJppf;
    private boolean multiThreaded;
    
    
    // period/purpose segments - work and othMaint
    // auto sufficiency (0 autos, autos<workers, autos>=workers),
    // and mode (SOV,HOV,Walk-Transit,Non-Motorized)
    private double[][][] expConstants;
    
    private HashMap<String,String> propertyMap;
    
    
    
    public AccessibilityLogsumsCalculator( HashMap<String,String> propertyMap, CtrampDmuFactoryIf dmuFactory, TazDataIf tazDataHandler, DestChoiceSize[] dcSizeObj,
            String[] incomeSegments, String[] autoSufficiencySegments ) 
    {
        this.propertyMap = propertyMap;
        this.dcSizeObj = dcSizeObj;
        this.dmuFactory = dmuFactory;
        this.tazDataHandler = tazDataHandler;
        this.incomeSegments = incomeSegments;
        this.autoSufficiencySegments = autoSufficiencySegments;

        
        maxTaz = tazDataHandler.getNumberOfZones();
        numberOfSubzones = tazDataHandler.getNumberOfSubZones();
        numDcAlts = maxTaz * numberOfSubzones;

        incomeSegmentVOTs = new double[4];
        
        incomeSegmentVOTs[0] = Double.parseDouble( propertyMap.get( ACC_UEC_VALUE_OF_TIME_LOW ) );
        incomeSegmentVOTs[1] = Double.parseDouble( propertyMap.get( ACC_UEC_VALUE_OF_TIME_MED ) );
        incomeSegmentVOTs[2] = Double.parseDouble( propertyMap.get( ACC_UEC_VALUE_OF_TIME_HIGH ) );
        incomeSegmentVOTs[3] = Double.parseDouble( propertyMap.get( ACC_UEC_VALUE_OF_TIME_VERYHIGH ) );

        numAccessibilityThreads = Integer.parseInt( propertyMap.get( ACC_NUM_THREADS ) );
        numOrigsPerJppfTask = Integer.parseInt( propertyMap.get( ACC_JPPF_PACKET_SIZE ) );

        expConstants = new double[NUM_PERIODS][][];
        
        if ( numOrigsPerJppfTask > 0 ) {
            useJppf = true;
            multiThreaded = false;
        }
        else if ( numAccessibilityThreads > 1 ) {
            useJppf = false;
            multiThreaded = true;
        }
        else {
            useJppf = false;
            multiThreaded = false;
        }
        
        trace = Util.getBooleanValueFromPropertyMap( propertyMap, ACC_TRACE_OD_UTILITY_PROPERTY_KEY );
        traceOtaz = Util.getIntegerArrayFromPropertyMap( propertyMap, ACC_TRACE_OD_UTILITY_ORIG_PROPERTY_KEY );
        traceDtaz = Util.getIntegerArrayFromPropertyMap( propertyMap, ACC_TRACE_OD_UTILITY_DEST_PROPERTY_KEY );

        // set up the tracer object
        tracer = Tracer.getTracer();
        tracer.setTrace(trace);
        if ( trace )
        {
            for (int i = 0; i < traceOtaz.length; i++)
            {
                for (int j = 0; j < traceDtaz.length; j++)
                {
                    tracer.traceZonePair(traceOtaz[i], traceDtaz[j]);
                }
            }
        }
                
    }

    
    public void closeAccessibilityLogsumsCalculator() {
        ExpUtilityModelManager expUtilityModelManager = ExpUtilityModelManager.getInstance();
        expUtilityModelManager.close();
    }
    
    public void setTestAlts( int value ) {
        numDcAlts = value;        
    }
    
    public ExpUtilityModel getExpUtilityModel( int periodIndex )  
    {
        
        ExpUtilityModel expUtilityModel = null;
        ExpUtilityModelManager expUtilityModelManager = ExpUtilityModelManager.getInstance();

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String uecFolder = propertyMap.get( PROJECT_UEC_FOLDER_PROPERTY_KEY );
        
        int expUtilitiesDataPage = -1;
        
        String accessibilitiesUecFileName = Util.getStringValueFromPropertyMap( propertyMap, ACC_UEC_FILE_KEY );
        accessibilitiesUecFileName = projectDirectory + uecFolder + "/" + accessibilitiesUecFileName;

        int opNmPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_NON_MOTOR_OP_UTILITY_PAGE_PROPERTY_KEY );
        
        switch ( periodIndex ) {

            case PEAK_INDEX:
                expUtilitiesDataPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_MANDATORY_DATA_PAGE_PROPERTY_KEY );

                int pkSovPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_SOV_PK_UTILITY_PAGE_PROPERTY_KEY );
                int pkHovPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_HOV_PK_UTILITY_PAGE_PROPERTY_KEY );
                int pkWtPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_WALK_TRANSIT_PK_UTILITY_PAGE_PROPERTY_KEY );
                int pkDtPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_DRIVE_TRANSIT_PK_UTILITY_PAGE_PROPERTY_KEY );
                expUtilityModel = expUtilityModelManager.getModelObject(propertyMap, dmuFactory, tazDataHandler, incomeSegmentVOTs, accessibilitiesUecFileName, expUtilitiesDataPage, opNmPage, pkSovPage, pkHovPage, pkWtPage, pkDtPage, "AM Peak" );
                break;

            case OFF_PEAK_INDEX:
                expUtilitiesDataPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_NON_MANDATORY_DATA_PAGE_PROPERTY_KEY );

                int opSovPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_SOV_OP_UTILITY_PAGE_PROPERTY_KEY );
                int opHovPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_HOV_OP_UTILITY_PAGE_PROPERTY_KEY );
                int opWtPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_WALK_TRANSIT_OP_UTILITY_PAGE_PROPERTY_KEY );
                int opDtPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_DRIVE_TRANSIT_OP_UTILITY_PAGE_PROPERTY_KEY );
                expUtilityModel = expUtilityModelManager.getModelObject(propertyMap, dmuFactory, tazDataHandler, incomeSegmentVOTs, accessibilitiesUecFileName, expUtilitiesDataPage, opNmPage, opSovPage, opHovPage, opWtPage, opDtPage, "MD Off-Peak" );
                break;
                
        }
        
        return expUtilityModel;
        
    }

        
    /**
     * Calculate constant terms, exponentiate, and store in constants array.
     */
    private void calculateConstants()
    {

        logger.info("Calculating constants");

        IndexValues iv = new IndexValues();

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String uecFolder = propertyMap.get( PROJECT_UEC_FOLDER_PROPERTY_KEY );
        String constantsUecFileName = Util.getStringValueFromPropertyMap( propertyMap, ACC_UEC_FILE_CONSTANTS_PROPERTY_KEY );
        constantsUecFileName = projectDirectory + uecFolder + "/" + constantsUecFileName;
        
        int workConstantsPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_WORK_PAGE_PROPERTY_KEY );
        int othMaintConstantsPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_OTHMAINT_PAGE_PROPERTY_KEY );
        int constantsDataPage = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_AUTO_SUFFICIENCY_CONSTANTS_DATA_PAGE_PROPERTY_KEY );
        
        AccConstantsDMU constantsDmu = dmuFactory.getAccConstantsDMU();
        UtilityExpressionCalculator workConstantsUEC = new UtilityExpressionCalculator( new File(constantsUecFileName), workConstantsPage, constantsDataPage, propertyMap, constantsDmu );
        UtilityExpressionCalculator othMaintConstantsUEC = new UtilityExpressionCalculator( new File(constantsUecFileName), othMaintConstantsPage, constantsDataPage, propertyMap, constantsDmu );


        int numAlts = workConstantsUEC.getNumberOfAlternatives();
        String[] altNames = workConstantsUEC.getAlternativeNames();
        expConstants[PEAK_INDEX] = new double[autoSufficiencySegments.length][numAlts];
        
        for ( int i=0; i < autoSufficiencySegments.length; i++ )
        {
            constantsDmu.setAutoSufficiency(i);
            double[] utilities = workConstantsUEC.solve( iv, constantsDmu, null );

            // exponentiate and store the constants
            for ( int j=0; j < numAlts; j++ )
            {
                expConstants[PEAK_INDEX][i][j] = Math.exp(utilities[j]);
                logger.info("Work Exp. Constant, market[" + i + ": " + autoSufficiencySegments[i] + "], Mode[" + j + ": " + altNames[j] + "] = " + expConstants[PEAK_INDEX][i][j]);
            }
        }

        
        numAlts = othMaintConstantsUEC.getNumberOfAlternatives();
        altNames = othMaintConstantsUEC.getAlternativeNames();
        expConstants[OFF_PEAK_INDEX] = new double[autoSufficiencySegments.length][numAlts];
        
        for ( int i=0; i < autoSufficiencySegments.length; i++ )
        {
            constantsDmu.setAutoSufficiency(i);
            double[] utilities = othMaintConstantsUEC.solve( iv, constantsDmu, null );

            // exponentiate and store the constants
            for ( int j=0; j < numAlts; j++ )
            {
                expConstants[OFF_PEAK_INDEX][i][j] = Math.exp(utilities[j]);
                logger.info("Other Maintenance Exp. Constant, market[" + i + ": " + autoSufficiencySegments[i] + "], Mode[" + j + ": " + altNames[j] + "] = " + expConstants[OFF_PEAK_INDEX][i][j]);
            }
        }
        
        
    }
    
    
    private double[][][] calculateSizeTerms( String[][] sizeTermSegmentNames )
    {

        // allocate the size array - numDcAlts * numPeriods * numSegments per period
        double[][][] accessibilitySize = new double[numDcAlts][sizeTermSegmentNames.length][];
        
        // loop over numDcAlts
        for( int destAlt=0; destAlt < numDcAlts; destAlt++ ) {

            int jTaz = ( destAlt / numberOfSubzones ) + 1;
            int jSubzoneIndex = destAlt - ( jTaz - 1 ) * numberOfSubzones;            
        
            // loop over the number of size term periods
            for( int i=0; i < sizeTermSegmentNames.length; i++ ) {
                
                accessibilitySize[destAlt][i] = new double[sizeTermSegmentNames[i].length];

                // loop over the number of size term segments in each size term period
                for ( int j=0; j < sizeTermSegmentNames[i].length; j++ )
                    accessibilitySize[destAlt][i][j] = dcSizeObj[i].getDcSize( dcSizeObj[i].getDcSizeArrayPurposeIndex( sizeTermSegmentNames[i][j] ), jTaz, jSubzoneIndex );
                
            }
        
        }
        
        return accessibilitySize;
        
    }


    /**
     * 
     * @param accessibilityModel
     * @param startIndex is the beginning DC Alt index for the range calculated in this method call
     * @param endIndex is the ending DC Alt index for the range calculated in this method call
     * @param periodIndex is 0 for peak/work and 1 for offPeak/othMaint
     * @param incomeIndex is 0-4 for low, med, high, very high, and is used to set the value of time
     * @param logsumsDmu is the DMU object used to get logged size and logsum for final logsum alternative values
     * @param logsumsUEC is the UEC object used for final logsum alternative values
     * @param accessibilitySize is the array of size terms by DC Alts, periods/purposes, and segments by period/purpose
     * @param incomeSegments are segment names - low, med, high, very high
     * @param autoSufficiencySegments are segment names - autos==0, autos<workers, autos>=workers
     * @return
     */
    private double[][] calculateLogsumsForIncomeSegment(  ExpUtilityModel accessibilityModel, int startIndex, int endIndex, int periodIndex, int incomeIndex,
            AccessibilityDMU logsumsDmu, UtilityExpressionCalculator logsumsUEC, double[][][] accessibilitySize, String[] incomeSegments, String[] autoSufficiencySegments ) {

        // get the accessibilities utilities alternatives
        int numAccessibilityAlts = logsumsUEC.getNumberOfAlternatives();
        TableDataSet altData = logsumsUEC.getAlternativeData();
        logsumsDmu.setAlternativeData(altData);
        
        double[][] accessibilities = new double[numDcAlts][];
        double[][] exponentiatedUtilities = new double[incomeSegments.length][autoSufficiencySegments.length];
        
        // Loop over destination choice model alternatives (origin zones and subzones)
        for ( int origAlt=startIndex; origAlt < endIndex; origAlt++ ) {

            accessibilities[origAlt] = new double[numAccessibilityAlts];
            
            int iTaz = ( origAlt / numberOfSubzones ) + 1;
            int iSubzoneIndex = origAlt - ( iTaz - 1 ) * numberOfSubzones;            

            if ( iTaz % 100 == 0 && iSubzoneIndex == 0 )
                logger.info( Thread.currentThread().getName() + ", periodIndex = " + periodIndex + ", incomeIndex = " + incomeIndex + ", origTaz = " + iTaz );
            
            accessibilityModel.calculateExponentiatedUtilities( iTaz, iSubzoneIndex, incomeIndex, tracer );
            double[] nmExpUtilities = accessibilityModel.getNmExpUtilities( incomeIndex );
            double[] sovExpUtilities = accessibilityModel.getSovExpUtilities( incomeIndex );
            double[] hovExpUtilities = accessibilityModel.getHovExpUtilities( incomeIndex );
            double[][] wtExpUtilities = accessibilityModel.getWtExpUtilities( incomeIndex );
            double[][] dtExpUtilities = accessibilityModel.getDtExpUtilities( incomeIndex );
            
            
            // Loop over destination choice model alternatives (destination zones and subzones)
            for ( int destAlt=0; destAlt < numDcAlts; destAlt++ ) {

                int jTaz = ( destAlt / numberOfSubzones ) + 1;
                int jSubzoneIndex = destAlt - ( jTaz - 1 ) * numberOfSubzones;            


                // 0: LOGSUM_0_AUTO
                exponentiatedUtilities[incomeIndex][LOGSUM_0_AUTO] = 
                        sovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_0_AUTO][0]
                        + hovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_0_AUTO][1]
                        + wtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_0_AUTO][2]
                        + dtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_0_AUTO][3]
                        + nmExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_0_AUTO][4];

                // 1: LOGSUM_AUTOS_LT_WORKERS
                exponentiatedUtilities[incomeIndex][LOGSUM_AUTOS_LT_WORKERS] =
                        sovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_LT_WORKERS][0]
                        + hovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_LT_WORKERS][1]
                        + wtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_AUTOS_LT_WORKERS][2]
                        + dtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_AUTOS_LT_WORKERS][3]
                        + nmExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_LT_WORKERS][4];

                // 2: LOGSUM_AUTOS_GE_WORKERS
                exponentiatedUtilities[incomeIndex][LOGSUM_AUTOS_GE_WORKERS] =
                        sovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_GE_WORKERS][0]
                        + hovExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_GE_WORKERS][1]
                        + wtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_AUTOS_GE_WORKERS][2]
                        + dtExpUtilities[jTaz][jSubzoneIndex] * expConstants[periodIndex][LOGSUM_AUTOS_GE_WORKERS][3]
                        + nmExpUtilities[jTaz] * expConstants[periodIndex][LOGSUM_AUTOS_GE_WORKERS][4];

                
                logsumsDmu.setLogsums( exponentiatedUtilities );
                logsumsDmu.setSizeTerms( accessibilitySize[destAlt][periodIndex] );

                if (trace)
                {
                    logger.info ( "iTaz = " + iTaz + ", iSubzone = " + iSubzoneIndex + ", jTaz = " + jTaz + ", jSubzone = " + jSubzoneIndex );
                    for(int j=0; j < exponentiatedUtilities.length; j++) {
                        logger.info ( String.format("%-10s %-10s %16.6e", incomeSegments[incomeIndex], autoSufficiencySegments[j], exponentiatedUtilities[incomeIndex][j] ) );
                    }
                }
                
                // accumulate sum-product of exponentiated utility and size term, by accessibility logsum alternative, for each origin taz
                for ( int alt=0; alt < numAccessibilityAlts; alt++ )
                {

                    double altExpUtility = logsumsDmu.getLogsum(alt + 1);
                    double altSizeTerm = logsumsDmu.getSizeTerm(alt + 1);

                    accessibilities[origAlt][alt] += ( altExpUtility * altSizeTerm );

                    if (trace)
                    {
                        logger.info( iTaz + "," + iSubzoneIndex + "," + jTaz + "," + jSubzoneIndex + "," + alt + "," + altExpUtility + ","
                                + altSizeTerm + "," + accessibilities[origAlt][alt] );
                    }
                    
                }
                
            } //end for destinations
            

            // calculate the final accessibility logsums
            for ( int alt=0; alt < numAccessibilityAlts; alt++ ){
                if ( accessibilities[origAlt][alt] > 0 )
                    accessibilities[origAlt][alt] = Math.log(accessibilities[origAlt][alt]);
                
            }
            
        }

        return accessibilities;
        
    }
    
    
    public double[][][] calculateAccessibilities( String[][] sizeTermSegmentNames )
    {
        
        calculateConstants();

        // calculate size terms for all periods and segments in periods
        double[][][] accessibilitySize = calculateSizeTerms( sizeTermSegmentNames );

        double[][][] accessibilities = new double[sizeTermSegmentNames.length][numDcAlts][];

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String uecFolder = propertyMap.get( PROJECT_UEC_FOLDER_PROPERTY_KEY );

        String[] logsumsFile = new String[NUM_PERIODS];
        logsumsFile[PEAK_INDEX] = Util.getStringValueFromPropertyMap( propertyMap, ACC_UEC_FILE_KEY );
        logsumsFile[PEAK_INDEX] = projectDirectory + uecFolder + "/" + logsumsFile[PEAK_INDEX];
        logsumsFile[OFF_PEAK_INDEX] = Util.getStringValueFromPropertyMap( propertyMap, ACC_UEC_FILE_KEY );
        logsumsFile[OFF_PEAK_INDEX] = projectDirectory + uecFolder + "/" + logsumsFile[OFF_PEAK_INDEX];

        int[] logsumsPage = new int[NUM_PERIODS];
        logsumsPage[PEAK_INDEX] = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_MANDATORY_ACCESSIBILITIES_UTILITY_PAGE_PROPERTY_KEY );
        logsumsPage[OFF_PEAK_INDEX] = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_NON_MANDATORY_ACCESSIBILITIES_UTILITY_PAGE_PROPERTY_KEY );

        int[] logsumsDataPage = new int[NUM_PERIODS];
        logsumsDataPage[PEAK_INDEX] = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_MANDATORY_DATA_PAGE_PROPERTY_KEY );
        logsumsDataPage[OFF_PEAK_INDEX] = Util.getIntegerValueFromPropertyMap( propertyMap, ACC_UEC_FILE_NON_MANDATORY_DATA_PAGE_PROPERTY_KEY );

        AccessibilityDMU logsumsDmu = dmuFactory.getAccessibilityDMU();
                    
        
        ExpUtilityModel accessibilityModel = null;
        
        if ( useJppf ) {
            
            int packetSize = numOrigsPerJppfTask;
            int numPackets = numDcAlts / packetSize;

            ArrayList<int[]> startEndIndexList = getStartEndIndexList( packetSize, numPackets );
            accessibilities = submitJppfTasks( startEndIndexList, accessibilitySize, logsumsFile, logsumsDataPage, logsumsPage, sizeTermSegmentNames.length, incomeSegmentVOTs.length, accessibilities, 0, incomeSegments, autoSufficiencySegments );
            
        }
        else if ( multiThreaded ) {
            
            int packetSize = numDcAlts / numAccessibilityThreads;
            int numPackets = numAccessibilityThreads;
            
            ArrayList<int[]> startEndIndexList = getStartEndIndexList( packetSize, numPackets );
            for ( int periodIndex=0; periodIndex < sizeTermSegmentNames.length; periodIndex++ ) {
                for ( int incomeIndex=0; incomeIndex < incomeSegmentVOTs.length; incomeIndex++ )            
                    accessibilities[periodIndex] = submitTasks( startEndIndexList, accessibilitySize, logsumsFile[periodIndex], logsumsDataPage[periodIndex], logsumsPage[periodIndex], periodIndex, incomeIndex, accessibilities[periodIndex], incomeSegments, autoSufficiencySegments );
            }
            
        }
        else {
            
            for ( int periodIndex=0; periodIndex < sizeTermSegmentNames.length; periodIndex++ ) {
                accessibilityModel = getExpUtilityModel( periodIndex );
                UtilityExpressionCalculator logsumsUEC = new UtilityExpressionCalculator( new File(logsumsFile[periodIndex]), logsumsPage[periodIndex], logsumsDataPage[periodIndex], propertyMap, logsumsDmu );
                for ( int incomeIndex=0; incomeIndex < incomeSegmentVOTs.length; incomeIndex++ )
                    accessibilities[periodIndex] = calculateLogsumsForIncomeSegment( accessibilityModel, 0, numDcAlts, periodIndex, incomeIndex, logsumsDmu, logsumsUEC, accessibilitySize, incomeSegments, autoSufficiencySegments );
            
            }
            
        }
        
        
        return accessibilities;

    }


    private double[][] submitTasks( ArrayList<int[]> startEndIndexList, double[][][] accessibilitySize, String logsumsFile, int logsumsDataPage, int logsumsPage, int periodIndex, int incomeIndex, double[][] accessibilities, String[] incomeSegments, String[] autoSufficiencySegments )
    {

        ExecutorService exec = Executors.newFixedThreadPool( numAccessibilityThreads );
        ArrayList<Future<List<Object>>> results = new ArrayList<Future<List<Object>>>();

        
        int startIndex = 0;
        int endIndex = 0;
        int taskIndex = 1;
        for (int[] startEndIndices : startEndIndexList)
        {
            startIndex = startEndIndices[0];
            endIndex = startEndIndices[1];

            logger.info(String.format("creating TASK: %d range: %d to %d.", taskIndex, startIndex, endIndex));
            CallableTask task = new CallableTask ( startIndex, endIndex, accessibilitySize, logsumsFile, logsumsDataPage, logsumsPage, periodIndex, incomeIndex, incomeSegments, autoSufficiencySegments, taskIndex );

            results.add(exec.submit(task));
            taskIndex++;
        }

                
        for (Future<List<Object>> fs : results)
        {

            try
            {
                List<Object> resultBundle = fs.get();
                int task = (Integer) resultBundle.get(0);
                int period = (Integer) resultBundle.get(1);
                int income = (Integer) resultBundle.get(2);
                int start = (Integer) resultBundle.get(3);
                int end = (Integer) resultBundle.get(4);
                logger.info(String.format("returned TASK: %d, period=%d, income=%d, start=%d, end=%d.", task, period, income, start, end));
                double[][] taskAccessibilities = (double[][]) resultBundle.get(5);
                int incomeOffset = income*autoSufficiencySegments.length;
                for (int i=start; i < end; i++) {
                    if ( accessibilities[i] == null )
                        accessibilities[i] = new double[taskAccessibilities[i].length];
                    for ( int j=0; j < autoSufficiencySegments.length; j++ )
                        accessibilities[i][j+incomeOffset] = taskAccessibilities[i][j+incomeOffset];
                }
            } catch (InterruptedException e)
            {
                e.printStackTrace();
                throw new RuntimeException();
            } catch (ExecutionException e)
            {
                logger.error("Exception returned in place of result object.", e);
                throw new RuntimeException();
            } finally
            {
                exec.shutdown();
            }

        } // future

        return accessibilities;
    }


    
    private double[][][] submitJppfTasks( ArrayList<int[]> startEndIndexList, double[][][] accessibilitySize, String[] logsumsFile, int[] logsumsDataPage, int[] logsumsPage, int numPeriods, int numIncomeSegments, double[][][] accessibilities, int numAccessibilityAlts, String[] incomeSegments, String[] autoSufficiencySegments )
    {

        JPPFClient jppfClient = new JPPFClient();
        JPPFJob job = new JPPFJob();

        try {
            DataProvider dataProvider = new MemoryMapDataProvider();
            dataProvider.setValue( "accessibilitySize", accessibilitySize );
            job.setDataProvider(dataProvider);
        }
        catch (Exception e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        
        int taskIndex = 1;
        int startIndex;
        int endIndex;
        
        for ( int periodIndex=0; periodIndex < numPeriods; periodIndex ++ ) {
            
            for ( int incomeIndex=0; incomeIndex < numIncomeSegments; incomeIndex ++ ) {
                
                for ( int[] startEndIndices : startEndIndexList ) {
                    startIndex = startEndIndices[0];
                    endIndex = startEndIndices[1];

                    JppfTask task = new JppfTask ( startIndex, endIndex, logsumsFile[periodIndex], logsumsDataPage[periodIndex], logsumsPage[periodIndex], periodIndex, incomeIndex, incomeSegments, autoSufficiencySegments, taskIndex );

                    try
                    {
                        job.addTask ( task );
                    }
                    catch (JPPFException e) {
                        // TODO Auto-generated catch block
                        e.printStackTrace();
                    }
                    taskIndex++;
                }

            }

        }

        
        try
        {
            List<JPPFTask> results = jppfClient.submit(job);

            for ( JPPFTask task : results ) {
                
                if (task.getException() != null)
                    throw task.getException();

                try {                       
                    List<Object> resultBundle = (List<Object>)task.getResult();
                    int taskId = (Integer) resultBundle.get(0);
                    int period = (Integer) resultBundle.get(1);
                    int income = (Integer) resultBundle.get(2);
                    int start = (Integer) resultBundle.get(3);
                    int end = (Integer) resultBundle.get(4);
                    logger.info(String.format("returned TASK: %d, period=%d, income=%d, start=%d, end=%d.", taskId, period, income, start, end));
                    double[][] taskAccessibilities = (double[][]) resultBundle.get(5);
                    int incomeOffset = income*autoSufficiencySegments.length;
                    for (int i=start; i < end; i++) {
                        if ( accessibilities[period][i] == null )
                            accessibilities[period][i] = new double[taskAccessibilities[i].length];
                        for ( int j=0; j < autoSufficiencySegments.length; j++ ) 
                            accessibilities[period][i][j+incomeOffset] = taskAccessibilities[i][j+incomeOffset];
                    }
                }
                catch (Exception e) {
                    logger.error( "", e );
                    throw new RuntimeException();
                }

            }
        }
        catch (Exception e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }

        
        return accessibilities;
        
    }

    
    public ArrayList<int[]> getStartEndIndexList( int packetSize, int numPackets )
    {

        ArrayList<int[]> startEndIndexList = new ArrayList<int[]>( numPackets );

        // assign start, end MGRA ranges to be used to assign to tasks
        int startIndex = 0;
        int endIndex = 0;
        for ( int i=0; i < numPackets - 1; i++ ) {
            endIndex = startIndex + packetSize;
            int[] startEndIndices = new int[2];
            startEndIndices[0] = startIndex;
            startEndIndices[1] = endIndex;
            startEndIndexList.add(startEndIndices);
            startIndex = endIndex;
        }
        endIndex = numDcAlts;
        int[] startEndIndices = new int[2];
        startEndIndices[0] = startIndex;
        startEndIndices[1] = endIndex;
        startEndIndexList.add(startEndIndices);
        
        return startEndIndexList;
    
    }
    
    public List<Object> call()
    {
        return null;
    }    
    
    
    public class CallableTask implements Callable<List<Object>>
    {

        private int startRange;
        private int endRange;
        private String logsumsFile;
        private int logsumsDataPage;
        private int logsumsPage;
        private int periodIndex;
        private int incomeIndex;
        private String[] incomeSegments;
        private String[] autoSufficiencySegments;
        private int taskIndex;
        private double[][][] accessibilitySize;
        
        private CallableTask( int startRange, int endRange, double[][][] accessibilitySize, String logsumsFile, int logsumsDataPage, int logsumsPage, int periodIndex, int incomeIndex, String[] incomeSegments, String[] autoSufficiencySegments, int taskIndex ) {
            this.startRange = startRange;
            this.endRange = endRange;
            this.logsumsFile = logsumsFile;
            this.logsumsDataPage = logsumsDataPage;
            this.logsumsPage = logsumsPage;
            this.periodIndex = periodIndex;
            this.incomeIndex = incomeIndex;
            this.incomeSegments = incomeSegments;
            this.autoSufficiencySegments = autoSufficiencySegments;
            this.taskIndex = taskIndex;
            this.accessibilitySize = accessibilitySize;
        }
        
        
        public List<Object> call()
        {
            
            ExpUtilityModel expUtilityModel = getExpUtilityModel( periodIndex );            
            
            AccessibilityDMU logsumsDmu = dmuFactory.getAccessibilityDMU();
            UtilityExpressionCalculator logsumsUEC = new UtilityExpressionCalculator( new File(logsumsFile), logsumsPage, logsumsDataPage, propertyMap, logsumsDmu );
                        
            double[][] accessibilities = calculateLogsumsForIncomeSegment( expUtilityModel, startRange, endRange, periodIndex, incomeIndex, logsumsDmu, logsumsUEC, accessibilitySize, incomeSegments, autoSufficiencySegments );
            
            List<Object> resultBundle = new ArrayList<Object>(6);
            resultBundle.add(taskIndex);
            resultBundle.add(periodIndex);
            resultBundle.add(incomeIndex);
            resultBundle.add(startRange);
            resultBundle.add(endRange);
            resultBundle.add(accessibilities);

            return resultBundle;
        }
        
    }
    

    public class JppfTask extends JPPFTask {

        private int startRange;
        private int endRange;
        private String logsumsFile;
        private int logsumsDataPage;
        private int logsumsPage;
        private int periodIndex;
        private int incomeIndex;
        private String[] incomeSegments;
        private String[] autoSufficiencySegments;
        private int taskIndex;

        
        public JppfTask( int startRange, int endRange, String logsumsFile, int logsumsDataPage, int logsumsPage, int periodIndex, int incomeIndex, String[] incomeSegments, String[] autoSufficiencySegments, int taskIndex ) {
            this.startRange = startRange;
            this.endRange = endRange;
            this.logsumsFile = logsumsFile;
            this.logsumsDataPage = logsumsDataPage;
            this.logsumsPage = logsumsPage;
            this.periodIndex = periodIndex;
            this.incomeIndex = incomeIndex;
            this.incomeSegments = incomeSegments;
            this.autoSufficiencySegments = autoSufficiencySegments;
            this.taskIndex = taskIndex;
        }
        
        
        public void run()
        {

            double[][] accessibilities = null;
            double[][][] accessibilitySize = null;
                     
            try {
                DataProvider dataProvider = getDataProvider();
                accessibilitySize = (double[][][]) dataProvider.getValue("accessibilitySize");

            }
            catch (Exception e) {
                e.printStackTrace();
            }
            
            ExpUtilityModel expUtilityModel = getExpUtilityModel( periodIndex );            
            
            AccessibilityDMU logsumsDmu = dmuFactory.getAccessibilityDMU();
            UtilityExpressionCalculator logsumsUEC = new UtilityExpressionCalculator( new File(logsumsFile), logsumsPage, logsumsDataPage, propertyMap, logsumsDmu );
                        
            accessibilities = calculateLogsumsForIncomeSegment( expUtilityModel, startRange, endRange, periodIndex, incomeIndex, logsumsDmu, logsumsUEC, accessibilitySize, incomeSegments, autoSufficiencySegments );
            
            List<Object> resultBundle = new ArrayList<Object>(6);
            resultBundle.add(taskIndex);
            resultBundle.add(periodIndex);
            resultBundle.add(incomeIndex);
            resultBundle.add(startRange);
            resultBundle.add(endRange);
            resultBundle.add(accessibilities);

            setResult( resultBundle );

        }

    }

}
