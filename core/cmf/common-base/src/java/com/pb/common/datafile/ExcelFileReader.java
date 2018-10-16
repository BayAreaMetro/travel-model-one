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

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import jxl.CellType;
import jxl.NumberCell;
import jxl.NumberFormulaCell;
import jxl.Workbook;
import jxl.Cell;
import jxl.Sheet;

import org.apache.log4j.Logger;


/**
 * Creates a TableData class from an Excel file.
 *
 * @author Joel Freedman
 * @author John Abraham
 * @version  1.1, 10/10/2007
 *
 * New version checks for cell types and throws an error
 * if it can't get a number value from a cell when it thinks
 * it should (J. Abraham, Sept-Oct 2007)
 */
public class ExcelFileReader extends TableDataFileReader implements  DataTypes {
    
    /**
     * 
     */
    private static final long serialVersionUID = 1L;

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    //These attributes are initialized on each call to readFile()
    private int columnCount;
    private int rowCount;
    private List columnData;
    private ArrayList columnLabels;
    private int[] columnType;
    private String worksheetName;
    private File workbookFile=null;
    
    
    public ExcelFileReader () {
    }
    
    /**
     * Set the name of the worksheet to read in this excel workbook.
     * @param name  THe name of the worksheet to read.
     */
    public void setWorksheetName(String name){
        worksheetName = name;
    }

    public TableDataSet readFile(File file) throws IOException {
        
        if(worksheetName == null){
            logger.fatal("Error:  must set worksheet to read using setWorksheetName method before reading");
            throw new RuntimeException();
        }
        
        return readFile(file, worksheetName, true);
    }

    
    /**
     * Convenience method to load a Excel file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnLabelsPresent  determines whether first line is treated
     *                              as column titles
     * @throws IOException
     * 
     */
    public TableDataSet readFile(File file, String worksheetName, boolean columnLabelsPresent) throws IOException {
        return readFile(file, worksheetName, columnLabelsPresent, null);
    }


    /**
     * Convenience method to load a Excel file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnsToRead list of column labels that should be read - all other
     *                      columns will be dropped from the table data set 
     * @throws IOException
     * 
     */
    public TableDataSet readFile(File file, String worksheetName, String[] columnsToRead) throws IOException {
        return readFile(file, worksheetName,true, columnsToRead);
    }


    /**
     * Main method which loads an Excel file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnLabelsPresent  determines whether first line is treated
     *                              as column titles
     * @param columnsToRead list of column labels that should be read - all other
     *                      columns will be dropped from the table data set 
     * @throws IOException
     * 
     */
	public TableDataSet readFile(File file, String worksheetName, boolean columnLabelsPresent, String[] columnsToRead) throws IOException {
        
		if ((columnsToRead != null) && (columnLabelsPresent == false)) {
			throw new RuntimeException("Column lables provided as filter but there are no column labels in Excel file");
		}
        
		//Initialize class attributes
		columnCount = 0;
		rowCount = 0;
		columnData = new ArrayList();
		columnLabels = new ArrayList();
		columnType = null;
        
		Workbook workbook = null;
           //open workbook
        try {
            workbook = Workbook.getWorkbook( file);
        }
        catch (Throwable t) {
            logger.error("Error attemting to open excel file " + file);
            t.printStackTrace();
        }
        
        Sheet worksheet = workbook.getSheet(worksheetName);
        if (worksheet==null) return null;
		boolean[] readColumnFlag = null;
        
		if (columnLabelsPresent) {
			readColumnFlag = readColumnLabels(worksheet, columnsToRead);
		}
		readData(worksheet, columnLabelsPresent, readColumnFlag);
        
		TableDataSet tds = makeTableDataSet();
		tds.setName(file.toString());
		return tds;
	}
        
        
	/**
	 * Read the excel file with a String[] of specified column formats (NUMBER or STRING),
	 * where the format is specified for all columns, all columns are read,
	 * and column headings must be present on the first line.
     * 
     * @param file  File object of excel workbook
     * @param worksheetName the name of the worksheet to read
     * @param columnFormats An array of column formats.
     * 
     * @return A tableDataSet object containing the data in the worksheet.
	 */
	public TableDataSet readFileWithFormats(File file, String worksheetName, String[] columnFormats) throws IOException {
        
		boolean columnLabelsPresent = true;
		String[] columnsToRead = null;
		
		if ((columnsToRead != null) && (columnLabelsPresent == false)) {
			throw new RuntimeException("Column lables provided as filter but there are no column labels in Excel file");
		}
        
		//Initialize class attributes
		columnCount = 0;
		rowCount = 0;
		columnData = new ArrayList();
		columnLabels = new ArrayList();
		columnType = null;
        
		Workbook workbook = openFile(file);
        Sheet worksheet = workbook.getSheet(worksheetName);
        
		boolean[] readColumnFlag = null;
        
		if (columnLabelsPresent) {
			readColumnFlag = readColumnLabels(worksheet, columnsToRead);
		}
        
		readData( worksheet, columnLabelsPresent, readColumnFlag, columnFormats);
        
		TableDataSet tds = makeTableDataSet();
		tds.setName(file.toString());
		return tds;
	}
        
        
    /**
     * Open file method.
     * @param file  The file.
     * @return The workbook
     * @throws IOException
     */
    private Workbook openFile(File file) throws IOException {
        logger.debug("Opening excel file: "+file);
        
        Workbook workbook = null;
        //open workbook
        try {
             workbook = Workbook.getWorkbook( file );
        }
        catch (Throwable t) {
            logger.error("Error attemting to open excel file " + file);
            t.printStackTrace();
        }
        return workbook;
    }

    /**
     * Read and parse the column titles from the first line of file.
     */
    private boolean[] readColumnLabels(Sheet worksheet, String[] columnsToRead)
            throws IOException {
        
        
        //Read the first cell
        Cell cell = worksheet.getCell(0,0);

        //Test for an empty file
        if (cell.getContents().length()==0) {
            throw new IOException("Error: first row in sheet looks like it's empty");
        }

        int count = countNumberOfColumns(worksheet);
        
        boolean[] readColumnFlag = new boolean[count];
        
        //Initialize the readColumnFlag to false if the caller has supplied a 
        //list of columns. It will be turned to true based on a comparison of the
        //column labels found in the file. Otherwise initialize to true.
        for (int i=0; i < count; i++) {
            if (columnsToRead != null)
                readColumnFlag[i] = false;
            else 
                readColumnFlag[i] = true;
        }
        
        //Read column titles
        int c = 0;
        for (int i=0; i < count; i++) {
            cell = worksheet.getCell(i, 0);
            String column_name = cell.getContents();
            
            //Check if column should be read based on list supplied by caller
            if (columnsToRead != null) {
                for (int j=0; j < columnsToRead.length; j++) {
                    if (columnsToRead[j].equalsIgnoreCase(column_name)) {
                        readColumnFlag[c] = true;

                        columnLabels.add(column_name);
                        columnCount++;
                        break;
                    }
                }
            }
            else {
                columnLabels.add(column_name);
                columnCount++;
            }
            c++; //the actual columnn number in the file being read
        }
        
        //Debugging output
        String msg = "column read flag = ";
        for (int i=0; i < readColumnFlag.length; i++) {
            if (readColumnFlag[i] == true)
                msg += "true";
            else
                msg += "false";
            if (i < (readColumnFlag.length-1))
                msg += ", ";
        }
        msg += "\n";
        logger.debug(msg);

        
        return readColumnFlag;
    }


	/**
	 *  Read and parse data portion of file.
	 */
	private void readData(Sheet worksheet, boolean columnLabelsPresent,
                          boolean[] readColumnFlag)
		throws IOException {

		//Determine the number of lines in the file
		rowCount = countNumberOfRows(worksheet);
        
		logger.debug("number of rows in file: " + rowCount);
		if (columnLabelsPresent) {
			rowCount--;
		}
        
		//Process each line in the file
       if (rowCount == 0) {
            columnType = new int[columnCount];
            readColumnFlag = new boolean[columnCount];
            for (int col =0; col<readColumnFlag.length; col++) {
                readColumnFlag[col] = true;
                columnType[col] = STRING;
                columnData.add(new String[rowCount]);
            }
        }
       
       int startRow=0;
       if(columnLabelsPresent)
           startRow=1;
          
        for(int rowNumber=startRow;rowNumber<=rowCount;++rowNumber){

			int tokenCount = countNumberOfColumns(worksheet);

			//columnCount will be 0 when column titles are not present
			if (columnCount == 0)
				columnCount = tokenCount;

			//Check that there are the right number of columns
			if (tokenCount < columnCount) {
				throw new RuntimeException(tokenCount + " columns found on line " + 
						rowNumber + ", should be at least " + columnCount + " in worksheet "+worksheet);
			}

			//Process the first line separately to set-up the column type data
			//structures
            
			if (readColumnFlag == null) {
				readColumnFlag = new boolean[columnCount];
				for (int col =0; col<readColumnFlag.length; col++) {
					readColumnFlag[col] = true;
				}
			}
			if (rowNumber == startRow) {
				columnType = new int[columnCount];

                int[] types = determineColumnTypes(worksheet,rowNumber); 

				//Loop through the columns on the first line and determine the type
				//of each column by trying to parse it
				//c is the actual column number of the column being read in the file
				//c2 is the column number in the data set
				int c2 = -1;
				for (int c=0; c < tokenCount; c++) {
					if (readColumnFlag[c] == false)  //skip columns that should not be read
						continue;
					c2++;
                    
					columnType[c2]=types[c];
                    if (columnType[c2]== NUMBER) {
                        columnData.add(new float[rowCount]);
                    } else columnData.add(new String[rowCount]);
				}
			}
            
			//Process each field on the current line
			//c is the actual column number of the column being read in the file
			//c2 is the column number in the data set
			int c2 = -1;
			for (int c=0; c < tokenCount; c++) {
				Cell cell = worksheet.getCell(c,rowNumber);
                String token = cell.getContents();
                token = token.replaceAll("[,]","");

				if (readColumnFlag[c] == false)  //skip columns that should not be read
					continue;
				c2++;
                
				switch(columnType[c2]) {
				case STRING:
					//Remove " character from string if present
					if (token.startsWith("\"")) {
						token = token.substring(1);
					}
					if (token.endsWith("\"")) {
						token = token.substring(0, token.length());
					}
					String[] s = (String[]) columnData.get(c2);
					s[rowNumber-1] = token;  
					break;
				case NUMBER:
					float[] f = (float[]) columnData.get(c2);
                    if (cell.getType() == CellType.NUMBER) {
                        f[rowNumber-1] = (float) ((NumberCell) cell).getValue();
                    } else if (cell.getType() == CellType.NUMBER_FORMULA) {
                        f[rowNumber-1] = (float) ((NumberFormulaCell) cell).getValue();
                    } else {
                        logger.warn("Getting a float value from a non-number format cell in "+worksheet.getName()+" row:"+(rowNumber-1)+" col:"+(c2+1));;
                        try {
                            f[rowNumber-1] = Float.parseFloat(token);
                        } catch ( NumberFormatException e) {
                            String msg = "Can't parse "+token+" from Excel file worksheet "+worksheet.getName() +" row:"+(rowNumber+1)+" col:"+(c2+1);
                            logger.fatal(msg);
                            throw new RuntimeException(msg, e);
                        }
                    }
					break;
				default:
					throw new RuntimeException("unknown column data type: " + columnType[c2] +
							" for row number " + rowNumber);
				}
			}
		}
        }

    
	/**
	 * Read and parse data portion of file where the caller has passed in a
     * String[] with formats of each field (STRING or NUMBER).
	 */
	private void readData(Sheet worksheet, boolean columnLabelsPresent,
                          boolean[] readColumnFlag, String[] columnFormats)
		 {

		//Determine the number of lines in the file
		rowCount = countNumberOfRows(worksheet);
        
		logger.debug("number of lines in file: " + rowCount);
		if (columnLabelsPresent) {
			rowCount--;
		}
        
		//Process each line in the file
        if (rowCount == 0) {
            columnType = new int[columnCount];
            
            //Loop through the columns and set the type of each column from the array of types sent in
            int c2 = -1;
            for (int c=0; c < columnCount; c++) {
                if (readColumnFlag[c] == false)  //skip columns that should not be read
                    continue;
                c2++;
                
                if ( columnFormats[c].equals("NUMBER") ) {                 
                    columnType[c2] = NUMBER; 
                    columnData.add(new float[rowCount]);
                } 
                else {
                    columnType[c2] = STRING; 
                    columnData.add(new String[rowCount]);
                }
            }
        }
        
        int startRow=0;
        if(columnLabelsPresent)
            startRow=1;
           
         for(int rowNumber=startRow;rowNumber<rowCount;++rowNumber){


			int tokenCount = countNumberOfColumns(worksheet);

			//columnCount will be 0 when column titles are not present
			if (columnCount == 0)
				columnCount = tokenCount;

			//Check that there are the right number of columns
			if (tokenCount < columnCount) {
				throw new RuntimeException(tokenCount + " columns found on line " + 
						rowNumber + ", should be at least " + columnCount);
			}

			//Process the first line separately to set-up the column type data
			//structures
            
			if (readColumnFlag == null) {
				readColumnFlag = new boolean[columnCount];
				for (int col =0; col<readColumnFlag.length; col++) {
					readColumnFlag[col] = true;
				}
			}
			if (rowNumber == startRow) {
				columnType = new int[columnCount];
                
				//Loop through the columns and set the type of each column from the array of types sent in
				int c2 = -1;
				for (int c=0; c < columnCount; c++) {
					if (readColumnFlag[c] == false)  //skip columns that should not be read
						continue;
					c2++;
					
					if ( columnFormats[c].equals("NUMBER") ) {                 
						columnType[c2] = NUMBER; 
						columnData.add(new float[rowCount]);
					} 
					else {
						columnType[c2] = STRING; 
						columnData.add(new String[rowCount]);
					}
				}
			}
            
			//Process each field on the current line
			//c is the actual column number of the column being read in the file
			//c2 is the column number in the data set
			int c2 = -1;
			for (int c=0; c < tokenCount; c++) {

                Cell cell = worksheet.getCell(c,rowNumber);
                String token = cell.getContents();
                token = token.replaceAll("[,]","");

				if (readColumnFlag[c] == false)  //skip columns that should not be read
					continue;
				c2++;
                
				switch(columnType[c2]) {
				case STRING:
					//Remove " character from string if present
					if (token.startsWith("\"")) {
						token = token.substring(1);
					}
					if (token.endsWith("\"")) {
						token = token.substring(0, token.length());
					}
					String[] s = (String[]) columnData.get(c2);
					s[rowNumber] = token;  
					break;
				case NUMBER:
					float[] f = (float[]) columnData.get(c2);
					if (cell.getType() == CellType.NUMBER) {
					    f[rowNumber] = (float) ((NumberCell) cell).getValue();
					} else if (cell.getType() == CellType.NUMBER_FORMULA) {
					    f[rowNumber] = (float) ((NumberFormulaCell) cell).getValue();
					} else {
					    logger.warn("Getting a float value from a non-number format cell in "+worksheet.getName());
                        try {
                            f[rowNumber] = Float.parseFloat(token);
                        } catch ( NumberFormatException e) {
                            logger.fatal("Can't parse "+token+" from Excel file worksheet "+worksheet.getName());
                        }
					}
					break;
				default:
					throw new RuntimeException("unknown column data type: " + columnType[c2] +
							" for row number " + rowNumber);
				}
			}
		}
	}

    
    /**
     * Helper method to find the number of rows in a worksheet.
     * 
     * @param sheet  The worksheet.
     * @return total number of rows.
     * 
     */
    private int countNumberOfRows(Sheet sheet)  {
        
        int rows=0;
        //compute the number of zones
        try {
            do{
                //get the row
                Cell cell = sheet.getCell(0,rows);
                String value = cell.getContents();
                
                if(value.length()==0)
                    break;
                
                 ++rows;
                
            }while(true);
        } catch (ArrayIndexOutOfBoundsException e) {
            // ran out of rows...
        }
        return rows;
    }
    /**
     * Helper method to find the number of columns in the worksheet.
     * 
     * @param sheet The worksheet.
     * @return total number of columns in the sheet
     * 
     */
    private int countNumberOfColumns(Sheet sheet)  {
        
        return sheet.getColumns();
       
   }
    private TableDataSet makeTableDataSet() {

        TableDataSet table = new TableDataSet();

        //Column labels were not present in the file
        if (columnLabels.size() == 0) {
            for (int i=0; i < columnCount; i++) {
                columnLabels.add("column_"+(i+1));
            }
        }
        
        for (int i=0; i < columnCount; i++) {
            table.appendColumn(columnData.get(i), (String) columnLabels.get(i));
        }

        return table;
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#readTable(java.lang.String)
     */
    public TableDataSet readTable(String tableName) throws IOException {
        if (workbookFile==null) {
            // try to read a .csv file
            File fileName = new File (getMyDirectory().getPath() + File.separator + tableName + ".csv");
            TableDataSet me= readFile(fileName);
            me.setName(tableName);
            return me;
        } else {
            TableDataSet table = readFile(workbookFile, tableName, true);
            if (table!=null) table.setName(tableName);
            return table;
            
        }
        
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#close()
     */
    public void close() {
    }

  
    /**
     * Parse fields in an excel worksheet row using the RegEx class (on the String method)
     * given a pattern string.
     *
     * @param worksheet The worksheet
     * @param row The row (0-init)
     * @return int array of token values
     */
    private int[] determineColumnTypes(Sheet worksheet, int row) {

        int columns = countNumberOfColumns(worksheet);
        int[] columnTypes = new int[columns];

        Cell cell = null;
        for(int i=0; i < columns; i++) {
            
            cell = worksheet.getCell(i,row);
            String token = cell.getContents();
            //If first character is a " then trim it
            if (token.startsWith("\"")) {
                columnTypes[i]=STRING;
            } else {
                try {
                    Float.parseFloat(token);
                    columnTypes[i] = NUMBER; 
                } 
                catch (NumberFormatException e) {
                    columnTypes[i] = STRING; 
                }
            }
        }

        return columnTypes;
    }

    public File getWorkbookFile() {
        return workbookFile;
    }

    public void setWorkbookFile(File workbookFile) {
        this.workbookFile = workbookFile;
    }
    
}
