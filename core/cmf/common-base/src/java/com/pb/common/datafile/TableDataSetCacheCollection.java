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

import java.io.IOException;
import java.lang.ref.Reference;
import java.lang.ref.ReferenceQueue;
import java.lang.ref.SoftReference;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.apache.log4j.Logger;

/**
 * @author jabraham
 * 
 * To change the template for this generated type comment go to Window -
 * Preferences - Java - Code Generation - Code and Comments
 */
public class TableDataSetCacheCollection extends TableDataSetCollection implements TableDataSet.TableDataSetWatcher {
    
    private static Logger logger = Logger.getLogger(TableDataSetCollection.class);
    private HashMap readDataSoftReferences = new HashMap();
    
    private HashMap dirtyDataSetMap = new HashMap();

    ReferenceQueue myReferenceQueue = new ReferenceQueue();

    public TableDataSetCacheCollection(TableDataReader reader, TableDataWriter writer) {
        super(reader,writer);
//        Runnable cleanUp = new Runnable() {
//            public void run() {
//                while (true) {
//                    try {
//                        TableDataSetSoftReference fred = (TableDataSetSoftReference) myReferenceQueue.remove();
//                        logger.info("TableDataSet "+fred.name+" is gone");
//                        readDataSoftReferences.remove(fred.name);
//                    } catch (InterruptedException e) {
//                        throw new RuntimeException("TableDataSetCacheCollection cleanup thread is being interrupted",e);
//                    }
//                }
//            }
//        };
//        Thread cleanUpThread = new Thread(cleanUp);
//        cleanUpThread.start();
    }
    
    

    /**
	 * @param name
	 * @return the TableDataSet requested
	 */
    public synchronized TableDataSet getTableDataSet(String name) {
        // first see if we can remove references to datasets that we don't use
        TableDataSetSoftReference fred;
        fred = (TableDataSetSoftReference) myReferenceQueue.poll();
        while (fred !=null) {
            if (logger.isDebugEnabled()) logger.debug("Removing key "+fred.name+" from list of TableDataSets read");
            readDataSoftReferences.remove(fred.name);
            fred = (TableDataSetSoftReference) myReferenceQueue.poll();
        }
        SoftReference wr = (SoftReference) readDataSoftReferences.get(name);
        TableDataSet theTable = null;
        if (wr!=null) {
            theTable = (TableDataSet) wr.get();
        }
        // could be the case that the soft reference was cleared before it became dirty, check
        // to see if we can find it in our dirty list.
        if (theTable == null) {
            theTable = (TableDataSet) dirtyDataSetMap.get(name);
            if (theTable!=null) {
                addTableToTempStorage(theTable);
            }
        }
        if (theTable == null) {
            try {
                if (logger.isDebugEnabled()) logger.debug("reading table "+name);
                theTable = getMyReader().readTable(name);
                double freeMem = Runtime.getRuntime().freeMemory()/1000000.0;
                if (logger.isDebugEnabled()) logger.debug("Memory is "+freeMem);
            } catch (IOException e) {
                e.printStackTrace();
            }
            if (theTable == null)
                throw new RuntimeException("Can't read in table " + name);
            addTableToTempStorage(theTable);
            theTable.addFinalizingListener(this);
        }
        return theTable;
    }



    private void addTableToTempStorage(TableDataSet theTable) {
        if (logger.isDebugEnabled()) logger.debug("Creating temporary references for "+theTable.getName());
        TableDataSetSoftReference fred = new TableDataSetSoftReference(theTable, myReferenceQueue);
        readDataSoftReferences.put(theTable.getName(), fred);
    }

    public synchronized void flushAndForget(TableDataSet me) {
        if (me.isDirty()) {
                writeTableToDisk(me);
        }
        //TODO remove this next line, shouldn't need to manually remove it from the SoftReferences.
        readDataSoftReferences.remove(me.getName());
        dirtyDataSetMap.remove(me.getName());
    }


    private void writeTableToDisk(TableDataSet me) {
        try {
            if (logger.isDebugEnabled()) logger.debug("writing table "+me.getName() + ".  Table has " + me.getRowCount() + " rows");
            getMyWriter().writeTable(me, me.getName());
            me.setDirty(false);
            dirtyDataSetMap.remove(me.getName());
        } catch (IOException e1) {
            e1.printStackTrace();
            throw new RuntimeException("Can't write out table " + me.getName());
        }
    }

    /*
	 * (non-Javadoc)
	 * 
	 * @see com.hbaspecto.calibrator.ModelInputsAndOutputs#flush()
	 */
    public synchronized void flush() {
        Iterator it = dirtyDataSetMap.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry e = (Map.Entry) it.next();
            TableDataSet t = (TableDataSet) e.getValue();
            if (t.isDirty()) {
                writeTableToDisk(t);
            } else {
               // if (logger.isDebugEnabled()) logger.debug("*don't need to flush* table "+t.getName()+" as it's not dirty");
            }
        }
        dirtyDataSetMap.clear();
        it = readDataSoftReferences.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry e = (Map.Entry) it.next();
            TableDataSet t = (TableDataSet) ((Reference) e.getValue()).get();
            if (t == null) {
                if (logger.isDebugEnabled()) logger.debug("soft reference to table "+e.getKey()+" has been cleared");
            } else {
                if (t.isDirty()) {
                    logger.error("Dirty table not in dirtyDataSetMap");
                    writeTableToDisk(t);
                } else {
               //     if (logger.isDebugEnabled()) logger.debug("*don't need to flush* table "+t.getName()+" as it's not dirty");
                }
            }
        }
    }
    
    /*
	 * Call flush first if any changes need to be written out
	 * 
	 * @see com.hbaspecto.calibrator.ModelInputsAndOutputs#invalidate()
	 */
    public synchronized void  invalidate() throws IOException {
        //TODO should we do something to remove them from the reference queue?
        readDataSoftReferences.clear();
        dirtyDataSetMap.clear();
        super.invalidate();
    }
    /**
     * @param aTable the TableDataSet to add to the colleciton
     */
    public synchronized void addTableDataSet(TableDataSet aTable) {
        addTableToTempStorage(aTable);
        aTable.setDirty(true);
        aTable.addFinalizingListener(this);
    }


    public synchronized void isBeingForgotten(TableDataSet t) {
        if (logger.isDebugEnabled()) {
            double freeMem = Runtime.getRuntime().freeMemory() / 1000000.0;
            logger.debug("getting ready to forget about table " + t.getName() + " freeMem="
                    + freeMem);
        }
    }

    public synchronized void isDirty(TableDataSet s) {
        if (logger.isDebugEnabled()) logger.debug("Table "+s+" is now dirty, creating a new soft reference to it now");
        dirtyDataSetMap.put(s.getName(),s);
        addTableToTempStorage(s);
    }

    @Override
    protected void finalize() throws Throwable {
        // this could be called at the end of the run, before all of the TableDatasets have been finalized
        // So we have to write out any dirty datasets.
        try {
            flush();
        } finally {
            super.finalize();
        }
        
    }
}
