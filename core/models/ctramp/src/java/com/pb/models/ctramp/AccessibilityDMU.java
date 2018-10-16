package com.pb.models.ctramp;

import java.io.Serializable;
import java.util.HashMap;
import org.apache.log4j.Logger;
import com.pb.common.calculator.VariableTable;
import com.pb.common.datafile.TableDataSet;

/**
 * This class is used to instantiate UEC DMU objects for calculating accessibility logsums. 
 *
 * @author Jim Hicks
 * @version Apr 19, 2012
 */
public class AccessibilityDMU
        implements Serializable, VariableTable
{

    protected transient Logger logger = Logger.getLogger(AccessibilityDMU.class);

    private static final String AUTO_SUFFICIENCY_INDEX_FIELD_NAME = "autoSufficiencyIndex";
    private static final String INCOME_INDEX_FIELD_NAME = "incomeIndex";
    private static final String SIZE_TERM_INDEX_FIELD_NAME = "sizeIndex";
    
    protected HashMap<String, Integer> methodIndexMap;

    private double[] sizeTerms;
    private double[][] logsums;

    // the alternativeData tabledataset has the following fields
    // sizeTermIndex: Used to index into the sizeTerms array
    // incomeIndex: Used as the first dimension index for the logsums array
    // autoSufficiencyIndex: Used as the second dimension index for the logsums array
    private TableDataSet alternativeData;
    private int sizeIndex;
    private int incomeIndex;
    private int autoSufficiencyIndex;

    private int autoSufficiency;

    public AccessibilityDMU()
    {
        setupMethodIndexMap();
    }

    private void setupMethodIndexMap()
    {
        methodIndexMap = new HashMap<String, Integer>();

        methodIndexMap.put("getAutoSufficiency", 0);
        methodIndexMap.put("getSizeTerm", 1);
        methodIndexMap.put("getLogsum", 2);

    }

    public double getValueForIndex(int variableIndex, int arrayIndex)
    {

        switch (variableIndex)
        {
            case 0:
                return getAutoSufficiency();
            case 1:
                return getSizeTerm(arrayIndex);
            case 2:
                return getLogsum(arrayIndex);

            default:
                logger.error("method number = " + variableIndex + " not found");
                throw new RuntimeException("method number = " + variableIndex + " not found");

        }
    }

    public void setAlternativeData(TableDataSet alternativeData)
    {
        this.alternativeData = alternativeData;
        autoSufficiencyIndex = alternativeData.getColumnPosition( AUTO_SUFFICIENCY_INDEX_FIELD_NAME );
        incomeIndex = alternativeData.getColumnPosition( INCOME_INDEX_FIELD_NAME );
        sizeIndex = alternativeData.getColumnPosition(SIZE_TERM_INDEX_FIELD_NAME);

    }
    
    public void setAutoSufficiency(int autoSufficiency)
    {
        this.autoSufficiency = autoSufficiency;
    }

    public void setSizeTerms(double[] sizeTerms)
    {
        this.sizeTerms = sizeTerms;
    }

    public void setLogsums(double[][] logsums)
    {
        this.logsums = logsums;
    }

    /**
     * For the given alternative, look up the size term and return it.
     * 
     * @param alt
     * @return
     */
    public double getSizeTerm(int alt)
    {
        int index = (int) alternativeData.getValueAt(alt, sizeIndex);
        return sizeTerms[index];
    }

    public int getAutoSufficiency()
    {
        return autoSufficiency;
    }
    
    /**
     * For the given alternative, look up the size term and return it.
     * 
     * @param alt
     * @return
     */
    public double getLogsum(int alt)
    {

        int i = (int) alternativeData.getValueAt(alt, incomeIndex);
        int a = (int) alternativeData.getValueAt(alt, autoSufficiencyIndex);

        return logsums[i][a];
    }

    public int getIndexValue(String variableName)
    {
        return methodIndexMap.get(variableName);
    }

    public int getAssignmentIndexValue(String variableName)
    {
        throw new UnsupportedOperationException();
    }

    public double getValueForIndex(int variableIndex)
    {
        throw new UnsupportedOperationException();
    }

    public void setValue(String variableName, double variableValue)
    {
        throw new UnsupportedOperationException();
    }

    public void setValue(int variableIndex, double variableValue)
    {
        throw new UnsupportedOperationException();
    }

}
