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

import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;

/**
 * @author jabraham
 *
 * To change the template for this generated type comment go to
 * Window - Preferences - Java - Code Generation - Code and Comments
 */
public class TableDataSetIndex implements TableDataSet.ChangeListener {

    public int[] getStringColumnNumbers() {
        return stringColumnNumbers;
    }
    
    public int[] getIntColumnNumbers() {
        return intColumnNumbers;
    }
    
    interface ChangeListener {
        public abstract void indexChanged(TableDataSetIndex r);
    }
    
    Set myUsers = new HashSet();
    
    public void addUser(ChangeListener r) {
        myUsers.add(new WeakReference(r));
    }
    
    private void notifyListeners() {
        Iterator it = myUsers.iterator();
        while (it.hasNext()) {
            WeakReference r = (WeakReference) it.next();
            if (r.get() == null) {
                it.remove();
            } else {
                ((ChangeListener) r.get()).indexChanged(this);
            }
        }
    }
    
    public void dispose() {
        // free up some memory and stop regenerating indices
        myTopLevelHashMap = null; // not necessary but might free up memory faster
        if (myTableDataSet!=null) {
            myTableDataSet.removeChangeListener(this);
        }
        myTableDataSet=null;
    }
    
    private String[] stringColumnNames;
    private String[] intColumnNames;
    private int[] stringColumnNumbers;
    private int[] intColumnNumbers;
    private HashMap myTopLevelHashMap;
    private final String tableName;
    
    private TableDataSet myTableDataSet;
    private TableDataSetCollection myCollection;

    /**
     * 
     */
   // public TableDataSetIndex(TableDataSet myTable) {
    //    myTableDataSet = myTable;
    //    myTableDataSet.addChangeListener(this);
    //}
    
    public TableDataSetIndex(TableDataSetCollection myCollection, String tableNameParam) {
        tableName = tableNameParam;
        if (tableName==null) {
            throw new RuntimeException("gotta have a table name for a TableDataSetIndex");
        }
        myTableDataSet = myCollection.getTableDataSet(tableName);
        this.myCollection = myCollection;
   }
    
    private void buildIndex() {
        myTopLevelHashMap = new HashMap();
        for (int row=1;row<=getMyTableDataSet().getRowCount();row++) {
            HashMap currentHashMap = myTopLevelHashMap;
            for (int key = 0;key < stringColumnNumbers.length+intColumnNumbers.length;key++) { 
                Object keyValue = null;
                if (key < stringColumnNumbers.length) {
                    keyValue = myTableDataSet.getStringValueAt(row,stringColumnNumbers[key]);
                } else {
                    keyValue = new Integer((int) myTableDataSet.getValueAt(row,intColumnNumbers[key-stringColumnNumbers.length]));
                }
                if (key == stringColumnNumbers.length + intColumnNumbers.length-1) {
                    // we're at the last key now
                    ArrayList theArrayList = (ArrayList) currentHashMap.get(keyValue);
                    if (theArrayList == null) {
                        theArrayList= new ArrayList();
                        currentHashMap.put(keyValue,theArrayList);
                    }
                    theArrayList.add(new Integer(row));
                } else {
                    HashMap nextHashMap = (HashMap) currentHashMap.get(keyValue);
                    if (nextHashMap ==null) {
                        nextHashMap = new HashMap();
                        currentHashMap.put(keyValue,nextHashMap);
                    }
                    currentHashMap = nextHashMap;
                }
            }
        }
        
    }
    
    public void setIndexColumns(String[] stringColumnNames, String[] intColumnNames) {
        this.stringColumnNames= stringColumnNames;
        this.intColumnNames = intColumnNames;
        stringColumnNumbers = new int[stringColumnNames.length];
        for (int c=0;c<stringColumnNames.length;c++) {
            stringColumnNumbers[c] = getMyTableDataSet().checkColumnPosition(stringColumnNames[c]);
        }
        intColumnNumbers = new int[intColumnNames.length];
        for (int c=0;c<intColumnNames.length;c++) {
            intColumnNumbers[c] = myTableDataSet.checkColumnPosition(intColumnNames[c]);
        }
        
        myTopLevelHashMap=null;
        String[] allIndexColumnNames = new String[stringColumnNames.length+intColumnNames.length];
        for (int i=0;i<allIndexColumnNames.length;i++) {
            if (i<stringColumnNames.length) {
                allIndexColumnNames[i]=stringColumnNames[i];
            } else {
                allIndexColumnNames[i] = intColumnNames[i-stringColumnNames.length];
            }
        }
        myTableDataSet.addChangeListener(this);
        myTableDataSet.setIndexColumnNames(allIndexColumnNames);
        notifyListeners();
    }
    
    public int[] getRowNumbers(String[] stringKeys, int[] intKeys) {
        if (myTopLevelHashMap==null) buildIndex();
        ArrayList rows = null;
        HashMap currentHashMap = myTopLevelHashMap;
        if (stringColumnNumbers.length==0 && intColumnNumbers.length==0) {
            // no conditions, return all rows
            int[] rowsArray = new int[getMyTableDataSet().getRowCount()];
            for (int r=1;r<=rowsArray.length;r++) {
                rowsArray[r-1] = r;
            }
            return rowsArray;
        }
        for (int key = 0;key < stringColumnNumbers.length+intColumnNumbers.length;key++) { 
            Object keyValue = null;
            if (key < stringColumnNumbers.length) {
                keyValue = stringKeys[key];
            } else {
                keyValue = new Integer(intKeys[key-stringColumnNumbers.length]);
            }
            if (key == stringColumnNumbers.length + intColumnNumbers.length-1) {
                // we're at the last key now
                rows = (ArrayList) currentHashMap.get(keyValue);
            } else {
                HashMap nextHashMap = (HashMap) currentHashMap.get(keyValue);
                if (nextHashMap ==null) {
                    nextHashMap = new HashMap();
                    //currentHashMap.put(keyValue,nextHashMap);
                }
                currentHashMap = nextHashMap;
            }
        }
        if (rows == null) return new int[0];
        int[] rowsArray = new int[rows.size()];
        for (int i=0;i<rowsArray.length;i++) {
            rowsArray[i]= ((Integer) rows.get(i)).intValue();
        }
        return rowsArray;
    }

    public TableDataSet getMyTableDataSet() {
        if (myTableDataSet == null) {
            myTableDataSet = myCollection.getTableDataSet(tableName);
            indexValuesChanged();
        }
        return myTableDataSet;
    }

    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataSet.ChangeListener#indexValuesChanged()
     */
    public void indexValuesChanged() {
        myTopLevelHashMap=null;
        notifyListeners();
    }

    /**
     * 
     */
    public void tableDataSetShouldBeReloaded() {
        myTableDataSet = null;
    }

    public String getTableName() {
        return tableName;
    }


}
