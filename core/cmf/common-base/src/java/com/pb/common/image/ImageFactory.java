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
package com.pb.common.image;

import java.awt.*;
import java.awt.image.*;
import java.awt.color.*;
import java.util.*;

/**
 * Creates instances of BufferedImage classes based on object data.
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2003
 */
public class ImageFactory {
    private short pixels[];
    private BufferedImage grayscaleImage;
    private int imageWidth = 256, imageHeight = 256;
    private int imageDepth = 8;
    private Object data;


    public ImageFactory() {
    }


    public ImageFactory(int width, int height, int depth, short data[]) {
        this.imageWidth = width;
        this.imageHeight = height;
        this.imageDepth = depth;
        this.data = data;
        grayscaleImage = createImage();
    }


    public void setImageDimension(int width, int height) {
        this.imageWidth = width;
        this.imageHeight = height;
    }

    public void setImageDepth(int depth) {
        this.imageDepth = depth;
    }

    public void setData(short data[]) {
        this.data = data;
        grayscaleImage = createImage();
    }

    public BufferedImage getGrayscaleImage() {
        return grayscaleImage;

    }

    public BufferedImage createImage() {

        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_GRAY),
                new int[]{imageDepth}, false, false,
                Transparency.OPAQUE,
                DataBuffer.TYPE_USHORT);
        ComponentSampleModel csm = new ComponentSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight, 1, imageWidth, new int[]{0});
        DataBuffer dataBuf = new DataBufferUShort((short[]) data, imageWidth);
        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));
        Hashtable ht = new Hashtable();
        ht.put("owner", "Lawrence Rodrigues");

        return new BufferedImage(ccm, wr, true, ht);
    }

    public static BufferedImage createGrayscaleImage(int imageWidth,
                                                     int imageHeight,
                                                     int imageDepth,
                                                     short data[]) {
        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_GRAY),
                new int[]{imageDepth},
                false, //hasAplha
                false, // alpha pre-multiplied
                Transparency.OPAQUE,
                DataBuffer.TYPE_USHORT);
        ComponentSampleModel csm = new ComponentSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight, 1, imageWidth, new int[]{0});
        DataBuffer dataBuf = new DataBufferUShort((short[]) data, imageWidth);
        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));
        Hashtable ht = new Hashtable();
        ht.put("owner", "Lawrence Rodrigues");
        return new BufferedImage(ccm, wr, true, ht);
    }


    public static BufferedImage createBandedRGBImage(int imageWidth,
                                                     int imageHeight,
                                                     int imageDepth,
                                                     short data[][]) {
        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_sRGB),
                new int[]{8, 8, 8}, false, false,
                Transparency.OPAQUE,
                DataBuffer.TYPE_USHORT);
        BandedSampleModel csm = new BandedSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight, 3); //,imageWidth, new int[] {0,1,2});
        DataBuffer dataBuf = new DataBufferUShort((short[][]) data, imageWidth);
        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));
        Hashtable ht = new Hashtable();
        ht.put("owner", "Lawrence Rodrigues");
        return new BufferedImage(ccm, wr, true, ht);
    }


    public static BufferedImage createBandedImage(int imageWidth,
                                                  int imageHeight,
                                                  int imageDepth,
                                                  short data[][]) {
        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_sRGB),
                new int[]{8, 8, 8}, false, false,
                Transparency.OPAQUE,
                DataBuffer.TYPE_USHORT);
        BandedSampleModel csm = new BandedSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight, imageWidth,
                new int[]{0, 1, 2}, new int[]{0, 1, 2});
        DataBuffer dataBuf = new DataBufferUShort(data, imageWidth * imageHeight);
        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));
        Hashtable ht = new Hashtable();
        ht.put("owner", "Lawrence Rodrigues");
        return new BufferedImage(ccm, wr, false, ht);
    }


    public static BufferedImage createInterleavedRGBImage(int imageWidth,
                                                          int imageHeight,
                                                          int imageDepth,
                                                          short data[],
                                                          boolean hasAlpha) {
        int pixelStride,transparency;
        if (hasAlpha) {
            pixelStride = 4;
            transparency = Transparency.TRANSLUCENT;
        } else {
            pixelStride = 3;
            transparency = Transparency.OPAQUE;
        }
        int[] numBits = new int[pixelStride];
        int[] bandoffsets = new int[pixelStride];

        for (int i = 0; i < pixelStride; i++) {
            numBits[i] = imageDepth;
            bandoffsets[i] = i;
        }

        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_sRGB),
                numBits,
                hasAlpha,
                false, //Alpha pre-multiplied
                transparency,
                DataBuffer.TYPE_USHORT);
        PixelInterleavedSampleModel csm = new PixelInterleavedSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight,
                pixelStride, //Pixel stride
                imageWidth * pixelStride, // Scanline stride
                bandoffsets);

        DataBuffer dataBuf = new DataBufferUShort(data, imageWidth * imageHeight * pixelStride);
        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));
        Hashtable ht = new Hashtable();
        ht.put("owner", "Lawrence Rodrigues");
        return new BufferedImage(ccm, wr, false, ht);
    }


    public static BufferedImage createRandomInterleavedImage(int wid, int ht, boolean hasAlpha) {
        int numBands = 3;
        if (hasAlpha) numBands = 4;
        short data1[] = new short[wid * ht * numBands];
        for (int i = 0; i < ht; i++) {
            for (int j = 0; j < wid; j++) {
                for (int k = 0; k < numBands; k++) {
                    if (k == 0 && hasAlpha)
                        data1[((i * wid + j) * numBands) + k] = (short) (255);
                    else
                        data1[((i * wid + j) * numBands) + k] = (short) (255 * Math.abs(Math.random()));
                }
            }
        }
        return ImageFactory.createInterleavedRGBImage(wid, ht, 8, data1, hasAlpha);
    }


    public static BufferedImage createBandedRGBImage(int imageWidth,
                                                     int imageHeight,
                                                     int imageDepth,
                                                     short data[][],
                                                     boolean hasAlpha) {
        int numbits,transparency;
        if (hasAlpha) {
            numbits = 4;
            transparency = Transparency.TRANSLUCENT;
        } else {
            numbits = 3;
            transparency = Transparency.OPAQUE;
        }
        int[] bits = new int[numbits];
        int[] bandoffsets = new int[numbits];
        int[] bandindices = new int[numbits];

        for (int i = 0; i < numbits; i++) {
            bits[i] = imageDepth;
            bandoffsets[i] = i;
            bandindices[i] = i;
        }

        ComponentColorModel ccm = new ComponentColorModel(
                ColorSpace.getInstance(ColorSpace.CS_sRGB),
                bits, //image depth array
                hasAlpha,
                false,
                Transparency.OPAQUE,
                DataBuffer.TYPE_USHORT);

        BandedSampleModel csm = new BandedSampleModel(
                DataBuffer.TYPE_USHORT,
                imageWidth, imageHeight,
                imageWidth, //scan line stride
                bandindices,
                bandoffsets);

        DataBuffer dataBuf = new DataBufferUShort(data, imageWidth * imageHeight);

        WritableRaster wr = Raster.createWritableRaster(csm, dataBuf, new Point(0, 0));

        return new BufferedImage(ccm, wr, false, null);
    }


    public static BufferedImage createRandomBandedImage(int wid, int ht) {
        short data1[][] = new short[3][wid * ht];
        for (int k = 0; k < 3; k++) {
            for (int i = 0; i < ht; i++) {
                for (int j = 0; j < wid; j++) {
                    data1[k][i * wid + j] = (short) (j * k);
                }
            }
        }
        return createBandedRGBImage(64, 64, 8, data1, false);
    }



    public static BufferedImage createGrayscaleBar(int wid, int ht, int maxvalue) {
        if ((wid < 0) || (ht < 0)) return null;
        int bits = 8;
        if (maxvalue > 255) bits = 16;
        short data[] = new short[wid * ht];
        int ratio = (int) (maxvalue / ht);
        for (int i = 0; i < ht; i++) {
            for (int j = 0; j < wid; j++) {
                data[i * wid + j] = (short) (i * ratio);
            }
        }
        return createGrayscaleImage(wid, ht, bits, data);
    }


    public static BufferedImage convertPackedToInterleaved(BufferedImage img) {
        ColorModel cm = img.getColorModel();
        if (!(cm instanceof DirectColorModel)) return null;
        int wid = img.getWidth(), ht = img.getHeight();
        short data1[] = new short[wid * ht * 3];
        SampleModel sm = img.getSampleModel();
        WritableRaster wr = img.getRaster();
        DataBuffer db = wr.getDataBuffer();
        int numbands = wr.getNumBands();
        int sample[] = new int[numbands];
        for (int i = 0; i < ht; i++) {
            for (int j = 0; j < wid; j++) {
                int pix[] = null;
                sample = (sm.getPixel(j, i, pix, db));
                for (int l = 0; l < numbands; l++)
                    data1[i * wid * 3 + (j * 3) + l] = (short) sample[l];
            }
        }
        return ImageFactory.createInterleavedRGBImage(wid, ht, 8, data1, false);
    }


    public static void main(String[] args) {
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
        BufferedImage bi = gs.createImage();

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
        BufferedImage bi1 = ImageFactory.createBandedImage(64, 64, 8, data1);
        //if (bi1 != null) JpegUtil.saveImageAsJPEG(bi1, "rgb.jpg");
    }
}
