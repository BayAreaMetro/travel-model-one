package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.DestChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;


public class MtcDestChoiceDMU extends DestChoiceDMU {

    int[] zoneTableRow;
    int[] county;

    private int amPmlogsumIndex;
    private int amMdlogsumIndex;
    private int mdMdlogsumIndex;

    
    
    public MtcDestChoiceDMU( TazDataIf tazDataManager, ModelStructure modelStructure ) {
        super( tazDataManager, modelStructure );
        setup( tazDataManager );
        setupMethodIndexMap();
    }


    private void setup( TazDataIf tazDataManager ) {

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        county = tazDataManager.getZonalCounty();

        amPmlogsumIndex = modelStructure.getSkimPeriodCombinationIndex( modelStructure.getDefaultAmHour(), modelStructure.getDefaultPmHour() );
        amMdlogsumIndex = modelStructure.getSkimPeriodCombinationIndex( modelStructure.getDefaultAmHour(), modelStructure.getDefaultMdHour() );
        mdMdlogsumIndex = modelStructure.getSkimPeriodCombinationIndex( modelStructure.getDefaultMdHour(), modelStructure.getDefaultMdHour() );
    }
    
    
    public int getOriginCounty() {
        int index = zoneTableRow[dmuIndex.getOriginZone()] - 1;
        return county[index];
    }

    public int getDestCountyAlt( int alt ) {
        int destZone = altToZone[alt];
        int index = zoneTableRow[destZone] - 1;
        return county[index];
    }
    
    public void setMcLogsum( int index, int zone, int subzone, double logsum ){
        modeChoiceLogsums[index][zone][subzone] = logsum;
    }

    
    public double getLogsumAMPMDestAlt ( int alt ) {
        int zone = altToZone[alt];
        int subZone = altToSubZone[alt];
        return getMcLogsumDestAlt( amPmlogsumIndex, zone, subZone );
    }
    
    public double getLogsumAMMDDestAlt ( int alt ) {
        int zone = altToZone[alt];
        int subZone = altToSubZone[alt];
        return getMcLogsumDestAlt( amMdlogsumIndex, zone, subZone );
    }
    
    public double getLogsumMDMDDestAlt ( int alt ) {
        int zone = altToZone[alt];
        int subZone = altToSubZone[alt];
        return getMcLogsumDestAlt( mdMdlogsumIndex, zone, subZone );
    }
    

    public int getHhIncomeInDollars() {
    	return hh.getIncomeInDollars(); 
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return hh.getHAnalyst();
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst(){
    	return person.getPAnalyst();
    }

    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getDcSoaCorrectionsAlt", 0 );
        methodIndexMap.put( "getDestCountyAlt", 1 );
        methodIndexMap.put( "getLnWorkLowDcSizeAlt", 2 );
        methodIndexMap.put( "getLnWorkMedDcSizeAlt", 3 );
        methodIndexMap.put( "getLnWorkHighDcSizeAlt", 4 );
        methodIndexMap.put( "getLnWorkVeryHighDcSizeAlt", 5 );
        methodIndexMap.put( "getLnUnivDcSizeAlt", 6 );
        methodIndexMap.put( "getLnGradeDcSizeAlt", 7 );
        methodIndexMap.put( "getLnHighDcSizeAlt", 8 );
        methodIndexMap.put( "getLnEscortKidsDcSizeAlt", 9 );
        methodIndexMap.put( "getLnEscortNoKidsDcSizeAlt", 10 );
        methodIndexMap.put( "getLnShoppingDcSizeAlt", 11 );
        methodIndexMap.put( "getLnEatOutDcSizeAlt", 12 );
        methodIndexMap.put( "getLnOthMaintDcSizeAlt", 13 );
        methodIndexMap.put( "getLnSocialDcSizeAlt", 14 );
        methodIndexMap.put( "getLnOthDiscrDcSizeAlt", 15 );
        methodIndexMap.put( "getLnWrkBasedDcSizeAlt", 16 );
        methodIndexMap.put( "getLogsumAMPMDestAlt", 17 );
        methodIndexMap.put( "getLogsumAMMDDestAlt", 18 );
        methodIndexMap.put( "getLogsumMDMDDestAlt", 19 );
        methodIndexMap.put( "getHhIncomeInDollars", 20 );
        methodIndexMap.put( "getOriginCounty", 21 );
        methodIndexMap.put( "getWorkTaz", 22 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 23 );
        methodIndexMap.put( "getPAnalyst", 24 );
    }
    
    
    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getDcSoaCorrectionsAlt( arrayIndex );
            case 1: return getDestCountyAlt( arrayIndex );
            case 2: return getLnDcSizeForPurposeAlt( arrayIndex, "work_low" );
            case 3: return getLnDcSizeForPurposeAlt( arrayIndex, "work_med" );
            case 4: return getLnDcSizeForPurposeAlt( arrayIndex, "work_high" );
            case 5: return getLnDcSizeForPurposeAlt( arrayIndex, "work_very high" );
            case 6: return getLnDcSizeForPurposeAlt( arrayIndex, "university" );
            case 7: return getLnDcSizeForPurposeAlt( arrayIndex, "school_grade" );
            case 8: return getLnDcSizeForPurposeAlt( arrayIndex, "school_high" );
            case 9: return getLnDcSizeForPurposeAlt( arrayIndex, "escort_kids" );
            case 10: return getLnDcSizeForPurposeAlt( arrayIndex, "escort_no kids" );
            case 11: return getLnDcSizeForPurposeAlt( arrayIndex, "shopping" );
            case 12: return getLnDcSizeForPurposeAlt( arrayIndex, "eatOut" );
            case 13: return getLnDcSizeForPurposeAlt( arrayIndex, "othMaint" );
            case 14: return getLnDcSizeForPurposeAlt( arrayIndex, "social" );
            case 15: return getLnDcSizeForPurposeAlt( arrayIndex, "othDiscr" );
            case 16: return getLnDcSizeForPurposeAlt( arrayIndex, "atwork" );
            case 17: return getLogsumAMPMDestAlt( arrayIndex );
            case 18: return getLogsumAMMDDestAlt( arrayIndex );
            case 19: return getLogsumMDMDDestAlt( arrayIndex );
            case 20: return getHhIncomeInDollars();
            case 21: return getOriginCounty();
            case 22: return getWorkTaz();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 23: return getHAnalyst();
            case 24: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }


}