package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.TripModeChoiceDMU;



public class MtcTripModeChoiceDMU extends TripModeChoiceDMU {

    ModelStructure modelStructure;
    int[] zoneTableRow;
    int[] areaType;
    float[] prkCostPeak;
    float[] prkCostOffPeak;
    int[] topology;
    float[] densityIndex;
    float[] terminalTime;
    int[] cordon;
    int[] cordonCost;

    public MtcTripModeChoiceDMU(TazDataIf tazDataManager, ModelStructure modelStructure){
        super( modelStructure );
        this.modelStructure = modelStructure;
        setup( tazDataManager );
        setupMethodIndexMap();
    }
    

    private void setup( TazDataIf tazDataManager ) {

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        areaType = tazDataManager.getZonalAreaType();
        prkCostPeak  = getZonalPeakHourlyParkingCost(tazDataManager);
        prkCostOffPeak  = getZonalOffPeakHourlyParkingCost(tazDataManager);
        topology = getZonalTopology(tazDataManager);
        densityIndex = getZonalDensityIndex(tazDataManager);
        terminalTime = getZonalTerminalTime(tazDataManager);
        cordon = tazDataManager.getZonalCordon();
        cordonCost = tazDataManager.getZonalCordonCost();
    }

    
    public int getHhSize() {
        return hh.getHhSize();
    }
    
    public int getAutos() {
        return hh.getAutoOwnershipModelResult();
    }

    public int getAge() {
        return person.getAge();
    }

    public int getWorkers() {
        return hh.getWorkers();
    }

    public int getHhIncomeInDollars(){
        return hh.getIncomeInDollars();
    }

    public short getIncomePercentOfPoverty(){
        return hh.getIncomePercentOfPoverty();
    }

    public float getTourDuration(){
    	float duration = tour.getTourEndHour() - tour.getTourStartHour();
    	return duration; 
    }
    
    public int getTourMode() {
    	int tourMode = tour.getTourModeChoice(); 
    	return tourMode; 
    }
    
    public int getTourStops(){
        return(tour.getNumInboundStops() + tour.getNumOutboundStops() );
    }

    
    public float getHourlyPeakParkingCostAtOrigin(){
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return prkCostPeak[index];
    }

    public float getHourlyOffPeakParkingCostAtOrigin(){
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return prkCostOffPeak[index];
    }

    public float getHourlyPeakParkingCostAtDestination(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return prkCostPeak[index];
    }

    public float getHourlyOffPeakParkingCostAtDestination(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return prkCostOffPeak[index];
    }

    public int getOriginTopology(){
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return topology[index];
    }

    public float getOriginDensityIndex(){
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return densityIndex[index];
    }
    
    public int getDestinationTopology(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return topology[index];
    }

    public float getDestinationDensityIndex(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return densityIndex[index];
    }

    public float getOriginTerminalTime(){
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return terminalTime[index];
    }
    
    public float getDestinationTerminalTime(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return terminalTime[index];
    }
    
    public int getAreaType(){
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return areaType[index];
    }

    public int getDestCordon() {
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return cordon[index];
    }

    public int getDestCordonCost() {
        int destZone = dmuIndex.getDestZone();
        int index = zoneTableRow[destZone] - 1;
        return cordonCost[index];
    }

    public int getOrigCordon() {
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return cordon[index];
    }

    public int getOrigCordonCost() {
        int origZone = dmuIndex.getOriginZone();
        int index = zoneTableRow[origZone] - 1;
        return cordonCost[index];
    }

    public float getValueOfTime(){ 
    	return person.getValueOfTime(); 
    }
    
    public int getTimeOutbound(){ 
    	return stop.getTourTodOut(); 
    }
    
    public int getTripTimeOfDay(){
        return stop.getDepartHour();
    }

    public int getTripIsInbound(){ 
    	if (stop.isInboundStop()) return 1; 
    	else return 0; 
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

    private float[] getZonalOffPeakHourlyParkingCost(TazDataIf tazDataManager){
        String fieldName = MtcTazDataHandler.ZONE_DATA_OFFPEAK_HOURLY_PARKING_COST_FIELD_NAME;
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

    private float[] getZonalTerminalTime(TazDataIf tazDataManager){
        String fieldName = MtcTazDataHandler.ZONE_DATA_TERMINAL_TIME_FIELD_NAME;
        return getZoneTableFloatColumn( tazDataManager, fieldName );
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
            logger.error ( String.format ( "invalid field name: %s, name not found in list of column headings for zone table.", fieldName) );
            throw new RuntimeException();
        }

        return ( tazDataManager.getZoneTableIntColumn( fieldName ) );
    }




    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getAge", 0 );
        methodIndexMap.put( "getAreaType", 1 );
        methodIndexMap.put( "getAutos", 2 );        
        methodIndexMap.put( "getHhSize", 3 );
        methodIndexMap.put( "getTourModeIsWalk", 4 );        
        methodIndexMap.put( "getWorkers", 5 );
        methodIndexMap.put( "getZonalLongWalkAccessDest", 6 );
        methodIndexMap.put( "getZonalLongWalkAccessOrig", 7 );
        methodIndexMap.put( "getZonalShortWalkAccessDest", 8 );
        methodIndexMap.put( "getZonalShortWalkAccessOrig", 9 );
        methodIndexMap.put( "getValueOfTime", 10 ); 
        methodIndexMap.put( "getTourCategoryJoint", 11 ); 
        methodIndexMap.put( "getNumberOfParticipantsInJointTour", 12 );
        methodIndexMap.put( "getTourCategorySubtour", 13 );
        methodIndexMap.put( "getTourModeIsSOV", 14 );
        methodIndexMap.put( "getTourModeIsBike", 15 );
        methodIndexMap.put( "getTourModeIsAuto", 16 );
        methodIndexMap.put( "getTourModeIsWalkTransit", 17 );
        methodIndexMap.put( "getTourModeIsDriveTransit", 18 );
        methodIndexMap.put( "getOriginTopology", 19 );
        methodIndexMap.put( "getOriginDensityIndex", 20 );
        methodIndexMap.put( "getDestinationTopology", 21 );
        methodIndexMap.put( "getDestinationDensityIndex", 22 );
        methodIndexMap.put( "getStopIsFirst", 23 );
        methodIndexMap.put( "getStopIsLast", 24 );
        methodIndexMap.put( "getHourlyPeakParkingCostAtOrigin", 25 );
        methodIndexMap.put( "getHourlyPeakParkingCostAtDestination", 26 );
        methodIndexMap.put( "getHourlyOffPeakParkingCostAtOrigin", 27 );
        methodIndexMap.put( "getHourlyOffPeakParkingCostAtDestination", 28 );
        methodIndexMap.put( "getTourDuration", 29 );
        methodIndexMap.put( "getTripTimeOfDay", 30 ); // note
        methodIndexMap.put( "getTripIsInbound", 31 );
        methodIndexMap.put( "getTerminalTimeAtOrigin", 32); 
        methodIndexMap.put( "getTerminalTimeAtDestination", 33);
        methodIndexMap.put( "getFreeParking", 34);
        methodIndexMap.put( "getTourMode", 35 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 36 );
        methodIndexMap.put( "getPAnalyst", 37 );
        // TM1.5: tnc/taxi/AV
        methodIndexMap.put("getWaitTimeTaxi", 38);
        methodIndexMap.put("getWaitTimeSingleTNC", 39);
        methodIndexMap.put("getWaitTimeSharedTNC", 40);
        methodIndexMap.put("getUseOwnedAV", 41);
        methodIndexMap.put("getTourModeIsRideHail", 42 );
        methodIndexMap.put("getHhIncomeInDollars", 43);
        methodIndexMap.put("getDestCordon", 44);
        methodIndexMap.put("getDestCordonCost", 45); 
        methodIndexMap.put("getOrigCordon", 46);
        methodIndexMap.put("getOrigCordonCost", 47);
        methodIndexMap.put("getHhIncomePctOfPoverty", 48);
    }
    
        
    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){

            case 0: return getAge();
            case 1: return getAreaType();
            case 2: return getAutos();
            case 3: return getHhSize();            
            case 4: return getTourModeIsWalk();            
            case 5: return getWorkers();
            case 6: return getZonalLongWalkAccessDest();
            case 7: return getZonalLongWalkAccessOrig();
            case 8: return getZonalShortWalkAccessDest();
            case 9: return getZonalShortWalkAccessOrig();
            case 10: return getValueOfTime(); 
            case 11: return getTourCategoryJoint(); 
            case 12: return getNumberOfParticipantsInJointTour();
            case 13: return getTourCategorySubtour();
            case 14: return getTourModeIsSOV();
            case 15: return getTourModeIsBike();
            case 16: return getTourModeIsAuto();
            case 17: return getTourModeIsWalkTransit();
            case 18: return getTourModeIsDriveTransit();
            case 19: return getOriginTopology();
            case 20: return getOriginDensityIndex();
            case 21: return getDestinationTopology();
            case 22: return getDestinationDensityIndex();
            case 23: return getStopIsFirst();
            case 24: return getStopIsLast();
            case 25: return getHourlyPeakParkingCostAtOrigin();
            case 26: return getHourlyPeakParkingCostAtDestination();
            case 27: return getHourlyOffPeakParkingCostAtOrigin();
            case 28: return getHourlyPeakParkingCostAtDestination();
            case 29: return getTourDuration(); 
            case 30: return getTripTimeOfDay();
            case 31: return getTripIsInbound(); 
            case 32: return getOriginTerminalTime(); 
            case 33: return getDestinationTerminalTime(); 
            case 34: return getFreeParking(); 
            case 35: return getTourMode();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 36: return getHAnalyst();
            case 37: return getPAnalyst();
            // TM1.5: tnc/taxi/AV
            case 38: return getWaitTimeTaxi();
            case 39: return getWaitTimeSingleTNC();
            case 40: return getWaitTimeSharedTNC();
            case 41: return getUseOwnedAV();
            case 42: return getTourModeIsRideHail();
            case 43: return getHhIncomeInDollars();
            case 44: return getDestCordon();
            case 45: return getDestCordonCost();
            case 46: return getOrigCordon();
            case 47: return getOrigCordonCost();
            case 48: return getIncomePercentOfPoverty();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
        
    }

}