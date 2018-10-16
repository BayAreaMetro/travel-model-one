package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.StopDCSoaDMU;
import com.pb.models.ctramp.TazDataIf;


public class MtcStopDCSoaDMU extends StopDCSoaDMU {


    public MtcStopDCSoaDMU( TazDataIf tazDataManager, ModelStructure modelStructure ) {
        super ( tazDataManager, modelStructure );
        setupMethodIndexMap();
    }

    
    
    public int getTourTodOut() {
        return getTod( tour.getTourStartHour() );
    }

    public int getTourTodIn() {
        return getTod( tour.getTourEndHour() );
    }

    // private methods
    
    // TODO: check if the hours are consistent with those used for skim periods  
    private int getTod(int hour) {

        int timePeriod = 0;

        if ( hour >= 3 && hour < 6 )
            timePeriod = 1;
        else if ( hour < 10 )
            timePeriod = 2;
        else if ( hour <= 12 )
            timePeriod = 3;
        else if ( hour < 15 )
            timePeriod = 4;
        else if ( hour < 19 )
            timePeriod = 5;
        else if ( hour <= 21 )
            timePeriod = 6;
        else
            timePeriod = 7;

        return timePeriod;

    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return tour.getPersonObject().getHouseholdObject().getHAnalyst();
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst(){
    	return tour.getPersonObject().getPAnalyst();
    }


    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getInboundStop", 0 );
        methodIndexMap.put( "getTourIsJoint", 1 );
        methodIndexMap.put( "getTourModeIsWalk", 2 );
        methodIndexMap.put( "getTourModeIsBike", 3 );
        methodIndexMap.put( "getTourModeIsWalkTransit", 4 );
        methodIndexMap.put( "getTourTodOut", 5 );
        methodIndexMap.put( "getTourTodIn", 6 );
        methodIndexMap.put( "getTourOriginZone", 7 );
        methodIndexMap.put( "getTourDestZone", 8 );
        methodIndexMap.put( "getLnStopDcSizeAlt", 9 );
        methodIndexMap.put( "getStopDestAreaTypeAlt", 10 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 11 );
        methodIndexMap.put( "getPAnalyst", 12 );

    }
    
    


    public int getIndexValue(String variableName) {
        return methodIndexMap.get(variableName);
    }



    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getInbound();
            case 1: return getTourIsJoint();
            case 2: return getTourModeIsWalk();
            case 3: return getTourModeIsBike();
            case 4: return getTourModeIsWalkTransit();
            case 5: return getTourTodOut();
            case 6: return getTourTodIn();
            case 7: return getTourOriginZone();
            case 8: return getTourDestZone();
            case 9: return getLnStopDcSizeAlt( arrayIndex );
            case 10: return getStopDestAreaTypeAlt( arrayIndex );
            // guojy: added for M. Gucwa's research on automated vehicles
            case 11: return getHAnalyst();
            case 12: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}