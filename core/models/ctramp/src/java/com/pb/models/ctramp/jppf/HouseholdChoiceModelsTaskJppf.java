package com.pb.models.ctramp.jppf;

import java.net.UnknownHostException;
import java.util.HashMap;

import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;

import org.apache.log4j.Logger;
import org.jppf.server.protocol.JPPFTask;
import org.jppf.task.storage.DataProvider;



public class HouseholdChoiceModelsTaskJppf extends JPPFTask {
	
    private transient HashMap<String, String> propertyMap;
    private transient MatrixDataServerIf ms;
    private transient HouseholdDataManagerIf hhDataManager;
    private transient ModelStructure modelStructure;
    private transient TazDataIf tazDataManager;
    private transient CtrampDmuFactoryIf dmuFactory;
    private transient String restartModelString;
    
    private int startIndex;
    private int endIndex;
    private int taskIndex;
    
    private boolean runWithTiming;

    
    
    public HouseholdChoiceModelsTaskJppf( int taskIndex, int startIndex, int endIndex ) {

        this.startIndex = startIndex;
        this.endIndex = endIndex;
        this.taskIndex = taskIndex;
        
        runWithTiming = true;
    }

    
    public void run() {

        long startTime = System.nanoTime();
        
        Logger logger = Logger.getLogger( "HouseholdChoiceModelsTaskJppf" );

        String threadName = null;
        try {
            threadName = "[" + java.net.InetAddress.getLocalHost().getHostName() + "] " + Thread.currentThread().getName();
        } catch (UnknownHostException e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }
        
        
        
        try {
            DataProvider dataProvider = getDataProvider();

            this.propertyMap = (HashMap<String,String>) dataProvider.getValue("propertyMap");
            this.ms = (MatrixDataServerIf) dataProvider.getValue("ms"); 
            this.modelStructure = (ModelStructure) dataProvider.getValue("modelStructure");
            this.tazDataManager = (TazDataIf) dataProvider.getValue("tazDataManager");
            this.hhDataManager = (HouseholdDataManagerIf) dataProvider.getValue("householdDataManager");
            this.dmuFactory = (CtrampDmuFactoryIf) dataProvider.getValue("dmuFactory");
            this.restartModelString = (String) dataProvider.getValue("restartModelString");

        } catch (Exception e) {
            e.printStackTrace();
        }
        
        // get the factory object used to create and recycle HouseholdChoiceModels objects.
        HouseholdChoiceModelsManager modelManager = HouseholdChoiceModelsManager.getInstance( propertyMap, restartModelString, modelStructure, tazDataManager, dmuFactory );         
        modelManager.managerSetup( ms );
        
        
        
        HouseholdChoiceModels hhModel = modelManager.getHouseholdChoiceModelsObject( taskIndex);
        
        long setup1 = 0;
        long setup2 = 0;
        long setup3 = 0;
        long setup4 = 0;
        long setup5 = 0;

        setup1 = (System.nanoTime() - startTime)/1000000;

        Household[] householdArray = hhDataManager.getHhArray( startIndex, endIndex ); 

        setup2 = (System.nanoTime() - startTime)/1000000;
        
        hhModel.zeroTimes();
        for ( int i=0; i < householdArray.length; i++ ) {
            
            try {
                if ( runWithTiming )
                    hhModel.runModelsWithTiming ( householdArray[i] );
                else
                    hhModel.runModels ( householdArray[i] );                
            }
            catch (RuntimeException e) {
                logger.fatal ( String.format("exception caught in taskIndex=%d hhModel index=%d applying hh model for i=%d, hhId=%d.", taskIndex, hhModel.getModelIndex(), i, householdArray[i].getHhId()) );
                logger.fatal( "Exception caught:", e );
                logger.fatal( "Throwing new RuntimeException() to terminate." );
                throw new RuntimeException();
            }
            
        }
        long[] componentTimes = hhModel.getTimes();
        long[][] partialTimes = hhModel.getPartialTimes();
        
        setup3 = (System.nanoTime() - startTime)/1000000;
        
        hhDataManager.setHhArray( householdArray, startIndex );

        setup4 = (System.nanoTime() - startTime)/1000000;
        
        logger.info( String.format("end of household choice model thread=%s, task[%d], hhModel[%d], startIndex=%d, endIndex=%d", threadName, taskIndex, hhModel.getModelIndex(), startIndex, endIndex) );

        setResult( String.format("taskIndex=%d, hhModelInstance=%d, startIndex=%d, endIndex=%d, thread=%s", taskIndex, hhModel.getModelIndex(), startIndex, endIndex, threadName) );
        
        setup5 = (System.nanoTime() - startTime)/1000000;

        logger.info( "task=" + taskIndex + ", setup=" + setup1 + ", getHhs=" + (setup2 - setup1) + ", processHhs=" + (setup3 - setup2) + ", putHhs=" + (setup4 - setup3) + ", return model=" + (setup5 - setup4) + "." );

        if ( runWithTiming )
            logModelComponentTimes( componentTimes, partialTimes, logger, hhModel.getModelIndex() );
        
        // this has to be the last statement in this method.
        // add this hhModel instance to the static queue shared by other tasks of this type
        modelManager.returnHouseholdChoiceModelsObject( hhModel, startIndex, endIndex );
    
    }
    
    public String getId() {
        return Integer.toString(taskIndex);
    }

    private void logModelComponentTimes( long[] componentTimes, long[][] partialTimes, Logger logger, int modelIndex ) {
     
        String[] label = { "AO", "FP", "CDAP", "IMTF", "IMTOD", "IMMC", "JTF", "JTDC", "JTTOD", "JTMC", "INMTF", "INMTDC", "INMTTOD", "INMTMC", "AWTF", "AWTDC", "AWTTOD", "AWTMC", "STF", "STDTM" };
        
        logger.info( "Household choice model component runtimes (in ms) for task: " + taskIndex + ", modelIndex: " + modelIndex + ", startIndex: " + startIndex + ", endIndex: " + endIndex );
        
        float total = 0;
        for ( int i=0; i < componentTimes.length; i++ ) {
            float time = (componentTimes[i]/1000000);
            logger.info( String.format("%-6d%24s:%10.1f", (i+1), label[i], time ) );
            total += time;
        }       
        logger.info( String.format("%-6s%24s:%10.1f", "Total", "Total all components", total ) );

        String[] rowLabels = { "SLC SOA", "SLC LS", "SLC TOT", "S TOD", "S MC", "S PLC", "TOTAL" };
        String[] colLabels = { "Stops", "No Stops" };
        
        logger.info( "" );
        logger.info( String.format("%-6s%24s:%15s%15s", "", "", colLabels[0], colLabels[1] ) );
        for ( int i=0; i < partialTimes.length; i++ ) {
            float time1 = (partialTimes[i][0]/1000000);
            float time2 = (partialTimes[i][1]/1000000);
            logger.info( String.format("%-6d%24s:%15.1f%15.1f", (i+1), rowLabels[i], time1, time2 ) );
        }       

    }
    
}
