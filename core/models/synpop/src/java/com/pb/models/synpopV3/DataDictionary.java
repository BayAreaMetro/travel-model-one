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
 */
package com.pb.models.synpopV3;

import java.io.BufferedReader;
import java.io.FileReader;

import java.util.ArrayList;
import java.util.StringTokenizer;
import org.apache.log4j.Logger;



/**
 * The DataDictionary class in the synpop.pums package reads and defines
 * the PUMS data dictionary for reading PUMS HH and Person data records.
 *
 */
public class DataDictionary {
	//default setting, use setter methods to change them
    private int NUMFIELDS=4;
    private int NUMHHATTRIBS=120;
    private int NUMPERSATTRIBS=130;
    
    public static final boolean DEBUG = false;
    protected Logger logger = Logger.getLogger("com.pb.models.synpopV3");
    public ArrayList HHAttribs;
    public ArrayList PersAttribs;

    public DataDictionary(String fileName) {
        this.HHAttribs = new ArrayList(NUMHHATTRIBS);
        this.PersAttribs = new ArrayList(NUMPERSATTRIBS);

        readPUMSDataDictionary(fileName);
        logger.info(this.HHAttribs.size() + " PUMS HH variables read.");
        logger.info(this.PersAttribs.size() +
            " PUMS Person variables read.");
    }
    
    public DataDictionary(String fileName, int NUMFIELDS, int NUMHHATTRIBS, int NUMPERSATTRIBS){
    	this.NUMFIELDS=NUMFIELDS;
    	this.NUMHHATTRIBS=NUMHHATTRIBS;
    	this.NUMPERSATTRIBS=NUMPERSATTRIBS;
        this.HHAttribs = new ArrayList(NUMHHATTRIBS);
        this.PersAttribs = new ArrayList(NUMPERSATTRIBS);

        readPUMSDataDictionary(fileName);
        logger.info(this.HHAttribs.size() + " PUMS HH variables read.");
        logger.info(this.PersAttribs.size() +
            " PUMS Person variables read.");
    }
    

    public int getStartCol(ArrayList attribs, String PUMSVariable) {
        int i = getPUMSVariableIndex(attribs, PUMSVariable);

        if (DEBUG) {
            logger.info("getStartCol PUMSVariable = " + PUMSVariable);
            logger.info("getStartCol PUMSVariable Index = " + i);
            logger.info("getStartCol PUMSVariable startCol = " +
                (((DataDictionaryRecord) attribs.get(i)).startCol));
        }

        return ((DataDictionaryRecord) attribs.get(i)).startCol;
    }

    public int getNumberCols(ArrayList attribs, String PUMSVariable) {
        int i = getPUMSVariableIndex(attribs, PUMSVariable);

        if (DEBUG) {
            logger.info("getNumberCols PUMSVariable = " + PUMSVariable);
            logger.info("getNumberCols PUMSVariable Index = " + i);
            logger.info("getNumberCols PUMSVariable numberCols = " +
                ((DataDictionaryRecord) attribs.get(i)).numberCols);
        }

        return ((DataDictionaryRecord) attribs.get(i)).numberCols;
    }

    public int getLastCol(ArrayList attribs, String PUMSVariable) {
        int i = getPUMSVariableIndex(attribs, PUMSVariable);

        if (DEBUG) {
            logger.info("getLastCol PUMSVariable = " + PUMSVariable);
            logger.info("getLastCol PUMSVariable Index = " + i);
            logger.info("getLastCol PUMSVariable lastCol = " +
                (((DataDictionaryRecord) attribs.get(i)).startCol +
                ((DataDictionaryRecord) attribs.get(i)).numberCols));
        }

        return ((DataDictionaryRecord) attribs.get(i)).startCol +
        ((DataDictionaryRecord) attribs.get(i)).numberCols;
    }

    public void printDictionary(ArrayList attribs) {

        if (attribs.size() > 0) {
            logger.info( String.format("%8s%16s%16s%16s", "Index", "Variable", "Start Column", "Number Columns") );
        }

        for (int i = 0; i < attribs.size(); i++) {
            logger.info( String.format("%-8d", i) );
            logger.info( String.format("%16d", ((DataDictionaryRecord) attribs.get(i)).variable) );
            logger.info( String.format("%16d", ((DataDictionaryRecord) attribs.get(i)).startCol) );
            logger.info( String.format("%16d", ((DataDictionaryRecord) attribs.get(i)).numberCols) );
        }
    }
    
    public ArrayList getHHAttribs(){
    	return HHAttribs;
    }
    
    public ArrayList getPersonAttribs(){
    	return PersAttribs;
    }

    private int getPUMSVariableIndex(ArrayList attribs, String PUMSVariable) {
        int index = -1;

        for (int i = 0; i < attribs.size(); i++) {
            if (((DataDictionaryRecord) attribs.get(i)).variable.equals(
                        PUMSVariable)) {
                index = i;

                break;
            }
        }

        if (index < 0) {
            logger.fatal("PUMS variable: " + PUMSVariable +
                " not found in data dictionary.");
            logger.fatal("exiting getPUMSVariableIndex(" + PUMSVariable +
                ") in DataDictionary.");
            logger.fatal("exit (10)");
            System.exit(10);
        }

        return index;
    }

    private void readPUMSDataDictionary(String fileName) {
        String token;
        int attrib;
        int tokenCount;
        int RECTYPECount = 0;

        try {
            BufferedReader in = new BufferedReader(new FileReader(fileName));
            String s = new String();

            // skip the first record (header) which defines fields
            s = in.readLine();

            while ((s = in.readLine()) != null) {
                if (s.length() > 0) {
                    StringTokenizer st = new StringTokenizer(s);
                    tokenCount = st.countTokens();

                    if (st.hasMoreTokens()) {
                        // only parse records beginning with "D"
                        token = st.nextToken();

                        if (token.equals("D")) {
                            if (tokenCount != NUMFIELDS) {
                                if (RECTYPECount <= 1) {
                                    attrib = HHAttribs.size();
                                } else {
                                    attrib = PersAttribs.size();
                                }

                                logger.fatal("data definition for attrib " +
                                    attrib + " in data dictionary file " +
                                    fileName + " has " + st.countTokens() +
                                    " fields, but should have " + NUMFIELDS +
                                    ".");
                                logger.fatal("exiting readPUMSDataDictionary(" +
                                    fileName + ").");
                                logger.fatal("exit (11)");
                                System.exit(11);
                            } else {
                                DataDictionaryRecord ddRecord = new DataDictionaryRecord();

                                ddRecord.variable = st.nextToken();
                                ddRecord.numberCols = Integer.parseInt(st.nextToken());
                                ddRecord.startCol = Integer.parseInt(st.nextToken()) -
                                    1;

                                if (ddRecord.variable.equals("RECTYPE")) {
                                    RECTYPECount++;
                                }

                                if (RECTYPECount == 1) {
                                    HHAttribs.add(ddRecord);
                                } else {
                                    PersAttribs.add(ddRecord);
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            logger.fatal(
                "IO Exception caught reading data dictionary file: " +
                fileName);
            e.printStackTrace();
        }
    }

    private class DataDictionaryRecord {
        String variable;
        int startCol;
        int numberCols;
    }
}
