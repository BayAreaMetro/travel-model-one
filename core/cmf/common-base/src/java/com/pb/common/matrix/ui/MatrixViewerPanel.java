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
package com.pb.common.matrix.ui;

import com.pb.common.matrix.Matrix;
import com.pb.common.matrix.MatrixReader;
import com.pb.common.ui.swing.DecimalFormatRenderer;
import com.pb.common.ui.swing.RightAlignHeaderRenderer;
import com.pb.common.ui.swing.RowHeaderRenderer;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import javax.swing.table.TableCellRenderer;
import javax.swing.table.TableColumn;
import java.awt.*;
import java.io.File;

/**
 * Shows matrix values in a spreadsheet like view using a JTable with fixed
 * row and header columns.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class MatrixViewerPanel extends JPanel {

    private static boolean DEBUG = true;
    protected static File matrixFile;

    /**
     * Displays a matrix in a table.
     *
     * @param m the matrix to display
     */
    public MatrixViewerPanel(Matrix m) {
        super(new GridLayout(1,0));
        createViewer(m);
    }

    /**
     * Creates the panel which contains a JTable.
     *
     * @param m the matrix to display
     */
    private void createViewer(Matrix m) {

        //Adapts a Matrix to a TableModel
        MatrixDataModel dataModel = new MatrixDataModel( m );

        //Create table to hold data and format it
        JTable dataTable = new JTable(dataModel);
        dataTable.setPreferredScrollableViewportSize(new Dimension(800, 600));
        dataTable.setAutoResizeMode(JTable.AUTO_RESIZE_OFF);

        initColumnSizes(dataTable);
        initCellValueDecimalFormat(dataTable, 2);

        JScrollPane scrollPane = createJScrollPane(dataTable);
        this.add(scrollPane);

//        if (DEBUG) {
//            table.addMouseListener(new MouseAdapter() {
//                public void mouseClicked(MouseEvent e) {
//                    printDebugData(table);
//                }
//            });
//        }

    }

    /**
     * Create a JScrollPane to hold a table and it's row header.
     *
     * @param dataTable table which holds matrix data
     * @return a JScrollPane with a dataTable in the viewport and rowHeader in the
     *           row heading area
     */
    private JScrollPane createJScrollPane(JTable dataTable) {

        int nRows = dataTable.getRowCount();
        //int nCols = dataTable.getColumnCount();
        MatrixDataModel model = (MatrixDataModel) dataTable.getModel();

        //Create TableModel for rowHeader
        DefaultTableModel headerData = new DefaultTableModel(0, 1);

        for (int i = 0; i < nRows; i++) {
            headerData.addRow(new Object[] {" " + model.getExternalRowNumber(i) + " "} );
        }

        /*for (int i = 0; i < nCols; i++) {
            headerData.addRow(new Object[] {" " + model.getExternalColNumber(i) + " "} );
        }*/

        //Create rowHeader
        JTable rowHeader = new JTable(headerData);

        LookAndFeel.installColorsAndFont
            (rowHeader, "TableHeader.background", "TableHeader.foreground", "TableHeader.font");

        JScrollPane scrollPane = new JScrollPane(dataTable,
                                                JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                                JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        rowHeader.setIntercellSpacing(new Dimension(0, 0));
        Dimension d = rowHeader.getPreferredScrollableViewportSize();
        d.width = rowHeader.getPreferredSize().width;
        rowHeader.setPreferredScrollableViewportSize(d);
        rowHeader.setRowHeight(dataTable.getRowHeight());
        rowHeader.setDefaultRenderer(Object.class, new RowHeaderRenderer());

        scrollPane.setRowHeaderView(rowHeader);

//        new JScrollPaneAdjuster(scrollPane);
//        new JTableRowHeaderResizer(scrollPane).setEnabled(true);

//        scrollPane.addComponentListener(new ComponentListener() {
//            public void componentResized(ComponentEvent e) {
//                Component c = e.getComponent();
//                Dimension d = c.getSize();
//                System.out.println("width=" + d.getWidth() + ", height=" + d.getHeight());
//            }
//            public void componentMoved(ComponentEvent e) { }
//            public void componentShown(ComponentEvent e) { }
//            public void componentHidden(ComponentEvent e) { }
//        }
//        );

            //Add header for JScrollPane corner
//        JTableHeader corner = rowHeader.getTableHeader();
//        corner.setReorderingAllowed(false);
//        corner.setResizingAllowed(false);
//        scrollPane.setCorner(JScrollPane.UPPER_LEFT_CORNER, corner);

        return scrollPane;
    }

    /*
     * This method picks good column sizes.
     * If all column heads are wider than the column's cells'
     * contents, then you can just use column.sizeWidthToFit().
     */
    private void initColumnSizes(JTable table) {
        TableColumn column = null;
        Component comp = null;
        int headerWidth = 0;
        int maxHeaderWidth = 0;
        TableCellRenderer headerRenderer = table.getTableHeader().getDefaultRenderer();

        // find the column width of the largest header value
        for (int i = 0; i < table.getColumnCount(); i++) {
            column = table.getColumnModel().getColumn(i);
            comp = headerRenderer.getTableCellRendererComponent(null, column.getHeaderValue(),
                                                                false, false, 0, 0);

            headerWidth = comp.getPreferredSize().width;

            if ( headerWidth > maxHeaderWidth )
            	maxHeaderWidth = headerWidth;
        }

        //Ensure columns are wide enough for most numbers
        if (maxHeaderWidth < 30)
            maxHeaderWidth = 30;

        //Create a new render to right align header values
        RightAlignHeaderRenderer newHeaderRenderer = new RightAlignHeaderRenderer();

        // set all column widths uniformly to the max width increased by some fixed percent (i.e. 100%)
        for (int i = 0; i < table.getColumnCount(); i++) {
        	column = table.getColumnModel().getColumn(i);
        	column.setPreferredWidth( (int)(maxHeaderWidth*2.0) );
            column.setHeaderRenderer(newHeaderRenderer);
        }
    }

    private void initCellValueDecimalFormat(JTable table, int decimalPlaces) {
        TableColumn column = null;

        for (int i = 0; i < table.getColumnCount(); i++) {
        	column = table.getColumnModel().getColumn(i);
        	column.setCellRenderer( new DecimalFormatRenderer(decimalPlaces) );
        }
    }

    /**
     * Create the GUI and show it.  For thread safety, this method should be
     * invoked from the event-dispatching thread.
     */
    private static void createAndShowGUI(File file) {

        //Try to read the matrix before doing anything
        Matrix m = MatrixReader.readMatrix(file, "");
        MatrixViewerPanel matrixContentPane = new MatrixViewerPanel(m);

        //Configure look and feel
        String nativeLF = UIManager.getSystemLookAndFeelClassName();
        try {
            UIManager.setLookAndFeel(nativeLF);
        }
        catch (Exception e) {
            e.printStackTrace();
        }

        JFrame.setDefaultLookAndFeelDecorated(true);

        JFrame frame = new JFrame("MatrixViewer - " + file.getAbsolutePath());
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

        matrixContentPane.setOpaque(true); //content panes must be opaque
        frame.setContentPane(matrixContentPane);

        frame.pack();
        frame.setLocation(200, 100);
        frame.setVisible(true);
    }

    private void printDebugData(JTable table) {
        int numRows = table.getRowCount();
        int numCols = table.getColumnCount();
        javax.swing.table.TableModel model = table.getModel();

        System.out.println("Value of data: ");
        for (int i=0; i < numRows; i++) {
            System.out.print("    row " + i + ":");
            for (int j=0; j < numCols; j++) {
                System.out.print("  " + model.getValueAt(i, j));
            }
            System.out.println();
        }
        System.out.println("--------------------------");
    }

    private static void usage() {
        System.out.println
         ("\n"+
            "usage: java " + MatrixViewer.class.getName() + " <name-of-matrix-file>\n"
         );
        System.exit(1);
    }

    /**
     * Using Main is a convenience for testing. It will show the MatrixViewer panel in
     * a simple JFrame.
     *
     * @param args program arguements - should be the file name of the matrix to display
     */
    public static void main(String[] args) {
        if (args.length < 1) {
            usage();
        }

        final File file = new File(args[0]);

        //Schedule a job for the event-dispatching thread:
        //creating and showing this application's GUI.
        javax.swing.SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                createAndShowGUI(file);
            }
        });
    }
}
