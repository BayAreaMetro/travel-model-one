package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.DcSoaDMU;
import com.pb.models.ctramp.TazDataIf;


public class MtcDcSoaDMU extends DcSoaDMU {

    int[] zoneTableRow;
    int[] county;


    public MtcDcSoaDMU( TazDataIf tazDataManager ) {
        super (tazDataManager);
        setup( tazDataManager );
        setupMethodIndexMap();
    }

    private void setup( TazDataIf tazDataManager ) {

        zoneTableRow = tazDataManager.getZoneTableRowArray();

        // the zone table columns below returned use 0-based indexing
        county = tazDataManager.getZonalCounty();
    }

    
    
    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getLnWorkLowDcSizeAlt", 0 );
        methodIndexMap.put( "getLnWorkMedDcSizeAlt", 1 );
        methodIndexMap.put( "getLnWorkHighDcSizeAlt", 2 );
        methodIndexMap.put( "getLnWorkVeryHighDcSizeAlt", 3 );
        methodIndexMap.put( "getLnUnivDcSizeAlt", 4 );
        methodIndexMap.put( "getLnGradeDcSizeAlt", 5 );
        methodIndexMap.put( "getLnHighDcSizeAlt", 6 );
        methodIndexMap.put( "getLnEscortKidsDcSizeAlt", 7 );
        methodIndexMap.put( "getLnEscortNoKidsDcSizeAlt", 8 );
        methodIndexMap.put( "getLnShoppingDcSizeAlt", 9 );
        methodIndexMap.put( "getLnEatOutDcSizeAlt", 10 );
        methodIndexMap.put( "getLnOthMaintDcSizeAlt", 11 );
        methodIndexMap.put( "getLnSocialDcSizeAlt", 12 );
        methodIndexMap.put( "getLnOthDiscrDcSizeAlt", 13 );
        methodIndexMap.put( "getLnWrkBasedDcSizeAlt", 14 );
        methodIndexMap.put( "getDestCountyAlt", 15 );
        methodIndexMap.put( "getOriginCounty", 16 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 17 );
    }
    
    
    // DMU methods - define one of these for every @var in the mode choice control file.
    public double getLnWorkLowDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "work_low" );
    }

    public double getLnWorkMedDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "work_med" );
    }

    public double getLnWorkHighDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "work_high" );
    }

    public double getLnWorkVeryHighDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "work_very high" );
    }

    public double getLnUnivDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "university" );
    }

    public double getLnGradeDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "school_grade" );
    }

    public double getLnHighDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "school_high" );
    }

    public double getLnEscortKidsDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "escort_kids" );
    }

    public double getLnEscortNoKidsDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "escort_no kids" );
    }

    public double getLnShoppingDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "shopping" );
    }

    public double getLnEatOutDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "eatOut" );
    }

    public double getLnOthMaintDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "othMaint" );
    }

    public double getLnSocialDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "social" );
    }

    public double getLnOthDiscrDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "othDiscr" );
    }

    public double getLnWrkBasedDcSizeAlt( int alt ) {
        return getLnDcSizeForPurpSegAlt( alt, "atwork" );
    }


    
    public int getOriginCounty( int alt ) {
        int index = zoneTableRow[dmuIndex.getOriginZone()] - 1;
        return county[index];
    }

    public int getDestCountyAlt( int alt ) {
        int destZone = altToZone[alt];
        int index = zoneTableRow[destZone] - 1;
        return county[index];
    }

    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return hh.getHAnalyst();
    }


    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
            case 0: return getLnWorkLowDcSizeAlt( arrayIndex );
            case 1: return getLnWorkMedDcSizeAlt( arrayIndex );
            case 2: return getLnWorkHighDcSizeAlt( arrayIndex );
            case 3: return getLnWorkVeryHighDcSizeAlt( arrayIndex );
            case 4: return getLnUnivDcSizeAlt( arrayIndex );
            case 5: return getLnGradeDcSizeAlt( arrayIndex );
            case 6: return getLnHighDcSizeAlt( arrayIndex );
            case 7: return getLnEscortKidsDcSizeAlt( arrayIndex );
            case 8: return getLnEscortNoKidsDcSizeAlt( arrayIndex );
            case 9: return getLnShoppingDcSizeAlt( arrayIndex );
            case 10: return getLnEatOutDcSizeAlt( arrayIndex );
            case 11: return getLnOthMaintDcSizeAlt( arrayIndex );
            case 12: return getLnSocialDcSizeAlt( arrayIndex );
            case 13: return getLnOthDiscrDcSizeAlt( arrayIndex );
            case 14: return getLnWrkBasedDcSizeAlt( arrayIndex );
            case 15: return getDestCountyAlt( arrayIndex );
            case 16: return getOriginCounty( arrayIndex ); 
            // guojy: added for M. Gucwa's research on automated vehicles
            case 17: return getHAnalyst();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }

}