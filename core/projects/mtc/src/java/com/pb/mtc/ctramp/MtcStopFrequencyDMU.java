package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.StopFrequencyDMU;


public class MtcStopFrequencyDMU extends StopFrequencyDMU {


    public MtcStopFrequencyDMU( ModelStructure modelStructure ) {
        super ( modelStructure );
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
        
        methodIndexMap.put( "getOriginAreaType", 0 );
        methodIndexMap.put( "getDestinationAreaType", 1 );
        methodIndexMap.put( "getIncomeInDollars", 2 );
        methodIndexMap.put( "getNumPersons", 3 );
        methodIndexMap.put( "getNumFullWork", 4 );
        methodIndexMap.put( "getNumStudent", 5 );
        methodIndexMap.put( "getNumVeh", 6 );
        methodIndexMap.put( "getCarSuff", 7 );
        methodIndexMap.put( "getNAge0to4", 8 );
        methodIndexMap.put( "getNAge5to15", 9 );
        methodIndexMap.put( "getNAdult", 10 );
        methodIndexMap.put( "getGenderIsFemale", 11 );
        methodIndexMap.put( "getStartTime", 12 );
        methodIndexMap.put( "getEndTime", 13 );
        methodIndexMap.put( "getNumAtWorkSubTours", 14 );
        methodIndexMap.put( "getNumWorkTours", 15 );
        methodIndexMap.put( "getNumUnivTours", 16 );
        methodIndexMap.put( "getNumSchoolTours", 17 );
        methodIndexMap.put( "getNumEscortTours", 18 );
        methodIndexMap.put( "getNumHShopTours", 19 );
        methodIndexMap.put( "getNumShopTours", 20 );
        methodIndexMap.put( "getNumHMaintTours", 21 );
        methodIndexMap.put( "getNumMaintTours", 22 );
        methodIndexMap.put( "getNumEatOutTours", 23 );
        methodIndexMap.put( "getNumVisitTours", 24 );
        methodIndexMap.put( "getTourIsJoint", 25 );
        methodIndexMap.put( "getTourIsVisit", 26 );
        methodIndexMap.put( "getNumPersonsInJointTour", 27 );
        methodIndexMap.put( "getJointTourHasAdultsOnly", 28 );
        methodIndexMap.put( "getTourModeIsTransit", 29 );
        methodIndexMap.put( "getTourModeIsDriveTransit", 30 );
        methodIndexMap.put( "getTourModeIsSchoolBus", 31 );
        methodIndexMap.put( "getTourModeIsNonMotorized", 32 );
        methodIndexMap.put( "getAccesibilityAtDestination", 33 );
        methodIndexMap.put( "getAccesibilityAtOrigin", 34 );
        methodIndexMap.put( "getNumStopsAlt", 35 );
        methodIndexMap.put( "getNumIbStopsAlt", 36 );
        methodIndexMap.put( "getNumObStopsAlt", 37 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 38 );
        methodIndexMap.put( "getPAnalyst", 39 );
    }
    
    



    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getOriginAreaType();
            case 1: return getDestinationAreaType();
            case 2: return getIncomeInDollars();
            case 3: return getNumPersons();
            case 4: return getNumFullWork();
            case 5: return getNumStudent();
            case 6: return getNumVeh();
            case 7: return getCarSuff();
            case 8: return getNAge0to4();
            case 9: return getNAge5to15();
            case 10: return getNAdult();
            case 11: return getGenderIsFemale();
            case 12: return getStartTime();
            case 13: return getEndTime();
            case 14: return getNumAtWorkSubTours();
            case 15: return getNumWorkTours();
            case 16: return getNumUnivTours();
            case 17: return getNumSchoolTours();
            case 18: return getNumEscortTours();
            case 19: return getNumHShopTours();
            case 20: return getNumShopTours();
            case 21: return getNumHMaintTours();
            case 22: return getNumMaintTours();
            case 23: return getNumEatOutTours();
            case 24: return getNumVisitTours();
            case 25: return getTourIsJoint();
            case 26: return getTourIsVisit();
            case 27: return getNumPersonsInJointTour();
            case 28: return getJointTourHasAdultsOnly();
            case 29: return getTourModeIsTransit();
            case 30: return getTourModeIsDriveTransit();
            case 31: return getTourModeIsSchoolBus();
            case 32: return getTourModeIsNonMotorized();
            case 33: return getAccesibilityAtDestination();
            case 34: return getAccesibilityAtOrigin();
            case 35: return getNumStopsAlt( arrayIndex );
            case 36: return getNumIbStopsAlt( arrayIndex );
            case 37: return getNumObStopsAlt( arrayIndex );
            // guojy: added for M. Gucwa's research on automated vehicles
            case 38: return getHAnalyst();
            case 39: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}