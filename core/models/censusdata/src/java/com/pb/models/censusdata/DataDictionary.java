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
package com.pb.models.censusdata;


import jxl.Cell;
import jxl.Sheet;
import jxl.Workbook;

import java.io.File;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.StringTokenizer;
import org.apache.log4j.Logger;

/**
 * The DataDictionary class reads and defines the PUMS data dictionary
 * for reading PUMS HH and Person data records.  It is possible to read
 * both 1990 and 2000 data formats.
 */
public class DataDictionary {

    protected Logger logger = Logger.getLogger(DataDictionary.class);

	private static final int HH_SHEET = 0;
	private static final int PERSON_SHEET = 1;

    private static final int NUMFIELDS = 4;

    public ArrayList HHAttribs;
    public ArrayList PersAttribs;
    
    String personsFieldName = "";
    String pumaFieldName = "";
    
    
    public DataDictionary (String fileName, String year ) {
        
        this.HHAttribs = new ArrayList();
        this.PersAttribs = new ArrayList();

        if ( year.equals("1990") ) {
            readPUMS1990DataDictionary(fileName);
            personsFieldName = "PERSONS";
            pumaFieldName = "PUMA";
        }
        else if ( year.equals("2000") ) {
            readPUMS2000DataDictionary(fileName);
            personsFieldName = "PERSONS";
            pumaFieldName = "PUMA5";
        }
        else {
            logger.error ("invalid year specified for DataDictionary(fileName=" + fileName + ", year=" + year + ").");
            logger.error ( "", new Exception() );
            System.exit(1);
        }
        
        logger.info (this.HHAttribs.size() + " PUMS HH variables read.");
        logger.info (this.PersAttribs.size() + " PUMS Person variables read.");
    }
    

    public String getPersonsFieldName() {
        return personsFieldName;
    }
    
    
    public String getPumaFieldName() {
        return pumaFieldName;
    }
    
    
    public int getStartCol (ArrayList attribs, String PUMSVariable) {
    
        int i = getPUMSVariableIndex (attribs, PUMSVariable);
        if(logger.isDebugEnabled()) {
            logger.debug ("getStartCol PUMSVariable = " + PUMSVariable);
            logger.debug ("getStartCol PUMSVariable Index = " + i);
            logger.debug ("getStartCol PUMSVariable startCol = " + (((DataDictionaryRecord)attribs.get(i)).startCol));
        }
        return ((DataDictionaryRecord)attribs.get(i)).startCol;
    }
    
        
    public int getNumberCols (ArrayList attribs, String PUMSVariable) {
    
        int i = getPUMSVariableIndex (attribs, PUMSVariable);
        if(logger.isDebugEnabled()) {
            logger.debug ("getNumberCols PUMSVariable = " + PUMSVariable);
            logger.debug ("getNumberCols PUMSVariable Index = " + i);
            logger.debug ("getNumberCols PUMSVariable numberCols = " + ((DataDictionaryRecord)attribs.get(i)).numberCols);
        }
        return ((DataDictionaryRecord)attribs.get(i)).numberCols;
    }
    
        
    public int getLastCol (ArrayList attribs, String PUMSVariable) {
    
        int i = getPUMSVariableIndex (attribs, PUMSVariable);
        if(logger.isDebugEnabled()) {
            logger.debug ("getLastCol PUMSVariable = " + PUMSVariable);
            logger.debug ("getLastCol PUMSVariable Index = " + i);
            logger.debug ("getLastCol PUMSVariable lastCol = " + (((DataDictionaryRecord)attribs.get(i)).startCol + ((DataDictionaryRecord)attribs.get(i)).numberCols));
        }
        return ((DataDictionaryRecord)attribs.get(i)).startCol + ((DataDictionaryRecord)attribs.get(i)).numberCols;
    }
    
       
    public void printDictionary (ArrayList attribs) {
        
        int blanks;
        
        if (attribs.size() > 0)
            logger.info ("Index    Variable      Start Column    Number Columns");
        for (int i=0; i < attribs.size(); i++) {
            
            logger.info (String.format("%-5d", i));
            logger.info (String.format("%-5d", i));

            blanks = 12 - ((DataDictionaryRecord)attribs.get(i)).variable.length();
            for (int b=0; b < blanks; b++)
                logger.info (" ");
            logger.info (((DataDictionaryRecord)attribs.get(i)).variable);
            
            blanks = 6;
            for (int b=0; b < blanks; b++)
                logger.info (" ");
            logger.info (String.format("%12d", ((DataDictionaryRecord)attribs.get(i)).startCol));
            
            blanks = 6;
            for (int b=0; b < blanks; b++)
                logger.info (" ");
            logger.info (String.format("%12d", ((DataDictionaryRecord)attribs.get(i)).numberCols));
        }

    }
    
     
    private int getPUMSVariableIndex (ArrayList attribs, String PUMSVariable) {
    
        int index = -1;
        
        for (int i=0; i < attribs.size(); i++) {
            String dataDictionaryEntry = ((DataDictionaryRecord)attribs.get(i)).variable;
            String dataDictionaryEntryTrimmed = dataDictionaryEntry.trim();
            if ( dataDictionaryEntryTrimmed.equalsIgnoreCase(PUMSVariable) ) {
                index = i;
                break;
            }
        }
        
        if (index < 0) {
            logger.fatal("PUMS variable: " + PUMSVariable + " not found in data dictionary.");
            logger.fatal("exiting getPUMSVariableIndex(" + PUMSVariable + ") in DataDictionary.");
            logger.fatal("exit (10)");
            System.exit (10);
        }
        
        return index;
    }


    
    private void readPUMS1990DataDictionary (String fileName) {
    
        String token;
        int attrib;
        int tokenCount;
        int RECTYPECount=0;
                
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
                                if (RECTYPECount <= 1)
                                    attrib = HHAttribs.size();
                                else
                                    attrib = PersAttribs.size();
                                logger.fatal("data definition for attrib " + attrib + " in data dictionary file " + fileName + " has " + st.countTokens() + " fields, but should have " + NUMFIELDS + ".");
                                logger.fatal("exiting readPUMSDataDictionary(" + fileName + ").");
                                logger.fatal("exit (11)");
                                System.exit (11);
                            }
                            else {
                                DataDictionaryRecord ddRecord = new DataDictionaryRecord();
                            
                                ddRecord.variable = st.nextToken();
                                ddRecord.numberCols = Integer.parseInt(st.nextToken());
                                ddRecord.startCol = Integer.parseInt(st.nextToken()) - 1;
                                
                                if (ddRecord.variable.equals("RECTYPE"))
                                    RECTYPECount++;
                                    
                                if (RECTYPECount == 1)
                                    HHAttribs.add(ddRecord);
                                else
                                    PersAttribs.add(ddRecord);
                            }
                        }
                    }
                }
                
            }
        } catch (Exception e) {
            logger.fatal ("IO Exception caught reading data dictionary file: " + fileName);
            e.printStackTrace();
        }
        
    }



	protected void readPUMS2000DataDictionary ( String fileName ) {
    
		Workbook workbook = null;
		
		try {
			workbook = Workbook.getWorkbook( new File(fileName) );
		}
		catch (Throwable t) {
			t.printStackTrace();
		}

		
		HHAttribs = readExcelDataDictionary ( workbook, "HH" );
		PersAttribs = readExcelDataDictionary ( workbook, "PERSON" );
		
	}



    protected ArrayList readExcelDataDictionary ( Workbook workbook, String definitionType ) {
        
        ArrayList attribs = new ArrayList();
        
        String recordType = null;
        
        Cell cell;
        Sheet sheet = null;
        
        if ( definitionType.equalsIgnoreCase("HH") ) {
            sheet = workbook.getSheet( HH_SHEET );
            recordType = "H";
        }
        else if ( definitionType.equalsIgnoreCase("PERSON") ) {
            sheet = workbook.getSheet( PERSON_SHEET );
            recordType = "P";
        }
        else {
            return null;
        }
        
        
        // H record indicators are in column 0
        int row = findEntry(sheet, recordType, 0, 0, false);
        if (row == -1)
            //No matching data records found
            return null;

        
        while (true) {

            DataDictionaryRecord ddRecord = new DataDictionaryRecord();
            
            // record type indicators are in column 0 (excel column A)
            row = findEntry(sheet, recordType, row, 0, false);
            if (row == -1)
                //No more matching data records found
                return attribs;
            
            // VARIABLE field is in column 5 (excel column F)
            cell = sheet.getCell( 5, row );
            ddRecord.variable = cell.getContents();

            // BEG field is in column 1 (excel column B)
            cell = sheet.getCell( 1, row );
            ddRecord.startCol = Integer.parseInt( cell.getContents() ) - 1;

            // LEN field is in column 3 (excel column D)
            cell = sheet.getCell( 3, row );
            ddRecord.numberCols = Integer.parseInt( cell.getContents() );

            attribs.add(ddRecord);
            
            row++;
            
        }
        
    }



	protected int findEntry(Sheet sheet, String keyword, int startRow, int startColumn, boolean fail) {
		int rowFound = -1;
		String str;

		try {
			for (int r=startRow; r < sheet.getRows(); r++) {
				Cell cell = sheet.getCell(startColumn, r);
				str = cell.getContents();
				if (str.equalsIgnoreCase(keyword)) {
					rowFound = r;
					break;
				}
			}
		} catch (RuntimeException e) {
			//Did not find keyword
		}

		if ( (rowFound < 0) && (fail) ) {
			String msg = "Control file does not contain a \""+keyword+"\" section";
			throw new RuntimeException(msg);
		}

		return rowFound;
	}

	
	
    protected class DataDictionaryRecord {
        String variable;
        int startCol;
        int numberCols;
    }
}

