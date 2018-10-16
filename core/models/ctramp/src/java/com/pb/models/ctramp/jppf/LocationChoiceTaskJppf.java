package com.pb.models.ctramp.jppf;


import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.UnknownHostException;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;

import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.jppf.MandatoryDestChoiceModel;

import org.apache.log4j.Logger;
import org.jppf.server.protocol.JPPFTask;
import org.jppf.task.storage.DataProvider;



public class LocationChoiceTaskJppf extends JPPFTask {
	
    private static String VERSION = "Task.1.0.3";
    
    private transient HashMap<String, String> propertyMap;
    private transient MatrixDataServerIf ms;
    private transient HouseholdDataManagerIf hhDataManager;
    private transient ModelStructure modelStructure;
    private transient String tourCategory;
    private transient TazDataIf tazDataManager;
    private transient DestChoiceSize dcSizeObj;
    private transient String dcUecFileName;
    private transient String soaUecFileName;
    private transient int soaSampleSize;
    private transient String modeChoiceUecFileName;
    private transient CtrampDmuFactoryIf dmuFactory;
    private transient String restartModelString;

    private int iteration;
    private int startIndex;
    private int endIndex;
    private int taskIndex = -1;

    
    
    public LocationChoiceTaskJppf( int taskIndex, int startIndex, int endIndex, int iteration ) {
        this.startIndex = startIndex;
        this.endIndex = endIndex;
        this.taskIndex = taskIndex; 
        this.iteration = iteration;
    }

    
    public void run() {

        long startTime = System.currentTimeMillis();

        String threadName = null;
        try {
            threadName = java.net.InetAddress.getLocalHost().getHostName() + " " + Thread.currentThread().getName();
        } catch (UnknownHostException e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }
        
        Logger logger = Logger.getLogger( this.getClass() );

        try {
            DataProvider dataProvider = getDataProvider();

            this.propertyMap = (HashMap<String,String>) dataProvider.getValue("propertyMap");
            this.ms = (MatrixDataServerIf) dataProvider.getValue("ms"); 
            this.modelStructure = (ModelStructure) dataProvider.getValue("modelStructure");
            this.tourCategory = (String) dataProvider.getValue("tourCategory");
            this.tazDataManager = (TazDataIf) dataProvider.getValue("tazDataManager");
            this.hhDataManager = (HouseholdDataManagerIf) dataProvider.getValue("householdDataManager");
            this.dcSizeObj = (DestChoiceSize) dataProvider.getValue("dcSizeObj");
            this.dcUecFileName = (String) dataProvider.getValue("dcUecFileName");
            this.soaUecFileName = (String) dataProvider.getValue("soaUecFileName");
            this.soaSampleSize = (Integer) dataProvider.getValue("soaSampleSize");
            this.modeChoiceUecFileName = (String) dataProvider.getValue("modeChoiceUecFileName");
            this.dmuFactory = (CtrampDmuFactoryIf) dataProvider.getValue("dmuFactory");
            this.restartModelString = (String) dataProvider.getValue("restartModelString");

        } catch (Exception e) {
            e.printStackTrace();
        }
        
        
        HouseholdChoiceModelsManager hhModelManager = HouseholdChoiceModelsManager.getInstance( propertyMap, restartModelString, modelStructure, tazDataManager, dmuFactory );
        hhModelManager.clearHhModels();

        
        
        // get the factory object used to create and recycle dcModel objects.
        DestChoiceModelManager modelManager = DestChoiceModelManager.getInstance();
        
        // one of tasks needs to initialize the manager object by passing attributes needed to create a destination choice model object.
        modelManager.factorySetup( propertyMap, ms, modelStructure, tourCategory, tazDataManager, dcSizeObj, dcUecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory, restartModelString );


        
        // get a dcModel object from manager, which either creates one or returns one for re-use.
        MandatoryDestChoiceModel dcModel = modelManager.getDcModelObject( taskIndex, iteration );

        // reset the dc size object so scaled size values are used for iteration >= 1.
        dcModel.setDcSize ( dcSizeObj, iteration );
        
        long setup1 = 0;
        long setup2 = 0;
        long setup3 = 0;
        long setup4 = 0;
        long lsTime = 0;
        long soaTime = 0;
        long totTime = 0;
        
//        long[][] filterCount = new long[dcModel.getFilterCount().length][dcModel.getFilterCount()[0].length];
//        long[][] expressionCount = new long[dcModel.getExpressionCount().length][dcModel.getExpressionCount()[0].length];
//        long[][] coeffCount = new long[dcModel.getCoeffCount().length][dcModel.getCoeffCount()[0].length];
        long cmUecTime = 0;
        long cmOtherTime = 0;
        long lsTotalTime = 0;
        
        Household[] householdArray = null;
        
        int i = -1;
        try {
        
            setup1 = System.currentTimeMillis() - startTime;

            householdArray = hhDataManager.getHhArray( startIndex, endIndex ); 

            setup2 = System.currentTimeMillis() - startTime;

            for ( i=0; i < householdArray.length; i++ ) {
                dcModel.applyWorkSchoolLocationChoice ( householdArray[i] );
                lsTime += dcModel.getLogsumTime();
                soaTime += dcModel.getSoaTime();
                totTime += dcModel.getTotTime();

                cmUecTime += dcModel.getCmUecTime();
                cmOtherTime += dcModel.getCmOtherTime();
                lsTotalTime += dcModel.getLsTotalTime();
//                long[][] counts = dcModel.getFilterCount();
//                for ( int j=0; j < counts.length; j++ )
//                    for ( int k=0; k < counts[j].length; k++ )
//                        filterCount[j][k] += counts[j][k];
//                counts = dcModel.getExpressionCount();
//                for ( int j=0; j < counts.length; j++ )
//                    for ( int k=0; k < counts[j].length; k++ )
//                        expressionCount[j][k] += counts[j][k];
//                counts = dcModel.getCoeffCount();
//                for ( int j=0; j < counts.length; j++ )
//                    for ( int k=0; k < counts[j].length; k++ )
//                        coeffCount[j][k] += counts[j][k];
            }
        
            setup3 = System.currentTimeMillis() - startTime;

            hhDataManager.setHhArray( householdArray, startIndex );
            
            setup4 = System.currentTimeMillis() - startTime;

        }
        catch ( Exception e ) {
            if ( i >= 0 && i < householdArray.length )
                System.out.println ( String.format("exception caught in taskIndex=%d applying dc model for i=%d, hhId=%d, startIndex=%d.", taskIndex, i, householdArray[i].getHhId(), startIndex) );
            else
                System.out.println ( String.format("exception caught in taskIndex=%d applying dc model for i=%d, startIndex=%d.", taskIndex, i, startIndex) );
            System.out.println ( "Exception caught:" );
            e.printStackTrace();
            System.out.println ( "Throwing new RuntimeException() to terminate." );
            throw new RuntimeException( e );
        }

        
        long total = (System.currentTimeMillis() - startTime) / 1000;
        logger.info( "task=" + taskIndex + " finished, thread=" + threadName + ", " + startTime + ", " + System.currentTimeMillis() + "." );
        logger.info( "task=" + taskIndex + ", setup=" + setup1 + ", getHhs=" + (setup2 - setup1) + ", processHhs=" + (setup3 - setup2)  + ", putHhs=" + (setup4 - setup3) + ", total=" + total + "." );
        logger.info( "task=" + taskIndex + ", lsTime=" + (lsTime/1000000) + ", soaTime=" + (soaTime/1000000) + ", totTime=" + (totTime/1000000) + ", cmUecTime=" + (cmUecTime/1000000) + ", cmOtherTime=" + (cmOtherTime/1000000) + ", lsTotalTime=" + (lsTotalTime/1000000) + "." );

//        writeCounts("filter", filterCount);        
//        writeCounts("expression", expressionCount);        
//        writeCounts("coeff", coeffCount);        

        String resultString = "result for thread=" + threadName + ", task=" + taskIndex + ", startIndex=" + startIndex + "endIndex=" + endIndex + ", total=" + total + "secs for task.";
        setResult( resultString );
        
        modelManager.returnDcModelObject( dcModel, taskIndex, startIndex, endIndex );
        
    }

    private void writeCounts(String countType, long[][] count){
        
        FileWriter writer;
        PrintWriter outStream = null;
        String fileName = "task" + taskIndex + "_" + countType + ".csv";
        try {
            writer = new FileWriter(new File(fileName));
            outStream = new PrintWriter(new BufferedWriter(writer));

            String headerString = "e";
            for ( int k=0; k < count[0].length; k++ )
                headerString += ( ", a" + (k+1) );
            outStream.println( headerString );

            for ( int j=0; j < count.length; j++ ){
                String valueString = String.valueOf((j+1));
                for ( int k=0; k < count[j].length; k++ )
                    valueString += ( "," + count[j][k] );
                outStream.println( valueString );
            }
            
            outStream.close();
        }
        catch (IOException e) {
            System.out.println( String.format("Exception occurred writing task performance file: %s.", fileName) );
            throw new RuntimeException(e);
        }
        
    }
    
    public String getId() {
        return Integer.toString(taskIndex);
    }
    
}
