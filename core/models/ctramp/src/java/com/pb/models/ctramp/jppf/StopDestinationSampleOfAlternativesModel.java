package com.pb.models.ctramp.jppf;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.util.Map;
import java.util.HashMap;

import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.Stop;
import com.pb.models.ctramp.StopDCSoaDMU;
import com.pb.models.ctramp.StopDestChoiceSize;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.Tour;

/**
 * @author crf <br/>
 *         Started: Nov 14, 2008 3:09:14 PM
 */
public class StopDestinationSampleOfAlternativesModel implements Serializable {
    
    private transient Logger logger = Logger.getLogger(StopDestinationSampleOfAlternativesModel.class);

    private static final String PROPERTIES_UEC_STOP_LOCATION_SOA = "UecFile.StopLocationSoa";
    private static final String PROPERTIES_STOP_LOCATION_SOA_SAMPLE_SIZE = "StopLocationSoa.SampleSize";

    protected static final int STOP_SOA_DATA_SHEET = 0;
    private static final int SOA_WORK_UEC_MODEL_PAGE = 1;
    private static final int SOA_UNIVERSITY_UEC_MODEL_PAGE = 2;
    private static final int SOA_SCHOOL_UEC_MODEL_PAGE = 3;
    private static final int SOA_ESCORT_UEC_MODEL_PAGE = 4;
    private static final int SOA_SHOPPING_UEC_MODEL_PAGE = 5;
    private static final int SOA_EAT_OUT_UEC_MODEL_PAGE = 6;
    private static final int SOA_OTH_MAINT_UEC_MODEL_PAGE = 7;
    private static final int SOA_SOCIAL_UEC_MODEL_PAGE = 8;
    private static final int SOA_OTH_DISC_UEC_MODEL_PAGE = 9;
    private static final int SOA_AT_WORK_UEC_MODEL_PAGE = 10;

    private static final int SOA_WORK_STOP_PURPOSE_INDEX = 1;
    private static final int SOA_ESCORT_STOP_PURPOSE_INDEX = 2;
    private static final int SOA_SHOPPING_STOP_PURPOSE_INDEX = 3;
    private static final int SOA_EAT_OUT_STOP_PURPOSE_INDEX = 4;
    private static final int SOA_OTH_MAINT_STOP_PURPOSE_INDEX = 5;
    private static final int SOA_SOCIAL_STOP_PURPOSE_INDEX = 6;
    private static final int SOA_OTH_DISC_STOP_PURPOSE_INDEX = 7;

    protected Map<String,Integer> uecPageMap;
    private Map<String,Integer> lookupIndexMap;


    protected String stopSoaUecFileName;
    protected StopDCSoaDMU stopSoaDmu;
    protected int sampleSize;

    protected Map<Integer,SampleOfAlternatives> soa;
    protected Map<Integer,boolean[]> destinationAvailability;
    protected Map<Integer,double[]> logSizeTerms;

    protected ModelStructure modelStructure;        
    protected TazDataIf tazDataManager;
    
    public StopDestinationSampleOfAlternativesModel( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) {
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;
        setup( propertyMap, tazDataManager, sizeModel, modelStructure, dmuFactory );
    }
//    public StopDestinationSampleOfAlternativesModel( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel, HashMap<String, Object[]> objectLockMap, HashMap<String, double[][]> probabilitiesMap, HashMap<String, double[][]> cumProbabilitiesMap ) {
//        setup( propertyMap, tazDataManager, sizeModel, objectLockMap, probabilitiesMap, cumProbabilitiesMap );
//    }

    
    //private void setup( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel, HashMap<String, Object[]> objectLockMap, HashMap<String, double[][]> probabilitiesMap, HashMap<String, double[][]> cumProbabilitiesMap ) {
    private void setup( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel, ModelStructure modelStructure, CtrampDmuFactoryIf dmuFactory ) {

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        stopSoaUecFileName = projectDirectory + propertyMap.get(PROPERTIES_UEC_STOP_LOCATION_SOA);
        sampleSize = Integer.parseInt( propertyMap.get(PROPERTIES_STOP_LOCATION_SOA_SAMPLE_SIZE) );
        stopSoaDmu = dmuFactory.getStopDCSoaDMU();

        uecPageMap = new HashMap<String,Integer>();
        uecPageMap.put(ModelStructure.WORK_PURPOSE_NAME,SOA_WORK_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.UNIVERSITY_PURPOSE_NAME,SOA_UNIVERSITY_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.SCHOOL_PURPOSE_NAME,SOA_SCHOOL_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.ESCORT_PURPOSE_NAME,SOA_ESCORT_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.SHOPPING_PURPOSE_NAME,SOA_SHOPPING_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.EAT_OUT_PURPOSE_NAME,SOA_EAT_OUT_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.OTH_MAINT_PURPOSE_NAME,SOA_OTH_MAINT_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.SOCIAL_PURPOSE_NAME,SOA_SOCIAL_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.OTH_DISCR_PURPOSE_NAME,SOA_OTH_DISC_UEC_MODEL_PAGE);
        uecPageMap.put(ModelStructure.AT_WORK_PURPOSE_NAME,SOA_AT_WORK_UEC_MODEL_PAGE);

        lookupIndexMap = new HashMap<String,Integer>();
        lookupIndexMap.put(ModelStructure.WORK_PURPOSE_NAME,SOA_WORK_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.UNIVERSITY_PURPOSE_NAME,SOA_WORK_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.SCHOOL_PURPOSE_NAME,SOA_WORK_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.ESCORT_PURPOSE_NAME,SOA_ESCORT_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.SHOPPING_PURPOSE_NAME,SOA_SHOPPING_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.EAT_OUT_PURPOSE_NAME,SOA_EAT_OUT_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.OTH_MAINT_PURPOSE_NAME,SOA_OTH_MAINT_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.SOCIAL_PURPOSE_NAME,SOA_SOCIAL_STOP_PURPOSE_INDEX);
        lookupIndexMap.put(ModelStructure.OTH_DISCR_PURPOSE_NAME,SOA_OTH_DISC_STOP_PURPOSE_INDEX);

        int numberOfZones = tazDataManager.getNumberOfZones();
        int numberOfSubZones = tazDataManager.getNumberOfSubZones();
        int numberOfAvailableZones = numberOfZones*tazDataManager.getNumberOfSubZones();
        int[] altToZone = tazDataManager.getAltToZoneArray();
        int[] altToSubZone = tazDataManager.getAltToSubZoneArray();

        //                      /purposes save escort\ /escort purposes                          \ /inbound and outbound tours\
//        int numberOfPurposes = (uecPageMap.size() - 1 + modelStructure.ESCORT_SEGMEMT_NAMES.length) * 2;

        soa = new HashMap<Integer,SampleOfAlternatives>();
        destinationAvailability = new HashMap<Integer,boolean[]>();
        logSizeTerms = new HashMap<Integer,double[]>();

        
        for ( String purpose : uecPageMap.keySet()) {
            int uecPage = uecPageMap.get( purpose );
            try {
                ChoiceModelApplication choiceModel = new ChoiceModelApplication (stopSoaUecFileName, uecPage, STOP_SOA_DATA_SHEET, propertyMap, (VariableTable)stopSoaDmu );
                soa.put( uecPage, new SampleOfAlternatives( choiceModel, numberOfSubZones, sampleSize ) );
                //soa.put(index,new SampleOfAlternatives( choiceModel, numberOfZones, objLocks, probs, cumProbs));
            } catch (RuntimeException e) {
                logger.error (String.format("exception caught setting up STOP SOA UEC model index for tour purpose %s", purpose, e));
                throw e;
            }
        }

        
        
        for (String purpose : lookupIndexMap.keySet()) {
            if (purpose.equals(ModelStructure.ESCORT_PURPOSE_NAME)) {
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,true,true), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,false,true), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,true,false), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,false,false), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
            } else {
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,true), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
                setSoaModelInfo( propertyMap, getPurposeLookupIndex(purpose,false), numberOfSubZones, numberOfAvailableZones, sizeModel, altToZone, altToSubZone );
            }
        }
//        for (String purpose : uecPageMap.keySet()) {
//            if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME)) {
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//            } else {
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone,objectLockMap.get(purpose),probabilitiesMap.get(purpose),cumProbabilitiesMap.get(purpose));
//            }
//        }

    }

    //private void setSoaModelInfo( HashMap<String, String> propertyMap, int index, int uecPage, int numberOfZones, int numberOfAlternatives, StopDestChoiceSize sizeModel, int[] altToZone, int[] altToSubZone, Object[] objLocks, double[][] probs, double[][] cumProbs ) {
    private void setSoaModelInfo( HashMap<String, String> propertyMap, int index, int numberOfSubZones, int numberOfAlternatives, StopDestChoiceSize sizeModel, int[] altToZone, int[] altToSubZone ) {
        
        boolean[] destAvailability;
        double[] logSizeTerm;
        if (destinationAvailability.containsKey(-1*index)) { //use already computed inbound/outbound value, if it exists
            destAvailability = destinationAvailability.get(-1*index);
            logSizeTerm = logSizeTerms.get(-1*index);
        } else {
            destAvailability = new boolean[numberOfAlternatives+1];
            logSizeTerm = new double[numberOfAlternatives+1];
            for (int i=1; i <= numberOfAlternatives; i++) {
                int zone = altToZone[i];
                int subzone = altToSubZone[i];
                String[] purposeSegments = getMainAndSubPurposeFromLookupIndex(index);
                double size = sizeModel.getDcSize(purposeSegments[0].toLowerCase(), purposeSegments[1].toLowerCase(), zone, subzone );
                destAvailability[i] = size > 0.0;
                logSizeTerm[i] = size > 0.0 ? Math.log(1+size) : 0.0;
            }
        }
        destinationAvailability.put(index,destAvailability);
        logSizeTerms.put(index,logSizeTerm);
    }

    protected int getPurposeLookupIndex(String purpose, boolean inbound) {
        return getPurposeLookupIndex(purpose,inbound,false);
    }

    /*lookup index is an integer: [uecPage][has kids], where if kids are present (where it matters) it is 1, else 0
    *   the indedx is multiplied by -1 if it is inbound, otherwise it is > 0 */
    protected int getPurposeLookupIndex(String purpose, boolean inbound, boolean hasKids) {
        return (lookupIndexMap.get(purpose)*10 + (hasKids ? 1 : 0)) * (inbound ? 1 : -1);
    }

//    private String getPurposeFromLookupIndex(int lookupIndex) {
//        StringBuilder sb = new StringBuilder();
//        if (lookupIndex < 0) {
//            sb.append(" outbound");
//            lookupIndex *= -1;
//        } else {
//            sb.append(" inbound");
//        }
//        int purposeIndex = lookupIndex / 10;
//        for (String purpose : lookupIndexMap.keySet()) {
//            if (lookupIndexMap.get(purpose) == purposeIndex) {
//                if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME))
//                    sb.insert(0,(lookupIndex - purposeIndex*10 == 1) ? " kids" : " no kids");
//                sb.insert(0,purpose);
//                break;
//            }
//        }
//        return sb.toString();
//    }

    protected String[] getMainAndSubPurposeFromLookupIndex(int lookupIndex) {
        lookupIndex = Math.abs(lookupIndex);
        int purposeIndex = lookupIndex / 10;
        String[] purposeSegments = new String[2];
        for (String purpose : lookupIndexMap.keySet()) {
            if (lookupIndexMap.get(purpose) == purposeIndex) {
                if (purpose.equals(ModelStructure.ESCORT_PURPOSE_NAME))
                    //0 = kids, 1 = no kids in modelStructure, oposite in lookupIndex
                    purposeSegments[1] = modelStructure.ESCORT_SEGMENT_NAMES[1 - lookupIndex + purposeIndex*10];
                else
                    purposeSegments[1] = purpose;
                purposeSegments[0] = purpose;
                break;
            }
        }
        return purposeSegments;
    }

    protected final StopSoaResult soaResult= new StopSoaResult();

    public class StopSoaResult implements Serializable {
        private int[] sample;
        private float[] corrections;
        private double[] stopLocationSize;
        private int numUniqueAlts;
        private StopSoaResult() {}
        protected void setSample(int[] sample) {
            this.sample = sample;
        }
        protected void setCorrections(float[] corrections) {
            this.corrections = corrections;
        }
        protected void setNumUniqueAltsInSample( int numAlts ){
            this.numUniqueAlts = numAlts;
        }
        protected void setStopLocationSize( double[] stopLocSize ){
            this.stopLocationSize = stopLocSize;
        }
        
        public int getNumUniqueAltsInSample() {
            return numUniqueAlts;
        }
        public int[] getSample() {
            return sample;
        }
        public float[] getCorrections() {
            return corrections;
        }
        public double[] getStopLocationSize() {
            return stopLocationSize;
        }
    }

    public StopSoaResult computeDestinationSampleOfAlternatives( Stop s ) {
        boolean inbound = s.isInboundStop();
        String stopPurpose = modelStructure.getPrimaryPurposeForIndex( s.getDestPurposeIndex() );
        int stopOrig = s.getOrig();
        int lookupIndex;
        boolean hasKids = false;
        Tour t = s.getTour();
        int tourDest = inbound ? t.getTourOrigTaz() : t.getTourDestTaz();
        String tourPurpose = t.getTourPrimaryPurpose();
        
        Household hh = t.getPersonObject().getHouseholdObject();
        
        if ( stopPurpose.equals(ModelStructure.ESCORT_PURPOSE_NAME) ) {
            hasKids = hh.getNumChildrenUnder19() > 0;
            lookupIndex = getPurposeLookupIndex( ModelStructure.ESCORT_PURPOSE_NAME, inbound, hasKids );
        } else {
            lookupIndex = getPurposeLookupIndex( stopPurpose, inbound );
        }
        double[] stopLocSize = logSizeTerms.get(lookupIndex);
        stopSoaDmu.setDmuState( hh.getHhTaz(), stopOrig, tourDest, hh, t, inbound, hasKids, stopLocSize );

        // apply sample of alternatives model for the work segment to which this worker belongs.
        int uecPage = uecPageMap.get( tourPurpose );
        SampleOfAlternatives soaModel = soa.get( uecPage );
        
        soaModel.applySampleOfAlternativesChoiceModel ( tourPurpose, stopSoaDmu, stopSoaDmu.getDmuIndexValues(), stopOrig, destinationAvailability.get(lookupIndex) );

        soaResult.setSample( soaModel.getSampleOfAlternatives() );
        soaResult.setCorrections( soaModel.getSampleCorrectionFactors() );
        soaResult.setNumUniqueAltsInSample( soaModel.getNumUniqueAlts() );
        soaResult.setStopLocationSize( stopLocSize );
        return soaResult;
    }

    
    public void cleanUp() {
        soa = null;
    }
    
    
    public int getSampleOfAlternativesSampleSize() {
        return sampleSize;
    }
    
    
}
