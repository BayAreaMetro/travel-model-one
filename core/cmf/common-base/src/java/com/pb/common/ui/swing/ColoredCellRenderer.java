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

import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.*;
import java.awt.*;

/**
 * A customer TableCellRender to color altering the rows in a table.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class ColoredCellRenderer extends DefaultTableCellRenderer {

    public Component getTableCellRendererComponent(JTable table, Object value,
                                                   boolean selected, boolean focused, int row, int column)
    {
        setEnabled(table == null || table.isEnabled());

        if ((row % 5) == 0)
            setBackground(Color.green);
        else
            setBackground(null);

        super.getTableCellRendererComponent(table, value, selected, focused, row, column);

        return this;
    }
}