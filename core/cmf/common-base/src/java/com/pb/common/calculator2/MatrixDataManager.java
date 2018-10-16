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
package com.pb.common.calculator2;

import com.pb.common.matrix.CollapsedMatrixCollection;
import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixCollection;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.matrix.MatrixType;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Set;


/**
 * Provides data management capabilities.
 *
 * @author    Tim Heier
 * @version   1.0, 8/3/2003
 */
public class MatrixDataManager implements Serializable {
    protected transient Logger logger = Logger.getLogger(
            "com.pb.common.calculator");

    private MatrixDataServerIf matrixDataServer;
    private static MatrixDataManager instance = new MatrixDataManager();

    //Holds references to each matrix object (excluding matrices in a matrix collection)
    private Matrix[] matrixValues = new Matrix[0];

    //Holds list of matrix entries read into memory
    private ArrayList<DataEntry> matrixEntryList = new ArrayList<DataEntry>();

    //Holds references to each matrix collection
    private MatrixCollection[] matrixCollectionValues = new MatrixCollection[0];

    //Maps a matrix name to a matrix collection index value. Built when matrices
    //are read but accessed at parse time
    private HashMap matrixNameToCollectionIndex = new HashMap(100);

    //Holdes a matrix name. The position in the array is used as a reverse lookup to get
    //the name at solve time.
    private ArrayList<String> matrixNames = new ArrayList<String>(100);


    private MatrixDataManager() {
    }

    /**
     * this method might be used to set a MatrixDataServer instance that implements remote method calls to a remote
     * storage location for matrices, allowing network access to the Matrix objects as opposed to i/o access.
     * @param mds is an instance of a class that implements MatrixDataServerIF.
     *
     */
    public void setMatrixDataServerObject( MatrixDataServerIf mds ) {
        this.matrixDataServer = mds;
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
        matrixValues = new Matrix[0];
        matrixEntryList.clear();

        matrixCollectionValues = new MatrixCollection[0];
        matrixNameToCollectionIndex.clear();
        matrixNames.clear();
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
        HashMap matrixMap = new HashMap();

        //Maps group names to an ArrayList of matrices in group (group == collection)
        HashMap collapsedMap = new HashMap();

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
                ArrayList matrixList = (ArrayList) collapsedMap.get(matrixEntries[i].groupName);

                //No entries with this group name exist in map, create a new list for the group
                if (matrixList == null) {
                    matrixList = new ArrayList();
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
            for ( Iterator it = matrixMap.keySet().iterator(); it.hasNext(); ) {
                String matrixName = (String) it.next();
                DataEntry matrixEntry = (DataEntry) matrixMap.get(matrixName);
                String fileName = matrixEntry.fileName;
                logger.fatal( String.format( "%-10s %s", matrixName, fileName) );
            }
            throw (e);
        }
        addMatrixCollections(matrixEntries, collapsedMap);

        if (logger.isDebugEnabled()) {
            logger.debug("Loaded matrix summary:");
            for (int m = 0; m < matrixValues.length; m++) {
                String name = matrixValues[m].getName();
                logger.debug("matrixName=" + name + ", position=" + m);
            }
        }

        if (logger.isDebugEnabled()) {
            logger.debug("Loaded collapsedMatrix summary:");
            logger.debug("number of collapsed matrix collections=" + matrixCollectionValues.length);
            logger.debug("number of matrices in collections=" + matrixNameToCollectionIndex.size());

            Iterator iter = matrixNameToCollectionIndex.keySet().iterator();

            while (iter.hasNext()) {
                String matrixName = (String) iter.next();
                int i = ((Integer) matrixNameToCollectionIndex.get(matrixName)).intValue();
                logger.debug("collapsedMatrixIndex=" + i + ", matrixName=" + matrixName);
            }
        }

    }

    /**
     * Checks to see if a matrix has been loaded already.
     * Combine matrix name + file name and test for uniqueness.
     */
    private boolean isMatrixLoaded(DataEntry entry) {
        for (int i = 0; i < matrixEntryList.size(); i++) {
            DataEntry matrixEntry = (DataEntry) matrixEntryList.get(i);

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
    private void addMatrices(HashMap matrixMap) {
        ArrayList newMatrixList = new ArrayList();

        //Iterate over matrix map and read matrices
        Iterator it = matrixMap.keySet().iterator();

        while (it.hasNext()) {
            String name = (String) it.next();
            DataEntry matrixEntry = (DataEntry) matrixMap.get(name);
            Matrix matrix = getMatrix(matrixEntry);

            newMatrixList.add(matrix);
        }

        combineMatrixValues(newMatrixList);
    }

    private void combineMatrixValues(ArrayList newMatrixList) {
        //Combine old array with new list
        int newLength = matrixValues.length + newMatrixList.size();
        Matrix[] newMatrixValues = new Matrix[newLength];

       //Copy existing values
        for (int i = 0; i < matrixValues.length; i++) {
            newMatrixValues[i] = matrixValues[i];
        }

        int j = 0;

        //Copy new values to end of existing list
        for (int i = matrixValues.length; i < newLength; i++) {
            newMatrixValues[i] = (Matrix) newMatrixList.get(j);
            j++;
        }

        matrixValues = newMatrixValues;
    }

    /*
     * Iterate over collection map and build a map of matrix names and values
     */
    private void addMatrixCollections(DataEntry[] matrixEntries, HashMap collapsedMap) {
        ArrayList tempMatrixCollectionList = new ArrayList();

        //Index of matrix collection
        int mcIndex = matrixCollectionValues.length;

        //Iterate over matrix map and build two parallel lists, one for
        //indexing by name and one for looking up a collection matrix based on a integer index
        Iterator it = collapsedMap.keySet().iterator();

        while (it.hasNext()) {
            String groupName = (String) it.next();
            ArrayList matrixList = (ArrayList) collapsedMap.get(groupName);

            int foundIndex = -1;

            //Look collection index matrix
            for (int j = 0; j < matrixList.size(); j++) {
                DataEntry matrixEntry = (DataEntry) matrixList.get(j);
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
            Matrix indexMatrix = getMatrix((DataEntry) matrixList.get(foundIndex));
            MatrixCollection mc = new CollapsedMatrixCollection(indexMatrix);

            //Loop over matrices in group and add to collection, don't add the
            //index matrix again.
            for (int j = 0; j < matrixList.size(); j++) {
                DataEntry matrixEntry = (DataEntry) matrixList.get(j);
                matrixNameToCollectionIndex.put(matrixEntry.name, new Integer(mcIndex));

                if (j != foundIndex) {
                    Matrix m = getMatrix(matrixEntry);
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
                                               ArrayList matrixList) {

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
        MatrixCollection mc = matrixCollectionValues[mcIndex];

        //Step #3
        for (int j = 0; j < matrixList.size(); j++) {
            DataEntry matrixEntry = (DataEntry) matrixList.get(j);

            logger.debug("adding: "+matrixEntry.name +
                        " to existing collection indexed by " + matrixEntries[matrixIndex].name +
                        ", collection=" + groupName +
                        ", collectionIndex=" + mcIndex);

            Matrix m = getMatrix(matrixEntry);
            mc.addMatrix(m);

            //Add name/index to map
            matrixNameToCollectionIndex.put(matrixEntry.name, new Integer(mcIndex));
        }

    }


    private void combineCollapsedMatrixValues(ArrayList newMatrixList) {
        //Combine old array with new list
        int newLength = matrixCollectionValues.length + newMatrixList.size();
        MatrixCollection[] newMatrixCollectionValues = new MatrixCollection[newLength];

        //Copy existing values
        for (int i = 0; i < matrixCollectionValues.length; i++) {
            newMatrixCollectionValues[i] = matrixCollectionValues[i];
        }

        int j = 0;

        //Copy new values to end of existing list
        for (int i = matrixCollectionValues.length; i < newLength; i++) {
            newMatrixCollectionValues[i] = (MatrixCollection) newMatrixList.get(j);
            j++;
        }

        matrixCollectionValues = newMatrixCollectionValues;
    }


    /**
     * get the Matrix object whose location is identified in the DataEntry object.
     * if an instance of MatrixDataServerIf has been set, it will get the Matrix object
     * from a server object using an RMI or xml-rpc based method, for example.  Otherwise readMatrix() is called.
     * @param matrixEntry is the DataEntry object that describes the specifics of the matrix data table
     * @return a Matrix object.
     */
    protected Matrix getMatrix(DataEntry matrixEntry) {

        if ( matrixDataServer == null ) {
            return readMatrix( matrixEntry );
        }
        else {
            matrixNames.add(matrixEntry.name);
            matrixEntryList.add(matrixEntry);
            Matrix matrix = matrixDataServer.getMatrix( matrixEntry );
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
        matrixNames.add(matrixEntry.name);

        //Add matrix entry to list of matrices read so far
        matrixEntryList.add(matrixEntry);

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

	synchronized public int findMatrixIndex(String variableName) {
        int index = -1;

        for (int i = 0; i < matrixValues.length; i++) {
            String matrixName = matrixValues[i].getName();

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

        Integer mcIndex = (Integer) matrixNameToCollectionIndex.get(variableName);

        if (mcIndex != null) {
            collectionIndex = mcIndex.intValue();
        }

        return collectionIndex;
    }

    /**
     * Returns an index value for the name of a matrix inside a matrix collection.
     */
	synchronized public int findMatrixCollectionNameIndex(String variableName) {
        int index = -1;

        for (int i = 0; i < matrixNames.size(); i++) {
            String matrixName = (String) matrixNames.get(i);

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
        return matrixValues[variableIndex].getValueAt(origIndex, destIndex);
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
    public double getValueForIndex(int variableIndex, int origIndex, int destIndex, int nameIndex) {

        //Lookup matrix collection which contains request matrix value
        MatrixCollection mc = matrixCollectionValues[variableIndex];

        //Lookup name of requested matrix
        String matrixName = (String) matrixNames.get(nameIndex);

        return mc.getValue(origIndex, destIndex, matrixName);
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
        for(Matrix m : matrixValues){
            float value = m.getValueAt(origTaz, destTaz);
            String name = m.getName();
            localLogger.info("Matrix "+name+" : "+value);
        }
        for(MatrixCollection mc : matrixCollectionValues){
            Set keySet = mc.getHashMap().keySet();
            Iterator i = keySet.iterator();
            while(i.hasNext()){
                String name = (String) i.next();
                float value = (float) mc.getValue(origTaz,destTaz,name);
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
    	
    	for(int i=0;i<matrixValues.length;++i){
    		Matrix tempMatrix = matrixValues[i];
    		matrixSum = tempMatrix.getSum();
    		if(matrixSum<0.1){
    			logger.info("Possible error: Matrix "+tempMatrix.getName()+" has a zero sum.");
    			return(true);
    		}
    	}
    	
    	for(int i=0;i<matrixCollectionValues.length;++i){
    		MatrixCollection tempMatrixCollection = matrixCollectionValues[i];
    		Set keySet = tempMatrixCollection.getHashMap().keySet();
    		Iterator iterator = keySet.iterator();
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
