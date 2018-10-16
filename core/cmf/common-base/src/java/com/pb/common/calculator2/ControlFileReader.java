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

import com.pb.common.util.ResourceUtil;
import jxl.Cell;
import jxl.Sheet;
import jxl.Workbook;
import jxl.WorkbookSettings;

import org.apache.log4j.Logger;

import java.io.File;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Reads a input file for the UEC class.
 *
 * @author    Tim Heier
 * @version   1.0, 2/28/2003
 */

public class ControlFileReader implements Serializable {

    public static int ALTERNATIVE_START_COL = 6;

    protected transient Logger logger = Logger.getLogger(ControlFileReader.class);
    protected File file;
    protected HashMap env;
    protected int modelSheet;
    protected int dataSheet;

    protected transient Workbook workbook;

    //Data from control file
    public ModelHeader header;
    public ModelEntry[] modelEntries;
    public ModelAlternative[] alternatives;

    public int[][] nestedAlternatives;
    public double[][] nestingCoefficients;
    
    //Initialize to zero incase there are no entries in control file
    public DataEntry[] tableEntries = new DataEntry[0];
    public DataEntry[] matrixEntries = new DataEntry[0];

    
    public float[][] coefficients;

    private ControlFileReader() {
    }

    
    public ControlFileReader(File file, HashMap env, int modelSheet, int dataSheet) {

        if (logger.isDebugEnabled()){
            logger.debug("excel library version="+Workbook.getVersion());
            logger.debug("file="+file);
            logger.debug("modelSheet="+modelSheet);
            logger.debug("dataSheet="+dataSheet);
        }
        this.file = file;
        this.env = env;
        this.modelSheet = modelSheet;
        this.dataSheet = dataSheet;

        //There is no data sheet
        if (this.dataSheet == -1) {
            return;
        }

        printEnvironmentVariables();

        try {
            WorkbookSettings ws = new WorkbookSettings();
            //ws.setGCDisabled( true );
            this.workbook = Workbook.getWorkbook( file, ws );
        }
        catch (Throwable t) {
            t.printStackTrace();
        }

        readModelHeader();
        readAlternativeHeader();
        readModelEntries();

        ArrayList tableList = readTableDataEntries();
        ArrayList matrixList = readMatrixDataEntries();


        
        //Convert list of table entries to an array
        tableEntries = new DataEntry[tableList.size()];
        for (int r=0; r < tableList.size(); r++) {
            tableEntries[r] = (DataEntry) tableList.get(r);
        }

        //Convert list of matrix entries to an array
        matrixEntries = new DataEntry[matrixList.size()];
        for (int r=0; r < matrixList.size(); r++) {
            matrixEntries[r] = (DataEntry) matrixList.get(r);
        }

        if ( logger.isDebugEnabled()) {
            for (int r=0; r < tableEntries.length; r++) {
                logger.debug("entry: "+tableEntries[r]);
            }
            for (int r=0; r < matrixEntries.length; r++) {
                logger.debug("entry: "+matrixEntries[r]);
            }
        }

    }


    private void printEnvironmentVariables() {

        if (env == null)
            env = new HashMap();

        if ( logger.isDebugEnabled()) {

        	//Print environment entries
	        Iterator keys = env.keySet().iterator();
	        while (keys.hasNext()) {
	            String name = (String) keys.next();
	            String value = (String) env.get(name);
	            logger.debug(name + "=" + value);
	        }
	        
        }

    }

    /**
     * Read the header for the model record.
     */
    protected void readModelHeader() {

        Cell cell;
        Sheet sheet = workbook.getSheet( modelSheet );

        int row = findEntry(sheet, "Model", 0, 0, true);

        cell = sheet.getCell(1, row);
        float number = Float.parseFloat( cell.getContents() );

        cell = sheet.getCell(2, row);
        String description = cell.getContents();

        cell = sheet.getCell(5, row);
        String dmu = cell.getContents();

        //Read number of alternatives or keyword
        cell = sheet.getCell(7, row);
        String value = cell.getContents();

        int numberOfAlts = 1;
        boolean isAlternativesInFile = false;

        if ( (value != null) && (value.toUpperCase().equals("FILE")) ) {
            isAlternativesInFile = true;
        }
        else {
            numberOfAlts = Integer.parseInt( cell.getContents() );
            isAlternativesInFile = false;
        }

        //Read number of levels in NL model; assume MNL if cell is 0, 1 or blank
        cell = sheet.getCell(9, row);
        int numberOfLevels = 1;
        try {
            numberOfLevels = Integer.parseInt( cell.getContents() );
        }
        catch ( NumberFormatException e ){
            numberOfLevels = 1;
        }
        if ( numberOfLevels < 1 )
            numberOfLevels = 1;
        
        header = new ModelHeader(number, description, dmu, numberOfAlts, numberOfLevels, isAlternativesInFile);

        if (logger.isDebugEnabled()) {
            logger.debug("model: "+header.toString());
        }

    }


    /**
     * Read the header for the model record.
     */
    protected void readAlternativeHeader() {

        Sheet sheet = workbook.getSheet( modelSheet );

        int row;
        row = findEntry(sheet, "Model", 0, 0, true);
        row = findEntry(sheet, "No", row, 0, true);

        row++;  //alternative names should be on next line

        alternatives = new ModelAlternative[header.numberOfAlts];

        for (int col=0; col < header.numberOfAlts; col++) {
            Cell cell = sheet.getCell(col+ALTERNATIVE_START_COL, row);
            String name = cell.getContents();
            alternatives[col] = new ModelAlternative(col+1, name);

            if ( logger.isDebugEnabled()){
                logger.debug("alternative: "+alternatives[col].toString());
            }
        }

    
        // if there was an entry in the header for number of levels (and the number > 1),
        // that number of lines follows the alternatives names to define the nesting structure,
        // then the same number of lines follows those to define the nesting coefficients.

        if ( header.numberOfLevels > 1 ) {
        
            nestedAlternatives = new int[header.numberOfLevels][header.numberOfAlts];
            
            for (int r=0; r < header.numberOfLevels; r++) {

                row++;
    
                for (int col=0; col < header.numberOfAlts; col++) {
                    Cell cell = sheet.getCell(col+ALTERNATIVE_START_COL, row);
                    int levelIndex = Integer.parseInt( cell.getContents() );
                    nestedAlternatives[r][col] = levelIndex;
        
                    if ( logger.isDebugEnabled()){
                        logger.debug( String.format ("level%d: col=%d, index=%d", r, col, levelIndex) );
                    }
                }
                
            }

            
            nestingCoefficients = new double[header.numberOfLevels][header.numberOfAlts];
            
            for (int r=0; r < header.numberOfLevels; r++) {

                row++;
    
                for (int col=0; col < header.numberOfAlts; col++) {
                    Cell cell = sheet.getCell(col+ALTERNATIVE_START_COL, row);
                    try {
                        nestingCoefficients[r][col] =  Double.parseDouble( cell.getContents() );
                    }
                    catch ( NumberFormatException e ){
                        nestingCoefficients[r][col] = 0.0;
                    }
        
                    if ( logger.isDebugEnabled()){
                        logger.debug( String.format ("level%d: col=%d, index=%.6f", r, col, nestingCoefficients[r][col]) );
                    }
                }
                
            }
        
        }

    }


    /**
     * Read the entries for the model record.
     */
    protected void readModelEntries() {

        Sheet sheet = workbook.getSheet( modelSheet );

        int row;
        row = findEntry(sheet, "Model", 0, 0, true);
        row = findEntry(sheet, "1", row, 0, true);

        Cell cell;

        //Temporary lists. We don't know how many entries there are.
        ArrayList entryList = new ArrayList();
        ArrayList coeffList = new ArrayList();

        while (true) {

			//Check for end of input
			if ( row == sheet.getRows() ) {
				break;
			}

            cell = sheet.getCell(0, row);
            String number = cell.getContents();

            //Check for end of input
            if ( (number == null) || (number.length() == 0) ) {
                break;
            }

            cell = sheet.getCell(1, row);
            String name = cell.getContents().trim();

            cell = sheet.getCell(2, row);
            String description = cell.getContents();

            cell = sheet.getCell(3, row);
            String filter = cell.getContents().trim();

            cell = sheet.getCell(4, row);
            String expression = cell.getContents().trim();

            cell = sheet.getCell(5, row);
            String index = cell.getContents().trim();

            //Add entry object to array list (temporarily)
            ModelEntry entry = new ModelEntry(name, description, filter, expression, index);
            entryList.add( entry );

            //Read coefficients for each alternative
            float[] coeff = new float[header.numberOfAlts];

            for (int col=0; col < header.numberOfAlts; col++) {
                cell = sheet.getCell(col+ALTERNATIVE_START_COL, row);
                String str = cell.getContents();
                if ( (str != null) && (str.length() > 0) )
                    coeff[col] = Float.parseFloat( str );
                else
                    coeff[col] = 0;

            }
            coeffList.add( coeff );

            row++;
        }

        //Convert array list of entries to an array
        modelEntries = new ModelEntry[entryList.size()];
        for (int r=0; r < entryList.size(); r++) {
            modelEntries[r] = (ModelEntry) entryList.get(r);
        }

        //Convert array list of coeffcients to an array of float
        coefficients = new float[coeffList.size()][header.numberOfAlts];
        for (int r=0; r < coeffList.size(); r++) {
            coefficients[r] = (float[]) coeffList.get(r);
        }

        if ( logger.isDebugEnabled()){
            for (int r=0; r < coeffList.size(); r++) {
                logger.debug("entry: "+modelEntries[r]);
            }

            for (int r=0; r < coeffList.size(); r++) {
                StringBuffer sb = new StringBuffer(256);
                sb.append("coeff:");
                for (int col=0; col < header.numberOfAlts; col++) {
                    sb.append("  " + coefficients[r][col]);
                }
                logger.debug(sb.toString());
            }
        }

    }


    protected ArrayList readTableDataEntries() {

        //Holds the entries found in the section
        ArrayList dataList = new ArrayList();

        Cell cell;

        Sheet sheet = workbook.getSheet( dataSheet );

        int row;
        row = findEntry(sheet, "Table Data", 0, 0, false);
		if (row == -1) {
			//No Table data section was found
			return dataList;
		}

		row = findEntry(sheet, "1", row, 0, false);
        if (row == -1) {
			//No Table data entries were found
            return dataList;
        }

        while (true) {

            cell = sheet.getCell(1, row);
            String type = cell.getContents();

            //Check for end of input
            if ( (type == null) || (type.length() == 0) ) {
                break;
            }

            cell = sheet.getCell(2, row);
            String format = cell.getContents();
			format = searchAndReplaceWithEnv( format );

			
            cell = sheet.getCell(3, row);
            String fileName = cell.getContents();
            fileName = searchAndReplaceWithEnv( fileName );

            
            //Add entry object to list
            DataEntry entry = new DataEntry(type, format, fileName);
            dataList.add( entry );

            row++;
        }

        return dataList;
    }


    protected ArrayList readMatrixDataEntries() {

        //Holds entries found in the section
        ArrayList matrixList = new ArrayList();

        Cell cell;
        Sheet sheet = workbook.getSheet( dataSheet );

        int row;
        row = findEntry(sheet, "Matrix Data", 0, 0, false);
		if (row == -1) {
			//No Matrix data section was found
			return matrixList;
		}

		row = findEntry(sheet, "1", row, 0, false);
		if (row == -1) {
			//No Matrix data entries were found
			return matrixList;
		}


        while (true) {
			
			if ( row >= sheet.getRows() ) {
				break;
			}
			
			
            cell = sheet.getCell(1, row);
            String name = cell.getContents();

            //Check for end of input
            if ( (name == null) || (name.length() == 0) ) {
                break;
            }

            cell = sheet.getCell(2, row);
            String format = cell.getContents();
			format = searchAndReplaceWithEnv( format );

			
            cell = sheet.getCell(3, row);
            String fileName = cell.getContents();

            cell = sheet.getCell(4, row);
            String matrixName = cell.getContents();

            cell = sheet.getCell(5, row);
            String groupName = cell.getContents();

            cell = sheet.getCell(6, row);
            String indexFlag = cell.getContents();

            String gName  = (groupName == null) ? "" : groupName;
            boolean iFlag = ((indexFlag != null) && (indexFlag.trim().length() > 0)) ? true : false;

            fileName = searchAndReplaceWithEnv( fileName );

            //Add entry object to array list (temporarily)
            DataEntry entry = new DataEntry("matrix", name, format, fileName, matrixName, gName, iFlag);
            matrixList.add( entry );

            row++;
        }

        return matrixList;
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

        /*
        if (LogConstants.DEBUG) {
            Logger.logDebug("found \""+keyword+"\"on row="+rowFound+", column="+startColumn);
        }
        */

        return rowFound;
    }

    public ModelHeader getHeader() {
        return header;
    }

    public ModelEntry[] getModelEntries() {
        return modelEntries;
    }

    public ModelAlternative[] getAlternatives() {
        return alternatives;
    }

    public DataEntry[] getTableEntries() {
        return tableEntries;
    }

    public DataEntry[] getMatrixEntries() {
        return matrixEntries;
    }

    public float[][] getCoefficients() {
        return coefficients;
    }

    public int[][] getNestedAlternatives() {
        return nestedAlternatives;
    }
    
    public double[][] getNestingCoefficients() {
        return nestingCoefficients;
    }
    
    /*
     * Search and replace patterns in a string based on values in the environment.
     */
    private String searchAndReplaceWithEnv(String inputStr) {

        String tempStr = new String( inputStr );

        //Check properties defined on command-line first
        String replacedString = ResourceUtil.replaceWithSystemPropertyValues(tempStr);

        //Next iterate over properties passed HashMap
        Iterator keys = env.keySet().iterator();
        while (keys.hasNext()) {
            String name = (String) keys.next();
            String value = (String) env.get(name);

            //If the property is defined on the command-line, it will replace what the user
            //passed in the environment (i.e. HashMap)
            value = ResourceUtil.checkSystemProperties(name, value);

            String patternStr = "%" + name + "%";
            Pattern pattern = Pattern.compile(patternStr);

            // Replace all occurrences of pattern in input
            Matcher matcher = pattern.matcher(replacedString);
            replacedString = matcher.replaceAll(value);
        }

        if ( logger.isDebugEnabled())
        	logger.debug("replacing input string = " + inputStr + ", output string = " + replacedString);


        if (replacedString.equals(""))
            return inputStr;
        else
            return replacedString;
    }


    public static void main(String[] args) {
        ControlFileReader file = new ControlFileReader(new File(args[0]), null, 1, 1);
    }

}
