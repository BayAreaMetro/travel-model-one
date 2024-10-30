package com.pb.mtc.ctramp;

import java.util.HashMap;
import java.util.Random;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataManager;
import com.pb.models.ctramp.CoordinatedDailyActivityPatternDMU;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;

public class MtcCoordinatedDailyActivityPatternDMU extends CoordinatedDailyActivityPatternDMU {

    private Logger cdapLogger = Logger.getLogger("cdap");
    
    // EN7 superdistrict boosts
    public static final String PROPERTIES_WFH_EN7_SUPERDISTRICT_BOOST = "CDAP.WFH.EN7.Superdistrict00";

    // indexed by work superdistrict
    private float[] WFH_EN7_BOOST;

    private int[] tazDataAgrEmpn;
    private int[] tazDataFpsEmpn;
    private int[] tazDataHerEmpn;
    private int[] tazDataMwtEmpn;
    private int[] tazDataOthEmpn;
    private int[] tazDataRetEmpn;
    private int[] tazDataTotEmp;

    TazDataIf tazDataManager;
    private MatrixDataManager matrixDataManager = null;
    private int DIST_MATRIX_INDEX = -1;

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
        // en7 superdistrict table
        this.WFH_EN7_BOOST = new float[34];  // hardcoded 34 == bad but no time
    }

    public void setPropertyFileValues( HashMap<String, String> propertyMap) {

        for (int district_num=1; district_num<=34; district_num++) {
            this.WFH_EN7_BOOST[district_num-1] = Float.parseFloat(propertyMap.get(
                PROPERTIES_WFH_EN7_SUPERDISTRICT_BOOST.replace("Superdistrict00",String.format("Superdistrict%02d",district_num))));
            // cdapLogger.info("Read superdistrict EN7 boosts for district " + district_num + ": " + this.WFH_EN7_BOOST[district_num-1]);
        }
    }

    public void setMatrixManager(MatrixDataManager passedMatrixDataManager){
        this.matrixDataManager = passedMatrixDataManager;
        this.DIST_MATRIX_INDEX = this.matrixDataManager.findMatrixIndex("DIST");
        // cdapLogger.info("setMatrixManager:" + this.matrixDataManager);
        // cdapLogger.info("this.DIST_MATRIX_INDEX:" + this.DIST_MATRIX_INDEX);
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

    // added for WFH UEC
    public int getHhIncomeInDollars(){
        return householdObject.getIncomeInDollars();
    }
    // person's industry is AGR?
    public int getIndustryAGR(){
        if (personA.getPersonIndustry() == "AGR") {
            return 1;
        }
        return 0;
    }
    // person's industry is HER?
    public int getIndustryHER(){
        if (personA.getPersonIndustry() == "HER") {
            return 1;
        }
        return 0;
    }
    // person's industry is MWT?
    public int getIndustryMWT(){
        if (personA.getPersonIndustry() == "MWT") {
            return 1;
        }
        return 0;
    }
    // person's industry is RET?
    public int getIndustryRET(){
        if (personA.getPersonIndustry() == "RET") {
            return 1;
        }
        return 0;
    }
    // get the home county of the household
    public int getHomeCounty(){
        return this.tazDataManager.getZoneCounty(householdObject.getHhTaz());
    }
    // get the work SD of the person
    public int getWorkSD(){
        int work_taz = personA.getUsualSchoolLocation();
        if (work_taz == 0) { return 0; }
        return this.tazDataManager.getZoneDistrict(work_taz);
    }
    /**
	 * Simple industry guesser (random) for person based upon the industry
	 * mix at their work location TAZ.
	 * @param Logger
	 */
    public void setIndustryForPersonA(Logger cdapLogger) {
        if (personA.getPersonIsWorker() == 0) {
            personA.setPersIndustryCategory( Person.IndustryStatus.NOT_APPLICABLE );
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.NOT_APPLICABLE );
            return;
        }
		int workLocation = personA.getPersonWorkLocationZone();
		if (workLocation == 0) {
            // I don't think this should happen
            personA.setPersIndustryCategory( Person.IndustryStatus.NOT_APPLICABLE );
            personA.setPersWorksFromHomeCategory( Person.WorkFromHomeStatus.NOT_APPLICABLE );
			return;
		}
        
        int workDistrict = this.tazDataManager.getZoneDistrict(workLocation);
        double totalEmpAtWorkLocation = Double.valueOf(this.tazDataTotEmp[workLocation-1]);

        if(householdObject.getDebugChoiceModels()){
            cdapLogger.debug(String.format(" HHID %d PersonID %d EmploymentCategory %s HomeTAZ %d WorkLocation %d WorkDistrict %d totalEmpAtWorkLocation=%f", 
                householdObject.getHhId(), personA.getPersonId(), personA.getPersonEmploymentCategory(), 
                householdObject.getHhTaz(), workLocation, workDistrict, totalEmpAtWorkLocation));
        }

        // make it cumulative
        double[] cumulative_share = new double[Person.IndustryStatus.values().length];
        double cumulative_total = 0.0;
        for (Person.IndustryStatus industry_category : Person.IndustryStatus.values()) {
            double ind_share = 0.0;
            if      (industry_category == Person.IndustryStatus.nul)            { ind_share = 0.0; }
            else if (industry_category == Person.IndustryStatus.NOT_APPLICABLE) { ind_share = 0.0; }
            else if (industry_category == Person.IndustryStatus.AGREMP) { ind_share = Double.valueOf(this.tazDataAgrEmpn[workLocation-1])/totalEmpAtWorkLocation; }
            else if (industry_category == Person.IndustryStatus.FPSEMP) { ind_share = Double.valueOf(this.tazDataFpsEmpn[workLocation-1])/totalEmpAtWorkLocation; }
            else if (industry_category == Person.IndustryStatus.HEREMP) { ind_share = Double.valueOf(this.tazDataHerEmpn[workLocation-1])/totalEmpAtWorkLocation; }
            else if (industry_category == Person.IndustryStatus.MWTEMP) { ind_share = Double.valueOf(this.tazDataMwtEmpn[workLocation-1])/totalEmpAtWorkLocation; }
            else if (industry_category == Person.IndustryStatus.OTHEMP) { ind_share = Double.valueOf(this.tazDataOthEmpn[workLocation-1])/totalEmpAtWorkLocation; }
            else if (industry_category == Person.IndustryStatus.RETEMP) { ind_share = Double.valueOf(this.tazDataRetEmpn[workLocation-1])/totalEmpAtWorkLocation; }

            cumulative_total += ind_share;
            cumulative_share[industry_category.ordinal()] = cumulative_total;

            if(householdObject.getDebugChoiceModels()){
                cdapLogger.debug(String.format("    industry %d %s:  share: %.4f  cumulate_share: %.4f", 
                industry_category.ordinal(), 
                (industry_category.ordinal() > 0 ? Person.industryCategoryNameArray[industry_category.ordinal()-1] : "NUL"), 
                ind_share, cumulative_share[industry_category.ordinal()]));
            }
        }

        double rn = householdObject.getHhRandom().nextDouble();
        Person.IndustryStatus chosen_industry = Person.IndustryStatus.nul;
        for (Person.IndustryStatus industry_category : Person.IndustryStatus.values()) {
            if (industry_category.ordinal() == 0) { continue; }

            chosen_industry = industry_category;
            if ((rn > cumulative_share[industry_category.ordinal() - 1]) & (rn < cumulative_share[industry_category.ordinal()])) {
                chosen_industry = industry_category;
                break;
            }
        }

        if(householdObject.getDebugChoiceModels()){
            cdapLogger.debug(String.format("    Random number = %.3f", rn));
            cdapLogger.debug(String.format("         industry = (%d) %s", chosen_industry.ordinal(), Person.industryCategoryNameArray[chosen_industry.ordinal()-1]));
        }
        personA.setPersIndustryCategory( chosen_industry );
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
        // added for work-from-home UEC
        methodIndexMap.put("getHhIncomeInDollars", 38);
        methodIndexMap.put("getIndustryAGR", 39);
        methodIndexMap.put("getIndustryHER", 40);
        methodIndexMap.put("getIndustryMWT", 41);
        methodIndexMap.put("getIndustryRET", 42);
        methodIndexMap.put("getHomeCounty", 43);
        methodIndexMap.put("getWorkSD", 44);
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
            // added for work-from-home UEC
            case 38: return getHhIncomeInDollars();
            case 39: return getIndustryAGR();
            case 40: return getIndustryHER();
            case 41: return getIndustryMWT();
            case 42: return getIndustryRET();
            case 43: return getHomeCounty();
            case 44: return getWorkSD();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}