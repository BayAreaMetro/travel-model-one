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
package com.pb.common.calculator;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.log4j.Logger;

import com.pb.common.matrix.CollapsedMatrixCollection;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixCollection;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import com.pb.common.matrix.TpplusMatrixReader64;


/**
 * Provides data management capabilities.
 *
 * @author    Tim Heier
 * @version   1.0, 8/3/2003
 */
public class MatrixDataManager implements Serializable {

    private static final long serialVersionUID = -8079023531897975508L;

    protected transient Logger logger = Logger.getLogger(
            "com.pb.common.calculator");

    private MatrixDataServerIf mDataServer;
    private static MatrixDataManager instance = new MatrixDataManager();

    //Holds references to each matrix object (excluding matrices in a matrix collection)
    private Matrix[] mValues = new Matrix[0];

    //Holds list of matrix entries read into memory
    private ArrayList<DataEntry> mEntryList = new ArrayList<DataEntry>();

    //Holds references to each matrix collection
    private MatrixCollection[] mGroupValues = new MatrixCollection[0];

    //Maps a matrix name to a matrix collection index value. Built when matrices
    //are read but accessed at parse time
    private HashMap<String, Integer> mMatrixNameToCollectionIndex = new HashMap<String, Integer>(
            100);
//    private volatile Map<String, Integer> mMatrixNameToCollectionIndex = new ConcurrentHashMap<String, Integer>(100);

    //Holds a matrix name. The position in the array is used as a reverse lookup to get
    //the name at solve time.
    private ArrayList<String> mMatrixNames = new ArrayList<String>(100); 

    // ----- Subscripted matrix array handling e.g. IVT[TIMEPERIOD] :
    // Allows matrix references with an array-like syntax, while enabling fast lookups
    // instead of string concatenation during model application.

    // Holds mapping of matrix-array name to index value
    private HashMap<String, Integer> mArrayNameLookup = new HashMap<String, Integer>();
    // Holds reverse mapping of matrix-array index value to another map of array-subscript:index-value.
    private HashMap<Integer, HashMap<Integer, Integer>> mArrayMappingToIndex = new HashMap<Integer, HashMap<Integer, Integer>>();

    // Holds mapping of matrix-collection-array name to index value
    private HashMap<String, Integer> mArrayGroupNameLookup = new HashMap<String, Integer>();
    // Holds reverse mapping of matrix-collection-array index value to another map of array-subscript:index-value.
    private HashMap<Integer, HashMap<Integer, String>> mArrayGroupToIndex = new HashMap<Integer, HashMap<Integer, String>>();

    private MatrixDataManager() {
    }

    /**
     * this method might be used to set a MatrixDataServer instance that implements remote method calls to a remote
     * storage location for matrices, allowing network access to the Matrix objects as opposed to i/o access.
     * @param mds is an instance of a class that implements MatrixDataServerIF.
     *
     */
    public void setMatrixDataServerObject( MatrixDataServerIf mds ) {
        this.mDataServer = mds;
    }


    /** Returns an instance to the singleton.
     */
    public static MatrixDataManager getInstance() {
        return instance;
    }

    /** Unloads the data that is being stored in memory so heap can be
     * reclaimed by the garbage collector.
     */
    synchronized public void clearData() {
        mValues = new Matrix[0];
        mEntryList.clear();

        mArrayMappingToIndex.clear();
        mArrayNameLookup.clear();

        mArrayGroupNameLookup.clear();
        mArrayGroupToIndex.clear();

        mGroupValues = new MatrixCollection[0];
        mMatrixNameToCollectionIndex.clear();
        mMatrixNames.clear();
    }

    synchronized public void addMatrixEntry(DataEntry entry) {
        throw new UnsupportedOperationException(
                "addMatrixEntry(DataEntry) not supported");
    }

    /** Add an array of matrices to the datamanager.
     *
     * @param matrixEntries
     */
    synchronized public void addMatrixEntries(DataEntry[] matrixEntries) {
        //Holds a map of matrix names and matrix references
        HashMap<String, DataEntry> matrixMap = new HashMap<String, DataEntry>();

        //Maps group names to an ArrayList of matrices in group (group == collection)
        HashMap<String, ArrayList<DataEntry>> collapsedMap = new HashMap<String, ArrayList<DataEntry>>();

        int nEntries = matrixEntries.length;

        for (int i = 0; i < nEntries; i++) {
            //check that there is a matrix name
            String matrixName = matrixEntries[i].name;

            //Skip matrices that are already loaded
            if (isMatrixLoaded(matrixEntries[i])) {
                logger.debug("adding: " + matrixName +
                        " to collection="+ matrixEntries[i].groupName+" is already loaded");
                continue;
            }

            //Keep track of matrices that are part of a collapsed collection
            if (matrixEntries[i].groupName.length() > 0) {
                ArrayList<DataEntry> matrixList = collapsedMap
                        .get(matrixEntries[i].groupName);

                //No entries with this group name exist in map, create a new list for the group
                if (matrixList == null) {
                    matrixList = new ArrayList<DataEntry>();
                }

                matrixList.add(matrixEntries[i]);
                collapsedMap.put(matrixEntries[i].groupName, matrixList);
            }
            //Matrix is not part of a collection
            else {
                matrixMap.put(matrixName, matrixEntries[i]);
            }
        }

        try {
            addMatrices(matrixMap);
        }
        catch (RuntimeException e) {
            logger.fatal( "Exception caught adding matrices to matrixMap in MatrixDataManager" );
            logger.fatal( "contents of matrixMap:" );
            for (Iterator<String> it = matrixMap.keySet().iterator(); it
                    .hasNext();) {
                String matrixName = it.next();
                DataEntry matrixEntry = matrixMap.get(matrixName);
                String fileName = matrixEntry.fileName;
                logger.fatal( String.format( "%-10s %s", matrixName, fileName) );
            }
            throw (e);
        }
        addMatrixCollections(matrixEntries, collapsedMap);

        if (logger.isDebugEnabled()) {
            logger.debug("Loaded matrix summary:");
            for (int m = 0; m < mValues.length; m++) {
                String name = mValues[m].getName();
                logger.debug("matrixName=" + name + ", position=" + m);
            }
        }

        if (logger.isDebugEnabled()) {
            logger.debug("Loaded collapsedMatrix summary:");
            logger.debug("number of collapsed matrix collections=" + mGroupValues.length);
            logger.debug("number of matrices in collections=" + mMatrixNameToCollectionIndex.size());

            Iterator<String> iter = mMatrixNameToCollectionIndex.keySet()
                    .iterator();

            while (iter.hasNext()) {
                String matrixName = iter.next();
                int i = mMatrixNameToCollectionIndex.get(matrixName).intValue();
                logger.debug("collapsedMatrixIndex=" + i + ", matrixName=" + matrixName);
            }
        }
    }

    /**
     * Checks to see if a matrix has been loaded already.
     * Combine matrix name + file name and test for uniqueness.
     */
    private boolean isMatrixLoaded(DataEntry entry) {
        for (int i = 0; i < mEntryList.size(); i++) {
            DataEntry matrixEntry = mEntryList.get(i);

            String loadedName = matrixEntry.name;
            String newName = entry.name;

            if (loadedName.equalsIgnoreCase(newName)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Iterate over matrices and build a linear list of matrix names and values.
     * The map should only contain new matrices that have not been seen before.
     */
    private void addMatrices(HashMap<String, DataEntry> matrixMap) {
        ArrayList<Matrix> newMatrixList = new ArrayList<Matrix>();

        //Iterate over matrix map and read matrices
        for (DataEntry matrixEntry : matrixMap.values()) {

            String name = matrixEntry.name;
            Matrix matrix = getMatrix(matrixEntry);
            if ( matrix == null) {
                RuntimeException e = new RuntimeException();
                logger.error( "MatrixDataManager received a null matrix object for " + name, e );
                throw e;
            }

            newMatrixList.add(matrix);

            if (name.contains("[")) {
                handleArrayMappedDataEntry(matrixEntry, newMatrixList.size());
            }
        }

        combineMatrixValues(newMatrixList);
    }

    /**
     * For DataEntries with an array subscript (e.g. time period), add matrix
     * name to arraymap lookup, using offset of this item in matrix array to
     * calculate its position in the final lookup table.
     *
     * @param entry
     *            DataEntry with an array subscript in its name.
     * @param offset
     *            offset of this item in the current matrix array
     */
    private void handleArrayMappedDataEntry(DataEntry entry, int offset) {
        int leftBrace = entry.name.indexOf("[");
        int rightBrace = entry.name.indexOf("]");

        // Final lookup in matrix array is the previous array length,
        // plus this item's location minus 1.
        int location = mValues.length + offset - 1;

        if (leftBrace == -1 || rightBrace == -1 || rightBrace < leftBrace) {
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received an array matrix name with weird braces. "
                    + e);
            throw e;
        }

        String matrixName = entry.name.substring(0,leftBrace);
        String subscript = entry.name.substring(leftBrace+1,rightBrace);

        int val;
        try {
            val = Integer.parseInt(subscript);
        } catch (NumberFormatException nfe){
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received an array matrix name with a non-integer subscript. " + e);
            throw e;
        }

        // find or create lookup table for this matrix name
        HashMap<Integer, Integer> lookups = null;

        if (mArrayNameLookup.containsKey(matrixName)) {
            lookups = mArrayMappingToIndex.get(mArrayNameLookup.get(matrixName));
        }

        if (lookups == null) {
            // create new hashtable for this matrix/collection name
            lookups = new HashMap<Integer, Integer>();
            int index = mArrayMappingToIndex.size();

            mArrayMappingToIndex.put(index, lookups);
            mArrayNameLookup.put(matrixName, index);
        }

        // ensure this lookup doesn't already exist.
        if (lookups.containsKey(val)) {
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received a duplicate array matrix lookup: "
                    + entry.name + e);
            throw e;
        }

        // add this subscript to the mapping, e.g. 1:43 means IVT[1] -> row 43
        // of matrix array.
        lookups.put(val, location);

        if (logger.isDebugEnabled()) {
            logger.debug("## Added array-mapped matrix: key=" + val
                    + " ; value=" + entry.name + " / " + location);
        }
    }

    private void handleArrayMappedCollectionDataEntry(DataEntry entry) {
        int leftBrace = entry.name.indexOf("[");
        int rightBrace = entry.name.indexOf("]");

        if (leftBrace == -1 || rightBrace == -1 || rightBrace < leftBrace) {
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received an array matrix name with weird braces. "
                    + e);
            throw e;
        }

        String matrixName = entry.name.substring(0, leftBrace);
        String strSubscript = entry.name.substring(leftBrace + 1, rightBrace);

        int subscript;
        try {
            subscript = Integer.parseInt(strSubscript);
        } catch (NumberFormatException nfe) {
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received an array matrix name with a non-integer subscript. "
                    + e);
            throw e;
        }

        // find or create lookup table for this matrix name
        HashMap<Integer, Integer> arraySubscriptLookups = null;

        if (mArrayGroupNameLookup.containsKey(matrixName)) {
            arraySubscriptLookups = mArrayMappingToIndex.get(mArrayGroupNameLookup.get(matrixName));
        }

        if (arraySubscriptLookups == null) {
            // create new hashtable for this matrix/collection name
            arraySubscriptLookups = new HashMap<Integer, Integer>();
            int index = mArrayMappingToIndex.size();

            mArrayMappingToIndex.put(index, arraySubscriptLookups);

            // Store name : index
            this.mArrayGroupNameLookup.put(matrixName, index);
        }

        // ensure this lookup doesn't already exist.
        if (arraySubscriptLookups.containsKey(subscript)) {
            RuntimeException e = new RuntimeException();
            logger.error("MatrixDataManager received a duplicate array matrix lookup: "
                    + entry.name + e);
            throw e;
        }

        // Add reverse-lookup to get matrix name from group and index
        int idx = mArrayGroupNameLookup.get(matrixName);
        HashMap<Integer, String> reverseTable = null;
        if (mArrayGroupToIndex.containsKey(idx)) {
            reverseTable = mArrayGroupToIndex.get(idx);
        } else {
            reverseTable = new HashMap<Integer, String>();
            mArrayGroupToIndex.put(idx, reverseTable);
        }
        reverseTable.put(subscript, entry.name);

        // Determine which collection this matrix belongs to.
        int group = mMatrixNameToCollectionIndex.get(entry.name);
        // add this subscript to the mapping, e.g. 1:7 means IVT[1] -> group 7
        // of matrix collections array.
        arraySubscriptLookups.put(subscript, group);

        if (logger.isDebugEnabled()) {
            logger.debug("## Added array-mapped matrix: key=" + subscript
                    + " ; value=" + entry.name + " / " + group);
        }
    }

    private void combineMatrixValues(ArrayList<Matrix> newMatrixList) {
        //Combine old array with new list
        int newLength = mValues.length + newMatrixList.size();
        Matrix[] newMatrixValues = new Matrix[newLength];

        //Copy existing values
        for (int i = 0; i < mValues.length; i++) {
            newMatrixValues[i] = mValues[i];
        }

        int j = 0;

        //Copy new values to end of existing list
        for (int i = mValues.length; i < newLength; i++) {
            newMatrixValues[i] = newMatrixList.get(j);
            j++;
        }

        mValues = newMatrixValues;
    }

    /*
     * Iterate over collection map and build a map of matrix names and values
     */
    private void addMatrixCollections(DataEntry[] matrixEntries,
            HashMap<String, ArrayList<DataEntry>> collapsedMap) {
        ArrayList<MatrixCollection> tempMatrixCollectionList = new ArrayList<MatrixCollection>();

        //Index of matrix collection
        int mcIndex = mGroupValues.length;

        //Iterate over matrix map and build two parallel lists, one for
        //indexing by name and one for looking up a collection matrix based on a integer index
        Iterator<String> it = collapsedMap.keySet().iterator();

        while (it.hasNext()) {
            String groupName = it.next();
            ArrayList<DataEntry> matrixList = collapsedMap.get(groupName);

            int foundIndex = -1;

            // Identify index matrix in this collection
            for (int j = 0; j < matrixList.size(); j++) {
                DataEntry matrixEntry = matrixList.get(j);
                if (matrixEntry.indexFlag) {
                    foundIndex = j;
                }
            }

            //No matrix in the collection was flagged as the index matrix. Add matrices
            //to an existing matrix collection
            if (foundIndex == -1) {
                addToExistingMatrixCollection(matrixEntries, groupName, matrixList);
                continue;  //skip rest of while loop
            }

            //All of the matrices in the collapsedMap are new matrices including the
            //index matrix so create a new collapsed matrix collection
            DataEntry dEntry = matrixList.get(foundIndex);
            Matrix indexMatrix = getMatrix(matrixList.get(foundIndex));
            if ( indexMatrix == null) {
                RuntimeException e = new RuntimeException();
                logger.error( "MatrixDataManager received a null matrix object for " + dEntry.name, e );
                throw e;
            }
            MatrixCollection mc = new CollapsedMatrixCollection(indexMatrix);

            //Loop over matrices in group and add to collection, don't add the
            //index matrix again.
            for (int j = 0; j < matrixList.size(); j++) {
                DataEntry matrixEntry = matrixList.get(j);
                mMatrixNameToCollectionIndex.put(matrixEntry.name, new Integer(mcIndex));

                if (j != foundIndex) {
                    Matrix m = getMatrix(matrixEntry);
                    if ( m == null) {
                        RuntimeException e = new RuntimeException();
                        logger.error( "MatrixDataManager received a null matrix object for " + matrixEntry.name, e );
                        throw e;
                    }
                    mc.addMatrix(m);
                }

                if (logger.isDebugEnabled()) {
                    logger.debug("adding: " + matrixEntry.name + " to collection=" + groupName +
                            ", collectionIndex=" + mcIndex);
                }
            }

            //Add matrix collection to temporary list
            tempMatrixCollectionList.add(mc);
            mcIndex++;

            // Handle matrix arrays
            for (int j = 0; j < matrixList.size(); j++) {
                DataEntry matrixEntry = matrixList.get(j);
                if (matrixEntry.name.contains("[")) {
                    handleArrayMappedCollectionDataEntry(matrixEntry);
                }
            }

        }

        combineCollapsedMatrixValues(tempMatrixCollectionList);
    }


    /** Add matrices to an existing matrix collection.
     *
     * Steps:
     * 1. Find index matrix for the group
     * 2. Find existing matrix collection that uses this matrix as index
     * 3. Add matrix to this collection
     */
    private void addToExistingMatrixCollection(DataEntry[] matrixEntries, String groupName,
            ArrayList<DataEntry> matrixList) {

        int matrixIndex = -1;

        //Step #1
        for (int j = 0; j < matrixEntries.length; j++) {
            if (matrixEntries[j].groupName.equalsIgnoreCase(groupName)) {
                if (matrixEntries[j].indexFlag) {
                    matrixIndex = j;
                    break;
                }
            }
        }
        if (matrixIndex == -1) {
            throw new RuntimeException("matrix group=" + groupName +
                    " does not have an index matrix specified");
        }

        //Step #2
        int mcIndex = findMatrixCollectionIndex(matrixEntries[matrixIndex].name);
        if (mcIndex == -1) {
        	logger.info("matrix group=" + groupName + " does not have a matrix named " + matrixEntries[matrixIndex].name + " (index " + matrixIndex + ")");
        	logger.info("full matrix group information:");
        	for (String matrixName : mMatrixNameToCollectionIndex.keySet())
        		logger.info("    matrix name: " + matrixName + ", matrix collection: " + mMatrixNameToCollectionIndex.get(matrixName));
        	for (int i = 0; i < matrixEntries.length; i++) {
        		logger.info("    group name: " + matrixEntries[i].groupName + ", index flag: " + matrixEntries[i].indexFlag + ", name: " + matrixEntries[i].name);
        	}
        	throw new RuntimeException("matrix group=" + groupName + " does not have a matrix named " + matrixEntries[matrixIndex].name + " (index " + matrixIndex + ")");
        }
        MatrixCollection mc = mGroupValues[mcIndex];

        //Step #3
        for (int j = 0; j < matrixList.size(); j++) {
            DataEntry matrixEntry = matrixList.get(j);

            logger.debug("adding: "+matrixEntry.name +
                    " to existing collection indexed by " + matrixEntries[matrixIndex].name +
                    ", collection=" + groupName +
                    ", collectionIndex=" + mcIndex);

            Matrix m = getMatrix(matrixEntry);
            if ( m == null) {
                RuntimeException e = new RuntimeException();
                logger.error( "MatrixDataManager received a null matrix object for " + matrixEntry.name, e );
                throw e;
            }
            mc.addMatrix(m);

            //Add name/index to map
            mMatrixNameToCollectionIndex.put(matrixEntry.name, new Integer(mcIndex));
        }

    }


    private void combineCollapsedMatrixValues(
            ArrayList<MatrixCollection> newMatrixList) {
        //Combine old array with new list
        int newLength = mGroupValues.length + newMatrixList.size();
        MatrixCollection[] newMatrixCollectionValues = new MatrixCollection[newLength];

        //Copy existing values
        for (int i = 0; i < mGroupValues.length; i++) {
            newMatrixCollectionValues[i] = mGroupValues[i];
        }

        int j = 0;

        //Copy new values to end of existing list
        for (int i = mGroupValues.length; i < newLength; i++) {
            newMatrixCollectionValues[i] = newMatrixList.get(j);
            j++;
        }

        mGroupValues = newMatrixCollectionValues;
    }


    /**
     * get the Matrix object whose location is identified in the DataEntry object.
     * if an instance of MatrixDataServerIf has been set, it will get the Matrix object
     * from a server object using an RMI or xml-rpc based method, for example.  Otherwise readMatrix() is called.
     * @param matrixEntry is the DataEntry object that describes the specifics of the matrix data table
     * @return a Matrix object.
     */
    protected Matrix getMatrix(DataEntry matrixEntry) {

        if ( mDataServer == null ) {
            return readMatrix( matrixEntry );
        }
        else {
            mMatrixNames.add(matrixEntry.name);
            mEntryList.add(matrixEntry);
            Matrix matrix = mDataServer.getMatrix( matrixEntry );
            matrix.setName(matrixEntry.name);
            return matrix;
        }

    }


    /*
     * Read a matrix.
     *
     * @param matrixEntry a DataEntry describing the matrix to read
     * @return a Matrix
     */
    private Matrix readMatrix(DataEntry matrixEntry) {
        long startTime;
        long endTime;

        Matrix matrix = null;

        String fileName = matrixEntry.fileName;

        //Add matrix token name to list
        mMatrixNames.add(matrixEntry.name);

        //Add matrix entry to list of matrices read so far
        mEntryList.add(matrixEntry);

        startTime = System.currentTimeMillis();

        if (matrixEntry.format.equalsIgnoreCase("emme2")) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.EMME2, new File(fileName));
            matrix = mr.readMatrix(matrixEntry.matrixName);
        } else if (matrixEntry.format.equalsIgnoreCase("binary")) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.BINARY, new File(fileName));
            matrix = mr.readMatrix();
        } else if (matrixEntry.format.equalsIgnoreCase("zip") || matrixEntry.format.equalsIgnoreCase("zmx")) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.ZIP, new File(fileName));
            matrix = mr.readMatrix();
        } else if (matrixEntry.format.equalsIgnoreCase("tpplus")) { 
        	MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS, new File(fileName));
            matrix = mr.readMatrix(matrixEntry.matrixName);
        } else if (matrixEntry.format.equalsIgnoreCase("tpplus32")) { // TODO: remove once 32bit reader DLL is no longer supported
           MatrixReader mr = MatrixReader.createReader(MatrixType.TPPLUS32, new File(fileName));
           matrix = mr.readMatrix(matrixEntry.matrixName); 
        } else if (matrixEntry.format.equalsIgnoreCase("transcad")) {
            MatrixReader mr = MatrixReader.createReader(MatrixType.TRANSCAD, new File(fileName));
            matrix = mr.readMatrix(matrixEntry.matrixName);
        } else {
            throw new RuntimeException("unsupported matrix type: " + matrixEntry.format);
        }

        endTime = System.currentTimeMillis();

        String msg = "Read " + matrixEntry.name + ", " + fileName;

        if (matrixEntry.matrixName.length() > 0)
            msg += ", " + matrixEntry.matrixName;
        msg += " in: " + (endTime - startTime) + " ms";

        logger.debug(msg);

        //Use token name from control file for matrix name (not name from underlying matrix)
        matrix.setName(matrixEntry.name);

        return matrix;
    }

    /**
     * Find matrix name in matrixValues index
     *
     * @param variableName
     *            Matrix name
     * @return index, or -1 if not found
     */
    synchronized public int findMatrixIndex(String variableName) {
        int index = -1;

        for (int i = 0; i < mValues.length; i++) {
            String matrixName = mValues[i].getName();

            if (matrixName.equalsIgnoreCase(variableName)) {
                index = i;
                break;
            }
        }

        return index;
    }

    /**
     * Returns an index value for a matrix collection that contains a specified matrix.
     */
    synchronized public int findMatrixCollectionIndex(String variableName) {
        int collectionIndex = -1;

        Integer mcIndex = mMatrixNameToCollectionIndex.get(variableName);

        if (mcIndex != null) {
            collectionIndex = mcIndex.intValue();
        }

        return collectionIndex;
    }

    synchronized public int findArrayMatrixIndex(String variableName) {

        if (this.mArrayNameLookup.containsKey(variableName)) {
            return mArrayNameLookup.get(variableName);
        }

        return -1;
    }

    synchronized public int findArrayMatrixCollectionIndex(String variableName) {

        if (mArrayGroupNameLookup.containsKey(variableName)) {
            return mArrayGroupNameLookup.get(variableName);
        }

        return -1;
    }

    /**
     * Returns an index value for the name of a matrix inside a matrix collection.
     */
    synchronized public int findMatrixCollectionNameIndex(String variableName) {
        int index = -1;

        for (int i = 0; i < mMatrixNames.size(); i++) {
            String matrixName = mMatrixNames.get(i);

            if (matrixName.equalsIgnoreCase(variableName)) {
                index = i;
                break;
            }
        }

        return index;
    }


    /**
     * Returns the cell value for a matrix.
     *
     * @param variableIndex
     * @param origIndex
     * @param destIndex
     * @return  cell value of the matrix
     */
    public double getValueForIndex(int variableIndex, int origIndex, int destIndex) {
        return mValues[variableIndex].getValueAt(origIndex, destIndex);
    }

    /**
     * Returns the cell value for a matrix array.
     *
     * @param variableIndex
     * @param origIndex
     * @param destIndex
     * @param arrayIndex
     * @return cell value of the matrix
     */
    public double getArrayValueForIndex(int variableIndex, int origIndex,
            int destIndex, int arrayIndex) {
        // Need to convert the variableIndex to a 'resolved' index which
        // accounts for the array argument.
        HashMap<Integer, Integer> arrayMap = mArrayMappingToIndex.get(variableIndex);

        // Trap typos in a UEC spreadsheet that can result in failed lookups.
        try {
            int resolvedIndex = arrayMap.get(arrayIndex);
            return mValues[resolvedIndex].getValueAt(origIndex, destIndex);

        } catch (Exception e) {
            // This will happen if either the array index is oob, or if the lookup varname was misspelled.
            logger.error("### Expression lookup failed for array index [" + arrayIndex + "] -- check UEC spreadsheet for typos?");
            throw new ArrayIndexOutOfBoundsException();
        }
    }

    /**
     * Returns the cell value for a matrix in a matrix collection.
     *
     * @param variableIndex
     * @param origIndex
     * @param destIndex
     * @param nameIndex
     * @return cell value of the matrix
     */
    public double getValueForIndex(int variableIndex, int origIndex,
            int destIndex, int nameIndex) {

        // Lookup matrix collection which contains request matrix value
        MatrixCollection mc = mGroupValues[variableIndex];

        // Lookup name of requested matrix
        String matrixName = mMatrixNames.get(nameIndex);

        return mc.getValue(origIndex, destIndex, matrixName);
    }

    /**
     * Returns the cell value for a matrix in an ARRAYED matrix collection.
     *
     * @param variableIndex
     * @param origIndex
     * @param destIndex
     * @param nameIndex
     * @return cell value of the matrix
     */
    public double getArrayValueForIndex(int variableIndex, int origIndex,
            int destIndex, int nameIndex, int arrayIndex) {

        // Need to convert the variableIndex to a 'resolved' index which
        // accounts for the array argument.
        HashMap<Integer, Integer> arrayMap = mArrayMappingToIndex.get(variableIndex);

        // Trap typos in a UEC spreadsheet that can result in failed lookups.
        try {
            int resolvedIndex = arrayMap.get(arrayIndex);
            //Lookup matrix collection which contains request matrix value
            MatrixCollection mc = mGroupValues[resolvedIndex];
            //Lookup name of requested matrix
            String matrixName = "";
            if (nameIndex > -1) {
                matrixName = mMatrixNames.get(nameIndex);
            } else {
                matrixName = mArrayGroupToIndex.get(variableIndex).get(
                        arrayIndex);
            }

            return mc.getValue(origIndex, destIndex, matrixName);

        } catch (Exception e) {
            // This will happen if either the array index is oob, or if the lookup varname was misspelled.
            logger.error("### Expression lookup failed for array index [" + arrayIndex + "] -- check UEC spreadsheet for typos?");
            throw new ArrayIndexOutOfBoundsException();
        }
    }

    /**
     * Log the values in the matrix for the originTaz and destTaz
     * @param origTaz
     * @param destTaz
     */
    public void logMatrixValues(int origTaz, int destTaz){

        logMatrixValues(logger, origTaz, destTaz);
    }


    /**
     * Log the values in the matrix for the originTaz and destTaz
     * @param localLogger - the logger to send the results to
     * @param origTaz
     * @param destTaz
     */
    public void logMatrixValues(Logger localLogger, int origTaz, int destTaz){

        localLogger.info("");
        localLogger.info("Matrix data values for origin "+origTaz+" destination "+destTaz);
        localLogger.info("");
        for(Matrix m : mValues){
            float value = m.getValueAt(origTaz, destTaz);
            String name = m.getName();
            localLogger.info("Matrix "+name+" : "+value);
        }
        for(MatrixCollection mc : mGroupValues){
            Set<?> keySet = mc.getHashMap().keySet();
            Iterator<?> i = keySet.iterator();
            while(i.hasNext()){
                String name = (String) i.next();
                float value = mc.getValue(origTaz,destTaz,name);
                localLogger.info("Matrix "+name+" : "+value);

            }
        }
        localLogger.info("");
    }

    /**
     * Checks the matrices in matrixValues and matrixCollectionValues for those with
     * a zero sum. Introduced to track down silent bug in transCAD dlls.
     * @return true if a matrix with a zero sum is found; false if no such matrix is found
     *
     */
    public boolean checkForZeroSumMatrices(){

        double matrixSum;

        for(int i=0;i<mValues.length;++i){
            Matrix tempMatrix = mValues[i];
            matrixSum = tempMatrix.getSum();
            if(matrixSum<0.1){
                logger.info("Possible error: Matrix "+tempMatrix.getName()+" has a zero sum.");
                return(true);
            }
        }

        for(int i=0;i<mGroupValues.length;++i){
            MatrixCollection tempMatrixCollection = mGroupValues[i];
            Set<?> keySet = tempMatrixCollection.getHashMap().keySet();
            Iterator<?> iterator = keySet.iterator();
            while(iterator.hasNext()){
                String matrixName = (String) iterator.next();
                Matrix tempMatrix = tempMatrixCollection.getMatrix(matrixName);
                matrixSum = tempMatrix.getSum();
                if(matrixSum<0.1){
                    logger.info("Possible error: Matrix "+matrixName+" has a zero sum.");
                }
            }
        }

        return(false);
    }

}
