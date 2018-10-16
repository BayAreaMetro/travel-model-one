package com.pb.models.ctramp.jppf;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.common.calculator.TableDataSetManager;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;
import com.pb.models.ctramp.jppf.MandatoryDestChoiceModel;

public class DestChoiceModelManager implements Serializable {

    private Logger logger = Logger.getLogger(DestChoiceModelManager.class);

    private static DestChoiceModelManager objInstance = null;

    private MatrixDataManager mdm = null;
    private LinkedList<MandatoryDestChoiceModel> modelQueue = null;

    private HashMap<String, String> propertyMap;
    private ModelStructure modelStructure;
    private String tourCategory;
    private TazDataIf tazDataManager;
    private DestChoiceSize dcSizeObj;
    private String dcUecFileName;
    private String soaUecFileName;
    private int soaSampleSize;
    private String modeChoiceUecFileName;
    private CtrampDmuFactoryIf dmuFactory;

    private int modelIndex;
    private int currentIteration;

    private int completedHouseholds = 0;

    
    
    private DestChoiceModelManager(){        
    }

    
        
    public static synchronized DestChoiceModelManager getInstance() {
        if ( objInstance == null ) {
            objInstance = new DestChoiceModelManager();
            objInstance.modelIndex = 0;
            objInstance.currentIteration = 0;
            objInstance.completedHouseholds = 0;
            return objInstance;
        }
        else {
            return objInstance;
        }
    }


    
    // the task instances should call needToInitialize() first, then this method if necessary.
    public synchronized void factorySetup( HashMap<String, String> propertyMap, MatrixDataServerIf ms, ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj,
            String dcUecFileName, String soaUecFileName, int soaSampleSize, String modeChoiceUecFileName, CtrampDmuFactoryIf dmuFactory, String restartModelString ) {

        if ( modelQueue != null ) {
            return;
        }

        modelIndex = 0;
        completedHouseholds = 0;
        
        System.out.println( String.format( "initializing DC ModelManager: thread=%s.", Thread.currentThread().getName() ) );
        
        this.propertyMap = propertyMap;
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;
        this.tourCategory = tourCategory;
        this.dcSizeObj = dcSizeObj;
        this.dcUecFileName = dcUecFileName;
        this.soaUecFileName = soaUecFileName;
        this.soaSampleSize = soaSampleSize;
        this.modeChoiceUecFileName = modeChoiceUecFileName;
        this.dmuFactory = dmuFactory;


        // the first thread to reach this method initializes the modelQueue used to recycle dcModel objects. 
        modelQueue = new LinkedList<MandatoryDestChoiceModel>();
        
        
        
        // Initialize the MatrixDataManager to use the MatrixDataServer instance passed in, unless ms is null.
        if ( ms == null ) {
            if ( mdm != null ) {
                logger.info ( Thread.currentThread().getName() + ": No remote MatrixServer being used, but MatrixDataManager already exists - resetting for DestChoiceModelManager." );
                mdm.clearData();
            }
            else {
                logger.info ( Thread.currentThread().getName() + ": No remote MatrixServer being used, MatrixDataManager will get created when needed by DestChoiceModelManager." );
            }
        }
        else if ( mdm == null ) {
            String testString = ms.testRemote();
            logger.info ( String.format( Thread.currentThread().getName() + ": DestChoiceModelManager needs MatrixDataManager, MatrixDataServer connection test: %s", testString ) );
            mdm = MatrixDataManager.getInstance();
            mdm.setMatrixDataServerObject( ms );
        }
        else {
            logger.info ( Thread.currentThread().getName() + ": MatrixDataManager already exists - resetting for DestChoiceModelManager." );
            mdm.clearData();
        }

        
        TableDataSetManager tdm = TableDataSetManager.getInstance();
        tdm.clearData();
    }

    
    public void returnDcModelObject ( MandatoryDestChoiceModel dcModel, int taskIndex, int startIndex, int endIndex ) {
        modelQueue.add( dcModel );
        completedHouseholds += (endIndex - startIndex + 1);
        int probCalcs = dcModel.getProbCalcs();
        logger.info( String.format( "returned dcModel=%d to queue, task=%d, thread=%s, completedHouseholds=%d, probCalcs=%d.", dcModel.getModelIndex(), taskIndex, Thread.currentThread().getName(), completedHouseholds, probCalcs ) );
    }
        
    
    /**
     * @return DestChoiceModel object created if less than the max number have been created, otherwise retrieved from the queue.
     * 
     */
    //public MandatoryDestChoiceModel getDcModelObject( int taskIndex, int iteration ) {
    public synchronized MandatoryDestChoiceModel getDcModelObject( int taskIndex, int iteration ) {
        
        String message = "";
        MandatoryDestChoiceModel dcModel = null;

        if ( modelQueue.isEmpty() ) {

            modelIndex ++;
            dcModel = createDestChoiceModelObject( modelIndex, propertyMap, modelStructure, tourCategory, tazDataManager, dcSizeObj,
                    dcUecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory );
            message = String.format( "created dcModel=%d, task=%d, thread=%s.", modelIndex, taskIndex, Thread.currentThread().getName() );
            
        }
        else {
        
            // the first task processed with an iteration parameter greater than the manager's current iteration count clears the dcModel cache and updates the iteration count.
            if ( iteration > currentIteration ) {
                currentIteration = iteration;
                completedHouseholds = 0;
            }
            
            dcModel = modelQueue.remove();    
            
            message = String.format( "removed dcModel=%d from queue, task=%d, thread=%s.", dcModel.getModelIndex(), taskIndex, Thread.currentThread().getName() );
            
        }

        logger.info( message );
        return dcModel;
            
    }
    
    
 
    private MandatoryDestChoiceModel createDestChoiceModelObject ( int modelIndex, HashMap<String, String> propertyMap, ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj,
            String dcUecFileName, String soaUecFileName, int soaSampleSize, String modeChoiceUecFileName, CtrampDmuFactoryIf dmuFactory ) {
        
        // create a new dcModel instance to be shared among tasks running in this node
        MandatoryDestChoiceModel dcModel = new MandatoryDestChoiceModel( modelIndex, propertyMap, modelStructure, tourCategory, tazDataManager, dcSizeObj,
                dcUecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory );
        
        return dcModel;
    }

    

    
    public void clearDcModels() {
        
        if ( modelQueue == null ) {
            return;
        }
    
        Iterator<MandatoryDestChoiceModel> it = modelQueue.iterator();
        while ( it.hasNext() ) {
            MandatoryDestChoiceModel dcModel = it.next();
            if ( dcModel != null ) {
                logger.info( "cleaned up dcModel " + dcModel.getModelIndex() + "." );
                dcModel = null;
            }
        }

        modelIndex = 0;
        completedHouseholds = 0;
        
        modelQueue.clear();
        modelQueue = null;
        
        dcSizeObj = null;
    }


    
    public MatrixDataManager getMatrixDataManager() {
        return mdm;
    }
    
    
}
