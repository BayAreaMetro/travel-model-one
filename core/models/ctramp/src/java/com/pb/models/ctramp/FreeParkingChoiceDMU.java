package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

/**
 * @author crf <br/>
 *         Started: Apr 14, 2009 11:09:58 AM
 */
public class FreeParkingChoiceDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(FreeParkingChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;

    protected Household hh;
    protected Person person; 
    private IndexValues dmuIndex;


    public FreeParkingChoiceDMU() {
    	dmuIndex = new IndexValues();
    }

    /** need to set hh and home taz before using**/
    public void setPersonObject (Person personObject) {
    	person = personObject; 
        hh = personObject.getHouseholdObject();
    }

    public void setDmuIndexValues( int hhId, int zoneId, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhId );
        dmuIndex.setZoneIndex( zoneId );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( hh.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug Free Parking UEC" );
        }
    }

    public IndexValues getDmuIndexValues() {
        return dmuIndex;
    }

    /*dmu @ functions*/

    public int getAutoOwnership() {
        return hh.getAutoOwnershipModelResult();
    }

    public int getFtwkPersons() {
        return hh.getNumFtWorkers();
    }

    public int getPtwkPersons() {
        return hh.getNumPtWorkers();
    }

    public int getSize() {
        return hh.getSize();
    }


    
    public int getIndexValue(String variableName) {
        return methodIndexMap.get(variableName);
    }

    public int getWorkLocation() {
    	return person.getUsualWorkLocation(); 
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
