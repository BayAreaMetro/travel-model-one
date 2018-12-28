package com.pb.models.ctramp.jppf;

import java.io.IOException;
import java.io.Serializable;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedList;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.util.ObjectUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;

public class HouseholdChoiceModelsManager implements Serializable {    

    private Logger logger = Logger.getLogger("HouseholdChoiceModelsManager");

    private static HouseholdChoiceModelsManager objInstance = null;

    private LinkedList<HouseholdChoiceModels> modelQueue = null;

    private HashMap<String, String> propertyMap;
    private String restartModelString;
    private ModelStructure modelStructure;
    private TazDataIf tazDataManager;
    private CtrampDmuFactoryIf dmuFactory;
    
    private int completedHouseholds = 0;
    
    private int modelIndex;

    
    private HouseholdChoiceModelsManager(){        
    }

    
        
   public static synchronized HouseholdChoiceModelsManager getInstance( HashMap<String, String> propertyMap, String restartModelString, ModelStructure modelStructure, TazDataIf tazDataManager, CtrampDmuFactoryIf dmuFactory ) {
        if ( objInstance == null ) {
            objInstance = new HouseholdChoiceModelsManager();
            
            objInstance.propertyMap = propertyMap;
            objInstance.restartModelString = restartModelString;
            objInstance.modelStructure = modelStructure;
            objInstance.tazDataManager = tazDataManager;
            objInstance.dmuFactory = dmuFactory;

            objInstance.completedHouseholds = 0;
            objInstance.modelIndex = 0;
            return objInstance;
        }
        else {
            return objInstance;
        }
    }

    
    // the task instances should call needToInitialize() first, then this method if necessary.
    public synchronized void managerSetup( MatrixDataServerIf ms ) {

        if ( modelQueue != null )
            return;
        
        modelIndex = 0;
        completedHouseholds = 0;
        
        //setupJointProbabilitiesCache();
        //setupIndivNonManProbabilitiesCache();
        //setupAtWorkProbabilitiesCache();
        
        // get the factory object used to create and recycle dcModel objects.  Call the manager's method to clear dcModel objects to free up memory if necessary.
        DestChoiceModelManager dcModelManager = DestChoiceModelManager.getInstance();
        dcModelManager.clearDcModels();
        MatrixDataManager mdm = dcModelManager.getMatrixDataManager();
        
        // the first thread to reach this method initializes the MatrixDataManager to use the MatrixDataServer instance passed in.
        if ( ms == null ) {
            if ( mdm != null ) {
                logger.info ( Thread.currentThread().getName() + ": No remote MatrixServer being used, but MatrixDataManager already exists." );
            }
            else {
                logger.info ( Thread.currentThread().getName() + ": No remote MatrixServer being used, MatrixDataManager will get created when needed for HouseholdChoiceModelManager." );
            }
        }
        else if ( mdm == null ) {
            String testString = ms.testRemote();
            logger.info ( String.format( Thread.currentThread().getName() + ": HouseholdChoiceModelManager needs MatrixDataManager, MatrixDataServer connection test: %s", testString ) );
            mdm = MatrixDataManager.getInstance();
            mdm.setMatrixDataServerObject( ms );
        }
        else {
            logger.info ( Thread.currentThread().getName() + ": MatrixDataManager already exists." );
        }

        // the first thread to reach this method initializes the modelQueue used to recycle hhChoiceModels objects. 
        modelQueue = new LinkedList<HouseholdChoiceModels>();

    }

    
    /**
     * @return DestChoiceModel object created if none is available from the queue.
     * 
     */
    public synchronized HouseholdChoiceModels getHouseholdChoiceModelsObject( int taskIndex ) {

        String message = "";
        HouseholdChoiceModels hhChoiceModels = null;
        
        
        if ( modelQueue.isEmpty() ) {
            // create choice model object
            //hhChoiceModels = new HouseholdChoiceModels( ++modelIndex, restartModelString, propertyMap, tazDataManager, modelStructure, dmuFactory, jointProbabilitiesCache, jointCumProbabilitiesCache, indivNonManProbabilitiesCache, indivNonManCumProbabilitiesCache, atWorkProbabilitiesCache, atWorkCumProbabilitiesCache );
            hhChoiceModels = new HouseholdChoiceModels( ++modelIndex, restartModelString, propertyMap, tazDataManager, modelStructure, dmuFactory );
//            long size = 0;
//            size = ObjectUtil.sizeOf( hhChoiceModels );
//            try {
//                size = ObjectUtil.checkObjectSize( hhChoiceModels );
//            }
//            catch (IOException e) {
//                // TODO Auto-generated catch block
//                e.printStackTrace();
//            }
            message = String.format( "created hhChoiceModels=%d, task=%d, thread=%s", modelIndex, taskIndex, Thread.currentThread().getName()  );
        }
        else {
            hhChoiceModels = modelQueue.remove();
            message = String.format( "removed hhChoiceModels=%d from queue, task=%d, thread=%s.", hhChoiceModels.getModelIndex(), taskIndex, Thread.currentThread().getName() );
        }
        logger.info( message );

        return hhChoiceModels;

    }

    
    /**
     * return the HouseholdChoiceModels object to the manager's queue so that it may be used by another thread
     * without it having to create one. 
     * @param hhModels
     */
    public void returnHouseholdChoiceModelsObject ( HouseholdChoiceModels hhModels, int startIndex, int endIndex ) {
        modelQueue.add( hhModels );
        completedHouseholds += (endIndex - startIndex + 1);
        logger.info( "returned hhChoiceModels=" + hhModels.getModelIndex() + " to queue: thread=" + Thread.currentThread().getName() + ", completedHouseholds=" + completedHouseholds + "." );
    }
        

    
    
    public synchronized void clearHhModels() {
        
        if ( modelQueue == null ) {
            return;
        }
        
        System.out.println( String.format( "%s:  clearing household choice models modelQueue, thread=%s.", new Date(), Thread.currentThread().getName() ) );
        
        while ( ! modelQueue.isEmpty() ) {
            HouseholdChoiceModels hhChoiceModels = modelQueue.remove();
            hhChoiceModels.cleanUp();
            System.out.println( "cleaned up hhModel " + hhChoiceModels.getModelIndex() + "." );
            hhChoiceModels = null;
        }
        
        modelIndex = 0;
        completedHouseholds = 0;
        
        modelQueue = null;

    }

}
