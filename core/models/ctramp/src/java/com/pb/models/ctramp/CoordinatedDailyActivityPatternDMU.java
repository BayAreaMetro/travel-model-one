package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.calculator.VariableTable;

/**
 * Decision making unit object for the Coordinated Daily Activity Pattern Model. This
 * DMU contains all the getters specified in the UEC, i.e. all the "@" variables. 
 *  
 * @author D. Ory
 *
 */
public class CoordinatedDailyActivityPatternDMU implements Serializable, VariableTable {
	
	protected transient Logger logger = Logger.getLogger(CoordinatedDailyActivityPatternDMU.class);

	protected HashMap<String, Integer> methodIndexMap;

    
    protected IndexValues dmuIndex;
    
    protected Household householdObject;
    protected Person personA, personB, personC;
    
    
    
    public CoordinatedDailyActivityPatternDMU(){
    	dmuIndex = new IndexValues();
    }

    public void setPropertyFileValues( HashMap<String, String> propertyMap ) {
        // pass
    }
    
    public void setDmuIndexValues(int zoneId) {
        dmuIndex.setZoneIndex(zoneId);

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( householdObject.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug CDAP UEC" );
        }

    }
    
    public IndexValues getIndexValues() {
        return dmuIndex; 
    }
    
    public void setMatrixManager(MatrixDataManager passedMatrixDataManager) {}

    public void setHousehold(Household passedInHouseholdObject){
    	
    	householdObject = passedInHouseholdObject;
    	
    	// set the household index
    	dmuIndex.setHHIndex(passedInHouseholdObject.getHhId());
    	
    	// set the home zone as the zone index
    	dmuIndex.setZoneIndex(passedInHouseholdObject.getHhTaz());
    }
    
    public void setPersonA(Person passedInPersonA){
    	this.personA = passedInPersonA;

        // set the stop zone as the work location
        dmuIndex.setStopZone(passedInPersonA.getPersonWorkLocationZone());
    }

    public void setWorksFromHomeForPersonA(Logger cdapLogger) {
        // pass -- implemented in subclass
    }
    
    public void setPersonB(Person passedInPersonB){
    	this.personB = passedInPersonB;
    }
    
    public void setPersonC(Person passedInPersonC){
    	this.personC = passedInPersonC;
    }
    
    // full-time worker
    public int getFullTimeWorkerA(){
    	return(personA.getPersonTypeIsFullTimeWorker());
    }
    
    public int getFullTimeWorkerB(){
    	return(personB.getPersonTypeIsFullTimeWorker());
    }
    
    public int getFullTimeWorkerC(){
    	return(personC.getPersonTypeIsFullTimeWorker());
    }
    // part-time worker
    public int getPartTimeWorkerA(){
    	return(personA.getPersonTypeIsPartTimeWorker());
    }
    
    public int getPartTimeWorkerB(){
    	return(personB.getPersonTypeIsPartTimeWorker());
    }
    
    public int getPartTimeWorkerC(){
    	return(personC.getPersonTypeIsPartTimeWorker());
    }
    
    // university student
    public int getUniversityStudentA(){
    	return(personA.getPersonIsUniversityStudent());
    }
    
    public int getUniversityStudentB(){
    	return(personB.getPersonIsUniversityStudent());
    }
    
    public int getUniversityStudentC(){
    	return(personC.getPersonIsUniversityStudent());
    }
    
    // non-working adult
    public int getNonWorkingAdultA(){
    	return(personA.getPersonIsNonWorkingAdultUnder65());
    }
    
    public int getNonWorkingAdultB(){
    	return(personB.getPersonIsNonWorkingAdultUnder65());
    }
    
    public int getNonWorkingAdultC(){
    	return(personC.getPersonIsNonWorkingAdultUnder65());
    }
    
    // retired
    public int getRetiredA(){
    	return(personA.getPersonIsNonWorkingAdultOver65());
    }
    
    public int getRetiredB(){
    	return(personB.getPersonIsNonWorkingAdultOver65());
    }
    
    public int getRetiredC(){
    	return(personC.getPersonIsNonWorkingAdultOver65());
    }
    
    // driving age school child
    public int getDrivingAgeSchoolChildA(){
    	return(personA.getPersonIsStudentDriving());
    }
    
    public int getDrivingAgeSchoolChildB(){
    	return(personB.getPersonIsStudentDriving());
    }
    
    public int getDrivingAgeSchoolChildC(){
    	return(personC.getPersonIsStudentDriving());
    }
    
    // non-driving school-age child
    public int getPreDrivingAgeSchoolChildA(){
    	return(personA.getPersonIsStudentNonDriving());
    }
    
    public int getPreDrivingAgeSchoolChildB(){
    	return(personB.getPersonIsStudentNonDriving());
    }
    
    public int getPreDrivingAgeSchoolChildC(){
    	return(personC.getPersonIsStudentNonDriving());
    }
    
    // pre-school child
    public int getPreSchoolChildA(){
    	return(personA.getPersonIsPreschoolChild());
    }
    
    public int getPreSchoolChildB(){
    	return(personB.getPersonIsPreschoolChild());
    }
    
    public int getPreSchoolChildC(){
    	return(personC.getPersonIsPreschoolChild());
    }
    
    // age
    public int getAgeA(){
    	return(personA.getAge());
    }
    
    // female
    public int getFemaleA(){
    	return(personA.getPersonIsFemale());
    }
    
    // household more cars than workers
    public int getMoreCarsThanWorkers(){
    	
    	int workers = householdObject.getWorkers();
    	int autos   = householdObject.getAutoOwnershipModelResult();
    	
    	if(autos>workers) return 1;
    	return 0;
    	
    }
    
    // household fewer cars than workers
    public int getFewerCarsThanWorkers(){
    	
    	int workers = householdObject.getWorkers();
    	int autos   = householdObject.getAutoOwnershipModelResult();
    	
    	if(autos<workers) return 1;
    	return 0;
    	
    }
    
    public int getUsualWorkLocationIsHome(){
    	return 0;
    	
    	// TODO coach this up if need be
    }
    
    public int getNoUsualWorkLocation(){
    	return 0;
    	
    	// TODO coach this up if need be
    }
    
    public int getNoUsualSchoolLocation(){
    	return 0;
    	
    	// TODO coach this up if need be
    }
    
    public int getHhSize(){
    	
    	int hhSize = Math.min(CoordinatedDailyActivityPatternModel.MAX_MODEL_HH_SIZE, householdObject.getSize());
    	
    	return(hhSize);
    }
    
    



    public int getIndexValue(String variableName) {
        return methodIndexMap.get(variableName);
    }


    
    public int getAssignmentIndexValue(String variableName) {
        throw new UnsupportedOperationException();
    }

    public double getValueForIndex(int variableIndex) {
        throw new UnsupportedOperationException();
    }

    public double getValueForIndex(int variableIndex, int arrayIndex) {
        throw new UnsupportedOperationException();
    }

    public void setValue(String variableName, double variableValue) {
        throw new UnsupportedOperationException();
    }

    public void setValue(int variableIndex, double variableValue) {
        throw new UnsupportedOperationException();
    }
    

}
