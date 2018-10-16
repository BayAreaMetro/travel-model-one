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
package com.pb.common.matrix.tests;

import com.pb.common.matrix.*;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Set;
/**
 * @author    Joel Freedman
 * @version   1.0, 1/27/2003
 *
 * Tests class and methods in the matrix package.
 *
 */
public class TestMatrixCollection {

    /**
     * Create a full matrix and set some sample values into it.
     * Create some more full matrices, then store the full matrices
     * in the matrix collection.  Then get the matrix from the 
     * collection and query some values 
     */
    public static void testMatrixCollection() {
        Matrix m1 = new Matrix(10, 10);
        m1.setName("Matrix 1");

        for (int i = 1; i <= m1.getRowCount(); ++i)
            for (int j = 1; j <= m1.getColumnCount(); ++j)
                m1.setValueAt(i, j, (float) (i * 2) + (j * 7));

        System.out.println("\n--------- Matrix 1 ---------");
        MatrixUtil.print(m1, "%10.2f");

        Matrix m2 = m1.multiply(m1);
        m2.setName("Matrix 2");

        System.out.println("\n--------- Matrix 2 ---------");
        MatrixUtil.print(m2, "%10.2f");

        Matrix m3 = m2.subtract(m1);
        m3.setName("Matrix 3");

        System.out.println("\n--------- Matrix 3 ---------");
        MatrixUtil.print(m3, "%10.2f");

        MatrixCollection mc = new MatrixCollection();
        mc.addMatrix(m1);
        mc.addMatrix(m2);
        mc.addMatrix(m3);

        System.out.println(
            "Matrix 1 value at 1,3 = " + mc.getValue(1, 3, "Matrix 1"));
        System.out.println(
            "Matrix 2 value at 5,2 = " + mc.getValue(5, 2, "Matrix 2"));
        System.out.println(
            "Matrix 3 value at 10,10 = " + mc.getValue(10, 10, "Matrix 3"));

    }

    /**
    * Create a full matrix and set some sample values into it.
    * Create some more full matrices, then store the full matrices
    * in the matrix collection.  Then get the matrix from the 
    * collection and query some values 
    */
    public static void testCollapsedMatrixCollection() {
        Matrix m1 = new Matrix(10, 10);
        m1.setName("Matrix 1");

        for (int i = 1; i <= m1.getRowCount(); ++i) {
            for (int j = 1; j <= m1.getColumnCount(); ++j) {
                m1.setValueAt(i, j, (float) (i * 2) + (j * 7));
                //0-out cells divisible by 5
                if (m1.getValueAt(i, j) % 5 == 0)
                    m1.setValueAt(i, j, (float) 0.0);
            }
        }

        System.out.println("\n--------- Matrix 1 ---------");
        MatrixUtil.print(m1, "%10.2f");

        Matrix m2 = m1.multiply(m1);
        m2.setName("Matrix 2");

        System.out.println("\n--------- Matrix 2 ---------");
        MatrixUtil.print(m2, "%10.2f");

        Matrix m3 = m2.multiply((float) 0.5);
        m3.setName("Matrix 3");

        System.out.println("\n--------- Matrix 3 ---------");
        MatrixUtil.print(m3, "%10.2f");

        MatrixCollection mc = new CollapsedMatrixCollection(m1, true);
        mc.addMatrix(m2);
        mc.addMatrix(m3);

        System.out.println(
            "Matrix 1 value at 1,3 = " + mc.getValue(1, 3, "Matrix 1"));
        System.out.println(
            "Matrix 1 value at 3,4 = " + mc.getValue(3, 4, "Matrix 1"));
        System.out.println(
            "Matrix 2 value at 5,2 = " + mc.getValue(5, 2, "Matrix 2"));
        System.out.println(
            "Matrix 2 value at 5,6 = " + mc.getValue(5, 6, "Matrix 2"));
        System.out.println(
            "Matrix 3 value at 10,10 = " + mc.getValue(10, 10, "Matrix 3"));

        CollapsedMatrixCollection cmc = (CollapsedMatrixCollection) mc;
        System.out.println(
            "Total connected zone-pairs = " + cmc.getTotalCells());

        Matrix m4 = mc.getMatrix("Matrix 3");

        System.out.println("\n--------- Matrix 3 Again ---------");
        MatrixUtil.print(m4, "%10.2f");

    }
    public static void testEmme2MatrixCollection() {

        MatrixReader mr =
            MatrixReader.createReader(
                MatrixType.EMME2,
                new File("c:/projects/phoenix/2020/emme2ban"));
        Matrix m1 = mr.readMatrix("mf21");
        m1.setName("mf21");
        Matrix m2 = mr.readMatrix("mf131");
        m2.setName("mf131");
        Matrix m3 = mr.readMatrix("mf306");
        m3.setName("mf306");
        MatrixCollection mc = new MatrixCollection();
        mc.addMatrix(m1);
        mc.addMatrix(m2);
        mc.addMatrix(m3);

        System.out.println(
            "Matrix mf21 value at 101,1641 = "
                + m1.getValueAt(101, 1641)
                + ","
                + mc.getValue(101, 1641, "mf21"));
        System.out.println(
            "Matrix mf131 value at 12,1255 = "
                + m2.getValueAt(12, 1255)
                + ","
                + mc.getValue(12,1255, "mf131"));
        System.out.println(
            "Matrix mf306 value at 1641,264 = "
                + m3.getValueAt(1641, 264)
                +","
                + mc.getValue(1641, 264, "mf306"));

        Matrix m4 = mc.getMatrix("mf21");

        MatrixWriter mw =
            MatrixWriter.createWriter(
                MatrixType.EMME2,
                new File("c:/projects/phoenix/2020/emme2ban"));
        mw.writeMatrix("mf55", m4);

        //how about adding an ms, mo or md matrix to the collection?
        Matrix m6 = mr.readMatrix("ms1");
        Matrix m7 = mr.readMatrix("mo6");
        Matrix m8 = mr.readMatrix("md34");
        
        mc.addMatrix(m6);
        mc.addMatrix(m7);
        mc.addMatrix(m8);
        
        System.out.println(
            "Matrix ms1 value at 264 = "
                + m6.getValueAt(264, 264)
                +","
                + mc.getValue(264, 264, "ms1"));

        System.out.println(
            "Matrix mo6 value at 1272,1 = "
                + m7.getValueAt(1272, 1)
                +","                
                + mc.getValue(1272,1, "mo6"));

        System.out.println(
            "Matrix md34 value at 1,989 = "
                + m8.getValueAt(1, 989)
                +","
                + mc.getValue(1, 989, "md34"));

        


    }

    public static void testEmme2CollapsedMatrixCollection() {

        //storing all the skim names in HashMap; names map to matrix location
        HashMap peakWalkLocalSkimLocations = new HashMap();
        peakWalkLocalSkimLocations.put("ivt", "mf25");
        peakWalkLocalSkimLocations.put("fwt", "mf23");
        peakWalkLocalSkimLocations.put("twt", "mf24");
        peakWalkLocalSkimLocations.put("brd", "mf26");
        peakWalkLocalSkimLocations.put("acc", "mf27");
        peakWalkLocalSkimLocations.put("egr", "mf28");
        peakWalkLocalSkimLocations.put("far", "mf30");

        MatrixReader mr =
            MatrixReader.createReader(
                MatrixType.EMME2,
                new File("c:/projects/phoenix/2020/emme2ban"));
        Matrix m =
            mr.readMatrix((String) peakWalkLocalSkimLocations.get("ivt"));
        m.setName("ivt");
        MatrixCollection peakWalkLocalSkims = new CollapsedMatrixCollection(m);

        //get an iterator for the HashMap, traverse across the set and add the rest of the skims 
        //to the collapsed matrix collection
        Set keys = peakWalkLocalSkimLocations.keySet();

        // now we can create and initialize a new ArrayList with that collection
        ArrayList skimNames = new ArrayList(keys);

        // and now we can iterate
        for (int i = 0; i < skimNames.size(); i++) {
            String key = (String) skimNames.get(i);

            if (key == "ivt")
                continue;

            String loc = (String) peakWalkLocalSkimLocations.get(key);
            System.out.println("reading "+key+", "+loc+" from emme2ban");
            m = mr.readMatrix(loc);
            m.setName(key);
            peakWalkLocalSkims.addMatrix(m);
        }

        System.out.println(
            "peakWalkLocal IVT at 858,959 = "
                + peakWalkLocalSkims.getValue(858, 959, "ivt"));
        System.out.println(
            "peakWalkLocal FWT at 858,959 = "
                + peakWalkLocalSkims.getValue(858, 959, "fwt"));
        System.out.println(
            "peakWalkLocal ACC at 1641,101 = "
                + peakWalkLocalSkims.getValue(1641, 101, "acc"));

    }

    public static void main(String[] args) {
        TestMatrixCollection.testMatrixCollection();
        TestMatrixCollection.testCollapsedMatrixCollection();
        //TestMatrixCollection.testEmme2MatrixCollection();
       // TestMatrixCollection.testEmme2CollapsedMatrixCollection();
    }


}
