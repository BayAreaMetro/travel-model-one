package com.pb.models.ctramp;

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.CSVFileReader;
import com.pb.models.ctramp.jppf.CtrampApplication;

import java.util.*;
import java.io.File;
import java.io.Serializable;

import org.apache.log4j.Logger;

/**
 * @author crf <br/>
 *         Started: Nov 15, 2008 4:17:57 PM
 */
public class StopDestChoiceSize implements Serializable {
    
    private transient Logger logger = Logger.getLogger(StopDestChoiceSize.class);

    public static final String PROPERTIES_STOP_DC_SIZE_INPUT = "StopDestinationChoice.SizeCoefficients.InputFile";


    private final Map<String,Map<String,Map<Integer,Double>>> sizeMap; //map of purpose,purpose segment, and zone/subzone to size
    private final TazDataIf tazDataManager;
    private final ModelStructure modelStructure;
    private Map<String,Map<String,Map<String,Double>>> sizeCoefficients;

    public StopDestChoiceSize( HashMap<String, String> propertyMap, TazDataIf tazDataManager, ModelStructure modelStructure ) {
        this.tazDataManager = tazDataManager;
        this.modelStructure = modelStructure;
        sizeMap = new HashMap<String,Map<String,Map<Integer,Double>>>();
        
        String projectDirectory = propertyMap.get( CtrampApplication.PROPERTIES_PROJECT_DIRECTORY );
        String coeffsFileName = propertyMap.get( PROPERTIES_STOP_DC_SIZE_INPUT );
        coeffsFileName = projectDirectory + coeffsFileName;
        
        loadSizeData( coeffsFileName );
    }

    public double getDcSize(String purpose, String purposeSegment, int zone, int subzone) {
        return sizeMap.get(purpose).get(purposeSegment).get(getZoneSubzoneMapping(zone,subzone));
    }

    private int getZoneSubzoneMapping(int zone, int subzone) {
        return zone*10 + subzone;
    }

    private void loadSizeData( String coeffsFileName ) {
        loadSizeCoefficientTableInformation( readSizeCoefficientTable( coeffsFileName ) );
        determineSizeCoefficients();
    }

    private TableDataSet readSizeCoefficientTable( String coeffsFileName ) {
		try{
            CSVFileReader reader = new CSVFileReader();
            return reader.readFile(
                    new File( coeffsFileName )
            );
        }
        catch(Exception e){
            logger.fatal( String.format( "Exception occurred reading DC Stop Size coefficients data file = %s.", coeffsFileName ), e);
            throw new RuntimeException();
        }
    }

    private Set<String> getValidPurposes() {
        Set<String> validPurposes = new HashSet<String>();
        validPurposes.add(modelStructure.WORK_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.ESCORT_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.SHOPPING_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.EAT_OUT_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.OTH_MAINT_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.SOCIAL_PURPOSE_NAME.toLowerCase());
        validPurposes.add(modelStructure.OTH_DISCR_PURPOSE_NAME.toLowerCase());
        return validPurposes;
    }

    private Set<String> getValidSegments(String purpose) {
        Set<String> validSegments = new HashSet<String>();
        validSegments.add(purpose);
        if (purpose.equals(modelStructure.ESCORT_PURPOSE_NAME.toLowerCase()))
            for (String segment : modelStructure.ESCORT_SEGMENT_NAMES)
                validSegments.add(segment.toLowerCase());
        return  validSegments;
    }

    private void loadSizeCoefficientTableInformation(TableDataSet coefficients) {
        Set<String> sizeTazColumns = new HashSet<String>();
        String[] coefficientTableColumns = coefficients.getColumnLabels();
        String purposeColumn = modelStructure.getDcSizeCoeffPurposeFieldName();
        String segmentColumn = modelStructure.getDcSizeCoeffSegmentFieldName();
        boolean foundPurposeColumn = false;
        boolean foundSegmentColumn = false;
        boolean errors = false;
        for(String label : coefficientTableColumns) {
            if (label.equals(purposeColumn)) {
                foundPurposeColumn = true;
                continue;
            }
            if (label.equals(segmentColumn)) {
                foundSegmentColumn = true;
                continue;
            }

            if (!tazDataManager.isValidZoneTableField(label)) {
                logger.fatal("Stop size coefficient table column does not correspond to taz data column: " + label);
                errors = true;
            }
            sizeTazColumns.add(label);
        }
        if (!foundPurposeColumn) {
            logger.fatal("Purpose column (" + purposeColumn + ") not found in stop size coefficient table");
            errors = true;
        }
        if (!foundSegmentColumn) {
            logger.fatal("Purpose segment column (" + segmentColumn + ") not found in stop size coefficient table");
            errors = true;
        }

        if (!errors) {
            sizeCoefficients = new HashMap<String,Map<String,Map<String,Double>>>();
            Set<String> validPurposes = getValidPurposes();
            for (int i = 1; i <= coefficients.getRowCount(); i++) {
                String purpose = coefficients.getStringValueAt(i,purposeColumn).toLowerCase();
                String segment = coefficients.getStringValueAt(i,segmentColumn).toLowerCase();
                if (validPurposes.contains(purpose)) {
                    if (!sizeCoefficients.containsKey(purpose))
                        sizeCoefficients.put(purpose,new HashMap<String,Map<String,Double>>());
                    if (getValidSegments(purpose).contains(segment)) {
                        Map<String,Double> coefficientMap = new HashMap<String,Double>();
                        for (String column : sizeTazColumns)
                            coefficientMap.put(column,(double) coefficients.getValueAt(i,column));
                        sizeCoefficients.get(purpose).put(segment,coefficientMap);
                    } else {
                        logger.fatal("Invalid segment for purpose " + purpose + " found in stop destination choice size coefficient table: " + segment);
                        errors = true;
                    }

                } else {
                    logger.fatal("Invalid purpose found in stop destination choice size coefficient table: " + purpose);
                    errors = true;
                }
            }
        }


        if (errors) {
            throw new RuntimeException("Errors in stop destination choice size coefficient file; see log file for details.");
        }
    }

    private void determineSizeCoefficients() {
        sizeMap.clear();
        for (String purpose : sizeCoefficients.keySet()) {
            sizeMap.put(purpose,new HashMap<String,Map<Integer,Double>>());
            for (String segment : sizeCoefficients.get(purpose).keySet()) {
                Map<Integer,Double> zoneSizeMap = new HashMap<Integer,Double>();
                for (int i = 1; i <= tazDataManager.getNumberOfZones(); i++) {
                    double size = 0.0d;
                    Map<String,Double> coefficients = sizeCoefficients.get(purpose).get(segment);
                    for (String column : sizeCoefficients.get(purpose).get(segment).keySet())
                        size += tazDataManager.getZoneTableValue(i,column)*coefficients.get(column);
                    double[] walkPercentages = tazDataManager.getZonalWalkPercentagesForTaz(i);
                    for (int j = 0; j < tazDataManager.getNumberOfSubZones(); j++)
                        zoneSizeMap.put(getZoneSubzoneMapping(i,j),size*walkPercentages[j]);
                }
                sizeMap.get(purpose).put(segment,zoneSizeMap);
            }
        }
    }
}
