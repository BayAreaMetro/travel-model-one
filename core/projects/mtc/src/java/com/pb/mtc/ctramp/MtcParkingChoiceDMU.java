package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ParkingChoiceDMU;
import com.pb.models.ctramp.TazDataIf;



public class MtcParkingChoiceDMU extends ParkingChoiceDMU {

    
    public MtcParkingChoiceDMU( TazDataIf tazDataManager ){
        super( tazDataManager );
        setupMethodIndexMap();
    }
    


    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();

        methodIndexMap.put( "getParkTazCbdAreaTypeAlt", 0 );
    }
    




    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
        	case 0: return getParkTazCbdAreaTypeAlt( arrayIndex );

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }

}