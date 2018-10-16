/*
 * Copyright 2006 PB Consult Inc.
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
 * Created on Mar 22, 2006 by Andrew Stryker <stryker@pbworld.com>
 */
package com.pb.models.utils;

import java.util.Arrays;
import java.util.Iterator;

import org.apache.log4j.Logger;

import com.pb.common.matrix.Matrix;

import static java.lang.Math.exp;

/**
 * A Sample of Alternatives Strategy specifically for
 * destination choice.
 *
 * The utility for selecting the sample is
 * U[j] = ln(size[j]) - lambda(dist[i,j])
 *
 * The user of this class supplies the size terms, the
 * lambda and the "distance" matrix.  (The distance could be measured
 * in time, or cost or whatever)
 *
 * The correction factor is returned to the user as well as the
 * set of sampled alternatives.
 *
 * To use:
 *  call 'calculateFullProbablitiyMatrix(skim, sizeterms, lambda)'
 *  and then when you are ready to select your destination taz
 *  call the 'sample(originZone, sampleSize)' method and then call
 *  'getSampleArray' to actually get the sample and
 *  'getCorrectionFactors' to get the correction factors.
 * 
 * @author Andrew Stryker, Christi Willison, Ofir Cohen
 * @version 0.2 Apr 13, 2006
 */
public class SampleDestinationAlternatives {
    static Logger logger = Logger.getLogger(SampleDestinationAlternatives.class);

    private Matrix probabilityMatrix;
    private Matrix cumulativeProbMatrix;

    private int uniqueSamples;

    private int alts[];
    private float cumulativeProbabilities[];

    private int sampleArray[];

    private float factors[];

    private int origin = -1;
    
    public SampleDestinationAlternatives() {

    }
    
    public void calculateFullProbabilityMatrix(Matrix skimMatrix, float[] sizeTerms, float lambda){
        int nTazs = skimMatrix.getColumnCount();

        //Do a quick consistency check
        if(nTazs != sizeTerms.length) {
            logger.warn("The number of size terms ("+(sizeTerms.length-1)+") is not consistent with the number" +
                    " of zones in your skim matrix ("+ nTazs+ ") - this might cause problems");
        }
        alts = new int[nTazs];
        cumulativeProbabilities = new float[nTazs];

        probabilityMatrix = new Matrix(nTazs, nTazs);
        probabilityMatrix.setExternalNumbers(skimMatrix.getExternalNumbers());
        
        cumulativeProbMatrix = new Matrix(nTazs, nTazs);
        cumulativeProbMatrix.setExternalNumbers(skimMatrix.getExternalNumbers());
        
        Iterator tazRows = skimMatrix.getExternalNumberIterator();
        while(tazRows.hasNext()){
            int row = (Integer)tazRows.next();
            float expSum = 0;
            float probSum = 0;
            Iterator tazCols = skimMatrix.getExternalNumberIterator();
            while(tazCols.hasNext()){
                float expUtility=0;
                int col = (Integer) tazCols.next();
                     
                if(sizeTerms.length<col)
                    expUtility=0;
                else expUtility = (float) (sizeTerms[col] * exp(lambda
                        * skimMatrix.getValueAt(row, col)));
                
                probabilityMatrix.setValueAt(row,col,expUtility);
                expSum += expUtility;
            }

            Iterator tazs = skimMatrix.getExternalNumberIterator();
            while(tazs.hasNext()){
                int column = (Integer)tazs.next();
                float value = probabilityMatrix.getValueAt(row,column);
                value /= expSum;
                
                probabilityMatrix.setValueAt(row,column,value);
                probSum += value;
                if(probSum>1.0001)
                    logger.info("error, Accumulative probSum in SampleDestinationChoice is >1");
                cumulativeProbMatrix.setValueAt(row, column, probSum);
            }
        }
    }

    /**
     * Sample destinations and compute correction factors.
     *
     * @param origin
     * @param nSamples
     */
    public long[] sample(int origin, int nSamples, boolean debugMode ) {
        // for time debug purpose
        long fillTime=0;
        long choiceTime=0;
        long cfTime=0;
        
        this.origin= origin;
        
        if (sampleArray == null || sampleArray.length != nSamples) {
            sampleArray = new int[nSamples];
            factors = new float[nSamples];
        }

        if (debugMode) {
            fillTime = System.currentTimeMillis();
        }
        //Reset the alts array
        Arrays.fill(alts,0);
        if (debugMode) {
            fillTime = System.currentTimeMillis() - fillTime;
            choiceTime = System.currentTimeMillis();
        }
        //Choose the sample set
        for (int i = 0; i < nSamples; ++i) {
            alts[(choose())] += 1;     //keeps track of the frequency
        }
        if( debugMode)
            choiceTime = System.currentTimeMillis() - choiceTime;
        
        //Convert the index values to external TAZ numbers
        //to populate sample array and calculate correction
        //factors.
        int s = 0;
        double k;
        if (debugMode)
            cfTime= System.currentTimeMillis(); 
        
        for (int i = 0; i < alts.length ; ++i) {
            if (alts[i] > 0) {
                int destTaz = cumulativeProbMatrix.getExternalNumber(i);
                sampleArray[s] = destTaz;
                k = (double)alts[i] / (nSamples * getProbability(destTaz));
                factors[s] = (float) Math.log(k);
                s++;
            }
        }

        cfTime = System.currentTimeMillis()-cfTime;
        //The sample array may not have 20 samples because
        //a zone may have been sampled more than one time.
        //Fill up the remaining elements of the sample array
        //and the correction factor array with -1 to indicate
        //this.
        uniqueSamples = s;
        while (s < nSamples) {
            sampleArray[s] = -1;
            factors[s] = -1;
            s++;
        }
        return new long[] {fillTime, choiceTime, cfTime};
    }

    /**
     * This method will return an internal number (index into array)
     * To get the destination TAZ, the external number must be
     * called for.
     * @return index into cumulativeProb matrix
     */
    private int choose() {
        fillCumulativeProbabilitiesArray();
        return SearchSortedArray.searchForInsertionPoint(cumulativeProbabilities);
    }
    
    private void fillCumulativeProbabilitiesArray(){
        cumulativeProbMatrix.getRow(origin, cumulativeProbabilities);
    }

    private float getProbability(int alternative) {
        return probabilityMatrix.getValueAt(origin,alternative);
    }
    
    public int getSampleSetCount() {
        return uniqueSamples;
    }
    
    public int[] getSampleArray() {
        return sampleArray;
    }
    
    public int getSample(int i) {
        return sampleArray[i];
    }
    
    public float[] getCorrectionFactors(){
        return factors;
    }
    
    public float getCorrectionFactor(int i) {
        return factors[i];
    }

 
}