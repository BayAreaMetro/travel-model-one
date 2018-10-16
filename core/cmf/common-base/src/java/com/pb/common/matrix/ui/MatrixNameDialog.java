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

import java.awt.*;
import java.awt.event.*;
import javax.swing.*;

public class MatrixNameDialog extends JDialog {
    private JLabel jLabel1;
    private JLabel jLabel2;
    private JTextField jTextField;
    private JButton okjButton;
    private JPanel contentPane;

    private String matrixName;

    public MatrixNameDialog(Frame w) {
        super(w, "Enter Matrix Name", true);
        initializeComponent();

        this.setVisible(false);
    }

    private void initializeComponent() {
        jLabel1 = new JLabel();
        jLabel2 = new JLabel();
        jTextField = new JTextField();
        okjButton = new JButton();
        contentPane = (JPanel) this.getContentPane();

        jLabel1.setText("For an EMME2BAN file, please enter matrix name:");
        jLabel2.setText("eg. mf2");
        jTextField.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {
                jTextField1_actionPerformed(e);
            }

        });

        okjButton.setText("OK");
        okjButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent e) {
                okjButton_actionPerformed(e);
            }

        });

        contentPane.setLayout(null);
        addComponent(contentPane, jLabel1, 55, 17, 271, 23);
        addComponent(contentPane, jLabel2, 69, 53, 60, 18);
        addComponent(contentPane, jTextField, 125, 53, 100, 22);
        addComponent(contentPane, okjButton, 141, 184, 83, 28);

        this.setTitle("Enter Matrix Name");
        this.setLocation(new Point(103, 352));
        this.setSize(new Dimension(360, 260));
    }

    /**
     * Add Component Without a Layout Manager (Absolute Positioning)
     */
    private void addComponent(Container container, Component c, int x, int y, int width, int height) {
        c.setBounds(x, y, width, height);
        container.add(c);
    }

    private void jTextField1_actionPerformed(ActionEvent e) {
        selectionMade();
    }

    private void okjButton_actionPerformed(ActionEvent e) {
        selectionMade();
    }

    private void selectionMade() {
        matrixName = jTextField.getText();
        if (matrixName.length() < 3) {
            System.out.println("Error in matrix name");
        }
        this.setVisible(false);
    }

    public String getMatrixName() {
        return matrixName;
    }

    public static void main(String[] args) {
        JFrame.setDefaultLookAndFeelDecorated(true);
        JDialog.setDefaultLookAndFeelDecorated(true);
        try {
            UIManager.setLookAndFeel("com.sun.java.swing.plaf.windows.WindowsLookAndFeel");
        } catch (Exception ex) {
            System.out.println("Failed loading L&F: ");
            System.out.println(ex);
        }
        final JFrame w = new JFrame("Owner Window");
        JButton btn = new JButton("Show Dialog");
        btn.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent e) {
                new MatrixNameDialog(w);
            }
        });
        JPanel p = new JPanel();
        p.add(btn);
        w.getContentPane().add(p);
        w.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        w.setSize(500, 360);
        w.setLocation(150, 36);
        w.setVisible(true);
    }

}
