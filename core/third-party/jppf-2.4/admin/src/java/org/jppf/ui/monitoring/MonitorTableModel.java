/*
 * JPPF.
 * Copyright (C) 2005-2010 JPPF Team.
 * http://www.jppf.org
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jppf.ui.monitoring;

import java.util.Map;

import javax.swing.table.AbstractTableModel;

import org.jppf.server.JPPFStats;
import org.jppf.ui.monitoring.data.*;

/**
 * Data model for the tables displaying the values.
 */
class MonitorTableModel extends AbstractTableModel
{
	/**
	 * The list of fields whose values are displayed in the table.
	 */
	private Fields[] fields = null;

	/**
	 * Initialize this table model witht he specified list of fields.
	 * @param fields the list of fields whose values are displayed in the table.
	 */
	MonitorTableModel(Fields[] fields)
	{
		this.fields = fields;
	}

	/**
	 * Get the number of columns in the table.
	 * @return 2.
	 * @see javax.swing.table.TableModel#getColumnCount()
	 */
	public int getColumnCount()
	{
		return 2;
	}

	/**
	 * Get the number of rows in the table.
	 * @return the number of fields displayed in the table.
	 * @see javax.swing.table.TableModel#getRowCount()
	 */
	public int getRowCount()
	{
		return fields.length;
	}

	/**
	 * Get a value at specified coordinates in the table.
	 * @param row the row coordinate.
	 * @param column the column coordinate.
	 * @return the value as an object.
	 * @see javax.swing.table.TableModel#getValueAt(int, int)
	 */
	public Object getValueAt(int row, int column)
	{
		Fields name = fields[row];
		if (column == 0) return name;
		Map<Fields, String> valuesMap = null;
		if (StatsHandler.getInstance().getStatsCount() > 0) valuesMap = StatsHandler.getInstance().getLatestStringValues();
		else valuesMap = StatsFormatter.getStringValuesMap(new JPPFStats());
		return valuesMap.get(name);
	}
}