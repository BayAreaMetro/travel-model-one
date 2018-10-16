package com.pb.models.ctramp.jppf;

import java.util.HashMap;
import java.util.LinkedList;
import org.apache.log4j.Logger;
import com.pb.common.calculator.MatrixDataManager;
import com.pb.common.matrix.MatrixIO32BitJvm;
import com.pb.common.matrix.MatrixType;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.MatrixDataServer;
import com.pb.models.ctramp.MatrixDataServerRmi;
import com.pb.models.ctramp.TazDataIf;


public class ExpUtilityModelManager
{


    private static Logger logger = Logger.getLogger( ExpUtilityModelManager.class );

    public static final int MATRIX_DATA_SERVER_PORT = 1171;

    private static ExpUtilityModelManager objInstance = null;
    private LinkedList<ExpUtilityModel> modelQueue = null;
    private int modelIndex;
    
    private MatrixDataServerRmi ms;
    private MatrixIO32BitJvm ioVm32Bit;
    private MatrixDataManager mdm;
    private boolean matrixIoSetup;
    
    private ExpUtilityModelManager() {
    }

    public static synchronized ExpUtilityModelManager getInstance() {
        if ( objInstance == null ) {
            objInstance = new ExpUtilityModelManager();
            objInstance.modelIndex = 0;
            objInstance.matrixIoSetup = false;
        }
        return objInstance;
    }

    
    public synchronized ExpUtilityModel getModelObject( HashMap<String,String> propertyMap, CtrampDmuFactoryIf dmuFactory, TazDataIf tazDataHandler,
            double[] valueOfTimeArray, String uecFileName, int dataPage, int nmPage, int sovPage, int hovPage, int wtPage, int dtPage, String periodDescription )  
    {

        ExpUtilityModel accModel = null;

        if ( modelQueue == null )
            modelQueue = new LinkedList<ExpUtilityModel>();

        
        if ( modelQueue.isEmpty() ) {
                
            modelIndex ++;
            accModel = new ExpUtilityModel();
            
            if ( matrixIoSetup == false )
                setupMatrixServer( propertyMap );
            
            accModel.setup( propertyMap, dmuFactory, tazDataHandler, valueOfTimeArray, uecFileName,
                dataPage, nmPage, sovPage, hovPage, wtPage, dtPage, periodDescription );
            
        }
        else {
        
            accModel = modelQueue.remove();    
            
        }

        return accModel;
            
    }

    
    public void returnAccessibilityModelObject ( ExpUtilityModel accModel ) {
        modelQueue.add( accModel );
    }
    
    public void close() {
        if ( ms != null ) {
            ms.stop32BitMatrixIoServer();
        }
        else {
            stop32BitMatrixIoServer();
        }
        
    }
    
    
    /**
     * Start a 32-bit matrix server to write matrices.
     * 
     * @param mType   Matrix type 
     */
    private void start32BitMatrixIoServer(MatrixType mType)
    {

        // start the matrix I/O server process
        ioVm32Bit = MatrixIO32BitJvm.getInstance();
        ioVm32Bit.setSizeInMegaBytes( 1024 );
        ioVm32Bit.startJVM32();

        // establish that matrix reader and writer classes will use the RMI versions
        ioVm32Bit.startMatrixDataServer(mType);
        logger.info("matrix data server 32 bit process started.");

    }

    /**
     * Stop the 32-bit matrix server.
    */
    private void stop32BitMatrixIoServer()
    {

        if ( ioVm32Bit != null ) {

            // stop the matrix I/O server process
            ioVm32Bit.stopMatrixDataServer();

            // close the JVM in which the RMI reader/writer classes were running
            ioVm32Bit.stopJVM32();
            logger.info("matrix data server 32 bit process stopped.");
            
        }

    }

        
    
    /**
     * Helper method for establishing connection to the matrix server.  If "none" was specified, default server is started
     * on localhost.  Otherwise, a server at the IP address and port specified is assumed to be running, and this code
     * will start the server and stop it when finished.
     * 
     * @param pMap is the proprty file HashMap
     */
    private void setupMatrixServer( HashMap<String, String> pMap ) {
        
        String matrixServerAddress = "";
        int serverPort = 0;

        // get matrix server address. if "none" is specified, no server will be
        // started, and matrix io will ocurr within the current process.
        matrixServerAddress = pMap.get( "RunModel.MatrixServerAddress" );
        if ( matrixServerAddress == null )
            matrixServerAddress = "localhost";

        // get matrix server port.
        String serverPortString = pMap.get( "RunModel.MatrixServerPort" );
        if ( serverPortString == null )
            serverPort = MATRIX_DATA_SERVER_PORT;
        else
            serverPort = Integer.parseInt( serverPortString );


        MatrixType mt = MatrixType.TPPLUS;

        
        
        try {

            if ( ! matrixServerAddress.equalsIgnoreCase("none") ) {

                if ( matrixServerAddress.equalsIgnoreCase("localhost") ) {

                    try {
                        // create the concrete data server object
                        start32BitMatrixIoServer( mt );        
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( "RuntimeException caught starting 64 bit matrix server on localhost -- exiting.", e );
                        close();
                    }

                }
                else {
                    try {
                        // create the RMI data server object
                        ms = new MatrixDataServerRmi( matrixServerAddress, serverPort, MatrixDataServer.MATRIX_DATA_SERVER_NAME );
                        ms.testRemote(Thread.currentThread().getName());
                        ms.start32BitMatrixIoServer( mt );

                        mdm = MatrixDataManager.getInstance();
                        mdm.setMatrixDataServerObject( ms );
                        
                    }
                    catch ( RuntimeException e ) {
                        logger.error ( "RuntimeException caught starting matrix server: " + matrixServerAddress + ":" + serverPort + " from RMI object -- exiting.", e );
                        throw new RuntimeException();
                    }
                }

            }

        }
        catch (Exception e) {

            close();
            
            logger.error( String.format("exception caught setting up matrix server -- exiting."), e );
            throw new RuntimeException();

        }

        matrixIoSetup = true;
        
    }
        
}
