package com.pb.models.ctramp;

import com.pb.common.calculator.IndexValues;
import com.pb.common.calculator.VariableTable;
import com.pb.common.newmodel.ChoiceModelApplication;
import com.pb.models.ctramp.jppf.*;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author crf
 *         Started Nov 4, 2010 1:55:52 PM
 */
public class TravelTimeModel {
    private static final int TT_DATA_SHEET = 0;
    private static final int TT_PEAK_TIME_SHEET = 1;
    private static final int TT_OFFPEAK_TIME_SHEET = 2;
    private static final int TT_PEAK_DISTANCE_SHEET = 3;
    private static final int TT_OFFPEAK_DISTANCE_SHEET = 4;
    private static final String PROPERTIES_UEC_TRAVEL_TIME_MODEL = "UecFile.TravelTime";

    private static final String[] timePeriods = {"peak","offpeak"};
    private static final int START_AM_PEAK = 6;
    private static final int END_AM_PEAK = 9;
    private static final int START_PM_PEAK = 15;
    private static final int END_PM_PEAK = 18;
    
    private final ChoiceModelApplication peakTimeModel;
    private final ChoiceModelApplication offPeakTimeModel;
    private final ChoiceModelApplication peakDistanceModel;
    private final ChoiceModelApplication offPeakDistanceModel;
    private final TravelTimeDMU modelDmu;
    private final IndexValues indices;
    private final Map<String,Integer> peakTimeModeToAlternativeMap;
    private final Map<String,Integer> offPeakTimeModeToAlternativeMap;
    private final Map<String,Integer> peakDistanceModeToAlternativeMap;
    private final Map<String,Integer> offPeakDistanceModeToAlternativeMap;

    public TravelTimeModel(HashMap<String, String> propertyMap) {
        String mcUecFile = propertyMap.get(com.pb.models.ctramp.jppf.CtrampApplication.PROPERTIES_PROJECT_DIRECTORY) +
                           propertyMap.get(PROPERTIES_UEC_TRAVEL_TIME_MODEL);

        modelDmu = new TravelTimeDMU();
        indices = new IndexValues();
        peakTimeModel = new ChoiceModelApplication(mcUecFile,TT_PEAK_TIME_SHEET,TT_DATA_SHEET,propertyMap,modelDmu);
        offPeakTimeModel = new ChoiceModelApplication(mcUecFile,TT_OFFPEAK_TIME_SHEET,TT_DATA_SHEET,propertyMap,modelDmu);
        peakDistanceModel = new ChoiceModelApplication(mcUecFile,TT_PEAK_DISTANCE_SHEET,TT_DATA_SHEET,propertyMap,modelDmu);
        offPeakDistanceModel = new ChoiceModelApplication(mcUecFile,TT_OFFPEAK_DISTANCE_SHEET,TT_DATA_SHEET,propertyMap,modelDmu);
        
        peakTimeModeToAlternativeMap = new HashMap<String,Integer>();
        String[] alts = peakTimeModel.getAlternativeNames();
        for (int i = 0; i < alts.length; i++)
        	peakTimeModeToAlternativeMap.put(alts[i].toLowerCase(),i);
        
        offPeakTimeModeToAlternativeMap = new HashMap<String,Integer>();
        alts = offPeakTimeModel.getAlternativeNames();
        for (int i = 0; i < alts.length; i++)
        	offPeakTimeModeToAlternativeMap.put(alts[i].toLowerCase(),i);
        
        peakDistanceModeToAlternativeMap = new HashMap<String,Integer>();
        alts = peakDistanceModel.getAlternativeNames();
        for (int i = 0; i < alts.length; i++)
        	peakDistanceModeToAlternativeMap.put(alts[i].toLowerCase(),i);
        
        offPeakDistanceModeToAlternativeMap = new HashMap<String,Integer>();
        alts = offPeakDistanceModel.getAlternativeNames();
        for (int i = 0; i < alts.length; i++)
        	offPeakDistanceModeToAlternativeMap.put(alts[i].toLowerCase(),i);
    }
   
    private boolean tripStartsInPeakPeriod(int startHour) {
        return ((startHour >= START_AM_PEAK && startHour <= END_AM_PEAK) ||
                (startHour >= START_PM_PEAK && startHour <= END_PM_PEAK));
    }

    private double getTravelTime(int origin, int dest, Boolean peak, String alt) {
        indices.setOriginZone(origin);
        indices.setDestZone(dest);
        ChoiceModelApplication app = peak ? peakTimeModel : offPeakTimeModel;
        app.computeUtilities(modelDmu,indices);
        return app.getUtilities()[(peak ? peakTimeModeToAlternativeMap : offPeakTimeModeToAlternativeMap).get(alt)];

    }
    
    private double getTravelDistance(int origin, int dest, Boolean peak, String alt) {
        indices.setOriginZone(origin);
        indices.setDestZone(dest);
        ChoiceModelApplication app = peak ? peakDistanceModel : offPeakDistanceModel;
        app.computeUtilities(modelDmu,indices);
        return app.getUtilities()[(peak ? peakDistanceModeToAlternativeMap : offPeakDistanceModeToAlternativeMap).get(alt)];

    }
    
    public String[] getTimeAlternatives(String period) {
        return (period == timePeriods[0]) ? peakTimeModel.getAlternativeNames() : offPeakTimeModel.getAlternativeNames();
    }
    
    public String[] getTimePeriods() {
        return timePeriods;
    }
    public double[] getTravelTimes(String period, int origin, int dest) {
        indices.setOriginZone(origin);
        indices.setDestZone(dest);
        ChoiceModelApplication app = (period == timePeriods[0]) ? peakTimeModel : offPeakTimeModel;
        app.computeUtilities(modelDmu,indices);
        return app.getUtilities();
    }

    public double[] getTravelDistances(String period, int origin, int dest) {
        indices.setOriginZone(origin);
        indices.setDestZone(dest);
        ChoiceModelApplication app = (period == timePeriods[0]) ? peakDistanceModel : offPeakDistanceModel;
        app.computeUtilities(modelDmu,indices);
        return app.getUtilities();
    }
    
    public double getTravelTime(String modeName, int startHour, int origin, int dest) {
        return getTravelTime(origin,dest,tripStartsInPeakPeriod(startHour),modeName.toLowerCase());
    }

    public double getTravelDistance(String modeName, int startHour, int origin, int dest) {
        return getTravelDistance(origin,dest,tripStartsInPeakPeriod(startHour),modeName.toLowerCase());
    }
    
    private class TravelTimeDMU implements VariableTable {

        public int getIndexValue(String variableName) {
            throw new UnsupportedOperationException();
        }

        public int getAssignmentIndexValue(String variableName) {
            throw new UnsupportedOperationException();
        }

        public double getValueForIndex(int variableIndex) {
            throw new UnsupportedOperationException();
        }

        public double getValueForIndex(int variableIndex, int arrayIndex) {
            throw new UnsupportedOperationException();
        }

        public void setValue(String variableName, double variableValue) {
            throw new UnsupportedOperationException();
        }

        public void setValue(int variableIndex, double variableValue) {
            throw new UnsupportedOperationException();
        }
    }

}
