package com.pb.models.ctramp.old;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.Callable;

import org.apache.log4j.Logger;

import com.pb.models.ctramp.Household;
import com.pb.models.ctramp.HouseholdDataManagerIf;
import com.pb.models.ctramp.sqlite.SqliteService;

public class LocationChoiceTask implements Callable< List<Object> > {
	
	
    public static Logger logger = Logger.getLogger(LocationChoiceTask.class);


    private static Object objLock = new Object();
    
    private static int UPDATE_FREQUENCY_SECONDS = 1;
    
    private static SqliteService sqliteService = null;
    private static boolean useSqliteDatabase = false;
    private static String sqliteTableName = "LocationChoiceTask";
    
    private DestChoiceModelFactory modelFactory;
    private HouseholdDataManagerIf hhDataManager;
    private Household[] householdArray;

    private int startIndex;
    private int endIndex;

    
    private static int nextId = 0;
    private int taskIndex = -1;

    
    public LocationChoiceTask( HashMap<String, String> propertyMap, DestChoiceModelFactory modelFactory, HouseholdDataManagerIf hhDataManager, int startIndex, int endIndex ) {

        this.hhDataManager = hhDataManager;
        this.modelFactory = modelFactory;
        this.startIndex = startIndex;
        this.endIndex = endIndex;

        
        synchronized ( objLock ) {
            if ( sqliteService == null  ) {
                String dbFilename = propertyMap.get( CtrampApplication.SQLITE_DATABASE_FILENAME );
                if ( dbFilename != null ) {
                    useSqliteDatabase = true;
                    sqliteService = new SqliteService();
                    sqliteService.connect( dbFilename, sqliteTableName );
                }
            }
        }
        
        taskIndex = ++nextId;

    }

    
    
    public List<Object> call() {

        DestChoiceModel dcModel;

        long initTime = 0;
        long startUpTime = 0;
        long runningTime = 0;
        long shutDownTime = 0;
        
        if ( useSqliteDatabase ) {
            synchronized ( objLock ) {
                sqliteService.insertRecord( sqliteTableName, taskIndex, 0, 0, (int)startUpTime, (int)runningTime, (int)shutDownTime );
            }
            initTime = System.currentTimeMillis();
        }

        
        logger.info( String.format( "getting dcModelInstance for taskInstance=%d.", taskIndex ) );
        dcModel = modelFactory.getDcModelObject();
        //logger.info( String.format("start of call() using dcModelInstance=%d, taskInstance=%d, startIndex=%d, endIndex=%d", dcModel.getDcModelObjectInstanceNumber(), taskIndex, startIndex, endIndex) );
            
        
        householdArray = hhDataManager.getHhArray( startIndex, endIndex ); 
        
        if ( useSqliteDatabase ) {
           startUpTime = (System.currentTimeMillis() - initTime) / 1000;
           synchronized ( objLock ) {
               sqliteService.updateRecord( sqliteTableName, taskIndex, 0, householdArray.length, (int)startUpTime, 0, 0 );
           }
        }

            
        long startElapsedTime = System.currentTimeMillis();        
        initTime = System.currentTimeMillis();

        for ( int i=0; i < householdArray.length; i++ ) {

            try {
                dcModel.applyDestinationChoiceForHousehold ( householdArray[i] );
            }
            catch (RuntimeException e) {
                //logger.fatal ( String.format("exception caught in taskIndex=%d dcModelInstance=%d applying dc model for i=%d, hhId=%d.", taskIndex, dcModel.getDcModelObjectInstanceNumber(), i, householdArray[i].getHhId()) );
                logger.fatal( "Exception caught:", e );
                logger.fatal( "Throwing new RuntimeException() to terminate." );
                throw new RuntimeException();
            }
            
            if ( useSqliteDatabase ) {
                long elapsedSeconds = (System.currentTimeMillis() - startElapsedTime) / 1000;
                if ( elapsedSeconds >= UPDATE_FREQUENCY_SECONDS ) {
                    runningTime = (System.currentTimeMillis() - initTime) / 1000;
                    startElapsedTime = System.currentTimeMillis();
                    synchronized ( objLock ) {
                        sqliteService.updateRecord( sqliteTableName, taskIndex, i, householdArray.length, (int)startUpTime, (int)runningTime, 0 );
                    }
                }
            }

        }
        
        
        if ( useSqliteDatabase ) {
            runningTime = (System.currentTimeMillis() - initTime) / 1000;
            synchronized ( objLock ) {
                sqliteService.updateRecord( sqliteTableName, taskIndex, householdArray.length, householdArray.length, (int)startUpTime, (int)runningTime, 0 );
            }
        }

        
        initTime = System.currentTimeMillis();

        hhDataManager.setHhArray( householdArray, startIndex );

        double[][][] result = dcModel.getModeledDestinationLocationsByDestZone();
        
        // copy the result array returned to an array declared in this object so it isn't released back with dcModel.
        double[][][] localResult = new double[result.length][][];
        for (int i=0; i < result.length; i++) {
            localResult[i] = new double[result[i].length][];
            for ( int j=0; j < result[i].length; j++ ) {
                localResult[i][j] = new double[result[i][j].length];
                for ( int k=0; k < result[i][j].length; k++ ) {
                    localResult[i][j][k] = result[i][j][k];
                }
            }
        }
                
        List<Object> resultBundle = new ArrayList<Object>(1);
        resultBundle.add( localResult );
        
        //logger.info( String.format("end of call() using dcModelInstance=%d, taskInstance=%d, startIndex=%d, endIndex=%d", dcModel.getDcModelObjectInstanceNumber(), taskIndex, startIndex, endIndex) );

        
        if ( useSqliteDatabase ) {
            shutDownTime = (System.currentTimeMillis() - initTime) / 1000;
            synchronized ( objLock ) {
                sqliteService.updateRecord( sqliteTableName, taskIndex, householdArray.length, householdArray.length, (int)startUpTime, (int)runningTime, (int)shutDownTime );
            }
         }

        householdArray = null;
        System.gc();
        
        
        // thius has to be the last statement in this method.
        // add this DestChoiceModel instance to the static queue shared by other tasks of this type
        modelFactory.returnDcModelObject( dcModel );

        return resultBundle;

    }
    
}
