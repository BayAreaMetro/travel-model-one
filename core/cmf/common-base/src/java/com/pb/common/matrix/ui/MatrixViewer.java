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

import com.pb.common.matrix.*;

import org.apache.log4j.Logger;


import java.awt.event.*;
import java.io.File;

import javax.swing.*;
import javax.swing.event.ChangeListener;
import javax.swing.event.ChangeEvent;

/** 
 * Display one or more matrices in a tabbed interface.
 *
 * @author    Tim Heier
 * @version   1.0, 3/27/2005
 */
public class MatrixViewer extends JFrame {

	protected static transient Logger logger = Logger.getLogger("com.pb.common.matrix.ui.MatrixViewer");

    private JFileChooser fileChooser;
    private MatrixNameDialog matrixDialog;

    private JTabbedPane jTabbedPane;

    private JMenuBar menuBar;
    private JMenu fileMenu;
    private JMenuItem openItem;
    private JMenuItem exitItem;

//    private MatrixViewerPanel mvPanel;

    public MatrixViewer (File file, String matrixName) {
        super("MatrixViewer 0.4");

        //Set Look and Feel before creating any UI components
        String nativeLF = UIManager.getSystemLookAndFeelClassName();
        try {
            UIManager.setLookAndFeel(nativeLF);
        }
        catch (Exception e) {
            e.printStackTrace();
        }

        JFrame.setDefaultLookAndFeelDecorated(true);
        JDialog.setDefaultLookAndFeelDecorated(true);

        initializeComponent();

        this.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        this.setLocation(100, 100);
        this.setSize(300, 300);
        this.setVisible(true);

        if (file != null) {
            do_openFile(file, matrixName);
        }
    }

    public MatrixViewer() {
        this(null, null);
    }

    private void initializeComponent() {

        //Create after look and feel has been established
        fileChooser = new JFileChooser();

        //Created but not shown yet
        matrixDialog = new MatrixNameDialog(this);

        //Create Menu Bar
        menuBar = new JMenuBar();
        this.setJMenuBar(menuBar);

        fileMenu = new JMenu("File");
        menuBar.add(fileMenu);

        openItem = new JMenuItem("Open...");
        fileMenu.add(openItem);

        openItem.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
                do_openFile();
            }
        });

        fileMenu.addSeparator();

        exitItem = new JMenuItem("Exit...");
        fileMenu.add(exitItem);

        exitItem.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
                System.exit(0);
            }
        });

        //Each MatrixViewer panel lives on it's own tabbed pane
        jTabbedPane = new JTabbedPane();

        jTabbedPane.addChangeListener(new ChangeListener() {
            public void stateChanged(ChangeEvent e)
            {
                jTabbedPane1_stateChanged(e);
            }

        });
        this.getContentPane().add(jTabbedPane);
    }

    private void jTabbedPane1_stateChanged(ChangeEvent e) {

    }

    private void do_openFile() {
        String matrixName = "";

        int returnVal = fileChooser.showOpenDialog(this);

        if (returnVal == JFileChooser.APPROVE_OPTION) {
            File file = fileChooser.getSelectedFile();

            MatrixType mType = MatrixReader.determineMatrixType(file);
            if (mType.equals(MatrixType.EMME2)) {
                matrixDialog.show();
                matrixName = matrixDialog.getMatrixName();
            }

            do_openFile(file, matrixName);
        }
    }

    private void do_openFile(File file, String matrixName) {
        Matrix m = MatrixReader.readMatrix(file, matrixName);
        MatrixViewerPanel mvPanel = new MatrixViewerPanel(m);

        m.logMatrixStatsToConsole();
        
        //Show matrix on it's tabbed pane
        jTabbedPane.addTab(file.getName(), mvPanel);
        this.pack();
    }

    public static void main(String[] args) {

        //File name and matrix name (eg Emme2 matrix)
        if (args.length == 2) {
            MatrixViewer viewer = new MatrixViewer(new File(args[0]), args[1]);
        }
        //File name only
        else if (args.length == 1) {
            MatrixViewer viewer = new MatrixViewer(new File(args[0]), null);
        }
        //No file name, display an empty window
        else {
            MatrixViewer viewer = new MatrixViewer();
        }
    }
}
