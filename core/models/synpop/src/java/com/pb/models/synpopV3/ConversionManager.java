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

import com.pb.common.datafile.TableDataSet;
import com.pb.common.datafile.DataTypes;
import com.pb.common.datafile.CSVFileReader;
import com.pb.common.datafile.CSVFileWriter;
import com.pb.common.matrix.Matrix;

import java.util.HashMap;
import java.util.Set;
import java.util.Iterator;
import java.util.Vector;
import org.apache.log4j.Logger;

import java.io.File;
import java.io.IOException;

/**
 * <p>
 * Company: PB Consult, Parsons Brinckerhoff
 * </p>
 * 
 * @author Wu Sun
 * @version 1.1, Oct. 1, 2004
 */
public class ConversionManager implements DataTypes {

	protected Logger logger = Logger.getLogger("com.pb.models.synpopV3");

	protected TableDataReader tableReader;

	protected CSVFileReader CSVReader = new CSVFileReader();

	protected CSVFileWriter CSVWriter = new CSVFileWriter();

	protected HashMap conversionTables;

	protected int NoConversionTables;

	protected HashMap tableBaseUnitMap;

	/**
	 * Constructor
	 * 
	 * @param tableReader
	 *            represents conversion table reader
	 */
	public ConversionManager(TableDataReader tableReader) {

		this.tableReader = tableReader;
		conversionTables = tableReader.getTables();
		tableBaseUnitMap = makeTableBaseUnitMap();
	}

	public void writeConvertedTable(TableDataSet table, String fileName) {
		String outputDir = PropertyParser
				.getPropertyByName("converted.directory");
		try {
			CSVWriter.writeFile(table, new File(outputDir + fileName));
		} catch (IOException e) {
			logger.error("failed writing out:" + fileName);
		}
	}

	public HashMap getTableBaseUnitMap() {
		return tableBaseUnitMap;
	}

	/**
	 * Convert from block group-based table to taz-based table Note: Block Group
	 * to TAZ is "many to many" relationship
	 * 
	 * @param conversionTableName
	 *            represents conversion table name, "TAZ00_BLKGRP00.csv"
	 * @param sourceTable
	 *            represents source block group-based table
	 * @param fields
	 *            represents fields to be included in taz-based table
	 * @return
	 */
	public TableDataSet BlkgrpToTAZ(String conversionTableName,
			String sourceTableName, TableDataSet sourceTable, String[] fields) {

		TableDataSet result = new TableDataSet();
		int numberOfInternalZones = PopulationSynthesizer.numberOfInternalZones;

		// initialize TAZ-table column labels
		String[] colLabels = new String[fields.length + 1];
		for (int i = 0; i < colLabels.length; i++) {
			if (i == 0) {
				colLabels[i] = "TAZ";
			} else {
				colLabels[i] = fields[i - 1];
			}
		}

		// in TAZ-table, initialize TAZ col with external TAZ
		int[] tazCol = new int[numberOfInternalZones];
		for (int i = 0; i < numberOfInternalZones; i++) {
			// tazCol[i] = i + 1;
			tazCol[i] = ExtTAZtoIntTAZIndex.getExternalTAZ(i+1);
		}

		// in TAZ-table, initialize data [NoTAZs][No Of fields]
		float[][] data = new float[numberOfInternalZones][fields.length];
		for (int i = 0; i < numberOfInternalZones; i++) {
			for (int j = 0; j < fields.length; j++) {
				data[i][j] = 0f;
			}
		}

		int NoMatrixRows = numberOfInternalZones;
		int NoMatrixCols = fields.length;
		Matrix workingMatrix;
		Matrix resultMatrix = new Matrix(data);

		// get block group column in table, this column must be named BLKGRP
		int NoBlocks = sourceTable.getRowCount();
		String[] block = sourceTable.getColumnAsString("BLKGRP");

		// populate TAZ-table
		HashMap currentMap = null;
		float[] fieldVals = new float[fields.length];

		for (int i = 0; i < NoBlocks; i++) {
			
			// clean current working Matrix
			workingMatrix = null;
			// "taz" percentage mapping of current block
			// in conversion table, there must be a "BLKGRP" and a "TAZ" columns
			currentMap = lookUp(conversionTableName, "BLKGRP", block[i], "TAZ");

			if (currentMap.size() < 1) {
				logger.error("Block group:" + block[i]
						+ " has no matching TAZ.");
			} else {
				// in current block, get its field values of those fields in
				// TAZ-based table
				for (int j = 0; j < fields.length; j++) {
					// current block field values of those fields in TAZ-based
					// table
					fieldVals[j] = sourceTable.getValueAt((i + 1), fields[j]);
				}
				// convert from block-table to taz-table
				workingMatrix = doWork(currentMap, NoMatrixRows, NoMatrixCols,
						fieldVals);
			}
			resultMatrix = resultMatrix.add(workingMatrix);
		}

		// append taz column to result table
		result.appendColumn(tazCol, null);

		// append field columns to result table
		float[] temp = new float[numberOfInternalZones];
		for (int j = 0; j < fields.length; j++) {
			temp = (resultMatrix.getColumn(j + 1)).copyValues1D();
			result.appendColumn(temp, null);
		}

		// in TAZ-table, set column labels
		result.setColumnLabels(colLabels);
		return result;
	}

	/**
	 * Convert blcok-based sf1 CTPP table to taz-based table Note: Block to TAZ
	 * is "many to 1" relationship
	 * 
	 * @param conversionTableName
	 *            represents conversion table name, "BLK00_TAZ00.csv"
	 * @param sourceTable
	 *            represents source sf1 tables, sf1p20 and sf1p26
	 * @return
	 */
	public TableDataSet BlockToTAZ(String conversionTableName,
			String sourceTableName, TableDataSet sourceTable) {

		int NoSourceRows = sourceTable.getRowCount();
		int NoSourceCols = sourceTable.getColumnCount();

		// initialize conversion table
		TableDataSet conversionTable = (TableDataSet) conversionTables
				.get(conversionTableName);
		int NoConversionRows = conversionTable.getRowCount();

		int[] resultTAZRow = ExtTAZtoIntTAZIndex.getExternalTAZs();
		int NoResultRows = resultTAZRow.length;
		int NoResultCols = NoSourceCols;

		// get "BLOCK" column in source table
		String[] block_s = sourceTable.getColumnAsString("BLOCK");
		// get "BLOCK" column in conversion table
		String[] block_c = conversionTable.getColumnAsString("BLOCK");
		// get "TAZ" column in conversion table
		int[] taz = conversionTable.getColumnAsInt("TAZ");

		// initialize temp table. temp table is non-unique TAZ-based table.
		TableDataSet tempTable = new TableDataSet();

		// make TAZ row for temp table, tazs are non-unique
		float[] tempTAZRow = new float[NoSourceRows];
		for (int i = 0; i < NoSourceRows; i++) {
			for (int j = 0; j < NoConversionRows; j++) {
				if (block_s[i].equalsIgnoreCase(block_c[j])) {
					tempTAZRow[i] = taz[j];
					break;
				}
			}
		}

		tempTable.appendColumn(tempTAZRow, null);

		// make other columns for temp table
		for (int i = 2; i < NoSourceCols + 1; i++) {
			tempTable.appendColumn(sourceTable.getColumnAsFloat(i), null);
		}

		// source table is converted to a taz-based table now, but, TAZ is not
		// unique
		// in following section, combine non-unique rows in temp table

		// result data definition
		float[][] data = new float[NoResultRows][NoResultCols];

		// populate result data
		for (int i = 0; i < NoResultRows; i++) {
			for (int j = 1; j < NoResultCols; j++) {
				for (int k = 0; k < NoSourceRows; k++) {
					if (tempTAZRow[k] == resultTAZRow[i]) {
						// set "TAZ" column
						data[i][0] = resultTAZRow[i];
						// combine rows
						data[i][j] += tempTable.getValueAt(k + 1, j + 1);
					}
				}
			}
		}

		// create result table
		TableDataSet result = TableDataSet.create(data);

		// set column labels to result table
		String[] colLabels = sourceTable.getColumnLabels();
		colLabels[0] = "TAZ";
		result.setColumnLabels(colLabels);
		return result;
	}

	/**
	 * Convert CTPP table to taz-based table Note: TAZ_CTPP and CENTROID is 1 to
	 * 1 relationship
	 * 
	 * @param conversionTableName
	 *            represents conversion table name, "TAZ00_TRACT_COUNTY.csv"
	 * @param sourceTable
	 *            represents source CTPP table, CTPP_62, 64, 66, 75
	 * @return
	 */
	public TableDataSet CtppToTAZ(String conversionTableName,
			String sourceTableName, TableDataSet sourceTable) {

		// initialize source table
		TableDataSet result = sourceTable;
		
		// get "TAZ_CTPP_S" column in source table
		String[] taz_ctpp_s = sourceTable.getColumnAsString("TAZ_CTPP_S");

		// initialize conversion table
		TableDataSet conversionTable = (TableDataSet) conversionTables
				.get(conversionTableName);
		
		// get TAZ_CTPP column in conversion table
		String[] taz_ctpp_c = conversionTable.getColumnAsString("TAZ_CTPP_S");
		
		// get TAZ Centroid column in conversion table
		int[] centroid = conversionTable.getColumnAsInt("CENTROID");

		for (int i = 0; i < sourceTable.getRowCount(); i++) {
			for (int j = 0; j < conversionTable.getRowCount(); j++) {
				if (taz_ctpp_s[i].equalsIgnoreCase(taz_ctpp_c[j])) {
					
					// CENTROID is 1st column in taz-table
					result.setStringValueAt(i + 1, 1, centroid[j] + "");
					break;
				}
			}
		}

		// update column labels
		String[] colLabels = result.getColumnLabels();
		
		colLabels[0] = "TAZ";
		result.setColumnLabels(colLabels);
		return result;
	}

	/**
	 * given a value in a column, create a map of corresponding columns and
	 * mapping percentage of these columns
	 * 
	 * -----------------------Example---------------------------------- TAZ 12
	 * maps to blocks 101, 102, 103 by percentage 20%, 40%, 40% the created map
	 * should be: 101--20% 102--40% 103--40%
	 * ----------------------------------------------------------------
	 * 
	 * @param conversionTableName
	 *            represents a conversion table name
	 * @param givenColName
	 *            represents the given column name, "TAZ" in our example.
	 * @param givenColVal
	 *            represents the given column value, 12 in our example.
	 * @param returnColName
	 *            represents the return column name, "blok" in our example.
	 * @return
	 */
	private HashMap lookUp(String conversionTableName, String givenColName,
			String givenColVal, String returnColName) {

		HashMap result = new HashMap();

		TableDataSet table = (TableDataSet) conversionTables
				.get(conversionTableName);

		int givenColPosition = table.getColumnPosition(givenColName);
		int returnColPosition = table.getColumnPosition(returnColName);

		// assume conversion table percentage columns name=base col name+"PC"
		// e.g.: TAZ---TAZPC BLKGRP--BLKGRPPC
		int givenColPctPosition = table.getColumnPosition(givenColName + "PC");
		int NoRows = table.getRowCount();

		int[] colTypes = table.getColumnType();
		String[] givenCol = new String[NoRows];
		String[] returnCol = new String[NoRows];
		int[] temp;

		// get given column values, if int, convert to String
		if (colTypes[givenColPosition - 1] == STRING) {
			givenCol = table.getColumnAsString(givenColPosition);
		} else {
			temp = null;
			temp = table.getColumnAsInt(givenColPosition);
			for (int i = 0; i < NoRows; i++) {
				givenCol[i] = temp[i] + "";
			}
		}

		// get return column values, if int, convert to String
		if (colTypes[returnColPosition - 1] == STRING) {
			returnCol = table.getColumnAsString(returnColPosition);
		} else {
			temp = null;
			temp = table.getColumnAsInt(returnColPosition);
			for (int i = 0; i < NoRows; i++) {
				returnCol[i] = temp[i] + "";
			}
		}

		// get given column percentage values
		float[] givenColPct = table.getColumnAsFloat(givenColPctPosition);

		float totPct = 0;
		for (int i = 0; i < NoRows; i++) {
			if (givenColVal.equalsIgnoreCase(givenCol[i])) {
				result.put(returnCol[i], new Float(givenColPct[i]));
				totPct += givenColPct[i];
			}
		}

		if (totPct < 0.99)
			logger.info("Warning: total percentage in lookup map=" + totPct
					+ " " + givenColVal + " in " + givenColName);

		return result;
	}

	/**
	 * make table name---------table base unit mapping note: table base is
	 * either "block", "blkgrp", or "taz" both table names and table base units
	 * are defined in arc.properties
	 * 
	 * @return
	 */
	private HashMap makeTableBaseUnitMap() {

		Vector tableNames = PropertyParser.getPropertyElementsByName(
				"census.tables", ",");
		Vector tableBaseUnits = PropertyParser.getPropertyElementsByName(
				"census.baseUnits", ",");
		HashMap map = new HashMap();

		if (tableNames.size() != tableBaseUnits.size()) {
			logger
					.error("in property file, table names and table base units don't match.");
		}
		for (int i = 0; i < tableNames.size(); i++) {
			map.put(tableNames.get(i), tableBaseUnits.get(i));
		}

		return map;
	}

	/**
	 * Convert from block-table to taz-table
	 * 
	 * @param map
	 *            represents "taz" percentage mapping of current block
	 * @param currentData
	 *            represents field data in taz-table
	 * @param fieldVals
	 *            represent field values for current block
	 * @return
	 */
	private Matrix doWork(HashMap map, int NoRows, int NoCols, float[] fieldVals) {

		// initialize matrix with all 0 data array
		Matrix result = new Matrix(NoRows, NoCols);
		// key set--TAZs
		Set keySet = map.keySet();
		Iterator itr = keySet.iterator();

		int NoFields = fieldVals.length;
		String tazObj = null;
		int taz = -1;
		int internalTAZ = -1;
		float pct = 0f;

		// ---------------------------------------------------------------------------
		// Convert block-table to taz-table example:
		// -----------------------------------------
		// From: To:
		// ----- ----
		// block field1 field2 field3 taz field1 field2 field3
		// 001 100 200 300 1 100*0.3 200*0.3 300*0.3
		// 2 100*0.7 200*0.7 300*0.7
		//									 		
		// block taz percent
		// 001 1 0.3
		// 001 2 0.7
		// ---------------------------------------------------------------------------

		while (itr.hasNext()) {
			// external taz in percentage map
			tazObj = (String) itr.next();
			taz = (new Integer(tazObj)).intValue();
			// percentage of this taz
			pct = ((Float) map.get(tazObj)).floatValue();

			// internal taz, also the row position in TAZ-based table
			internalTAZ = ExtTAZtoIntTAZIndex.getInternalTAZ(taz);

			for (int i = 0; i < NoFields; i++) {
				result.setValueAt(internalTAZ, i + 1, fieldVals[i] * pct);
			}
		}
		return result;
	}

}
