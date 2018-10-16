package com.pb.models.ctramp.old;

import java.io.Serializable;
import java.util.HashMap;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

import org.apache.log4j.Logger;

import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.calculator.MatrixDataServerIf;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataIf;


public class DestChoiceModelFactory implements Serializable {

    public static Logger logger = Logger.getLogger(DestChoiceModelFactory.class);

    private static DestChoiceModelFactory instance = new DestChoiceModelFactory();

    private BlockingQueue<DestChoiceModel> modelQueue = new LinkedBlockingQueue<DestChoiceModel>();

    
    private HashMap<String, String> propertyMap;
    private MatrixDataServerIf ms;
    private ModelStructure modelStructure;
    private String tourCategory;
    private TazDataIf tazDataManager;
    private DestChoiceSize dcSizeObj;
    private String dcUecFileName;
    private String soaUecFileName;
    private int soaSampleSize;
    private String modeChoiceUecFileName;
    private CtrampDmuFactoryIf dmuFactory;
   
    
    private DestChoiceModelFactory(){        
    }


    
    
    /**
     * creates a DestChoiceModelObject.  The synchronized method allows access to only one thread at a time
     * so only one DestChoiceModel object will be created at a time.  Once the first one in a virtual machine
     * is created, a large amount of input data will have been read into static data members, and others that
     * are created afterward will take less time.
     */
    private DestChoiceModel createDcModelInstance() {

        MatrixDataManager mdm = MatrixDataManager.getInstance();
        mdm.setMatrixDataServerObject( ms );
        String testString = ms.testRemote(Thread.currentThread().getName());
        logger.info ( String.format( "Remote MatrixDataServer test: %s", testString ) );
        
        // create the destination choice model
        DestChoiceModel dcModel = new DestChoiceModel( propertyMap, modelStructure, tourCategory, tazDataManager, dcSizeObj,
            dcUecFileName, soaUecFileName, soaSampleSize, modeChoiceUecFileName, dmuFactory );

       // logger.info ( String.format( "DestChoiceModel model instance %d created.", dcModel.getDcModelObjectInstanceNumber() ) );

        return dcModel;
    }
    
    
    public static DestChoiceModelFactory getDestChoiceModelFactoryInstance( HashMap<String, String> propertyMap, MatrixDataServerIf ms,
            ModelStructure modelStructure, String tourCategory, TazDataIf tazDataManager, DestChoiceSize dcSizeObj,
            String dcUecFileName, String soaUecFileName, int soaSampleSize, String modeChoiceUecFileName, CtrampDmuFactoryIf dmuFactory ) {

        instance.propertyMap = propertyMap;
        instance.ms = ms;
        instance.modelStructure = modelStructure;
        instance.tourCategory = tourCategory;
        instance.tazDataManager = tazDataManager;
        instance.dcSizeObj = dcSizeObj;
        instance.dcUecFileName = dcUecFileName;
        instance.soaUecFileName = soaUecFileName;
        instance.soaSampleSize = soaSampleSize;
        instance.modeChoiceUecFileName = modeChoiceUecFileName;
        instance.dmuFactory = dmuFactory;
                
        return instance;
    }
    
    public String getDcUecFilName() {
        return instance.dcUecFileName;
    }
    
    
    public synchronized void returnDcModelObject ( DestChoiceModel dcModel ) {
        modelQueue.add( dcModel );
    }
        
    
    /**
     * @return DestChoiceModel object from the queue if one is in the queue, otherwisw creates one.
     */
    public synchronized DestChoiceModel getDcModelObject () {
        if ( modelQueue.size() == 0 ) {
            return instance.createDcModelInstance();
        }
        else {
            DestChoiceModel dcModel = modelQueue.remove();
            dcModel.zeroModeledDestinationLocationsByDestZoneArray();
            return dcModel;
        }
    }
    
    
}
