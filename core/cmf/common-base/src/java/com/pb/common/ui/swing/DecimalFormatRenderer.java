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
package com.pb.common.ui.swing;

import java.text.NumberFormat;
import javax.swing.table.DefaultTableCellRenderer;

public class DecimalFormatRenderer extends DefaultTableCellRenderer {

	int numberOfDecimalPlaces;
	
	public DecimalFormatRenderer( int numberOfDecimalPlaces ) {
		super();
		setHorizontalAlignment(javax.swing.SwingConstants.RIGHT);
		this.numberOfDecimalPlaces = numberOfDecimalPlaces;
	}

	// values in the table being rendered are String representations of floating point numbers
	public void setValue(Object value) {
		if ( value != null ) {
			Number numberValue = (Number) Float.valueOf((String)value);
			NumberFormat formatter = NumberFormat.getNumberInstance();
			formatter.setMaximumFractionDigits( numberOfDecimalPlaces );
			value = formatter.format(numberValue.floatValue());
		} 
		super.setValue(value);
  } 

} 
