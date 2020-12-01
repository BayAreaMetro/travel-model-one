package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.CoordinatedDailyActivityPatternDMU;


public class MtcCoordinatedDailyActivityPatternDMU extends CoordinatedDailyActivityPatternDMU {


    public MtcCoordinatedDailyActivityPatternDMU() {
        super ();
        setupMethodIndexMap();
    }


    // household income
    public int getIncomeLess20k(){
    	if (householdObject.getIncomeInDollars() < 20000) return 1; 
    	else return 0; 
    }
    
    public int getIncome50to100k(){
    	int income = householdObject.getIncomeInDollars(); 
    	if ((income>=50000) && (income < 100000)) return 1; 
    	else return 0; 
    }
    
    public int getIncomeMore100k(){
    	if (householdObject.getIncomeInDollars() >= 100000) return 1; 
    	else return 0; 
    }
 
    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return householdObject.getHAnalyst();
    }

    // added for cdap-worktaz
    public int getUsualWorkLocationA(){
        return personA.getPersonWorkLocationZone();
    }


    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getFullTimeWorkerA", 0 );
        methodIndexMap.put( "getFullTimeWorkerB", 1 );
        methodIndexMap.put( "getFullTimeWorkerC", 2 );
        methodIndexMap.put( "getPartTimeWorkerA", 3 );
        methodIndexMap.put( "getPartTimeWorkerB", 4 );
        methodIndexMap.put( "getPartTimeWorkerC", 5 );
        methodIndexMap.put( "getUniversityStudentA", 6 );
        methodIndexMap.put( "getUniversityStudentB", 7 );
        methodIndexMap.put( "getUniversityStudentC", 8 );
        methodIndexMap.put( "getNonWorkingAdultA", 9 );
        methodIndexMap.put( "getNonWorkingAdultB", 10 );
        methodIndexMap.put( "getNonWorkingAdultC", 11 );
        methodIndexMap.put( "getRetiredA", 12 );
        methodIndexMap.put( "getRetiredB", 13 );
        methodIndexMap.put( "getRetiredC", 14 );
        methodIndexMap.put( "getDrivingAgeSchoolChildA", 15 );
        methodIndexMap.put( "getDrivingAgeSchoolChildB", 16 );
        methodIndexMap.put( "getDrivingAgeSchoolChildC", 17 );
        methodIndexMap.put( "getPreDrivingAgeSchoolChildA", 18 );
        methodIndexMap.put( "getPreDrivingAgeSchoolChildB", 19 );
        methodIndexMap.put( "getPreDrivingAgeSchoolChildC", 20 );
        methodIndexMap.put( "getPreSchoolChildA", 21 );
        methodIndexMap.put( "getPreSchoolChildB", 22 );
        methodIndexMap.put( "getPreSchoolChildC", 23 );
        methodIndexMap.put( "getAgeA", 24 );
        methodIndexMap.put( "getFemaleA", 25 );
        methodIndexMap.put( "getMoreCarsThanWorkers", 26 );
        methodIndexMap.put( "getFewerCarsThanWorkers", 27 );
        methodIndexMap.put( "getIncomeLess20k", 28 );
        methodIndexMap.put( "getIncome50to100k", 29 );
        methodIndexMap.put( "getIncomeMore100k", 30 );
        methodIndexMap.put( "getUsualWorkLocationIsHome", 31 );
        methodIndexMap.put( "getNoUsualWorkLocation", 32 );
        methodIndexMap.put( "getNoUsualSchoolLocation", 33 );
        methodIndexMap.put( "getHhSize", 34 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 35 );
        // added for cdap-worktaz
        methodIndexMap.put( "getUsualWorkLocationA", 36);
    }
    
    



    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getFullTimeWorkerA();
            case 1: return getFullTimeWorkerB();
            case 2: return getFullTimeWorkerC();
            case 3: return getPartTimeWorkerA();
            case 4: return getPartTimeWorkerB();
            case 5: return getPartTimeWorkerC();
            case 6: return getUniversityStudentA();
            case 7: return getUniversityStudentB();
            case 8: return getUniversityStudentC();
            case 9: return getNonWorkingAdultA();
            case 10: return getNonWorkingAdultB();
            case 11: return getNonWorkingAdultC();
            case 12: return getRetiredA();
            case 13: return getRetiredB();
            case 14: return getRetiredC();
            case 15: return getDrivingAgeSchoolChildA();
            case 16: return getDrivingAgeSchoolChildB();
            case 17: return getDrivingAgeSchoolChildC();
            case 18: return getPreDrivingAgeSchoolChildA();
            case 19: return getPreDrivingAgeSchoolChildB();
            case 20: return getPreDrivingAgeSchoolChildC();
            case 21: return getPreSchoolChildA();
            case 22: return getPreSchoolChildB();
            case 23: return getPreSchoolChildC();
            case 24: return getAgeA();
            case 25: return getFemaleA();
            case 26: return getMoreCarsThanWorkers();
            case 27: return getFewerCarsThanWorkers();
            case 28: return getIncomeLess20k();
            case 29: return getIncome50to100k();
            case 30: return getIncomeMore100k();
            case 31: return getUsualWorkLocationIsHome();
            case 32: return getNoUsualWorkLocation();
            case 33: return getNoUsualSchoolLocation();
            case 34: return getHhSize();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 35: return getHAnalyst();
            // added for cdap-worktaz
            case 36: return getUsualWorkLocationA();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}