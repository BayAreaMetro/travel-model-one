package com.pb.models.ctramp;

import com.pb.common.datafile.DataFile;
import com.pb.common.datafile.DataReader;
import com.pb.common.datafile.DataWriter;
import com.pb.common.datafile.DiskObjectArray;
import com.pb.common.datafile.OLD_CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.IndexSort;
import com.pb.common.util.ObjectUtil;
import com.pb.common.util.SeededRandom;
import com.pb.common.model.ChoiceModelApplication;
import com.pb.models.ctramp.jppf.CtrampApplication;

import java.io.*;
import java.util.*;

import org.apache.log4j.Logger;

/**
 * @author Jim Hicks
 *
 * Class for managing household and person object data read from synthetic population files.
 */
public abstract class HouseholdDataManager implements HouseholdDataManagerIf, Serializable {

    protected transient Logger logger = Logger.getLogger(HouseholdDataManager.class);

    protected static int MAX_HHS_PER_FILE = 100000;    
    protected static int MAX_BYTES_HH_OBJECT = 30000;
    protected static int NUMBER_OF_IN_MEMORY_HHS = 10000;
    

    
    
    public static final String PROPERTIES_SYNPOP_INPUT_HH   = "PopulationSynthesizer.InputToCTRAMP.HouseholdFile";
    public static final String PROPERTIES_SYNPOP_INPUT_PERS = "PopulationSynthesizer.InputToCTRAMP.PersonFile";

    public static final String NUMBER_OF_HH_OBJECTS_HELD_IN_MEMORY_KEY = "Number.InMemory.HHs";

    public static final String RANDOM_SEED_NAME = "Model.Random.Seed";

    public static final String OUTPUT_HH_DATA_FILE_TARGET = "outputHouseholdData.file";
    public static final String OUTPUT_PERSON_DATA_FILE_TARGET = "outputPersonData.file";
    
    public static final String HH_ID_FIELD_NAME              = "HHID";
    public static final String HH_HOME_TAZ_FIELD_NAME        = "TAZ";
    public static final String HH_INCOME_CATEGORY_FIELD_NAME = "hinccat1";
    public static final String HH_INCOME_DOLLARS_FIELD_NAME  = "HINC";
    public static final String HH_WORKERS_FIELD_NAME         = "hworkers";
    public static final String HH_AUTOS_FIELD_NAME           = "VEHICL";
    public static final String HH_SIZE_FIELD_NAME            = "PERSONS";
    public static final String HH_TYPE_FIELD_NAME            = "HHT";

    public static final String[] hhHeadings = {
        HH_ID_FIELD_NAME,
        HH_HOME_TAZ_FIELD_NAME,
        HH_INCOME_CATEGORY_FIELD_NAME,
        HH_INCOME_DOLLARS_FIELD_NAME,
        HH_WORKERS_FIELD_NAME,
        HH_AUTOS_FIELD_NAME,
        HH_SIZE_FIELD_NAME,
        HH_TYPE_FIELD_NAME
    };
    
    
    
    public static final String PERSON_HH_ID_FIELD_NAME               = "HHID";
    public static final String PERSON_PERSON_ID_FIELD_NAME           = "PERID";
    public static final String PERSON_AGE_FIELD_NAME                 = "AGE";
    public static final String PERSON_GENDER_FIELD_NAME              = "SEX";
    public static final String PERSON_EMPLOYMENT_CATEGORY_FIELD_NAME = "pemploy";
    public static final String PERSON_STUDENT_CATEGORY_FIELD_NAME    = "pstudent";
    public static final String PERSON_TYPE_CATEGORY_FIELD_NAME       = "ptype";

    public static final String[] persHeadings = {
        PERSON_HH_ID_FIELD_NAME,
        PERSON_PERSON_ID_FIELD_NAME,
        PERSON_AGE_FIELD_NAME,
        PERSON_GENDER_FIELD_NAME,
        PERSON_EMPLOYMENT_CATEGORY_FIELD_NAME,
        PERSON_STUDENT_CATEGORY_FIELD_NAME,
        PERSON_TYPE_CATEGORY_FIELD_NAME
    };
    
    
    
//    public static final String MODELED_WORK_ZONE_FIELD_NAME      = "chosenWorkZone";
//    public static final String MODELED_WORK_SUBZONE_FIELD_NAME   = "chosenWorkSubZone";
//    public static final String MODELED_SCHOOL_ZONE_FIELD_NAME    = "chosenSchoolZone";
//    public static final String MODELED_SCHOOL_SUBZONE_FIELD_NAME = "chosenSchoolSubZone";
//    
//    public static final String MODELED_CDAP_ACTIVITY_PATTERN_FIELD_NAME = "chosenActivityPattern";
//    public static final String MODELED_CDAP_ACTIVITY_FIELD_NAME         = "chosenActivity";
//    
//    public static final String MODELED_MANDATORY_WORK_TOURS            = "numberOfMandatoryWorkTours";
//    public static final String MODELED_MANDATORY_SCHOOL_TOURS          = "numberOfMandatorySchoolTours";
//    public static final String MODELED_MANDATORY_WORK_AND_SCHOOL_TOURS = "numberOfMandatoryWorkAndSchoolTours";

    protected static final String MAX_HHS_PER_DISK_OBJECT_FILE_KEY = "Households.disk.object.maximum.hhs.per.file";
    protected static final String NUMBER_OF_DISK_OBJECT_FILES_KEY =  "Households.disk.object.number.of.files";
    
    public static final String PROPERTIES_HOUSEHOLD_TRACE_LIST = "Debug.Trace.HouseholdIdList";


    //protected DiskObjectArray[] hhDiskObjectArray;
    protected ArrayList<DiskObjectArray> hhDiskObjectArrayList = null;

    protected HashMap<String, String> propertyMap;
    
    protected String projectDirectory;
    protected String outputHouseholdFileName;
    protected String outputPersonFileName;

    protected TazDataIf tazDataManager;
    protected ModelStructure modelStructure;

    protected TableDataSet hhTable;
    protected TableDataSet personTable;

    protected HashSet<Integer> householdTraceSet;

    protected Household[] fullHhArray;
    protected int[] hhIndexArray;
    protected int numberOfHouseholds;

    protected int inputRandomSeed;
    protected int numPeriods;
    protected int firstPeriod;


    protected float sampleRate;
    protected int sampleSeed;
    
    protected int maximumNumberOfHouseholdsPerFile = 0;
    protected int numberOfHouseholdDiskObjectFiles = 0;

    
    public HouseholdDataManager() {
    }




    /**
     * Associate data in hh and person TableDataSets read from synthetic population files with
     * Household objects and Person objects with Households.
     */
    protected abstract void mapTablesToHouseholdObjects();



    /**
     * Returns a String reporting that testRemote() has been called.  Used for debugging purposes, to test
     * RMI call.
     */
    public String testRemote() {
        System.out.println("testRemote() called by remote process.");
        return String.format("testRemote() method in %s called.", this.getClass().getCanonicalName() );
    }


    /**
     * Read the list of household IDs set in the properties file, from the PROPERTIES_HOUSEHOLD_TRACE_LIST
     * property, and set the IDs in the householdTraceSet HashSet.
     * 
     */
    public void setDebugHhIdsFromHashmap () {

        householdTraceSet = new HashSet<Integer>();

        // get the household ids for which debug info is required
        String householdTraceStringList = propertyMap.get( PROPERTIES_HOUSEHOLD_TRACE_LIST );

        if ( householdTraceStringList != null ) {
            StringTokenizer householdTokenizer = new StringTokenizer(householdTraceStringList,",");
            while(householdTokenizer.hasMoreTokens()){
                String listValue = householdTokenizer.nextToken();
                int idValue = Integer.parseInt( listValue.trim() );
                householdTraceSet.add( idValue );
            }
        }
        
        logger.info("Household Trace Set: " + householdTraceSet); 
    }



    /**
     * Read household and person data.  Set the sampleSeed from the properties file in the SeededRandom class, which is used to set the order for the HH
     * index array (to randomize the household array).
     */
    public void setupHouseholdDataManager( ModelStructure modelStructure, TazDataIf tazDataManager, String inputHouseholdFileName, String inputPersonFileName ) {

        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;

        // read synthetic population files
        readHouseholdData(inputHouseholdFileName);

        readPersonData(inputPersonFileName);
    	
        // Set the seed for the JVM default SeededRandom object - should only be used to set the order for the
        // HH index array so that hhs can be processed in an arbitrary order as opposed to the order imposed by
        // the synthetic population generator.
        // The seed was set as a command line argument for the model run, or the default if no argument supplied
        SeededRandom.setSeed( sampleSeed );
        
        // the seed read from the properties file controls seeding the Household object random number generator objects.
        inputRandomSeed = Integer.parseInt( propertyMap.get( HouseholdDataManager.RANDOM_SEED_NAME ) );

        // map synthetic population table data to objects to be used by CT-RAMP
    	mapTablesToHouseholdObjects();
    	hhTable = null;
    	personTable = null;
    	
        numberOfHouseholds = fullHhArray.length;
        logPersonSummary( fullHhArray );            

        setTraceHouseholdSet();

    }
    
    


    /**
     * Read property file values.
     */
    public void setPropertyFileValues ( HashMap<String, String> propertyMap ) {
        
        String propertyValue = "";
        this.propertyMap = propertyMap;

        // save the project specific parameters in class attributes
        this.projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );

        outputHouseholdFileName = propertyMap.get( CtrampApplication.PROPERTIES_OUTPUT_HOUSEHOLD_FILE );
        outputPersonFileName = propertyMap.get( CtrampApplication.PROPERTIES_OUTPUT_PERSON_FILE );

        setDebugHhIdsFromHashmap ();

        propertyValue = propertyMap.get( CtrampApplication.PROPERTIES_SCHEDULING_NUMBER_OF_TIME_PERIODS );
        if ( propertyValue == null )
            numPeriods = 0;
        else
            numPeriods = Integer.parseInt( propertyValue );

        propertyValue = propertyMap.get( CtrampApplication.PROPERTIES_SCHEDULING_FIRST_TIME_PERIOD );
        if ( propertyValue == null )
            firstPeriod = 0;
        else
            firstPeriod = Integer.parseInt( propertyValue );

        propertyValue = propertyMap.get( MAX_HHS_PER_DISK_OBJECT_FILE_KEY );
        if ( propertyValue == null )
            maximumNumberOfHouseholdsPerFile = 0;
        else
            maximumNumberOfHouseholdsPerFile = Integer.parseInt( propertyValue );

        propertyValue = propertyMap.get( NUMBER_OF_DISK_OBJECT_FILES_KEY );
        if ( propertyValue == null )
            numberOfHouseholdDiskObjectFiles = 0;
        else
            numberOfHouseholdDiskObjectFiles = Integer.parseInt( propertyValue );
        
        
        
        propertyValue = propertyMap.get( NUMBER_OF_HH_OBJECTS_HELD_IN_MEMORY_KEY );
        if ( propertyValue != null )
            NUMBER_OF_IN_MEMORY_HHS = Integer.parseInt( propertyValue );
        
        
    }


    /**
     * Sort the households randomly.
     */
    public int[] getRandomOrderHhIndexArray( int numHhs ) {
        
        int[] data = new int[numHhs];
        for ( int i=0; i < numHhs; i++ )
            data[i] = (int)(100000000*SeededRandom.getRandom());

        return IndexSort.indexSort( data );

    }


    /**
     * Sort the households by home TAZ.
     */
    public int[] getHomeTazOrderHhIndexArray( int[] hhSortArray ) {
        return IndexSort.indexSort( hhSortArray );
    }

    /**
     * Reset the random number for the household to the number imposed by the random number count.
     * 
     * @param h  The household
     * @param count  The random number count.
     */

    private void resetRandom(Household h, int count) {
        // get the household's Random
        Random r = h.getHhRandom();

        int seed = inputRandomSeed + h.getHhId();
        r.setSeed( seed );

        // select count Random draws to reset this household's Random to it's state prior to
        // the model run for which model results were stored in HouseholdDataManager.
        for ( int i=0; i < count; i++ )
            r.nextDouble();

        // reset the randomCount for the household's Random
        h.setHhRandomCount(count);
    }


    /**
     * Reset the random number to the one used for usual work and school location choice. Currently 0.
     */
    public void resetUwslRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current random count for the end of the shadow price iteration passed in.
                // this value was set at the end of UsualWorkSchoolLocation model step for the given iter.
                // if < 0, random count should be set to 0.
                int uwslCount = 0;
                
                // draw uwslCount random numbers from the household's Random
                resetRandom(tempHhs[r], uwslCount);
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    /**
     * Reset the random number to the one used for auto ownership.
     */
   public void resetAoRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {

                 int aoCount = tempHhs[r].getUwslRandomCount( );

                // draw stlCount random numbers
                resetRandom( tempHhs[r], aoCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetFpRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int fpCount = tempHhs[r].getAoRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], fpCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetCdapRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int cdapCount = tempHhs[r].getFpRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], cdapCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetImtfRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int imtfCount = tempHhs[r].getCdapRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], imtfCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetImtodRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int imtodCount = tempHhs[r].getImtfRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], imtodCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetImmcRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to mode choice model from the Household object.
                // this value was set at the end of time of day step.
                int immcCount = tempHhs[r].getImtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], immcCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }

    
    public void resetJtfRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int jtfCount = tempHhs[r].getImtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], jtfCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetJtlRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int jtlCount = tempHhs[r].getJtfRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], jtlCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetJtodRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int jtodCount = tempHhs[r].getJtlRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], jtodCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }

    public void resetJmcRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to mode choice model from the Household object.
                // this value was set at the end of time of day step.
                int jmcCount = tempHhs[r].getJtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], jmcCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }

    public void resetInmtfRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int inmtfCount = tempHhs[r].getJtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], inmtfCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetInmtlRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int inmtlCount = tempHhs[r].getInmtfRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], inmtlCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetInmtodRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int inmtodCount = tempHhs[r].getInmtlRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], inmtodCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetInmmcRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to mode choice model from the Household object.
                // this value was set at the end of time of day step.
                int inmmcCount = tempHhs[r].getInmtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], inmmcCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }
    
    
    public void resetAwfRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int awfCount = tempHhs[r].getInmtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], awfCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetAwlRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int awlCount = tempHhs[r].getAwfRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], awlCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetAwtodRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int awtodCount = tempHhs[r].getAwlRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], awtodCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetAwmcRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to mode choice model from the Household object.
                // this value was set at the end of time of day step.
                int awmcCount = tempHhs[r].getAwtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], awmcCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }

    public void resetStfRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int stfCount = tempHhs[r].getAwtodRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], stfCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;

        }

    }


    public void resetStlRandom() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ ) {
                // get the current count prior to stop location model from the Household object.
                // this value was set at the end of stop frequency model step.
                int stlCount = tempHhs[r].getStfRandomCount();

                // draw stlCount random numbers
                resetRandom( tempHhs[r], stlCount );
            }
            setHhArray( tempHhs, startRange );

            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }
        
    }


    // this is called at the end of UsualWorkSchoolLocation model step.
    public void setUwslRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setUwslRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Auto Ownership model step.
    public void setAoRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setAoRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Auto Ownership model step.
    public void setFpRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setFpRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Coordinated Daily Activity Pattern model step.
    public void setCdapRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setCdapRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Individual Mandatory Tour Frequency model step.
    public void setImtfRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setImtfRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Individual Mandatory Tour Departure and Duration model step.
    public void setImtodRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setImtodRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Individual Mandatory Tour mode choice model step.
    public void setImmcRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setImmcRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }
    
    // this is called at the end of At-work Subtour Frequency model step.
    public void setAwfRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setAwfRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of At-work Subtour Location Choice model step.
    public void setAwlRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setAwlRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of At-work Subtour Departure time, duration and mode choice model step.
    public void setAwtodRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setAwtodRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of At-work Subtour  mode choice model step.
    public void setAwmcRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setAwmcRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Joint Tour Frequency model step.
    public void setJtfRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setJtfRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }


    // this is called at the end of Joint Tour Destination Choice model step.
    public void setJtlRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setJtlRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Joint Tour departure and duration Choice model step.
    public void setJtodRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setJtodRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Joint Tour departure and duration Choice model step.
    public void setJmcRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setJmcRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }
    // this is called at the end of Individual non-mandatory Tour frequency Choice model step.
    public void setInmtfRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setInmtfRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Individual non-mandatory Tour destination choice Choice model step.
    public void setInmtlRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setInmtlRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Individual non-mandatory Tour departure and duration choice Choice model step.
    public void setInmtodRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setInmtodRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Individual non-mandatory Tour mode Choice model step.
    public void setInmmcRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setInmmcRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Stop Frequency Choice model step.
    public void setStfRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setStfRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }

    // this is called at the end of Stop Location Choice model step.
    public void setStlRandomCount() {

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setStlRandomCount( tempHhs[r].getHhRandomCount() );
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

    }



    /**
     *  set the hh id for which debugging info from choice models applied to this household will be logged if debug logging.
     */
    public void setDebugHouseholdId( int debugHhId, boolean value ) {
        int index = hhIndexArray[debugHhId];
        Household tempHh = getHhArrayElement( index );
        tempHh.setDebugChoiceModels(value);
        setHhArrayElement( tempHh, index );
    }

    
    /**
     * Sets the HashSet used to trace households for debug purposes and sets the
     * debug switch for each of the listed households. Also sets
     */
    public void setTraceHouseholdSet() {
        
        // loop through the households in the set and set the trace switches
        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            for ( int r=0; r < tempHhs.length; r++ )
                tempHhs[r].setDebugChoiceModels(false);
            setHhArray( tempHhs, startRange );
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

        
        for( int id : householdTraceSet ) {
            int index = hhIndexArray[id];
            Household tempHh = getHhArrayElement( index );
            tempHh.setDebugChoiceModels(true);
            setHhArrayElement( tempHh, index );
        }
        
    }
    


    /**
     * Sets the sample rate used to run the model for a portion of the households.
     * @param sampleRate, proportion of total households for which to run the model [0.0, 1.0].
     */
    public void setHouseholdSampleRate( float sampleRate, int sampleSeed ) {
        this.sampleRate = sampleRate;
        this.sampleSeed = sampleSeed;
    }
    


    public void setHhArray(Household[] hhArray) {
        fullHhArray = hhArray;
    }
    
    
    public void setHhArray( Household[] tempHhs, int startIndex ) {
        //long startTime = System.currentTimeMillis();
        //logger.info( String.format( "start setHhArray for startIndex=%d, startTime=%d.", startIndex, startTime ) );

        if ( hhDiskObjectArrayList != null ) {
            putHhArrayIntoDiskObject( tempHhs, startIndex );
        }
        else {
            for (int i=0; i < tempHhs.length; i++) {
                fullHhArray[startIndex + i] = tempHhs[i]; 
            }
        }
        
        //long endTime = System.currentTimeMillis();
        //logger.info( String.format( "end setHhArray for startIndex=%d, endTime=%d, elapsed=%d millisecs.", startIndex, endTime, (endTime - startTime) ) );
    }

    public void setHhArrayElement( Household tempHh, int index ) {
        if ( hhDiskObjectArrayList != null ) {
            putHhArrayElementIntoDiskObject( tempHh, index );
        }
        else {
            fullHhArray[index] = tempHh;
        }        
    }
    
    
    /**
     * return the array of Household objects holding the synthetic population and choice model outcomes.
     * @return hhs
     */
    public Household[] getHhArray() {
        return fullHhArray;
    }
    

    public Household[] getHhArray(int first, int last) {
        //long startTime = System.currentTimeMillis();
        //logger.info( String.format( "start getHhArray for first=%d, last=%d, startTime=%d.", first, last, startTime ) );
        
        Household[] tempHhs = null;
        if ( hhDiskObjectArrayList != null ) {
            tempHhs = getHhArrayFromDiskObject( first, last );
        }
        else {
            tempHhs = new Household[last-first+1];
            for (int i=0; i < tempHhs.length; i++) {
                tempHhs[i] = fullHhArray[first + i]; 
            }
        }
        
        //long endTime = System.currentTimeMillis();
        //logger.info( String.format( "end getHhArray for first=%d, last=%d, endTime=%d, elapsed=%d millisecs.", first, last, endTime, (endTime - startTime) ) );
        
        return tempHhs;
    }

    
    public Household getHhArrayElement( int index ) {
        if ( hhDiskObjectArrayList != null ) {
            return getHhArrayElementFromDiskObject( index );
        }
        else {
            return fullHhArray[index];
        }        
    }
    
    
    public int getArrayIndex( int hhId ){
        int i = hhIndexArray[hhId];
        return i;
    }
    
    /**
     * return the number of household objects read from the synthetic population.
     * @return
     */
    public int getNumHouseholds() {
        return numberOfHouseholds;
    }
    
    

    /**
     * set walk segment (0-none, 1-short, 2-long walk to transit access) for the origin for this tour
     */
    public short getInitialOriginWalkSegment (short taz, double randomNumber) {
        double[] proportions = tazDataManager.getZonalWalkPercentagesForTaz( taz );
        return (short)ChoiceModelApplication.getMonteCarloSelection(proportions, randomNumber);
    }




    private void readHouseholdData( String inputHouseholdFileName ) {
        
        // construct input household file name from properties file values
        String fileName = projectDirectory + "/" + inputHouseholdFileName;

        try{
            logger.info( "reading popsyn household data file." );
            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            reader.setDelimSet( "," + reader.getDelimSet() );
            hhTable = reader.readFile(new File( fileName ));
        }
        catch(Exception e){
            logger.fatal( String.format( "Exception occurred reading synthetic household data file: %s into TableDataSet object.", fileName ) );
            throw new RuntimeException(e);
        }
        
    }

    
    private void readPersonData( String inputPersonFileName ) {
        
        // construct input person file name from properties file values
        String fileName = projectDirectory + "/" + inputPersonFileName;

        try{
            logger.info( "reading popsyn person data file." );
            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            reader.setDelimSet( "," + reader.getDelimSet() );
            personTable = reader.readFile(new File( fileName ));
        }
        catch(Exception e){
            logger.fatal( String.format( "Exception occurred reading synthetic person data file: %s into TableDataSet object.", fileName ) );
            throw new RuntimeException(e);
        }
        
    }


    
    
    public void logPersonSummary( Household[] hhs ) {

        HashMap<String, HashMap<String, int[]>> summaryResults;

        summaryResults = new HashMap<String, HashMap<String,int[]>>();

        for(int i=0; i < hhs.length; ++i){

            Household household = hhs[i];
            
            Person[] personArray = household.getPersons();
            for (int j = 1; j < personArray.length; ++j) {
                Person person = personArray[j];
                String personType = person.getPersonType();

                String employmentStatus = person.getPersonEmploymentCategory();
                String studentStatus = person.getPersonStudentCategory();
                int age = person.getAge();
                int ageCategory;
                if (age <= 5) {
                    ageCategory = 0;
                } else if (age <= 15) {
                    ageCategory = 1;
                } else if (age <= 18) {
                    ageCategory = 2;
                } else if (age <= 24) {
                    ageCategory = 3;
                }   else if (age <= 44) {
                    ageCategory = 4;
                } else if (age <= 64) {
                    ageCategory = 5;
                } else {
                    ageCategory = 6;
                }

                if (summaryResults.containsKey(personType)) {
                    //have person type
                    if (summaryResults.get(personType).containsKey(employmentStatus)) {
                        //have employment category
                        summaryResults.get(personType).get(employmentStatus)[ageCategory]+=1;
                    } else {
                        //don't have employment category
                        summaryResults.get(personType).put(employmentStatus, new int[7]);
                        summaryResults.get(personType).get(employmentStatus)[ageCategory]+=1;
                    }
                    if (summaryResults.get(personType).containsKey(studentStatus)) {
                        //have student category
                        summaryResults.get(personType).get(studentStatus)[ageCategory]+=1;
                    } else {
                        //don't have student category
                        summaryResults.get(personType).put(studentStatus, new int[7]);
                        summaryResults.get(personType).get(studentStatus)[ageCategory]+=1;
                    }
                } else {
                    //don't have person type
                    summaryResults.put(personType, new HashMap<String,int[]>());
                    summaryResults.get(personType).put(studentStatus, new int[7]);
                    summaryResults.get(personType).get(studentStatus)[ageCategory]+=1;
                    summaryResults.get(personType).put(employmentStatus, new int[7]);
                    summaryResults.get(personType).get(employmentStatus)[ageCategory]+=1;
                }
            }
        }
        String headerRow = String.format("%5s\t", "Age\t");
        for (String empCategory: Person.employmentCategoryNameArray) {
            headerRow += String.format("%16s\t", empCategory );
        }
        for (String stuCategory: Person.studentCategoryNameArray) {
            headerRow += String.format("%16s\t", stuCategory );
        }
        String[] ageCategories = {"0-5","6-15","16-18","19-24","25-44","45-64","65+"};

        for (String personType: summaryResults.keySet()) {

            logger.info("Summary for person type: " + personType);

            logger.info(headerRow);
            String row = "";

            HashMap<String, int[]> personTypeSummary = summaryResults.get(personType);

            for (int j = 0; j<ageCategories.length;++j) {
                row = String.format("%5s\t", ageCategories[j]);
                for (String empCategory: Person.employmentCategoryNameArray) {
                    if (personTypeSummary.containsKey(empCategory)) {
                        row += String.format("%16d\t", personTypeSummary.get(empCategory)[j]);
                    } else row += String.format("%16d\t", 0);
                }
                for (String stuCategory: Person.studentCategoryNameArray) {
                    if (personTypeSummary.containsKey(stuCategory)) {
                        row += String.format("%16d\t", personTypeSummary.get(stuCategory)[j]);
                    } else row += String.format("%16d\t", 0);
                }
                logger.info(row);
            }

        }

    }



    
    public int[][][] getTourPurposePersonsByHomeZone( String[] purposeList ) {

        int numZones = tazDataManager.getNumberOfZones();
        int numWalkSubzones = tazDataManager.getNumberOfSubZones();
        
        int[][][] personsWithMandatoryPurpose = new int[purposeList.length][numZones+1][numWalkSubzones];

        
        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            // hhs is dimesioned to number of households + 1.
            int count=0;
            for ( int r=0; r < tempHhs.length; r++ ) {

                Person[] persons = tempHhs[r].getPersons();

                int homeZone = tempHhs[r].getHhTaz();
                int homeSubZone = tempHhs[r].getHhWalkSubzone();
                
                for ( int p=1; p < persons.length; p++) {

                    Person person = persons[p];
                    
                    int purposeIndex = -1;
                    try {

                        if ( person.getPersonIsWorker() == 1 ) {
                            
                            purposeIndex = person.getWorkLocationPurposeIndex();
                            personsWithMandatoryPurpose[purposeIndex][homeZone][homeSubZone] ++;

                        }

                        if ( person.getPersonIsPreschoolChild() == 1 || person.getPersonIsStudentDriving() == 1 || person.getPersonIsStudentNonDriving() == 1 ) {
                            
                            purposeIndex = person.getSchoolLocationPurposeIndex();
                            personsWithMandatoryPurpose[purposeIndex][homeZone][homeSubZone] ++;

                        }
                        else if ( person.getPersonIsUniversityStudent() == 1 ) {
                            
                            purposeIndex = person.getUniversityLocationPurposeIndex();
                            personsWithMandatoryPurpose[purposeIndex][homeZone][homeSubZone] ++;

                        }

                        count++;
                        
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( String.format("exception caught summing workers/students by origin zone for household table record r=%d, startRange=%d, endRange=%d, count=%d.", r, startRange, endRange, count ) );
                        throw e;
                    }

                }
                
            } // r (households)

            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }
        
        return personsWithMandatoryPurpose;

    }


   

    
    public int[][] getIndividualNonMandatoryToursByHomeZoneSubZone( String purposeString ) {

        // dimension the array
        int numZones = tazDataManager.getNumberOfZones();
        int numWalkSubzones = tazDataManager.getNumberOfSubZones();
        
        int[][] individualNonMandatoryTours = new int[numZones+1][numWalkSubzones];

        // hhs is dimesioned to number of households + 1.
        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            // hhs is dimesioned to number of households + 1.
            int count = 0;
            for ( int r=0; r < tempHhs.length; r++ ) {


                Person[] persons = tempHhs[r].getPersons();
        
                for ( int p=1; p < persons.length; p++) {
        
                    Person person = persons[p];
                    
                    ArrayList<Tour> it = person.getListOfIndividualNonMandatoryTours();
        
                    try {
        
                        if ( it.size() == 0 )
                            continue;
        
                        for ( Tour tour : it ) {
                            // increment the segment count if it's the right purpose
                            String tourPurpose = tour.getTourPurpose();
                            if ( purposeString.startsWith( tourPurpose ) ) {
                                int homeZone = tempHhs[r].getHhTaz();
                                int homeSubZone = tempHhs[r].getHhWalkSubzone();
                                individualNonMandatoryTours[homeZone][homeSubZone] ++;
                                count++;
                            }
                        }
        
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( String.format("exception caught counting number of individualNonMandatory tours for purpose: %s, for household table record r=%d, personNum=%d, startRange=%d, endRange=%d, count=%d.", purposeString, r, person.getPersonNum(), startRange, endRange, count ) );
                        throw e;
                    }
        
                }

            } // r (households)

            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }
    
        return individualNonMandatoryTours;
        
    }



    public double[][][] getMandatoryToursByDestZoneSubZone() {

        // dimension the array
        int numZones = tazDataManager.getNumberOfZones();
        int numWalkSubzones = tazDataManager.getNumberOfSubZones();

        // get correspondence between mandatory purpose names and their array indices
        String[] mandatoryPurposes = modelStructure.getDcModelPurposeList( ModelStructure.MANDATORY_CATEGORY );
        HashMap<String,Integer> tourPurposeIndexMap = new HashMap<String,Integer>();
        for ( int p=0; p < mandatoryPurposes.length; p++ )
            tourPurposeIndexMap.put( mandatoryPurposes[p], p );
                
        double[][][] mandatoryTours = new double[mandatoryPurposes.length][numZones+1][numWalkSubzones];

        

        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            // hhs is dimesioned to number of households + 1.
            int count = 0;
            for ( int r=0; r < tempHhs.length; r++ ) {

                Person[] persons = tempHhs[r].getPersons();
    
                for ( int p=1; p < persons.length; p++) {
    
                    Person person = persons[p];
                    
                    String purposeName = "";
                    int purposeIndex = -1;
                    int destZone = -1;
                    int destSubZone = -1;
                    try {
    
                        if ( person.getPersonIsWorker() == 1 && person.getPersonWorkLocationZone() > 0 ) {
                            
                            purposeIndex = person.getWorkLocationPurposeIndex();
                            destZone = person.getPersonWorkLocationZone();
                            destSubZone = person.getPersonWorkLocationSubZone();
                            mandatoryTours[purposeIndex][destZone][destSubZone]++;
    
                        }
    
                        if ( person.getPersonIsPreschoolChild() == 1 || person.getPersonIsStudentDriving() == 1 || person.getPersonIsStudentNonDriving() == 1 && person.getPersonSchoolLocationZone() > 0 ) {
                            
                            purposeIndex = person.getSchoolLocationPurposeIndex();
                            destZone = person.getPersonSchoolLocationZone();
                            destSubZone = person.getPersonSchoolLocationSubZone();
                            mandatoryTours[purposeIndex][destZone][destSubZone]++;
    
                        }
                        else if ( person.getPersonIsUniversityStudent() == 1 && person.getPersonSchoolLocationZone() > 0 ) {
                            
                            purposeIndex = person.getUniversityLocationPurposeIndex();
                            destZone = person.getPersonSchoolLocationZone();
                            destSubZone = person.getPersonSchoolLocationSubZone();
                            mandatoryTours[purposeIndex][destZone][destSubZone]++;
    
                        }
    
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( String.format("exception caught counting number of mandatory tour destinations for purpose: %s, for household table record r=%d, personNum=%d.", purposeName, r, person.getPersonNum() ) );
                        logger.error ( String.format("     r = %d.", r ) );
                        logger.error ( String.format("     household id = %d.", tempHhs[r] ) );
                        logger.error ( String.format("     personNum = %d.", person.getPersonNum() ) );
                        logger.error ( String.format("     purpose name = %s, purposeIndex = %d.", purposeName, purposeIndex ) );
                        logger.error ( String.format("     destZone = %d, destSubZone = %d.", destZone, destSubZone ) );
                        logger.error ( String.format("     startRange = %d, endRange = %d, count = %d.", startRange, endRange, count ) );
                    }
    
                }
            
            } // r (households)
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

        return mandatoryTours;
        
    }



    public int[][] getJointToursByHomeZoneSubZone( String purposeString ) {

        // dimension the array
        int numZones = tazDataManager.getNumberOfZones();
        int numWalkSubzones = tazDataManager.getNumberOfSubZones();

        int[][] jointTours = new int[numZones+1][numWalkSubzones];

        // hhs is dimesioned to number of households + 1.
        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            // hhs is dimesioned to number of households + 1.
            int count = 0;
            for ( int r=0; r < tempHhs.length; r++ ) {

                try {
    
                    Tour[] jt = tempHhs[r].getJointTourArray();
    
                    if ( jt == null )
                        continue;
    
                    for ( int i=0; i < jt.length; i++ ) {
                        // increment the segment count if it's the right purpose
                        if ( jt[i].getTourPurpose().equalsIgnoreCase( purposeString )) {
                            int homeZone = tempHhs[r].getHhTaz();
                            int homeSubZone = tempHhs[r].getHhWalkSubzone();
                            jointTours[homeZone][homeSubZone] ++;
                            count++;
                        }
                    }
    
                }
                catch ( RuntimeException e ) {
                    logger.error ( String.format("exception caught counting number of joint tours for purpose: %s, for household table record r=%d, startRange=%d, endRange=%d, count=%d.", purposeString, r, startRange, endRange, count ) );
                    throw e;
                }

            } // r (households)
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

        return jointTours;
    }


    public int[][] getAtWorkSubtoursByWorkZoneSubZone( String purposeString ) {

        // dimension the array
        int numZones = tazDataManager.getNumberOfZones();
        int numWalkSubzones = tazDataManager.getNumberOfSubZones();
        
        int[][] subtours = new int[numZones+1][numWalkSubzones];

        // hhs is dimesioned to number of households + 1.
        int startRange = 0;
        int endRange = 0;
        while ( endRange < getNumHouseholds() ) {
            
            endRange = startRange + NUMBER_OF_IN_MEMORY_HHS;
            if ( endRange + NUMBER_OF_IN_MEMORY_HHS > getNumHouseholds() )
                endRange = getNumHouseholds();
            
            Household[] tempHhs = getHhArray( startRange, endRange-1 );
            // hhs is dimesioned to number of households + 1.
            int count = 0;
            for ( int r=0; r < tempHhs.length; r++ ) {


                Person[] persons = tempHhs[r].getPersons();
    
                for ( int p=1; p < persons.length; p++) {
    
                    Person person = persons[p];
                    
                    ArrayList<Tour> subtourList = person.getListOfAtWorkSubtours();
    
                    try {
    
                        if ( subtourList.size() == 0 )
                            continue;
    
                        for ( Tour tour : subtourList ) {
                            // increment the segment count if it's the right purpose
                            String tourPurpose = tour.getTourPurpose();
                            if ( tourPurpose.startsWith( purposeString ) ) {
                                int workZone = tour.getTourOrigTaz();
                                int workSubZone = tour.getTourOrigWalkSubzone();
                                subtours[workZone][workSubZone] ++;
                                count++;
                            }
                        }
    
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( String.format("exception caught counting number of at-work subtours for purpose: %s, for household table record r=%d, personNum=%d, startRange=%d, endRange=%d, count=%d.", purposeString, r, person.getPersonNum(), startRange, endRange, count ) );
                        throw e;
                    }
    
                }

            } // r (households)
            
            startRange += NUMBER_OF_IN_MEMORY_HHS;
            
        }

        return subtours;
    }

    
    /*
    public void createSerializedHhArrayInFileFromObject( String serializedObjectFileName, String serializedObjectKey ){

        int start = 1;
        int end = maximumNumberOfHouseholdsPerFile;
        if ( end >= hhs.length )
            end = hhs.length - 1;

        for ( int i=1; i <= numberOfHouseholdDiskObjectFiles; i++ ) {

            String filename = serializedObjectFileName + "_" + i;
            try{
                DataFile dataFile = new DataFile( filename, 1 );
                DataWriter dw = new DataWriter( serializedObjectKey );
                dw.writeObject( getHhArray(start, end) );
                dataFile.insertRecord( dw );
                dataFile.close();
            }
            catch(NotSerializableException e) {
                logger.error( String.format("NotSerializableException for %s.  Trying to create serialized object with key=%s, in filename=%s.", hhs.getClass().getName(), serializedObjectKey, serializedObjectFileName ), e );
                throw new RuntimeException();
            }
            catch(IOException e) {
                logger.error( String.format("IOException trying to write disk object file=%s, with key=%s for writing.", serializedObjectFileName, serializedObjectKey ), e );
                throw new RuntimeException();
            }

            start += maximumNumberOfHouseholdsPerFile;
            end += maximumNumberOfHouseholdsPerFile;
            if ( end >= hhs.length )
                end = hhs.length - 1;
            
        }
        
    }


    public Household[] createHhArrayFromSerializedObjectInFile( String serializedObjectFileName, String serializedObjectKey ){

        Household[] hhs;
        

        // read the highest numbered file first, which is the "partial" file.  The number of remaining
        // files and number of hhs per file will then allow the full hhs array to be dimensioned.
        String filename = serializedObjectFileName + "_" + numberOfHouseholdDiskObjectFiles;
        try{
            DataFile dataFile = new DataFile( filename, "r" );
            DataReader dr = dataFile.readRecord( serializedObjectKey );
            Household[] tempHhs = (Household[])dr.readObject();
            dataFile.close();
            
            int totalNumberOfHhs = tempHhs.length + (numberOfHouseholdDiskObjectFiles - 1)*maximumNumberOfHouseholdsPerFile;
            hhs = new Household[totalNumberOfHhs];
            int start = (numberOfHouseholdDiskObjectFiles - 1)*maximumNumberOfHouseholdsPerFile;
            setHhArray( tempHhs, start );
        }
        catch(IOException e) {
            logger.error( String.format("IOException trying to read hhArray disk object file=%s, with key=%s.", serializedObjectFileName, serializedObjectKey ), e );
            throw new RuntimeException();
        }
        catch(ClassNotFoundException e) {
            logger.error( String.format("could not instantiate %s object, with key=%s from filename=%s.", Household.class.getName(), serializedObjectFileName, serializedObjectKey ), e );
            throw new RuntimeException();
        }

        // now read the remining files and store each one in the hhs array.
        int start = 0;
        for ( int i=1; i < numberOfHouseholdDiskObjectFiles; i++ ) {

            filename = serializedObjectFileName + "_" + i;
            try{
                DataFile dataFile = new DataFile( filename, "r" );
                DataReader dr = dataFile.readRecord( serializedObjectKey );
                Household[] tempHhs = (Household[])dr.readObject();
                setHhArray( tempHhs, start );
                dataFile.close();
            }
            catch(IOException e) {
                logger.error( String.format("IOException trying to read hhArray disk object file=%s, with key=%s.", serializedObjectFileName, serializedObjectKey ), e );
                throw new RuntimeException();
            }
            catch(ClassNotFoundException e) {
                logger.error( String.format("could not instantiate %s object, with key=%s from filename=%s.", hhs.getClass().getName(), serializedObjectFileName, serializedObjectKey ), e );
                throw new RuntimeException();
            }
            
            start += maximumNumberOfHouseholdsPerFile;

        }
        
        return hhs;

    }
    */
    
    
    public Household[] getHhArrayFromDiskObject( int first, int last ) {
        
        Household[] tempHhs = new Household[last-first+1];
        for ( int i=first; i <= last; i++ ){
            int fileIndex = i / MAX_HHS_PER_FILE;
            int recordIndex = i - fileIndex*MAX_HHS_PER_FILE;
            DiskObjectArray doa = hhDiskObjectArrayList.get( fileIndex );
            tempHhs[i - first] = (Household)doa.get( recordIndex ); 
        }
        
        return tempHhs;
    }

    
    public Household getHhArrayElementFromDiskObject( int index ) {
        int fileIndex = index / MAX_HHS_PER_FILE;
        int recordIndex = index - fileIndex*MAX_HHS_PER_FILE;
        DiskObjectArray doa = hhDiskObjectArrayList.get( fileIndex );
        Household tempHh = (Household)doa.get( recordIndex ); 
        return tempHh;
    }

    
    public void putHhArrayIntoDiskObject( Household[] tempHhs, int first ) {

        for ( int i=first; i < first + tempHhs.length; i++ ){
            int fileIndex = i / MAX_HHS_PER_FILE;
            int recordIndex = i - fileIndex*MAX_HHS_PER_FILE;
            DiskObjectArray doa = hhDiskObjectArrayList.get( fileIndex );
            doa.add( recordIndex, tempHhs[i - first] ); 
        }
        
    }

    
    public void putHhArrayElementIntoDiskObject( Household tempHh, int index ) {
        int fileIndex = index / MAX_HHS_PER_FILE;
        int recordIndex = index - fileIndex*MAX_HHS_PER_FILE;
        DiskObjectArray doa = hhDiskObjectArrayList.get( fileIndex );
        doa.add( recordIndex, tempHh ); 
    }

    
    
    
    
    
    
    /*
    public long getBytesUsedByHouseholdArray() {
        
        long numBytes = 0;
        for ( int i=0; i < hhs.length; i++ ) {
            Household hh = hhs[i];
            long size = ObjectUtil.sizeOf( hh );
            numBytes += size;
        }
        
        return numBytes;
    }
    */
    
}