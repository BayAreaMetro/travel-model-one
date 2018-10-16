package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;


/**
 * @author Jim Hicks
 *
 * Class for managing household and person object data read from synthetic population files.
 */
public class HouseholdDataManagerRmi implements HouseholdDataManagerIf, Serializable {

    UtilRmi remote;
    String connectString;



    public HouseholdDataManagerRmi( String hostname, int port, String className ){

        connectString = String.format("//%s:%d/%s", hostname, port, className );
        remote = new UtilRmi(connectString);

    }

    public void setPropertyFileValues ( HashMap<String, String> propertyMap ) {
        Object[] objArray = { propertyMap };
        remote.method( "setPropertyFileValues", objArray);
    }

    public void setDebugHhIdsFromHashmap () {
        Object[] objArray = {};
        remote.method( "setDebugHhIdsFromHashmap", objArray);
    }

    public void setupHouseholdDataManager(ModelStructure modelStructure, TazDataIf tazDataManager, String inputHouseholdFileName, String inputPersonFileName ){
        Object[] objArray = { modelStructure, tazDataManager, inputHouseholdFileName, inputPersonFileName };
        remote.method( "setupHouseholdDataManager", objArray);
    }

    public void logPersonSummary( Household[] hhs ) {
        Object[] objArray = { hhs };
        remote.method( "logPersonSummary", objArray);
    }
    
    public int getArrayIndex( int hhId ) {
        Object[] objArray = { hhId };
        return (Integer)remote.method( "getArrayIndex", objArray);
    }
    
    public double[][][] getMandatoryToursByDestZoneSubZone() {
        Object[] objArray = {};
        return (double[][][])remote.method( "getMandatoryToursByDestZoneSubZone", objArray);
    }    
    
    public int[][][] getTourPurposePersonsByHomeZone( String[] purposeList ) {
        Object[] objArray = { purposeList };
        return (int[][][])remote.method( "getTourPurposePersonsByHomeZone", objArray);
    }

    public int[][] getIndividualNonMandatoryToursByHomeZoneSubZone( String purposeString ) {
        Object[] objArray = { purposeString };
        return (int[][])remote.method( "getIndividualNonMandatoryToursByHomeZoneSubZone", objArray);
    }    
    
    public int[][] getJointToursByHomeZoneSubZone( String purposeString ) {
        Object[] objArray = { purposeString };
        return (int[][])remote.method( "getJointToursByHomeZoneSubZone", objArray);
    }    
    
    public int[][] getAtWorkSubtoursByWorkZoneSubZone( String purposeString ) {
        Object[] objArray = { purposeString };
        return (int[][])remote.method( "getAtWorkSubtoursByWorkZoneSubZone", objArray);
    }    
    
    public String testRemote() {
        Object[] objArray = {};
        return (String)remote.method( "testRemote", objArray);
    }

    public void mapTablesToHouseholdObjects() {
        Object[] objArray = {};
        remote.method( "mapTablesToHouseholdObjects", objArray);
    }

    public void mapTablesToHouseholdObjects( String inputHouseholdFileName, String inputPersonFileName, ModelStructure modelStructure, TazDataIf tazDataManager ) {
        Object[] objArray = { inputHouseholdFileName, inputPersonFileName, modelStructure, tazDataManager };
        remote.method( "mapTablesToHouseholdObjects", objArray);
    }

    public void writeResultData () {
        Object[] objArray = {};
        remote.method( "writeResultData", objArray);
    }

    public int[] getRandomOrderHhIndexArray( int numHhs ) {
        Object[] objArray = { numHhs };
        return (int[])remote.method( "getRandomOrderHhIndexArray", objArray);
    }

    public int[] getHomeTazOrderHhIndexArray( int[] hhIds ) {
        Object[] objArray = { hhIds };
        return (int[])remote.method( "getHomeTazOrderHhIndexArray", objArray);
    }
    
    
    /**
     *  set the hh id for which debugging info from choice models applied to this household will be logged if debug logging.
     */
    public void setDebugHouseholdId( int debugHhId, boolean value ) {
        Object[] objArray = { debugHhId, value };
        remote.method( "setDebugHouseholdId", objArray);
    }

    /**
     * Sets the HashSet used to trace households for debug purposes and sets the
     * debug switch for each of the listed households. Also sets
     */
    public void setTraceHouseholdSet(){
        Object[] objArray = {};
        remote.method( "setTraceHouseholdSet", objArray);
    }

    public void setHouseholdSampleRate( float sampleRate, int sampleSeed ){
        Object[] objArray = { sampleRate, sampleSeed };
        remote.method( "setHouseholdSampleRate", objArray);
    }

    public void setUwslRandomCount() {
        Object[] objArray = {};
        remote.method( "setUwslRandomCount", objArray);
    }

    public void setAoRandomCount() {
        Object[] objArray = {};
        remote.method( "setAoRandomCount", objArray);
    }

    public void setFpRandomCount() {
        Object[] objArray = {};
        remote.method( "setFpRandomCount", objArray);
    }

    public void setCdapRandomCount() {
        Object[] objArray = {};
        remote.method( "setCdapRandomCount", objArray);
    }

    public void setImtfRandomCount() {
        Object[] objArray = {};
        remote.method( "setImtfRandomCount", objArray);
    }

    public void setImtodRandomCount() {
        Object[] objArray = {};
        remote.method( "setImtodRandomCount", objArray);
    }

    public void setImmcRandomCount() {
        Object[] objArray = {};
        remote.method( "setImmcRandomCount", objArray);
    }

    public void setAwfRandomCount() {
        Object[] objArray = {};
        remote.method( "setAwfRandomCount", objArray);
    }

    public void setAwlRandomCount() {
        Object[] objArray = {};
        remote.method( "setAwlRandomCount", objArray);
    }

    public void setAwtodRandomCount() {
        Object[] objArray = {};
        remote.method( "setAwtodRandomCount", objArray);
    }

    public void setAwmcRandomCount() {
        Object[] objArray = {};
        remote.method( "setAwmcRandomCount", objArray);
    }
    
    public void setJtfRandomCount() {
        Object[] objArray = {};
        remote.method( "setJtfRandomCount", objArray);
    }

    public void setJtlRandomCount() {
        Object[] objArray = {};
        remote.method( "setJtlRandomCount", objArray);
    }

    public void setJtodRandomCount() {
        Object[] objArray = {};
        remote.method( "setJtodRandomCount", objArray);
    }
    
    public void setJmcRandomCount() {
        Object[] objArray = {};
        remote.method( "setJmcRandomCount", objArray);
    }

    public void setInmtfRandomCount() {
        Object[] objArray = {};
        remote.method( "setInmtfRandomCount", objArray);
    }

    public void setInmtlRandomCount() {
        Object[] objArray = {};
        remote.method( "setInmtlRandomCount", objArray);
    }

    public void setInmtodRandomCount() {
        Object[] objArray = {};
        remote.method( "setInmtodRandomCount", objArray);
    }
    
    public void setInmmcRandomCount() {
        Object[] objArray = {};
        remote.method( "setInmmcRandomCount", objArray);
    }

    public void setStfRandomCount() {
        Object[] objArray = {};
        remote.method( "setStfRandomCount", objArray);
    }

    public void setStlRandomCount() {
        Object[] objArray = {};
        remote.method( "setStlRandomCount", objArray);
    }

    public void resetUwslRandom() {
        Object[] objArray = {};
        remote.method( "resetUwslRandom", objArray);
    }

    public void resetAoRandom() {
        Object[] objArray = {};
        remote.method( "resetAoRandom", objArray);
    }

    public void resetFpRandom() {
        Object[] objArray = {};
        remote.method( "resetFpRandom", objArray);
    }

    public void resetCdapRandom() {
        Object[] objArray = {};
        remote.method( "resetCdapRandom", objArray);
    }

    public void resetImtfRandom() {
        Object[] objArray = {};
        remote.method( "resetImtfRandom", objArray);
    }

    public void resetImtodRandom() {
        Object[] objArray = {};
        remote.method( "resetImtodRandom", objArray);
    }

    public void resetImmcRandom() {
        Object[] objArray = {};
        remote.method( "resetImmcRandom", objArray);
    }
    
    public void resetAwfRandom() {
        Object[] objArray = {};
        remote.method( "resetAwfRandom", objArray);
    }

    public void resetAwlRandom() {
        Object[] objArray = {};
        remote.method( "resetAwlRandom", objArray);
    }

    public void resetAwtodRandom() {
        Object[] objArray = {};
        remote.method( "resetAwtodRandom", objArray);
    }

    public void resetAwmcRandom() {
        Object[] objArray = {};
        remote.method( "resetAwmcRandom", objArray);
    }
    
    public void resetJtfRandom() {
        Object[] objArray = {};
        remote.method( "resetJtfRandom", objArray);
    }

    public void resetJtlRandom() {
        Object[] objArray = {};
        remote.method( "resetJtlRandom", objArray);
    }

    public void resetJtodRandom() {
        Object[] objArray = {};
        remote.method( "resetJtodRandom", objArray);
    }

    public void resetJmcRandom() {
        Object[] objArray = {};
        remote.method( "resetJmcRandom", objArray);
    }
    
    public void resetInmtfRandom() {
        Object[] objArray = {};
        remote.method( "resetInmtfRandom", objArray);
    }

    public void resetInmtlRandom() {
        Object[] objArray = {};
        remote.method( "resetInmtlRandom", objArray);
    }

    public void resetInmtodRandom() {
        Object[] objArray = {};
        remote.method( "resetInmtodRandom", objArray);
    }

    public void resetInmmcRandom() {
        Object[] objArray = {};
        remote.method( "resetInmmcRandom", objArray);
    }
    
    public void resetStfRandom() {
        Object[] objArray = {};
        remote.method( "resetStfRandom", objArray);
    }

    public void resetStlRandom() {
        Object[] objArray = {};
        remote.method( "resetStlRandom", objArray);
    }


    /**
     * return the array of Household objects holding the synthetic population and choice model outcomes.
     * @return hhs
     */
    public Household[] getHhArray() {
        Object[] objArray = {};
        return (Household[])remote.method( "getHhArray", objArray);
    }
    
    public Household[] getHhArray(int first, int last) {
        Object[] objArray = { first, last };
        return (Household[])remote.method( "getHhArray", objArray);
    }

    public void setHhArray( Household[] hhs ) {
        Object[] objArray = { hhs };
        remote.method( "setHhArray", objArray);
    }

    public void setHhArray( Household[] tempHhs, int startIndex )  {
        Object[] objArray = { tempHhs, startIndex };
        remote.method( "setHhArray", objArray);
    }
    
    
    /**
     * return the array of Household objects holding the synthetic population and choice model outcomes.
     * @return hhs
     */
    public int[] getHhIndexArray() {
        Object[] objArray = {};
        return (int[])remote.method( "getHhIndexArray", objArray);
    }

    /**
     * return the number of household objects read from the synthetic population.
     * @return number of households in synthetic population
     */
    public int getNumHouseholds() {
        Object[] objArray = {};
        return (Integer)remote.method( "getNumHouseholds", objArray);
    }


    /**
     * set walk segment (0-none, 1-short, 2-long walk to transit access) for the origin for this tour
     */
    public short getInitialOriginWalkSegment (short taz, double randomNumber) {
        Object[] objArray = { taz, randomNumber };
        return (Short)remote.method( "getInitialOriginWalkSegment", objArray);
    }

    public long getBytesUsedByHouseholdArray() {
        Object[] objArray = {};
        return (Long)remote.method( "getBytesUsedByHouseholdArray", objArray);
    }
    
    
    public void createSerializedHhArrayInFileFromObject( String serializedObjectFileName, String serializedObjectKey ) {
        Object[] objArray = { serializedObjectFileName, serializedObjectKey };
        remote.method( "createSerializedHhArrayInFileFromObject", objArray);
    }

    
    public Household[] createHhArrayFromSerializedObjectInFile( String serializedObjectFileName, String serializedObjectKey ) {
        Object[] objArray = { serializedObjectFileName, serializedObjectKey };
        return (Household[])remote.method( "createHhArrayFromSerializedObjectInFile", objArray);
    }
    
}