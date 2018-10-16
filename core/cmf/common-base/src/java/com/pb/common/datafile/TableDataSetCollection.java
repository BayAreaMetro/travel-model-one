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

import org.apache.log4j.Logger;

import java.io.IOException;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

/**
 * @author jabraham
 * 
 * To change the template for this generated type comment go to Window -
 * Preferences - Java - Code Generation - Code and Comments
 */
public class TableDataSetCollection {
    
    private static Logger logger = Logger.getLogger(TableDataSetCollection.class);
    
    private HashMap readTableDataSets = new HashMap();
    private ArrayList cacheOfCurrentlyUsedIndices = new ArrayList();
    private TableDataReader myReader = null;
    private TableDataWriter myWriter = null;

    public TableDataSetCollection(TableDataReader reader, TableDataWriter writer) {
        setMyReader(reader);
        setMyWriter(writer);
    }

    public synchronized TableDataSetIndex getTableDataSetIndex(String tableName, String[] stringKeyColumnNames, String[] intKeyColumnNames) {
        TableDataSetIndex theIndex = null;
        TableDataSet theTableDataSet = getTableDataSet(tableName);
        Iterator it = cacheOfCurrentlyUsedIndices.iterator();
        while (it.hasNext() && theIndex == null) {
            WeakReference r = (WeakReference) it.next();
            TableDataSetIndex anIndex = (TableDataSetIndex) r.get();
            if (anIndex != null) {
                if (anIndex.getTableName().equals(tableName)) {
                    theIndex = anIndex; // assume they match then prove
										// otherwise
                    if (anIndex.getStringColumnNumbers().length != stringKeyColumnNames.length
                        || anIndex.getIntColumnNumbers().length != intKeyColumnNames.length) {
                        theIndex = null;
                    } else {
                        for (int j = 0; j < stringKeyColumnNames.length; j++) {
                            int column = theTableDataSet.getColumnPosition(stringKeyColumnNames[j]);
                            if (column != anIndex.getStringColumnNumbers()[j]) {
                                theIndex = null;
                            }
                        }
                        for (int j = 0; j < intKeyColumnNames.length; j++) {
                            int column = theTableDataSet.getColumnPosition(intKeyColumnNames[j]);
                            if (column != anIndex.getIntColumnNumbers()[j]) {
                                theIndex = null;
                            }
                        }
                    }

                }
            } else {
                // null weak reference
                it.remove();
            }
        }
        if (theIndex == null) {
            theIndex = new TableDataSetIndex(this, tableName);
            theIndex.setIndexColumns(stringKeyColumnNames, intKeyColumnNames);
            cacheOfCurrentlyUsedIndices.add(new WeakReference(theIndex));
        }
        return theIndex;
    }

    /**
	 * @param name
	 * @return the TableDataSet requested
	 */
    public synchronized TableDataSet getTableDataSet(String name) {
        TableDataSet theTable = (TableDataSet) readTableDataSets.get(name);
        if (theTable == null) {
            try {
                logger.info("reading table "+name);
                theTable = getMyReader().readTable(name);
            } catch (IOException e) {
                e.printStackTrace();
            }
            if (theTable == null)
                throw new RuntimeException("Can't read in table " + name);
            readTableDataSets.put(name, theTable);
        }
        return theTable;
    }
    
    public synchronized void flushAndForget(TableDataSet me) {
        if (me.isDirty()) {
            try {
                logger.info("writing table "+me.getName() + ".  Table has " + me.getRowCount() + " rows");
                getMyWriter().writeTable(me, me.getName());
            } catch (IOException e1) {
                e1.printStackTrace();
                throw new RuntimeException("Can't write out table " + me.getName());
            }

        }
        readTableDataSets.remove(me.getName());
    }

    /*
	 * (non-Javadoc)
	 * 
	 * @see com.hbaspecto.calibrator.ModelInputsAndOutputs#flush()
	 */
    public synchronized void flush() {
        Iterator it = readTableDataSets.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry e = (Map.Entry) it.next();
            TableDataSet t = (TableDataSet) e.getValue();
            if (t.isDirty()) {
                try {
                    logger.info("writing table "+t.getName() + ".  Table has " + t.getRowCount() + " rows");
                    getMyWriter().writeTable(t, (String) e.getKey());
                } catch (IOException e1) {
                    e1.printStackTrace();
                    throw new RuntimeException("Can't write out table " + e.getKey());
                }
            }
        }
        getMyWriter().close();

    }
    
    /*
	 * Call flush first if any changes need to be written out
	 * 
	 * @see com.hbaspecto.calibrator.ModelInputsAndOutputs#invalidate()
	 */
    public synchronized void  invalidate() throws IOException {
        readTableDataSets.clear();
//        cacheOfCurrentlyUsedIndices.clear();
        Iterator it = cacheOfCurrentlyUsedIndices.iterator();
        while (it.hasNext()) {
            TableDataSetIndex x = (TableDataSetIndex) ((WeakReference) it.next()).get();
            if (x!=null) x.tableDataSetShouldBeReloaded();
            else it.remove();
        }
    }

    synchronized void  setMyReader(TableDataReader myReader) {
        this.myReader = myReader;
    }

    TableDataReader getMyReader() {
        return myReader;
    }

    synchronized void  setMyWriter(TableDataWriter myWriter) {
        this.myWriter = myWriter;
    }

    TableDataWriter getMyWriter() {
        return myWriter;
    }

    /**
     * @param landInventoryTable
     */
    public synchronized void addTableDataSet(TableDataSet aTable) {
        readTableDataSets.put(aTable.getName(),aTable);
        aTable.setDirty(true);
    }

    /**
     * 
     */
    public synchronized void close() {
        myReader.close();
        myWriter.close();
        
    }

}
