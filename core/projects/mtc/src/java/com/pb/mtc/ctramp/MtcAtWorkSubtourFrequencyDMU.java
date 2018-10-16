package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.AtWorkSubtourFrequencyDMU;
import com.pb.models.ctramp.ModelStructure;

public class MtcAtWorkSubtourFrequencyDMU extends AtWorkSubtourFrequencyDMU {

    
    public MtcAtWorkSubtourFrequencyDMU( ModelStructure modelStructure ){
        super( modelStructure );
        this.modelStructure = modelStructure;
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
        methodIndexMap.put( "getNumAutos", 1 );
        methodIndexMap.put( "getPersonIsFullTimeWorker", 2 );
        methodIndexMap.put( "getPersonIsNonworker", 3 );
        methodIndexMap.put( "getWorkTazAreaType", 4 );
        methodIndexMap.put( "getWorkTourDuration", 5 );
        methodIndexMap.put( "getJointMaintShopEatPerson", 6 );
        methodIndexMap.put( "getJointDiscrPerson", 7 );
        methodIndexMap.put( "getIndivMaintShopEscortFt", 8 );
        methodIndexMap.put( "getIndivMaintShopEscortPt", 9 );
        methodIndexMap.put( "getIndivDiscrFt", 10 );
        methodIndexMap.put( "getIndivDiscrPt", 11 );
        methodIndexMap.put( "getIndivEatOut", 12 );
        methodIndexMap.put( "getWorkTourModeIsSOV", 13 );
        methodIndexMap.put( "getNumPersonWorkTours", 14 );
        methodIndexMap.put( "getWorkStudNonMandatoryTours", 15 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 16 );
        methodIndexMap.put( "getPAnalyst", 17 );
    } 
    

    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getHhIncomeInDollars();
            case 1: return getNumAutos();
            case 2: return getPersonIsFullTimeWorker();
            case 3: return getPersonIsNonworker();
            case 4: return getWorkTazAreaType();
            case 5: return getWorkTourDuration();
            case 6: return getJointMaintShopEatPerson();
            case 7: return getJointDiscrPerson();
            case 8: return getIndivMaintShopEscortFt();
            case 9: return getIndivMaintShopEscortPt();
            case 10: return getIndivDiscrFt();
            case 11: return getIndivDiscrPt();
            case 12: return getIndivEatOut();
            case 13: return getWorkTourModeIsSOV();
            case 14: return getNumPersonWorkTours();
            case 15: return getWorkStudNonMandatoryTours();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 16: return getHAnalyst();
            case 17: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }


}
