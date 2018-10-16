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

import java.awt.BorderLayout;
import javax.swing.*;
import javax.swing.table.*;

import java.util.Vector;

/**
 * Creates a row header which can be used in JList.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class RowHeaderList {
    
    public static void main(String[] args) {
        DefaultListModel list = new DefaultListModel();
        DefaultTableModel data = new DefaultTableModel(0, 6);

        for (int i = 0; i < 30; i++) {
            list.addElement("Line: " + i);

            Vector v = new Vector();

            for (int k = 0; k < 6; k++)
                v.add(new Float(k / (float) i));

            data.addRow(v);
        }

        JTable table = new JTable(data);

        JList rowHeader = new JList(list);

        LookAndFeel.installColorsAndFont
                (rowHeader, "TableHeader.background",
                        "TableHeader.foreground", "TableHeader.font");


        rowHeader.setFixedCellHeight(table.getRowHeight());
        rowHeader.setCellRenderer(new RowHeaderRenderer());

        JScrollPane scrollPane = new JScrollPane(table);

        scrollPane.setRowHeaderView(rowHeader);


        new JScrollPaneAdjuster(scrollPane);


        JFrame f = new JFrame("Row Header Test");

        f.getContentPane().add(scrollPane, BorderLayout.CENTER);

        f.pack();
        f.setLocation(200, 100);
        f.setVisible(true);
    }
}

