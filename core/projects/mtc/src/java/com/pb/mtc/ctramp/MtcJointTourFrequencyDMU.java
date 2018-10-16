package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.JointTourFrequencyDMU;
import com.pb.models.ctramp.ModelStructure;

public class MtcJointTourFrequencyDMU extends JointTourFrequencyDMU {

    
    public MtcJointTourFrequencyDMU( ModelStructure modelStructure ){
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
    	return tour.getPersonObject().getPAnalyst();
    }



    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getStayHomePatternCountFullTime", 0 );
        methodIndexMap.put( "getStayHomePatternCountPartTime", 1 );
        methodIndexMap.put( "getStayHomePatternCountHomemaker", 2 );
        methodIndexMap.put( "getStayHomePatternCountRetiree", 3 );
        methodIndexMap.put( "getStayHomePatternCountUnivDrivingStudent", 4 );
        methodIndexMap.put( "getStayHomePatternCountNonDrivingChild", 5 );
        methodIndexMap.put( "getNonMandatoryPatternCountFullTime", 6 );
        methodIndexMap.put( "getNonMandatoryPatternCountPartTime", 7 );
        methodIndexMap.put( "getNonMandatoryPatternCountHomemaker", 8 );
        methodIndexMap.put( "getNonMandatoryPatternCountRetiree", 9 );
        methodIndexMap.put( "getNonMandatoryPatternCountUnivDrivingStudent", 10 );
        methodIndexMap.put( "getNonMandatoryPatternCountNonDrivingChild", 11 );
        methodIndexMap.put( "getMandatoryPatternCountFullTime", 12 );
        methodIndexMap.put( "getMandatoryPatternCountDrivingStudent", 13 );
        methodIndexMap.put( "getMandatoryPatternCountNonDrivingChild", 14 );
        methodIndexMap.put( "getTimeWindowOverlapAdult", 15 );
        methodIndexMap.put( "getTimeWindowOverlapChild", 16 );
        methodIndexMap.put( "getTimeWindowOverlapAdultChild", 17 );
        methodIndexMap.put( "getIncomeBetween50And100", 18 );
        methodIndexMap.put( "getIncomeGreaterThan100", 19 );
        methodIndexMap.put( "getAutosInHH", 20 );
        methodIndexMap.put( "getDriverCount", 21 );
        methodIndexMap.put( "getWorkerCount", 22 );
        methodIndexMap.put( "getWalkRetailAccessibility", 23 );
        methodIndexMap.put( "getHhIncomeInDollars", 24 );
        methodIndexMap.put( "getHouseholdSize", 25 );
        methodIndexMap.put( "getCarsEqualsWorkers", 26 );
        methodIndexMap.put( "getMoreCarsThanWorkers", 27 );
        methodIndexMap.put( "getNumAdults", 28 );
        methodIndexMap.put( "getNumChildren", 29 );
        methodIndexMap.put( "getPersonIsAdult", 30 );
        methodIndexMap.put( "getPersonIsChild", 31 );
        methodIndexMap.put( "getPersonIsFullTimeWorker", 32 );
        methodIndexMap.put( "getPersonIsPartTimeWorker", 33 );
        methodIndexMap.put( "getPersonIsUniversity", 34 );
        methodIndexMap.put( "getPersonIsNonworker", 35 );
        methodIndexMap.put( "getPersonIsPreschool", 36 );
        methodIndexMap.put( "getPersonIsStudentNonDriving", 37 );
        methodIndexMap.put( "getPersonIsStudentDriving", 38 );
        methodIndexMap.put( "getPersonStaysHome", 39 );
        methodIndexMap.put( "getFullTimeWorkers", 40 );
        methodIndexMap.put( "getPartTimeWorkers", 41 );
        methodIndexMap.put( "getUniversityStudents", 42 );
        methodIndexMap.put( "getNonWorkers", 43 );
        methodIndexMap.put( "getDrivingAgeStudents", 44 );
        methodIndexMap.put( "getNonDrivingAgeStudents", 45 );
        methodIndexMap.put( "getPreSchoolers", 46 );
        methodIndexMap.put( "getHomeTazIsUrban", 47 );
        methodIndexMap.put( "getHomeTazIsSuburban", 48 );
        methodIndexMap.put( "getMaxAdultOverlaps", 49 );
        methodIndexMap.put( "getMaxChildOverlaps", 50 );
        methodIndexMap.put( "getMaxMixedOverlaps", 51 );
        methodIndexMap.put( "getMaxPairwiseOverlapAdult", 52 );
        methodIndexMap.put( "getMaxPairwiseOverlapChild", 53 );
        methodIndexMap.put( "getTravelActiveAdults", 54 );
        methodIndexMap.put( "getTravelActiveChildren", 55 );
        methodIndexMap.put( "getTourPurposeIsEat", 56 );
        methodIndexMap.put( "getTourPurposeIsDiscretionary", 57 );
        methodIndexMap.put( "getJointTourComposition", 58 );
        methodIndexMap.put( "getJointTourPurposeIndex", 59 );
        methodIndexMap.put( "getJTours", 60 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 61 );
        methodIndexMap.put( "getPAnalyst", 62 );
        
    }
    
    
    
    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getStayHomePatternCountFullTime();
            case 1: return getStayHomePatternCountPartTime();
            case 2: return getStayHomePatternCountHomemaker();
            case 3: return getStayHomePatternCountRetiree();
            case 4: return getStayHomePatternCountUnivDrivingStudent();
            case 5: return getStayHomePatternCountNonDrivingChild();
            case 6: return getNonMandatoryPatternCountFullTime();
            case 7: return getNonMandatoryPatternCountPartTime();
            case 8: return getNonMandatoryPatternCountHomemaker();
            case 9: return getNonMandatoryPatternCountRetiree();
            case 10: return getNonMandatoryPatternCountUnivDrivingStudent();
            case 11: return getNonMandatoryPatternCountNonDrivingChild();
            case 12: return getMandatoryPatternCountFullTime();
            case 13: return getMandatoryPatternCountDrivingStudent();
            case 14: return getMandatoryPatternCountNonDrivingChild();
            case 15: return getTimeWindowOverlapAdult();
            case 16: return getTimeWindowOverlapChild();
            case 17: return getTimeWindowOverlapAdultChild();
            case 18: return getIncomeBetween50And100();
            case 19: return getIncomeGreaterThan100();
            case 20: return getAutosInHH();
            case 21: return getDriverCount();
            case 22: return getWorkerCount();
            case 23: return getWalkRetailAccessibility();
            case 24: return getHhIncomeInDollars();
            case 25: return getHouseholdSize();
            case 26: return getCarsEqualsWorkers();
            case 27: return getMoreCarsThanWorkers();
            case 28: return getNumAdults();
            case 29: return getNumChildren();
            case 30: return getPersonIsAdult();
            case 31: return getPersonIsChild();
            case 32: return getPersonIsFullTimeWorker();
            case 33: return getPersonIsPartTimeWorker();
            case 34: return getPersonIsUniversity();
            case 35: return getPersonIsNonworker();
            case 36: return getPersonIsPreschool();
            case 37: return getPersonIsStudentNonDriving();
            case 38: return getPersonIsStudentDriving();
            case 39: return getPersonStaysHome();
            case 40: return getFullTimeWorkers();
            case 41: return getPartTimeWorkers();
            case 42: return getUniversityStudents();
            case 43: return getNonWorkers();
            case 44: return getDrivingAgeStudents();
            case 45: return getNonDrivingAgeStudents();
            case 46: return getPreSchoolers();
            case 47: return getHomeTazIsUrban();
            case 48: return getHomeTazIsSuburban();
            case 49: return getMaxAdultOverlaps();
            case 50: return getMaxChildOverlaps();
            case 51: return getMaxMixedOverlaps();
            case 52: return getMaxPairwiseOverlapAdult();
            case 53: return getMaxPairwiseOverlapChild();
            case 54: return getTravelActiveAdults();
            case 55: return getTravelActiveChildren();
            case 56: return getTourPurposeIsEat();
            case 57: return getTourPurposeIsDiscretionary();
            case 58: return getJointTourComposition();
            case 59: return getJointTourPurposeIndex();
            case 60: return getJTours();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 61: return getHAnalyst();
            case 62: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }


}
