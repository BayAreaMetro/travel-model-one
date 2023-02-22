package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;


public class MtcModeChoiceDMU extends ModeChoiceDMU {


    int[] zoneTableRow;
    int[] areaType;
    float[] prkCost;
    int[] topology;
    float[] densityIndex;
    

    public MtcModeChoiceDMU( TazDataIf tazDataManager, ModelStructure modelStructure ){
        super( modelStructure );
        setup( tazDataManager );
        setupMethodIndexMap();
    }



    private void setup( TazDataIf tazDataManager ) {

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();
        prkCost = getZonalPeakHourlyParkingCost(tazDataManager);
        topology = getZonalTopology(tazDataManager);
        densityIndex = getZonalDensityIndex(tazDataManager); 
    }


    
    public int getZonalShortWalkAccessOrig() {
        if ( tour.getTourOrigWalkSubzone() == 1 )
            return 1;
        else
            return 0;
    }

    public int getZonalShortWalkAccessDest() {
        if ( tour.getTourDestWalkSubzone() == 1 )
            return 1;
        else
            return 0;
    }

    public int getZonalLongWalkAccessOrig() {
        if ( tour.getTourOrigWalkSubzone() == 2 )
            return 1;
        else
            return 0;
    }

    public int getZonalLongWalkAccessDest() {
        if ( tour.getTourDestWalkSubzone() == 2 )
            return 1;
        else
            return 0;
    }


    // TODO ask joel about removing this, return dummy for now
    public int getParkingAvailabilityIndex(){
    	return(0);
    }

    public float getTimeOutbound(){
    	return(tour.getTourStartHour());
    }

    public float getTimeInbound(){
    	return(tour.getTourEndHour());
    }
    
    public float getTourDuration(){
    	float duration = tour.getTourEndHour() - tour.getTourStartHour() + 1;
    	return duration; 
    }

    public int getTopology(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return topology[index];
    }

    public float getDensityIndex(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return densityIndex[index];
    }

    public float getOriginDensityIndex(){
        int origZone = dmuIndex.getOriginZone(); 
        int index = zoneTableRow[origZone] - 1;
        return densityIndex[index];
    }
    
    public int getAreaType(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return areaType[index];
    }

    public float getValueOfTime(){ 
        return person.getValueOfTime(); 
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return hh.getHAnalyst();
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getPAnalyst(){
    	return person.getPAnalyst();
    }

    // private methods

    private float[] getZonalPeakHourlyParkingCost(TazDataIf tazDataManager){
        String fieldName = MtcTazDataHandler.ZONE_DATA_PEAK_HOURLY_PARKING_COST_FIELD_NAME;
        return getZoneTableFloatColumn( tazDataManager, fieldName );
    }

    private int[] getZonalTopology(TazDataIf tazDataManager){
        String fieldName = MtcTazDataHandler.ZONE_DATA_TOPOLOGY_FIELD_NAME;
        return getZoneTableIntColumn( tazDataManager, fieldName );
    }

    private float[] getZonalDensityIndex(TazDataIf tazDataManager){
        String hhFieldName = MtcTazDataHandler.ZONE_DATA_HH_FIELD_NAME;        
        String empFieldName = MtcTazDataHandler.ZONE_DATA_EMP_FIELD_NAME;        
        String resAcreFieldName = MtcTazDataHandler.ZONE_DATA_RESACRE_FIELD_NAME;        
        String comAcreFieldName = MtcTazDataHandler.ZONE_DATA_COMACRE_FIELD_NAME;

        float[] hh = getZoneTableFloatColumn(tazDataManager, hhFieldName);
        float[] emp = getZoneTableFloatColumn(tazDataManager, empFieldName);
        float[] resAcre = getZoneTableFloatColumn(tazDataManager, resAcreFieldName);
        float[] comAcre = getZoneTableFloatColumn(tazDataManager, comAcreFieldName);
        
        float[] densityIndex = new float[hh.length];
        for (int i=0; i<densityIndex.length; i++) {
        	float totAcres = resAcre[i] + comAcre[i]; 
        	float hhDensity = hh[i] / Math.max(totAcres,1);
        	float empDensity = emp[i] / Math.max(totAcres,1);
        	
        	if (hhDensity+empDensity > 0) {
        		densityIndex[i] = (hhDensity * empDensity) / (hhDensity + empDensity);	
        	} else {
        		densityIndex[i] = 0; 
        	}
        }
        
        return densityIndex; 
    }


    private float[] getZoneTableFloatColumn( TazDataIf tazDataManager, String fieldName ){

        if ( fieldName == null || ! tazDataManager.isValidZoneTableField(fieldName) ) {
            logger.error ( String.format ( "invalid field name: %s, name not found in list of column headings for zone table.", fieldName) );
            throw new RuntimeException();
        }

        return ( tazDataManager.getZoneTableFloatColumn( fieldName ) );
    }


    private int[] getZoneTableIntColumn( TazDataIf tazDataManager, String fieldName ){

        if ( fieldName == null || ! tazDataManager.isValidZoneTableField(fieldName) ) {
            String[] columnNames = tazDataManager.getZoneDataTableColumnLabels(); 
        	logger.error ( String.format ( "invalid field name: %s, name not found in list of column headings for zone table.", fieldName) );
            logger.error ( String.format ( "valud column names are: %s", columnNames.toString())); 
            throw new RuntimeException();
        }

        return ( tazDataManager.getZoneTableIntColumn( fieldName ) );
    }



    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getAge", 0 );
        methodIndexMap.put( "getAreaType", 1 );
        methodIndexMap.put( "getAutos", 2 );
        methodIndexMap.put( "getTourDuration", 3 );
        methodIndexMap.put( "getHhSize", 4 );
        
        methodIndexMap.put( "getParkingAvailabilityIndex", 6 );
        methodIndexMap.put( "getTimeInbound", 7 );
        methodIndexMap.put( "getTimeOutbound", 8 );
        methodIndexMap.put( "getTopology", 9 );
        methodIndexMap.put( "getDensityIndex", 10 );
        methodIndexMap.put( "getWorkers", 11 );
        methodIndexMap.put( "getZonalLongWalkAccessDest", 12 );
        methodIndexMap.put( "getZonalLongWalkAccessOrig", 13 );
        methodIndexMap.put( "getZonalShortWalkAccessDest", 14 );
        methodIndexMap.put( "getZonalShortWalkAccessOrig", 15 );
        methodIndexMap.put( "getValueOfTime", 16); 
        methodIndexMap.put( "getTourCategoryJoint", 17); 
        methodIndexMap.put( "getNumberOfParticipantsInJointTour", 18 );
        methodIndexMap.put( "getTourCategorySubtour", 19 );
        methodIndexMap.put( "getWorkTourModeIsSOV", 20 );
        methodIndexMap.put( "getWorkTourModeIsBike", 21 );
        methodIndexMap.put( "getFreeParking", 22 );
        methodIndexMap.put( "getOriginDensityIndex", 23 );
        methodIndexMap.put( "getOrigSubzone", 24 );
        methodIndexMap.put( "getDestSubzone", 25 );
        methodIndexMap.put( "getAccessibilityValueOfTime", 26 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 27 );
        methodIndexMap.put( "getPAnalyst", 28 );
        
        methodIndexMap.put( "getOrigTaxiWaitTime", 30 );
        methodIndexMap.put( "getDestTaxiWaitTime", 31 );
        methodIndexMap.put( "getOrigSingleTNCWaitTime", 32 );
        methodIndexMap.put( "getDestSingleTNCWaitTime", 33 );
        methodIndexMap.put( "getOrigSharedTNCWaitTime", 34 );
        methodIndexMap.put( "getDestSharedTNCWaitTime", 35 );
        methodIndexMap.put( "getUseOwnedAV", 36);
        methodIndexMap.put( "getOrigCounty", 37);
        methodIndexMap.put( "getHhIncomeInDollars", 38);
        methodIndexMap.put( "getOrigCordon", 39);
        methodIndexMap.put( "getOrigCordonCost", 40);
      }
    
        
    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){

            case 0: return getAge();
            case 1: return getAreaType();
            case 2: return getAutos();
            case 3: return getTourDuration();
            case 4: return getHhSize();
            
            case 6: return getParkingAvailabilityIndex();
            case 7: return getTimeInbound();
            case 8: return getTimeOutbound();
            case 9: return getTopology();
            case 10: return getDensityIndex();
            case 11: return getWorkers();
            case 12: return getZonalLongWalkAccessDest();
            case 13: return getZonalLongWalkAccessOrig();
            case 14: return getZonalShortWalkAccessDest();
            case 15: return getZonalShortWalkAccessOrig();
            case 16: return getValueOfTime(); 
            case 17: return getTourCategoryJoint(); 
            case 18: return getNumberOfParticipantsInJointTour();
            case 19: return getTourCategorySubtour();
            case 20: return getWorkTourModeIsSOV();
            case 21: return getWorkTourModeIsBike();
            case 22: return getFreeParking(); 
            case 23: return getOriginDensityIndex(); 

            case 24: return getOrigSubzone(); 
            case 25: return getDestSubzone(); 
            case 26: return getAccessibilityValueOfTime();

            // guojy: added for M. Gucwa's research on automated vehicles
            case 27: return getHAnalyst();
            case 28: return getPAnalyst();
            
            case 30: return getOrigTaxiWaitTime();
            case 31: return getDestTaxiWaitTime();
            case 32: return getOrigSingleTNCWaitTime();
            case 33: return getDestSingleTNCWaitTime();
            case 34: return getOrigSharedTNCWaitTime();
            case 35: return getDestSharedTNCWaitTime();
            case 36: return getUseOwnedAV();
            case 37: return getOrigCounty();
            case 38: return getHhIncomeInDollars();
            case 39: return getOrigCordon();
            case 40: return getOrigCordonCost();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }


}