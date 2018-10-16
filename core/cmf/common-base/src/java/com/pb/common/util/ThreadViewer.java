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
package com.pb.common.util;

import javax.swing.*;
import javax.swing.table.TableColumn;
import javax.swing.table.TableColumnModel;
import java.awt.*;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;

public class ThreadViewer extends JPanel {

    private ThreadViewerTableModel tableModel;

    public ThreadViewer() {
        tableModel = new ThreadViewerTableModel();

        JTable table = new JTable(tableModel);
        table.setAutoResizeMode(JTable.AUTO_RESIZE_LAST_COLUMN);

        TableColumnModel colModel = table.getColumnModel();
        int numColumns = colModel.getColumnCount();

        // manually size all but the last column
        for (int i = 0; i < numColumns - 1; i++) {
            TableColumn col = colModel.getColumn(i);

            col.sizeWidthToFit();
            col.setPreferredWidth(col.getWidth() + 5);
            col.setMaxWidth(col.getWidth() + 5);
        }

        JScrollPane sp = new JScrollPane(table);

        setLayout(new BorderLayout());
        add(sp, BorderLayout.CENTER);
    }

    public void dispose() {
        tableModel.stopRequest();
    }

    protected void finalize() throws Throwable {
        dispose();
    }

    public static JFrame createFramedInstance() {
        final ThreadViewer viewer = new ThreadViewer();

        final JFrame f = new JFrame("ThreadViewer");
        f.addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent e) {
                f.setVisible(false);
                f.dispose();
                viewer.dispose();
            }
        });

        f.setContentPane(viewer);
        f.setSize(500, 300);
        f.setVisible(true);

        return f;
    }

    public static void main(String[] args) {
        JFrame f = ThreadViewer.createFramedInstance();

        // For this example, exit the VM when the viewer
        // frame is closed.
        f.addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent e) {
                System.exit(0);
            }
        });

        // Keep the main thread from exiting by blocking
        // on wait() for a notification that never comes.
        Object lock = new Object();
        synchronized (lock) {
            try {
                lock.wait();
            } catch (InterruptedException x) {
            }
        }
    }
}
