package com.pb.mtc.ctramp;

import java.util.HashMap;

import org.apache.log4j.Logger;
import com.pb.models.ctramp.IndividualMandatoryTourFrequencyDMU;

public class MtcIndividualMandatoryTourFrequencyDMU extends IndividualMandatoryTourFrequencyDMU {

    public static Logger logger = Logger.getLogger(MtcIndividualMandatoryTourFrequencyDMU.class);


    public MtcIndividualMandatoryTourFrequencyDMU(){
    	super();
    	setupMethodIndexMap();
    }
    
    public int getIncomeHigherThan50k () {
    	if (household.getIncomeInDollars() > 50000) return 1; 
    	else return 0; 
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
        
        methodIndexMap.put( "getFullTimeWorker", 0 );
        methodIndexMap.put( "getPartTimeWorker", 1 );
        methodIndexMap.put( "getUniversityStudent", 2 );
        methodIndexMap.put( "getNonWorkingAdult", 3 );
        methodIndexMap.put( "getRetired", 4 );
        methodIndexMap.put( "getDrivingAgeSchoolChild", 5 );
        methodIndexMap.put( "getPreDrivingAgeSchoolChild", 6 );
        methodIndexMap.put( "getFemale", 7 );
        methodIndexMap.put( "getAge", 8 );
        methodIndexMap.put( "getStudentIsEmployed", 9 );
        methodIndexMap.put( "getNonStudentGoesToSchool", 10 );
        methodIndexMap.put( "getAutos", 11 );
        methodIndexMap.put( "getDrivers", 12 );
        methodIndexMap.put( "getPreschoolChildren", 13 );
        methodIndexMap.put( "getNonWorkers", 14 );
        methodIndexMap.put( "getIncomeHigherThan50k", 15 );
        methodIndexMap.put( "getNonFamilyHousehold", 16 );
        methodIndexMap.put( "getChildrenUnder16NotAtSchool", 17 );
        methodIndexMap.put( "getAreaType", 18 );
        methodIndexMap.put( "getUsualWorkLocation", 19 );
        methodIndexMap.put( "getUsualSchoolLocation", 20 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 21 );
        methodIndexMap.put( "getPAnalyst", 22 );
    }
    


    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getFullTimeWorker();
            case 1: return getPartTimeWorker();
            case 2: return getUniversityStudent();
            case 3: return getNonWorkingAdult();
            case 4: return getRetired();
            case 5: return getDrivingAgeSchoolChild();
            case 6: return getPreDrivingAgeSchoolChild();
            case 7: return getFemale();
            case 8: return getAge();
            case 9: return getStudentIsEmployed();
            case 10: return getNonStudentGoesToSchool();
            case 11: return getAutos();
            case 12: return getDrivers();
            case 13: return getPreschoolChildren();
            case 14: return getNonWorkers();
            case 15: return getIncomeHigherThan50k();
            case 16: return getNonFamilyHousehold();
            case 17: return getChildrenUnder16NotAtSchool();
            case 18: return getAreaType();
            case 19: return getUsualWorkLocation();
            case 20: return getUsualSchoolLocation();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 21: return getHAnalyst();
            case 22: return getPAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }
    
}