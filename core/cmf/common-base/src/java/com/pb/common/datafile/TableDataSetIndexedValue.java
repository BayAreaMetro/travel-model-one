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
package com.pb.common.datafile;

import javax.swing.event.TableModelEvent;


/**
 * 
 * @author jabraham
 * 
 */
public class TableDataSetIndexedValue implements TableDataSetIndex.ChangeListener, java.io.Serializable, Cloneable {

    static final long serialVersionUID = 182225536892554622L;
    String[][] stringKeyNameValues = new String[2][0];
    String[][] intKeyNameValues = new String[2][0];
    private int[][] intKeyValues = new int[1][0];
    private String myTableName = new String();
    private String myFieldName = new String();
    transient TableDataSetIndex myLastIndex = null;
    transient TableDataSetCollection myLastCollection = null;
    private transient int lastDataColumnNumber = -1;
    transient int[] lastRowNumbers;
    protected transient java.beans.PropertyChangeSupport propertyChange;
    /**
     * <code>valueMode</code> controls behaviour when multiple records match the indices
     */
    private int valueMode=SINGLE_VALUE_MODE; 
    /**
     * With <code>SUM_MODE</code> the value returned is the sum of all the values
     * that match the indices.  When a value is put it is divided by the number of 
     * records that match the indices
     */
    public static final int SUM_MODE=1; 
    /**
     * With <code>AVERAGE_MODE</code> the value returned is the average of all the values 
     * that match the indices.  When a value is put the value is put into all of the records
     * that match the indices
     */
    public static final int AVERAGE_MODE=2;
    /**
     * With <code>SINGLE_VALUE_MODE</code> a runtime exception is thrown if there is
     * more than one record in the table that matches the indices
     */
    public static final int SINGLE_VALUE_MODE=3;
    
    private boolean errorOnMissingValues = false;

    public boolean isErrorOnMissingValues() {
        return errorOnMissingValues;
    }

    public void setErrorOnMissingValues(boolean errorOnMissingValues) {
        this.errorOnMissingValues = errorOnMissingValues;
    }

    public TableDataSetIndexedValue(
        String tableName,
        String[] stringKeyNames,
        String[] intKeyNames,
        String[][] stringIndexValues,
        int[][] intIndexValues,
        String columnName) {
        
        stringKeyNameValues = new String[1+stringIndexValues.length][];
        stringKeyNameValues[0] = stringKeyNames;
        for (int i=0;i<stringIndexValues.length;i++) {
            stringKeyNameValues[i+1] = stringIndexValues[i];
        }
        intKeyNameValues = new String[1+intIndexValues.length][];
        intKeyNameValues[0] = intKeyNames;
        for (int r=0;r<intIndexValues.length;r++) {
            intKeyNameValues[r+1] = new String[intIndexValues[r].length];
            for (int i=0;i<intKeyNameValues[r+1].length;i++) {
                intKeyNameValues[r+1][i]= Integer.toString(intIndexValues[r][i]);
            }
        }
        setMyTableName(tableName);
        intKeyValues = intIndexValues;
        setMyFieldName(columnName);
        checkArraySizeConsistency();
    }

    private void checkArraySizeConsistency() {
        if (stringKeyNameValues.length != intKeyNameValues.length) {
            throw new RuntimeException("Number of rows in string key values and int key values is incorrect");
        }
        for (int i=1;i<stringKeyNameValues.length;i++) {
            if (stringKeyNameValues[i].length != stringKeyNameValues[0].length) {
                throw new RuntimeException("Row "+i+" of string key values has wrong length -- doesn't match keys");
            }
        }
        for (int i=1;i<intKeyNameValues.length;i++) {
            if (intKeyNameValues[i].length != intKeyNameValues[0].length ||
                intKeyValues[i-1].length != intKeyNameValues[0].length) {
                throw new RuntimeException("Row "+i+" of int key values has wrong length -- doesn't match keys");
            }
        }
    }

    public TableDataSetIndexedValue() {
        //null constructor
    }
    
    /**
     * @param s
     */
    public TableDataSetIndexedValue(TableDataSetIndexedValue s) {
        // deep array copy
        this.stringKeyNameValues = new String[s.stringKeyNameValues.length][];
        for (int i=0;i<stringKeyNameValues.length;i++) {
            stringKeyNameValues[i] = new String[s.stringKeyNameValues[i].length];
            System.arraycopy(s.stringKeyNameValues[i],0,stringKeyNameValues[i],0,stringKeyNameValues[i].length);
        }
        this.intKeyNameValues = new String[s.intKeyNameValues.length][];
        for (int i=0;i<intKeyNameValues.length;i++) {
            intKeyNameValues[i] = new String[s.intKeyNameValues[i].length];
            System.arraycopy(s.intKeyNameValues[i],0,intKeyNameValues[i],0,intKeyNameValues[i].length);
        }
        updateIntKeys();
        myTableName = s.myTableName;
        myFieldName = s.myFieldName;
        myLastIndex = s.myLastIndex;
        myLastCollection = s.myLastCollection;
        lastDataColumnNumber = s.lastDataColumnNumber;
        if (s.lastRowNumbers != null) {
            lastRowNumbers = new int[s.lastRowNumbers.length];
            System.arraycopy(s.lastRowNumbers,0,lastRowNumbers,0,lastRowNumbers.length);
        }
        // don't clone the property change object I guess
        //propertyChange = (PropertyChangeSupport) s.propertyChange.clone();
        valueMode = s.valueMode;
    }

    private void getRowNumbers() {
        checkArraySizeConsistency();
        lastRowNumbers = null;
        for (int i=0;i<stringKeyNameValues.length-1;i++) {
            int[] rowNumbers = myLastIndex.getRowNumbers(stringKeyNameValues[i+1],intKeyValues[i]);
            if (lastRowNumbers == null) {
                lastRowNumbers = rowNumbers;
            } else {
                int[] newRowNumbers = new int[lastRowNumbers.length+rowNumbers.length];
                System.arraycopy(lastRowNumbers,0,newRowNumbers,0,lastRowNumbers.length);
                System.arraycopy(rowNumbers,0,newRowNumbers,lastRowNumbers.length,rowNumbers.length);
                lastRowNumbers = newRowNumbers;
            }
        }
    }
    
    private int getDataColumnNumber() {
        lastDataColumnNumber = myLastIndex.getMyTableDataSet().checkColumnPosition(getMyFieldName());
        return lastDataColumnNumber;
    }

    public float retrieveValue(TableDataSetCollection y) {
        updateLinks(y);
        return calculateValue();
    }

    /**
     * @return
     */
    private float calculateValue() {
        if (lastRowNumbers.length>1 && valueMode == SINGLE_VALUE_MODE) {
            throw new MultipleValueException("Multiple matching index values in SINGLE_VALUE_MODE "+this);
        }
        if (lastRowNumbers.length<1 && isErrorOnMissingValues()) {
            throw new MissingValueException("No matching index values for "+this);
        }
        float sum=0;
        float denominator= 0;
        for (int r=0;r<lastRowNumbers.length;r++){
            sum += myLastIndex.getMyTableDataSet().getValueAt(lastRowNumbers[r],lastDataColumnNumber);
            denominator++;
        }
        if (valueMode == AVERAGE_MODE && denominator !=0) {
            return sum/denominator;
        }
        return sum;
    }

    /**
     * @param m
     * @return  boolean value that indicates whether the index is valid
     */
    public boolean hasValidIndexes(TableDataSetCollection m) {
        boolean current = true;
        current = current && (myLastCollection ==m);
        return current;
    }
    
    private void updateLinks(TableDataSetCollection y) {
        boolean getNewIndex = true;
        if (myLastIndex != null) {
            getNewIndex=false;
        }
        if (myLastCollection != y) {
            myLastCollection = y;
            getNewIndex = true;
        }
        if (getNewIndex) {
            myLastIndex = myLastCollection.getTableDataSetIndex(getMyTableName(), stringKeyNameValues[0], intKeyNameValues[0]);
            myLastIndex.addUser(this);
            getRowNumbers();
            getDataColumnNumber();
        }
        if (lastRowNumbers == null) {
            getRowNumbers();
        }
        if (lastDataColumnNumber == -1) {
            getDataColumnNumber();
        }
    }
    
    public void putValue(TableDataSetCollection y, float value) {
        updateLinks(y);
        putValues(value);
    }

    private void putValues(float compositeValue) {
        if (lastRowNumbers.length>1 && valueMode == SINGLE_VALUE_MODE) {
            throw new RuntimeException("Multiple matching index values in SINGLE_VALUE_MODE "+this);
        }
        float value= compositeValue;
        if (valueMode == SUM_MODE) {
            value = compositeValue/lastRowNumbers.length;
        }
        for (int r=0;r<lastRowNumbers.length;r++){
            myLastIndex.getMyTableDataSet().setValueAt(lastRowNumbers[r],lastDataColumnNumber, value);
        }
        
    }

    public void setMyTableName(String myTableName) {
        this.myTableName = myTableName;
        //System.out.println("Table name now " + myTableName);
        myLastIndex=null;
        myLastCollection=null;
    }

    public String getMyTableName() {
        return myTableName;
    }

    /**
	 * The addPropertyChangeListener method was generated to support the
	 * propertyChange field.
	 */
    public synchronized void addPropertyChangeListener(java.beans.PropertyChangeListener listener) {
        getPropertyChange().addPropertyChangeListener(listener);
    }
    /**
	 * The firePropertyChange method was generated to support the
	 * propertyChange field.
	 */
    public void firePropertyChange(String propertyName, Object oldValue, Object newValue) {
        getPropertyChange().firePropertyChange(propertyName, oldValue, newValue);
    }
    protected java.beans.PropertyChangeSupport getPropertyChange() {
        if (propertyChange == null) {
            propertyChange = new java.beans.PropertyChangeSupport(this);
        };
        return propertyChange;
    }

    private void updateIntKeys()  {
        intKeyValues = new int[intKeyNameValues.length-1][];
        NumberFormatException lastExceptionFound = null;
        for (int r=1;r<intKeyNameValues.length;r++) {
            intKeyValues[r-1] = new int[intKeyNameValues[r].length];
            for (int i=0;i<intKeyValues[r-1].length;i++) {
                try {
                    if (intKeyNameValues[r][i].length()>0) { 
                        intKeyValues[r-1][i] = Integer.valueOf(intKeyNameValues[r][i]).intValue();
                    } else {
                        intKeyValues[r-1][i]=0;
                    }
                } catch (java.lang.NumberFormatException e) {
                    lastExceptionFound = e;;
                }
                
            }
        }
    }

    public void setMyFieldName(String myFieldName) {
        this.myFieldName = myFieldName;
        //myLastCollection = null;
        //myLastIndex = null;
        lastDataColumnNumber = -1;
    }
    
    /**
     * To manually set the data column number.  You have to know what column number
     * has the data you are interested in; if you don't use setMyFieldName instead.
     * @param myDataColumnNumber
     */
    public void setMyDataColumn(String dataColumnName, int dataColumnNumber) {
        myFieldName = dataColumnName;
        lastDataColumnNumber = dataColumnNumber;
    }

    public String getMyFieldName() {
        return myFieldName;
    }
    
    
    public String toString() {
        StringBuffer myInfo = new StringBuffer();
        myInfo.append(getMyTableName());
        myInfo.append(" ");
        myInfo.append(getMyFieldName());
        myInfo.append(" (");
        for (int s=0;s<stringKeyNameValues[0].length;s++) {
            myInfo.append(stringKeyNameValues[0][s]);
            for (int v=1;v<Math.min(stringKeyNameValues.length,4);v++) {
                myInfo.append(":");
                myInfo.append(stringKeyNameValues[v][s]);
            }
            if (stringKeyNameValues.length>4) myInfo.append("..."+(stringKeyNameValues.length-4)+" more...");
            myInfo.append(" ");
        }
        for (int i=0;i<intKeyNameValues[0].length;i++) {
            myInfo.append(intKeyNameValues[0][i]);
            for (int v=1;v<Math.min(intKeyNameValues.length,4);v++) {
                myInfo.append(":");
                myInfo.append(intKeyNameValues[v][i]);
            }
            if (intKeyNameValues.length>4) myInfo.append("..."+(intKeyNameValues.length-4)+" more...");
            myInfo.append(" ");
        }
        myInfo.append(")");
        return myInfo.toString();
    }
    /**
     * @return Returns the intKeyNameValues.
     */
    public String[][] getIntKeyNameValues() {
        return intKeyNameValues;
    }

    /**
     * @param intKeyNameValues The intKeyNameValues to set.
     */
    public void setIntKeyNameValues(String[][] intKeyNameValues) {
        this.intKeyNameValues = intKeyNameValues;
        updateIntKeys();
        myLastCollection= null;
        myLastIndex = null;
    }

    /**
     * @return Returns the stringKeyNameValues.
     */
    public String[][] getStringKeyNameValues() {
        return stringKeyNameValues;
    }

    /**
     * @param stringKeyNameValues The stringKeyNameValues to set.
     */
    public void setStringKeyNameValues(String[][] stringKeyNameValues) {
        this.stringKeyNameValues = stringKeyNameValues;
        myLastCollection= null;
        myLastIndex = null;
    }

    public void setValueMode(int valueMode) {
        this.valueMode = valueMode;
    }

    public int getValueMode() {
        return valueMode;
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataSetIndex.ChangeListener#indexChanged()
     */
    public void indexChanged(TableDataSetIndex r) {
        lastRowNumbers=null;
    }

    /**
     * @param newFieldName
     * @param newFieldValues
     */
    public void addNewStringKey(String newFieldName, String[] newFieldValues) {
        if (newFieldValues.length >0) {
            String[][] oldKeyValues = stringKeyNameValues;
            
            // number of permutations and combinations
            int numRows = (oldKeyValues.length-1)*newFieldValues.length;
            stringKeyNameValues = new String[numRows+1][];
            stringKeyNameValues[0] = new String[oldKeyValues[0].length+1];
            System.arraycopy(oldKeyValues[0],0,stringKeyNameValues[0],0,oldKeyValues[0].length);
            stringKeyNameValues[0][oldKeyValues[0].length] = newFieldName;

            //also need to make more int key rows
            String[][] oldIntKeyNameValues = intKeyNameValues;
            intKeyNameValues = new String[numRows+1][];
            intKeyNameValues[0] = oldIntKeyNameValues[0];
            
            for (int originalRow=1;originalRow<oldKeyValues.length;originalRow++) {
                for (int addingRow=0;addingRow<newFieldValues.length;addingRow++) {
                    int newRow = (originalRow-1)*newFieldValues.length+addingRow+1;
                    stringKeyNameValues[newRow] = new String[oldKeyValues[originalRow].length+1];
                    System.arraycopy(oldKeyValues[originalRow],0,stringKeyNameValues[newRow],0,oldKeyValues[originalRow].length);
                    stringKeyNameValues[newRow][oldKeyValues[0].length] = newFieldValues[addingRow];

                    // and for int keys
                    intKeyNameValues[newRow] = new String[oldIntKeyNameValues[originalRow].length];
                    System.arraycopy(oldIntKeyNameValues[originalRow],0,intKeyNameValues[newRow],0,oldIntKeyNameValues[originalRow].length);
                }
                
            }
            updateIntKeys();
            myLastCollection= null;
            myLastIndex = null;
        }
       }

    /**
     * @param newFieldName
     * @param newFieldValues
     */
    public void addNewIntKey(String newFieldName, String[] newFieldValues) {
        if (newFieldValues.length>0) {
            String[][] oldKeyValues = intKeyNameValues;
            
            // number of permutations and combinations
            int numRows = (oldKeyValues.length-1)*newFieldValues.length;
            intKeyNameValues = new String[numRows+1][];
            intKeyNameValues[0] = new String[oldKeyValues[0].length+1];
            System.arraycopy(oldKeyValues[0],0,intKeyNameValues[0],0,oldKeyValues[0].length);
            intKeyNameValues[0][oldKeyValues[0].length] = newFieldName;
            
            //also need to make more string key rows
            String[][] oldStringKeyNameValues = stringKeyNameValues;
            stringKeyNameValues = new String[numRows+1][];
            stringKeyNameValues[0] = oldStringKeyNameValues[0];
            
            for (int originalRow=1;originalRow<oldKeyValues.length;originalRow++) {
                for (int addingRow=0;addingRow<newFieldValues.length;addingRow++) {
                    int newRow = (originalRow-1)*newFieldValues.length+addingRow+1;
                    intKeyNameValues[newRow] = new String[oldKeyValues[originalRow].length+1];
                    System.arraycopy(oldKeyValues[originalRow],0,intKeyNameValues[newRow],0,oldKeyValues[originalRow].length);
                    intKeyNameValues[newRow][oldKeyValues[0].length] = newFieldValues[addingRow];
                    // and for string keys
                    stringKeyNameValues[newRow] = new String[oldStringKeyNameValues[originalRow].length];
                    System.arraycopy(oldStringKeyNameValues[originalRow],0,stringKeyNameValues[newRow],0,oldStringKeyNameValues[originalRow].length);
                }
                
            }
            updateIntKeys();
            myLastCollection= null;
            myLastIndex = null;
        }
    }
    
    /* (non-Javadoc)
     * @see java.lang.Object#clone()
     */
    public Object clone() throws CloneNotSupportedException {
        TableDataSetIndexedValue newOne = (TableDataSetIndexedValue) super.clone();
        newOne.stringKeyNameValues = (String[][]) this.stringKeyNameValues.clone();
        for (int i=0;i<newOne.stringKeyNameValues.length;i++) newOne.stringKeyNameValues[i]= (String[]) this.stringKeyNameValues[i].clone();
        newOne.intKeyNameValues = (String[][]) this.intKeyNameValues.clone();
        for (int i =0;i<newOne.intKeyNameValues.length;i++) newOne.intKeyNameValues[i] = (String[]) this.intKeyNameValues[i].clone();
        newOne.intKeyValues = (int[][]) this.intKeyValues.clone();
        for (int i =0;i<newOne.intKeyValues.length;i++) newOne.intKeyValues[i]=(int[]) this.intKeyValues[i].clone();
        if (this.lastRowNumbers!=null) newOne.lastRowNumbers = (int[]) this.lastRowNumbers.clone();
        newOne.propertyChange = null;
        return newOne;
    }

    /**
     * 
     */
    public float retrieveValue() {
        if (myLastCollection!=null) {
            return retrieveValue(myLastCollection);
        }
        if (isErrorOnMissingValues()) {
            throw new RuntimeException("Tried to retrieve a value with a TableDataSetIndexedValue without having first set a TableDataSetCollection");
        }
        return 0;
        
    }

    /**
     * @param collection
     * @return  String indicating the retrieval status
     */
    public String retrieveValueStatusString(TableDataSetCollection collection) {
        try {
            updateLinks(collection);
        } catch (RuntimeException e) {
            return "Error updating links "+e;
        }
        if (lastRowNumbers.length==0) {
            return "no matching rows";
        }
        if (lastRowNumbers.length>1 && valueMode == SINGLE_VALUE_MODE) {
            return "Multiple matching index values in SINGLE_VALUE_MODE";
        } 
        return String.valueOf(retrieveValue(collection));
    }

    /**
     * @param e
     */
    public void updateIntKeys(TableModelEvent e, String[][] newIntKeyNameValues) {
        boolean updateAll = true;
        if (e.getType()== e.UPDATE) {
            if (e.getFirstRow()>0 && e.getLastRow()<=intKeyValues.length) {
                updateAll=false;
                for (int i = e.getFirstRow(); i<= e.getLastRow();i++ ) {
                    for (int c=0;c<intKeyValues[i-1].length;c++) {
                        intKeyNameValues[i][c] = newIntKeyNameValues[i][c];
                        try {
                            intKeyValues[i-1][c] = Integer.valueOf(intKeyNameValues[i][c]).intValue();
                        } catch (java.lang.NumberFormatException e1) {
                            //  if the number format is wrong we won't do anything
                        }
                    }
                }
            } 
        }
        if (updateAll) {
            setIntKeyNameValues(newIntKeyNameValues);
        } else {
            getRowNumbers();
        }
    }

    public void setStringValues(String[][] stringValues) {
        if (stringKeyNameValues.length != stringValues.length+1) {
            String[][] oldStringKeyNameValues = stringKeyNameValues;
            stringKeyNameValues = new String[stringValues.length+1][];
            stringKeyNameValues[0] = oldStringKeyNameValues[0];
        } 
        for (int i=0;i<stringValues.length;i++) {
            stringKeyNameValues[i+1] = stringValues[i];
        }
        lastRowNumbers = null;
    }

    public void setIntValues(int[][] intValues) {
        if (intKeyNameValues.length != intValues.length+1) {
            String[][] oldIntKeyNameValues = intKeyNameValues;
            intKeyNameValues = new String[intValues.length+1][];
            intKeyNameValues[0] = oldIntKeyNameValues[0];
        } 
        for (int i=0;i<intValues.length;i++) {
            for (int j=0;j<intValues[i].length;j++) {
                intKeyNameValues[i+1][j] = String.valueOf(intValues[i][j]);
            }
        }
        intKeyValues= intValues;
        lastRowNumbers = null;
    }

    public int getMyDataColumnNumber() {
        return lastDataColumnNumber;
    }


}
