package com.pb.models.ctramp.jppf;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import org.apache.log4j.Logger;
import org.jppf.client.JPPFClient;
import org.jppf.client.JPPFJob;
import org.jppf.server.protocol.JPPFTask;
import org.jppf.task.storage.DataProvider;
import org.jppf.task.storage.MemoryMapDataProvider;

import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;


public class HouseholdChoiceModelRunner {
	
    private Logger logger = Logger.getLogger(HouseholdChoiceModelRunner.class);

    private static int PACKET_SIZE = 0;

    private static String PROPERTIES_NUM_INITIALIZATION_PACKETS = "number.initialization.packets";
    private static String PROPERTIES_INITIALIZATION_PACKET_SIZE = "initialization.packet.size";
    private static int NUM_INITIALIZATION_PACKETS = 0;
    private static int INITIALIZATION_PACKET_SIZE = 0;

    private int ONE_HH_ID = -1;
    
    private static final String HOUSEHOLD_CHOICE_PACKET_SIZE = "distributed.task.packet.size";
    private static final String RUN_THIS_HOUSEHOLD_ONLY = "run.this.household.only";    
    
    private HashMap<String, String> propertyMap;
    private String restartModelString;
    private MatrixDataServerIf ms;
    private HouseholdDataManagerIf hhDataManager;
    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;
    private CtrampDmuFactoryIf dmuFactory;    
    
    private JPPFClient jppfClient = new JPPFClient();
    
    
    // The number of initialization packets are the number of "small" packets submited at the beginning of a 
    // distributed task to minimize synchronization issues that significantly slow down model object setup.
    // It is assumed that after theses small packets have run, all the model objects will have been setup,
    // and the task objects can process much bigger chuncks of households.


    public HouseholdChoiceModelRunner( HashMap<String, String> propertyMap, JPPFClient jppfClient, String restartModelString, HouseholdDataManagerIf hhDataManager, MatrixDataServerIf ms, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ) {
        setupHouseholdChoiceModelRunner ( propertyMap, jppfClient, restartModelString, hhDataManager, ms, modelStructure, tazDataManager, dmuFactory );
    }


    private void setupHouseholdChoiceModelRunner ( HashMap<String, String> propertyMap, JPPFClient jppfClient, String restartModelString, HouseholdDataManagerIf hhDataManager, MatrixDataServerIf ms, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ) {
        
        this.propertyMap = propertyMap;
        this.restartModelString = restartModelString;
        this.hhDataManager = hhDataManager;
        this.ms = ms;
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;
        this.dmuFactory = dmuFactory;
        this.jppfClient = jppfClient;


        String oneHhString = propertyMap.get( RUN_THIS_HOUSEHOLD_ONLY );
        if ( oneHhString != null )
            ONE_HH_ID = Integer.parseInt( oneHhString );

        
        String propertyValue = propertyMap.get( HOUSEHOLD_CHOICE_PACKET_SIZE );
        if ( propertyValue == null )
            PACKET_SIZE = 0;
        else
            PACKET_SIZE = Integer.parseInt( propertyValue );
            
            
        propertyValue = propertyMap.get( PROPERTIES_NUM_INITIALIZATION_PACKETS );
        if ( propertyValue == null )
            NUM_INITIALIZATION_PACKETS = 0;
        else
            NUM_INITIALIZATION_PACKETS = Integer.parseInt( propertyValue );
            
            
        propertyValue = propertyMap.get( PROPERTIES_INITIALIZATION_PACKET_SIZE );
        if ( propertyValue == null )
            INITIALIZATION_PACKET_SIZE = 0;
        else
            INITIALIZATION_PACKET_SIZE = Integer.parseInt( propertyValue );
            
            
    }
    

    
    /**
     * 
     * JPPF framework based method
     */
    public void runHouseholdChoiceModels () {

        long initTime = System.currentTimeMillis();

        submitTasks();        
        
        jppfClient.close();

        logger.info( String.format( "household model runner finished %d households in %d minutes.", hhDataManager.getNumHouseholds(), ((System.currentTimeMillis()-initTime)/1000)/60 ) );
        
    }

    
    /**
     * @param client is a JPPFClient object which is used to establish a connection to a computing node, submit tasks, and receive results.
     */
    private void submitTasks() {

        // if PACKET_SIZE was not specified, create a single task to use for all households
        if ( PACKET_SIZE == 0 )
            PACKET_SIZE = hhDataManager.getNumHouseholds();


        // Create a setup task object and submit it to the computing node.
        // This setup task creates the HouseholdChoiceModelManager and causes it to create the necessary numuber
        // of HouseholdChoiceModels objects which will operate in parallel on the computing node.
        try {
            
            JPPFJob job = new JPPFJob();

            DataProvider dataProvider = new MemoryMapDataProvider();
            dataProvider.setValue("propertyMap", propertyMap);
            dataProvider.setValue("ms", ms);
            dataProvider.setValue("modelStructure", modelStructure);
            dataProvider.setValue("tazDataManager", tazDataManager);
            dataProvider.setValue("householdDataManager", hhDataManager);
            dataProvider.setValue("dmuFactory", dmuFactory);
            dataProvider.setValue("restartModelString", restartModelString);
            
            job.setDataProvider(dataProvider);
            
            ArrayList<int[]> startEndTaskIndicesList = getTaskHouseholdRanges( hhDataManager.getNumHouseholds() );
            
            int startIndex = 0;
            int endIndex = 0;
            int taskIndex = 1;
            for ( int[] startEndIndices : startEndTaskIndicesList ) {
                startIndex = startEndIndices[0];
                endIndex = startEndIndices[1];

                HouseholdChoiceModelsTaskJppf task = new HouseholdChoiceModelsTaskJppf( taskIndex, startIndex, endIndex );
                job.addTask ( task );
                taskIndex++;
            }

            

            List<JPPFTask> results = jppfClient.submit(job);
            for (JPPFTask task : results) {
                if (task.getException() != null) throw task.getException();

                try {                       
                    logger.info( String.format("HH TASK: %s returned: %s.", task.getId(), (String)task.getResult() ) );
                }
                catch (Exception e) {
                    logger.error( "Exception returned by computing node caught in HouseholdChoiceModelsTaskJppf.", e );
                    throw new RuntimeException();
                }

            }

        }
        catch (Exception e) {
            logger.error( "Exception caught creating/submitting/receiving HouseholdChoiceModelsTaskJppf.", e );
            throw new RuntimeException();
        }

    }
    
    
    
    private ArrayList<int[]> getTaskHouseholdRanges( int numberOfHouseholds ) {
        
        ArrayList<int[]> startEndIndexList = new ArrayList<int[]>(); 

        if ( ONE_HH_ID < 0 ) {
            
            int numInitializationHouseholds = NUM_INITIALIZATION_PACKETS*INITIALIZATION_PACKET_SIZE;

            
            int startIndex = 0;
            int endIndex = 0;
            if ( numInitializationHouseholds < numberOfHouseholds ) {
                
                while ( endIndex < numInitializationHouseholds ) {
                    endIndex = startIndex + INITIALIZATION_PACKET_SIZE - 1;
                
                    int[] startEndIndices = new int[2];
                    startEndIndices[0] = startIndex; 
                    startEndIndices[1] = endIndex;
                    startEndIndexList.add( startEndIndices );
                    
                    startIndex += INITIALIZATION_PACKET_SIZE;
                }

            }
            
            
            while ( endIndex < numberOfHouseholds - 1 ) {
                endIndex = startIndex + PACKET_SIZE - 1;
                if ( endIndex + PACKET_SIZE > numberOfHouseholds )
                    endIndex = numberOfHouseholds - 1;
            
                int[] startEndIndices = new int[2];
                startEndIndices[0] = startIndex; 
                startEndIndices[1] = endIndex;
                startEndIndexList.add( startEndIndices );
                
                startIndex += PACKET_SIZE;
            }

            
            return startEndIndexList;

        }
        else {

            // create a single task packet high one household id
            int[] startEndIndices = new int[2];
            int index = hhDataManager.getArrayIndex( ONE_HH_ID );
            startEndIndices[0] = index; 
            startEndIndices[1] = index;
            startEndIndexList.add( startEndIndices );
            
            return startEndIndexList;

        }
        
        
    }

    
}
