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
package com.pb.common.matrix;

import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.TableDataSet;
import com.pb.common.util.ResourceUtil;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.util.ResourceBundle;

/**
 * MatrixCompression.java
 * Compresses an alphaZone matrix to the betaZone level.
 *
 * A betaZone is an aggregation of alphaZones.
 * For example, alphaZones are TAZs, while betaZones are districts containing a group of TAZs.
 *
 * The betaZone matrix type is specified by the user, and can either be the SUM, MEAN, MIN, or MAX of the alphaZones
 *
 * An AlphaToBeta object must be passed in the constructor; this is the lookup table for the betaZone of each alphaZone
 *
 * @author Steve Hansen
 * @version 1.1 Apr 13, 2004
 * version 1.1 - removed column vector dependencies for the alpha to beta zone mapping
 *
 */
public class MatrixCompression{

    protected static Logger logger = Logger.getLogger("com.pb.common.matrix");
    protected AlphaToBeta a2b;
    protected float missingValue = Float.NEGATIVE_INFINITY;

    /** constructor
     * An AlphaToBeta object must be passed in the constructor; this is the lookup table for the betaZone of each alphaZone
     * @param alpha2Beta - the correspondence table used for squeeze
     */
    public MatrixCompression(AlphaToBeta alpha2Beta){
        a2b = alpha2Beta;
    }

    public enum MatrixCompressionType {
        SUM,MEAN,MAX,MIN
    }
    
    /**
     * Trims a matrix to include only those with valid apha zones, 
     * for example, trim to only internals.  
     * 
     * @param aMatrix Matrix to be trimmed, with alpha zones
     * @return A sub-matrix consisting of only those cells contained in the Alpha2Beta.
     */
    public Matrix getTrimmedAlphaMatrix(Matrix aMatrix) {
        int[] alphaExternals = a2b.getAlphaExternals1Based();
        return aMatrix.getSubMatrix(alphaExternals);
    }
    
    /**
     * Trims a matrix to include only those with valid apha zones, 
     * compresses it, and returns the compressed matrix.  
     * 
     * @param aMatrix Matrix to be trimmed and compressed, with alpha zones
     * @param matrixReturnType (sum, mean, max, min)
     * @return A compressed sub-matrix.
     */
    public Matrix getTrimmedCompressedMatrix(Matrix aMatrix, String matrixReturnType) {
        Matrix trimmedMatrix = getTrimmedAlphaMatrix(aMatrix);
        return getCompressedMatrix(trimmedMatrix, matrixReturnType);
    }

    public Matrix getCompressedMatrix(Matrix aMatrix, MatrixCompressionType type) {
        return getCompressedMatrix(aMatrix, type.toString());
    }


    /**
     * takes an alphaZone matrix, and returns a betaZone matrix, as specified by the user
     * @param aMatrix the alphaZone matrix
     * @param matrixReturnType - The type of district matrix to return ("SUM" "MEAN" "MIN" or "MAX")
     * @return bMatrix - the betaZone matrix
     */
    public Matrix getCompressedMatrix(Matrix aMatrix, String matrixReturnType){
        if(matrixReturnType.equalsIgnoreCase("SUM")){
            Matrix bMatrix = squeezeSum(aMatrix);
            bMatrix.setExternalNumbers(a2b.betaExternals);
            return bMatrix;
        }
        else if(matrixReturnType.equalsIgnoreCase("MEAN")){
            Matrix bMatrix = squeezeMean(aMatrix);
            bMatrix.setExternalNumbers(a2b.betaExternals);
            return bMatrix;
        }
        else if(matrixReturnType.equalsIgnoreCase("MIN")){
            return squeezeMin(aMatrix);
        }
        else if(matrixReturnType.equalsIgnoreCase("MAX")){
            return squeezeMax(aMatrix);
        } else{
            logger.error("Matrix return type must equal SUM, MEAN, MIN or MAX");
            System.exit(1);
            return aMatrix;
        }
    }
    
    public void setMissingValue ( float missingValue ) {
        this.missingValue = missingValue;
    }

    public Matrix getWeightedMeanCompressedMatrix(Matrix aMatrix, Matrix aWeightMatrix) {
        return squeezeWeightedMean(aMatrix,aWeightMatrix);
    }

    private Matrix squeezeSum(Matrix aMatrix){

        int tazI;
        int tazJ;
        int districtI;
        int districtJ;

        float sum;

            Matrix bMatrix = createBetaMatrix(aMatrix);

            for(int i=0;i<aMatrix.getRowCount();i++){
                for(int j=0;j<aMatrix.getColumnCount();j++){
                    tazI = aMatrix.getExternalNumber(i);
                    tazJ = aMatrix.getExternalNumber(j);
                    districtI = a2b.getBetaZone(tazI);
                    districtJ = a2b.getBetaZone(tazJ);
                    
                    // handle column vectors
                    if (aMatrix.getRowCount() == 1) {
                        tazI = 1;
                        districtI = 1;
                    }
                    
                    // handle row vectors
                    if (aMatrix.getColumnCount() == 1) {
                        tazJ = 1;
                        districtJ = 1;
                    }
                    
                    sum = bMatrix.getValueAt(districtI,districtJ);
                    sum = sum + aMatrix.getValueAt(tazI,tazJ);
                    bMatrix.setValueAt(districtI,districtJ,sum);
                }
            }
            return bMatrix;
    }

    private Matrix squeezeWeightedMean(Matrix aMatrix, Matrix aWeightMatrix) {
        Matrix bMatrix = createBetaMatrix(aMatrix);
        Matrix countMatrix = createBetaMatrix(aMatrix);

        int[] iExternals = aMatrix.getExternalRowNumbers();
        int[] jExternals = aMatrix.getExternalColumnNumbers();

        for (int i = 1; i < iExternals.length; i++) {
            for (int j = 1; j < jExternals.length; j++) {
                int iExt = iExternals[i];
                int jExt = jExternals[j];
                int iDistrict = a2b.getBetaZone(iExt);
                int jDistrict = a2b.getBetaZone(jExt);

                if (iDistrict >= 0 && jDistrict >= 0) {
                    float weight = aWeightMatrix.getValueAt(iExt,jExt);
                    float value = aMatrix.getValueAt(iExt,jExt);
                    if (value != missingValue) {
                        bMatrix.setValueAt(iDistrict,jDistrict,weight*value);
                        countMatrix.setValueAt(iDistrict,jDistrict,weight+countMatrix.getValueAt(iDistrict,jDistrict));
                    }
                }
            }
        }

        iExternals = bMatrix.getExternalRowNumbers();
        jExternals = bMatrix.getExternalColumnNumbers();
        for (int i = 1; i < iExternals.length; i++) {
            for (int j = 1; j < jExternals.length; j++) {
                int iExt = iExternals[i];
                int jExt = jExternals[j];
                float weight = countMatrix.getValueAt(iExt,jExt);
                bMatrix.setValueAt(iExt,jExt,weight > 0 ? bMatrix.getValueAt(iExt,jExt)/weight : missingValue);
            }
        }
        return bMatrix;
    }

    private Matrix squeezeMean(Matrix aMatrix){

        int tazI;
        int tazJ;
        int districtI;
        int districtJ;


        Matrix bMatrix =createBetaMatrix(aMatrix);
        Matrix countMatrix = createBetaMatrix(aMatrix);

        float sum;
        int count;

        // sum aMatrix values into bMatrix values, and save a separate matrix of counts of azones in bzones.
        for(int i=0;i<aMatrix.getRowCount();i++){
            for(int j=0;j<aMatrix.getColumnCount();j++){
                tazI = aMatrix.getExternalNumber(i);
                tazJ = aMatrix.getExternalNumber(j);
                districtI = a2b.getBetaZone(tazI);
                districtJ = a2b.getBetaZone(tazJ);
                
                if (districtJ !=-1 && districtI !=-1) {
    
                    if ( aMatrix.getValueAt(tazI,tazJ) != missingValue ) {
                        sum = bMatrix.getValueAt(districtI,districtJ) + aMatrix.getValueAt(tazI,tazJ);
                        count = (int)countMatrix.getValueAt(districtI,districtJ) + 1;
                        bMatrix.setValueAt(districtI, districtJ, sum);
                        countMatrix.setValueAt(districtI, districtJ, count);
                    }
                }

            }
        }
        
        // divide bzone values by bzone counts to get bzone means
        int[] externalIds = bMatrix.getExternalNumbers();
        for(int i=1; i <= bMatrix.getRowCount(); i++){
            for(int j=1; j <= bMatrix.getColumnCount(); j++){

            	districtI = externalIds[i];
            	districtJ = externalIds[j];

            	sum = bMatrix.getValueAt(districtI, districtJ);
                count = (int)countMatrix.getValueAt(districtI, districtJ);

                if ( count > 0 ) {
                    bMatrix.setValueAt( districtI, districtJ, sum/count );
                }
                else {
                    bMatrix.setValueAt( districtI, districtJ, missingValue );
                }
            }
        }
        
        return bMatrix;
    }

    private Matrix squeezeMin(Matrix aMatrix){

        int tazI;
        int tazJ;
        int districtI;
        int districtJ;

        Matrix bMatrix = createBetaMatrix(aMatrix);
        Matrix countMatrix = createBetaMatrix(aMatrix);

        float currentMin;
        float nextValue;
        int count;

        for(int i=0;i<aMatrix.getRowCount();i++){
            for(int j=0;j<aMatrix.getColumnCount();j++){
                tazI = aMatrix.getExternalNumber(i);
                tazJ = aMatrix.getExternalNumber(j);
                districtI = a2b.getBetaZone(tazI);
                districtJ = a2b.getBetaZone(tazJ);

                count = (int)countMatrix.getValueAt(districtI,districtJ);
                currentMin = bMatrix.getValueAt(districtI,districtJ);
                nextValue = aMatrix.getValueAt(tazI,tazJ);
                if(count==0 || nextValue<currentMin)
                    currentMin=nextValue;
                bMatrix.setValueAt(districtI, districtJ, currentMin);
                countMatrix.setValueAt(districtI,districtJ,count + 1);
            }
        }
        return bMatrix;
    }

    private Matrix squeezeMax(Matrix aMatrix){

        int tazI;
        int tazJ;
        int districtI;
        int districtJ;

        int betaZoneColumnSize;

        if(aMatrix.getColumnCount()==1)
            betaZoneColumnSize=1;
        else
            betaZoneColumnSize=a2b.betaSize();

        Matrix bMatrix = new Matrix(a2b.betaSize(),betaZoneColumnSize);
        bMatrix.setExternalNumbers(a2b.betaExternals);
        Matrix countMatrix = new Matrix(a2b.betaSize(),betaZoneColumnSize);
        countMatrix.setExternalNumbers(a2b.betaExternals);

        float currentMax;
        float nextValue;
        int count;

        for(int i=0;i<aMatrix.getRowCount();i++){
            for(int j=0;j<aMatrix.getColumnCount();j++){
                tazI = aMatrix.getExternalNumber(i);
                tazJ = aMatrix.getExternalNumber(j);
                districtI = a2b.getBetaZone(tazI);
                districtJ = a2b.getBetaZone(tazJ);

                count = (int)countMatrix.getValueAt(districtI,districtJ);
                currentMax = bMatrix.getValueAt(districtI,districtJ);
                nextValue = aMatrix.getValueAt(tazI,tazJ);
                if(count==0 || nextValue>currentMax)
                    currentMax=nextValue;
                bMatrix.setValueAt(districtI, districtJ, currentMax);
                countMatrix.setValueAt(districtI,districtJ,count + 1);
            }
        }
        return bMatrix;
    }

    public static TableDataSet loadTableDataSet(){

        ResourceBundle rb = ResourceUtil.getResourceBundle("pt");
        String path = ResourceUtil.getProperty(rb, "alphatobeta.file");
        try {
            CSVFileReader reader = new CSVFileReader();
            return reader.readFile(new File(path));
        } catch (IOException e) {
            logger.error("Error loading TableDataSet "+path);
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Create a beta zone matrix.
     * 
     * @param aMatrix
     *            Alpha zone matrix.
     * @return the beta zone matrix.
     */
    protected Matrix createBetaMatrix(Matrix aMatrix) {

        int betaZoneColumnSize;
        int betaZoneRowSize;

        if (aMatrix.getColumnCount() == 1)
            betaZoneColumnSize = 1;
        else
            betaZoneColumnSize = a2b.betaSize();

        if (aMatrix.getRowCount() == 1) {
            betaZoneRowSize = 1;
        } else {
            betaZoneRowSize = a2b.betaSize();
        }

        Matrix bMatrix = new Matrix(betaZoneRowSize, betaZoneColumnSize);
        bMatrix.setExternalNumbers(a2b.betaExternals);

        bMatrix.setName(aMatrix.getName() + "beta");

        return bMatrix;
    }

    public static void main (String[] args) throws Exception {
        //TableDataSet alphaToBeta = loadTableDataSet();
        //AlphaToBeta a2b = new AlphaToBeta(alphaToBeta.getColumnAsInt(alphaToBeta.getColumnPosition("AZone")),
        //                                  alphaToBeta.getColumnAsInt(alphaToBeta.getColumnPosition("BZone")));

        int[] externalTest = {0,1,2,3,4,5,6,10,11,12};
        int[] aZones = {1,2,3,4,5,6,10,11,12};
        int[] bZones = {1,1,1,4,4,4,10,10,10};
        AlphaToBeta a2b = new AlphaToBeta(aZones, bZones);
        MatrixCompression squeeze = new MatrixCompression(a2b);
        //ResourceBundle rb = ResourceUtil.getResourceBundle("pt");
        //String path = ResourceUtil.getProperty(rb, "skimPath.path");
        //MatrixReader pkTimeReader= MatrixReader.createReader(MatrixType.ZIP,new File(path+"pktime.zip"));
        //Matrix pkTime= pkTimeReader.readMatrix(path+"pktime.zip");
        float[][] test = new float[9][9];
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                test[i][j] = i;
            }
        }
        Matrix testMatrix = new Matrix(test);
        testMatrix.setExternalNumbers(externalTest);
        Matrix squeezed = squeeze.getCompressedMatrix(testMatrix,"SUM");

        for(int i=0;i<squeezed.getRowCount();i++){
            for(int j=0;j<squeezed.getColumnCount();j++){
            	logger.debug("origin: "+squeezed.getExternalNumber(i)+
                            " destination: "+squeezed.getExternalNumber(j)+
                            " value: "+squeezed.getValueAt(squeezed.getExternalNumber(i),squeezed.getExternalNumber(j)));
            }
        }
    }
}