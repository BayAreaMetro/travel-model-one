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
 * Created on Jul 14, 2004
 *
 * To change the template for this generated file go to
 * Window - Preferences - Java - Code Generation - Code and Comments
 */
package com.pb.common.matrix;

import java.io.IOException;
import java.io.Writer;

/**
 * @author jabraham
 *
 * A class representing a histogram of the values in a matrix
 */
public class MatrixHistogram {
    
    private double[] bandBoundaries;
    private double[] bandQuantities;
    private double[] bandAverageLengths;
    
    

    /**
     * @return Returns the bandAverageLengths.
     */
    public double[] getBandAverageLengths() {
        return bandAverageLengths;
    }

    /**
     * @param bandBoundaries
     */
    public MatrixHistogram(double[] bandBoundaries) {
        this.bandBoundaries = bandBoundaries;
        bandQuantities = new double[bandBoundaries.length+1];
        bandAverageLengths = new double[bandBoundaries.length+1];
       }
    
    public double[] generateHistogram(Matrix boundaryMatrix, Matrix quantityMatrix) {
        bandQuantities = new double[bandBoundaries.length+1];
        bandAverageLengths = new double[bandBoundaries.length+1];
        int[] externalNumbers = quantityMatrix.getExternalNumbers();
        for (int i=1;i<externalNumbers.length;i++) {
            for (int j=1;j<externalNumbers.length; j++)  {
                float boundary = boundaryMatrix.getValueAt(externalNumbers[i],externalNumbers[j]);
                float quantity = quantityMatrix.getValueAt(externalNumbers[i],externalNumbers[j]);
                int b = 0;
                boolean foundBand = false;
                do {
                    if (b < bandBoundaries.length) {
                        if (bandBoundaries[b] > boundary) {
                            if (quantity >0) {
                                bandAverageLengths[b] = (bandAverageLengths[b]*bandQuantities[b] + boundary * quantity)/(bandQuantities[b]+quantity);
                            }
                            // found it;
                            bandQuantities[b] += quantity;
                            // force termination
                            foundBand = true;
                        }
                    } else {
                        // last band
                        if (quantity >0) {
                            bandAverageLengths[b] = (bandAverageLengths[b]*bandQuantities[b] + boundary * quantity)/(bandQuantities[b]+quantity);
                        }
                        bandQuantities[b] += quantity;
                        foundBand = true;
                    }
                    b++;
                } while (!foundBand);
            }
        }
        return bandQuantities;
    }


    double[] getBandQuantities() {
        return bandQuantities;
    }

    void setBandBoundaries(double[] bandBoundaries) {
        this.bandBoundaries = bandBoundaries;
    }

    double[] getBandBoundaries() {
        return bandBoundaries;
    }

    /**
     * @param commodity
     * @param direction
     * @param w
     *
     */
    public void writeHistogram(String commodity, String direction, Writer w) throws IOException{
        for (int b=0;b<bandQuantities.length;b++) {
            double boundary = 0;
            if (b!=0) boundary = bandBoundaries[b-1]; 
            w.write(commodity+","+direction+","+b+","+boundary+","+bandQuantities[b]+","+bandAverageLengths[b]+"\n");
        }
    }
    
}
