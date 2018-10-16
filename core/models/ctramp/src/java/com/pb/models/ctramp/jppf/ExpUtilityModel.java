package com.pb.models.ctramp.jppf;

import java.util.HashMap;
import org.apache.log4j.Logger;
import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.util.Tracer;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.ModeChoiceDMU;
import com.pb.models.ctramp.TazDataIf;
import com.pb.common.newmodel.ChoiceModelApplication;

public class ExpUtilityModel
{

    private static transient Logger logger = Logger.getLogger(ExpUtilityModel.class);

    
    private int maxTaz;
    private int numDcAlts;
    private int numberOfSubzones;
    
    private IndexValues index;
    
    private ModeChoiceDMU mcDmuObject;
    
    private ChoiceModelApplication nmModel;
    private ChoiceModelApplication sovModel;
    private ChoiceModelApplication hovModel;
    private ChoiceModelApplication wtModel;
    private ChoiceModelApplication dtModel;
    
    private double[][] nmExpUtilities;
    private double[][] sovExpUtilities;
    private double[][] hovExpUtilities;
    private double[][][] wtExpUtilities;
    private double[][][] dtExpUtilities;

    private double[] valueOfTimeArray;
    
    
    
    public ExpUtilityModel() {
    }

    
    public synchronized void setup( HashMap<String,String> propertyMap, CtrampDmuFactoryIf dmuFactory, TazDataIf tazDataHandler,
            double[] valueOfTimeArray, String uecFileName, int dataPage, int nmPage, int sovPage, int hovPage, int wtPage, int dtPage, String periodDescription )  
    {
        
        this.valueOfTimeArray = valueOfTimeArray;
        
        maxTaz = tazDataHandler.getNumberOfZones();
        numberOfSubzones = tazDataHandler.getNumberOfSubZones();
        numDcAlts = maxTaz * numberOfSubzones;
        
        
        // Create the modal utility CghoiceModelApplication objects to use to compute logsums accross modes
        mcDmuObject = dmuFactory.getModeChoiceDMU();
        index = new IndexValues();

        
        // dimension the arrays to be used to store pre-computed exponentiated utilities for use in calculating accessibility logsums
        // and create the mode specific ChoiceModelApplication object
        if ( nmPage >= 0 ) {
            nmExpUtilities = new double[valueOfTimeArray.length][maxTaz+1];
            nmModel  = createChoiceModel( propertyMap, uecFileName, nmPage, dataPage, mcDmuObject, periodDescription + " Non-Motorized Accessibility Utility Logsum" );
        }
        
        if ( sovPage >= 0 ) {
            sovExpUtilities = new double[valueOfTimeArray.length][maxTaz+1];
            sovModel = createChoiceModel( propertyMap, uecFileName, sovPage, dataPage, mcDmuObject, periodDescription + " SOV Accessibility Utility Logsum" );
        }
        
        if ( hovPage >= 0 ) {
            hovExpUtilities = new double[valueOfTimeArray.length][maxTaz+1];
            hovModel = createChoiceModel( propertyMap, uecFileName, hovPage, dataPage, mcDmuObject, periodDescription + " HOV Accessibility Utility Logsum" );
        }
        
        if ( wtPage >= 0 ) {
            wtExpUtilities = new double[valueOfTimeArray.length][maxTaz+1][numberOfSubzones];
            wtModel = createChoiceModel( propertyMap, uecFileName, wtPage, dataPage, mcDmuObject, periodDescription + " WT Accessibility Utility Logsum" );
        }

        if ( dtPage >= 0 ) {
            dtExpUtilities = new double[valueOfTimeArray.length][maxTaz+1][numberOfSubzones];
            dtModel = createChoiceModel( propertyMap, uecFileName, dtPage, dataPage, mcDmuObject, periodDescription + " DT Accessibility Utility Logsum" );
        }
        
    }

    
    /**
     * Use the ChoiceModelApplication object to get the logsum over the subnest alternatives,
     * then exponentiate, to store the summed, exponentiated utilities by subnest.
     * 
     * @param iTaz origin TAZ
     * @param iSubzone origin subzone
     * @param tracer used to specify orig/dest for debug output
     * 
     */
    public void calculateExponentiatedUtilities( int iTaz, int iSubzone, int incomeIndex, Tracer tracer ) {

        double utility = -999;

        mcDmuObject.setOrigSubzone( iSubzone );
        mcDmuObject.setAccessibilityValueOfTime( valueOfTimeArray[incomeIndex] );
        
        for ( int dcAlt=0; dcAlt < numDcAlts; dcAlt++ ) {

            int jTaz = ( dcAlt / numberOfSubzones ) + 1;
            int jSubzoneIndex = dcAlt - ( jTaz - 1 ) * numberOfSubzones;            

            mcDmuObject.setDestSubzone( jSubzoneIndex );
            mcDmuObject.setDmuIndexValues( 0, iTaz, jTaz );
            
            // highway utiities are the same for all subzones in a TAZ, so just compute once for subzone 0 for each dest TAZ.
            if ( jSubzoneIndex == 0 ) {
            
                // NM exponentiated utility            
                utility = calculateLogsumForTazPair( nmModel, mcDmuObject, tracer, iTaz, jTaz );
                if ( utility > -500 )
                    nmExpUtilities[incomeIndex][jTaz] = Math.exp( utility );

                // SOV exponentiated utility            
                utility = calculateLogsumForTazPair( sovModel, mcDmuObject, tracer, iTaz, jTaz );
                if ( utility > -500 )
                    sovExpUtilities[incomeIndex][jTaz] = Math.exp( utility );

                // HOV exponentiated utility            
                utility = calculateLogsumForTazPair( hovModel, mcDmuObject, tracer, iTaz, jTaz );
                if ( utility > -500 )
                    hovExpUtilities[incomeIndex][jTaz] = Math.exp( utility );

            }
            // transit utiities are unnecesry for subzone index = 0, so just compute for subzone 1 and 2 for each dest TAZ.
            else {
                
                // peak Walt-transit exponentiated utility            
                utility = calculateLogsumForTazPair( wtModel, mcDmuObject, tracer, iTaz, jTaz );
                if ( utility > -500 )
                    wtExpUtilities[incomeIndex][jTaz][jSubzoneIndex] = Math.exp( utility );

                // peak Walt-transit exponentiated utility            
                utility = calculateLogsumForTazPair( dtModel, mcDmuObject, tracer, iTaz, jTaz );
                if ( utility > -500 )
                    dtExpUtilities[incomeIndex][jTaz][jSubzoneIndex] = Math.exp( utility );
            }

        }
            
    }
    

    /**
     * Create a ChoiceModelApplication object for the properties specified.
     * 
     * @param propertyMap The application properties file HashMap.
     * @param UECFileName The path/name of the UEC containing the utility specification.
     * @param modelSheet The sheet (0-indexed) containing the utility specification.
     * @param dataSheet The sheet (0-indexed) containing the data specification.
     */
    private ChoiceModelApplication createChoiceModel( HashMap<String, String> propertyMap, String uecFileName, int modelSheet, int dataSheet, Object dmuObject, String description )
    {
        // use the choice model application to set up the model structure
        ChoiceModelApplication modelApp = new ChoiceModelApplication(uecFileName, modelSheet, dataSheet, propertyMap, (VariableTable)dmuObject );
        modelApp.setDescription( description );
        return modelApp;
    }
    

    /**
     * Solve auto utilities for a given zone-pair
     * 
     * @param pTaz Production/Origin TAZ.
     * @param aTaz Attraction/Destination TAZ.
     * @return The root utility.
     */
    private double calculateLogsumForTazPair( ChoiceModelApplication modelApp, Object dmu, Tracer tracer, int pTaz, int aTaz )
    {

        boolean trace = false; 
        index.setDebug( false );
        if ( tracer.isTraceOn() && tracer.isTraceZonePair(pTaz, aTaz) )
        {
            trace = true;
            index.setDebug( true );
        }
        index.setOriginZone(pTaz);
        index.setDestZone(aTaz);
        index.setZoneIndex(aTaz);

        modelApp.computeUtilities(dmu, index);
        double logsum = modelApp.getLogsum();

        // logging
        if ( trace )
        {
            modelApp.logUECResults( logger );
            trace = false;
        }

        return logsum;
    }    
    
    
    public double[] getNmExpUtilities( int incomeIndex ) {
        return nmExpUtilities[incomeIndex];
    }
    
    public double[] getSovExpUtilities( int incomeIndex ) {
        return sovExpUtilities[incomeIndex];
    }
    
    public double[] getHovExpUtilities( int incomeIndex ) {
        return hovExpUtilities[incomeIndex];
    }
    
    public double[][] getWtExpUtilities( int incomeIndex ) {
        return wtExpUtilities[incomeIndex];
    }
    
    public double[][] getDtExpUtilities( int incomeIndex ) {
        return dtExpUtilities[incomeIndex];
    }
    
}
