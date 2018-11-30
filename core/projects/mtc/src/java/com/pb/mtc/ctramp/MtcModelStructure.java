package com.pb.mtc.ctramp;

import com.pb.models.ctramp.ModelStructure;

import java.util.HashMap;
import java.util.ArrayList;

import org.apache.log4j.Logger;

public class MtcModelStructure extends ModelStructure {

    public final String[] MANDATORY_DC_PURPOSE_NAMES = { WORK_PURPOSE_NAME, UNIVERSITY_PURPOSE_NAME, SCHOOL_PURPOSE_NAME };
    public final String[] WORK_PURPOSE_SEGMENT_NAMES = { "low", "med", "high", "very high" };
    public final static int[] INCOME_SEGMENT_DOLLAR_LIMITS = {30000, 60000, 100000, Integer.MAX_VALUE}; 
    public final String[] UNIVERSITY_PURPOSE_SEGMENT_NAMES = { };
    public final String[] SCHOOL_PURPOSE_SEGMENT_NAMES = { "high", "grade" };

    public final String[] TOUR_PURPOSE_ABBREVIATIONS = { "W", "W", "W", "W", "U", "H", "G" };
        
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_LOW               = 1;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_MED               = 2;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_HIGH              = 3;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_VERY_HIGH         = 4;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_UNIVERSITY_UNIVERSITY  = 5;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_SCHOOL_HIGH            = 6;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_SCHOOL_GRADE           = 7;

    public final int USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_WORK                       = 1;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_UNIVERSITY                 = 2;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_SCHOOL_HIGH                = 3;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_SCHOOL_GRADE               = 4;

    public final int USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK           = 1;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_UNIVERSITY     = 2;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_SCHOOL_HIGH    = 3;
    public final int USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_SCHOOL_GRADE   = 3;

    public final int  MANDATORY_STOP_FREQ_UEC_INDEX_WORK                                 = 1;
    public final int  MANDATORY_STOP_FREQ_UEC_INDEX_UNIVERSITY                           = 2;
    public final int  MANDATORY_STOP_FREQ_UEC_INDEX_SCHOOL                               = 3;

    public final int  MANDATORY_STOP_LOC_UEC_INDEX_WORK                                 = 1;
    public final int  MANDATORY_STOP_LOC_UEC_INDEX_UNIVERSITY                           = 2;
    public final int  MANDATORY_STOP_LOC_UEC_INDEX_SCHOOL                               = 3;

    public final int  MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_WORK                         = 1;
    public final int  MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_UNIVERSITY                   = 2;
    public final int  MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SCHOOL                       = 3;



    public final String[] NON_MANDATORY_DC_PURPOSE_NAMES = { "escort", "shopping", "eatOut", "othMaint", "social", "othDiscr" };
    public final String[] ESCORT_PURPOSE_SEGMENT_NAMES = { "kids", "no kids" };
    public final String[] SHOPPING_PURPOSE_SEGMENT_NAMES = { };
    public final String[] EAT_OUT_PURPOSE_SEGMENT_NAMES = { };
    public final String[] OTH_MAINT_PURPOSE_SEGMENT_NAMES = { };
    public final String[] SOCIAL_PURPOSE_SEGMENT_NAMES = { };
    public final String[] OTH_DISCR_PURPOSE_SEGMENT_NAMES = { };

    public final int NON_MANDATORY_SOA_UEC_INDEX_ESCORT_KIDS                             = 8;
    public final int NON_MANDATORY_SOA_UEC_INDEX_ESCORT_NO_KIDS                          = 9;
    public final int NON_MANDATORY_SOA_UEC_INDEX_SHOPPING                                = 10;
    public final int NON_MANDATORY_SOA_UEC_INDEX_EAT_OUT                                 = 11;
    public final int NON_MANDATORY_SOA_UEC_INDEX_OTHER_MAINT                             = 12;
    public final int NON_MANDATORY_SOA_UEC_INDEX_SOCIAL                                  = 13;
    public final int NON_MANDATORY_SOA_UEC_INDEX_OTHER_DISCR                             = 14;

    public final int NON_MANDATORY_DC_UEC_INDEX_ESCORT_KIDS                              = 5;
    public final int NON_MANDATORY_DC_UEC_INDEX_ESCORT_NO_KIDS                           = 6;
    public final int NON_MANDATORY_DC_UEC_INDEX_SHOPPING                                 = 7;
    public final int NON_MANDATORY_DC_UEC_INDEX_EAT_OUT                                  = 8;
    public final int NON_MANDATORY_DC_UEC_INDEX_OTHER_MAINT                              = 9;
    public final int NON_MANDATORY_DC_UEC_INDEX_SOCIAL                                   = 10;
    public final int NON_MANDATORY_DC_UEC_INDEX_OTHER_DISCR                              = 11;

    public final int NON_MANDATORY_MC_UEC_INDEX_ESCORT_KIDS                              = 4;
    public final int NON_MANDATORY_MC_UEC_INDEX_ESCORT_NO_KIDS                           = 4;
    public final int NON_MANDATORY_MC_UEC_INDEX_SHOPPING                                 = 5;
    public final int NON_MANDATORY_MC_UEC_INDEX_EAT_OUT                                  = 6;
    public final int NON_MANDATORY_MC_UEC_INDEX_OTHER_MAINT                              = 7;
    public final int NON_MANDATORY_MC_UEC_INDEX_SOCIAL                                   = 8;
    public final int NON_MANDATORY_MC_UEC_INDEX_OTHER_DISCR                              = 9;

    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_ESCORT                           = 4;
    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_SHOPPING                         = 5;
    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_EAT_OUT                          = 6;
    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_OTHER_MAINT                      = 7;
    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_SOCIAL                           = 8;
    public final int  NON_MANDATORY_STOP_FREQ_UEC_INDEX_OTHER_DISCR                      = 9;

    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_ESCORT                           = 4;
    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_SHOPPING                         = 5;
    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_EAT_OUT                          = 6;
    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_OTHER_MAINT                      = 7;
    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_SOCIAL                           = 8;
    public final int  NON_MANDATORY_STOP_LOC_UEC_INDEX_OTHER_DISCR                      = 9;

    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_ESCORT                   = 4;
    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SHOPPING                 = 5;
    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_EAT_OUT                  = 6;
    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_OTHER_MAINT              = 7;
    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SOCIAL                   = 8;
    public final int  NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_OTHER_DISCR              = 9;

    
    public final String[] AT_WORK_DC_PURPOSE_NAMES = { "atwork" };
    public final String[] AT_WORK_DC_SIZE_SEGMENT_NAMES = { };

    public final int AT_WORK_SOA_UEC_INDEX_EAT                                           = 15;
    public final int AT_WORK_SOA_UEC_INDEX_BUSINESS                                      = 15;
    public final int AT_WORK_SOA_UEC_INDEX_MAINT                                         = 15;
    
    public final int AT_WORK_DC_UEC_INDEX_EAT                                           = 12;
    public final int AT_WORK_DC_UEC_INDEX_BUSINESS                                      = 12;
    public final int AT_WORK_DC_UEC_INDEX_MAINT                                         = 12;
    
    public final int AT_WORK_MC_UEC_INDEX_EAT                                           = 10;
    public final int AT_WORK_MC_UEC_INDEX_BUSINESS                                      = 10;
    public final int AT_WORK_MC_UEC_INDEX_MAINT                                         = 10;

    public final int MTC_AT_WORK_PURPOSE_INDEX_EAT                                          = 1;
    public final int MTC_AT_WORK_PURPOSE_INDEX_BUSINESS                                     = 2;
    public final int MTC_AT_WORK_PURPOSE_INDEX_MAINT                                        = 3;

    public final int AT_WORK_STOP_FREQ_UEC_INDEX_EAT                                    = 10;
    public final int AT_WORK_STOP_FREQ_UEC_INDEX_BUSINESS                               = 10;
    public final int AT_WORK_STOP_FREQ_UEC_INDEX_MAINT                                  = 10;

    public final int  AT_WORK_STOP_LOC_UEC_INDEX                                        = 10;

    public final int  AT_WORK_TRIP_MODE_CHOICE_UEC_INDEX                                = 10;
    
    // TODO: set these values from project specific code.
    public static final int ESCORT_INDEX = 3;
    
    public static final int[] SOV_ALTS = { 1, 2 };
    public static final int[] HOV_ALTS = { 3, 4, 5, 6 };
    public static final int[] WALK_ALTS = { 7 };
    public static final int[] BIKE_ALTS = { 8 };
    public static final int[] NON_MOTORIZED_ALTS = { 7, 8 };
    public static final int[] TRANSIT_ALTS = { 9, 10, 11, 12, 13, 14, 15, 16, 17, 18 };
    public static final int[] WALK_LOCAL_ALTS = { 9 };
    public static final int[] WALK_PREMIUM_ALTS = { 10, 11, 12, 13 };
    public static final int[] DRIVE_TRANSIT_ALTS = { 14, 15, 16, 17, 18 };
    public static final int[] SCHOOL_BUS_ALTS = {};
    public static final int MAXIMUM_TOUR_MODE_ALT_INDEX = 20;

    public static final int NUM_INCOME_CATEGORIES = 4; 
    
    public static final int[] TRIP_SOV_ALTS = { 1, 2 };
    public static final int[] TRIP_HOV_ALTS = { 3, 4, 5, 6 };
    

    public static final String[] JTF_ALTERNATIVE_LABELS = { "0_tours", "1_Shop", "1_Main", "1_Eat", "1_Visit", "1_Disc", "2_SS", "2_SM", "2_SE", "2_SV", "2_SD", "2_MM", "2_ME", "2_MV", "2_MD", "2_EE", "2_EV", "2_ED", "2_VV", "2_VD", "2_DD" };
    public static final String[] AWF_ALTERNATIVE_LABELS = { "0_subTours", "1_eat", "1_business", "1_maint", "2_business", "2_eat_business" };

    public final double[][] CDAP_6_PLUS_PROPORTIONS = {
            { 0.0, 0.0, 0.0 },
            { 0.79647, 0.09368, 0.10985 },
            { 0.61678, 0.25757, 0.12565 },
            { 0.69229, 0.15641, 0.15130 },
            { 0.00000, 0.67169, 0.32831 },
            { 0.00000, 0.54295, 0.45705 },
            { 0.77609, 0.06004, 0.16387 },
            { 0.68514, 0.09144, 0.22342 },
            { 0.14056, 0.06512, 0.79432 }
        };

        
    public static final int EA = 0;
    public static final int AM = 1;
    public static final int MD = 2;
    public static final int PM = 3;
    public static final int EV = 4;
    public static final int[] SKIM_PERIODS = { EA, AM, MD, PM, EV };
    public static final String[] SKIM_PERIOD_STRINGS = { "EA", "AM", "MD", "PM", "EV" };
    

    public static final int EA_EA = 0;
    public static final int EA_AM = 1;
    public static final int EA_MD = 2;
    public static final int EA_PM = 3;
    public static final int EA_EV = 4;
    public static final int AM_EA = -1; // (AM cannot be before EA, so flag that combination as -1)
    public static final int AM_AM = 5;
    public static final int AM_MD = 6;
    public static final int AM_PM = 7;
    public static final int AM_EV = 8;
    public static final int MD_EA = -1; // (MD cannot be before EA, so flag that combination as -1)
    public static final int MD_AM = -1; // (MD cannot be before AM, so flag that combination as -1)
    public static final int MD_MD = 9;
    public static final int MD_PM = 10;
    public static final int MD_EV = 11;
    public static final int PM_EA = -1; // (PM cannot be before EA, so flag that combination as -1)
    public static final int PM_AM = -1; // (PM cannot be before AM, so flag that combination as -1)
    public static final int PM_MD = -1; // (PM cannot be before MD, so flag that combination as -1)
    public static final int PM_PM = 12;
    public static final int PM_EV = 13;
    public static final int EV_EA = -1; // (EV cannot be before EA, so flag that combination as -1)
    public static final int EV_AM = -1; // (EV cannot be before AM, so flag that combination as -1)
    public static final int EV_MD = -1; // (EV cannot be before MD, so flag that combination as -1)
    public static final int EV_PM = -1; // (EV cannot be before PM, so flag that combination as -1)
    public static final int EV_EV = 14;

    public static final int[] SKIM_PERIOD_COMBINATION_INDICES = { EA_EA, EA_AM, EA_MD, EA_PM, EA_EV, AM_AM, AM_MD, AM_PM, AM_EV, MD_MD, MD_PM, MD_EV, PM_PM, PM_EV, EV_EV };
    public static final int[][] SKIM_PERIOD_COMBINATIONS = {
        { EA_EA, EA_AM, EA_MD, EA_PM, EA_EV },
        { AM_EA, AM_AM, AM_MD, AM_PM, AM_EV },
        { MD_EA, MD_AM, MD_MD, MD_PM, MD_EV },
        { PM_EA, PM_AM, PM_MD, PM_PM, PM_EV },
        { EV_EA, EV_AM, EV_MD, EV_PM, EV_EV },
    };
    
    
    
    public static final int  MIN_DRIVING_AGE = 16;
    public static final int  MAX_AGE_GRADE_SCHOOL = 14;

    // guojy: time frame represented in the model 
    public static final int MTC_START_HOUR = 5;	// 5am of the day
    public static final int MTC_END_HOUR = 24;	// 12am of the next day
    public static final double MTC_HOUR_PER_TIME_PERIOD = 1; // each time period is 1 hour


    public MtcModelStructure(){
		super();

        jtfAltLabels = JTF_ALTERNATIVE_LABELS;
        awfAltLabels = AWF_ALTERNATIVE_LABELS;

	    
        dcSizePurposeSegmentMap = new HashMap<String,HashMap<String,Integer>>();
        
        dcSizeIndexSegmentMap = new HashMap<Integer,String>();
        dcSizeSegmentIndexMap = new HashMap<String,Integer>();
        dcSizeArrayIndexPurposeMap = new HashMap<Integer,String>();
        dcSizeArrayPurposeIndexMap = new HashMap<String,Integer>();

        
        
        setMandatoryPurposeNameValues();

        setUsualWorkAndSchoolLocationSoaUecSheetIndexValues ();
        setUsualWorkAndSchoolLocationUecSheetIndexValues ();
        setUsualWorkAndSchoolLocationModeChoiceUecSheetIndexValues ();

        setMandatoryStopFreqUecSheetIndexValues();
        setMandatoryStopLocUecSheetIndexValues();
        setMandatoryTripModeChoiceUecSheetIndexValues();
        
        
        
        
        setNonMandatoryPurposeNameValues();
        
        setNonMandatoryDcSoaUecSheetIndexValues();
        setNonMandatoryDcUecSheetIndexValues();
        setNonMandatoryModeChoiceUecSheetIndexValues();

        setNonMandatoryStopFreqUecSheetIndexValues();
        setNonMandatoryStopLocUecSheetIndexValues();
        setNonMandatoryTripModeChoiceUecSheetIndexValues();
        
        
        
        
        setAtWorkPurposeNameValues();
        
        setAtWorkDcSoaUecSheetIndexValues();
        setAtWorkDcUecSheetIndexValues();
        setAtWorkModeChoiceUecSheetIndexValues();

        setAtWorkStopFreqUecSheetIndexValues();
        setAtWorkStopLocUecSheetIndexValues();        
        setAtWorkTripModeChoiceUecSheetIndexValues();
        
        createDcSizePurposeSegmentMap();        
        
        mapModelSegmentsToDcSizeArraySegments();
        

    }


    private void mapModelSegmentsToDcSizeArraySegments() {
        
        Logger logger = Logger.getLogger( this.getClass() );
        
        dcSizeDcModelPurposeMap = new HashMap<String,String>();
        dcModelDcSizePurposeMap = new HashMap<String,String>();
        
        // loop over soa model names and map top dc size array indices
        for (int i=0; i < dcModelPurposeIndexMap.size(); i++){
            String modelSegment = dcModelIndexPurposeMap.get(i);
            
            // look for this modelSegment name in the dc size array names map, with and without "_segment".
            if ( dcSizeArrayPurposeIndexMap.containsKey(modelSegment) ) {
                dcSizeDcModelPurposeMap.put(modelSegment, modelSegment);
                dcModelDcSizePurposeMap.put(modelSegment, modelSegment);
            }
            else {
                int underscoreIndex = modelSegment.indexOf('_');
                if ( underscoreIndex < 0 ) {
                    if ( dcSizeArrayPurposeIndexMap.containsKey( modelSegment + "_" + modelSegment ) ) {
                        dcSizeDcModelPurposeMap.put( modelSegment + "_" + modelSegment, modelSegment );
                        dcModelDcSizePurposeMap.put( modelSegment, modelSegment + "_" + modelSegment );
                    }
                    else {
                        logger.error( String.format("could not establish correspondence between DC SOA model purpose string = %s", modelSegment) );
                        logger.error( String.format("and a DC array purpose string:") );
                        int j=0;
                        for ( String key : dcSizeArrayPurposeIndexMap.keySet() )
                            logger.error( String.format("%-2d: %s", ++j, key) );
                        throw new RuntimeException(); 
                    }
                }
                else {
                    // all at-work size segments should map to one model segment
                    if ( modelSegment.substring(0,underscoreIndex).equalsIgnoreCase(AT_WORK_PURPOSE_NAME) ) {
                        dcSizeDcModelPurposeMap.put( AT_WORK_PURPOSE_NAME + "_" + AT_WORK_PURPOSE_NAME, modelSegment );
                        dcModelDcSizePurposeMap.put( modelSegment, AT_WORK_PURPOSE_NAME + "_" + AT_WORK_PURPOSE_NAME );
                    }
                    else {
                        logger.error( String.format("could not establish correspondence between DC SOA model purpose string = %s", modelSegment) );
                        logger.error( String.format("and a DC array purpose string:") );
                        int j=0;
                        for ( String key : dcSizeArrayPurposeIndexMap.keySet() )
                            logger.error( String.format("%-2d: %s", ++j, key) );
                        throw new RuntimeException(); 
                    }
                }
            }
            
        }

    }
    
    public int getIncomeSegment( int hhIncomeInDollars ) {
    	for (int i=0; i<INCOME_SEGMENT_DOLLAR_LIMITS.length; i++) {
    		if (hhIncomeInDollars<INCOME_SEGMENT_DOLLAR_LIMITS[i]) {
    			return i+1; 
    		}
    	}
    	throw new RuntimeException("Invalid income segments defined in ModelStructure"); 
    }

    // TODO figure out how to avoid separate copies of this method for static and standard
    public static int getIncomeSegmentStatic( int hhIncomeInDollars ) {
    	for (int i=0; i<INCOME_SEGMENT_DOLLAR_LIMITS.length; i++) {
    		if (hhIncomeInDollars<INCOME_SEGMENT_DOLLAR_LIMITS[i]) {
    			return i+1; 
    		}
    	}
    	throw new RuntimeException("Invalid income segments defined in ModelStructure"); 
    }
    
    public String getSchoolPurpose( int age ) {
        if ( age <= MAX_AGE_GRADE_SCHOOL )
            return (schoolPurposeName + "_" + SCHOOL_PURPOSE_SEGMENT_NAMES[1]).toLowerCase();
        else
            return (schoolPurposeName + "_" + SCHOOL_PURPOSE_SEGMENT_NAMES[0]).toLowerCase();
    }

    public String getSchoolPurpose() {
        return schoolPurposeName.toLowerCase();
    }

    public String getUniversityPurpose() {
        return universityPurposeName.toLowerCase();
    }

    public String getWorkPurposeFromIncomeInDollars( int hhIncomeInDollars ) {
        return getWorkPurposeFromIncomeInDollars( false, hhIncomeInDollars );
    }

    // MTC work purposes not segmented by part-time
    public String getWorkPurposeFromIncomeInDollars( boolean isPtWorker, int hhIncomeInDollars ) {
    	int incomeSegment = getIncomeSegment(hhIncomeInDollars); 
    	return (workPurposeName + "_" + WORK_PURPOSE_SEGMENT_NAMES[incomeSegment-1]).toLowerCase(); 
    }


    public boolean getTourModeIsSov( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < SOV_ALTS.length; i++ ) {
            if ( SOV_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsSovOrHov( int tourMode ) {
        for ( int i=0; i < SOV_ALTS.length; i++ ) {
            if ( SOV_ALTS[i] == tourMode )
                return true;
        }
        
        for ( int i=0; i < HOV_ALTS.length; i++ ) {
            if ( HOV_ALTS[i] == tourMode )
                return true;
        }
        
        return false;
    }

    public boolean getTourModeIsNonMotorized( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < NON_MOTORIZED_ALTS.length; i++ ) {
            if ( NON_MOTORIZED_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsBike( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < BIKE_ALTS.length; i++ ) {
            if ( BIKE_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsWalk( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < WALK_ALTS.length; i++ ) {
            if ( WALK_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsWalkLocal( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < WALK_LOCAL_ALTS.length; i++ ) {
            if ( WALK_LOCAL_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsWalkPremium( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < WALK_PREMIUM_ALTS.length; i++ ) {
            if ( WALK_PREMIUM_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }

    public boolean getTourModeIsTransit( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < TRANSIT_ALTS.length; i++ ) {
            if ( TRANSIT_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }


    public boolean getTourModeIsDriveTransit( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < DRIVE_TRANSIT_ALTS.length; i++ ) {
            if ( DRIVE_TRANSIT_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }


    public boolean getTourModeIsSchoolBus( int tourMode ) {
        boolean returnValue = false;
        for ( int i=0; i < SCHOOL_BUS_ALTS.length; i++ ) {
            if ( SCHOOL_BUS_ALTS[i] == tourMode ) {
                returnValue = true;
                break;
            }
        }
        return returnValue;
    }



    
    public boolean getTripModeIsSovOrHov( int tripMode ) {  

        for ( int i=0; i < TRIP_SOV_ALTS.length; i++ ) {
            if ( TRIP_SOV_ALTS[i] == tripMode )
                return true;
        }
        
        for ( int i=0; i < TRIP_HOV_ALTS.length; i++ ) {
            if ( TRIP_HOV_ALTS[i] == tripMode )
                return true;
        }
        
        return false;
    }



    
    private int createPurposeIndexMaps( String purposeName, String[] segmentNames, int index, String categoryString ) {
        
        HashMap<String, Integer> segmentMap = new HashMap<String, Integer>();
        String key = "";
        if ( segmentNames.length > 0 ) {
            for ( int i=0; i < segmentNames.length; i++ ) {
                segmentMap.put ( segmentNames[i].toLowerCase(), i );
                key = purposeName.toLowerCase() + "_" + segmentNames[i].toLowerCase();
                dcSizeIndexSegmentMap.put ( index, key );
                dcSizeSegmentIndexMap.put ( key, index++ );
            }
        }
        else {
            segmentMap.put ( purposeName.toLowerCase(), 0 );
            key = purposeName.toLowerCase() + "_" + purposeName.toLowerCase();
            dcSizeIndexSegmentMap.put ( index, key );
            dcSizeSegmentIndexMap.put ( key, index++ );
        }
        dcSizePurposeSegmentMap.put( purposeName.toLowerCase(), segmentMap );
        
        return index;
        
    }
    

    /**
     * This method defines the segmentation for which destination choice size variables are calculated.
     */
    private void createDcSizePurposeSegmentMap() {

        int index = 0;
        
        // put work purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( WORK_PURPOSE_NAME, WORK_PURPOSE_SEGMENT_NAMES, index, MANDATORY_CATEGORY );
        
        // put university purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( UNIVERSITY_PURPOSE_NAME, UNIVERSITY_PURPOSE_SEGMENT_NAMES, index, MANDATORY_CATEGORY );

        // put school purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( SCHOOL_PURPOSE_NAME, SCHOOL_PURPOSE_SEGMENT_NAMES, index, MANDATORY_CATEGORY );
        
        // put escort purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( ESCORT_PURPOSE_NAME, ESCORT_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put shopping purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( SHOPPING_PURPOSE_NAME, SHOPPING_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put eat out purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( EAT_OUT_PURPOSE_NAME, EAT_OUT_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put oth main purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( OTH_MAINT_PURPOSE_NAME, OTH_MAINT_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put social purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( SOCIAL_PURPOSE_NAME, SOCIAL_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put oth discr purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( OTH_DISCR_PURPOSE_NAME, OTH_DISCR_PURPOSE_SEGMENT_NAMES, index, INDIVIDUAL_NON_MANDATORY_CATEGORY );
        
        // put at work purpose segments, by which DC Size calculations are segmented, into a map to be stored by purpose name. 
        index = createPurposeIndexMaps( AT_WORK_PURPOSE_NAME, AT_WORK_DC_SIZE_SEGMENT_NAMES, index, AT_WORK_CATEGORY );
        
    }
    
    public HashMap<String, HashMap<String, Integer>> getDcSizePurposeSegmentMap() {
        return dcSizePurposeSegmentMap;
    }
    
    
    

    private void setMandatoryPurposeNameValues() {

        int index = 0;

        int numDcSizePurposeSegments = 0;
        if ( WORK_PURPOSE_SEGMENT_NAMES.length > 0 )
            numDcSizePurposeSegments += WORK_PURPOSE_SEGMENT_NAMES.length;
        else
            numDcSizePurposeSegments += 1;
        if ( UNIVERSITY_PURPOSE_SEGMENT_NAMES.length > 0 )
            numDcSizePurposeSegments += UNIVERSITY_PURPOSE_SEGMENT_NAMES.length;
        else
            numDcSizePurposeSegments += 1;
        if ( SCHOOL_PURPOSE_SEGMENT_NAMES.length > 0 )
            numDcSizePurposeSegments += SCHOOL_PURPOSE_SEGMENT_NAMES.length;
        else
            numDcSizePurposeSegments += 1;


        mandatoryDcModelPurposeNames = new String[numDcSizePurposeSegments];

        

        workPurposeName = WORK_PURPOSE_NAME.toLowerCase();
        workPurposeSegmentNames = new String[WORK_PURPOSE_SEGMENT_NAMES.length];
        if ( workPurposeSegmentNames.length > 0 ) {
            for ( int i=0; i < WORK_PURPOSE_SEGMENT_NAMES.length; i++ ) {
                workPurposeSegmentNames[i] = WORK_PURPOSE_SEGMENT_NAMES[i].toLowerCase();
                mandatoryDcModelPurposeNames[index] = workPurposeName + "_" + workPurposeSegmentNames[i];
                dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                
                // a separate size term is calculated for each work purpose_segment 
                dcSizeArrayIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                dcSizeArrayPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                index++;
            }
        }
        else {
            mandatoryDcModelPurposeNames[index] = workPurposeName;
            dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
            dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );

            // a separate size term is calculated for each work purpose_segment 
            String name = mandatoryDcModelPurposeNames[index] + "_" + mandatoryDcModelPurposeNames[index];
            dcSizeArrayIndexPurposeMap.put( index, name );
            dcSizeArrayPurposeIndexMap.put( name, index );
            index++;
        }

        universityPurposeName = UNIVERSITY_PURPOSE_NAME.toLowerCase();
        universityPurposeSegmentNames = new String[UNIVERSITY_PURPOSE_SEGMENT_NAMES.length];
        if ( universityPurposeSegmentNames.length > 0 ) {
            for ( int i=0; i < universityPurposeSegmentNames.length; i++ ) {
                universityPurposeSegmentNames[i] = UNIVERSITY_PURPOSE_SEGMENT_NAMES[i].toLowerCase();
                mandatoryDcModelPurposeNames[index] = universityPurposeName + "_" + universityPurposeSegmentNames[i];
                dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                
                // a separate size term is calculated for each university purpose_segment 
                dcSizeArrayIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                dcSizeArrayPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                index++;
            }
        }
        else {
            mandatoryDcModelPurposeNames[index] = universityPurposeName;
            dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
            dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
            
            // a separate size term is calculated for each university purpose_segment 
            String name = mandatoryDcModelPurposeNames[index] + "_" + mandatoryDcModelPurposeNames[index];
            dcSizeArrayIndexPurposeMap.put( index, name );
            dcSizeArrayPurposeIndexMap.put( name, index );
            index++;
        }

        schoolPurposeName = SCHOOL_PURPOSE_NAME.toLowerCase();
        schoolPurposeSegmentNames = new String[SCHOOL_PURPOSE_SEGMENT_NAMES.length];
        if ( schoolPurposeSegmentNames.length > 0 ) {
            for ( int i=0; i < schoolPurposeSegmentNames.length; i++ ) {
                schoolPurposeSegmentNames[i] = SCHOOL_PURPOSE_SEGMENT_NAMES[i].toLowerCase();
                mandatoryDcModelPurposeNames[index] = schoolPurposeName + "_" + schoolPurposeSegmentNames[i];
                dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                
                // a separate size term is calculated for each school purpose_segment 
                dcSizeArrayIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
                dcSizeArrayPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
                index++;
            }
        }
        else {
            mandatoryDcModelPurposeNames[index] = schoolPurposeName;
            dcModelPurposeIndexMap.put( mandatoryDcModelPurposeNames[index], index );
            dcModelIndexPurposeMap.put( index, mandatoryDcModelPurposeNames[index] );
            
            // a separate size term is calculated for each school purpose_segment 
            String name = mandatoryDcModelPurposeNames[index] + "_" + mandatoryDcModelPurposeNames[index];
            dcSizeArrayIndexPurposeMap.put( index, name );
            dcSizeArrayPurposeIndexMap.put( name, index );
        }


    }


    private void setUsualWorkAndSchoolLocationSoaUecSheetIndexValues () {
        dcSoaUecIndexMap.put( "work_low", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_LOW );
        dcSoaUecIndexMap.put( "work_med", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_MED );
        dcSoaUecIndexMap.put( "work_high", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_HIGH );
        dcSoaUecIndexMap.put( "work_very high", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_WORK_VERY_HIGH );
        dcSoaUecIndexMap.put( "university", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_UNIVERSITY_UNIVERSITY );
        dcSoaUecIndexMap.put( "school_grade", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_SCHOOL_GRADE );
        dcSoaUecIndexMap.put( "school_high", USUAL_WORK_AND_SCHOOL_LOCATION_SOA_UEC_INDEX_SCHOOL_HIGH );
    }


    private void setUsualWorkAndSchoolLocationUecSheetIndexValues () {
        dcUecIndexMap.put( "work_low", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_WORK );
        dcUecIndexMap.put( "work_med", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_WORK );
        dcUecIndexMap.put( "work_high", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_WORK );
        dcUecIndexMap.put( "work_very high", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_WORK );
        dcUecIndexMap.put( "university", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_UNIVERSITY );
        dcUecIndexMap.put( "school_grade", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_SCHOOL_GRADE );
        dcUecIndexMap.put( "school_high", USUAL_WORK_AND_SCHOOL_LOCATION_UEC_INDEX_SCHOOL_HIGH );
    }


    private void setUsualWorkAndSchoolLocationModeChoiceUecSheetIndexValues () {
        tourModeChoiceUecIndexMap.put( "work_low", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK );
        tourModeChoiceUecIndexMap.put( "work_med", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK );
        tourModeChoiceUecIndexMap.put( "work_high", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK );
        tourModeChoiceUecIndexMap.put( "work_very high", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK );
        tourModeChoiceUecIndexMap.put( "work_part time", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_WORK );
        tourModeChoiceUecIndexMap.put( "university", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_UNIVERSITY );
        tourModeChoiceUecIndexMap.put( "school_grade", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_SCHOOL_GRADE );
        tourModeChoiceUecIndexMap.put( "school_high", USUAL_WORK_AND_SCHOOL_LOCATION_MODE_CHOICE_UEC_INDEX_SCHOOL_HIGH );
    }

    private void setMandatoryStopFreqUecSheetIndexValues () {
        stopFreqUecIndexMap.put( "work_low",       MANDATORY_STOP_FREQ_UEC_INDEX_WORK );
        stopFreqUecIndexMap.put( "work_med",       MANDATORY_STOP_FREQ_UEC_INDEX_WORK );
        stopFreqUecIndexMap.put( "work_high",      MANDATORY_STOP_FREQ_UEC_INDEX_WORK );
        stopFreqUecIndexMap.put( "work_very high", MANDATORY_STOP_FREQ_UEC_INDEX_WORK );
        stopFreqUecIndexMap.put( "university",     MANDATORY_STOP_FREQ_UEC_INDEX_UNIVERSITY );
        stopFreqUecIndexMap.put( "school_grade",   MANDATORY_STOP_FREQ_UEC_INDEX_SCHOOL );
        stopFreqUecIndexMap.put( "school_high",    MANDATORY_STOP_FREQ_UEC_INDEX_SCHOOL );
    }


    private void setMandatoryStopLocUecSheetIndexValues () {
        stopLocUecIndexMap.put( "work", MANDATORY_STOP_LOC_UEC_INDEX_WORK );
        stopLocUecIndexMap.put( "university", MANDATORY_STOP_LOC_UEC_INDEX_UNIVERSITY );
        stopLocUecIndexMap.put( "school", MANDATORY_STOP_LOC_UEC_INDEX_SCHOOL );
    }

    private void setMandatoryTripModeChoiceUecSheetIndexValues () {
        tripModeChoiceUecIndexMap.put( "work", MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_WORK );
        tripModeChoiceUecIndexMap.put( "university", MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_UNIVERSITY );
        tripModeChoiceUecIndexMap.put( "school", MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SCHOOL );
    }


    private void setNonMandatoryPurposeNameValues() {
       
        // initialize index to the length of the mandatory names list already developed.
        int index = dcSizeArrayPurposeIndexMap.size();


        ESCORT_SEGMENT_NAMES = ESCORT_PURPOSE_SEGMENT_NAMES;

        // ESCORT is the only non-mandatory purpose with segments
        ArrayList<String> purposeNamesList = new ArrayList<String>();
        for ( int i=0; i < NON_MANDATORY_DC_PURPOSE_NAMES.length; i++ ) {
            if ( NON_MANDATORY_DC_PURPOSE_NAMES[i].equalsIgnoreCase( ESCORT_PURPOSE_NAME ) ) {
                for ( int j=0; j < ESCORT_SEGMENT_NAMES.length; j++ ) {
                    String name = (ESCORT_PURPOSE_NAME + "_" + ESCORT_SEGMENT_NAMES[j]).toLowerCase();
                    purposeNamesList.add( name );
                    dcModelPurposeIndexMap.put( name, index );
                    dcModelIndexPurposeMap.put( index, name );
                    
                    // a separate size term is calculated for each non-mandatory purpose_segment 
                    dcSizeArrayIndexPurposeMap.put( index, name );
                    dcSizeArrayPurposeIndexMap.put( name, index );
                    index++;
                }
            }
            else {
                String name = NON_MANDATORY_DC_PURPOSE_NAMES[i].toLowerCase();
                purposeNamesList.add( name );
                dcModelPurposeIndexMap.put( name, index );
                dcModelIndexPurposeMap.put( index, name );

                // a separate size term is calculated for each non-mandatory purpose_segment 
                dcSizeArrayIndexPurposeMap.put( index, name+"_"+name );
                dcSizeArrayPurposeIndexMap.put( name+"_"+name, index );
                index++;
            }
        }

        int escortOffset = ESCORT_SEGMENT_NAMES.length;

        jointDcModelPurposeNames = new String[purposeNamesList.size()-escortOffset];
        nonMandatoryDcModelPurposeNames = new String[purposeNamesList.size()];
        for ( int i=0; i < purposeNamesList.size(); i++ ) {
            nonMandatoryDcModelPurposeNames[i] = purposeNamesList.get(i);
            if ( i > escortOffset - 1 )
                jointDcModelPurposeNames[i-escortOffset] = purposeNamesList.get(i);
        }

    }


    private void setNonMandatoryDcSoaUecSheetIndexValues () {
        dcSoaUecIndexMap.put( "escort_kids", NON_MANDATORY_SOA_UEC_INDEX_ESCORT_KIDS );
        dcSoaUecIndexMap.put( "escort_no kids", NON_MANDATORY_SOA_UEC_INDEX_ESCORT_NO_KIDS );
        dcSoaUecIndexMap.put( "shopping", NON_MANDATORY_SOA_UEC_INDEX_SHOPPING );
        dcSoaUecIndexMap.put( "eatout", NON_MANDATORY_SOA_UEC_INDEX_EAT_OUT );
        dcSoaUecIndexMap.put( "othmaint", NON_MANDATORY_SOA_UEC_INDEX_OTHER_MAINT );
        dcSoaUecIndexMap.put( "social", NON_MANDATORY_SOA_UEC_INDEX_SOCIAL );
        dcSoaUecIndexMap.put( "othdiscr", NON_MANDATORY_SOA_UEC_INDEX_OTHER_DISCR );
    }


    private void setNonMandatoryDcUecSheetIndexValues () {
        dcUecIndexMap.put( "escort_kids", NON_MANDATORY_DC_UEC_INDEX_ESCORT_KIDS );
        dcUecIndexMap.put( "escort_no kids", NON_MANDATORY_DC_UEC_INDEX_ESCORT_NO_KIDS );
        dcUecIndexMap.put( "shopping", NON_MANDATORY_DC_UEC_INDEX_SHOPPING );
        dcUecIndexMap.put( "eatout", NON_MANDATORY_DC_UEC_INDEX_EAT_OUT );
        dcUecIndexMap.put( "othmaint", NON_MANDATORY_DC_UEC_INDEX_OTHER_MAINT );
        dcUecIndexMap.put( "social", NON_MANDATORY_DC_UEC_INDEX_SOCIAL );
        dcUecIndexMap.put( "othdiscr", NON_MANDATORY_DC_UEC_INDEX_OTHER_DISCR );
    }


    private void setNonMandatoryModeChoiceUecSheetIndexValues () {
        tourModeChoiceUecIndexMap.put( "escort_kids", NON_MANDATORY_MC_UEC_INDEX_ESCORT_KIDS );
        tourModeChoiceUecIndexMap.put( "escort_no kids", NON_MANDATORY_MC_UEC_INDEX_ESCORT_NO_KIDS );
        tourModeChoiceUecIndexMap.put( "shopping", NON_MANDATORY_MC_UEC_INDEX_SHOPPING );
        tourModeChoiceUecIndexMap.put( "eatout", NON_MANDATORY_MC_UEC_INDEX_EAT_OUT );
        tourModeChoiceUecIndexMap.put( "othmaint", NON_MANDATORY_MC_UEC_INDEX_OTHER_MAINT );
        tourModeChoiceUecIndexMap.put( "social", NON_MANDATORY_MC_UEC_INDEX_SOCIAL );
        tourModeChoiceUecIndexMap.put( "othdiscr", NON_MANDATORY_MC_UEC_INDEX_OTHER_DISCR );
    }

    private void setNonMandatoryStopFreqUecSheetIndexValues () {
        stopFreqUecIndexMap.put( "escort_kids", NON_MANDATORY_STOP_FREQ_UEC_INDEX_ESCORT );
        stopFreqUecIndexMap.put( "escort_no kids", NON_MANDATORY_STOP_FREQ_UEC_INDEX_ESCORT );
        stopFreqUecIndexMap.put( "shopping", NON_MANDATORY_STOP_FREQ_UEC_INDEX_SHOPPING );
        stopFreqUecIndexMap.put( "eatout", NON_MANDATORY_STOP_FREQ_UEC_INDEX_EAT_OUT );
        stopFreqUecIndexMap.put( "othmaint", NON_MANDATORY_STOP_FREQ_UEC_INDEX_OTHER_MAINT );
        stopFreqUecIndexMap.put( "social", NON_MANDATORY_STOP_FREQ_UEC_INDEX_SOCIAL );
        stopFreqUecIndexMap.put( "othdiscr", NON_MANDATORY_STOP_FREQ_UEC_INDEX_OTHER_DISCR );
    }

    private void setNonMandatoryStopLocUecSheetIndexValues () {
        stopLocUecIndexMap.put( "escort", NON_MANDATORY_STOP_LOC_UEC_INDEX_ESCORT );
        stopLocUecIndexMap.put( "shopping", NON_MANDATORY_STOP_LOC_UEC_INDEX_SHOPPING );
        stopLocUecIndexMap.put( "eatout", NON_MANDATORY_STOP_LOC_UEC_INDEX_EAT_OUT );
        stopLocUecIndexMap.put( "othmaint", NON_MANDATORY_STOP_LOC_UEC_INDEX_OTHER_MAINT );
        stopLocUecIndexMap.put( "social", NON_MANDATORY_STOP_LOC_UEC_INDEX_SOCIAL );
        stopLocUecIndexMap.put( "othdiscr", NON_MANDATORY_STOP_LOC_UEC_INDEX_OTHER_DISCR );
    }

    private void setNonMandatoryTripModeChoiceUecSheetIndexValues () {
        tripModeChoiceUecIndexMap.put( "escort", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_ESCORT );
        tripModeChoiceUecIndexMap.put( "shopping", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SHOPPING );
        tripModeChoiceUecIndexMap.put( "eatout", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_EAT_OUT );
        tripModeChoiceUecIndexMap.put( "othmaint", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_OTHER_MAINT );
        tripModeChoiceUecIndexMap.put( "social", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_SOCIAL );
        tripModeChoiceUecIndexMap.put( "othdiscr", NON_MANDATORY_TRIP_MODE_CHOICE_UEC_INDEX_OTHER_DISCR );
    }

    
    private void setAtWorkPurposeNameValues() {

        AT_WORK_PURPOSE_INDEX_EAT = MTC_AT_WORK_PURPOSE_INDEX_EAT;
        AT_WORK_PURPOSE_INDEX_BUSINESS = MTC_AT_WORK_PURPOSE_INDEX_BUSINESS;
        AT_WORK_PURPOSE_INDEX_MAINT = MTC_AT_WORK_PURPOSE_INDEX_MAINT;
        
        AT_WORK_SEGMENT_NAMES = new String[3];
        AT_WORK_SEGMENT_NAMES[0] = AT_WORK_EAT_PURPOSE_NAME;
        AT_WORK_SEGMENT_NAMES[1] = AT_WORK_BUSINESS_PURPOSE_NAME;
        AT_WORK_SEGMENT_NAMES[2] = AT_WORK_MAINT_PURPOSE_NAME;
        
        
        // initialize index to the length of the home-based tour names list already developed.
        int index = dcSizeArrayPurposeIndexMap.size();

        // the same size term is used by each at-work soa model 
        dcSizeArrayIndexPurposeMap.put( index, AT_WORK_PURPOSE_NAME+"_"+AT_WORK_PURPOSE_NAME );
        dcSizeArrayPurposeIndexMap.put( AT_WORK_PURPOSE_NAME+"_"+AT_WORK_PURPOSE_NAME, index );

        ArrayList<String> purposeNamesList = new ArrayList<String>();
        for ( int j=0; j < AT_WORK_SEGMENT_NAMES.length; j++ ) {
            String name = ( AT_WORK_PURPOSE_NAME + "_" + AT_WORK_SEGMENT_NAMES[j]).toLowerCase();
            purposeNamesList.add( name );
            dcModelPurposeIndexMap.put( name, index );
            dcModelIndexPurposeMap.put( index, name );
            index++;
        }

        
        atWorkDcModelPurposeNames = new String[purposeNamesList.size()];
        for ( int i=0; i < purposeNamesList.size(); i++ ) {
            atWorkDcModelPurposeNames[i] = purposeNamesList.get(i);
        }

    }


    private void setAtWorkDcSoaUecSheetIndexValues () {
        dcSoaUecIndexMap.put( "atwork_eat", AT_WORK_SOA_UEC_INDEX_EAT );
        dcSoaUecIndexMap.put( "atwork_business", AT_WORK_SOA_UEC_INDEX_BUSINESS );
        dcSoaUecIndexMap.put( "atwork_maint", AT_WORK_SOA_UEC_INDEX_MAINT );
    }


    private void setAtWorkDcUecSheetIndexValues () {
        dcUecIndexMap.put( "atwork_eat", AT_WORK_DC_UEC_INDEX_EAT );
        dcUecIndexMap.put( "atwork_business", AT_WORK_DC_UEC_INDEX_BUSINESS );
        dcUecIndexMap.put( "atwork_maint", AT_WORK_DC_UEC_INDEX_MAINT );
    }


    private void setAtWorkModeChoiceUecSheetIndexValues () {
        tourModeChoiceUecIndexMap.put( "atwork_eat", AT_WORK_MC_UEC_INDEX_EAT );
        tourModeChoiceUecIndexMap.put( "atwork_business", AT_WORK_MC_UEC_INDEX_BUSINESS );
        tourModeChoiceUecIndexMap.put( "atwork_maint", AT_WORK_MC_UEC_INDEX_MAINT );
    }

    private void setAtWorkStopFreqUecSheetIndexValues () {
        stopFreqUecIndexMap.put( "atwork_eat", AT_WORK_STOP_FREQ_UEC_INDEX_EAT );
        stopFreqUecIndexMap.put( "atwork_business", AT_WORK_STOP_FREQ_UEC_INDEX_BUSINESS );
        stopFreqUecIndexMap.put( "atwork_maint", AT_WORK_STOP_FREQ_UEC_INDEX_MAINT );
    }

    private void setAtWorkStopLocUecSheetIndexValues () {
        stopLocUecIndexMap.put( AT_WORK_PURPOSE_NAME, AT_WORK_STOP_LOC_UEC_INDEX );
    }

    private void setAtWorkTripModeChoiceUecSheetIndexValues () {
        tripModeChoiceUecIndexMap.put( AT_WORK_PURPOSE_NAME, AT_WORK_TRIP_MODE_CHOICE_UEC_INDEX );
    }

    

    
    public double[][] getCdap6PlusProps() {
        return CDAP_6_PLUS_PROPORTIONS;
    }
    

    public String getMandatoryPurposeAbbreviation( int tourPurposeIndex ){
        return TOUR_PURPOSE_ABBREVIATIONS[tourPurposeIndex];
    }

    
    

    public int getSkimMatrixPeriod(int hour) {

        int skimPeriodIndex = 0;

        if ( hour <= 5 )
            skimPeriodIndex = EA;
        else if ( hour <= 10 )
            skimPeriodIndex = AM;
        else if ( hour <= 15 )
            skimPeriodIndex = MD;
        else if ( hour <= 19 )
            skimPeriodIndex = PM;
        else
            skimPeriodIndex = EV;

        return skimPeriodIndex;

    }
    
    public String getSkimMatrixPeriodString (int hour) {
        int index = getSkimMatrixPeriod( hour );
        return SKIM_PERIOD_STRINGS[index];
    }
    
    
    public int getDefaultAmHour() {
        return 8;
    }
    
    public int getDefaultPmHour() {
        return 17;
    }
    
    public int getDefaultMdHour() {
        return 14;
    }
    
    public int[] getSkimPeriodCombinationIndices() {
        return SKIM_PERIOD_COMBINATION_INDICES;
    }

    public int getSkimPeriodCombinationIndex( int startHour, int endHour ) {
        
        int startPeriodIndex = getSkimMatrixPeriod( startHour );
        int endPeriodIndex = getSkimMatrixPeriod( endHour );
        
        if ( SKIM_PERIOD_COMBINATIONS[startPeriodIndex][endPeriodIndex] < 0 ) {
            String errorString = String.format( "startHour=%d, startPeriod=%d, endHour=%d, endPeriod=%d is invalid combination.", startHour, startPeriodIndex, endHour, endPeriodIndex );
            throw new RuntimeException( errorString );
        }
        else {
            return SKIM_PERIOD_COMBINATIONS[startPeriodIndex][endPeriodIndex];
        }
        
    }
    
    public int getIsAmPeak(int hour) {
    	if ( getSkimMatrixPeriod(hour)==AM )
    		return 1;
    	else
    		return 0;
    }
    
    public int getIsPmPeak(int hour) {
    	if ( getSkimMatrixPeriod(hour)==PM )
    		return 1;
    	else
    		return 0;
    }

    
    public int getMaxTourModeIndex() {
        return MAXIMUM_TOUR_MODE_ALT_INDEX;
    }
    
    /* guojy:
     * returns the hour of day that corresponds to the 1st time period in the simulation
     * @see com.pb.models.ctramp.ModelStructure#getStartHour()
     */
    public double getStartHour() {
    	
    	return MTC_START_HOUR;
    }
    
    /* guojy:
     * returns the hour of day that corresponds to the last time period in the simulation
     * @see com.pb.models.ctramp.ModelStructure#getEndHour()
     */
    public double getEndHour() {
    	
    	return MTC_END_HOUR;
    }
    
    /* guojy:
     * converts time period number into hour of day (0-24)
     * @see com.pb.models.ctramp.ModelStructure#getHourFromTimePeriodNumber(int)
     */
    public double getHourFromTimePeriodNumber(int timePeriodNumber) {
    	
    	return MTC_START_HOUR + timePeriodNumber*MTC_HOUR_PER_TIME_PERIOD;
    }
    
    /* guojy:
     * returns total number of time periods represented in the model
     * @see com.pb.models.ctramp.ModelStructure#getTotalTimePeriods()
     */
    public byte	   getTotalTimePeriods() {
    	
    	return (byte) ( (MTC_END_HOUR - MTC_START_HOUR) / MTC_HOUR_PER_TIME_PERIOD )+1;
    }
    
}
    