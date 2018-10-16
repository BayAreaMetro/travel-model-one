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

import java.awt.Component;
import java.awt.Insets;
import javax.swing.ListCellRenderer;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.BorderFactory;
import javax.swing.JList;
import javax.swing.JTable;
import javax.swing.UIManager;
import javax.swing.border.Border;
import javax.swing.plaf.BorderUIResource;

/**
 * Creates a row header which can be used in JTable to make it look and act more like a
 * spreadsheet.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class RowHeaderRenderer extends DefaultTableCellRenderer implements ListCellRenderer {

    protected Border noFocusBorder, focusBorder;

    public RowHeaderRenderer() {
        setOpaque(true);
        setBorder(noFocusBorder);
    }

    public void updateUI() {
        super.updateUI();
        Border cell = UIManager.getBorder("TableHeader.cellBorder");
        Border focus = UIManager.getBorder("Table.focusCellHighlightBorder");

        focusBorder = new BorderUIResource.CompoundBorderUIResource(cell, focus);

        Insets i = focus.getBorderInsets(this);

        noFocusBorder = new BorderUIResource.CompoundBorderUIResource
                (cell, BorderFactory.createEmptyBorder(i.top, i.left, i.bottom, i.right));

        /* Alternatively, if focus shouldn't be supported:

        focusBorder = noFocusBorder = cell;
    
        */
    }

    public Component getListCellRendererComponent(JList list, Object value,
                                                  int index, boolean selected, boolean focused) {
        if (list != null) {
            if (selected) {
                setBackground(list.getSelectionBackground());
                setForeground(list.getSelectionForeground());
            } else {
                setBackground(list.getBackground());
                setForeground(list.getForeground());
            }

            setFont(list.getFont());

            setEnabled(list.isEnabled());
        } else {
            setBackground(UIManager.getColor("TableHeader.background"));
            setForeground(UIManager.getColor("TableHeader.foreground"));
            setFont(UIManager.getFont("TableHeader.font"));
            setEnabled(true);
        }

        if (focused)
            setBorder(focusBorder);
        else
            setBorder(noFocusBorder);

        setValue(value);

        return this;
    }

    public Component getTableCellRendererComponent(JTable table, Object value,
                                                   boolean selected, boolean focused, int row, int column) {
        if (table != null) {
            if (selected) {
                setBackground(table.getSelectionBackground());
                setForeground(table.getSelectionForeground());
            } else {
                setBackground(table.getBackground());
                setForeground(table.getForeground());
            }

            setFont(table.getFont());

            setEnabled(table.isEnabled());
        } else {
            setBackground(UIManager.getColor("TableHeader.background"));
            setForeground(UIManager.getColor("TableHeader.foreground"));
            setFont(UIManager.getFont("TableHeader.font"));
            setEnabled(true);
        }

        if (focused)
            setBorder(focusBorder);
        else
            setBorder(noFocusBorder);

        setValue(value);

        return this;
    }
}