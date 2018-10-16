package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

public class IndividualMandatoryTourFrequencyDMU implements Serializable, VariableTable {
	
    protected transient Logger logger = Logger.getLogger(IndividualMandatoryTourFrequencyDMU.class);
    
    protected HashMap<String, Integer> methodIndexMap;
    
    protected IndexValues dmuIndex;
    protected Household household;
    protected Person person;
    
    protected double walkDistanceToWork, walkDistanceToSchool;
    protected double roundTripAutoTimeToWork, roundTripAutoTimeToSchool;

    private int homeTazAreaType;

    
    public IndividualMandatoryTourFrequencyDMU(){
    	dmuIndex = new IndexValues();
    }
    
    public IndexValues getIndexValues(){
    	return dmuIndex;
    }
    
    public void setHousehold(Household passedInHousehold){
    	household = passedInHousehold;
    	
    	// set the origin and zone indices
    	dmuIndex.setOriginZone(household.getHhTaz());
        dmuIndex.setZoneIndex(household.getHhTaz());
        dmuIndex.setHHIndex(household.getHhId());

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( household.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug IMTF UEC" );
        }

    }


    public void setHomeTazAreaType( int at ) {
        homeTazAreaType = at;
    }

    public void setDestinationZone(int destinationZone){
    	dmuIndex.setDestZone(destinationZone);
    }
    
    public void setPerson(Person passedInPerson){
    	person	= passedInPerson;
    }
    


    public int getFullTimeWorker(){
    	return(person.getPersonTypeIsFullTimeWorker());
    }

    public int getPartTimeWorker(){
    	return(person.getPersonTypeIsPartTimeWorker());
    }

    public int getUniversityStudent(){
    	return(person.getPersonIsUniversityStudent());
    }

    public int getNonWorkingAdult(){
    	return(person.getPersonIsNonWorkingAdultUnder65());
    }

    public int getRetired(){
    	return(person.getPersonIsNonWorkingAdultOver65());
    }

    public int getDrivingAgeSchoolChild(){
    	return(person.getPersonIsStudentDriving());
    }

    public int getPreDrivingAgeSchoolChild(){
    	return(person.getPersonIsStudentNonDriving());
    }

    public int getFemale(){
    	return(person.getPersonIsFemale());
    }

    public int getAge(){
    	return(person.getAge());
    }

    public int getStudentIsEmployed(){

    	if(person.getPersonIsUniversityStudent()==1 || person.getPersonIsStudentDriving()==1){
    		return(person.getPersonIsWorker());
    	}

    	return (0);
    }

    public int getNonStudentGoesToSchool(){

    	if(person.getPersonTypeIsFullTimeWorker()==1 || person.getPersonTypeIsPartTimeWorker()==1 ||
    			person.getPersonIsNonWorkingAdultUnder65()==1 || person.getPersonIsNonWorkingAdultOver65()==1){

    		return(person.getPersonIsStudent());
    	}

    	return(0);


    }

    public int getAutos(){
    	return (household.getAutoOwnershipModelResult());
    }

    public int getDrivers(){
    	return (household.getDrivers());
    }

    public int getPreschoolChildren(){
    	return household.getNumPreschool();
    }

    public int getNonWorkers(){
    	return (household.getNumberOfNonWorkingAdults());
    }

    public int getNonFamilyHousehold(){
    	return(household.getIsNonFamilyHousehold());
    }

    public int getChildrenUnder16NotAtSchool(){
    	return(household.getNumberOfChildrenUnder16WithHomeOrNonMandatoryActivity());
    }

    public int getAreaType(){
        return homeTazAreaType;
    }

    public int getUsualWorkLocation(){
        return person.getUsualWorkLocation();
    }

    public int getUsualSchoolLocation(){
        return person.getUsualSchoolLocation();
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
