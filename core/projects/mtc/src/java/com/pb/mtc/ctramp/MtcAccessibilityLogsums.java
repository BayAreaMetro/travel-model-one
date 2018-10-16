package com.pb.mtc.ctramp;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.ResourceBundle;
import org.apache.log4j.Logger;
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.ResourceUtil;
import com.pb.models.ctramp.CtrampDmuFactoryIf;
import com.pb.models.ctramp.DestChoiceSize;
import com.pb.models.ctramp.ModelStructure;
import com.pb.models.ctramp.TazDataHandler;
import com.pb.models.ctramp.jppf.AccessibilityLogsumsCalculator;
import com.pb.models.ctramp.jppf.CtrampApplication;

public class MtcAccessibilityLogsums
{

    private static transient Logger logger = Logger.getLogger(MtcAccessibilityLogsums.class);
    
    private static final String[] INCOME_SEGMENTS = {
        "HHINC < 30K",
        "30K <= HHINC < 60K",
        "60K <= HHINC < 100K",
        "HHINC >= 100K"
    };        
    
    private static final String[] AUTO_SUFFICIENCY_SEGMENTS = {
        "0 AUTOS",
        "AUTOS < WORKERS",
        "AUTOS >= WORKERS"
    };
        
    private static final String[][] SIZE_SEGMENTS = {
        
        { "work_low",
        "work_med",
        "work_high",
        "work_very high" },
        
        { "othMaint" }
        
    };
    
    private TazDataHandler tazDataHandler;    
    
    
    private MtcAccessibilityLogsums(){        
    }
    
    
//     private void runOdTest( AccessibilityLogsumsCalculator testObject ) {
//        
//        int iTaz = 120;
//        int jTaz = 1200;
//        double[][] logsums = new double[3][3];
//        for ( int iSubzone=0; iSubzone < 3; iSubzone++ ) {
//            for ( int jSubzone=0; jSubzone < 3; jSubzone++ )
//                logsums[iSubzone][jSubzone] = testObject.calculateWalkTransitExpUtilitiesTraceOnly( iTaz, iSubzone, jTaz, jSubzone );       
//        }
//
//        for ( int iSubzone=0; iSubzone < 3; iSubzone++ ) {
//            for ( int jSubzone=0; jSubzone < 3; jSubzone++ )
//                logger.info( "Logsum = " + logsums[iSubzone][jSubzone] + ", for iTaz=" + iTaz + ", iSubzone=" + iSubzone + ", jTaz=" + jTaz + ", jSubzone=" + jSubzone );
//        }
//       
//     }
   

    private void createAccessibilitiesLogsumsTables( AccessibilityLogsumsCalculator logsumsObject ) {        
        
        double[][][] accessibilitiesTable = logsumsObject.calculateAccessibilities( SIZE_SEGMENTS );
         
        String mandatoryAccFileName = "./mandatoryAccessibities.csv";
        writeAccessibilitiesTable( mandatoryAccFileName, accessibilitiesTable[0] );
         
        String nonMandatoryAccFileName = "./nonMandatoryAccessibities.csv";
        writeAccessibilitiesTable( nonMandatoryAccFileName, accessibilitiesTable[1] );
         
        logsumsObject.closeAccessibilityLogsumsCalculator();         
    }
     
    
    private void writeAccessibilitiesTable( String accFileName, double[][] accessibilitiesTable ) {

        int numberOfSubzones = tazDataHandler.getNumberOfSubZones();
        String[] headings = {
                "lowInc_0_autos", "lowInc_autos_lt_workers", "lowInc_autos_ge_workers",
                "medInc_0_autos", "medInc_autos_lt_workers", "medInc_autos_ge_workers",
                "highInc_0_autos", "highInc_autos_lt_workers", "highInc_autos_ge_workers",
                "veryHighInc_0_autos", "veryHighInc_autos_lt_workers", "veryHighInc_autos_ge_workers"
        };
        
        float[] altTable = new float[accessibilitiesTable.length];
        float[] tazTable = new float[accessibilitiesTable.length];
        float[] subzoneTable = new float[accessibilitiesTable.length];
        
        float[][] floatTable = new float[accessibilitiesTable.length][];
        for ( int i=0; i < accessibilitiesTable.length; i++ ) {
            
            altTable[i] = i;
            int jTaz = ( i / numberOfSubzones ) + 1;
            int jSubzoneIndex = i - ( jTaz - 1 ) * numberOfSubzones;            
            tazTable[i] = jTaz;
            subzoneTable[i] = jSubzoneIndex;
  
            try {
                
                if ( accessibilitiesTable[i] == null ) {
                    floatTable[i] = new float[headings.length];
                    Arrays.fill( floatTable[i], Float.NEGATIVE_INFINITY );
                }
                else {
                    floatTable[i] = new float[accessibilitiesTable[i].length];
                    for ( int j=0; j < accessibilitiesTable[i].length; j++ )
                        floatTable[i][j] = (float)accessibilitiesTable[i][j];
                }

            }
            catch ( Exception e ) {
                
                logger.error ( "error for i = " + i, e );
                
            }
            
        }
         
        
        File accFile = new File( accFileName );
        TableDataSet accData = TableDataSet.create( floatTable, headings );
        accData.appendColumn( altTable, "destChoiceAlt" );
        accData.appendColumn( tazTable, "taz" );
        accData.appendColumn( subzoneTable, "subzone" );
        
        CSVFileWriter csv = new CSVFileWriter();

        try {
             csv.writeFile(accData, accFile);
        }
        catch (IOException e) {

             logger.error("Error trying to write accessiblities data file " + accFileName);
             throw new RuntimeException(e);
        }
         
    }


    private void createLogsumsFiles( String baseName, int testArgs ) {
        
        ResourceBundle rb = ResourceUtil.getResourceBundle ( baseName );
        HashMap<String, String> pMap = ResourceUtil.getResourceBundleAsHashMap ( baseName );

        String projectDirectory = ResourceUtil.getProperty( rb, CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        tazDataHandler = new MtcTazDataHandler( rb, projectDirectory );
        ModelStructure modelStructure = new MtcModelStructure();
        CtrampDmuFactoryIf dmuFactory = new MtcCtrampDmuFactory( tazDataHandler, modelStructure );

        // create an object for calculating destination choice attraction size terms and managing shadow price calculations.
        DestChoiceSize[] dcSizeObjs = new DestChoiceSize[2];
        
        dcSizeObjs[0] = new DestChoiceSize( modelStructure, tazDataHandler );
        dcSizeObjs[0].setupDestChoiceSize( rb, projectDirectory, ModelStructure.MANDATORY_CATEGORY );
        dcSizeObjs[0].calculateDcSize();

        dcSizeObjs[1] = new DestChoiceSize( modelStructure, tazDataHandler );
        dcSizeObjs[1].setupDestChoiceSize( rb, projectDirectory, ModelStructure.INDIVIDUAL_NON_MANDATORY_CATEGORY );
        dcSizeObjs[1].calculateDcSize();
        
        
        AccessibilityLogsumsCalculator logsumsObject = new AccessibilityLogsumsCalculator( pMap, dmuFactory, tazDataHandler, dcSizeObjs,
                INCOME_SEGMENTS, AUTO_SUFFICIENCY_SEGMENTS );
        
        if ( testArgs > 0 )
            logsumsObject.setTestAlts( testArgs );
        
        createAccessibilitiesLogsumsTables( logsumsObject );
        
    }
    



    public static void main(String[] args) {


        long startTime = System.currentTimeMillis();
        
        // if there is a second comand line argument, use it as the number of destination choice alternatives
        // to shorten the runtime.  Otherwise, the full set ( 1454 tazs * 3 subzones = 4362 ) are calculated.
        int testArgs = -1;
        
        logger.info( "MTC Accessibility Logsum Calculator" );
        
        if ( args.length == 0 ) {
            logger.error( "no properties file base name was specified as an argument." );
            logger.error( "please add the properties file base name (without .properties extension) as the only command line argument." );
            return;
        }
        else {      
            
            String baseName;
            if ( args[0].endsWith(".properties") ) {
                int index = args[0].indexOf(".properties");
                baseName = args[0].substring(0, index);
            }
            else {
                baseName = args[0];
            }
            
            if ( args.length == 2 ) {
                testArgs = Integer.parseInt( args[1] );
            }

            MtcAccessibilityLogsums mainObject = null;
            try {
                mainObject = new MtcAccessibilityLogsums();
                mainObject.createLogsumsFiles( baseName, testArgs );
            }
            catch(Exception e) {
                logger.fatal( "Caught exception running createLogsumsFiles() method.", e );
            }
            
        }

       logger.info("");
       logger.info("MTC Accessibility Logsum Calculator finished in "
               + ((System.currentTimeMillis() - startTime) / 60000.0) + " minutes.");

       System.exit(-1);
    }
    
}
