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

import org.apache.log4j.Logger;

import java.io.*;
import java.net.URL;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;


/**
 * Creates a TableData class from a CSV file. The default delimiter character is a comma.
 *
 * @author   Tim Heier
 * @version  1.0, 2/07/2004
 *
 */
public class CSVFileReader extends TableDataFileReader implements  DataTypes {
    
    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    
    //Can be set by caller
    private char delimiter = ',';

    //Pattern composed of regular expression used to parse CSV fields
    private String pattern = ",(?=(?:[^\"]*\"[^\"]*\")*(?![^\"]*\"))";
    private Pattern regexPattern = Pattern.compile(pattern);

    //These attributes are initialized on each call to readFile()
    private int columnCount;
    private int rowCount;
    private List columnData;
    private ArrayList columnLabels;
    private int[] columnType;

    
    public CSVFileReader () {
    }


    /**
     * Sets the delimiters used by the StringTokenizer when reading column values.
     * 
     * @param delimiter character separating fields in CSV file, default is a comma
     */
    public void setDelimiter(char delimiter) {
        this.delimiter = delimiter;

        //Update the pattern string with the new delimiter
        pattern = Character.toString(delimiter) + pattern.substring(1);
        regexPattern = Pattern.compile(pattern);
    }
    
    
    /**
     * 
     * @return the delimiter in use
     */
    public char getDelimiter() {
        return delimiter;
    }
    
    /**
     *
     * @return the pattern string used to parse CSV fields
     */
    public String getPattern() {
        return pattern;
    }

    /**
     *
     * @param pattern new pattern string to be used when parsing CSV fields
     */
    public void setPattern(String pattern) {
        this.pattern = pattern;
        regexPattern = Pattern.compile(pattern);
    }


    public TableDataSet readFile(File file) throws IOException {
        return readFile(file, true);
    }

    public TableDataSet readFile(String urlString) throws IOException {
        return readFile(urlString, true);
    }

    
    /**
     * Convenience method to load a CSV file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnLabelsPresent  determines whether first line is treated
     *                              as column titles
     * @throws IOException
     * 
     */
    public TableDataSet readFile(File file, boolean columnLabelsPresent) throws IOException {
        return readFile(file, columnLabelsPresent, null);
    }

    public TableDataSet readFile(String urlString, boolean columnLabelsPresent) throws IOException {
        return readFile(urlString, columnLabelsPresent, null);
    }




    /**
     * Convenience method to load a CSV file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnsToRead list of column labels that should be read - all other
     *                      columns will be dropped from the table data set 
     * @throws IOException
     * 
     */
    public TableDataSet readFile(File file, String[] columnsToRead) throws IOException {
        return readFile(file, true, columnsToRead);
    }


    /**
     * Main method which loads a CSV file into a table data class.
     * 
     * @param file  name of file to read
     * @param columnLabelsPresent  determines whether first line is treated
     *                              as column titles
     * @param columnsToRead list of column labels that should be read - all other
     *                      columns will be dropped from the table data set 
     * @throws IOException
     * 
     */
	public TableDataSet readFile(File file, boolean columnLabelsPresent, String[] columnsToRead) throws IOException {
        
		if ((columnsToRead != null) && (columnLabelsPresent == false)) {
			throw new RuntimeException("Column lables provided as filter but there are no column labels in CSV file");
		}
        
		//Initialize class attributes
		columnCount = 0;
		rowCount = 0;
		columnData = new ArrayList();
		columnLabels = new ArrayList();
		columnType = null;
        
		BufferedReader inStream = openFile(file);
        
		boolean[] readColumnFlag = null;
        
		if (columnLabelsPresent) {
			readColumnFlag = readColumnLabels(inStream, columnsToRead);
            boolean readAColumn=false;
            for (boolean b: readColumnFlag) {
                readAColumn = readAColumn || b;
            }
            if (!readAColumn) {
                logger.fatal("No columns read when reading file "+file);
                throw new RuntimeException("No columns read when reading file "+file);
            }
		}
		readData(file, inStream, columnLabelsPresent, readColumnFlag);
        
		TableDataSet tds = makeTableDataSet();
		tds.setName(file.toString());
		return tds;
	}

    /**
     * Main method which loads a CSV file into a table data class.
     *
     * @param urlString  http address of file to read
     * @param columnLabelsPresent  determines whether first line is treated
     *                              as column titles
     * @param columnsToRead list of column labels that should be read - all other
     *                      columns will be dropped from the table data set
     * @throws IOException
     *
     */
	public TableDataSet readFile(String urlString, boolean columnLabelsPresent, String[] columnsToRead) throws IOException {

		if ((columnsToRead != null) && (columnLabelsPresent == false)) {
			throw new RuntimeException("Column lables provided as filter but there are no column labels in CSV file");
		}

		//Initialize class attributes
		columnCount = 0;
		rowCount = 0;
		columnData = new ArrayList();
		columnLabels = new ArrayList();
		columnType = null;

        URL url;
        URLConnection urlConn;
        DataInputStream dis;

        url = new URL(urlString);
        urlConn = url.openConnection();
        dis = new DataInputStream(urlConn.getInputStream());
        BufferedReader inStream = new BufferedReader(new InputStreamReader(dis));


		boolean[] readColumnFlag = null;

		if (columnLabelsPresent) {
			readColumnFlag = readColumnLabels(inStream, columnsToRead);
            boolean readAColumn=false;
            for (boolean b: readColumnFlag) {
                readAColumn = readAColumn || b;
            }
            if (!readAColumn) {
                logger.fatal("No columns read when reading file "+ urlString);
                throw new RuntimeException("No columns read when reading file "+ urlString);
            }
		}
		readData(urlString, inStream, columnLabelsPresent, readColumnFlag);

		TableDataSet tds = makeTableDataSet();
		tds.setName(urlString.substring((urlString.lastIndexOf("/"))+1, urlString.length()));
        System.out.println("Table Name is: " + tds.getName());
        return tds;
	}


    /*
	 * Read the csv file with a String[] of specified column formats (NUMBER or STRING),
	 * where the format is specified for all columns, all columns are read,
	 * and column headings must be present on the first line.
	 */
	public TableDataSet readFileWithFormats(File file, String[] columnFormats) throws IOException {
        
		boolean columnLabelsPresent = true;
		String[] columnsToRead = null;
		
		if ((columnsToRead != null) && (columnLabelsPresent == false)) {
			throw new RuntimeException("Column lables provided as filter but there are no column labels in CSV file");
		}
        
		//Initialize class attributes
		columnCount = 0;
		rowCount = 0;
		columnData = new ArrayList();
		columnLabels = new ArrayList();
		columnType = null;
        
		BufferedReader inStream = openFile(file);
        
		boolean[] readColumnFlag = null;
        
		if (columnLabelsPresent) {
			readColumnFlag = readColumnLabels(inStream, columnsToRead);
		}
		readData(file, inStream, columnLabelsPresent, readColumnFlag, columnFormats);
        
		TableDataSet tds = makeTableDataSet();
		tds.setName(file.toString());
		return tds;
	}
        
        
    private BufferedReader openFile(File file) throws IOException {
        logger.debug("Opening file: "+file);
        
        BufferedReader inStream = null;
        try {
            inStream = new BufferedReader( new FileReader(file) );
        }
        catch (IOException e) {
            throw e;
        }
        
        return inStream;
    }


    /**
     * Read and parse the column titles from the first line of file.
     */
    private boolean[] readColumnLabels(BufferedReader inStream, String[] columnsToRead)
            throws IOException {
        //Read the first line
        String line = inStream.readLine();

        //Test for an empty file
        if (line == null) {
            throw new IOException("Error: file looks like it's empty");
        }

        //Tokenize the first line
        String[] tokens = parseTokens(line);
        int count = tokens.length;

        boolean[] readColumnFlag = new boolean[count];
        
        //Initialize the readColumnFlag to false if the caller has supplied a 
        //list of columns. It will be turned to true basedon a comparison of the
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
            String column_name = tokens[i];
            
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
	private void readData(File file, BufferedReader inStream, boolean columnLabelsPresent,
                          boolean[] readColumnFlag)
		throws IOException {

		int rowNumber = 0;

		//Determine the number of lines in the file
		rowCount = findNumberOfLinesInFile(file);
        
		logger.debug("number of lines in file: " + rowCount);
		if (columnLabelsPresent) {
			rowCount--;
		}
        
		//Process each line in the file
		String line;
        if (rowCount == 0) {
            columnType = new int[columnCount];
            readColumnFlag = new boolean[columnCount];
            for (int col =0; col<readColumnFlag.length; col++) {
                readColumnFlag[col] = true;
                columnType[col] = STRING;
                columnData.add(new String[rowCount]);
            }
        }
        
		while ((line = inStream.readLine()) != null) {

			String[] tokens = parseTokens(line);
			int tokenCount = tokens.length;

			//columnCount will be 0 when column titles are not present
			if (columnCount == 0)
				columnCount = tokenCount;

			//Check that there are the right number of columns
			if (tokenCount < columnCount) {
				throw new RuntimeException(tokenCount + " columns found on line " + 
						rowNumber + ", should be at least " + columnCount + " in file "+file);
			}

			//Process the first line separately to set-up the column type data
			//structures
            
			if (readColumnFlag == null) {
				readColumnFlag = new boolean[columnCount];
				for (int col =0; col<readColumnFlag.length; col++) {
					readColumnFlag[col] = true;
				}
			}
			if (rowNumber == 0) {
				columnType = new int[columnCount];

                int[] types = determineColumnTypes(line); 

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
				String token = tokens[c];

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
					f[rowNumber] = Float.parseFloat(token);
					break;
				default:
					throw new RuntimeException("unknown column data type: " + columnType[c2] +
							" for row number " + rowNumber);
				}
			}
			rowNumber++;
		}
		inStream.close();
	}

    /**
	 *  Read and parse data portion of file.
	 */
	private void readData(String urlString, BufferedReader inStream, boolean columnLabelsPresent,
                          boolean[] readColumnFlag)
		throws IOException {

		int rowNumber = 0;

		//Determine the number of lines in the file
		rowCount = findNumberOfLinesInFile(urlString);

		logger.debug("number of lines in file: " + rowCount);
		if (columnLabelsPresent) {
			rowCount--;
		}

		//Process each line in the file
		String line;
        if (rowCount == 0) {
            columnType = new int[columnCount];
            readColumnFlag = new boolean[columnCount];
            for (int col =0; col<readColumnFlag.length; col++) {
                readColumnFlag[col] = true;
                columnType[col] = STRING;
                columnData.add(new String[rowCount]);
            }
        }

		while ((line = inStream.readLine()) != null) {

			String[] tokens = parseTokens(line);
			int tokenCount = tokens.length;

			//columnCount will be 0 when column titles are not present
			if (columnCount == 0)
				columnCount = tokenCount;

			//Check that there are the right number of columns
			if (tokenCount < columnCount) {
				throw new RuntimeException(tokenCount + " columns found on line " +
						rowNumber + ", should be at least " + columnCount + " in file "+ urlString);
			}

			//Process the first line separately to set-up the column type data
			//structures

			if (readColumnFlag == null) {
				readColumnFlag = new boolean[columnCount];
				for (int col =0; col<readColumnFlag.length; col++) {
					readColumnFlag[col] = true;
				}
			}
			if (rowNumber == 0) {
				columnType = new int[columnCount];

                int[] types = determineColumnTypes(line);

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
				String token = tokens[c];

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
					f[rowNumber] = Float.parseFloat(token);
					break;
				default:
					throw new RuntimeException("unknown column data type: " + columnType[c2] +
							" for row number " + rowNumber);
				}
			}
			rowNumber++;
		}
		inStream.close();
	}


    /**
	 * Read and parse data portion of file where the caller has passed in a
     * String[] with formats of each field (STRING or NUMBER).
	 */
	private void readData(File file, BufferedReader inStream, boolean columnLabelsPresent,
                          boolean[] readColumnFlag, String[] columnFormats)
		throws IOException {

		int rowNumber = 0;

		//Determine the number of lines in the file
		rowCount = findNumberOfLinesInFile(file);
        
		logger.debug("number of lines in file: " + rowCount);
		if (columnLabelsPresent) {
			rowCount--;
		}
        
		//Process each line in the file
		String line;
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
        
        
		while ((line = inStream.readLine()) != null) {

            String[] tokens = parseTokens(line);
			int tokenCount = tokens.length;

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
			if (rowNumber == 0) {
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
				String token = tokens[c];

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
					f[rowNumber] = Float.parseFloat(token);
					break;
				default:
					throw new RuntimeException("unknown column data type: " + columnType[c2] +
							" for row number " + rowNumber);
				}
			}
			rowNumber++;
		}
		inStream.close();
	}

    
    /**
     * Helper method to find the number of lines in a text file.
     * 
     * @return total number of lines in file
     * 
     */
    private int findNumberOfLinesInFile(File file) throws IOException {
        int numberOfRows = 0;
        
        try {
            BufferedReader stream = new BufferedReader( new FileReader(file) );
            while (stream.readLine() != null) {
                numberOfRows++;
            }
            stream.close();
        }
        catch (IOException e) {
            throw e;
        }
        
        return numberOfRows;
    }

    /**
     * Helper method to find the number of lines in a text file.
     *
     * @return total number of lines in file
     *
     */
    private int findNumberOfLinesInFile(String urlString) throws IOException {
        int numberOfRows = 0;

        try {
            URL url = new URL(urlString);
            URLConnection urlConn = url.openConnection();
            DataInputStream dis = new DataInputStream(urlConn.getInputStream());
            BufferedReader stream = new BufferedReader(new InputStreamReader(dis));
            while (stream.readLine() != null) {
                numberOfRows++;
            }
            stream.close();
        }
        catch (IOException e) {
            throw e;
        }

        return numberOfRows;
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
        File fileName = new File (getMyDirectory().getPath() + File.separator + tableName + ".csv");
        TableDataSet me= readFile(fileName);
        me.setName(tableName);
        return me;
        
    }


    /* (non-Javadoc)
     * @see com.pb.common.datafile.TableDataReader#close()
     */
    public void close() {
    }

    /**
     * Parse fields in a CSV file using the RegEx class (on the String method)
     * given a pattern string.
     *
     * @param line from CSV file
     * @return String array of token values
     */
    private String[] parseTokens(String line) {

        String[] tokens = regexPattern.split(line);

        for(int i=0; i < tokens.length; i++) {
            //If first character is a " then trim it
            if (tokens[i].startsWith("\"")) {
                tokens[i] = tokens[i].substring(1);
            }
            //If last character is a " then trim it
            if (tokens[i].endsWith("\"")) {
                tokens[i] = tokens[i].substring(0, (tokens[i].length()-1) );
            }
            //Replace escaped " characters with single ", ie. "" to "
            tokens[i] = tokens[i].replaceAll("\"\"", "\"");
        }

        return tokens;
    }

    /**
     * Parse fields in a CSV file using the RegEx class (on the String method)
     * given a pattern string.
     *
     * @param line from CSV file
     * @return String array of token values
     */
    private int[] determineColumnTypes(String line) {

        String[] tokens = regexPattern.split(line);
        int[] columnTypes = new int[tokens.length];

        for(int i=0; i < tokens.length; i++) {
            //If first character is a " then trim it
            if (tokens[i].startsWith("\"")) {
                columnTypes[i]=STRING;
            } else {
                try {
                    Float.parseFloat(tokens[i]);
                    columnTypes[i] = NUMBER; 
                } 
                catch (NumberFormatException e) {
                    columnTypes[i] = STRING; 
                }
            }
        }

        return columnTypes;
    }
    
}
