package com.pb.models.ctramp;

import java.io.Serializable;


/**
 * This class provides methods defined in the TazDataIf interface for accessing zonal data stored in
 * its TazDataManager object.
 *
 * A CT-RAMP tour based model application could create an instance of a subclass of this class, where additional
 * project specific varaible definitions and methods are defined and pass that instance to its model
 * component objects.
 *
 * Alternatively, an application could use TazDataHandlerRmi as the base class instead and create a "remoteable" subclass.
 * The TazDataHandlerRmi class implements the same interface, so the model component classes can be unaware of whether the
 * taz data handler object accesses zonal data from its member object or remotely from a server.  Those methods in the
 * rmi class access zonal data from a TazDataManager object contained in a "taz data server" object which must exist in
 * a separate JVM on the same machine or on another addressable machine over the network.
 *
 * The flexibility provided by this design is intended to allow the "local" instance to be declared and passed within a single JVM
 * to model components for possibly greater performance (yet to be tested and proven) at production run time.
 * The "rmi" instance however allows the model components to access zonal data from a "long-running process" (the server
 * class may execute for weeks or months).  This approach aids in model development as during development, model
 * applications can be written to skip startup procedures for reading zonal data, and access them directly from the
 * server that is already running.
 *
 * A similar approach is planned for managing objects such as Household objects and ModelResults objects so that model
 * components, for example individual non-mandatory tour related models which occur well into the tour based model stream,
 * can be run in a "hot-start" fasion, where the model component of interest is executed immediately where all the
 * preliminary data and prior model results it requires are stored in long-running server objects.  Testing and debugging
 * of these model components can occur without the time required to run through all preliminary steps.
 *
 *
 */

public class TazDataHandlerRmi implements TazDataIf, Serializable {

    UtilRmi remote;
    String connectString;

    public TazDataHandlerRmi( String hostname, int port, String className ){

        connectString = String.format("//%s:%d/%s", hostname, port, className );
        remote = new UtilRmi(connectString);

    }





    public String testRemote() {
        Object[] objArray = {};
        return (String)remote.method( "testRemote", objArray);
    }

    public int[] getAltToZoneArray () {
        Object[] objArray = {};
        return (int[])remote.method( "getAltToZoneArray", objArray);
    }

    public int[] getAltToSubZoneArray () {
        Object[] objArray = {};
        return (int[])remote.method( "getAltToSubZoneArray", objArray);
    }

    public int[] getIndexToZoneArray () {
        Object[] objArray = {};
        return (int[])remote.method( "getIndexToZoneArray", objArray);
    }

    public int[] getZoneTableRowArray () {
        Object[] objArray = {};
        return (int[])remote.method( "getZoneTableRowArray", objArray);
    }



    /**
     * @param field is the field name to be checked against the column names in the zone data table.
     * @return true if field matches one of the zone data table column names, otherwise false.
     */
    public boolean isValidZoneTableField(String field){
        Object[] objArray = { field };
        return (Boolean)remote.method( "isValidZoneTableField", objArray);
    }


    public String[] getZoneDataTableColumnLabels() {
        Object[] objArray = {};
        return (String[])remote.method( "getZoneDataTableColumnLabels", objArray);
    }

    public int getNumberOfZones(){
        Object[] objArray = {};
        return (Integer)remote.method( "getNumberOfZones", objArray);
    }

    public int getNumberOfSubZones(){
        Object[] objArray = {};
        return (Integer)remote.method( "getNumberOfSubZones", objArray);
    }

    public String[] getSubZoneNames() {
        Object[] objArray = {};
        return (String[])remote.method( "getSubZoneNames", objArray);
    }


    public double[] getZonalWalkPercentagesForTaz( int taz ) {
        Object[] objArray = { taz };
        return (double[])remote.method( "getZonalWalkPercentagesForTaz", objArray);
    }

    public float getZoneTableValue ( int taz, String fieldName ) {
        Object[] objArray = { taz, fieldName };
        return (Float)remote.method( "getZoneTableValue", objArray);
    }

    public int[] getZoneTableIntColumn ( String fieldName ) {
        Object[] objArray = { fieldName };
        return (int[])remote.method( "getZoneTableIntColumn", objArray);
    }

    // get the table column from the fieldname passed in
    public float[] getZoneTableFloatColumn ( String fieldName ) {
        Object[] objArray = { fieldName };
        return (float[])remote.method( "getZoneTableFloatColumn", objArray);
    }



    /**
     * @param tableRowNumber is the zone table row number
     * @return zone number for the table row.
     */
    public int getTazNumber ( int tableRowNumber ) {
        Object[] objArray = { tableRowNumber };
        return (Integer)remote.method( "getTazNumber", objArray);
    }

    /**
     * @return area type from the zone data table for the zone.
     */
    public int[] getZonalAreaType () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalAreaType", objArray);
    }
    
    /**
     * @return cordon from the zone data table for the zone.
     */
    public int[] getZonalCordon () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalCordon", objArray);
    }

    /**
     * @return cordon cost from the zone data table for the zone.
     */
    public int[] getZonalCordonCost () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalCordonCost", objArray);
    }

    /**
     * @return district from the zone data table for the zone.
     */
    public int[] getZonalDistrict () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalDistrict", objArray);
    }

    public int[] getZonalParkTot () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalParkTot", objArray);
    }    

    public int[] getZonalParkLong () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalParkLong", objArray);
    }
    
    public float[] getZonalPropFree () {
        Object[] objArray = {};
        return (float[])remote.method( "getZonalPropFree", objArray);
    }
       
    public float[] getZonalParkRate () {
        Object[] objArray = {};
        return (float[])remote.method( "getZonalParkRate", objArray);
    }
    
    public String getZonalParkTotFieldName () {    
        Object[] objArray = {};
        return (String)remote.method( "getZonalParkTotFieldName", objArray);
    }

    public String getZonalParkRateFieldName () {    
        Object[] objArray = {};
        return (String)remote.method( "getZonalParkRateFieldName", objArray);
    }

    /**
     * @return integer county value from the zone data table for the zone.
     */
    public int[] getZonalCounty () {
        Object[] objArray = {};
        return (int[])remote.method( "getZonalCounty", objArray);
    }

    public int getZoneIsCbd( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneIsCbd", objArray);
    }

    public int getZoneIsUrban( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneIsUrban", objArray);
    }

    public int getZoneIsSuburban( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneIsSuburban", objArray);
    }

    public int getZoneIsRural( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneIsRural", objArray);
    }

    public int getZoneCounty( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneCounty", objArray);
    }

    public int getZoneCordon( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneCordon", objArray);
    }

    public int getZoneCordonCost( int taz ) {
        Object[] objArray = { taz };
        return (Integer)remote.method( "getZoneCordonCost", objArray);
    }

    public float getPopEmpPerSqMi(int taz) {
        Object[] objArray = { taz };
        return (Float)remote.method( "getPopEmpPerSqMi", objArray);
    }


    public float[] getPkAutoRetailAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getPkAutoRetailAccessibity", objArray);
    }

    public float[] getPkAutoTotalAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getPkAutoTotalAccessibity", objArray);
    }

    public float[] getPkTransitRetailAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getPkTransitRetailAccessibity", objArray);
    }

    public float[] getPkTransitTotalAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getPkTransitTotalAccessibity", objArray);
    }

    public float[] getOpAutoRetailAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getOpAutoRetailAccessibity", objArray);
    }

    public float[] getOpAutoTotalAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getOpAutoTotalAccessibity", objArray);
    }

    public float[] getOpTransitRetailAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getOpTransitRetailAccessibity", objArray);
    }

    public float[] getOpTransitTotalAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getOpTransitTotalAccessibity", objArray);
    }

    public float[] getNonMotorizedRetailAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getNonMotorizedRetailAccessibity", objArray);
    }

    public float[] getNonMotorizedTotalAccessibity() {
        Object[] objArray = {};
        return (float[])remote.method( "getNonMotorizedTotalAccessibity", objArray);
    }

    /**
     * Get a new array of zones.
     * 
     */
    public int[] getTazs(){
    	
        Object[] objArray = {};
        return (int[])remote.method( "getTazs",objArray);
    	
    }
    
    /**
     * Get a new array of zones, indexed from 1
     */
    public int[] getTazsOneBased(){
    	
        Object[] objArray = {};
        return (int[])remote.method( "getTazsOneBased",objArray);
    	
    }
   

}