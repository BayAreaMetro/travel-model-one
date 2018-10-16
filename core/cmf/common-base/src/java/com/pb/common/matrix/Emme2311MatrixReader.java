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

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Set;
import java.util.StringTokenizer;
import java.util.TreeSet;

import org.apache.log4j.Logger;

/**
 * Implementes a MatrixReader to read matrices from a .311 text file.
 *
 * @author    Joel Freedman
 * @version   1.0, 6/2003
 */
public class Emme2311MatrixReader extends MatrixReader {

    protected Logger logger = Logger.getLogger("com.pb.common.matrix");

    private BufferedReader inStream = null;
    /**
     * @param file represents the physical matrix file
     */
    public Emme2311MatrixReader(File file) {
        this.file = file;

    }


    public Matrix[] readMatrices() throws MatrixException{
        
          throw new UnsupportedOperationException("Not yet implemented");
       
    }
    /**
     * TODO: matrix reader
     */
     public Matrix readMatrix() throws MatrixException {
         int[] externalNumbers = readZoneIds();
         Matrix m = readContent(externalNumbers);
         return m;
         
    }

    private Matrix readContent(int[] externalNumbers) {
        openFile();
        Matrix m = new Matrix(externalNumbers.length,externalNumbers.length);
        readHeader(m);
        m.setExternalNumbers(externalNumbers);
        try {
            String line;
            while((line=inStream.readLine())!=null) {
                String[] lineElements = line.split("[\\s:]+");
                if (lineElements.length>1) {
                    int origin = (Integer.valueOf(lineElements[1])).intValue();
                    for (int c=2;c<lineElements.length;c+=2) {
                        int destination = Integer.valueOf(lineElements[c]).intValue();
                        float value;
                        if (lineElements[c+1] == null) {
                            throw new RuntimeException("Can't parse line "+line);
                        }
                        if (lineElements[c+1].length()==0) {
                            throw new RuntimeException("Empty substring parsing line "+line);
                        }
                        if(lineElements[c+1].charAt(0)=='*') value = Float.NEGATIVE_INFINITY;
                        else value = Float.valueOf(lineElements[c+1]).floatValue();
                        m.setValueAt(origin,destination,value);
                    }
                }
            }
            inStream.close();
            
        } catch (IOException e) {
            throw new MatrixException(e, "IOException reading emme2 311 matrix");
        }
        return m;
    }


    private int[] readZoneIds() {
        openFile();
        int[] externalNumbers;
        try {
            // first 4 rows are header
            for (int hRow = 0; hRow <4; hRow++) {
                inStream.readLine();
            }
            Set <Integer> uniqueOrigValues = new TreeSet <Integer> ();
            Set <Integer> uniqueDestValues = new TreeSet <Integer> ();
            String line;
            while((line=inStream.readLine())!=null) {
                String[] lineElements = line.split("[\\s:]+");
                if (lineElements.length>1) {
                    uniqueOrigValues.add(Integer.valueOf(lineElements[1]));
                    for (int c=2;c<lineElements.length;c+=2) {
                        uniqueDestValues.add(Integer.valueOf(lineElements[c]));
                    }
                }
            }
            if (uniqueOrigValues.size() != uniqueDestValues.size()) {
                logger.error("You are attempting to create a non-square matrix.");
                logger.error("Number of origins: " + uniqueOrigValues.size());
                logger.error("Number of destinations: "+ uniqueDestValues.size());
                throw new RuntimeException();
            }

            externalNumbers = new int[uniqueOrigValues.size() + 1];
            int index = 1;

            for (Object element : uniqueOrigValues) {
                externalNumbers[index] = (Integer) element;
                index++;
            }
            inStream.close();
            
        } catch (IOException e) {
            throw new MatrixException(e, "IOException reading emme2 311 matrix");
        }
        return externalNumbers;
    }


    private void readHeader(Matrix m) {
        // throw away first 3 lines
        try {
            inStream.readLine();
            inStream.readLine();
            inStream.readLine();
            String s = inStream.readLine();
            String[] parts = s.split("\\s+",3);
            m.name = parts[1].split("=")[1];
            if (!parts[1].split("=")[0].equals("matrix")) {
                throw new MatrixException("Emme2 matrix file does not have correct format, need \"matrix=\" in line 4 followed by the matrix name");
            }
            m.description=parts[2];
        } catch (IOException e) {
            throw new MatrixException(e, "Can't open Emme2 311 matrix file");
        }
    }


    public Matrix readMatrix(String index) throws MatrixException{
        throw new UnsupportedOperationException("Use method, readMatrix()");
    }

    private void openFile() throws MatrixException {
        logger.debug("Opening file: "+ file);

        try {
            inStream = new BufferedReader( new FileReader(file) );
        }
        catch (Exception e) {
            throw new MatrixException(e, MatrixException.FILE_NOT_FOUND + ", "+ file);
        }

    }




}
