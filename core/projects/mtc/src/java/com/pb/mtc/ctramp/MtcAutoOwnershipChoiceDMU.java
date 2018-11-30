package com.pb.mtc.ctramp;

import java.util.HashMap;

import com.pb.models.ctramp.AutoOwnershipChoiceDMU;
import com.pb.models.ctramp.Person;
import com.pb.models.ctramp.TazDataIf;


public class MtcAutoOwnershipChoiceDMU extends AutoOwnershipChoiceDMU {


    int[] zoneTableRow;
    float[] densityIndex;
    
    public MtcAutoOwnershipChoiceDMU( TazDataIf tazDataManager ) {
        super ();
        setup( tazDataManager );
        setupMethodIndexMap();
    }

    private void setup( TazDataIf tazDataManager ) {

        zoneTableRow = tazDataManager.getZoneTableRowArray();
        densityIndex = getZonalDensityIndex(tazDataManager); 
    }
    
	public double getLnHhIncomeThousands() {
		double inc1000 = hh.getIncomeInDollars() / 1000.0;
		// make consistent with lowest value in estimation file
		inc1000 = Math.max(2.5, inc1000); 
		double value = Math.log(inc1000); 
		return value; 
	}
    
	public double getHhIncomeInDollars() {
		double value = hh.getIncomeInDollars();
		return value; 
	}

	public int getNumPersAge0to4() {
		return hh.getNumPersons0to4(); 
	}
	
	public int getNumPersAge5to15() {
		return hh.getNumPersons5to15(); 
	}
	
	public int getNumPersAge16to17() {
		return hh.getNumPersons16to17(); 
	}

	public int getNumPersAge18to24() {
		return hh.getNumPersons18to24(); 
	}
	
	public int getNumPersAge25to34() {
		Person[] persons = hh.getPersons(); 
	    int numPersons25to34 = 0;
	    for (int i=1; i < persons.length; i++) {
	        if ( persons[i].getAge() >= 25 && persons[i].getAge() <= 34 )
	            numPersons25to34 ++;
	    }
	    return numPersons25to34;
	}

	public int getNumPersAge65Plus() {
		Person[] persons = hh.getPersons(); 
	    int numPersons65Plus = 0;
	    for (int i=1; i < persons.length; i++) {
	        if ( persons[i].getAge() >= 65)
	        	numPersons65Plus ++;
	    }
	    return numPersons65Plus;
	}

    public float getDensityIndex(){
        int zone = hh.getHhTaz(); 
        int index = zoneTableRow[zone] - 1;
        return densityIndex[index];
    }
    
    // guojy: added for M. Gucwa's research on automated vehicles
    public int getHAnalyst(){
    	return hh.getHAnalyst();
    }


    private void setupMethodIndexMap() {
        methodIndexMap = new HashMap<String, Integer>();
        
        methodIndexMap.put( "getDrivers",  1 );
        methodIndexMap.put( "getWorkers",  2 );
        
        methodIndexMap.put( "getLnHhIncomeThousands", 4);
        methodIndexMap.put( "getHhIncomeInDollars",   5);
        methodIndexMap.put( "getNumPersAge0to4",   6);
        methodIndexMap.put( "getNumPersAge5to15",  7);
        methodIndexMap.put( "getNumPersAge16to17", 8);
        methodIndexMap.put( "getNumPersAge18to24", 9);
        methodIndexMap.put( "getNumPersAge25to34", 10);       
        methodIndexMap.put( "getWorkTourAutoTimeSavings", 11);
        methodIndexMap.put( "getSchoolDriveTourAutoTimeSavings", 12 );
        methodIndexMap.put( "getSchoolNonDriveTourAutoTimeSavings", 13 );
        methodIndexMap.put( "getDensityIndex", 14 );
        // guojy: added for M. Gucwa's research on automated vehicles
        methodIndexMap.put( "getHAnalyst", 15 );
        methodIndexMap.put( "getNumPersAge65Plus", 16); 
        methodIndexMap.put( "getWorkTourAutoTime",17);
        
        
     }
    
    


    public double getValueForIndex(int variableIndex, int arrayIndex) {

        switch ( variableIndex ){
        	case 1:  return getDrivers();                                                   
        	case 2:  return getWorkers();                    
        	
        	case 4:  return getLnHhIncomeThousands();                                          
        	case 5:  return getHhIncomeInDollars();                          
        	case 6:  return getNumPersAge0to4();                                    
        	case 7:  return getNumPersAge5to15();                                   
        	case 8:  return getNumPersAge16to17();                                  
        	case 9:  return getNumPersAge18to24();                                  
        	case 10: return getNumPersAge25to34();                                  
        	case 11: return getWorkTourAutoTimeSavings();                    
        	case 12: return getSchoolDriveTourAutoTimeSavings();      
        	case 13: return getSchoolNonDriveTourAutoTimeSavings(); 
            case 14: return getDensityIndex();
            // guojy: added for M. Gucwa's research on automated vehicles
            case 15: return getHAnalyst();
            case 16: return getNumPersAge65Plus();
            case 17: return getWorkTourAutoTime();

            default:
                logger.error("method number = "+variableIndex+" not found");
                throw new RuntimeException("method number = "+variableIndex+" not found");
        
        }
    }
    

    // private methods

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


}