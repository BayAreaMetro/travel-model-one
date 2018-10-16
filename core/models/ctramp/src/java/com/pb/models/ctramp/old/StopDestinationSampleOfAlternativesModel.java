package com.pb.models.ctramp.old;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.util.Map;
import java.util.HashMap;

import com.pb.common.model.ChoiceModelApplication;
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

    public static final String PROPERTIES_UEC_STOP_LOCATION_SOA = "UecFile.StopLocationSoa";
    public static final String PROPERTIES_STOP_LOCATION_SOA_SAMPLE_SIZE = "StopLocationSoa.SampleSize";

    private static final int STOP_SOA_DATA_SHEET = 0;
    private static final int SOA_WORK_UEC_MODEL_PAGE = 1;
    private static final int SOA_ESCORT_UEC_MODEL_PAGE = 2;
    private static final int SOA_SHOPPING_UEC_MODEL_PAGE = 3;
    private static final int SOA_EAT_OUT_UEC_MODEL_PAGE = 4;
    private static final int SOA_OTH_MAINT_UEC_MODEL_PAGE = 5;
    private static final int SOA_SOCIAL_UEC_MODEL_PAGE = 6;
    private static final int SOA_OTH_DISC_UEC_MODEL_PAGE = 7;


    private String stopSoaUecFileName;
    private StopDCSoaDMU stopSoaDmu;
    private int sampleSize;

    private Map<Integer,SampleOfAlternatives> soa;
    private Map<Integer,boolean[]> destinationAvailability;
    private Map<Integer,double[]> logSizeTerms;

    private HashMap<String,Integer> uecPageMap;
    private ModelStructure modelStructure;    
    
    
    public StopDestinationSampleOfAlternativesModel( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel, ModelStructure modelStructure ) {
        this.modelStructure = modelStructure;
        setup( propertyMap, tazDataManager, sizeModel );
    }

    
    private void setup( HashMap<String, String> propertyMap, TazDataIf tazDataManager, StopDestChoiceSize sizeModel ) {

        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        stopSoaUecFileName = projectDirectory + propertyMap.get(PROPERTIES_UEC_STOP_LOCATION_SOA);
        sampleSize = Integer.parseInt( propertyMap.get(PROPERTIES_STOP_LOCATION_SOA_SAMPLE_SIZE) );
        stopSoaDmu = new StopDCSoaDMU(tazDataManager,modelStructure);

        uecPageMap = new HashMap<String,Integer>();
        uecPageMap.put(modelStructure.WORK_PURPOSE_NAME,SOA_WORK_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.ESCORT_PURPOSE_NAME,SOA_ESCORT_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.SHOPPING_PURPOSE_NAME,SOA_SHOPPING_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.EAT_OUT_PURPOSE_NAME,SOA_EAT_OUT_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.OTH_MAINT_PURPOSE_NAME,SOA_OTH_MAINT_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.SOCIAL_PURPOSE_NAME,SOA_SOCIAL_UEC_MODEL_PAGE);
        uecPageMap.put(modelStructure.OTH_DISCR_PURPOSE_NAME,SOA_OTH_DISC_UEC_MODEL_PAGE);

        
        int numberOfZones = tazDataManager.getNumberOfZones();
        int numberOfAvailableZones = numberOfZones*tazDataManager.getNumberOfSubZones();
        int[] altToZone = tazDataManager.getAltToZoneArray();
        int[] altToSubZone = tazDataManager.getAltToSubZoneArray();

        //                      /purposes save escort\ /escort purposes                          \ /inbound and outbound tours\
//        int numberOfPurposes = (uecPageMap.size() - 1 + ModelStructure.ESCORT_SEGMEMT_NAMES.length) * 2;

        soa = new HashMap<Integer,SampleOfAlternatives>();
        destinationAvailability = new HashMap<Integer,boolean[]>();
        logSizeTerms = new HashMap<Integer,double[]>();

        for (String purpose : uecPageMap.keySet()) {
            if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME)) {
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
            } else {
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,true),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
                setSoaModelInfo(propertyMap,getPurposeLookupIndex(purpose,false),uecPageMap.get(purpose),numberOfZones,numberOfAvailableZones,sizeModel,altToZone,altToSubZone);
            }
        }

    }

    private void setSoaModelInfo( HashMap<String, String> propertyMap, int index, int uecPage, int numberOfZones, int numberOfAlternatives, StopDestChoiceSize sizeModel, int[] altToZone, int[] altToSubZone ) {
        
        try {
            ChoiceModelApplication choiceModel = new ChoiceModelApplication (stopSoaUecFileName, uecPage, STOP_SOA_DATA_SHEET, propertyMap, stopSoaDmu.getClass());
            soa.put(index,new SampleOfAlternatives( choiceModel, numberOfZones, new double[numberOfAlternatives][], new double[numberOfAlternatives][]));
        } catch (RuntimeException e) {
            logger.error (String.format("exception caught setting up STOP SOA UEC model index for purpose %s", getPurposeFromLookupIndex(index)),e);
            throw e;
        }

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

    private int getPurposeLookupIndex(String purpose, boolean inbound) {
        return getPurposeLookupIndex(purpose,inbound,false);
    }

    /*lookup index is an integer: [uecPage][has kids], where if kids are present (where it matters) it is 1, else 0
    *   the indedx is multiplied by -1 if it is inbound, otherwise it is > 0 */
    private int getPurposeLookupIndex(String purpose, boolean inbound, boolean hasKids) {
        return (uecPageMap.get(purpose)*10 + (hasKids ? 1 : 0)) * (inbound ? 1 : -1);
    }

    private String getPurposeFromLookupIndex(int lookupIndex) {
        StringBuilder sb = new StringBuilder();
        if (lookupIndex < 0) {
            sb.append(" outbound");
            lookupIndex *= -1;
        } else {
            sb.append(" inbound");
        }
        int purposeIndex = lookupIndex / 10;
        for (String purpose : uecPageMap.keySet()) {
            if (uecPageMap.get(purpose) == purposeIndex) {
                if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME))
                    sb.insert(0,(lookupIndex - purposeIndex*10 == 1) ? " kids" : " no kids");
                sb.insert(0,purpose);
                break;
            }
        }
        return sb.toString();
    }

    private String[] getMainAndSubPurposeFromLookupIndex(int lookupIndex) {
        lookupIndex = Math.abs(lookupIndex);
        int purposeIndex = lookupIndex / 10;
        String[] purposeSegments = new String[2];
        for (String purpose : uecPageMap.keySet()) {
            if (uecPageMap.get(purpose) == purposeIndex) {
                if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME))
                    //0 = kids, 1 = no kids in ModelStructure, oposite in lookupIndex
                    purposeSegments[1] = modelStructure.ESCORT_SEGMENT_NAMES[1 - lookupIndex + purposeIndex*10];
                else
                    purposeSegments[1] = purpose;
                purposeSegments[0] = purpose;
                break;
            }
        }
        return purposeSegments;
    }

    private final StopSoaResult soaResult= new StopSoaResult();

    public class StopSoaResult implements Serializable {
        private int[] sample;
        private float[] corrections;
        private StopSoaResult() {}
        private void setSample(int[] sample) {
            this.sample = sample;
        }
        private void setCorrections(float[] corrections) {
            this.corrections = corrections;
        }

        public int[] getSample() {
            return sample;
        }

        public float[] getCorrections() {
            return corrections;
        }
    }

    public StopSoaResult computeDestinationSampleOfAlternatives(Stop s) {
        boolean inbound = s.isInboundStop();
        String purpose = s.getDestPurpose( modelStructure );
        int origin = s.getOrig();
        int lookupIndex;
        boolean hasKids = false;
        Tour t = s.getTour();
        int dest = inbound ? t.getTourOrigTaz() : t.getTourDestTaz();
        Household hh = t.getPersonObject().getHouseholdObject();
        if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME)) {
            hasKids = hh.getNumChildrenUnder19() > 0;
            lookupIndex = getPurposeLookupIndex(modelStructure.ESCORT_PURPOSE_NAME,inbound,hasKids);
        } else {
            lookupIndex = getPurposeLookupIndex(purpose,inbound);
        }
        stopSoaDmu.setDmuState(hh.getHhTaz(),origin,dest,hh,t,inbound,hasKids,logSizeTerms.get(lookupIndex));

        // apply sample of alternatives model for the work segment to which this worker belongs.
        SampleOfAlternatives soaModel = soa.get(lookupIndex);
        soaModel.applySampleOfAlternativesChoiceModel (purpose, stopSoaDmu, stopSoaDmu.getDmuIndexValues(),origin,sampleSize,destinationAvailability.get(lookupIndex));

        soaResult.setSample(soaModel.getSampleOfAlternatives());
        soaResult.setCorrections(soaModel.getSampleCorrectionFactors());
        return soaResult;
    }

}
