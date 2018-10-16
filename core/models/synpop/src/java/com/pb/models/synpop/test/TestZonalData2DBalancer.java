package com.pb.models.synpop.test;

import com.pb.common.matrix.NDimensionalMatrixDouble;
import com.pb.models.synpop.ZonalData2DBalancer;

import org.apache.log4j.Logger;

/**
 * Calculate a joint probability distribution of HHs (hhincome x hhsize) for each zone
 * based on marginal distributions of hhincome and hhsize by zone and seed joint
 * distributions of weighted PUMS households by hhincome and hhsize from the puma
 * in which the zone is located. 
 *
 */
public class TestZonalData2DBalancer {
    
	protected static Logger logger = Logger.getLogger(TestZonalData2DBalancer.class);
    
    
    public TestZonalData2DBalancer(String[] args) {
        
//        String appPropFile = args[0].substring(args[0].lastIndexOf('/')+1,args[0].length());
//        String globalPropFile = args[1].substring(args[1].lastIndexOf('/')+1,args[1].length());
//        runTest( appPropFile, globalPropFile );

        runTest( args[0], args[1] );

    }
    
    private void runTest( String appPropFile, String globalPropFile ) {
        
        ZonalData2DBalancer zdb = new ZonalData2DBalancer( appPropFile, globalPropFile );

        zdb.init();
        NDimensionalMatrixDouble[] finalBalancedTable = zdb.balanceZonalData();
        
        zdb.writeOutputFiles ( finalBalancedTable );
        
        logger.info( "TestZonalData2DBalancer.runTest() is finished." );

    }
    
    
    // the following main() is used to test the methods implemented in this object.
    public static void main (String[] args) {
        
        TestZonalData2DBalancer test = new TestZonalData2DBalancer(args);
        
    }

}



