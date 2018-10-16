package com.pb.models.ctramp;

import org.apache.log4j.Logger;

import java.io.Serializable;
import java.util.HashMap;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;

/**
 * @author crf <br/>
 *         Started: Apr 14, 2009 1:34:03 PM
 */
public class ParkingChoiceDMU implements Serializable, VariableTable {
    
    protected transient Logger logger = Logger.getLogger(ParkingChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;

    protected HashMap<String, Float> averageDailyHoursParkedMap; // key: purpose name, value: average hours parked per day by purpose
    
    private IndexValues dmuIndex;
    private TazDataIf tazDataManager;

    private Tour tour;
    private int[] parkTazs;
    
    
    public ParkingChoiceDMU(TazDataIf tazDataManager) {
        this.tazDataManager = tazDataManager;
        dmuIndex = new IndexValues();
    }

    
    
    
    
    public void setDmuState(Household hh, int originZone, int destZone) {
        setDmuIndexValues( hh.getHhId(), originZone, destZone, hh.getDebugChoiceModels() );
    }

    private void setDmuIndexValues(int hhId, int origTaz, int destTaz, boolean hhDebug) {
        dmuIndex.setHHIndex(hhId);
        dmuIndex.setOriginZone(origTaz);
        dmuIndex.setDestZone(destTaz);
        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ("");
        
        if ( hhDebug ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ("Debug Parking Choice UEC");
        }

    }
    
    
    public IndexValues getDmuIndexValues() {
        return dmuIndex;
    }
    

    /**
     * 
     * @return 1 if dest is in CBD
     */
    public int getParkTazCbdAreaTypeAlt( int alt ){
        // parkTazs array is zero-based.
        int taz = parkTazs[alt-1];
        return tazDataManager.getZoneIsCbd( taz );
    }

    /**
     * get the hourly parking rate for the parking location alternative, and multiply
     * by the average daily hours parking for the tour purpose.
     * 
     * @return daily parking cost for the parking location alternative
     */
    public float getParkingCostAlt( int alt ){
        int taz = parkTazs[alt-1];
        float rate = tazDataManager.getZoneTableValue( taz, tazDataManager.getZonalParkRateFieldName() );
        float hours = averageDailyHoursParkedMap.get( tour.getTourPrimaryPurpose() );
        
        return hours * rate;
    }

    public float getParkTotAlt( int alt ){
        int taz = parkTazs[alt-1];
        return tazDataManager.getZonalParkTot()[taz-1];       
    }
    
    public void setParkTazArray ( int[] parkTazs ){
        this.parkTazs = parkTazs;
    }
    
    protected int getTourIsJoint() {
        return tour.getTourCategoryIsJointNonMandatory() ? 1 : 0;
    }

    public float getParkTot(){
        int dest = dmuIndex.getDestZone();
        return tazDataManager.getZonalParkTot()[dest-1];
    }  
    
    public void setTourObject( Tour tour ) {
        this.tour = tour;
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
