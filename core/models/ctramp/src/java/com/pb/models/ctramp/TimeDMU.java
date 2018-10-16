package com.pb.models.ctramp;

import java.io.Serializable;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;


public class TimeDMU implements Serializable, VariableTable {

    IndexValues dmuIndex = null;
    
    // switches used in the Individual Mandatory Tour Frequency Model
    int imtfWorkSwitch, imtfSchoolSwitch;

    public TimeDMU () {
        dmuIndex = new IndexValues();
    }
    
    
    public void setDmuIndexValues( int hhId, int zoneId, int origTaz, int destTaz, boolean debugUec ) {
        dmuIndex.setHHIndex( hhId );
        dmuIndex.setZoneIndex( zoneId );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( debugUec ) {
            dmuIndex.setDebug(true);
//            dmuIndex.setDebugLabel ( "Debug IMTF Time UEC" );
            dmuIndex.setDebugLabel ( "Debug AO Time UEC" );
        }

    }
    
    public IndexValues getDmuIndexValues() {
        return dmuIndex; 
    }
    
    
    
    
//    /**
//     * Used in the Individual Mandatory Tour Frequency model; set to true
//     * when the model is applied for a worker (to get round trip time to work,
//     * which uses peak skims)
//     * @param workOn
//     */
//    public void setImtfWorkSwitch(int workOn){
//    	imtfWorkSwitch = workOn;
//    }
//    
//    /**
//     * Used in the Individual Mandatory Tour Frequency model; set to true
//     * when the model is applied for a student (to get round trip time to school,
//     * which uses peak skims in the o/d direction and off-peak skims in the d/o
//     * direction)
//     * @param schoolOn
//     */
//    public void setImtfSchoolSwitch(int schoolOn){
//    	imtfSchoolSwitch = schoolOn;
//    }
//    
//    public int getImtfWorkSwitch(){
//    	return this.imtfWorkSwitch;
//    }
//    
//    public int getImtfSchoolSwitch(){
//    	return this.imtfSchoolSwitch;
//    }
    



    public int getAssignmentIndexValue(String variableName) {
        throw new UnsupportedOperationException();
    }

    public int getIndexValue(String variableName) {
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


