package com.pb.models.ctramp;

import java.util.HashMap;


/**
 * @author Jim Hicks
 *
 * Class for managing household and person object data read from synthetic population files.
 */
public interface HouseholdDataManagerIf {

    public String testRemote();

    public void setPropertyFileValues ( HashMap<String, String> propertyMap );

    public void setDebugHhIdsFromHashmap ();

    public int[] getRandomOrderHhIndexArray( int numHhs );
    public int[] getHomeTazOrderHhIndexArray( int[] hhIds );
    
    public void mapTablesToHouseholdObjects( String inputHouseholdFileName, String inputPersonFileName, ModelStructure modelStructure, TazDataIf tazDataManager );

    public int getArrayIndex( int hhId );
    
    public void setHhArray( Household[] hhs );
    public void setHhArray( Household[] tempHhs, int startIndex );
    
    public void setupHouseholdDataManager( ModelStructure modelStructure, TazDataIf tazDataManager, String inputHouseholdFileName, String inputPersonFileName );

    public int[][][] getTourPurposePersonsByHomeZone( String[] purposeList );
    public double[][][] getMandatoryToursByDestZoneSubZone();
    public int[][] getIndividualNonMandatoryToursByHomeZoneSubZone( String purposeString );
    public int[][] getJointToursByHomeZoneSubZone( String purposeString );
    public int[][] getAtWorkSubtoursByWorkZoneSubZone( String purposeString );
    
    public void logPersonSummary( Household[] hhs );
    
    public void setUwslRandomCount();

    public void setAoRandomCount();

    public void setCdapRandomCount();

    public void setImtfRandomCount();

    public void setImtodRandomCount();

    public void setImmcRandomCount();
    
    public void setAwfRandomCount();

    public void setAwlRandomCount();

    public void setAwtodRandomCount();

    public void setAwmcRandomCount();
    
    public void setJtfRandomCount();

    public void setJtlRandomCount();

    public void setJtodRandomCount();

    public void setJmcRandomCount();
    
    public void setInmtfRandomCount();

    public void setInmtlRandomCount();

    public void setInmtodRandomCount();

    public void setInmmcRandomCount();
    
    public void setStfRandomCount();

    public void setStlRandomCount();

    public void resetUwslRandom();

    public void resetAoRandom();

    public void resetFpRandom();

    public void resetCdapRandom();

    public void resetImtfRandom();

    public void resetImtodRandom();

    public void resetImmcRandom();
    
    public void resetAwfRandom();

    public void resetAwlRandom();

    public void resetAwtodRandom();

    public void resetAwmcRandom();
    
    public void resetJtfRandom();

    public void resetJtlRandom();

    public void resetJtodRandom();

    public void resetJmcRandom();
    
    public void resetInmtfRandom();

    public void resetInmtlRandom();

    public void resetInmtodRandom();

    public void resetInmmcRandom();
    
    public void resetStfRandom();

    public void resetStlRandom();



    /**
     *  set the hh id for which debugging info from choice models applied to this household will be logged if debug logging.
     */
    public void setDebugHouseholdId( int debugHhId, boolean value );

    /**
     * Sets the HashSet used to trace households for debug purposes and sets the
     * debug switch for each of the listed households. Also sets
     */
    public void setTraceHouseholdSet();


    /**
     * Sets the HashSet used to trace households for debug purposes and sets the
     * debug switch for each of the listed households. Also sets
     */
    public void setHouseholdSampleRate( float sampleRate, int sampleSeed );


    /**
     * return the array of Household objects holding the synthetic population and choice model outcomes.
     * @return hhs
     */
    public Household[] getHhArray();
    public Household[] getHhArray(int firstHhIndex, int lastHhIndex);


    /**
     * return the number of household objects read from the synthetic population.
     * @return
     */
    public int getNumHouseholds();



    /**
     * set walk segment (0-none, 1-short, 2-long walk to transit access) for the origin for this tour
     */
    public short getInitialOriginWalkSegment (short taz, double randomNumber);

    
    
    /*
    public long getBytesUsedByHouseholdArray();
    
    public void createSerializedHhArrayInFileFromObject( String serializedObjectFileName, String serializedObjectKey );
    public Household[] createHhArrayFromSerializedObjectInFile( String serializedObjectFileName, String serializedObjectKey );
     */
}