/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
/*
 * Created on Nov 18, 2004
 *
 * To change the template for this generated file go to
 * Window - Preferences - Java - Code Generation - Code and Comments
 */
package com.pb.common.matrix;

import java.io.Serializable;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeMap;


/**
 * @author jabraham
 * A class to store floats indexed by a number of strings
 */
public class StringIndexedNDimensionalMatrix extends NDimensionalMatrix implements Serializable {
   static final long serialVersionUID=-6183852523591881L;
    
   
   private boolean addKeysOnTheFly = false; 
   private TreeMap[] stringIndices;
   private int[] lastUsedIndices;
   private String[] columnNames;

    /* (non-Javadoc)
     * @see com.pb.common.matrix.NDimensionalMatrix#getValue(int[])
     */
    public float getValue(String[] stringLocation) throws RuntimeException {
        return super.getValue(getIntLocation(stringLocation));
    }
    
    public int[] getIntLocation(String[] stringLocation) throws RuntimeException {
        int[] location = new int[dimensions];
        for (int i=0;i<dimensions;i++) {
            Integer dimensionLocation = (Integer) stringIndices[i].get(stringLocation[i]);
            if (dimensionLocation == null) {
                throw new RuntimeException("invalid string index "+stringLocation[i]+" in index "+i+" of StringIndexedNDimensionalMatrix");
            }
            location[i] = dimensionLocation.intValue();
        }
        return location;
    }
    
    public int getIntLocationForDimension(int dimension, String stringLocation) throws RuntimeException {
        Integer dimensionLocation = (Integer) stringIndices[dimension].get(stringLocation);
        if (dimensionLocation == null) {
            throw new RuntimeException("invalid string index "+stringLocation+" in index "+dimension+" of StringIndexedNDimensionalMatrix");
        }
        return dimensionLocation.intValue();
    }
    
    public String getStringLocationForDimension(int dimension, int intLocation) throws RuntimeException {
        Integer integerLocation = new Integer(intLocation);
        if (!stringIndices[dimension].containsValue(integerLocation)) {
            throw new RuntimeException("invalid integer index "+intLocation+" in index "+dimension +" of StringIndexedNDimensionalMatrix");
        }
        Iterator entryIt = stringIndices[dimension].entrySet().iterator();
        while (entryIt.hasNext()) {
            Map.Entry e = (Map.Entry) entryIt.next();
            if (((Integer) e.getValue()).intValue()== intLocation) {
                return (String) e.getKey();
            }
        }
        // should never reach this;
        throw new RuntimeException("invalid integer index "+intLocation+" in index "+dimension +" of StringIndexedNDimensionalMatrix");
    }

    /* (non-Javadoc)
     * @see com.pb.common.matrix.NDimensionalMatrix#setValue(float, int[])
     */
    public void setValue(float inValue, String[] stringLocation) throws RuntimeException {
        int[] location = new int[dimensions];
        for (int i =0;i<dimensions;i++) {
            Integer dimensionLocation = (Integer) stringIndices[i].get(stringLocation[i]);
            if (dimensionLocation == null) {
                if (addKeysOnTheFly) {
                    dimensionLocation = new Integer(getNextIndex(i));
                    stringIndices[i].put(stringLocation[i],dimensionLocation);
                } else {
                    throw new RuntimeException("invalid string index "+stringLocation[i]+" in index "+i+" of StringIndexedNDimensionalMatrix");
                }
            }
            location[i] = dimensionLocation.intValue();
        }
        super.setValue(inValue, location);
    }
    

    /**
     * @param name
     * @param matrixDimensions
     * @param matrixShape
     */
    public StringIndexedNDimensionalMatrix(String name, int matrixDimensions, int[] matrixShape, String[] columnNames) {
        super(name, matrixDimensions, matrixShape);
        stringIndices = new TreeMap[matrixDimensions];
        lastUsedIndices = new int[matrixDimensions];
        this.columnNames = columnNames;
        for (int i=0;i<matrixDimensions; i++) {
            stringIndices[i] = new TreeMap();
            lastUsedIndices[i] = -1;
        }
    }
    
    public void setStringKeys(String[][] keyNames) {
        lastUsedIndices = new int[dimensions];
        for (int i =0; i< dimensions; i++) {
            stringIndices[i] = new TreeMap();
            lastUsedIndices[i] = -1;
        }
        if (keyNames.length!=dimensions) {
            throw new RuntimeException("Keynames for StringIndexedNDimensionalMatrix do not have the write number of dimensions");
        }
        for (int i =0; i<dimensions; i++) {
            for (int j=0; j<keyNames[i].length; j++) {
                Object bob = (Integer) stringIndices[i].get(keyNames[i][j]);
                if (bob !=null) {
                    throw new RuntimeException("Duplicate key entry in StringIndexedNDimensionalMatrix "+keyNames[i][j]);
                }
                Integer dimensionLocation = new Integer(getNextIndex(i));
                stringIndices[i].put(keyNames[i][j],dimensionLocation);
                
            }
        }
    }
    
    /**
     * @param name
     * @param array
     */
    public StringIndexedNDimensionalMatrix(String name, double[][] array, String[][] indices,  String[] columnNames) {
        super(name, array);
        stringIndices = new TreeMap[2];
        if (indices.length!=2) throw new RuntimeException("Indices in 2D constructor for StringIndexedNDimensionalMatrix must be a 2D array, indices[0] is string array of first index names, indices[1] is string array of second index names");
        for (int i=0;i<indices.length;i++) {
            for (int j=0;j<indices[i].length;j++) {
                int dimLocation = getNextIndex(i);
                Integer dimensionLocation = new Integer(dimLocation);
                stringIndices[i].put(indices[i][j],dimensionLocation);
            }
        }
        this.columnNames = columnNames;
    }

    /**
     * @param i
     * @return
     */
    private int getNextIndex(int i) {
        lastUsedIndices[i]++;
        if (lastUsedIndices[i]>= this.getShape(i)) {
            logger.error("Too many keys in StringIndexedNDimensionalMatrix for dimension "+i);

            // TODO get rid of this debug code
            Iterator it = stringIndices[i].entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry e = (Map.Entry) it.next();
                String key = (String) e.getKey();
                Integer value = (Integer) e.getValue();
                System.out.println(value +" "+key);
            }

                
            throw new RuntimeException("Too many keys in StringIndexedNDimensionalMatrix for dimension "+i);
        }
        return lastUsedIndices[i];
    }

    public void setAddKeysOnTheFly(boolean addKeysOnTheFly) {
        this.addKeysOnTheFly = addKeysOnTheFly;
    }

    public boolean isAddKeysOnTheFly() {
        return addKeysOnTheFly;
    }

    /**
     * @param string
     * @return int
     */
    public int getColumn(String string) throws RuntimeException {
        for (int i =0;i<columnNames.length;i++) {
            if (string.equals(columnNames[i])) {
                return i;
            }
        }
        logger.warn("Can't find column "+string+" in StringINdexedNDimensionalMatrix");
        throw new RuntimeException("Can't find column "+string+" in StringIndexedNDimensionalMatrix");
    }

}
