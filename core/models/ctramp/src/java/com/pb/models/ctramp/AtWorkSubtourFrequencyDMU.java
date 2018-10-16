package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;

import org.apache.log4j.Logger;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;


public class AtWorkSubtourFrequencyDMU implements Serializable, VariableTable {

    protected transient Logger logger = Logger.getLogger(AtWorkSubtourFrequencyDMU.class);

    protected HashMap<String, Integer> methodIndexMap;
    
    
    protected Household hh;
    protected Person person;
    protected Tour tour;
    protected IndexValues dmuIndex;

    protected int homeTazIsUrban;
    protected int workTazAreaType;
    
    protected ModelStructure modelStructure;
    

    public AtWorkSubtourFrequencyDMU( ModelStructure modelStructure ){
        this.modelStructure = modelStructure;
    	dmuIndex = new IndexValues();
    }



    public Household getHouseholdObject() {
        return hh;
    }

    public void setHouseholdObject ( Household hhObject ) {
        hh = hhObject;
    }

    public void setPersonObject ( Person persObject ) {
        person = persObject;
    }

    public void setTourObject ( Tour tourObject ) {
        tour = tourObject;
    }




    // DMU methods - define one of these for every @var in the mode choice control file.

    public void setDmuIndexValues( int hhId, int zoneId, int origTaz, int destTaz ) {
        dmuIndex.setHHIndex( hhId );
        dmuIndex.setZoneIndex( zoneId );
        dmuIndex.setOriginZone( origTaz );
        dmuIndex.setDestZone( destTaz );

        dmuIndex.setDebug(false);
        dmuIndex.setDebugLabel ( "" );
        if ( hh.getDebugChoiceModels() ) {
            dmuIndex.setDebug(true);
            dmuIndex.setDebugLabel ( "Debug INMTF UEC" );
        }

    }


    public IndexValues getDmuIndexValues() {
        return dmuIndex;
    }


    public int getNumAutos() {
        return hh.getAutoOwnershipModelResult();
    }


    public int getPersonIsFullTimeWorker() {
        return person.getPersonIsFullTimeWorker();
    }

    public int getPersonIsNonworker() {
        return person.getPersonIsNonWorkingAdultUnder65() + person.getPersonIsNonWorkingAdultOver65();
    }





    public void setWorkTazAreaType( int at ){
        workTazAreaType = at;
    }

    public int getWorkTazAreaType() {
        return workTazAreaType;
    }
    


    public int getWorkTourDuration() {
        int start = tour.getTourStartHour();
        int end = tour.getTourEndHour();
        return end - start;
    }
    
    /**
     * @return number of joint non-mandatory maint, shop, eat-out tours participated in by person.
     */
    public int getJointMaintShopEatPerson(){
        int numTours = 0;
        Tour[] jt = hh.getJointTourArray();
        if ( jt != null ) {
            int personNum = person.getPersonNum();
            for ( Tour t : jt ) {
                // if joint tour is maint/shop/eat, see if person participated
                String tourPurpose = t.getTourPurpose();
                if ( tourPurpose.equalsIgnoreCase( modelStructure.getOthMaintPurposeName() ) ||
                     tourPurpose.equalsIgnoreCase( modelStructure.getShoppingPurposeName() ) ||
                     tourPurpose.equalsIgnoreCase( modelStructure.getEatOutPurposeName() ) ) {
                        byte[] personNums = t.getPersonNumArray();
                        for ( int i=0; i < personNums.length; i++ ) {
                            if (personNums[i] == personNum) {
                                numTours ++;
                                break;
                            }
                        }
                }
            }
        }

        return numTours;
    }
    
    /**
     * @return number of joint non-mandatory discretionary tours participated in by person.
     */
    public int getJointDiscrPerson(){
        int numTours = 0;
        Tour[] jt = hh.getJointTourArray();
        if ( jt != null ) {
            int personNum = person.getPersonNum();
            for ( Tour t : jt ) {
                // if joint tour is maint/shop/eat, see if person participated
                String tourPurpose = t.getTourPurpose();
                if ( tourPurpose.equalsIgnoreCase( modelStructure.getOthDiscrPurposeName() ) ) {
                    byte[] personNums = t.getPersonNumArray();
                    for ( int i=0; i < personNums.length; i++ ) {
                        if (personNums[i] == personNum) {
                            numTours ++;
                            break;
                        }
                    }
                }
            }
        }

        return numTours;
    }
    
    /**
     * @return number of individual non-mandatory maint, shop, escort tours by
     * a person who is a full time worker.
     */
    public int getIndivMaintShopEscortFt() {
        int numTours = 0;
        if ( person.getPersonIsFullTimeWorker() == 1 )
            numTours = getNumIndivMaintShopEscortTours();
        return numTours;
    }
    
    /**
     * @return number of individual non-mandatory maint, shop, escort tours by
     * a person who is a part time worker.
     */
    public int getIndivMaintShopEscortPt() {
        int numTours = 0;
        if ( person.getPersonIsPartTimeWorker() == 1 )
            numTours = getNumIndivMaintShopEscortTours();
        return numTours;
    }
    

    /**
     * @return number of individual non-mandatory discretionary tours by
     * a person who is a full time worker.
     */
    public int getIndivDiscrFt() {
        int numTours = 0;
        if ( person.getPersonIsFullTimeWorker() == 1 )
            numTours = getNumIndivDiscrTours();
        return numTours;
    }
    
    /**
     * @return number of individual non-mandatory discretionary tours by
     * a person who is a part time worker.
     */
    public int getIndivDiscrPt() {
        int numTours = 0;
        if ( person.getPersonIsPartTimeWorker() == 1 )
            numTours = getNumIndivDiscrTours();
        return numTours;
    }
    
    /**
     * @return number of individual non-mandatory eat-out tours by person.
     */
    public int getIndivEatOut() {
        int numTours = 0;
        ArrayList<Tour> tourList = person.getListOfIndividualNonMandatoryTours();
        if ( tourList != null ) {
            for ( Tour t : tourList ) {
                String tourPurpose = t.getTourPurpose();
                if ( tourPurpose.equalsIgnoreCase( modelStructure.getEatOutPurposeName() ) ) {
                        numTours ++;
                }
            }
        }
        return numTours;
    }
    
    
    private int getNumIndivMaintShopEscortTours() {
        int numTours = 0;
        ArrayList<Tour> tourList = person.getListOfIndividualNonMandatoryTours();
        if ( tourList != null ) {
            for ( Tour t : tourList ) {
                String tourPurpose = t.getTourPurpose();
                if ( tourPurpose.equalsIgnoreCase( modelStructure.getOthMaintPurposeName() ) ||
                     tourPurpose.equalsIgnoreCase( modelStructure.getShoppingPurposeName() ) ||
                     tourPurpose.equalsIgnoreCase( modelStructure.getEscortPurposeName() ) ) {
                        numTours ++;
                }
            }
        }
        return numTours;
    }
    
    private int getNumIndivDiscrTours() {
        int numTours = 0;
        ArrayList<Tour> tourList = person.getListOfIndividualNonMandatoryTours();
        if ( tourList != null ) {
            for ( Tour t : tourList ) {
                String tourPurpose = t.getTourPurpose();
                if ( tourPurpose.equalsIgnoreCase( modelStructure.getOthDiscrPurposeName() ) ) {
                        numTours ++;
                }
            }
        }
        return numTours;
    }
 
    public int getWorkTourModeIsSOV() {
        boolean tourModeIsSov = modelStructure.getTourModeIsSov( tour.getTourModeChoice() );
        if ( tourModeIsSov )
            return 1;
        else
            return 0;
    }
    
    public int getNumPersonWorkTours() {
        return person.getListOfWorkTours().size();
    }
    
    /**
     * return 1 if person is worker or student with non-mandatory tours; 0 otherwise.
     */
    public float getWorkStudNonMandatoryTours () {
        if ( person.getPersonIsWorker() == 1 || person.getPersonIsStudent() == 1 ) { 
            ArrayList<Tour> tourList = person.getListOfIndividualNonMandatoryTours(); 
            if ( tourList ==  null ) 
                return 0;
            else if ( tourList.size() > 0 ) 
                return 1;
        }
        return 0;
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
