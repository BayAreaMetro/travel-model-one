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
package com.pb.common.image.tests;

import java.io.*;
import java.util.zip.GZIPOutputStream;

/**
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2003
 */
public class SVGImageTest {

    //public static int WIDTH = 30141;
    //blic static int HEIGHT = 26848;
    public static int WIDTH = 100;
    public static int HEIGHT = 200;

    public static String svgFile = "test.svg";
    public static String svgzFile = "test.svgz";


    public static void createSVGZFile() {
        try {
            // Create the GZIP output stream
            GZIPOutputStream out = new GZIPOutputStream(new FileOutputStream(svgzFile));

            // Transfer bytes from the input file to the GZIP output stream
            byte[] buf = new byte[1024];
            int len;

            // Complete the GZIP file
            out.finish();
            out.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public static void createSVGFile() {
        PrintWriter out = null;
        try {
            out = new PrintWriter(new BufferedWriter(new FileWriter(svgFile)));
        } catch (IOException e) {
            e.printStackTrace();
        }

        out.println("<svg>");

        int cy = 1;
        for (int row = 0; row < HEIGHT; row++) {
            int cx = 1;
            for (int col = 0; col < WIDTH; col++) {
                out.println("<circle cx=\"" + cx + "\" cy=\"" + cy + "\" r=\"1\"/>");
                cx += 2;
            }
            cy += 2;
        }

        out.println("</svg>");
        out.close();
    }


    public static void main(String[] args) {
        SVGImageTest.createSVGFile();
    }


}
