package com.pb.models.synpop;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.matrix.NDimensionalMatrixBalancerDouble;
import com.pb.common.matrix.NDimensionalMatrixDouble;
import com.pb.common.matrix.RowVector;
import com.pb.common.util.ResourceUtil;
import com.pb.common.util.SeededRandom;
import com.pb.models.censusdata.DataDictionary;
import com.pb.models.censusdata.PUMSDataReader;
import com.pb.models.censusdata.PumsGeography;
import org.apache.log4j.Logger;

import java.io.*;
import java.util.HashMap;
import java.util.ResourceBundle;

/**
 * Calculate a joint probability distribution of HHs (hhincome x hhsize) for each zone
 * based on marginal distributions of hhincome and hhsize by zone and seed joint
 * distributions of weighted PUMS households by hhincome and hhsize from the puma
 * in which the zone is located. 
 *
 */
public class ZonalData2DBalancer {
    
	protected static Logger logger = Logger.getLogger("com.pb.common.util");
    
    // the Halo object defines such things as the states and pumas in the model area,
    // the zonal correspondence file, etc...
    PumsGeography halo = null;
    
    HashMap propertyMap = null;
    HashMap globalPropertyMap = null;

    NDimensionalMatrixDouble[][] seedTables = null;
    float[][][] targets = null;

    

    
    public ZonalData2DBalancer () {
        propertyMap = ResourceUtil.getResourceBundleAsHashMap("zonalBalance");
        globalPropertyMap = ResourceUtil.getResourceBundleAsHashMap("global");
    }

    public ZonalData2DBalancer ( String propertyFileName, String globalPropertyFileName ) {
        propertyMap = ResourceUtil.getResourceBundleAsHashMap( propertyFileName );
        globalPropertyMap = ResourceUtil.getResourceBundleAsHashMap(globalPropertyFileName);
    }

    public ZonalData2DBalancer (ResourceBundle rb, ResourceBundle globalRb) {
        propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(rb);
        globalPropertyMap = ResourceUtil.changeResourceBundleIntoHashMap(globalRb);
    }



    public NDimensionalMatrixDouble[] balanceZonalData() {
        
        NDimensionalMatrixDouble[] balancedZonalTables = new NDimensionalMatrixDouble[targets[0].length];
        NDimensionalMatrixBalancerDouble mb2 = new NDimensionalMatrixBalancerDouble();
        
        for (int i=0; i < targets[0].length; i++) {
            
            int[] statePumaIndices = halo.getStatePumaIndicesFromZoneIndex( i );
            
            mb2.setSeed( seedTables[statePumaIndices[0]][statePumaIndices[1]] );
            
            mb2.setTarget( new RowVector( targets[0][i] ), 0 );
            mb2.setTarget( new RowVector( targets[1][i] ), 1 );
            
            mb2.balance();

            balancedZonalTables[i] = mb2.getBalancedMatrix();
                
        }
     
        return balancedZonalTables;
        
    }

    

    // get the set of hh attributes need for SPG1 from PUMS files
    public NDimensionalMatrixDouble[][] getSeedTablesFromPUMS () {
        
        double[][][][] seedFrequencyTables = new double[halo.getNumberOfStates()][][][];
        NDimensionalMatrixDouble[][] seedMatrices = new NDimensionalMatrixDouble[halo.getNumberOfStates()][];
        
//        PUMSData pums = new PUMSData ( (String)propertyMap.get("pumsDictionary.fileName"), (String)propertyMap.get("year") );

        
        // get the filenames for PUMS data for each state in the model area
        String propertyName;
        String[] PUMSFILE = new String[halo.getNumberOfStates()];
        for (int i=0; i < PUMSFILE.length; i++) {
            propertyName = "pums" + halo.getStateLabel(i) + ".fileName";
            PUMSFILE[i] = (String)propertyMap.get( propertyName );
        }

        // get the field names and field range values for the categoris on which to balance
        String variable1 = (String)propertyMap.get( "pums.field1.name" );
        String variable2 = (String)propertyMap.get( "pums.field2.name" );
        String variable1RangesString = (String)propertyMap.get( "pums.field1.ranges" );
        int[] variable1Ranges = ResourceUtil.getIntValuesFromString(variable1RangesString);
        String variable2RangesString = (String)propertyMap.get( "pums.field2.ranges" );
        int[] variable2Ranges = ResourceUtil.getIntValuesFromString(variable2RangesString);
        
        // set the PUMS field names for fields to be read
        String[] hhFieldNames = { (String)propertyMap.get( "pums.field1.name" ),
                (String)propertyMap.get( "pums.field2.name" ),
                (String)propertyMap.get( "pums.pumaField.name" ),
                (String)propertyMap.get( "pums.hhWeightField.name" ) };

        
        // now read the PUMS data.
        // read only the hh records residing in pumas which intersect our study area.
        DataDictionary dd = new DataDictionary( (String)propertyMap.get("pumsDictionary.fileName"), (String)propertyMap.get("year") );
        PUMSDataReader dr = new PUMSDataReader();
        
        


        
        // create a HashMap of field names to use based on those specified in properties file
        HashMap fieldNameMap = new HashMap();
        fieldNameMap.put( "pumaName", (String)propertyMap.get( "pums.pumaField.name" ) );
        fieldNameMap.put( "hhWeightName", (String)propertyMap.get( "pums.hhWeightField.name" ) );
        fieldNameMap.put( "variable1Name", variable1 );
        fieldNameMap.put( "variable2Name", variable2 );
        fieldNameMap.put( "variable1Ranges", variable1Ranges );
        fieldNameMap.put( "variable2Ranges", variable2Ranges );
        

        for (int i=0; i < halo.getNumberOfStates(); i++) {
            
            // get the pumaIndex array for the state being read
            int[] pumaSet = halo.getStatePumaIndexArray(i);

            // get the TableDataSet of PUMS household records with the desired fields
            dr.readPumsAttributes( PUMSFILE[i], dd, hhFieldNames, null, pumaSet);
            TableDataSet hhTable = dr.getHhTableDataSet();
            
            seedFrequencyTables[i] = getSeedMatricesForStateByPuma( hhTable, i, fieldNameMap );
            
            seedMatrices[i] = new NDimensionalMatrixDouble[halo.getNumberOfPumas(i)];
            for ( int j=0; j < halo.getNumberOfPumas(i); j++ )
                seedMatrices[i][j] = new NDimensionalMatrixDouble( "stateIndex="+i+",pumaIndex="+j, seedFrequencyTables[i][j] ); 
                
        }
        
        return seedMatrices;
        
    }


    
    private double[][][] getSeedMatricesForStateByPuma (TableDataSet hhTable, int stateIndex, HashMap fieldMap ) {

        int range1 = 0;
        int range2 = 0;

        int[] field1Ranges = (int[])fieldMap.get( "variable1Ranges" );
        int[] field2Ranges = (int[])fieldMap.get( "variable2Ranges" );
        
        int numPumas = halo.getNumberOfPumas(stateIndex);
        
        double[][][] freqTable = new double[numPumas][field1Ranges.length-1][field2Ranges.length-1]; 

       
        
        // go through table rows and count number of weighted hhs in each combination of categories by puma.
        for (int h=1; h < hhTable.getRowCount()+1; h++) {
            
            int puma = (int)hhTable.getValueAt( h, (String)fieldMap.get( "pumaName" ) );
            int hhWeight = (int)hhTable.getValueAt( h, (String)fieldMap.get( "hhWeightName" ) );
            int field1Value = (int)hhTable.getValueAt( h, (String)fieldMap.get( "variable1Name" ) );
            int field2Value = (int)hhTable.getValueAt( h, (String)fieldMap.get( "variable2Name" ) );

            
            int pumaIndex = halo.getPumaIndex( stateIndex, puma );

            
            // fieldRanges should include one more element than the number of ranges,
            // the first element is the absolute min, and the min for the first range
            // the second element is the min for the second range
            // the last is the absolute max, and does not correspond to a range, thus the extra element
            for ( int i=0; i < field1Ranges.length-1; i++ ) {
                if ( field1Value >= field1Ranges[i] && field1Value < field1Ranges[i+1] ) {
                    range1 = i;
                    break;
                }
            }
            
            for ( int i=0; i < field2Ranges.length-1; i++ ) {
                if ( field2Value >= field2Ranges[i] && field2Value < field2Ranges[i+1] ) {
                    range2 = i;
                    break;
                }
            }
            
            freqTable[pumaIndex][range1][range2] += hhWeight;
            
        }
            
        return (freqTable);
        
    }
    
    
    
    //  return a set of balancing targets, 1 target for each category, 1 set of targets for each zone
    private float[][] readBalancingTargets( String fileName, String[] zoneLabels ) {
 
        // read the target data into a TableDataSet, one row for each zonal set of targets
        TableDataSet table = null;
        CSVFileReader reader = new CSVFileReader();
        try {
            table = reader.readFile(new File( fileName ));
        } catch (IOException e) {
            logger.error ( "IOException caught trying to read targets file " + fileName, e );
        }
    
        
        
        // make sure the zone label read in from the targets file matches the order of the zone labels
        // in the input set of zones to be balanced.
        int[] inputZoneLabels = table.getColumnAsInt(1);
        for ( int i=0; i < zoneLabels.length; i++ ) {
            if ( inputZoneLabels[i] != Integer.parseInt(zoneLabels[i]) ) {
                logger.error ( "zone label for i = " + i + "(of " + zoneLabels.length + ", counting from 0) in targets file " + fileName );
                logger.error ( "is out of order with the zone table being balanced.  Zone table zoneLabels[i] = " + zoneLabels[i] + "." );
                logger.error ( "There should be a one-to-one correspondence between zones in the zonal target data files and the" );
                logger.error ( "set of zones for which balancing is being done." );
                logger.error ( "", new Exception() );
            }
        }
        
        
        
        // the targets table has a field for zoneId and a set of fields, one for each target category
        float[][] targetValuesTransposed = new float[table.getColumnCount()-1][]; 
        for (int i=1; i < table.getColumnCount(); i++)
            targetValuesTransposed[i-1] = table.getColumnAsFloat(i+1);
    
        float[][] targetValues = new float[targetValuesTransposed[0].length][targetValuesTransposed.length];
        for (int i=0; i < targetValuesTransposed[0].length; i++)
            for (int j=0; j < targetValuesTransposed.length; j++)
                targetValues[i][j] = targetValuesTransposed[j][i]; 
        
        
        // return the float array of zonal target sets which has been verified to match with the input zones
        return targetValues;
    
    }

    
    
    public void init () {
    
        // set the global random number seed
        SeededRandom.setSeed( 0 );
    
        halo = new PumsGeography();
        halo.setPumaFieldName( (String)globalPropertyMap.get("pumaField.name") );
        halo.setTazFieldName( (String)globalPropertyMap.get("alpha.name") );
        halo.setStateLabelFieldName( (String)globalPropertyMap.get("stateLabelField.name") );
        halo.setStateFipsFieldName( (String)globalPropertyMap.get("stateFipsField.name") );

//        // Get list of alpha2beta file field formats to fields will be either NUMERIC or STRING when read into TableDataSet.
//        String formatString = (String)globalPropertyMap.get("alpha2beta.formats");
//        ArrayList formatList = new ArrayList();
//        StringTokenizer st = new StringTokenizer(formatString, ", |");
//        while (st.hasMoreTokens()) {
//            formatList.add(st.nextElement());
//        }
//        String[] alpha2betaColumnFormats = new String[formatList.size()];
//        for (int i=0; i < alpha2betaColumnFormats.length; i++)
//            alpha2betaColumnFormats[i] = (String)formatList.get(i);


        // read the zonal correspondence file into the halo object
        halo.readZoneIndices ( (String)globalPropertyMap.get("alpha2beta.file"), null );      
        
        
        // read the targets files
        targets = new float[2][][];
        
        String target1FileName = (String)propertyMap.get("field1.target.file");
        String target2FileName = (String)propertyMap.get("field2.target.file");
            
        targets[0] = readBalancingTargets( target1FileName, halo.getZoneLabels() );
        targets[1] = readBalancingTargets( target2FileName, halo.getZoneLabels() );
        
        
        // read the pums data and generate seed tables for each state, puma
        seedTables = getSeedTablesFromPUMS();

    }

    
    
    public void writeOutputFiles ( NDimensionalMatrixDouble[] finalBalancedTable ) {

        String variable1 = (String)propertyMap.get( "pums.field1.name" );
        String variable2 = (String)propertyMap.get( "pums.field2.name" );

        String outputFileName = (String)propertyMap.get("output.file");
        
        PrintWriter outStream = null;

        // open output stream for writing balanced tables results file
        try {
            
            // write csv file header record
            outStream = new PrintWriter (new BufferedWriter( new FileWriter(outputFileName) ) );
            outStream.println ( "zone," + variable1 + "," + variable2 + ",households" );
                

            int[] location = new int[2];
            
            // write hh size/income category descriptions and frequencies by state and puma
            for (int i=0; i < finalBalancedTable.length; i++) {
                int[] shape = finalBalancedTable[i].getShape();
                for (int j=0; j < shape[0]; j++) {
                    for (int k=0; k < shape[1]; k++) {
                        location[0] = j;
                        location[1] = k;
                        outStream.println( halo.getIndexZone(i) + "," + j + "," + k + "," + finalBalancedTable[i].getValue(location) );
                    }
                }
            }
            outStream.close();
        
        }
        catch (IOException e) {
            logger.fatal ("I/O exception balanced table file.", e);
            System.exit(1);
        }
        
    }
    
    
    // the following main() is used to test the methods implemented in this object.
    public static void main (String[] args) {
        
        String propFile = null;
        String globalFile = null;
        
        if ( args[0].indexOf('.') < 0 )
            propFile = args[0];
        else
            propFile = args[0].substring(0,args[0].indexOf('.'));
        
        if ( args[1].indexOf('.') < 0 )
            globalFile = args[1];
        else
            globalFile = args[1].substring(0,args[1].indexOf('.'));
        
        ZonalData2DBalancer test = new ZonalData2DBalancer( propFile, globalFile );

        test.init();
        NDimensionalMatrixDouble[] finalBalancedTable = test.balanceZonalData();
        
        test.writeOutputFiles ( finalBalancedTable );
        
        logger.info( "ZonalData2DBalancer.main() is finished." );
    }

}



