package com.pb.models.ctramp;

import java.io.*;
import java.text.DecimalFormat;
import java.util.*;

import org.apache.log4j.Logger;

import com.pb.common.datafile.*;
import com.pb.common.util.ResourceUtil;

/**
 * Handles building and storing destination choice size variables
 *
 */

public class DestChoiceSize implements Serializable {
	
    private transient Logger logger = Logger.getLogger(DestChoiceSize.class);
    

    public static final String PROPERTIES_DC_SIZE_INPUT      = "UsualWorkAndSchoolLocationChoice.SizeCoefficients.InputFile";
    public static final String PROPERTIES_DC_SIZE_OUTPUT     = "UsualWorkAndSchoolLocationChoice.SizeTerms.OutputFile";
    public static final String PROPERTIES_DC_SHADOW_OUTPUT   = "UsualWorkAndSchoolLocationChoice.ShadowPricing.OutputFile";
    public static final String PROPERTIES_DC_SHADOW_NITER    = "UsualWorkAndSchoolLocationChoice.ShadowPricing.MaximumIterations";

    protected HashMap<String,HashMap<String,Integer>> dcSizePurposeSegmentIndexMap;
    protected HashMap<String,HashMap<String,HashMap<String,Float>>> dcSizeCoeffsByPurposeAndSegmentMap;
    protected String[] dcSizeVariablesList;
    

    // 1st dimension is an index for the set of DC Size variables used in Sample of Alternative choice and destination choice,
    // 2nd dimension is zone number (1,...,numZones), 3rd dimension walk subzone index is 0: no walk %, 1: shrt %, 2: long %.
    protected double[][][] dcSize;
    protected double[][][] originalSize;
    protected double[][][] originalAdjSize;
    protected double[][][] scaledSize;
    protected double[][][] balanceSize;
    protected double[][][] previousSize;
    protected double[][][] shadowPrice;

    protected int maxShadowPriceIterations;

    protected String destChoiceWorkerAdjustmentFileName = "Not yet implemented";
    protected String dcShadowOutputFileName;
    protected String dcSizeTermOutputFileName;

    protected boolean dcSizeCalculated = false;

    protected ModelStructure modelStructure;
    protected TazDataIf tazDataManager;


    protected String[] subZoneNames;
    protected int numSubZones;
    protected int numZones;

    protected int[] areaType;
    protected int[] zoneTableRow;

    protected String projectDirectory;
    protected String tourCategory;

    
    

    public DestChoiceSize( ModelStructure modelStructure, TazDataIf tazDataManager){

        // establish the model structure
        this.modelStructure = modelStructure;
        this.tazDataManager = tazDataManager;

        numZones = tazDataManager.getNumberOfZones();
        numSubZones = tazDataManager.getNumberOfSubZones();
        subZoneNames = tazDataManager.getSubZoneNames();

    }



    public void setupDestChoiceSize( ResourceBundle rb, String projectDirectory, String tourCategory ){

        HashMap<String, String> propertyMap = ResourceUtil.changeResourceBundleIntoHashMap(rb);
        setupDestChoiceSize( propertyMap, projectDirectory, tourCategory );

    }


    public void setupDestChoiceSize( HashMap<String, String> propertyMap, String projectDirectory, String tourCategory ){

        this.projectDirectory = projectDirectory;
        this.tourCategory = tourCategory;

        dcSizeTermOutputFileName = projectDirectory + propertyMap.get( PROPERTIES_DC_SIZE_OUTPUT );

        dcShadowOutputFileName = projectDirectory + propertyMap.get( PROPERTIES_DC_SHADOW_OUTPUT );

        // get the number of shadow price iterations
        try {
            maxShadowPriceIterations = Integer.parseInt( propertyMap.get( PROPERTIES_DC_SHADOW_NITER ) );
        }
        catch (NumberFormatException e) {
            maxShadowPriceIterations = 1;
        }

        // read the dc size coefficients file
        String destChoiceSizeFileName = projectDirectory + propertyMap.get( PROPERTIES_DC_SIZE_INPUT );
        readDcSizeCoeffsArray(destChoiceSizeFileName);

    }


    public boolean getDcSizeCalculated() {
        return dcSizeCalculated;
    }


    public void setDcSizeCalculated( boolean dcSizeCalculatedArg ) {
        dcSizeCalculated = dcSizeCalculatedArg;
    }


    public int getMaxShadowPriceIterations() {
        return maxShadowPriceIterations;
    }


    /**
     * Read the size variable coefficient values from the file whose name is passed in.
     * Store the values for later calculation, and check the consistency between purpose, segment values in the file
     * and those defined in the modelStructure object.  Also check consistency between coefficient field names
     * and zonal table field names.
     * @param dcSizeVariablesFileName is the file name for the destination choice size coefficient values.
     */
    private void readDcSizeCoeffsArray(String dcSizeVariablesFileName){
		
		// read in the csv table
		TableDataSet coeffTable;
		try{

            OLD_CSVFileReader reader = new OLD_CSVFileReader();
            reader.setDelimSet( "," + reader.getDelimSet() );
            coeffTable = reader.readFile(new File( dcSizeVariablesFileName ));
            
        }
        catch(Exception e){
            logger.fatal( String.format( "Exception occurred reading DC Size coefficients data file: %s into TableDataSet object.", dcSizeVariablesFileName ) );
            throw new RuntimeException();
        }
        
        
        // declare a map to get the dcSize[][][] 1st index from the purpose/segment
        dcSizePurposeSegmentIndexMap = new HashMap<String,HashMap<String,Integer>>();
        
        // prepare the coefficients map and purpose/segment lists
        dcSizeCoeffsByPurposeAndSegmentMap = new HashMap<String,HashMap<String,HashMap<String,Float>>>();


        // fetch the purpose and segment field name strings
        String purposeFieldName = modelStructure.getDcSizeCoeffPurposeFieldName();
        String segmentFieldName = modelStructure.getDcSizeCoeffSegmentFieldName();


        // loop through each row, check for consistent variable naming with modelStructure and zonal table, and store the values in the maps.
        String[] columnLabels = coeffTable.getColumnLabels();
        for(int i=0; i < coeffTable.getRowCount(); i++){
        	
        	// set the row number (table data is one-based)
        	int rowNumber = i+1;
        	
        	String purposeString = coeffTable.getStringValueAt(rowNumber, purposeFieldName);
            String segmentString = coeffTable.getStringValueAt(rowNumber, segmentFieldName);

            if ( modelStructure.isValidDcSizePurposeSegment( purposeString, segmentString ) ) {

                // new the map and list to store the coefficients
                HashMap<String,Float> sizeCoeffsByVariableNameMap = new HashMap<String,Float>(columnLabels.length-2);
                dcSizeVariablesList = new String[columnLabels.length-2];

                // loop through the rest of the columns and store the coefficients
                int varCount  = 0;
                for( String fieldName : columnLabels ) {

                    // skip the purpose and segment columns
                    if( fieldName.equalsIgnoreCase(purposeFieldName)) continue;
                    if( fieldName.equalsIgnoreCase(segmentFieldName)) continue;

                    // make sure the field name is also defined in the zonal table
                    if ( ! tazDataManager.isValidZoneTableField(fieldName) ) {
                        logger.error ( String.format("the fieldName: %s, defined in the header row in column: %d, of file: %s,", fieldName, (varCount+2), dcSizeVariablesFileName) );
                        logger.error ( String.format("does not match any of the zonal data table field names defined in the %s object:", tazDataManager.getClass().getName()) );
                        logger.error ( String.format("    %16s", "Taz Data Fields:"));
                        for ( String name : tazDataManager.getZoneDataTableColumnLabels() )
                            logger.error ( String.format("    %s16", name));
                        throw new RuntimeException();
                    }


                    float coeffValue = coeffTable.getValueAt( rowNumber, fieldName );
                    sizeCoeffsByVariableNameMap.put( fieldName, coeffValue );

                    // keep them in an array for later indexing
                    dcSizeVariablesList[varCount++] = fieldName;

                }

                // get the coeffs map for the purpose (or create one), then store a map for segments
                String purpKey = purposeString.toLowerCase();
                String segKey = segmentString.toLowerCase();
                HashMap<String,HashMap<String,Float>> segmentMap = null;
                if ( dcSizeCoeffsByPurposeAndSegmentMap.containsKey(purpKey) )
                    segmentMap = dcSizeCoeffsByPurposeAndSegmentMap.get( purpKey );
                else
                    segmentMap = new HashMap<String,HashMap<String,Float>>();
                segmentMap.put( segKey, sizeCoeffsByVariableNameMap );
                dcSizeCoeffsByPurposeAndSegmentMap.put( purpKey, segmentMap );

                
                // the TableDataSet row id will be the index for the dcSize array calculated.
                HashMap<String,Integer> indexMap = null;
                if ( dcSizePurposeSegmentIndexMap.containsKey(purpKey) )
                    indexMap = dcSizePurposeSegmentIndexMap.get( purpKey );
                else
                    indexMap = new HashMap<String,Integer>();
                indexMap.put( segKey, i );
                
            }
        	
        } // row loop
        
	}
	
	
    public void calculateDcSize() {
        
    	// initialize dcSize array used in DC model
        String[] dcSizeArrayPurposes = modelStructure.getDcSizeArrayPurposeStrings(); 

        // allocate the dcSize array for purposes that match the tourCategory for which size is being calculated.
        dcSize = new double[dcSizeArrayPurposes.length][][];
        int purposeIndexOffset = modelStructure.getDcSizeArrayCategoryIndexOffset(tourCategory);
        int end = purposeIndexOffset + modelStructure.getNumDcSizeArrayCategorySegments(tourCategory);
        for ( int i=purposeIndexOffset; i < end; i++ ) {
            dcSize[i] = new double[numZones+1][numSubZones];
        }

        // loop through the variables used in the size calculation and get the columns from the zonal data table
        float[][] tempVariableTable = new float[dcSizeVariablesList.length][];
        for( int l=0; l < dcSizeVariablesList.length; l++ ) {
            String variableName = dcSizeVariablesList[l];
            tempVariableTable[l] = tazDataManager.getZoneTableFloatColumn( variableName );
        }


        
        // get the dcSize segments for which size is calculated
        String[] dcSizeSegmentPurposes = modelStructure.getDcSizeSegmentStrings();        
        
        // get the offset and number of segments to calculate
        purposeIndexOffset = modelStructure.getDcSizeSegmentCategoryIndexOffset(tourCategory);
        end = purposeIndexOffset + modelStructure.getNumDcSizeSegmentCategorySegments(tourCategory);
        
        // loop through the purpose and segments to create the size terms
    	for( int p=purposeIndexOffset; p < end; p++ ){

    		// get the coefficients map
	    	int underscoreIndex = dcSizeSegmentPurposes[p].indexOf('_');
	        String purposeString = dcSizeSegmentPurposes[p].substring(0,underscoreIndex);
	        String segmentString = dcSizeSegmentPurposes[p].substring(underscoreIndex+1);
	        
	        HashMap<String,HashMap<String,Float>> segmentMap = dcSizeCoeffsByPurposeAndSegmentMap.get( purposeString );
	        if (segmentMap==null) logger.error("Could not find purpose " + purposeString + " in dcSizeCeoffs maps.");
	        
	        HashMap<String,Float> coefficientsMap = segmentMap.get( segmentString );
	        if (coefficientsMap==null) logger.error("Could not find segment " + segmentString 
	        		+ " of purpose " + purposeString + " in dcSizeCeoffs maps.");
	
	        float[] tempCoefficients = new float[dcSizeVariablesList.length];
	        for( int l=0; l < dcSizeVariablesList.length; l++ ) {
	            String variableName = dcSizeVariablesList[l];
	            tempCoefficients[l] = coefficientsMap.get(variableName);
	        }

            //TODO: make sure zone number and tabledata row indices are used correctly and appropriately
            
            //TODO: this is not generic - it's project specific with area type segmentation -- need to resolve this better.

            // if a dc size segment is areatype based, the size is calculated only if the zone is within that area type.
            // otherwise the size is calcualted for every zone.
            if ( isSegmentAreaTypeBased(segmentString) ){
                
                // loop through the zones and sub-zones to compute the size terms
                for( int k=0; k < numZones; k++ ) {

                    int zoneNumber = k + 1;
                    double totalZonalSize = 0.0;

                    
                    // check to see if zone is in the area type for the segment being calculated
                    boolean validSegment = false;
                    if ( segmentString.equalsIgnoreCase( TazDataHandler.AreaType.CBD.name() ) ) {
                        if ( tazDataManager.getZoneIsCbd( zoneNumber ) == 1 )
                            validSegment = true;
                    }
                    else if ( segmentString.equalsIgnoreCase( TazDataHandler.AreaType.URBAN.name() ) ) {
                        if ( tazDataManager.getZoneIsUrban( zoneNumber ) == 1 )
                            validSegment = true;
                    }
                    else if ( segmentString.equalsIgnoreCase( TazDataHandler.AreaType.SUBURBAN.name() ) ) {
                        if ( tazDataManager.getZoneIsSuburban( zoneNumber ) == 1 )
                            validSegment = true;
                    }
                    else if ( segmentString.equalsIgnoreCase( TazDataHandler.AreaType.RURAL.name() ) ) {
                        if ( tazDataManager.getZoneIsRural( zoneNumber ) == 1 )
                            validSegment = true;
                    }
                    
                    // if segment is an area type and zone is not in this area type, zone's size will be 0.
                    if ( validSegment ) {
                        
                        // loop through the variables
                        for(int l=0; l < dcSizeVariablesList.length; l++) {

                            // compute the size term element.
                            // note that field names used in destination choice size coefficients file must
                            // also be found in zonal data file.
                            // tempVariableTable[l] is 0-based indexed
                            float coefficient = tempCoefficients[l];
                            float zonalValue = tempVariableTable[l][k];
                            totalZonalSize += coefficient * zonalValue;

                        } // l - variables in size calculation

                        int index = modelStructure.getDcSizeArrayCategoryIndexOffset( ModelStructure.AT_WORK_CATEGORY ); 
                        
                        // dcSize[p] is 1-based indexed
                        double[] subzoneWalkPercentages = tazDataManager.getZonalWalkPercentagesForTaz( zoneNumber );
                        for( int l=0; l < numSubZones; l++ )
                            dcSize[index][zoneNumber][l] = totalZonalSize * subzoneWalkPercentages[l];

                    }

                } // k (zonal loop)

            }
            else {
                
                // loop through the zones and sub-zones to compute the size terms
                for( int k=0; k < numZones; k++ ) {

                    int zoneNumber = k + 1;
                    double totalZonalSize = 0.0;

                    // loop through the variables
                    for(int l=0; l < dcSizeVariablesList.length; l++) {

                        // compute the size term element.
                        // note that field names used in destination choice size coefficients file must
                        // also be found in zonal data file.
                        // tempVariableTable[l] is 0-based indexed
                        float coefficient = tempCoefficients[l];
                        float zonalValue = tempVariableTable[l][k];
                        totalZonalSize += coefficient * zonalValue;

                    } // l - variables in size calculation

                    // dcSize[p] is 1-based indexed
                    double[] subzoneWalkPercentages = tazDataManager.getZonalWalkPercentagesForTaz( zoneNumber );
                    for( int l=0; l < numSubZones; l++ )
                        dcSize[p][zoneNumber][l] = totalZonalSize * subzoneWalkPercentages[l];

                } // k (zonal loop)

            }
            

    	} // i (purpose loop)
        
        // write a file of calculated size values, before any balancing or adjustments
        purposeIndexOffset = modelStructure.getDcSizeArrayCategoryIndexOffset(tourCategory);
        end = purposeIndexOffset + modelStructure.getNumDcSizeArrayCategorySegments(tourCategory);
        writeZonalDcSizeValues( dcSizeArrayPurposes, purposeIndexOffset, end );
        
    }
    
    private void writeZonalDcSizeValues( String[] dcSizePurposeList, int start, int end ) {
    	
        try {
            
            // create the writer
        	PrintWriter outStream =  new PrintWriter(new BufferedWriter( new FileWriter(dcSizeTermOutputFileName) ) );

            // make the header
        	String header = String.format("%s", "zone,subzone" );
        	
        	// loop through the purpose and segment lists to build the header
            for( int i=0; i < dcSizePurposeList.length; i++ ) {
                String purposeString = dcSizePurposeList[i];
                header += String.format(",%s",purposeString);
            } // i
            outStream.println(header);


            // loop through the zones
        	for( int i=1; i <= numZones; i++ ) {
        		
        	    int rowNumber = i;
        		int zoneNumber = (int) tazDataManager.getTazNumber( rowNumber );
        		
        		// loop through sub zones
        		for( int j=0; j < numSubZones; j++ ) {

        			String indexRecord = String.format("%d,%s", zoneNumber, subZoneNames[j]);
        			String dataRecord = "";
        			
        			// loop through the purposes and segments within purposes and print the size terms
                    for( int k=start; k < end; k++ )
                        dataRecord += String.format(",%.5f",dcSize[k][zoneNumber][j]);

                    // write the line
        			outStream.println(indexRecord+dataRecord);
        			
        		} // j (sub zone loop)
		
        	} // i (zone loop)
        	
        	outStream.close();

        }
        catch (IOException e) {
            logger.fatal("IO Exception writing calcualted DC Size values to file: " + dcSizeTermOutputFileName );
            throw new RuntimeException(e);
        }
        
    }


    

    /**
     * Scale the destination choice size values so that the total modeled destinations by purpose and segment match the total origins.
     * total Origin/Destination constraining usuallu done for home oriented mandatory tours, e.g. work university, school.
     * This method also has the capability to read a file of destination size adjustments and apply them during the balancing procedure.
     * This capability was used in the Morpc model and was transferred to the Baylanta project, but may or may not be used.
     * 
     * @param originsByHomeZone - total long term choice origin locations (i.e. number of workers, university students, or school age students)
     * in residence zone, subzone, by purpose, segment.
     *
     */
    public void balanceSizeVariables( int[][][] originsByHomeZone, String[] purposeList, int start, int end ) {
        
        // store the original size variable values determined when ZonalDataManager object was created.
        // set the initial sizeBalance values to the original size variable values.
        
        originalSize = duplicateDouble3DArray ( dcSize, start, end );
        balanceSize = duplicateDouble3DArray ( dcSize, start, end );
        
        // create the shadow price array
        shadowPrice = new double[purposeList.length][][];
        
        // create the total origin locations array 
        double[] totalOriginLocations = new double[purposeList.length];
        
        // store the dc size terms with no overrides
        double[] totalDcSizeNoOverrides = new double[purposeList.length];
        
        // store the dc size terms with overrides
        double[] totalDcSizeWithOverrides = new double[purposeList.length];
        
        for(int i=0;i<purposeList.length;++i){
        	
        	String purposeString = purposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 

    		// complete the array sizing
    		shadowPrice[i] = new double[numZones+1][numSubZones];

    		// loop through the segments
            for( int k=1; k <= numZones; k++ ) {
                for( int l=0; l < numSubZones; l++ ) {

                    // initialize shadow price with 1.0
                    shadowPrice[i][k][l] = 1.0;

                    // sum the total origins
                    totalOriginLocations[i] += originsByHomeZone[i][k][l];

                    // initialize the overrides arrays with the original size terms
                    totalDcSizeNoOverrides[i] += originalSize[dcSizeArrayIndex][k][l];


                } // l (sub-zone)
            } // k (zone)

            totalDcSizeWithOverrides[i] = totalDcSizeNoOverrides[i];
    			
        } // i (purpose)
        
          
        // log a report of total origin locations by purpose and segment
        logger.info("");
        logger.info("total origin locations by purpose and segment before any balancing, destination size adjustments, or shadow price scaling:");
        double purposeSum = 0.0;
        for(int i=0;i<purposeList.length;++i){
        	String purposeString = purposeList[i];
            purposeSum += totalOriginLocations[i];
            logger.info( String.format("    %-24s:  %10.1f", purposeString, totalOriginLocations[i]) );
    	} // i
        logger.info( String.format("    %-24s:  %10.1f", "Total", purposeSum) );
        logger.info( "" );
        


        // log a report of total destination choice size calculated by puprpose, segment
        logger.info("");
        logger.info("total destination choice size by purpose, segment before any balancing, destination choice size adjustments, or shadow price scaling:");
        purposeSum = 0.0;
        for( int i=0; i < purposeList.length; i++ ) {
        	String purposeString = purposeList[i];
            purposeSum += totalDcSizeNoOverrides[i];
            logger.info( String.format("    %-24s:  %10.1f", purposeString, totalDcSizeNoOverrides[i]) );
        }
        logger.info( String.format("    %-24s:  %10.1f", "Total", purposeSum) );
        logger.info( "" );



        // apply the adjustments specified in a file, if any, prior to balancing to constrain total origin and destination locations.
        // the array returned is used to determine if an override was made which affects the way the balancing calculations are made.
        boolean[][][] subzoneOverRides = dcSizeAdjustmentsAndOverrides();


        // save original adjusted size variable arrays prior to balancing - used in reporting size variable calculations to output files.
        originalAdjSize = duplicateDouble3DArray ( balanceSize, start, end );

          
        scaledSize = new double[balanceSize.length][][];
        double tot=0.0;
        for(int i=0;i<purposeList.length;++i){
        	
        	String purposeString = purposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 

            // Balance destination choice size variables to equal total origin locations by purpose and segment.
            // If a subzone belongs to a zone that had an adjustment over-ride, skip scaling values for the subzone,
            // as the adjusted size value was set in the adjustment procedure, and the origin locations adjusted accordingly as well.
            // The scaledSize calculated is what is adjusted by shadow pricing adjustments, and dcSize, the array referenced
            // by UEC DMUs is a duplicate copy of this array after the shadow pricing calculations are made.
            scaledSize[i] = duplicateDouble2DArray ( balanceSize[dcSizeArrayIndex] );

    		// loop through the segments
            tot=0.0;
            for(int k=1;k<=numZones;++k){
                for(int l=0;l<numSubZones;++l){

                    // scale values for size where an override was not specified for the subzone and purpose.  Adjusted values are already set.
                    if ( subzoneOverRides == null || subzoneOverRides[i][k][l] == false ) {
                        if (totalDcSizeNoOverrides[i] > 0.0)
                            scaledSize[i][k][l] = ( balanceSize[dcSizeArrayIndex][k][l] * totalOriginLocations[i] ) / totalDcSizeNoOverrides[i];
                        else
                            scaledSize[i][k][l] = 0.0f;
                    }
                    
                    tot += scaledSize[i][k][l];

                }
            }
        }

        //TODO: create a new class for destination choice size adjustments and define input file format
        /**
         *
         * I probably want to make the destination choice size adjustments procedure a separate class and create a method
         * that will produce the following log report that can be called from here.
         *
         *
        if ( adjustmentSet.size() > 0 ) {
            
            // log out final adjusted and scaled size values for subzones affected by specified adjustments
            logger.info( "" );
            logger.info( "Size variables for subzones with adjustments specified, after adjustments, after scaling" );
            String logString = String.format("%13s %13s", "Zone", "Subzone" );
            for ( int i=1; i < Structure.WorkDcSegments.values().length; i++ )
                logString += String.format(" %13s", Structure.WorkDcSegments.values()[i].name() );
            logger.info( logString );
            boolean[][] subzoneLogged = new boolean[numZones+1][numSubZones];
            Iterator it = adjustmentSet.iterator();
            while ( it.hasNext() ) {
                Adjustment adj = (Adjustment)it.next();
                for (int w=0; w < numSubZones; w++) {
                    if ( subzoneLogged[adj.zone][w] == false ) {
                        logString = String.format("%13d %13d", adj.zone, w );
                        for ( int k=1; k < Structure.WorkDcSegments.values().length; k++ )
                            logString += String.format(" %13.2f", scaledSize[k][adj.zone][w] );
                        logger.info( logString );
        
                        subzoneLogged[adj.zone][w] = true;
                    }
                }
            }

        }
         */

        
        
        
        // set destination choice size variables for the first iteration of shadow pricing to calculated scaled values,
        // one purpose at a time, for purposes that will have shadow pricing adjustments.
        // non-mandatory type size values aren't scaled (not total origin/destination constrained).

        //TODO: make a method in StructureTourpose to return only purposes for which shadow pricing is applied.
        // for now, all purposes have shadow pricing
        for(int i=0;i<purposeList.length;++i) {
            String purposeString = purposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
            dcSize[dcSizeArrayIndex] = duplicateDouble2DArray (scaledSize[i]);
        }
        
        // sum scaled destination size values by segment for reporting
        double[] sumScaled = new double[purposeList.length];
        for( int i=0; i < purposeList.length; i++ ) {
            String purposeString = purposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
            for( int j=1; j <= numZones; j++ ) {
                for( int k=0; k < numSubZones; k++ ) {
                    sumScaled[i] +=  scaledSize[i][j][k];
                }
            }
        }

        // log a report of total destination locations by purpose and segment
        logger.info("");
        logger.info("total destination choice size by purpose, segment after destination choice size adjustments, after shadow price scaling:");
        purposeSum = 0.0;
        for(int i=0;i<purposeList.length;++i){
        	String purposeString = purposeList[i];
            purposeSum += sumScaled[i];
            logger.info( String.format("    %-24s:  %10.1f", purposeString, sumScaled[i]) );
        }
        logger.info( String.format("    %-24s:  %10.1f", "Total", purposeSum) );
        logger.info( "" );

        // save scaled size variables used in shadow price adjustmnents for reporting to output file
        previousSize = new double[purposeList.length][][];
        for(int i=0;i<purposeList.length;++i)
            previousSize[i] = duplicateDouble2DArray ( scaledSize[i] );

    }
   
    /**
     * As per the Morpc model, a file of specified destination choice size adjustments and overrides can be read in and applied
     * during the balancing stage.  The adjustments are used to interject specific knowledge about zones or make
     * corrections to specific purpose, segment, zone, subzone values calculated by the generic destination choice size model.
     *
     * If the adjustment spcification filename is not defined in the propoerties file, no adjustments are made.
     */
    private boolean[][][] dcSizeAdjustmentsAndOverrides() {

        // get an ArrayList of Adjustment objects and apply adjustments prior to scaling calculations
        // make an array of length of zones that indicate if over-ride adjustments have been defined for each zone
        boolean[][][] subzoneOverRides = null;

        /*******
         *
         * The code in this comment out section needs to be implemented correctly for the file format yet to be specified
         * for this project.  The Morpc format may work, or may be modified, and this code needs to be implemented accordingly.
         *
         * As long as this code is commented out, no attarction size adjustments may be made.
         *
         *
        ArrayList adjustmentSet = dcSizeAdjustmentsAndOverrides();

        if ( adjustmentSet.size() > 0 ) {

            // log a report of total destination choice size calculated by puprpose, segment - start by logging a header for the report,
            // then print lines of values of the adjustments
            logger.info("");
            logger.info( "Size Variable Adjustments Specified" );
            String logString = String.format("%13s %13s %13s %13s", "Purpose", "Segment", "Zone", "Code" );
            for ( Structure.TourPurpose purpose : Structure.TourPurpose.values() ) {
                Structure.Segment[] segments = purpose.getSegments();
                for ( int s=0; s < segments.length; s++ )
                    logString += String.format(" %13s", segments[s].getName() );
                logger.info( logString );

                Iterator it = adjustmentSet.iterator();
                while ( it.hasNext() ) {
                    Adjustment adj = (Adjustment)it.next();

                    logString = String.format("%-13s %13d %13s    ", purpose.name(), adj.zone, adj.code);
                    for (int i=0; i < adj.adjustment.length; i++)
                        logString += String.format(" %13.2f", adj.adjustment[i] );
                    logger.info( logString );

                }

            }



            // log out original size values for subzones affected by specified adjustments
            logger.info( "" );
            logger.info( "Size variables for subzones with adjustments specified, before adjustments, before scaling" );
            logString = String.format("%13s %13s", "Zone", "Subzone" );
            for ( int i=1; i < Structure.WorkDcSegments.values().length; i++ )
                logString += String.format(" %13s", Structure.WorkDcSegments.values()[i].name() );
            logger.info( logString );
            boolean[][] subzoneLogged = new boolean[numZones+1][numSubZones];
            it = adjustmentSet.iterator();
            while ( it.hasNext() ) {
                Adjustment adj = (Adjustment)it.next();
                for (int w=0; w < numSubZones; w++) {
                    if ( subzoneLogged[adj.zone][w] == false ) {
                        logString = String.format("%13d %13d", adj.zone, w );
                        for ( int k=1; k < Structure.WorkDcSegments.values().length; k++ )
                            logString += String.format(" %13.2f", originalSize[k][adj.zone][w] );
                        logger.info( logString );

                        subzoneLogged[adj.zone][w] = true;
                    }
                }
            }



            subzoneOverRides = new boolean[Structure.WorkDcSegments.values().length][numZones+1][numSubZones];

            // apply adjustments
            it = adjustmentSet.iterator();
            while ( it.hasNext() ) {
                Adjustment adj = (Adjustment)it.next();
                applySizeVariableAdjustments( adj, originsByHomeZone, totalDcSizeNoOverrides, totalDcSizeWithOverrides );

                if ( adj.code.equalsIgnoreCase("O") ) {
                    for (int w = 0; w < numSubZones; w++) {
                        for (int p=0; p < adj.adjustment.length; p++) {
                            if ( adj.adjustment[p] != 0.0 ) {
                                subzoneOverRides[p+1][adj.zone][w] = true;
                            }
                        }
                    }
                }

            }


            // log out adjusted, but un-scaled size values for subzones affected by specified adjustments
            logger.info( "" );
            logger.info( "Size variables for subzones with adjustments specified, after adjustments, before scaling" );
            logString = String.format("%13s %13s", "Zone", "Subzone" );
            for ( int i=1; i < Structure.WorkDcSegments.values().length; i++ )
                logString += String.format(" %13s", Structure.WorkDcSegments.values()[i].name() );
            logger.info( logString );
            Arrays.fill(subzoneLogged, false);
            it = adjustmentSet.iterator();
            while ( it.hasNext() ) {
                Adjustment adj = (Adjustment)it.next();
                for (int w=0; w < numSubZones; w++) {
                    if ( subzoneLogged[adj.zone][w] == false ) {
                        logString = String.format("%13d %13d", adj.zone, w );
                        for ( int k=1; k < Structure.WorkDcSegments.values().length; k++ )
                            logString += String.format(" %13.2f", balanceSize[k][adj.zone][w] );
                        logger.info( logString );

                        subzoneLogged[adj.zone][w] = true;
                    }
                }
            }



        }

        **************/


        return subzoneOverRides;

    }


    private ArrayList<Adjustment> getDestinationChoiceSizeAdjustments() {
        
        /* define a set of adjustments to make, for testing purposes
        
        // create an Adjustment object for a zone - (multiply, add, overRide, zone)
        // for a worker with segments - (LO, MED, HI, VHI, PT).
        // These are read in from a file in production runs.
        
        // put adjustment objects in an ArrayList to return 
        ArrayList adjustmentSet = new ArrayList();
        
        double[] testAdj1 = { 0.0, 2.0, 0.0, 0.0, 0.0 };
        double[] testAdj2 = { 0.0, 75.0, 0.0, 0.0, 50.0 };
        double[] testAdj3 = { 0.0, 0.0, 0.0, 1100.0, 0.0 };
        
        adjustmentSet.add( new Adjustment( 800, "M", testAdj1 ) );
        adjustmentSet.add( new Adjustment( 800, "A", testAdj2 ) );
        adjustmentSet.add( new Adjustment( 300, "O", testAdj3 ) );
        
        end of code to define testing adjustments  */
        
        
        ArrayList<Adjustment> adjustmentSet = readAdjustmentsFile();
        return adjustmentSet;
        
    }
    
    
    private ArrayList<Adjustment> readAdjustmentsFile () {
        
        if(destChoiceWorkerAdjustmentFileName.equalsIgnoreCase("Not yet implemented")) 
        	return new ArrayList<Adjustment>();
        
        // put adjustment objects in an ArrayList to return 
        ArrayList<Adjustment> adjustmentSet = new ArrayList<Adjustment>();
        TableDataSet table = null;
        
        try {
            CSVFileReader reader = new CSVFileReader();
            table = reader.readFile(new File(destChoiceWorkerAdjustmentFileName));
        }
        catch (IOException e) {
            logger.error ( "exception thrown reading destination choice adjustments file: " + destChoiceWorkerAdjustmentFileName, e );
        }
        
        for (int row=1; row <= table.getRowCount(); row++) {
            String[] rowStringValues = table.getRowValuesAsString(row);
            
            int zone = Integer.parseInt(rowStringValues[0]);
            String code = rowStringValues[1].toUpperCase();

            double[] values = new double[rowStringValues.length-2];
            for (int j=2; j < rowStringValues.length; j++)
                values[j-2] = Double.parseDouble(rowStringValues[j]);

            adjustmentSet.add( new Adjustment( zone, code, values ) );
            
        }
        
        return adjustmentSet;
    }



    private void applySizeVariableAdjustments( Adjustment adj, double[][][] originsByHomeZone, double[] totalDcSizeNoOverrides, double[] totalDcSizeWithOverrides ) {

        //TODO: need to implement this in new class for destination choice adjustments
        /**
         *

        // make adjustments as specified
        for (int w = 0; w < numSubZones; w++) {

            for ( int p=0; p < adj.adjustment.length; p++ ) {
                
                // it is assumed that only non-zero adjustment values will be indications of an adjustment to be made
                if ( adj.adjustment[p] == 0.0 )
                    continue;
                
                double origValue = balanceSize[p+1][adj.zone][w];
                double adjValue = origValue;
                
                
                // apply adjustments and save adjusted size value for the specific purpose.
                // scaling for zones with O adjustments will be based on total Ps and As without the over-rides.
                // scaling for zones with M or A adjustments will be based on Ps and As that include those adjustments
                
                // if over-ride value, ignore any multiply and/or add values also specified:
                if ( adj.code.equalsIgnoreCase("O") ) {
                    
                    // get over-ride value for this subzone
                    adjValue = zonalWalkPctArray[w][adj.zone]*adj.adjustment[p];

                    originsByHomeZone[p+1][adj.zone][w] -= adjValue;
                    totalDcSizeNoOverrides[p+1] -= origValue;
                    totalDcSizeWithOverrides[p+1] += ( adjValue - origValue );

                }
                else {
                    // otherwise, apply multiply and/or add:

                    if ( adj.code.equalsIgnoreCase("M") )
                        adjValue *= adj.adjustment[p];
                    if ( adj.code.equalsIgnoreCase("A") )
                        adjValue += zonalWalkPctArray[w][adj.zone]*adj.adjustment[p];

                    //  adjust destination choice size and origin location totals for mandatory types by the adjustment increment; don't need to adjust for non-mandatory as no scaling is done.
                    totalDcSizeNoOverrides[p+1] += ( adjValue - origValue );
                    totalDcSizeWithOverrides[p+1] += ( adjValue - origValue );

                }

                
                
                // apply adjusted values to size variable arrays for specific purpose
                balanceSize[p+1][adj.zone][w] = adjValue;
            
            }

        }
        
         */

    }
    
    
    
    
    public int getDcSizeArrayPurposeIndex(String purposeString){
        int index = -1;
        try {
            if ( purposeString.indexOf('_') < 0 )
                purposeString = purposeString.toLowerCase() + "_" + purposeString.toLowerCase();
            index = modelStructure.getDcSizeArrayPurposeIndex( purposeString );
        }
        catch ( Exception e ) {
            logger.fatal("Purpose " + purposeString + " is not defined in Destination Choice Size Coefficients file.", e);
            throw new RuntimeException();
        }
        return index;
    }
    
    
    public double getDcSize( int index, int zone, int walkSubzone){
    	return dcSize[index][zone][walkSubzone];
    }
    
    
    public void updateSizeVariables(String[] tourPurposeList, int start, int end) {
        
        // only size variables for mandatory types are adjusted by shadow prices

        //TODO: make a method in StructureTourpose to return only purposes for which shadow pricing is applied.
        // for now, all purposes have shadow pricing
    	for( int i=0; i < tourPurposeList.length; i++ ) {
            String purposeString = tourPurposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
            for(int k=1; k <= numZones; k++ ) {
                for( int l=0; l < numSubZones; l++ ) {
                    dcSize[dcSizeArrayIndex][k][l] = scaledSize[i][k][l] * shadowPrice[i][k][l];
                    if ( dcSize[dcSizeArrayIndex][k][l] < 0.0f )
                        dcSize[dcSizeArrayIndex][k][l] = 0.0f;
                }
            }
        }

    }
    
    

    public void updateShadowPrices( double[][][] modeledDestinationLocationsByDestZone, String[] tourPurposeList ) {

        // only size variables for mandatory types are adjusted by shadow prices

        //TODO: make a method in StructureTourpose to return only purposes for which shadow pricing is applied.
        // for now, all purposes have shadow pricing
    	for( int i=0; i < tourPurposeList.length; i++) {
//            String purposeString = tourPurposeList[i];
//            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
//            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
            for( int k=1; k <=numZones; k++ ) {
                for( int l=0; l < numSubZones; l++ ) {
                    if ( modeledDestinationLocationsByDestZone[i][k][l] > 0 )
                        shadowPrice[i][k][l] *= ( scaledSize[i][k][l] / modeledDestinationLocationsByDestZone[i][k][l] );
//                    else
//                        shadowPrice[i][k][l] *= scaledSize[i][k][l];
                }
            }
        }
    }

 
    
    public void reportMaxDiff( int iteration, double[][][] modeledDestinationLocationsByDestZone, String[] tourPurposeList ) {


        double[] maxSize = { 10, 100, 1000, Double.MAX_VALUE };
        double[] maxDeltas = { 0.05, 0.10, 0.25, 0.50, 1.0, Double.MAX_VALUE };

        int[] nObs = new int[maxSize.length];
        double[] sse = new double[maxSize.length];
        double[] sumObs = new double[maxSize.length];
        
        
        logger.info( "Shadow Price Iteration " + iteration );
        
        double minRange = 0.0;
        for ( int r=0; r < maxSize.length; r++ ) {
            
            logger.info( String.format( "Frequency of chosen zone,subzone locations with non-zero DC Size < %s by range of relative error", (maxSize[r]<1000000 ? String.format("%.1f", maxSize[r]) : "+Inf") ) );
            logger.info( String.format( "%-24s %15s %15s %15s %15s %15s %15s %15s %8s", "purpose", "0 DCs", "< 5%", "< 10%", "< 25%", "< 50%", "< 100%", "100% +", "Total" ) );

            int tot = 0;
            int[] tots = new int[maxDeltas.length+1];
            String logRecord = "";
            for( int i=0; i < tourPurposeList.length; i++ ) {

                //String purposeString = tourPurposeList[i];
                //int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
                //int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
                
                tot = 0;
                int[] freqs = new int[maxDeltas.length+1];
                int nonZeroSizeLocs = 0;
                for( int k=1; k <= numZones; k++ ) {
                    for( int l=0; l < numSubZones; l++ ) {

                        if ( scaledSize[i][k][l] > minRange && scaledSize[i][k][l] <= maxSize[r] ) {

                            nonZeroSizeLocs++;
                            
                            if ( modeledDestinationLocationsByDestZone[i][k][l] == 0.0 ) {
                                // store the number of DC alternatives where DC Size > 0, but alternative was not chosen.
                                // relative error measure is not meaningful for this case, so report number of cases separately.
                                freqs[0] ++;

                                // calculations for %RMSE
                                sse[r] += scaledSize[i][k][l]*scaledSize[i][k][l]; 
                            }
                            else {
                                
                                double relDiff = Math.abs( scaledSize[i][k][l] - modeledDestinationLocationsByDestZone[i][k][l] ) / scaledSize[i][k][l];
                                for ( int j=0; j < maxDeltas.length; j++ ) {
                                    if ( relDiff < maxDeltas[j] ) {
                                        // store number of DC alternatives chosen where DC Size > 0, by relative error range.
                                        freqs[j+1]++;
                                        break;
                                    }
                                }

                                // calculations for %RMSE
                                sse[r] += relDiff*relDiff; 
                            }
                            
                            // calculations for %RMSE
                            sumObs[r] += scaledSize[i][k][l]; 
                            nObs[r]++;

                        }
                    }
                }

                for ( int k=0; k < freqs.length; k++ ) {
                    tots[k] += freqs[k];
                    tot += freqs[k];
                }

                logRecord = String.format( "%-24s", tourPurposeList[i] );

                for ( int k=0; k < freqs.length; k++ ) {
                    float pct = 0.0f;
                    if ( tot > 0 )
                        pct = (float)(100.0*freqs[k]/tot);
                    logRecord += String.format( " %6d (%5.1f%%)", freqs[k], pct );
                }

                logRecord += String.format( " %8d", tot );
                logger.info( logRecord );

            }


            tot = 0;
            for ( int k=0; k < tots.length; k++ ) {
                tot += tots[k];
            }

            logRecord = String.format( "%-24s", "Total" );
            String underline = String.format( "------------------------" );

            for ( int k=0; k < tots.length; k++ ) {
                float pct = 0.0f;
                if ( tot > 0 )
                    pct = (float)(100.0*tots[k]/tot);
                logRecord += String.format( " %6d (%5.1f%%)", tots[k], pct );
                underline += String.format( "----------------" );
            }

            logRecord += String.format( " %8d", tot );
            underline += String.format( "---------" );

            logger.info( underline );
            logger.info( logRecord );
            
            
            double rmse = -1.0;
            if ( nObs[r] > 1 )
                rmse = 100.0 * ( Math.sqrt( sse[r]/(nObs[r] - 1) ) / ( sumObs[r]/nObs[r] ) );
                
            logger.info( "%RMSE = " + ( rmse < 0 ? "N/A, no observations" : String.format("%.1f, with mean %.1f, for %d observations.", rmse, ( sumObs[r]/nObs[r] ), nObs[r]) ) );

            logger.info( "" );

            minRange = maxSize[r];
            
        }

        logger.info( "" );
        logger.info( "" );

    }
    

    
    public void updateShadowPricingInfo( int iteration, int[][][] originsByHomeZone, double[][][] modeledDestinationLocationsByDestZone, String[] tourPurposeList, int start, int end ) {
        
        
        ArrayList<String> tableHeadings = new ArrayList<String>();
        tableHeadings.add("alt");
        tableHeadings.add("zone");
        tableHeadings.add("subzone");


        for( int i=0; i < tourPurposeList.length; i++ ){
            String purposeString = tourPurposeList[i];
            tableHeadings.add( String.format("%s_origins", purposeString) );
            tableHeadings.add( String.format("%s_sizeOriginal", purposeString) );
            tableHeadings.add( String.format("%s_sizeAdjOriginal", purposeString) );
            tableHeadings.add( String.format("%s_sizeScaled", purposeString) );
            tableHeadings.add( String.format("%s_sizePrevious", purposeString) );
            tableHeadings.add( String.format("%s_modeledDests", purposeString) );
            tableHeadings.add( String.format("%s_sizeFinal", purposeString) );
            tableHeadings.add( String.format("%s_shadowPrices", purposeString) );
        }

        // define a TableDataSet for use in writing output file
        float[][] tableData = new float[numZones*numSubZones+1][tableHeadings.size()];
   
        int alt = 1;
        for ( int i=1; i <= numZones; i++ ) {
            for ( int j=0; j < numSubZones; j++ ) {
                
                tableData[alt][0] = alt;
                tableData[alt][1] = i;
                tableData[alt][2] = j;

                int index = 3;
                
                for( int p=0; p < tourPurposeList.length; p++ ){
                    String purposeString = tourPurposeList[p];
                    int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
                    int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
                    
                    tableData[alt][index++] = (float)originsByHomeZone[p][i][j];
                    tableData[alt][index++] = (float)originalSize[dcSizeArrayIndex][i][j];
                    tableData[alt][index++] = (float)originalAdjSize[dcSizeArrayIndex][i][j];
                    tableData[alt][index++] = (float)scaledSize[p][i][j];
                    tableData[alt][index++] = (float)previousSize[p][i][j];
                    tableData[alt][index++] = (float)modeledDestinationLocationsByDestZone[p][i][j];
                    tableData[alt][index++] = (float)dcSize[dcSizeArrayIndex][i][j];
                    tableData[alt][index++] = (float)shadowPrice[p][i][j];
                }
                alt++;
                
            }

        }

        TableDataSet outputTable = TableDataSet.create(tableData, tableHeadings);

        // write outputTable to new output file
        try {
            String newFilename = this.dcShadowOutputFileName.replaceFirst(".csv", "_" + iteration + ".csv");
            CSVFileWriter writer = new CSVFileWriter();
            writer.writeFile(outputTable, new File(newFilename), new DecimalFormat("#.000000000000"));
            //writer.writeFile( outputTable, new File(newFilename) );
        }
        catch (IOException e) {
            throw new RuntimeException(e);
        }

        
        // save scaled size variables used in shadow price adjustmnents for reporting to output file
        for(int i=0;i<tourPurposeList.length;++i) {
            String purposeString = tourPurposeList[i];
            int dcModelIndex = modelStructure.getDcModelPurposeIndex(purposeString);
            int dcSizeArrayIndex = modelStructure.getDcSizeArrayIndexFromDcModelIndex(dcModelIndex); 
            previousSize[i] = duplicateDouble2DArray ( dcSize[dcSizeArrayIndex] );
        }
        
    }

    
    
    public void restoreShadowPricingInfo( String fileName ) {
        
        OLD_CSVFileReader reader = new OLD_CSVFileReader(); 
        
        TableDataSet tds = null;
        try {
            tds = reader.readFileAsDouble( new File(fileName) );
        } catch (IOException e) {
            logger.error( "exception reading saved shadow price file: " + fileName + " from previous model run." , e );
        }
        
        // the following are based on format used to write the shadow pricing file
        // first three columns are indices: ALT, ZONE, SUBZONE.
        int columnIndex = 3;
        int numberOfColumnsPerPurpose = 8;
        int scaledSizeColumnOffset = 3;
        int previousSizeColumnOffset = 4;
        int finalSizeColumnOffset = 6;
        int finalShadowPriceOffset = 7;

        String[] tourPurposeList = modelStructure.getDcModelPurposeList( ModelStructure.MANDATORY_CATEGORY );
        
        for( int i=0; i < tourPurposeList.length; i++ ){
            
            // first restore the scaled size values; getColumnAsFloat(column) takes a 1s based column value
            int column = columnIndex + i*numberOfColumnsPerPurpose + scaledSizeColumnOffset + 1;
            double[] columnData = tds.getColumnAsDoubleFromDouble(column);
            int k = 1;
            for ( int z=1; z <= numZones; z++ ) {
                for ( int sz=0; sz < numSubZones; sz++ ) {
                    scaledSize[i][z][sz] = columnData[k];
                    k++;
                }
            }
            
            // next restore the final size values
            column = columnIndex + i*numberOfColumnsPerPurpose + finalSizeColumnOffset + 1;
            columnData = tds.getColumnAsDoubleFromDouble(column);
            k = 1;
            for ( int z=1; z <= numZones; z++ ) {
                for ( int sz=0; sz < numSubZones; sz++ ) {
                    dcSize[i][z][sz] = columnData[k];
                    k++;
                }
            }
            
            // next restore the previous size values
            column = columnIndex + i*numberOfColumnsPerPurpose + previousSizeColumnOffset + 1;
            columnData = tds.getColumnAsDoubleFromDouble(column);
            k = 1;
            for ( int z=1; z <= numZones; z++ ) {
                for ( int sz=0; sz < numSubZones; sz++ ) {
                    previousSize[i][z][sz] = columnData[k];
                    k++;
                }
            }
            
            // finally restore the final shadow price values
            column = columnIndex + i*numberOfColumnsPerPurpose + finalShadowPriceOffset + 1;
            columnData = tds.getColumnAsDoubleFromDouble(column);
            k = 1;
            for ( int z=1; z <= numZones; z++ ) {
                for ( int sz=0; sz < numSubZones; sz++ ) {
                    shadowPrice[i][z][sz] = columnData[k];
                    k++;
                }
            }
            
        }

    }

    
    
    private boolean isSegmentAreaTypeBased( String segment ) {
        boolean returnValue = false;
        for ( String atSeg : ModelStructure.DC_SIZE_AREA_TYPE_BASED_SEGMENTS ) {
            if ( atSeg.equalsIgnoreCase( segment ) ) { 
                  returnValue = true; 
                  break;
            }
        }
        return returnValue;
    }

    /**
     * Create a new double[][][], dimension it exactly as the argument array, and copy the element values
     * from the argument array to the new one.
     *
     * @param in a 3-dimensional double array to be duplicated
     * @return an exact duplicate of the argument array
     */
    private double[][][] duplicateDouble3DArray ( double[][][] in, int start, int end ) {
        double[][][] out = new double[in.length][][];
        for ( int s=start; s < end; s++ ) {
            out[s] = new double[in[s].length][];
            for ( int i=0; i < in[s].length; i++ ) {
                out[s][i] = new double[in[s][i].length];
                for ( int j=0; j < in[s][i].length; j++ ) {
                    out[s][i][j] = in[s][i][j];
                }
            }
        }
        return out;
    }



    /**
     * Create a new double[][], dimension it exactly as the argument array, and copy the element values
     * from the argument array to the new one.
     *
     * @param in a 2-dimensional double array to be duplicated
     * @return an exact duplicate of the argument array
     */
    private double[][] duplicateDouble2DArray ( double[][] in ) {
        double[][] out = new double[in.length][];
        for ( int i=0; i < in.length; i++ ) {
            out[i] = new double[in[i].length];
            for ( int j=0; j < in[i].length; j++ ) {
                out[i][j] = in[i][j];
            }
        }
        return out;
    }



    // Inner class to define data structure for size variable adjustment data
    class Adjustment {
        int zone;               // taz for which adjustment should be made
        String code;            // adjustment code - M(multiply), A(add) or O(override)
        double[] adjustment;    // adjustment values
        Adjustment( int zone, String code, double[] adj ) {
            this.zone = zone;
            this.code = code;
            this.adjustment = adj;
        }
    }
    
    

}
