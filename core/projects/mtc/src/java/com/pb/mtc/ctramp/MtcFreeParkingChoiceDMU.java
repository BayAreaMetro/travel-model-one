package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.FreeParkingChoiceDMU;


public class MtcFreeParkingChoiceDMU extends FreeParkingChoiceDMU {


    public MtcFreeParkingChoiceDMU() {
        super();
        setupMethodIndexMap();
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
        
        methodIndexMap.put( "getHhIncomeInDollars", 0 );
        methodIndexMap.put( "getAutoOwnership", 1 );
        methodIndexMap.put( "getFtwkPersons", 2 );
        methodIndexMap.put( "getPtwkPersons", 3 );
        methodIndexMap.put( "getSize", 4 );
        methodIndexMap.put( "getWorkLocation", 5); 
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 6 );
        methodIndexMap.put( "getPAnalyst", 7 );
    }
    
    


    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getHhIncomeInDollars();
            case 1: return getAutoOwnership();
            case 2: return getFtwkPersons();
            case 3: return getPtwkPersons();
            case 4: return getSize();
            case 5: return getWorkLocation(); 
            // guojy: added for M. Gucwa's research on automated vehicles
            case 6: return getHAnalyst();
            case 7: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}