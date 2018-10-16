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
public class AccConstantsDMU
        implements Serializable, VariableTable
{

    protected transient Logger logger = Logger.getLogger(AccConstantsDMU.class);

    protected HashMap<String, Integer> methodIndexMap;

    private int autoSufficiency;

    public AccConstantsDMU()
    {
        setupMethodIndexMap();
    }

    private void setupMethodIndexMap()
    {
        methodIndexMap = new HashMap<String, Integer>();

        methodIndexMap.put("getAutoSufficiency", 0);

    }

    public double getValueForIndex(int variableIndex, int arrayIndex)
    {

        switch (variableIndex)
        {
            case 0:
                return getAutoSufficiency();

            default:
                logger.error("method number = " + variableIndex + " not found");
                throw new RuntimeException("method number = " + variableIndex + " not found");

        }
    }

    public void setAutoSufficiency(int autoSufficiency)
    {
        this.autoSufficiency = autoSufficiency;
    }



    public int getAutoSufficiency()
    {
        return autoSufficiency;
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
