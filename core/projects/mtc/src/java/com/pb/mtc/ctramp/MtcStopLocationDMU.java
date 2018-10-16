package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.StopLocationDMU;
import com.pb.models.ctramp.TazDataIf;


public class MtcStopLocationDMU extends StopLocationDMU {


    
    public MtcStopLocationDMU( TazDataIf tazDataManager, ModelStructure modelStructure ) {
        super ( tazDataManager, modelStructure );
        setupMethodIndexMap();
    }


    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return household.getHAnalyst();
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst(){
    	return person.getPAnalyst();
    }
    
    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getDcSoaCorrectionsAlt", 0 );
        methodIndexMap.put( "getTripModeChoiceLogsumOrigToStopAlt", 1 );
        methodIndexMap.put( "getTripModeChoiceLogsumStopAltToDest", 2 );
        methodIndexMap.put( "getStopDestAreaTypeAlt", 3 );
        methodIndexMap.put( "getStopPurposeIsWork", 4 );
        methodIndexMap.put( "getStopPurposeIsEscort", 5 );
        methodIndexMap.put( "getStopPurposeIsShopping", 6 );
        methodIndexMap.put( "getStopPurposeIsEatOut", 7 );
        methodIndexMap.put( "getStopPurposeIsOthMaint", 8 );
        methodIndexMap.put( "getStopPurposeIsSocial", 9 );
        methodIndexMap.put( "getStopPurposeIsOthDiscr", 10 );
        methodIndexMap.put( "getTourOriginZone", 11 );
        methodIndexMap.put( "getTourDestZone", 12 );
        methodIndexMap.put( "getTourMode", 13 );
        methodIndexMap.put( "getStopNumber", 14 );
        methodIndexMap.put( "getInboundStop", 15 );
        methodIndexMap.put( "getTourIsJoint", 16 );
        methodIndexMap.put( "getLnStopDcSizeAlt", 17 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 18 );
        methodIndexMap.put( "getPAnalyst", 19 );
   }
    
    


    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getDcSoaCorrectionsAlt( arrayIndex );
            case 1: return getTripModeChoiceLogsumOrigToStopAlt( arrayIndex );
            case 2: return getTripModeChoiceLogsumStopAltToDest( arrayIndex );
            case 3: return getStopDestAreaTypeAlt( arrayIndex );
            case 4: return getStopPurposeIsWork();
            case 5: return getStopPurposeIsEscort();
            case 6: return getStopPurposeIsShopping();
            case 7: return getStopPurposeIsEatOut();
            case 8: return getStopPurposeIsOthMaint();
            case 9: return getStopPurposeIsSocial();
            case 10: return getStopPurposeIsOthDiscr();
            case 11: return getTourOriginZone();
            case 12: return getTourDestZone();
            case 13: return getTourMode();
            case 14: return getStopNumber();
            case 15: return getInboundStop();
            case 16: return getTourIsJoint();
            case 17: return getLnStopDcSizeAlt( arrayIndex );
            // guojy: added for M. Gucwa's research on automated vehicles
            case 18: return getHAnalyst();
            case 19: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}