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

import javax.imageio.ImageIO;
import java.awt.image.RenderedImage;
import java.awt.image.BufferedImage;
import java.awt.image.DataBuffer;
import java.io.IOException;
import java.io.File;
import org.apache.log4j.Logger;

/**
 * Creates image files such as JPEG and TIFF.
 *
 * Note: This class is in the prototyping stage.
 *
 * @author    Tim Heier
 * @version   1.0, 11/1/2003
 */
public class ImageSaver {

    protected static Logger logger = Logger.getLogger("com.pb.common.image");


    /** Calculates the size of an image based on the actual size of the data buffer
     * which is more realistic than just width * height * bytesPerPixel (color).
     *
     * @param image to find size of
     * @return size of image in bytes
     */
    public static long sizeOf(BufferedImage image) {
        DataBuffer db = image.getRaster().getDataBuffer();
        int dataType = db.getDataType();
        int elementSizeInBits = DataBuffer.getDataTypeSize(dataType);

        return db.getNumBanks() * db.getSize() * elementSizeInBits / 8;
    }


    public static void saveAsTIFF(RenderedImage image, String fileName) throws IOException {

        String _fileName = fileName;

        if (! _fileName.endsWith("tiff"))
            _fileName = new String(fileName+"tiff");

        ImageIO.write(image, "tiff", new File(_fileName));
    }


    public static void saveAsJPEG(RenderedImage image, String fileName) throws IOException {

        String _fileName = fileName;

        if (! _fileName.endsWith("jpeg"))
            _fileName = new String(fileName+"jpeg");

        ImageIO.write(image, "jpeg", new File(_fileName));
    }

}
