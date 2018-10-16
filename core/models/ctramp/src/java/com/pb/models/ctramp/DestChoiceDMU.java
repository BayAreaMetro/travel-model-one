package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;


public abstract class DestChoiceDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(DestChoiceDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    public DestChoiceSize dcSizeObj;

    public Household hh;
    public Person person;
    public Tour tour;
    public IndexValues dmuIndex = null;

    public int[] altToZone;
    public int[] altToSubZone;

    public double[][][] modeChoiceLogsums;
    public double[][] dcSoaCorrections;
    
    public ModelStructure modelStructure;
    
    
    public DestChoiceDMU ( TazDataIf tazDataManager, ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
        initDmuObject( tazDataManager );
    }


    abstract public void setMcLogsum( int index, int zone, int subzone, double logsum );
    
    
    
    
    private void initDmuObject( TazDataIf tazDataManager ) {

        dmuIndex = new IndexValues();

        altToZone = tazDataManager.getAltToZoneArray();
        altToSubZone = tazDataManager.getAltToSubZoneArray();

        // create default objects - some choice models use these as place holders for values
        person = new Person( null, -1 );
        hh = new Household();


        int numZones = tazDataManager.getNumberOfZones();
        int numSubZones = tazDataManager.getNumberOfSubZones();

        
        int numMcLogsumIndices = modelStructure.getSkimPeriodCombinationIndices().length;
        modeChoiceLogsums = new double[numMcLogsumIndices][numZones+1][numSubZones];
        dcSoaCorrections = new double[numZones+1][numSubZones];

    }

    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }
    
    public void setPersonObject ( Person personObject ) {
        person = personObject;
    }
    
    public void setTourObject ( Tour tour ) {
        this.tour = tour;
    }

    public void setDestChoiceSize ( DestChoiceSize dcSizeObj ) {
        this.dcSizeObj = dcSizeObj;
    }


    public void setDcSoaCorrections( int zone, int subzone, double correction ){
        dcSoaCorrections[zone][subzone] = correction;
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
            dmuIndex.setDebugLabel ( "Debug DC UEC" );
        }

    }
    
    public IndexValues getDmuIndexValues() {
        return dmuIndex; 
    }
    
    public Household getHouseholdObject() {
        return hh;
    }

    public Person getPersonObject() {
        return person;
    }
    
    


    // DMU methods - define one of these for every @var in the mode choice control file.

    protected double getDcSoaCorrectionsAlt( int alt ){
        int zone = altToZone[alt];
        int subzone = altToSubZone[alt];
        return dcSoaCorrections[zone][subzone];
    }
    
    protected double getMcLogsumDestAlt( int index, int zone, int subZone ) {
        return modeChoiceLogsums[index][zone][subZone];
    }
    
    protected double getLnDcSizeForPurposeAlt( int alt, String purposeString ){

        int zone = altToZone[alt];
        int subzone = altToSubZone[alt];
        
        int purposeIndex = dcSizeObj.getDcSizeArrayPurposeIndex(purposeString);
        double size = dcSizeObj.getDcSize(purposeIndex, zone, subzone);

        double logSize = 0.0;
        if ( size > 0 )
            logSize = Math.log(size);
        
        return logSize;
    	
    }
    
    

    
    protected int getZonalShortWalkAccessOrig() {
        if ( hh.getHhWalkSubzone() == 1 )
            return 1;
        else
            return 0;
    }


    protected int getZonalShortWalkAccessDestAlt( int alt ) {
        int subzone = altToSubZone[alt];
        if ( subzone == 1 )
            return 1;
        else
            return 0;
    }
    
    protected int getAutos() {
        return hh.getAutoOwnershipModelResult();
    }
    
    protected int getWorkers() {
        return hh.getWorkers();
    }

    protected int getNumChildrenUnder16() {
        return hh.getNumChildrenUnder16();
    }

    protected int getNumChildrenUnder19() {
        return hh.getNumChildrenUnder19();
    }

    protected int getAge() {
        return person.getAge();
    }

    protected int getFullTimeWorker() {
        if ( person.getPersonIsFullTimeWorker() == 1 )
            return 1;
        else
            return 0;
    }

    protected int getWorkTaz() {       
        return person.getUsualWorkLocation();
    }

    protected int getWorkTourModeIsSOV() {
        boolean tourModeIsSov = modelStructure.getTourModeIsSov( tour.getTourModeChoice() );
        if ( tourModeIsSov )
            return 1;
        else
            return 0;
    }
    
    
    protected int getTourIsJoint() {
        return tour.getTourCategoryIndex() == ModelStructure.JOINT_NON_MANDATORY_CATEGORY_INDEX ? 1 : 0;
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


