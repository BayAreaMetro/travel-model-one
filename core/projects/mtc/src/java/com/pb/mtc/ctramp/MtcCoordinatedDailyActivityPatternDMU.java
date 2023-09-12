package com.pb.mtc.ctramp;

import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

import com.pb.models.ctramp.CoordinatedDailyActivityPatternDMU;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;

public class MtcCoordinatedDailyActivityPatternDMU extends CoordinatedDailyActivityPatternDMU {

    private Logger cdapLogger = Logger.getLogger("cdap");
    
    // industry-base simple model specification
    // wfh_rate = m*ln(income) + b
    public static final String PROPERTIES_WFH_AGREMP_M = "CDAP.WFH.CountyX.agremp.M";
    public static final String PROPERTIES_WFH_AGREMP_B = "CDAP.WFH.CountyX.agremp.B";
    public static final String PROPERTIES_WFH_FPSEMP_M = "CDAP.WFH.CountyX.fpsemp.M";
    public static final String PROPERTIES_WFH_FPSEMP_B = "CDAP.WFH.CountyX.fpsemp.B";
    public static final String PROPERTIES_WFH_HEREMP_M = "CDAP.WFH.CountyX.heremp.M";
    public static final String PROPERTIES_WFH_HEREMP_B = "CDAP.WFH.CountyX.heremp.B";
    public static final String PROPERTIES_WFH_MWTEMP_M = "CDAP.WFH.CountyX.mwtemp.M";
    public static final String PROPERTIES_WFH_MWTEMP_B = "CDAP.WFH.CountyX.mwtemp.B";
    public static final String PROPERTIES_WFH_OTHEMP_M = "CDAP.WFH.CountyX.othemp.M";
    public static final String PROPERTIES_WFH_OTHEMP_B = "CDAP.WFH.CountyX.othemp.B";
    public static final String PROPERTIES_WFH_RETEMP_M = "CDAP.WFH.CountyX.retemp.M";
    public static final String PROPERTIES_WFH_RETEMP_B = "CDAP.WFH.CountyX.retemp.B";
    // additional factors
    public static final String PROPERTIES_WFH_FULLTIMEWORKER_FACTOR = "CDAP.WFH.FullTimeWorker.Factor";
    public static final String PROPERTIES_WFH_PARTTIMEWORKER_FACTOR = "CDAP.WFH.PartTimeworker.Factor";

    // indexed by home county
    private float[] WFH_AGREMP_M; // Agriculture & Natural Resources
    private float[] WFH_AGREMP_B;
    private float[] WFH_FPSEMP_M; // Financial & Professional Services
    private float[] WFH_FPSEMP_B;
    private float[] WFH_HEREMP_M; // Health, Educational & Recreational Services
    private float[] WFH_HEREMP_B;
    private float[] WFH_MWTEMP_M; // Manufacturing, Wholesale & Transportation
    private float[] WFH_MWTEMP_B;
    private float[] WFH_OTHEMP_M; // Other
    private float[] WFH_OTHEMP_B;
    private float[] WFH_RETEMP_M; // Retail
    private float[] WFH_RETEMP_B;

    private float WFH_FULLTIMEWORKER_FACTOR;
    private float WFH_PARTTIMEWORKER_FACTOR;

    private int[] tazDataAgrEmpn;
    private int[] tazDataFpsEmpn;
    private int[] tazDataHerEmpn;
    private int[] tazDataMwtEmpn;
    private int[] tazDataOthEmpn;
    private int[] tazDataRetEmpn;
    private int[] tazDataTotEmp;

    TazDataIf tazDataManager;

    public MtcCoordinatedDailyActivityPatternDMU(TazDataIf tazData) {
        super ();
        setupMethodIndexMap();
        logger.info("MtcCoordinatedDailyActivityPatternDMU constructor; tazData=" + tazData);
        this.tazDataManager = tazData; // keep a reference to this
        this.tazDataAgrEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_AGR_NATRES_EMP_FIELD_NAME);
        this.tazDataFpsEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_FINANCE_PROF_EMP_FIELD_NAME);
        this.tazDataHerEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_HEALTH_EDU_REC_EMP_FIELD_NAME);
        this.tazDataMwtEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_MANU_WHOLESALE_TRANS_EMP_FIELD_NAME);
        this.tazDataOthEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_OTHER_EMP_FIELD_NAME);
        this.tazDataRetEmpn = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_RETAIL_EMP_FIELD_NAME);
        this.tazDataTotEmp  = tazData.getZoneTableIntColumn(MtcTazDataHandler.ZONE_DATA_EMP_FIELD_NAME);
        this.WFH_AGREMP_M = new float[9];
        this.WFH_AGREMP_B = new float[9];
        this.WFH_FPSEMP_M = new float[9];
        this.WFH_FPSEMP_B = new float[9];
        this.WFH_HEREMP_M = new float[9];
        this.WFH_HEREMP_B = new float[9];
        this.WFH_MWTEMP_M = new float[9];
        this.WFH_MWTEMP_B = new float[9];
        this.WFH_OTHEMP_M = new float[9];
        this.WFH_OTHEMP_B = new float[9];
        this.WFH_RETEMP_M = new float[9];
        this.WFH_RETEMP_B = new float[9];
    }

    public void setPropertyFileValues( HashMap<String, String> propertyMap) {
        for (int county_num=1; county_num<=9; county_num++) {
            this.WFH_AGREMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_AGREMP_M.replace("CountyX","County"+county_num)));
            this.WFH_AGREMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_AGREMP_B.replace("CountyX","County"+county_num)));
            this.WFH_FPSEMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_FPSEMP_M.replace("CountyX","County"+county_num)));
            this.WFH_FPSEMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_FPSEMP_B.replace("CountyX","County"+county_num)));
            this.WFH_HEREMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_HEREMP_M.replace("CountyX","County"+county_num)));
            this.WFH_HEREMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_HEREMP_B.replace("CountyX","County"+county_num)));
            this.WFH_MWTEMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_MWTEMP_M.replace("CountyX","County"+county_num)));
            this.WFH_MWTEMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_MWTEMP_B.replace("CountyX","County"+county_num)));
            this.WFH_OTHEMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_OTHEMP_M.replace("CountyX","County"+county_num)));
            this.WFH_OTHEMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_OTHEMP_B.replace("CountyX","County"+county_num)));
            this.WFH_RETEMP_M[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_RETEMP_M.replace("CountyX","County"+county_num)));
            this.WFH_RETEMP_B[county_num-1] = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_RETEMP_B.replace("CountyX","County"+county_num)));

            if (county_num==9) {
                cdapLogger.info("Read County9 properties agr-m:" + this.WFH_AGREMP_M[county_num-1] + "; agr-b:" + this.WFH_AGREMP_B[county_num-1]);
                cdapLogger.info("Read County9 properties fps-m:" + this.WFH_FPSEMP_M[county_num-1] + "; fps-b:" + this.WFH_FPSEMP_B[county_num-1]);
                cdapLogger.info("Read County9 properties her-m:" + this.WFH_HEREMP_M[county_num-1] + "; her-b:" + this.WFH_HEREMP_B[county_num-1]);
                cdapLogger.info("Read County9 properties mwt-m:" + this.WFH_MWTEMP_M[county_num-1] + "; mwt-b:" + this.WFH_MWTEMP_B[county_num-1]);
                cdapLogger.info("Read County9 properties oth-m:" + this.WFH_OTHEMP_M[county_num-1] + "; oth-b:" + this.WFH_OTHEMP_B[county_num-1]);
                cdapLogger.info("Read County9 properties ret-m:" + this.WFH_RETEMP_M[county_num-1] + "; ret-b:" + this.WFH_RETEMP_B[county_num-1]);
            }
        }

        this.WFH_FULLTIMEWORKER_FACTOR = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_FULLTIMEWORKER_FACTOR));
        this.WFH_PARTTIMEWORKER_FACTOR = Float.parseFloat(propertyMap.get(PROPERTIES_WFH_PARTTIMEWORKER_FACTOR));

        cdapLogger.info("Read properties fulltime worker factor:" + this.WFH_FULLTIMEWORKER_FACTOR + "; parttime worker factor:" + this.WFH_PARTTIMEWORKER_FACTOR);
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

    /**
	 * Simple works from home model for person based upon their household income and the industry
	 * mix at their work location TAZ.
	 * @param Logger
	 */
    public void setWorksFromHomeForPersonA(Logger cdapLogger) {
        if (personA.getPersonIsWorker() == 0) {
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.NOT_APPLICABLE.ordinal() );
            return;
        }
		int workLocation = personA.getPersonWorkLocationZone();
		if (workLocation == 0) {
            // I don't think this should happen
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.NOT_APPLICABLE.ordinal() );
			return;
		}
        // get household income and employment taz shares
		int hhinc = householdObject.getIncomeInDollars();
        if (hhinc < 0) {
            hhinc = 0;
        }
        double ln_hhinc = Math.log(hhinc);
        int homeCounty = this.tazDataManager.getZoneCounty(householdObject.getHhTaz());
        // https://github.com/BayAreaMetro/modeling-website/wiki/TazData

        // apply log model, constrained to [0.0, 1.0]
        double agr_wfh = Math.min(1.0, Math.max(0.0, this.WFH_AGREMP_M[homeCounty-1]*ln_hhinc + this.WFH_AGREMP_B[homeCounty-1]));
        double fps_wfh = Math.min(1.0, Math.max(0.0, this.WFH_FPSEMP_M[homeCounty-1]*ln_hhinc + this.WFH_FPSEMP_B[homeCounty-1]));
        double her_wfh = Math.min(1.0, Math.max(0.0, this.WFH_HEREMP_M[homeCounty-1]*ln_hhinc + this.WFH_HEREMP_B[homeCounty-1]));
        double mwt_wfh = Math.min(1.0, Math.max(0.0, this.WFH_MWTEMP_M[homeCounty-1]*ln_hhinc + this.WFH_MWTEMP_B[homeCounty-1]));
        double oth_wfh = Math.min(1.0, Math.max(0.0, this.WFH_OTHEMP_M[homeCounty-1]*ln_hhinc + this.WFH_OTHEMP_B[homeCounty-1]));
        double ret_wfh = Math.min(1.0, Math.max(0.0, this.WFH_RETEMP_M[homeCounty-1]*ln_hhinc + this.WFH_RETEMP_B[homeCounty-1]));

        double agr_share = Double.valueOf(this.tazDataAgrEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        double fps_share = Double.valueOf(this.tazDataFpsEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        double her_share = Double.valueOf(this.tazDataHerEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        double mwt_share = Double.valueOf(this.tazDataMwtEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        double oth_share = Double.valueOf(this.tazDataOthEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        double ret_share = Double.valueOf(this.tazDataRetEmpn[workLocation-1])/Double.valueOf(this.tazDataTotEmp[workLocation-1]);
        // weighted average based on the industry mix at the work TAZ 
        double overall_wfh = agr_wfh*agr_share +
                             fps_wfh*fps_share +
                             her_wfh*her_share +
                             mwt_wfh*mwt_share +
                             oth_wfh*oth_share +
                             ret_wfh*ret_share;

        // trace household debug
        if(householdObject.getDebugChoiceModels()){
            cdapLogger.debug(String.format(" HHID %d PersonID %d EmploymentCategory %s HomeTAZ %d HomeCounty %d WorkLocation %d", 
                householdObject.getHhId(), personA.getPersonId(), personA.getPersonEmploymentCategory(), 
                householdObject.getHhTaz(), homeCounty, workLocation));
            cdapLogger.debug(String.format("     agr_wfh * agr_share = %.3f * %.3f", agr_wfh, agr_share));
            cdapLogger.debug(String.format("     fps_wfh * fps_share = %.3f * %.3f", fps_wfh, fps_share));
            cdapLogger.debug(String.format("     her_wfh * her_share = %.3f * %.3f", her_wfh, her_share));
            cdapLogger.debug(String.format("     mwt_wfh * mwt_share = %.3f * %.3f", mwt_wfh, mwt_share));
            cdapLogger.debug(String.format("     oth_wfh * oth_share = %.3f * %.3f", oth_wfh, oth_share));
            cdapLogger.debug(String.format("     ret_wfh * ret_share = %.3f * %.3f", ret_wfh, ret_share));
            cdapLogger.debug(String.format("                 = > wfh = %.3f", overall_wfh));
        }
        if (personA.getPersonIsFullTimeWorker() == 1) {
            overall_wfh = overall_wfh*this.WFH_FULLTIMEWORKER_FACTOR;
            if(householdObject.getDebugChoiceModels()){
                cdapLogger.debug(String.format(" x FullTime factor %.3f = %.3f", this.WFH_FULLTIMEWORKER_FACTOR, overall_wfh));
            }

        } else if (personA.getPersonIsPartTimeWorker() == 1) {
            overall_wfh = overall_wfh*WFH_PARTTIMEWORKER_FACTOR;
            if(householdObject.getDebugChoiceModels()){
                cdapLogger.debug(String.format(" x PartTime factor %.3f = %.3f", this.WFH_PARTTIMEWORKER_FACTOR, overall_wfh));
            }
        }

        // should I be using this?
        double rn = householdObject.getHhRandom().nextDouble();
        if (rn < overall_wfh) {
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.WORKS_FROM_HOME.ordinal());
        } else {
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.GOES_TO_WORK.ordinal());
        }
        if(householdObject.getDebugChoiceModels()){
            cdapLogger.debug(String.format("           Random number = %.3f", rn));
            cdapLogger.debug(String.format("         works_from_home = (%d) %s", personA.getPersonWorksFromHome(), personA.getPersonWfhCategory()));
        }
    }
    
    // added for simple works-from-home choice
    public int getWorksFromHomeA(){
        return personA.getPersonWorksFromHome();
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
        // added for simple works-from-home choice
        methodIndexMap.put( "getWorksFromHomeA", 37);
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
            // added for simple works-from-home choice
            case 37: return getWorksFromHomeA();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}