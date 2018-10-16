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

import com.pb.common.util.IndexSort;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.text.DecimalFormat;
import java.util.*;


/**
 * Represents a table of data read from a CSV file.
 *
 * @version  1.0, 2/08/03
 * @author   Tim Heier
 *
 */
public class TableDataSet implements DataTypes, Serializable {

    protected static transient Logger logger = Logger.getLogger("com.pb.common.datafile");
    private boolean columnLabelsPresent = false;
    private boolean dirty = false;
    private ArrayList columnLabels = new ArrayList();
    private ArrayList columnData = new ArrayList();
    private int[] columnIndex = null;
    private int[] columnType = null;
    
    // the index columns work with the TableDataSetIndex and TableDataSetIndexedValue
    // if an index column changes, then any TableDataSetIndex that uses that column has to regenerate
    // its index.
    private boolean[] indexColumns = null;
    
    private int nRows;
    private int nCols;
    private DecimalFormat valueFormat = new DecimalFormat("#.#");
    
    public interface ChangeListener {
        void indexValuesChanged();
    }
    
    private Set changeListeners = null;
    private String name;
    
    public void addChangeListener(ChangeListener letMeKnow) {
        if (changeListeners==null) {
            changeListeners = new HashSet();
        }
        changeListeners.add(letMeKnow);
    }
    

    void fireIndexValuesChanged() {
        if (changeListeners != null) {
            Iterator it = changeListeners.iterator();
            while (it.hasNext())  {
                ((ChangeListener) it.next()).indexValuesChanged();
            }
        }
    }

    /**
     * Creates an empty table data set. Should populate with calls to appendColumn()
     * method.
     *
     */
    public TableDataSet() {
    }

    public boolean isColumnLabelsPresent() {
        return columnLabelsPresent;
    }

    public int getRowCount() {
        return nRows;
    }

    public int getColumnCount() {
        return nCols;
    }

    public String[] getColumnLabels() {
        String[] a = new String[1];

        return (String[]) columnLabels.toArray(a);
    }

    public int[] getColumnType() {
        return columnType;
    }

    public void setColumnLabels(String[] titles) {
        columnLabels = new ArrayList(titles.length);

        for (int i = 0; i < titles.length; ++i) {
            columnLabels.add(titles[i]);
        }

        columnLabelsPresent = true;
        
        fireIndexValuesChanged();
        setDirty(true);
        
    }

    /**
    * Return the sum of the column entries given a column postion.
    *
    * @return  The index of the column
    *
    */
    public float getColumnTotal(int column) {
        checkColumnNumber(column, NUMBER);

        //Data is 0 based so subtract 1 from what the user supplies
        column = column - 1;

        float[] f = (float[]) columnData.get(column);

        float total = 0.0f;

        for (int i = 0; i < f.length; i++) {
            total += f[i];
        }

        return total;
    }

	/**
	 * Returns a column of data as an array of int. Note loss of precision could
	 * occur. Convenience method, data is stored in the returned array starting
	 * at position 0.
	 *
	 * @param columnName name of column to retrieve
	 *
	 * @return an int array of values for the requested column.
	 */
	public int[] getColumnAsInt( String columnName ) {
		return getColumnAsInt( getColumnPosition(columnName), 0 );
	}

	/**
	 * Returns a column of data as an array of int given the column name.
	 * Note loss of precision could occur. Convenience method, data is stored
	 * in the returned array starting at position 0.
	 *
	 * @param column column number to retrieve (1-based)
	 *
	 * @return an int array of values for the requested column.
	 */
	public int[] getColumnAsInt(int column) {
		return getColumnAsInt(column, 0);
	}

    /**
     * Returns a column of data as an array of int. Note loss of precision could
     * occur.
     *
     * @param column column number to retrieve (1-based)
     * @param startPosition starting position of the data in returned array
     *
     * @return an int array of values for the requested column.
     */
    public int[] getColumnAsInt(int column, int startPosition) {
        checkColumnNumber(column, NUMBER);

        //Data is 0 based so subtract 1 from what the user supplied
        column = column - 1;

        float[] f = (float[]) columnData.get(column);
        int[] values = new int[nRows + startPosition];

        for (int i = 0; i < nRows; ++i)
            values[i + startPosition] = (int) f[i];

        return values;
    }
    


    /**
     * Returns a column of data as an array of long. Note loss of precision could
     * occur if the column is stored as a float.
     *
     * @param column column number to retrieve (1-based)
     *
     * @return a long array of values for the requested column.
     */
    public long[] getColumnAsLong(int column) {
        column = column - 1;

        int startPosition = 0; //position to start in array

        long[] values = new long[nRows + startPosition];

        if (columnType[column] == NUMBER) {
    
            //Data is 0 based so subtract 1 from what the user supplied
            float[] f = (float[]) columnData.get(column);
    
            for (int i = 0; i < nRows; ++i)
                values[i + startPosition] = (int) f[i];
        } else if (columnType[column] == STRING){
            
            String[] s = (String[]) columnData.get(column);
            
            for (int i=0;i<nRows;i++) {
                values[i+startPosition] = Long.valueOf(s[i]).longValue();
            }
        } else {
            throw new RuntimeException("Can't convert column "+columnLabels.get(column)+" to long");
        }
        return values;
    
    }


	/**
	 * Returns a column of data as a float array.
	 *
	 * @param column column number to retrieve (1-based)
	 *
	 * @return an int array of values for the requested column.
	 */
	public float[] getColumnAsFloat(int column) {
		checkColumnNumber(column, NUMBER);

		//Data is 0 based so subtract 1 from what the user supplied
		column = column - 1;

		int startPosition = 0; //position to start in array

		float[] f = (float[]) columnData.get(column);
		float[] values = new float[nRows + startPosition];

		for (int i = 0; i < nRows; ++i)
			values[i + startPosition] = f[i];

		return values;
	}

	/**
	 * Returns a column of data as a float array given the columnName.
	 *
	 * @param columnName name of column to retrieve
	 *
	 * @return an int array of values for the requested column.
	 */
	public float[] getColumnAsFloat( String columnName ) {
	    
		int columnPosition = getColumnPosition( columnName );
		return getColumnAsFloat ( columnPosition );
		
	}

	/**
	 * Returns a column of data as a double array.
	 *
	 * @param column column number to retrieve (1-based)
	 *
	 * @return an int array of values for the requested column.
	 */
	public double[] getColumnAsDouble(int column) {
		checkColumnNumber(column, NUMBER);

		//Data is 0 based so subtract 1 from what the user supplied
		column = column - 1;

		int startPosition = 0; //position to start in array

		float[] f = (float[]) columnData.get(column);
		double[] values = new double[nRows + startPosition];

		for (int i = 0; i < nRows; ++i)
			values[i + startPosition] = f[i];

		return values;
	}

	/**
	 * Returns a column of data as a double array given the columnName.
	 *
	 * @param columnName name of column to retrieve
	 *
	 * @return an int array of values for the requested column.
	 */
    public double[] getColumnAsDouble( String columnName ) {
        
        int columnPosition = getColumnPosition( columnName );
        return getColumnAsDouble ( columnPosition );
        
    }
    
    
    
    /**
     * The use of this method assumes that the reader that populated this TableDataSet saved column data as double[].
     * @param columnName
     * @return
     */
    public double[] getColumnAsDoubleFromDouble( String columnName ) {
        
        int columnPosition = getColumnPosition( columnName );
        return getColumnAsDoubleFromDouble ( columnPosition );
        
    }
    public double[] getColumnAsDoubleFromDouble(int column) {
        checkColumnNumber(column, DOUBLE);

        //Data is 0 based so subtract 1 from what the user supplied
        column = column - 1;

        return (double[])columnData.get(column);
    }

    
    
	/**
	 * Returns a column of data as a boolean array.
	 *
	 * @param column column number to retrieve (1-based)
	 *
	 * @return an int array of values for the requested column.
	 */
	public boolean[] getColumnAsBoolean(int column) {
		checkColumnNumber(column, STRING);

		//Data is 0 based so subtract 1 from what the user supplied
		column = column - 1;

		int startPosition = 0; //position to start in array

		String[] f = (String[]) columnData.get(column);
		boolean[] values = new boolean[nRows + startPosition];

		for (int i = 0; i < nRows; ++i)
			values[i + startPosition] = f[i].equalsIgnoreCase("true");

		return values;
	}

	/**
	 * Returns a column of data as a boolean array given the columnName.
	 *
	 * @param columnName name of column to retrieve
	 *
	 * @return an int array of values for the requested column.
	 */
	public boolean[] getColumnAsBoolean( String columnName ) {
	    
		int columnPosition = getColumnPosition( columnName );
		return getColumnAsBoolean ( columnPosition );
		
	}

    /**
     * Returns a column of data as an array of Strings.
     *
     * @param column column number to retrieve (1-based)
     *
     * @return a String array of values for the requested column.
     * @throws  RuntimeException when the column type is not a STRING
     */
    public String[] getColumnAsString(int column) {
        checkColumnNumber(column, STRING);

        //Data is 0 based so subtract 1 from what the user supplied
        column = column - 1;

        int startPosition = 0; //position to start in array

        String[] s = (String[]) columnData.get(column);
        String[] values = new String[s.length + startPosition];

        for (int i = 0; i < s.length; ++i)
            values[i + startPosition] = s[i];

        return values;
    }

	/**
	 * Returns a column of data as a String array given the columnName.
	 *
	 * @param columnName name of column to retrieve
	 *
	 * @return an int array of values for the requested column.
	 */
	public String[] getColumnAsString( String columnName ) {
	    
		int columnPosition = getColumnPosition( columnName );
		return getColumnAsString ( columnPosition );
		
	}

    /**
     * A package scoped method.
     *
     * @return columnData
     */
    ArrayList getColumnData() {
        return columnData;
    }

    /**
     * Checks if a column number is in range and that type is correct.
     *
     * @param column
     * @param type column type to compare against
     */
    private void checkColumnNumber(int column, int type) {
        //Data is 0 based so subtract 1 from what the user supplied
        column = column - 1;

        if ((column < 0) || (column > nCols)) {
            String msg = "Column number out of range: " + column;
            msg += (", number of columns: " + nCols);

            throw new RuntimeException(msg);
        }

        if (columnType[column] != type) {
            throw new RuntimeException("column " + column + " is type " +
                columnType[column] + " not type " + type);
        }
    }

    /**
    * Return the name of the column given a postion. Column numbers are 1-based.
    *
    * @return  The name of the column or an empty string if the requested
    *          field is out of bounds.
    */
    public String getColumnLabel(int column) {
        //Data is 0 based so subtract 1 from what the user supplies
        column = column - 1;

        if ((columnLabels != null) && (column >= 0) &&
                (column < columnLabels.size())) {
            return (String) columnLabels.get(column);
        } else {
            return "";
        }
    }

    /**
    * Return the postion of a column given the name.  Column numbers are 1-based.
    *
    * @return  -1 if the requested column name is not found.
    *
    */
    public int getColumnPosition(String columnName) {
        int position = -1;

        for (int col = 0; col < columnLabels.size(); col++) {
            String currentColumn = (String) columnLabels.get(col);
            if (currentColumn.equalsIgnoreCase(columnName)) {
                position = col + 1;
                break;
            }
        }

        return position;
    }
    
    public int checkColumnPosition(String columnName) throws RuntimeException {
        int position = getColumnPosition(columnName);
        if (position <0) throw new RuntimeException("Column "+columnName+" does not exist in TableDataSet "+getName());
        return position;
    }
    
    /**
     * Indicates whether or not the table constains the specified column. 
     * 
     * @param columnName Name of the column to check. 
     * @return boolean indicating if the column is present.  
     */
    public boolean containsColumn(String columnName) {
        int position = getColumnPosition(columnName); 
        if (position>=0) return true; 
        else return false;         
    }

    /**
     * Return the values in a specified row as a float[]
     *
     * @param row  row number to retrieve, values are 0-based
     *
     * @throws RuntimeException when one of the columns is of type STRING
     *
     */
    public float[] getRowValues(int row) {
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;

        int startPosition = 0; //position to start in array

        float[] rowValues = new float[nCols + startPosition];

        for (int c = 0; c < nCols; c++) {
            if (columnType[c] == STRING) {
                throw new RuntimeException("column " + c + 1 +
                    " is of type STRING");
            }

            float[] f = (float[]) columnData.get(c);

            rowValues[c + startPosition] = f[row];
        }

        return rowValues;
    }

    /**
     * Return a values from a specified row using the indexed column.
     *
     * @param row indexed row number
     */
    public float[] getIndexedRowValuesAt(int row) {
        if (columnIndex == null) {
            throw new RuntimeException("No index defined.");
        }

        row = columnIndex[row] + 1; // getRowValues will subtract 1

        return getRowValues(row);
    }

    /**
     * Return the row number from the index.
     *
     * @param index indexed row number
     * @return the row number associated with the index
     */
    public int getIndexedRowNumber(int index) {
        if (columnIndex == null) {
            throw new RuntimeException("No index defined.");
        }

        return columnIndex[index] + 1; // getRowValues will subtract 1
    }

    
    /**
     * Return the values in a specified row as a String[]
     *
     * @param row  row number to retrieve, values are 0-based
     *
     * @throws RuntimeException when one of the columns is of type STRING
     *
     */
    public String[] getRowValuesAsString(int row) {
        //TODO lookup based on indexed column
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;

        int startPosition = 0; //position to start in array

        String[] rowValues = new String[nCols + startPosition];

        for (int c = 0; c < nCols; c++) {
            switch (columnType[c]) {
            case STRING:
                String[] s = (String[]) columnData.get(c);
                rowValues[c + startPosition] = s[row];
                break;
            case NUMBER:
                float[] f = (float[]) columnData.get(c);
                rowValues[c + startPosition] = valueFormat.format(f[row]);
                break;
            }
        }

        return rowValues;
    }

    /**
     * Returns a copy of the values in the table as a float[][]
     */
    public float[][] getValues() {
        float[][] tableValues = new float[nRows][nCols];

        for (int c = 0; c < nCols; c++) {
            if (columnType[c] == STRING) {
                throw new RuntimeException("column " + c + 1 +
                    " is of type STRING");
            }

            float[] f = (float[]) columnData.get(c);

            for (int r = 0; r < nRows; r++) {
                tableValues[r][c] = f[r];
            }
        }

        return tableValues;
    }

    /**
     * Return a value from a specified row and column. For speed, the column
     * type is not checked. A RuntimeException will be thrown if the column is
     * of type NUMBER.
     *
     */
    public float getValueAt(int row, int column) {
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;
        column = column - 1;

        
        //TODO lookup based on indexed column
        float[] f = null;
        try {
            f = (float[]) columnData.get(column);
        } catch (ClassCastException e) {
            throw new RuntimeException("Column "+column+" in TableDataSet is not float values",e);
        }

        return f[row];
    }

    public float getValueAt(int row, String columnName) {
        int columnNumber = getColumnPosition(columnName);

        if (columnNumber <= 0) {
            logger.error("no column named " + columnName + " in TableDataSet");
            throw new RuntimeException("no column named " + columnName +
                " in TableDataSet");
        }

        return getValueAt(row, columnNumber);
    }

    /**
     * Return a value from a specified row and column. If the column type is
     * not STRING then the numberic value will be converted to string before
     * it is returned.
     *
     */
    public String getStringValueAt(int row, int column) {
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;
        column = column - 1;

        String value;

        if (columnType[column] == NUMBER) {
            float[] f = (float[]) columnData.get(column);
            value = valueFormat.format(f[row]);
        } else {
            String[] s = (String[]) columnData.get(column);
            value = s[row];
        }

        return value;
    }

    /**
     * Return a value from a specified row and column. 
     *
     */
    public boolean getBooleanValueAt(int row, int column) {
        String boolString = getStringValueAt(row,column);
        if (boolString == null) throw new RuntimeException("Boolean value in TableDataSet "+name+" is blank (null)");
        if (use1sAnd0sForTrueFalse) {
        	if (boolString.equals("0")) return false;
        	if (boolString.equals("1")) return true;
        }
        if (boolString.equalsIgnoreCase("true")) return true;
        if (boolString.equalsIgnoreCase("false")) return false;
        throw new RuntimeException("Boolean value in table dataset "+name+" column "+ column+ " is neither true nor false, but "+boolString);
    }
    
    public boolean getBooleanValueAt(int row, String columnName) {
        return getBooleanValueAt(row,checkColumnPosition(columnName));
    }
    
    public void setBooleanValueAt(int row, String columnName, boolean value) {
        setBooleanValueAt(row,checkColumnPosition(columnName), value);
    }
    
    public void setBooleanValueAt(int row, int column, boolean value) {
        if (value) setStringValueAt(row,column,"true");
        else setStringValueAt(row,column,"false");
    }

    /**
     * Return a value from a specified row and column. For speed, the column
     * type is not checked. A RuntimeException will be thrown if the column is
     * of type STRING.
     *
     */
    public String getStringValueAt(int row, String columnName) {
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;

        int columnNumber = getColumnPosition(columnName);

        if (columnNumber <= 0) {
            logger.error("no column named " + columnName + " in TableDataSet");
            
            throw new RuntimeException("no column named " + columnName +
                " in TableDataSet");
        }

        //Call with 1-based row and column numbers
        return getStringValueAt(row + 1, columnNumber);
    }
    
    /**
     * Set at a value using the column name.
     */
    public void setValueAt(int row, String colName, float newValue) {
        int col = getColumnPosition(colName);
        setValueAt(row, col, newValue);
    }
    
	/**
	 * Return a value from a specified row and column. For speed, the column
	 * type is not checked. A RuntimeException will be thrown if the column is
	 * of type NUMBER.
	 *
	 */
	public void setValueAt(int row, int column, float newValue) {
		//Data is 0 based so subtract 1 from what the user supplies
		row = row - 1;
		column = column - 1;

		float[] f = (float[]) columnData.get(column);

		f[row] = newValue;
        
        // any TableDataSetIndex that uses this column will have to regenerate its index.
        if (indexColumns[column]==true) {
            fireIndexValuesChanged();
        }
        setDirty(true);
	}

	/**
	 * update the column specified with the int values specified.
	 *
	 */
	public void setColumnAsInt ( int column, int[] newValues ) {
		//Data is 0 based so subtract 1 from what the user supplies
		column = column - 1;

		float[] f = new float[newValues.length];
		for (int i=0; i < newValues.length; i++)
		    f[i] = (float)newValues[i];
		    
		columnData.set( column, f );
        if (indexColumns[column]==true) {
            fireIndexValuesChanged();
        }
        
		setDirty(true);
	}

	/**
	 * update the column specified with the float values specified.
	 *
	 */
	public void setColumnAsFloat ( int column, float[] newValues ) {
		//Data is 0 based so subtract 1 from what the user supplies
		column = column - 1;

		columnData.set( column, newValues );
        if (indexColumns[column]==true) {
            fireIndexValuesChanged();
        }
        
		setDirty(true);
	}

	/**
	 * update the column specified with the double values specified.
	 *
	 */
	public void setColumnAsDouble ( int column, double[] newValues ) {
		//Data is 0 based so subtract 1 from what the user supplies
		column = column - 1;

		float[] f = new float[newValues.length];
		for (int i=0; i < newValues.length; i++)
		    f[i] = (float)newValues[i];
		    
		columnData.set( column, f );
        if (indexColumns[column]==true) {
            fireIndexValuesChanged();
        }
        
		setDirty(true);
	}

    public void setIndexedValueAt(int row, String colName, float newValue) {
         if (columnIndex == null) {
            throw new RuntimeException("No index defined.");
        }
        row = columnIndex[row] + 1;

        int col = getColumnPosition(colName);
        setValueAt(row, col, newValue);
    }

    /**
     * Return a value from an indexed row and column. For speed, the column
     * type is not checked. A RuntimeException will be thrown if the column is
     * of type NUMBER.
     *
     */
    public void setIndexedValueAt(int row, int column, float newValue) {
        if (columnIndex == null) {
            throw new RuntimeException("No index defined.");
        }

        row = columnIndex[row] + 1; // getRowValues will subtract 1
        setValueAt(row, column, newValue);
    }

    /**
     * Return a value from a specified row and column. For speed, the column
     * type is not checked. A RuntimeException will be thrown if the column is
     * of type STRING.
     *
     */
    public void setStringValueAt(int row, int column, String newValue) {
        //Data is 0 based so subtract 1 from what the user supplies
        row = row - 1;
        column = column - 1;

        //TODO lookup based on indexed column
        String[] s = (String[]) columnData.get(column);

        s[row] = newValue;
        setDirty(true);
        if (indexColumns[column]==true) {
            fireIndexValuesChanged();
        }
        if (column == stringIndexColumn)
            stringIndexDirty = true;
    }

    /**
     * Set the value of a {@code STRING} column at a specified row.
     *
     * @param row
     *        The (1-based) row number.
     *
     * @param column
     *        The name of the column.
     *
     * @param value
     *        The value to place in {@code column} at {@code row}.
     *
     * @throws ClassCastException if {@code column} is not a {@code STRING} column.
     * @throws RuntimeException if {@code column} is not found in this table.
     */
    public void setStringValueAt(int row, String column, String value) {
        setStringValueAt(row,checkColumnPosition(column),value);
    }
    
    public void setIndexColumnNames(String[] indexColumnNames) {
        for (int i=0;i<indexColumnNames.length;i++) {
            int column = getColumnPosition(indexColumnNames[i]);
            if (column==-1) throw new RuntimeException("Can't find column name "+indexColumnNames[i]+" in TableDataSet for indexing");
            indexColumns[column-1]= true;
        }
    }

    /**
     * Returns a boolean indicating whether the file has been modified.
     */
    public boolean isDirty() {
        return dirty;
    }

    /**
     * Updates the dirty flag.
     */
    public void setDirty(boolean dirtyParam) {
        if (dirtyParam == true && dirty == false) {
            dirty = dirtyParam;
            if (myWatchers!=null) {
                for (int w=0;w<myWatchers.size();w++) {
                    TableDataSetWatcher t = (TableDataSetWatcher) myWatchers.get(w);
                    t.isDirty(this);
                }
            }
        }
        if (dirtyParam == false && dirty == true) {
            if (logger.isDebugEnabled()) logger.debug("Making TableDataset "+name+" into a clean one");
        }
        dirty = dirtyParam;
    }

    /** Build an index for constant-time access to a row based on column data values
     *
     * @param columnNumber used to build index should be an int in range
     *                      1..number of columns
     *
     */
    public void buildIndex(int columnNumber) {
        columnNumber = columnNumber - 1; //zero-based numbering

        //Retrieve the desired column
        float[] column = (float[]) columnData.get(columnNumber);

        //Find highest number in indexed column
        int highestNumber = 0;

        for (int r = 0; r < nRows; r++) {
            highestNumber = (int) Math.max(highestNumber, column[r]);
        }

        //Initialize the internal numbering by storing the position of each external number
        columnIndex = new int[highestNumber + 1];

        //-1 denotes unused numbers in sequence
        Arrays.fill(this.columnIndex, -1);

        //Integerize the column values (could be a problem)
        for (int r = 0; r < nRows; r++) {
            columnIndex[(int) column[r]] = r;
        }

        if (logger.isDebugEnabled()) {
            logger.debug("Indexed column: " + columnNumber);
            logger.debug("Highest Number in indexed column: " + highestNumber);

            //for (int r=0; r < highestNumber; r++) {
            //    Logger.logDebug("columnIndex["+r+"]="+columnIndex[r]);
            //}
        }
    }

    /**
     * Return the row number from a specified column and 
     * a specified value in the column using the indexed column.
     * 
     * Must call: public void buildIndex(int columnNumber)  beforehand
     */
    public float getIndexedValueAt(int value, int col) {
        if (columnIndex == null) {
            throw new RuntimeException("No index defined for column: " + col);
        }

        value = columnIndex[value];
        col = col - 1; //zero-based

        float[] column = (float[]) columnData.get(col);

        return column[value];
    }

    public float getIndexedValueAt(int value, String columnName) {
        int columnNumber = getColumnPosition(columnName);

        if (columnNumber <= 0) {
            logger.error("no column named " + columnName + " in TableDataSet");
            throw new RuntimeException("no column named " + columnName +
                " in TableDataSet");
        }

        return getIndexedValueAt(value, columnNumber);
    }

    /**
     * Update a TableDataSet by appending a column of data and a column heading.
     *
     * @param newColumn the float[] array of data to append to TableDataSet
     * @param newColumnLabel the new column heading to add to ArrayList.
     *
     */
    public void appendColumn(Object newColumn, String newColumnLabel) {
        int newType = -1;
        int rows = -1;

        if (newColumn instanceof float[] ) {
            newType = NUMBER;
            rows = ((float[]) newColumn).length;
            columnData.add((float[]) newColumn); //Add new column as float[]
        } else if (newColumn instanceof int[] ) {
            newType = NUMBER;
            rows = ((int[]) newColumn).length;
            int[] tempIntArray = (int[]) newColumn;
            float[] tempFloatArray = new float[rows];
            for (int i=0; i < rows; i++)
                tempFloatArray[i] = tempIntArray[i];
            columnData.add(tempFloatArray); //Add new column as float[]
        } else if (newColumn instanceof double[] ) {
            newType = NUMBER;
            rows = ((double[]) newColumn).length;
            double[] tempDoubleArray = (double[]) newColumn;
            float[] tempFloatArray = new float[rows];
            for (int i=0; i < rows; i++)
                tempFloatArray[i] = (float)tempDoubleArray[i];
            columnData.add(tempFloatArray); //Add new column as float[]
        } else if (newColumn instanceof String[]) {
            newType = STRING;
            rows = ((String[]) newColumn).length;
            columnData.add((String[]) newColumn); //Add new column as String[]
        } else {
            throw new RuntimeException(
                "invalid column type - cannot add to table");
        }

        //The first column added will determine the number of rows
        if (nRows == 0) {
            nRows = rows;
        }

        // check that the newColumn has the same number of rows as this dataset
        if (rows != nRows) {
            String msg = "could not append column with " + rows +
                " elements to data set with " + nRows + " rows.";
            logger.error(msg);
            throw new RuntimeException(msg);
        }

        //Extend type array and add type
        if (columnType == null) {
            columnType = new int[1];
            columnType[0] = newType;
        } else {
            int[] oldColumnType = columnType;
            columnType = new int[oldColumnType.length + 1];

            System.arraycopy(oldColumnType, 0, columnType, 0,
                oldColumnType.length);
            columnType[columnData.size() - 1] = newType;
        }

        //Extend type array and add type
        if (indexColumns == null) {
            indexColumns = new boolean[1];
            indexColumns[0] = false;
        } else {
            boolean[] oldIndexColumns = indexColumns;
            indexColumns = new boolean[oldIndexColumns.length + 1];

            System.arraycopy(oldIndexColumns, 0, indexColumns, 0,
                    oldIndexColumns.length);
            indexColumns[columnData.size() - 1] = false;
        }

        //Update number of columns
        nCols = columnData.size();

        //Add column label - if null or blank, then make a default lable
        if ((newColumnLabel == null) || (newColumnLabel.length() == 0)) {
            newColumnLabel = "column_" + nCols;
        }

        columnLabels.add(newColumnLabel);
        columnLabelsPresent = true;
    }
    public void appendColumnAsDouble(Object newColumn, String newColumnLabel) {
        int newType = -1;
        int rows = -1;

        if (newColumn instanceof double[] ) {
            newType = DOUBLE;
            rows = ((double[]) newColumn).length;
            double[] tempDoubleArray = (double[]) newColumn;
            columnData.add(tempDoubleArray); //Add new column as float[]
        } else if (newColumn instanceof String[]) {
            newType = STRING;
            rows = ((String[]) newColumn).length;
            columnData.add((String[]) newColumn); //Add new column as String[]
        } else {
            throw new RuntimeException(
                "invalid column type - cannot add to table");
        }

        //The first column added will determine the number of rows
        if (nRows == 0) {
            nRows = rows;
        }

        // check that the newColumn has the same number of rows as this dataset
        if (rows != nRows) {
            String msg = "could not append column with " + rows +
                " elements to data set with " + nRows + " rows.";
            logger.error(msg);
            throw new RuntimeException(msg);
        }

        //Extend type array and add type
        if (columnType == null) {
            columnType = new int[1];
            columnType[0] = newType;
        } else {
            int[] oldColumnType = columnType;
            columnType = new int[oldColumnType.length + 1];

            System.arraycopy(oldColumnType, 0, columnType, 0,
                oldColumnType.length);
            columnType[columnData.size() - 1] = newType;
        }

        //Extend type array and add type
        if (indexColumns == null) {
            indexColumns = new boolean[1];
            indexColumns[0] = false;
        } else {
            boolean[] oldIndexColumns = indexColumns;
            indexColumns = new boolean[oldIndexColumns.length + 1];

            System.arraycopy(oldIndexColumns, 0, indexColumns, 0,
                    oldIndexColumns.length);
            indexColumns[columnData.size() - 1] = false;
        }

        //Update number of columns
        nCols = columnData.size();

        //Add column label - if null or blank, then make a default lable
        if ((newColumnLabel == null) || (newColumnLabel.length() == 0)) {
            newColumnLabel = "column_" + nCols;
        }

        columnLabels.add(newColumnLabel);
        columnLabelsPresent = true;
    }

    
    
    /**
     * Convenience method to create a TableDataSet from a float[][] without column
     * labels. Default column labels will be created.
     * titles.
     *
     * @param tableData the float[][] array of data to covert to TableDataSet
     *
     */
    public static TableDataSet create(float[][] tableData) {
        int rows = tableData.length;
        int cols = tableData[0].length;

        //Create a new data set
        TableDataSet newTable = new TableDataSet();

        for (int c = 0; c < cols; c++) {
            float[] newColumn = new float[rows];

            for (int r = 0; r < rows; r++) {
                newColumn[r] = tableData[r][c];
            }

            newTable.appendColumn(newColumn, "column_" + (c + 1));
        }

        return newTable;
    }

	/**
	 * Create a TableDataSet from a float[][] data array, and a list of column
	 * titles.
	 *
	 * @param tableData the float[][] array of data to covert to TableDataSet
	 * @param tableHeadings the ArrayList of table headings
	 *
	 */
	public static TableDataSet create(float[][] tableData,
		ArrayList tableHeadings) {
		int rows = tableData.length;
		int cols = tableData[0].length;

		//Create a new data set
		TableDataSet newTable = new TableDataSet();

		for (int c = 0; c < cols; c++) {
			float[] newColumn = new float[rows];

			for (int r = 0; r < rows; r++) {
				newColumn[r] = tableData[r][c];
			}

			newTable.appendColumn(newColumn, (String) tableHeadings.get(c));
		}

		return newTable;
	}

    /**
	 * Create a TableDataSet from a float[][] data array, and an array of column
	 * titles.
	 *
	 * @param tableData the float[][] array of data to covert to TableDataSet
	 * @param tableHeadings the ArrayList of table headings
	 *
	 */
	public static TableDataSet create(float[][] tableData,
		String[] tableHeadings) {
		int rows = tableData.length;
		int cols = tableData[0].length;

		//Create a new data set
		TableDataSet newTable = new TableDataSet();

		for (int c = 0; c < cols; c++) {
			float[] newColumn = new float[rows];

			for (int r = 0; r < rows; r++) {
				newColumn[r] = tableData[r][c];
			}

			newTable.appendColumn(newColumn, tableHeadings[c]);
		}

		return newTable;
	}

	/**
	 * Create a TableDataSet from a String[][] data array, and a list of column
	 * titles.
	 *
	 * @param tableData the String[][] array of data to covert to TableDataSet
	 * @param tableHeadings the ArrayList of table headings
	 *
	 */
	public static TableDataSet create(String[][] tableData,
		ArrayList tableHeadings) {
		int rows = tableData.length;
		int cols = tableData[0].length;

		//Create a new data set
		TableDataSet newTable = new TableDataSet();

		for (int c = 0; c < cols; c++) {
			String[] newColumn = new String[rows];

			for (int r = 0; r < rows; r++) {
				newColumn[r] = tableData[r][c];
			}

			newTable.appendColumn(newColumn, (String) tableHeadings.get(c));
		}

		return newTable;
	}

    /**
	 * Create a TableDataSet from a String[][] data array, and an array of column
	 * titles.
	 *
	 * @param tableData the String[][] array of data to covert to TableDataSet
	 * @param tableHeadings the array of table headings
	 *
	 */
	public static TableDataSet create(String[][] tableData,
		String[] tableHeadings) {
		int rows = tableData.length;
		int cols = tableData[0].length;

		//Create a new data set
		TableDataSet newTable = new TableDataSet();

		for (int c = 0; c < cols; c++) {
			String[] newColumn = new String[rows];

			for (int r = 0; r < rows; r++) {
				newColumn[r] = tableData[r][c];
			}

			newTable.appendColumn(newColumn, tableHeadings[c]);
		}

		return newTable;
	}

	
    /**
     * Read the file and return the TableDataSet.
     * 
     * @param fileName
     * @return data
     */
    public static TableDataSet readFile(String fileName){
    	
    	logger.info("Begin reading the data in file " + fileName);
	    TableDataSet data;	
        try {
        	OLD_CSVFileReader csvFile = new OLD_CSVFileReader();
        	data = csvFile.readFile(new File(fileName));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        
        logger.info("End reading the data in file " + fileName);
        return data;
    }


    /**
     * Write the file.
     * 
     * @param fileName  Name of file to write
     * @param data      Data to write
     */
    public static void writeFile(String fileName, TableDataSet data){
    	
    	logger.info("Begin writing the data in file " + fileName);
	    try {
	    	CSVFileWriter csvFile = new CSVFileWriter();
        	csvFile.writeFile(data, new File(fileName));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        
        logger.info("End writing the data in file " + fileName);
     }

    /**
	 * Columns from the TableDataSet argument that do not also appear in the
	 * current object are appended to the current object.
	 *
	 * @param tdsIn the float[][] array of data to covert to TableDataSet
	 *
	 */
	public void merge ( TableDataSet tdsIn ) {
	    
	    String[] tdsInHeadings = tdsIn.getColumnLabels();
	    int[] tdsInTypes = tdsIn.getColumnType();
	    
		for (int c = 0; c < tdsIn.getColumnCount(); c++) {

		    // if the column heading in the input TableDataSet already exists, skip it.
			if ( getColumnPosition(tdsInHeadings[c]) >= 0 )
			    continue;
		    
			logger.info("Adding column " + tdsInHeadings[c] + " to TableDataSet due to merge");
            if ( tdsInTypes[c] == NUMBER ) {
				float[] newColumn = new float[nRows];

				for (int r = 0; r < nRows; r++)
					newColumn[r] = tdsIn.getValueAt( r+1, c+1 );

				appendColumn( newColumn, tdsInHeadings[c] );
			}
			else if ( tdsInTypes[c] == STRING ) {
				String[] newColumn = new String[nRows];

				for (int r = 0; r < nRows; r++)
					newColumn[r] = tdsIn.getStringValueAt( r+1, c+1 );

				appendColumn( newColumn, tdsInHeadings[c] );
			}
		}
        setDirty(true);
		
	}

    /**
     * Static method to log the frequency of values in
     * a column specified by the user.
     *
     * @param tableName String identifying contents of TableDataSet
     * @param tds containing column for creating frequency table
     * @param columnPosition position of desired column
     *
     */
    public static void logColumnFreqReport(String tableName, TableDataSet tds,
        int columnPosition) {
        if (tds.getRowCount() == 0) {
            logger.info(tableName + " Table is empty - no data to summarize");

            return;
        }

        float[] columnData = new float[tds.getRowCount()];
        int[] sortValues = new int[tds.getRowCount()];

        for (int r = 1; r <= tds.getRowCount(); r++) {
            columnData[r - 1] = tds.getValueAt(r, columnPosition);
            sortValues[r - 1] = (int) (columnData[r - 1] * 10000);
        }

        // sort the column elements
        int[] index = IndexSort.indexSort(sortValues);

        ArrayList bucketValues = new ArrayList();
        ArrayList bucketSizes = new ArrayList();

        // count the number of identical elements into buckets
        float oldValue = columnData[index[0]];
        int count = 1;

        for (int r = 1; r < tds.getRowCount(); r++) {
            if (columnData[index[r]] > oldValue) {
                bucketValues.add(Float.toString(oldValue));
                bucketSizes.add(Integer.toString(count));
                count = 0;
                oldValue = columnData[index[r]];
            }

            count++;
        }

        bucketValues.add(Float.toString(oldValue));
        bucketSizes.add(Integer.toString(count));

        // print a simple summary table
        logger.info("Frequency Report table: " + tableName);
        logger.info("Frequency for column " + columnPosition + ": " +
            (tds.getColumnLabel(columnPosition)));
        logger.info(String.format("%8s", "Value") +
            String.format("%11s", "Frequency"));

        int total = 0;

        for (int i = 0; i < bucketValues.size(); i++) {
            float value = Float.parseFloat((String) (bucketValues.get(i)));
            logger.info(String.format("%8.0f", value) +
                    String.format("%11d", Integer.parseInt((String) (bucketSizes.get(i)))));
            total += Integer.parseInt((String) (bucketSizes.get(i)));
        }

        logger.info(String.format("%8s", "Total") +
            String.format("%11d\n\n\n", total));
    }

    /**
     * Logs the frequency of values in a column specified by the user.
     * The array list argument can hold descriptions of the values
     * if they are known.  For example if a column lists alternatives 1-5, you
     * might know that alt 1= 0_autos, alt2=1_auto, etc.
     *
     * @param tableName String identifying contents of TableDataSet
     * @param tds containing column for creating frequency table
     * @param columnPosition position of desired column
     *
     */
    public static void logColumnFreqReport(String tableName, TableDataSet tds,
        int columnPosition, String[] descriptions) {
        if (tds.getRowCount() == 0) {
            logger.info(tableName + " Table is empty - no data to summarize");

            return;
        }

        float[] columnData = new float[tds.getRowCount()];
        int[] sortValues = new int[tds.getRowCount()];

        for (int r = 1; r <= tds.getRowCount(); r++) {
            columnData[r - 1] = tds.getValueAt(r, columnPosition);
            sortValues[r - 1] = (int) (columnData[r - 1] * 10000);
        }

        // sort the column elements
        int[] index = IndexSort.indexSort(sortValues);

        ArrayList bucketValues = new ArrayList();
        ArrayList bucketSizes = new ArrayList();

        // count the number of identical elements into buckets
        float oldValue = columnData[index[0]];
        int count = 1;

        for (int r = 1; r < tds.getRowCount(); r++) {
            if (columnData[index[r]] > oldValue) {
                bucketValues.add(Float.toString(oldValue));
                bucketSizes.add(Integer.toString(count));
                count = 0;
                oldValue = columnData[index[r]];
            }

            count++;
        }

        bucketValues.add(Float.toString(oldValue));
        bucketSizes.add(Integer.toString(count));

        // print a simple summary table
        logger.info("Frequency Report table: " + tableName);
        logger.info("Frequency for column " + columnPosition + ": " +
            (tds.getColumnLabel(columnPosition)));
        logger.info(String.format("%8s", "Value") +
            String.format("%13s", "Description") +
            String.format("%11s", "Frequency"));

        if(descriptions!=null)
            if(bucketValues.size() != descriptions.length)
                logger.fatal("The number of descriptions does not match the number of values in your data");

        int total = 0;

        for (int i = 0; i < bucketValues.size(); i++) {
            float value = Float.parseFloat((String) (bucketValues.get(i)));
            String description = "";               //default value as sometime certain columns don't have descriptions
            if(descriptions !=null) {
                description = descriptions[i];
            }
            logger.info(String.format("%8.0f", value) + "  " + String.format("%-11s", description) +
                String.format("%11d", Integer.parseInt((String) (bucketSizes.get(i)))));
            total += Integer.parseInt((String) (bucketSizes.get(i)));
        }

        logger.info(String.format("%23s", "Total") +
            String.format("%9d\n\n\n", total));
    }


    /**
     * @param index
     */
    public void removeChangeListener(ChangeListener index) {
        changeListeners.remove(index);
    }


    public void setName(String name) {
        this.name = name;
    }


    public String getName() {
        return name;
    }

    /* (non-Javadoc)
     * @see java.lang.Object#toString()
     */
    public String toString() {
        return "TableDataSet "+name;
    }


    public interface TableDataSetWatcher {
        public void isBeingForgotten(TableDataSet s);
        public void isDirty(TableDataSet s);
    }
    
    private ArrayList myWatchers = null;
	public boolean use1sAnd0sForTrueFalse = false;
    
    public void addFinalizingListener(TableDataSetWatcher watcher) {
        if (myWatchers ==null) {
            myWatchers = new ArrayList();
        }
        myWatchers.add(watcher);
    }


    void tellWatchersImBeingForgotten() {
        if (myWatchers != null) {
                for (int w=0;w<myWatchers.size();w++) {
                ((TableDataSetWatcher) myWatchers.get(w)).isBeingForgotten(this);
            }
        }
        columnData = null;
    }


//    // TODO remove this method, just for debugging.
//    @Override
//    protected void finalize() throws Throwable {
//        logger.info("Finalizing TableDataSet "+name);
//        tellWatchersImBeingForgotten();
//        if (isDirty()) {
//            logger.fatal("Finalizing a dirty dataset, this is bad!");
//            // normally one would throw a RuntimeException, but the finalize() method could be called from a different thread.
//            // so safer to exit()
//            System.exit(1);
//        }
//        super.finalize();
//    }
    

    ////// String Indexing Stuff //////
    private Map<String,Integer> stringIndex = null; //map of string index keys to 1-based row numbers
    private int stringIndexColumn = -1;
    private boolean stringIndexDirty;

    /**
     * Build a string index on the specified column. The values in the column must be unique. If the column is
     * modified after the index is built, the index must be rebuilt (using this function) before it can be used again.
     *
     * @param column
     *        The column to build the index on.
     *
     * @throws IllegalStateException if the column contains repeated values.
     * @throws RuntimeException if the column is not of type {@code STRING}.
     */
    public void buildStringIndex(int column) {
        checkColumnNumber(column, STRING);
        column--; //changed to a zero based index
        String[] columnValues = (String[]) columnData.get(column);

        stringIndex = new HashMap<String, Integer>(columnValues.length);
        Set<String> repeatedValues = new HashSet<String>();

        for (int i = 0; i < columnValues.length; i++)
            if (stringIndex.put(columnValues[i],i+1) != null)
                repeatedValues.add(columnValues[i]);

        if (repeatedValues.size() > 0) {
            //nulify the index, as it is invalid anyway, in case somebody catches this exception and tries to carry on
            stringIndex = null;
            stringIndexColumn = -1;
            throw new IllegalStateException("String index cannot be built on a column with non-unique values." +
                    "The following values have been repeated: " + Arrays.toString(repeatedValues.toArray(new String[repeatedValues.size()])));
        }

        stringIndexColumn = column;
        stringIndexDirty = false;
    }

    private void checkStringIndexValue(String index) {
        if (stringIndex == null)
            throw new IllegalStateException("No string index exists for this table.");
        if (stringIndexDirty)
            throw new IllegalStateException("String index column changed, must be rebuilt.");
        if (!stringIndex.containsKey(index))
            throw new IllegalArgumentException("String value not found in index: " + index);
    }

    /**
     * Get the (0-based) row number for the given string index value.
     *
     * @param index
     *        The string index value.
     *
     * @return the row number corresponding to index {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     */
    public int getStringIndexedRowNumber(String index) {
        checkStringIndexValue(index);
        return stringIndex.get(index)-1;
    }

    /**
     * Get the value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     * @throws RuntimeException if {@code column} does not hold {@code float}s.
     */
    public float getStringIndexedValueAt(String index, int column) {
        checkStringIndexValue(index);
        return getValueAt(stringIndex.get(index),column);
    }

    /**
     * Get the value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table, or does not hold {@code float}s.
     */
    public float getStringIndexedValueAt(String index, String column) {
        checkStringIndexValue(index);
        return getValueAt(stringIndex.get(index),column);
    }

    /**
     * Get the boolean value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     * @throws RuntimeException if {@code column} does not hold {@code boolean}s.
     */
    public boolean getStringIndexedBooleanValueAt(String index, int column) {
        checkStringIndexValue(index);
        return getBooleanValueAt(stringIndex.get(index),column);
    }

    /**
     * Get the boolean value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table, or does not hold {@code boolean}s.
     */
    public boolean getStringIndexedBooleanValueAt(String index, String column) {
        checkStringIndexValue(index);
        return getBooleanValueAt(stringIndex.get(index),column);
    }

    /**
     * Get the string value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     */
    public String getStringIndexedStringValueAt(String index, int column) {
        checkStringIndexValue(index);
        return getStringValueAt(stringIndex.get(index),column);
    }

    /**
     * Get the string value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @return the value in {@code column} at the row specified by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table.
     */
    public String getStringIndexedStringValueAt(String index, String column) {
        checkStringIndexValue(index);
        return getStringValueAt(stringIndex.get(index),column);
    }

    /**
     * Set the value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     * @throws ClassCastException if {@code column} does not hold {@code float}s.
     */
    public void setStringIndexedValueAt(String index, int column, float value) {
        checkStringIndexValue(index);
        setValueAt(stringIndex.get(index),column,value);
    }

    /**
     * Set the value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table.
     * @throws ClassCastException if {@code column} does not hold {@code float}s.
     */
    public void setStringIndexedValueAt(String index, String column, float value) {
        checkStringIndexValue(index);
        setValueAt(stringIndex.get(index),column,value);
    }

    /**
     * Set the boolean value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     * @throws ClassCastException if {@code column} does not hold {@code boolean}s.
     */
    public void setStringIndexedBooleanValueAt(String index, int column, boolean value) {
        checkStringIndexValue(index);
        setBooleanValueAt(stringIndex.get(index),column,value);
    }

    /**
     * Set the boolean value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table.
     * @throws ClassCastException if {@code column} does not hold {@code boolean}s.
     */
    public void setStringIndexedBooleanValueAt(String index, String column, boolean value) {
        checkStringIndexValue(index);
        setBooleanValueAt(stringIndex.get(index),column,value);
    }

    /**
     * Set the string value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The (1-based) column number.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws IndexOutOfBoundsException if {@code column} is less than 1 or greater than the number of columns in this table.
     * @throws ClassCastException if {@code column} does not hold {@code String}s.
     */
    public void setStringIndexedStringValueAt(String index, int column, String value) {
        checkStringIndexValue(index);
        setStringValueAt(stringIndex.get(index),column,value);
    }

    /**
     * Set the string value for the specified column and row (specified by string index).
     *
     * @param index
     *        The index specifying the row.
     *
     * @param column
     *        The column name.
     *
     * @param value
     *        The value to place in {@code column} at the row indexed by {@code index}.
     *
     * @throws IllegalStateException if no string index has been built for this table, or if the index needs to be
     *                               rebuilt (because the index column has been modified after the index was built).
     * @throws IllegalArgumentException if {@code index} is not found in the index column.
     * @throws RuntimeException if {@code column} is not found in the table.
     * @throws ClassCastException if {@code column} does not hold {@code String}s.
     */
    public void setStringIndexedStringValueAt(String index, String column, String value) {
        checkStringIndexValue(index);
        setStringValueAt(stringIndex.get(index),column,value);
    }

    //The user must ensure that the keys in the HashMap correspond
    //to the headers in the table and that each column in the table
    //has a value in the HashMap that is of the correct type. This
    //method will not do a lot of error checking or handling.
    //
    //
    public void appendRow(HashMap rowData){

        int type;
        String[] headers = getColumnLabels();
        int columnNum = 1;
        for(String header : headers){
            System.out.println("Header Value to Append: " + header);
            type = getColumnType()[getColumnPosition(header)-1];
            if(type == DataTypes.NUMBER){
                float[] col = getColumnAsFloat(header);
                float[] newCol = new float[col.length+1];
                System.arraycopy(col, 0, newCol, 0, col.length);
                newCol[newCol.length-1] = (Float) rowData.get(header);
                replaceFloatColumn(columnNum, newCol);
            }else if(type == DataTypes.STRING){
                String[] col = getColumnAsString(header);
                String[] newCol = new String[col.length+1];
                System.arraycopy(col, 0, newCol, 0, col.length);
                newCol[newCol.length-1] = (String) rowData.get(header);
                replaceStringColumn(columnNum, newCol);
            }
            columnNum++;
        }
        nRows++;

    }

    //column positions are 1-number of columns but columnData ArrayList
    //is zero-based so subtract 1 from the supplied colNumber
    public void replaceFloatColumn(int colNumber, float[] newData){
        columnData.remove(colNumber-1);
        columnData.add(colNumber-1, newData);
    }

    //column positions are 1-number of columns but columnData ArrayList
    //is zero-based so subtract 1 from the supplied colNumber
    public void replaceStringColumn(int colNumber, String[] newData){
        columnData.remove(colNumber-1);
        columnData.add(colNumber-1, newData);
    }
    
}


