package com.pb.models.ctramp;

/**
 * Created by IntelliJ IDEA.
 * User: Jim
 * Date: Jul 1, 2008
 * Time: 9:58:21 AM
 *
 * Interface for accessing zonal information used by CT-RAMP modules
 */
public interface TazDataIf {

    public String testRemote();
    public int[] getAltToZoneArray ();
    public int[] getAltToSubZoneArray ();
    public int[] getIndexToZoneArray ();
    public int[] getZoneTableRowArray ();

    public int getZoneIsCbd( int taz );
    public int getZoneIsUrban( int taz );
    public int getZoneIsSuburban( int taz );
    public int getZoneIsRural( int taz );
    public int getZoneCounty( int taz );
    public int getZoneCordon( int taz );
    public int getZoneCordonCost( int taz );

    public float getPopEmpPerSqMi(int taz);

    public float[] getPkAutoRetailAccessibity();
    public float[] getPkAutoTotalAccessibity();
    public float[] getPkTransitRetailAccessibity();
    public float[] getPkTransitTotalAccessibity();
    public float[] getOpAutoRetailAccessibity();
    public float[] getOpAutoTotalAccessibity();
    public float[] getOpTransitRetailAccessibity();
    public float[] getOpTransitTotalAccessibity();
    public float[] getNonMotorizedRetailAccessibity();
    public float[] getNonMotorizedTotalAccessibity();
    
    /**
     *
     * @param field is the field name to be checked against the column names in the zone data table.
     * @return true if field matches one of the zone data table column names, otherwise false.
     */
    public boolean isValidZoneTableField(String field);

    /**
     * @return a String[] of the column labels in the zone data table
     */
    public String[] getZoneDataTableColumnLabels();

    /**
     * @return an int value for the number of zones, i.e. rows in the zone data table
     */
    public int getNumberOfZones();
    
    /**
     * 
     * @return an array of taz numbers, starting at element 0
     */
    public int[] getTazs();

    /**
     * 
     * @return an array of taz numbers, starting at element 1
     */
    public int[] getTazsOneBased();
    
    
    /**
     * @return an int value for the number of subZones, i.e. number of walkTransit accessible segments defined
     * in model for zones.  Typical value might be 3, "no walk access", "short walk access", "long walk access".
     */    
    public int getNumberOfSubZones();

    /**
     * @return a String[] for the subZone names, e.g. "no walk access", "short walk access", "long walk access".
     */
    public String[] getSubZoneNames();

    /**
     * @param taz is the taz index for the zonalWalkPctArray which is dimensioned to ZONES+1, assuming taz index values
     * range from 1 to NUM_ZONES.
     * @return a double[], dimensioned to NUM_SIBZONES, with the subzone proportions for the TAZ passed in
     */
    public double[] getZonalWalkPercentagesForTaz( int taz );

    /**
     * @param taz is the taz index for the zone data table which is dimensioned to ZONES+1, assuming taz index values
     * range from 1 to NUM_ZONES.
     * @param fieldName is the column label in the zone data table.
     * @return a float value from the zone data table at the specified row index and column label.
     */
    public float getZoneTableValue ( int taz, String fieldName );

    public int[] getZoneTableIntColumn ( String fieldName );

    public float[] getZoneTableFloatColumn ( String fieldName );

    /**
     * @param tableRowNumber is the zone table row number
     * @return zone number for the table row.
     */
    public int getTazNumber ( int tableRowNumber );

    /**
     * @return area type from the zone data table for the zone index.
     */
    public int[] getZonalAreaType ();

    /**
     * @return district from the zone data table for the zone index.
     */
    public int[] getZonalDistrict ();

    /**
     * @return integer county value from the zone data table for the zone index.
     */
    public int[] getZonalCounty ();

    /**
     * @return the parking rate array
     */
    float[] getZonalParkRate ();

    /**
     * @return the proportion of free parking array
     */
    float[] getZonalPropFree ();

    /**
     * @return the number of long parking spots array
     */
    int[] getZonalParkLong ();

    /**
     * @return the number of parking spots array
     */
    int[] getZonalParkTot ();

    public String getZonalParkTotFieldName ();
    public String getZonalParkRateFieldName ();
    
}
