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

import com.pb.common.image.ImageSaver;

import java.awt.image.BufferedImage;
import java.awt.*;
import java.io.IOException;


/**
 * Test class for the ImageSaver class.
 *
 * Note: This class is in the prototyping stage.
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2003
 */
public class ImageSaverTest {

    public static int WIDTH = 30141;
    public static int HEIGHT = 26848;
    //public static int WIDTH = 640;
    //public static int HEIGHT = 480;


    public static void main(String[] args) {

        ImageSaverTest test = new ImageSaverTest();
        test.testSaveAsTIFF();
        test.testSaveAsJPEG();
        test.testSizeOf();
    }


    public void testSaveAsTIFF() {

        try {
            ImageSaver.saveAsTIFF(createImage(), "test_image.tiff");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public void testSaveAsJPEG() {

        try {
            ImageSaver.saveAsJPEG(createImage(), "test_image.jpeg");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public void testSizeOf() {

        System.out.println("size of test image = " + ImageSaver.sizeOf(createImage()));
    }


    /** Create a test image.
     *
     * @return  buffered image
     */

    public BufferedImage createImage() {
        //BufferedImage img = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_BYTE_BINARY);
        BufferedImage img = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = img.createGraphics();

        g2d.setBackground(Color.WHITE);
        g2d.clearRect(0,0,WIDTH,HEIGHT);

        g2d.setColor(Color.BLACK);
        g2d.drawLine(50,50,250,250);
        g2d.drawRect(310,310,100,100);

        return img;
    }


/*
    public static BufferedImage createImage() {

        ImageFactory gs = new ImageFactory();
        int wid = 64, ht = 64;
        short data[] = new short[wid * ht];
        for (int i = 0; i < ht; i++) {
            for (int j = 0; j < wid; j++) {
                data[i * ht + j] = (short) j;
            }
        }
        gs.setImageDimension(wid, ht);
        gs.setData(data);

        wid = 64;
        ht = 64;
        short data1[][] = new short[3][wid * ht];
        for (int k = 0; k < 3; k++) {
            for (int i = 0; i < ht; i++) {
                for (int j = 0; j < wid; j++) {
                    data1[k][i * ht + j] = (short) (j * k);
                }
            }
        }
        return gs.createBandedImage(64, 64, 8, data1);
    }
*/

}

